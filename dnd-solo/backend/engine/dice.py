"""Dice Roller: парсер формул D&D (2d6+3, 1d20+5 adv, 4d6dl1, 1d20+5 dis)."""
from __future__ import annotations

import random
import re
from dataclasses import dataclass, field

# 4d6dl1 / 4d6kh3, adv / dis
_FORMULA_RE = re.compile(
    r"""^\s*
    (?P<count>\d*)d(?P<sides>\d+)
    (?:(?P<drop>dl|kh)(?P<drop_n>\d+))?
    (?:(?P<keep>kl|dh)(?P<keep_n>\d+))?
    (?P<mod>[+-]\d+)?
    (?:\s*(?P<mode>adv|dis))?
    \s*$""",
    re.VERBOSE | re.IGNORECASE,
)


@dataclass
class DiceResult:
    formula: str
    total: int
    rolls: list[int] = field(default_factory=list)
    dropped: list[int] = field(default_factory=list)
    modifier: int = 0
    mode: str | None = None  # "adv" | "dis" | None

    def __str__(self) -> str:
        parts = [f"{self.formula} = {self.total}"]
        shown = [r for r in self.rolls if r not in self.dropped]
        parts.append(f"(rolls: {shown}, mod: {self.modifier:+d})")
        if self.mode:
            parts.append(f"[{self.mode}]")
        return " ".join(parts)


class DiceError(ValueError):
    pass


def roll(formula: str) -> DiceResult:
    """Бросает кубики по формуле. Броски случайны, логируются вызывающей стороной."""
    m = _FORMULA_RE.match(formula.replace(" ", ""))
    if not m:
        raise DiceError(f"Непонятная формула броска: {formula!r}")

    count = int(m.group("count")) if m.group("count") else 1
    sides = int(m.group("sides"))
    if count < 1 or count > 100 or sides < 2 or sides > 1000:
        raise DiceError(f"Недопустимая формула: {formula!r}")
    modifier = int(m.group("mod")) if m.group("mod") else 0
    mode = m.group("mode").lower() if m.group("mode") else None

    rolls: list[int] = []
    dropped: list[int] = []

    if mode in ("adv", "dis") and count == 1 and sides == 20:
        # advantage: два броска d20, берём максимум; dis — минимум
        a, b = random.randint(1, 20), random.randint(1, 20)
        keep = max(a, b) if mode == "adv" else min(a, b)
        drop = b if keep == a else a
        rolls = [a, b]
        dropped = [drop]
        total = keep + modifier
        return DiceResult(formula, total, rolls, dropped, modifier, mode)

    rolls = [random.randint(1, sides) for _ in range(count)]

    if m.group("drop"):
        n = int(m.group("drop_n"))
        if m.group("drop").lower() == "dl":  # drop lowest n
            dropped = sorted(rolls)[:n]
        else:  # kh = keep highest -> drop the rest
            dropped = sorted(rolls)[:-n] if n < count else []
    elif m.group("keep"):
        n = int(m.group("keep_n"))
        if m.group("keep").lower() == "kh":
            dropped = sorted(rolls)[:-n] if n < count else []
        else:  # kl = keep lowest
            dropped = sorted(rolls)[n:]

    total = sum(r for r in rolls if r not in dropped) + modifier
    return DiceResult(formula, total, rolls, dropped, modifier, mode)


def modifier_for(score: int) -> int:
    """Модификатор по характеристике (ability score) — чистая математика 5e."""
    return (score - 10) // 2
