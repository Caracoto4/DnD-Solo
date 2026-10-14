"""Prompt Builder: собирает полный запрос к LLM (только EN).

system: роль DM + правила формата ответа
state: JSON с актуальным состоянием (без перевода — числа)
rag_context / campaign_text: текст кампании (V1 — обрезка)
history: последние N сообщений
"""
from __future__ import annotations

import json
from typing import Any

from .system_prompt import SYSTEM_PROMPT

STATE_TEMPLATE = """CURRENT GAME STATE (JSON, authoritative - do not contradict it):
{state}

CAMPAIGN CONTEXT (excerpt from the adventure module, if any):
{campaign}

CONVERSATION HISTORY (oldest to newest):
{history}

PLAYER'S LAST ACTION (already translated to English):
{player_action}

Respond with the strict JSON object only."""

CAMPAIGN_MAX_CHARS = 6000  # V1: тупая обрезка вместо RAG


def build_messages(
    state: dict[str, Any],
    history: list[dict[str, str]],
    player_action_en: str,
    campaign_text: str = "",
    last_result: str | None = None,
) -> list[dict[str, str]]:
    """Собирает messages для koboldcpp. history: [{"role":"user"|"assistant","content":...}] (EN)."""
    state_json = json.dumps(state, ensure_ascii=False, indent=1)
    history_lines = [
        f"{m['role'].upper()}: {m['content']}" for m in history
    ] or ["(empty)"]
    campaign = campaign_text[:CAMPAIGN_MAX_CHARS] if campaign_text else "(none)"

    user_block = STATE_TEMPLATE.format(
        state=state_json,
        campaign=campaign,
        history="\n".join(history_lines),
        player_action=player_action_en,
    )
    if last_result:
        user_block = f"DICE/ENGINE RESULTS:\n{last_result}\n\n" + user_block

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_block},
    ]
