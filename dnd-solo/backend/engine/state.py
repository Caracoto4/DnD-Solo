"""State Manager — единственный модуль, изменяющий состояние игры.

Хранит Character, Inventory, Quest Log, World State.
LLM НЕ меняет числа напрямую — только через state_changes, которые
валидируются и применяются здесь (см. apply_state_changes).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from typing import Any

from .dice import modifier_for


@dataclass
class Character:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "Герой"
    race: str = "Человек"
    class_name: str = "Следопыт"
    level: int = 1
    str: int = 10
    dex: int = 10
    con: int = 10
    intelligence: int = 10
    wis: int = 10
    cha: int = 10
    hp_max: int = 10
    hp_current: int = 10
    hp_temp: int = 0
    ac: int = 12
    initiative_bonus: int = 0
    speed: int = 30
    hit_dice: str = "1d10"
    death_saves_success: int = 0
    death_saves_fail: int = 0
    conditions: list[str] = field(default_factory=list)
    proficiencies: list[str] = field(default_factory=list)

    @property
    def ability_mods(self) -> dict[str, int]:
        return {
            "str": modifier_for(self.str),
            "dex": modifier_for(self.dex),
            "con": modifier_for(self.con),
            "int": modifier_for(self.intelligence),
            "wis": modifier_for(self.wis),
            "cha": modifier_for(self.cha),
        }

    @property
    def proficiency_bonus(self) -> int:
        return 2 + (self.level - 1) // 4

    @property
    def is_unconscious(self) -> bool:
        return self.hp_current <= 0

    def to_prompt_dict(self) -> dict[str, Any]:
        """Компактный dict для system prompt (без перевода — числа)."""
        return {
            "name": self.name, "race": self.race, "class": self.class_name,
            "level": self.level,
            "abilities": {"STR": self.str, "DEX": self.dex, "CON": self.con,
                          "INT": self.intelligence, "WIS": self.wis, "CHA": self.cha},
            "modifiers": {k.upper(): v for k, v in self.ability_mods.items()},
            "proficiency_bonus": self.proficiency_bonus,
            "hp": {"current": self.hp_current, "max": self.hp_max, "temp": self.hp_temp},
            "ac": self.ac, "speed": self.speed,
            "conditions": self.conditions,
            "death_saves": {"success": self.death_saves_success, "fail": self.death_saves_fail},
        }


@dataclass
class Item:
    name: str
    qty: int = 1
    equipped: bool = False
    weight: float = 0.0


@dataclass
class WorldState:
    location: str = ""
    time_of_day: str = ""
    weather: str = ""
    flags: dict[str, Any] = field(default_factory=dict)


@dataclass
class GameState:
    """Единый источник правды игры."""
    character: Character = field(default_factory=Character)
    inventory: list[Item] = field(default_factory=list)
    world: WorldState = field(default_factory=WorldState)
    quest_log: list[dict[str, Any]] = field(default_factory=list)
    campaign_text: str = ""
    turn: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "character": asdict(self.character),
            "inventory": [asdict(i) for i in self.inventory],
            "world": asdict(self.world),
            "quest_log": self.quest_log,
            "turn": self.turn,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "GameState":
        st = cls()
        st.character = Character(**d.get("character", {}))
        st.inventory = [Item(**i) for i in d.get("inventory", [])]
        st.world = WorldState(**d.get("world", {}))
        st.quest_log = d.get("quest_log", [])
        st.turn = d.get("turn", 0)
        return st

    def to_prompt_dict(self) -> dict[str, Any]:
        return {
            "character": self.character.to_prompt_dict(),
            "inventory": [{"name": i.name, "qty": i.qty, "equipped": i.equipped}
                          for i in self.inventory],
            "location": self.world.location,
            "time_of_day": self.world.time_of_day,
            "weather": self.world.weather,
            "flags": self.world.flags,
            "quests": self.quest_log,
            "turn": self.turn,
        }


# ── Применение state_changes от LLM ───────────────────────────────

VALID_OPS = {
    "damage", "heal", "set_hp_temp", "add_item", "remove_item", "equip_item",
    "set_flag", "add_condition", "remove_condition", "add_quest", "update_quest",
    "set_location", "set_time", "set_weather", "use_spell_slot",
    "death_save", "reset_death_saves",
}


class StateChangeError(ValueError):
    pass


def apply_state_changes(state: GameState, changes: list[dict[str, Any]]) -> list[str]:
    """Валидирует и применяет state_changes. Возвращает список применённых операций.

    Броски урона ("amount": "2d6") выполняются движком (Dice Roller),
    LLM не может напрямую менять числа.
    """
    from .dice import roll as dice_roll

    applied: list[str] = []
    for ch in changes:
        op = ch.get("op")
        if op not in VALID_OPS:
            raise StateChangeError(f"Неизвестная операция: {op!r}")
        if ch.get("target", "player") != "player":
            applied.append(f"[skipped npc op] {op}")
            continue
        c = state.character

        if op in ("damage", "heal"):
            amount = ch.get("amount")
            total = dice_roll(amount).total if isinstance(amount, str) else int(amount)
            if op == "damage":
                dmg_type = ch.get("type", "bludgeoning")
                if c.hp_temp > 0:
                    absorbed = min(c.hp_temp, total)
                    c.hp_temp -= absorbed
                    total -= absorbed
                c.hp_current = max(-c.hp_max, c.hp_current - total)
                applied.append(f"damage {total} ({dmg_type}), hp={c.hp_current}")
            else:
                c.hp_current = min(c.hp_max, c.hp_current + total)
                applied.append(f"heal {total}, hp={c.hp_current}")
        elif op == "set_hp_temp":
            c.hp_temp = max(0, int(ch.get("value", 0)))
            applied.append(f"hp_temp={c.hp_temp}")
        elif op == "add_item":
            name = str(ch.get("item", "")).strip()
            if not name:
                raise StateChangeError("add_item: нет имени предмета")
            qty = int(ch.get("qty", 1))
            if qty <= 0:
                raise StateChangeError("add_item: qty должен быть > 0")
            found = next((i for i in state.inventory if i.name.lower() == name.lower()), None)
            if found:
                found.qty += qty
            else:
                state.inventory.append(Item(name=name, qty=qty))
            applied.append(f"add_item {name} x{qty}")
        elif op == "remove_item":
            name = str(ch.get("item", "")).strip()
            qty = int(ch.get("qty", 1))
            found = next((i for i in state.inventory if i.name.lower() == name.lower()), None)
            if not found:
                raise StateChangeError(f"remove_item: предмет {name!r} отсутствует в инвентаре")
            if found.qty < qty:
                raise StateChangeError(
                    f"remove_item: недостаточно {name!r} (есть {found.qty}, нужно {qty})")
            found.qty -= qty
            if found.qty == 0:
                state.inventory.remove(found)
            applied.append(f"remove_item {name} x{qty}")
        elif op == "equip_item":
            name = str(ch.get("item", "")).strip()
            found = next((i for i in state.inventory if i.name.lower() == name.lower()), None)
            if not found:
                raise StateChangeError(f"equip_item: предмет {name!r} отсутствует")
            found.equipped = bool(ch.get("value", True))
            applied.append(f"equip_item {name}={found.equipped}")
        elif op == "set_flag":
            key = str(ch.get("key", "")).strip()
            if not key:
                raise StateChangeError("set_flag: нет key")
            state.world.flags[key] = ch.get("value")
            applied.append(f"set_flag {key}={ch.get('value')}")
        elif op == "add_condition":
            cond = str(ch.get("condition", "")).strip().lower()
            if cond and cond not in c.conditions:
                c.conditions.append(cond)
            applied.append(f"add_condition {cond}")
        elif op == "remove_condition":
            cond = str(ch.get("condition", "")).strip().lower()
            if cond in c.conditions:
                c.conditions.remove(cond)
            applied.append(f"remove_condition {cond}")
        elif op == "add_quest":
            q = {"id": uuid.uuid4().hex[:8],
                 "title": str(ch.get("title", "Квест")),
                 "status": "active",
                 "details": str(ch.get("details", ""))}
            state.quest_log.append(q)
            applied.append(f"add_quest {q['title']}")
        elif op == "update_quest":
            qid = ch.get("id")
            q = next((x for x in state.quest_log if x.get("id") == qid), None)
            if not q:
                raise StateChangeError(f"update_quest: квест {qid!r} не найден")
            for k in ("title", "details", "status"):
                if k in ch:
                    q[k] = ch[k]
            applied.append(f"update_quest {qid}")
        elif op == "set_location":
            state.world.location = str(ch.get("value", ""))
            applied.append(f"set_location {state.world.location}")
        elif op == "set_time":
            state.world.time_of_day = str(ch.get("value", ""))
            applied.append(f"set_time {state.world.time_of_day}")
        elif op == "set_weather":
            state.world.weather = str(ch.get("value", ""))
            applied.append(f"set_weather {state.world.weather}")
        elif op == "use_spell_slot":
            lvl = int(ch.get("level", 0))
            left = int(state.world.flags.get(f"slots_l{lvl}", 0))
            if left <= 0:
                raise StateChangeError(f"use_spell_slot: нет ячеек уровня {lvl}")
            state.world.flags[f"slots_l{lvl}"] = left - 1
            applied.append(f"use_spell_slot L{lvl} -> {left - 1}")
        elif op == "death_save":
            if bool(ch.get("success")):
                c.death_saves_success += 1
            else:
                c.death_saves_fail += 1
            applied.append(f"death_save {'success' if ch.get('success') else 'fail'}")
        elif op == "reset_death_saves":
            c.death_saves_success = 0
            c.death_saves_fail = 0
            applied.append("death_saves reset")
        else:
            raise StateChangeError(f"op {op!r} не реализован")
    return applied
