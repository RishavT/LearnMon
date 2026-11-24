# SPDX-License-Identifier: GPL-3.0
from unittest.mock import Mock

import pytest

from tuxemon.debugging.cases import CASES, READ, RETRY, Encounter


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
