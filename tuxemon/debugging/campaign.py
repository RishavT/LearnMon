# SPDX-License-Identifier: GPL-3.0
"""Boot the debugging campaign inside the normal Tuxemon world client."""

import pygame

from tuxemon.client import LocalPygameClient
from tuxemon.database.runtime import db
from tuxemon.debugging.cases import READ
from tuxemon.debugging.names import PROBLEM_NAMES_VERSION
from tuxemon.launcher import GameLauncher
from tuxemon.monster.monster import Monster
from tuxemon.session import local_session
from tuxemon.technique.technique import Technique
from tuxemon.tools import open_dialog


def launch(config, context) -> None:
    client = LocalPygameClient.create(config, context, enable_network=False)
    local_session.set_client(client)
    pygame.display.set_caption("Tuxemon | Debugging Trail")

    meta = db.mod_metadata.get_mod_metadata("tuxemon").model_copy(
        update={
            "starting_map": "debug_citypark.tmx",
            "starting_position": (18, 23),
        }
    )
    GameLauncher(client).launch(session=local_session, meta=meta)
    client.event_engine.execute_action("play_music", ["music_city_park"])
    player = local_session.player
    player.game_variables.set("debug_trail_active", True)
    player.game_variables.set(PROBLEM_NAMES_VERSION, True)
    starter = Monster.spawn_base("dandylion", 5)
    starter.moves.replace_all_moves([Technique.create(READ)])
    player.party.add_monster(starter, 0)
    open_dialog(
        client,
        [
            "Dandylion knows Read Log. Walk right into the grass to try it.",
        ],
        dialog_speed="max",
    )
    try:
        client.main()
    finally:
        pygame.quit()
