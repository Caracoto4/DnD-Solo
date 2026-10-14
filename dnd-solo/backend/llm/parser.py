"""Парсер и валидатор строгого JSON-протокола ответа LLM (ТЗ 5.6).

Невалидный JSON -> raise ProtocolError, вызывающая сторона делает retry (max 2).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

_CHECK_TYPES = {"skill", "attack", "save", "initiative", "death_save"}


class ProtocolError(ValueError):
    pass


@dataclass
class DMResponse:
    narrative: str
    requested_checks: list[dict[str, Any]] = field(default_factory=list)
    state_changes: list[dict[str, Any]] = field(default_factory=list)
    suggested_actions: list[str] = field(default_factory=list)


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _extract_json(text: str) -> str:
    """Достаёт JSON: сначала пытаемся как есть, потом из ```json блока,
    потом первый сбалансированный {...}."""
    text = text.strip()
    if text.startswith("{"):
        return text
    m = _FENCE_RE.search(text)
    if m:
        return m.group(1)
    start = text.find("{")
    if start == -1:
        raise ProtocolError("В ответе нет JSON-объекта")
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise ProtocolError("Несбалансированный JSON в ответе")


def parse_dm_response(raw: str) -> DMResponse:
    """Парсит и валидирует ответ LLM. Бросает ProtocolError при проблемах."""
    try:
        data = json.loads(_extract_json(raw))
    except json.JSONDecodeError as e:
        raise ProtocolError(f"Невалидный JSON: {e}") from e

    if not isinstance(data, dict):
        raise ProtocolError("Ответ — не JSON-объект")

    narrative = data.get("narrative")
    if not isinstance(narrative, str) or not narrative.strip():
        raise ProtocolError("Поле narrative отсутствует или пустое")

    checks = data.get("requested_checks", []) or []
    if not isinstance(checks, list):
        raise ProtocolError("requested_checks должен быть массивом")
    for ch in checks:
        if not isinstance(ch, dict):
            raise ProtocolError("requested_checks[i] должен быть объектом")
        if ch.get("type") not in _CHECK_TYPES:
            raise ProtocolError(f"Недопустимый type проверки: {ch.get('type')!r}")
        if not isinstance(ch.get("dc"), (int, float)):
            raise ProtocolError("У проверки нет dc")

    changes = data.get("state_changes", []) or []
    if not isinstance(changes, list):
        raise ProtocolError("state_changes должен быть массивом")
    for ch in changes:
        if not isinstance(ch, dict) or "op" not in ch:
            raise ProtocolError(f"state_changes[i]: нет op — {ch!r}")

    actions = data.get("suggested_actions", []) or []
    if not isinstance(actions, list) or not all(isinstance(a, str) for a in actions):
        raise ProtocolError("suggested_actions должен быть массивом строк")

    return DMResponse(
        narrative=narrative.strip(),
        requested_checks=checks,
        state_changes=changes,
        suggested_actions=actions[:6],
    )
