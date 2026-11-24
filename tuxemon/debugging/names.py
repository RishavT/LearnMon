# SPDX-License-Identifier: GPL-3.0
"""Migrate captured problems in pre-naming Debugging Trail saves."""

from collections.abc import Mapping
from typing import Any

from tuxemon.debugging.cases import CASES
from tuxemon.locale.locale import T
from tuxemon.save_system.save_state import NPCState

PROBLEM_NAMES_VERSION = "debug_problem_names_v1"


def migrate_problem_names(state: NPCState) -> NPCState:
    variables = state.game_variables
    cleared = variables.get("debug_cases_cleared", 0)
    if (
        not variables.get("debug_trail_active")
        or variables.get(PROBLEM_NAMES_VERSION)
        or not isinstance(cleared, int)
    ):
        return state

    cases = {case.monster: case for case in CASES[: max(0, cleared)]}

    def name_capture(monster: Mapping[str, Any]) -> Mapping[str, Any]:
        case = cases.get(monster.get("slug", ""))
        name = monster.get("name")
        if case is None or monster.get("acquisition") != "captured":
            return monster
        moves = {move.get("slug") for move in monster.get("moves") or ()}
        if not set(case.reward) <= moves:
            return monster
        if name and name not in (
            T.translate(case.monster),
            case.monster.title(),
        ):
            return monster
        return {**monster, "name": case.title}

    return state.model_copy(
        update={
            "game_variables": {**variables, PROBLEM_NAMES_VERSION: True},
            "monsters": [name_capture(monster) for monster in state.monsters],
            "monster_boxes": {
                key: [name_capture(monster) for monster in monsters]
                for key, monsters in state.monster_boxes.items()
            },
        }
    )
