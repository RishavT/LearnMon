# SPDX-License-Identifier: GPL-3.0
from unittest.mock import Mock

import pytest

from tuxemon.debugging.cases import CASES, INSPECT, READ, RETRY, Encounter


def test_each_case_is_solvable_with_moves_unlocked_so_far():
    known = {READ}
    for case in CASES:
        encounter = Encounter(case)
        for step in case.steps:
            assert step.move in known
            encounter.use(step.move, known)
            if step.options:
                encounter.answer(step.answer)
        assert encounter.solved
        known.update(case.reward)


def test_attempting_an_unknown_move_does_not_advance_the_battle():
    encounter = Encounter(CASES[0])
    encounter.use(READ, set())
    assert encounter.turns == 0
    assert not encounter.pending


def test_wrong_trace_answer_leaves_a_recoverable_case():
    encounter = Encounter(CASES[0])
    encounter.use(READ, {READ})
    encounter.answer(0)
    assert not encounter.solved
    assert encounter.drops == 1
    encounter.use(READ, {READ})
    encounter.answer(1)
    assert encounter.solved


def test_retry_can_create_a_duplicate_before_diagnosis():
    encounter = Encounter(CASES[1])
    encounter.use(RETRY, {RETRY})
    assert encounter.duplicates == 1
    assert encounter.progress == 0


@pytest.mark.parametrize(
    "active",
    [pytest.param(False, id="normal"), pytest.param(True, id="campaign")],
)
def test_party_release_is_only_hidden_during_the_debugging_campaign(
    monkeypatch, active
):
    from tuxemon.states import monster_menu

    monster = Mock(held_item=None)
    menu = Mock()
    menu.get_selected_item.return_value.game_object = monster
    party = Mock(party_size=2, monsters=[monster, Mock(held_item=None)])
    party.owner.bag.items = []
    party.owner.game_variables.get.return_value = active
    show_choices = Mock()
    monkeypatch.setattr(monster_menu, "open_choice_dialog", show_choices)

    monster_menu.MonsterMenuHandler(Mock(), party).open_monster_submenu(menu)

    options = show_choices.call_args.args[1].get_menu()
    assert any(option.key == "release" for option in options) is not active


def test_debugging_battles_use_the_native_combat_screen():
    from tuxemon.states.combat_state import CombatState
    from tuxemon.states.debug_battle import DebugBattleState

    assert issubclass(DebugBattleState, CombatState)


def test_case_notes_keep_observed_clues_without_revealing_future_steps():
    encounter = Encounter(CASES[1])
    assert encounter.evidence_notes == []
    encounter.use(RETRY, {INSPECT, READ, RETRY})
    assert encounter.evidence_notes == []
    encounter.use(INSPECT, {INSPECT})
    assert encounter.evidence_notes == [encounter.case.steps[0].evidence]
    encounter.use(READ, {READ})
    encounter.answer(1)
    assert not encounter.solved
    assert len(encounter.evidence_notes) == 2
    assert "order #311" in encounter.evidence_notes[-1]
