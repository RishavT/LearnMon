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
    assert encounter.drops == 2
    encounter.use(READ, {READ})
    encounter.answer(1)
    assert encounter.solved


def test_retry_can_create_a_duplicate_before_diagnosis():
    encounter = Encounter(CASES[1])
    encounter.use(RETRY, {RETRY})
    assert encounter.duplicates == 2
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
    battle.elapsed = 0.0
    battle.hud = Mock()
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


def test_battle_enters_once_and_exits_its_audio_lifecycle(monkeypatch):
    from tuxemon.state.state import State
    from tuxemon.states.debug_battle import DebugBattleState

    monkeypatch.setattr(State, "resume", lambda self: None)
    monkeypatch.setattr(State, "shutdown", lambda self: None)
    battle = DebugBattleState.__new__(DebugBattleState)
    battle.audio = Mock()
    battle.case = CASES[0]
    battle.entered = False

    battle.resume()
    battle.resume()
    battle.shutdown()

    battle.audio.enter.assert_called_once_with()
    battle.audio.leave.assert_called_once_with()


def test_move_cues_play_once_even_when_frames_skip(monkeypatch):
    from tuxemon.state.state import State
    from tuxemon.states.debug_battle import DebugBattleState

    monkeypatch.setattr(State, "update", lambda self, dt: None)
    battle = DebugBattleState.__new__(DebugBattleState)
    battle.elapsed = 0.0
    battle.hud = Mock()
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


def test_echo_order_opens_with_two_orders_from_one_checkout_attempt():
    encounter = Encounter(CASES[1])
    original, echo = encounter.receipts
    assert (original.order_id, echo.order_id) == (311, 312)
    assert original.request_id == echo.request_id == "ord-74"
    assert encounter.duplicates == 1
    assert encounter.turns == 0


def test_echo_order_comparison_preserves_receipts_and_premature_retry_adds_one():
    encounter = Encounter(CASES[1])
    initial_receipts = encounter.receipts
    encounter.use(INSPECT, {INSPECT, RETRY})
    assert "#311 and #312" in encounter.evidence_notes[0]
    assert encounter.receipts == initial_receipts
    encounter.use(RETRY, {INSPECT, RETRY})
    assert encounter.receipts[:2] == initial_receipts
    assert encounter.receipts[-1].order_id == 313
    assert encounter.receipts[-1].request_id == "ord-75"
    assert encounter.duplicates == 2
    encounter.use(READ, {READ})
    encounter.answer(0)
    assert encounter.solved
    assert len(encounter.receipts) == 3


def test_echo_order_offer_to_submit_a_fresh_order_has_a_recoverable_cost():
    encounter = Encounter(CASES[1])
    encounter.use(INSPECT, {INSPECT})
    encounter.use(READ, {READ})
    encounter.answer(1)
    assert encounter.receipts[-1].order_id == 313
    assert not encounter.solved
    encounter.use(READ, {READ})
    encounter.answer(0)
    assert encounter.solved


def test_repeat_crash_preserves_the_throwing_frame_and_shows_another_exception():
    encounter = Encounter(CASES[0])
    encounter.use(READ, {READ})
    assert encounter.crash_count == 2
    assert "at renderCart (cart.js:42)" in encounter.evidence_notes[0]


def test_legacy_campaign_names_migrate_in_party_and_storage():
    from tuxemon.debugging.names import migrate_problem_names
    from tuxemon.save_system.save_state import NPCState

    def old_capture(case, name):
        return {
            "slug": case.monster,
            "name": name,
            "acquisition": "captured",
            "moves": [{"slug": move} for move in case.reward],
        }

    ordinary = {"slug": "agnite", "name": "Agnite", "acquisition": "captured"}
    state = NPCState(
        game_variables={"debug_trail_active": True, "debug_cases_cleared": 3},
        monsters=[
            {"slug": "dandylion", "name": "Dandylion"},
            old_capture(CASES[0], "Agnite"),
            old_capture(CASES[1], "My Aardart"),
            ordinary,
        ],
        monster_boxes={"reserve": [old_capture(CASES[2], "Ampystoma")]},
    )

    migrated = migrate_problem_names(state)

    assert [monster["name"] for monster in migrated.monsters] == [
        "Dandylion",
        "Crash Loop",
        "My Aardart",
        "Agnite",
    ]
    assert migrated.monster_boxes["reserve"][0]["name"] == "Checkout Blackout"
    assert state.monsters[1]["name"] == "Agnite"
    assert migrate_problem_names(migrated) is migrated


def test_problem_name_migration_skips_normal_saves():
    from tuxemon.debugging.names import migrate_problem_names
    from tuxemon.save_system.save_state import NPCState

    state = NPCState(monsters=[{"slug": "agnite", "name": "Agnite"}])

    assert migrate_problem_names(state) is state


def test_named_problems_keep_their_names_through_monster_save(monkeypatch):
    from tuxemon.database.bootstrap import bootstrap_database
    from tuxemon.database.registry import validator
    from tuxemon.element import Element, ElementTypesHandler
    from tuxemon.monster.monster import Monster
    from tuxemon.shape import Shape
    from tuxemon.taste import Taste

    monkeypatch.setattr(validator, "_instance", None)
    monkeypatch.setattr(Element, "_elements", {})
    monkeypatch.setattr(ElementTypesHandler, "_multiplier_cache", {})
    monkeypatch.setattr(Shape, "_shapes", {})
    monkeypatch.setattr(Taste, "_tastes", {})
    database = bootstrap_database()
    for table in ("element", "shape", "taste", "monster"):
        database.load(table)
    for module in ("element", "shape", "taste", "monster.monster"):
        monkeypatch.setattr(f"tuxemon.{module}.db", database)

    for case in CASES:
        monster = Monster(
            case.monster, database.lookup(case.monster, "monster")
        )
        monster.name = case.title

        restored = Monster.from_save(monster.get_state())
        assert restored.name == case.title
        assert restored.slug == case.monster
