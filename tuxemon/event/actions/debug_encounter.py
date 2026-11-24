# SPDX-License-Identifier: GPL-3.0
from dataclasses import dataclass

from tuxemon.debugging.cases import CASES
from tuxemon.event.eventaction import EventAction
from tuxemon.session import Session


@dataclass
class DebugEncounterAction(EventAction):
    """Enter the next debugging case when walking through City Park grass."""

    name = "debug_encounter"

    def start(self, session: Session) -> None:
        index = session.player.game_variables.get("debug_cases_cleared", 0)
        if index < len(CASES):
            session.player.cancel_movement()
            session.client.push_state(
                "DebugBattleState", session=session, index=index
            )
        self.stop()
