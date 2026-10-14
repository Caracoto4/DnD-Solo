"""Smoke-тест движка: dice + state (без LLM). Запуск: python -m backend.tests.test_engine"""
import sys

from backend.engine.dice import roll, modifier_for, DiceError
from backend.engine.state import GameState, Character, apply_state_changes, StateChangeError


def main() -> int:
    # Dice
    r = roll("2d6+3")
    assert r.total == sum(r.rolls) + 3, r
    r = roll("4d6dl1")
    assert len(r.dropped) == 1 and r.total == sum(x for x in r.rolls if x not in r.dropped), r
    r = roll("1d20+5 adv")
    assert r.mode == "adv" and r.total == max(r.rolls) + 5, r
    r = roll("1d20+5 dis")
    assert r.mode == "dis" and r.total == min(r.rolls) + 5, r
    try:
        roll("abc")
        raise AssertionError("DiceError не выброшен")
    except DiceError:
        pass
    assert modifier_for(16) == 3 and modifier_for(8) == -1

    # State
    state = GameState(character=Character(name="Тест", hp_max=20, hp_current=20))
    applied = apply_state_changes(state, [
        {"op": "damage", "target": "player", "amount": "2d6", "type": "fire"},
        {"op": "add_item", "target": "player", "item": "Rope", "qty": 1},
        {"op": "add_item", "target": "player", "item": "rope", "qty": 2},
        {"op": "set_flag", "key": "found_door", "value": True},
        {"op": "add_quest", "title": "Test quest"},
    ])
    assert len(applied) == 5, applied
    assert state.inventory[0].name == "Rope" and state.inventory[0].qty == 3
    assert state.world.flags["found_door"] is True
    assert len(state.quest_log) == 1

    # удаление несуществующего предмета — отказ
    try:
        apply_state_changes(state, [{"op": "remove_item", "item": "Sword"}])
        raise AssertionError("StateChangeError не выброшен")
    except StateChangeError:
        pass

    # сериализация
    d = state.to_dict()
    state2 = GameState.from_dict(d)
    assert state2.character.hp_current == state.character.hp_current
    assert state2.inventory[0].qty == 3

    print("OK: dice + state smoke test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
