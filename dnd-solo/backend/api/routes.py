"""FastAPI routes: chat (game loop), character, saves, dice, health."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from ..db import database as db
from ..engine import state as st
from ..engine.dice import roll as dice_roll, DiceError
from ..llm.client import KoboldClient, LLMError
from ..llm.parser import parse_dm_response, ProtocolError
from ..llm.prompt_builder import build_messages
from ..translate.translator import Translator

log = logging.getLogger("api")
router = APIRouter()

_ROOT = Path(__file__).resolve().parents[2]  # dnd-solo/ (routes.py -> api -> backend -> dnd-solo)
with open(_ROOT / "config.yaml", encoding="utf-8") as f:
    CFG = yaml.safe_load(f)

DB_PATH = str(_ROOT / CFG["paths"]["db_path"])
db.init_db(DB_PATH)

client = KoboldClient(
    endpoint=CFG["llm"]["endpoint"],
    model=CFG["llm"]["model"],
    temperature=CFG["llm"]["temperature"],
    max_tokens=CFG["llm"]["max_tokens"],
    timeout=CFG["llm"]["request_timeout"],
)
translator = Translator(DB_PATH, enabled=CFG["translate"]["enabled"],
                        retries=CFG["translate"]["retries"],
                        backoff_base=CFG["translate"]["backoff_base"])

SESSION: dict[str, Any] = {
    "state": st.GameState(),
    "history_en": [],
}

# упрощённая карта навыков → характеристика (V2 — Rules Engine)
_SKILL_ABIL = {
    "perception": "wis", "stealth": "dex", "athletics": "str",
    "arcana": "int", "history": "int", "insight": "wis",
    "medicine": "wis", "persuasion": "cha", "deception": "cha",
    "intimidation": "cha", "investigation": "int", "acrobatics": "dex",
    "sleight of hand": "dex", "survival": "wis", "nature": "int",
    "religion": "int", "performance": "cha", "animal handling": "wis",
}


class CharacterIn(BaseModel):
    # поле strength с alias "str": имя "str" затеняет builtin и ломает pydantic
    model_config = ConfigDict(populate_by_name=True)

    name: str = "Герой"
    race: str = "Человек"
    class_name: str = "Следопыт"
    level: int = 1
    strength: int = Field(10, alias="str")
    dexterity: int = Field(10, alias="dex")
    constitution: int = Field(10, alias="con")
    intelligence: int = 10
    wisdom: int = Field(10, alias="wis")
    charisma: int = Field(10, alias="cha")
    hp_max: int = 10
    ac: int = 12
    speed: int = 30


class ChatIn(BaseModel):
    message: str  # RU


class RollIn(BaseModel):
    formula: str


class SaveIn(BaseModel):
    name: str


@router.get("/api/health")
async def health() -> dict[str, Any]:
    llm_ok = await client.health()
    return {"backend": True, "koboldcpp": llm_ok, "db": Path(DB_PATH).exists()}


@router.post("/api/character")
async def set_character(c: CharacterIn) -> dict[str, Any]:
    """Ручной ввод листа персонажа (MVP-форма)."""
    state = st.GameState(character=st.Character(
        name=c.name, race=c.race, class_name=c.class_name, level=c.level,
        str=c.strength, dex=c.dexterity, con=c.constitution,
        intelligence=c.intelligence, wis=c.wisdom, cha=c.charisma,
        hp_max=c.hp_max, hp_current=c.hp_max, ac=c.ac, speed=c.speed,
    ))
    SESSION["state"] = state
    SESSION["history_en"] = []
    return state.to_prompt_dict()


@router.get("/api/state")
async def get_state() -> dict[str, Any]:
    return SESSION["state"].to_prompt_dict()


@router.post("/api/roll")
async def roll(r: RollIn) -> dict[str, Any]:
    try:
        res = dice_roll(r.formula)
    except DiceError as e:
        raise HTTPException(400, str(e))
    return {"formula": res.formula, "total": res.total, "rolls": res.rolls,
            "dropped": res.dropped, "modifier": res.modifier, "mode": res.mode}


@router.post("/api/chat")
async def chat(msg: ChatIn) -> dict[str, Any]:
    """Полный game loop (ТЗ 5.7): перевод → prompt → LLM → парс → state → перевод."""
    state: st.GameState = SESSION["state"]
    history: list[dict[str, str]] = SESSION["history_en"]

    # 1. Автоснапшот для undo + перевод RU→EN
    db.push_undo(DB_PATH, state.to_dict())
    action_en = await translator.ru_to_en(msg.message)

    # 2. Prompt → запрос к LLM → парс с retry
    raw_response = ""
    dm = None
    last_err = ""
    for attempt in range(CFG["llm"]["json_retries"] + 1):
        messages = build_messages(
            state=state.to_prompt_dict(),
            history=history[-CFG["game"]["history_max_messages"]:],
            player_action_en=action_en,
            campaign_text=state.campaign_text,
            last_result=last_err or None,
        )
        try:
            raw_response = await client.chat(messages)
        except LLMError as e:
            db.log_llm(DB_PATH, {"messages": messages}, None, ok=False)
            raise HTTPException(502, f"LLM недоступен: {e}")
        db.log_llm(DB_PATH, {"messages": messages}, raw_response, ok=True)
        try:
            dm = parse_dm_response(raw_response)
            break
        except ProtocolError as e:
            last_err = (f"Your previous response was invalid: {e}. "
                        f"Return ONLY the correct JSON object.")
            log.warning("protocol error (attempt %d): %s", attempt + 1, e)

    if dm is None:
        raise HTTPException(502, "LLM не смог вернуть валидный JSON после ретраев")

    # 3. Валидация и применение state_changes движком
    try:
        applied = st.apply_state_changes(state, dm.state_changes)
    except st.StateChangeError as e:
        log.warning("state_change rejected: %s", e)
        applied = [f"[отклонено движком] {e}"]

    # 4. requested_checks — бросает движок (не LLM)
    check_results = []
    for chk in dm.requested_checks:
        bonus = 0
        ctype = chk["type"]
        if ctype in ("skill", "attack"):
            skill = str(chk.get("name", "")).lower()
            abil = _SKILL_ABIL.get(skill, "str")
            bonus = state.character.ability_mods[abil]
            if skill in [p.lower() for p in state.character.proficiencies]:
                bonus += state.character.proficiency_bonus
        elif ctype == "initiative":
            bonus = state.character.ability_mods["dex"] + state.character.initiative_bonus
        roll_res = dice_roll("1d20")
        total = roll_res.total + bonus
        check_results.append(
            f"{ctype} {chk.get('name', '')} vs DC {chk['dc']}: "
            f"roll {roll_res.rolls[0]} + {bonus} = {total} -> "
            f"{'SUCCESS' if total >= chk['dc'] else 'FAILURE'} ({chk.get('reason', '')})"
        )

    # 5. Перевод narrative и suggested_actions EN→RU
    narrative_ru = await translator.en_to_ru(dm.narrative)
    actions_ru = [await translator.en_to_ru(a) for a in dm.suggested_actions]

    # 6. История
    state.turn += 1
    history.append({"role": "user", "content": f"[Player action] {action_en}"})
    history.append({"role": "assistant", "content": dm.narrative})
    if check_results:
        history.append({"role": "user",
                        "content": "[Engine dice results, apply them in the next reply]\n"
                                   + "\n".join(check_results)})
        narrative_ru += "\n\n🎲 " + " | ".join(check_results)

    return {
        "narrative": narrative_ru,
        "suggested_actions": actions_ru,
        "state_changes_applied": applied,
        "requested_checks": dm.requested_checks,
        "check_results": check_results,
        "state": state.to_prompt_dict(),
    }


@router.post("/api/save")
async def save(s: SaveIn) -> dict[str, Any]:
    db.save_snapshot(DB_PATH, s.name, SESSION["state"].to_dict())
    return {"ok": True, "name": s.name}


@router.post("/api/load")
async def load_save(s: SaveIn) -> dict[str, Any]:
    snap = db.load_snapshot(DB_PATH, s.name)
    if snap is None:
        raise HTTPException(404, f"Сохранение {s.name!r} не найдено")
    SESSION["state"] = st.GameState.from_dict(snap)
    SESSION["history_en"] = []
    return SESSION["state"].to_prompt_dict()


@router.get("/api/saves")
async def saves() -> list[dict[str, Any]]:
    return db.list_saves(DB_PATH)


@router.post("/api/undo")
async def undo() -> dict[str, Any]:
    snap = db.pop_undo(DB_PATH)
    if snap is None:
        raise HTTPException(404, "Нечего откатывать")
    SESSION["state"] = st.GameState.from_dict(snap)
    return SESSION["state"].to_prompt_dict()
