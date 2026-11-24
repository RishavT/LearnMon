# SPDX-License-Identifier: GPL-3.0
from dataclasses import dataclass

from tuxemon.combat.combat_context import BattleMode, CombatContext, CombatType
from tuxemon.debugging.cases import CASES
from tuxemon.entity.npc import NPC
from tuxemon.event.eventaction import EventAction
from tuxemon.monster.monster import Monster
from tuxemon.session import Session


@dataclass
class DebugEncounterAction(EventAction):
    """Enter the next native debugging battle in City Park."""

    name = "debug_encounter"

    def start(self, session: Session) -> None:
        player = session.player
        index = player.game_variables.get("debug_cases_cleared", 0)
        if index >= len(CASES):
            self.stop()
            return

        client = session.client
        client.environment_manager.load_environment("grass")
        opponent = NPC.create(session, "wild_encounter")
        monster = Monster.spawn_base(CASES[index].monster, 5 + index)
        monster.wild = True
        opponent.party.insert_monster_to_party(monster)
        context = CombatContext(
            session=session,
            teams=[player, opponent],
            combat_type=CombatType.MONSTER,
            battle_mode=BattleMode.SINGLE,
        )
        player.cancel_movement()
        client.queue_state("DebugBattleState", context=context, index=index)
        client.push_state("FlashTransition", max_flash_count=1)
        environment = client.environment_manager.get_active_environment()
        if environment is not None and (
            track := environment.get_battle_music().battle.music
        ):
            client.current_music.play(track)
        self.stop()
