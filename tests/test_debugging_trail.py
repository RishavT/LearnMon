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


def test_move_result_is_revealed_once_when_its_effect_finishes(monkeypatch):
    from tuxemon.state.state import State
    from tuxemon.states.debug_battle import DebugBattleState

    monkeypatch.setattr(State, "update", lambda self, dt: None)
    battle = DebugBattleState.__new__(DebugBattleState)
    battle.elapsed = battle.disruption_time = 0.0
    reveal = Mock()
    battle.play_effect(READ, 0.5, reveal)

    battle.update(0.49)
    reveal.assert_not_called()
    battle.update(0.02)
    battle.update(0.5)
    reveal.assert_called_once_with()


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


def test_evidence_panel_keeps_request_and_corresponding_log_together():
    from tuxemon.states.debug_battle import DebugBattleState

    battle = DebugBattleState.__new__(DebugBattleState)
    battle.case = CASES[2]
    battle.fight = Encounter(battle.case)
    battle.feedback = ""
    battle.fight.use(INSPECT, {INSPECT})
    battle.fight.use(READ, {READ})
    lines = battle.evidence_for_panel().splitlines()

    assert lines[0].startswith("Original request: POST /checkout returned 500")
    assert "cart-19" in lines[0] and "cart-19" in lines[1]
    assert "coupon was null" in lines[2]
    assert "returned 201" not in battle.evidence_for_panel()


def test_battle_music_starts_once_and_restores_the_park_mix(monkeypatch):
    from tuxemon.state.state import State
    from tuxemon.states.debug_battle import DebugBattleState

    monkeypatch.setattr(State, "resume", lambda self: None)
    monkeypatch.setattr(State, "shutdown", lambda self: None)
    battle = DebugBattleState.__new__(DebugBattleState)
    battle.client = Mock()
    battle.park_mix = None
    music = battle.client.current_music
    music.current_song = "music_city_park"
    music.get_volume.return_value = 0.27
    music.muted = False

    battle.resume()
    battle.resume()
    battle.shutdown()

    assert music.play.call_args_list[0].args == ("music_battle_loop_slow",)
    assert len(music.play.call_args_list) == 2
    music.play.assert_called_with("music_city_park", volume=0.27, fade_ms=300)


def test_move_cues_play_once_even_when_frames_skip(monkeypatch):
    from tuxemon.state.state import State
    from tuxemon.states.debug_battle import DebugBattleState

    monkeypatch.setattr(State, "update", lambda self, dt: None)
    battle = DebugBattleState.__new__(DebugBattleState)
    battle.elapsed = battle.disruption_time = 0.0
    battle.client = Mock()
    completed = Mock()
    battle.play_effect(
        READ, 0.9, completed, cues=((0.2, "sfx_pulse"), (0.55, "sfx_shine"))
    )

    battle.update(0.15)
    battle.update(0.48)
    battle.update(0.4)

    assert [
        cue.args[0] for cue in battle.client.sound_manager.play.call_args_list
    ] == ["sfx_pulse", "sfx_shine"]
    completed.assert_called_once()
