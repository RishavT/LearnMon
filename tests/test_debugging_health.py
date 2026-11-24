# SPDX-License-Identifier: GPL-3.0
import pytest

from tuxemon.debugging.cases import CASES, INSPECT, READ, RETRY, Encounter


def test_unique_evidence_and_correct_diagnosis_damage_wild_once():
    fight = Encounter(CASES[0])
    assert fight.party_hp == fight.wild_hp == fight.max_hp
    assert fight.use(READ, {READ}).value == "Super effective!"
    revealed_hp = fight.wild_hp
    assert 0 < revealed_hp < fight.max_hp
    assert fight.party_hp == fight.max_hp

    assert fight.answer(0).value == "Not effective."
    assert 0 < fight.party_hp < fight.max_hp
    assert fight.wild_hp == revealed_hp
    hurt_hp = fight.party_hp
    assert fight.use(READ, {READ}).value == "Review"
    assert fight.pending
    assert fight.party_hp == hurt_hp
    assert fight.wild_hp == revealed_hp

    assert fight.answer(1).value == "Super effective!"
    assert fight.solved and fight.wild_hp == 0
    assert fight.party_hp == hurt_hp
    assert fight.use(READ, {READ}) is None


def test_wrong_moves_and_retries_exhaust_shared_health_without_solving():
    fight = Encounter(CASES[1])
    assert fight.use(READ, {READ}).value == "Not effective."
    generic_damage = fight.max_hp - fight.party_hp
    assert generic_damage > 0
    starting_hp = fight.party_hp
    assert fight.use(RETRY, {INSPECT, RETRY}).value == "Not effective."
    assert starting_hp - fight.party_hp > generic_damage
    assert fight.receipts[-1].order_id == 313
    fight.use(RETRY, {INSPECT, RETRY})
    fight.use(RETRY, {INSPECT, RETRY})
    assert fight.defeated and not fight.solved
    assert fight.party_hp == 0 and fight.wild_hp == fight.max_hp
    receipts = fight.receipts
    assert fight.use(RETRY, {RETRY}) is None
    assert fight.receipts == receipts


@pytest.mark.parametrize(
    "case", [pytest.param(case, id=case.monster) for case in CASES]
)
def test_only_original_case_completion_can_exhaust_wild_hp(case):
    fight = Encounter(case)
    for step in case.steps:
        assert fight.wild_hp > 0
        outcome = fight.use(step.move, {step.move})
        assert outcome.value == "Super effective!"
        if step.options:
            assert fight.wild_hp > 0
            assert fight.answer(step.answer).value == "Super effective!"
    assert fight.wild_hp == 0 and fight.solved and not fight.defeated
    assert fight.party_hp == fight.max_hp


def test_defeat_retry_and_backpack_share_one_attempt_budget(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import Mock

    from tuxemon.platform.const import buttons
    from tuxemon.state.state import State
    from tuxemon.states.debug_battle import DebugBattleState

    monkeypatch.setattr(State, "update", lambda state, dt: None)
    battle = DebugBattleState.__new__(DebugBattleState)
    battle.case = CASES[1]
    battle.fight = Encounter(battle.case)
    battle.client = Mock()
    battle.audio = Mock()
    battle.backpack = Mock(is_open=False, selected=1)
    battle.hud = Mock()
    battle.effect = None
    battle.active = battle.selected = 0
    battle.elapsed = 0.0
    battle.caught = battle.announcing = False
    battle.party = [
        Mock(moves=Mock(get_moves=lambda: [SimpleNamespace(slug=READ)])),
        Mock(moves=Mock(get_moves=lambda: [SimpleNamespace(slug=RETRY)])),
    ]

    battle.apply_move(READ)
    health_after_mistake = battle.fight.party_hp
    battle.update(1)
    battle.process_backpack(buttons.A)
    battle.update(1)
    assert battle.active == 1
    assert battle.fight.party_hp == health_after_mistake

    for _ in range(3):
        battle.apply_move(RETRY)
        battle.update(1)
    assert battle.fight.defeated
    assert battle.choices == ("Try Again", "Return to City Park")
    battle.audio.defeat.assert_called_once_with()
    battle.process_event(SimpleNamespace(button=buttons.A, pressed=True))

    assert battle.fight.party_hp == battle.fight.wild_hp == battle.fight.max_hp
    assert not battle.fight.defeated and not battle.fight.solved
    assert battle.active == 0 and battle.announcing
    assert len(battle.fight.receipts) == 2
    battle.audio.retry.assert_called_once_with()
    battle.update(2)
    assert not battle.announcing and battle.effect.name == "double_stamp"


def test_repeated_wrong_trace_can_be_defeated_without_spending_read_log():
    fight = Encounter(CASES[0])
    for _ in range(4):
        fight.use(READ, {READ})
        fight.answer(0)
    assert fight.defeated and not fight.solved
    assert fight.party_hp == 0
    assert len(fight.evidence_notes) == 1
    assert fight.message == "That choice does not match the evidence."
