# SPDX-License-Identifier: GPL-3.0
"""A turn-based debugging encounter presented inside the Tuxemon RPG."""

from textwrap import wrap

import pygame

from tuxemon.core.effects.capture import register_capture
from tuxemon.debugging.cases import CASES, LABELS, Encounter
from tuxemon.item.item import Item
from tuxemon.monster.monster import Monster
from tuxemon.monster.sprite import MonsterSpriteHandler, SpriteLoader
from tuxemon.platform.const import buttons
from tuxemon.state.state import State
from tuxemon.technique.technique import Technique
from tuxemon.tools import open_dialog

SIZE = (960, 540)


class DebugBattleState(State):
    name = "DebugBattleState"

    def __init__(self, client, session, index):
        super().__init__(client)
        self.session = session
        self.index = index
        self.case = CASES[index]
        self.fight = Encounter(self.case, message=self.case.symptom)
        self.target = Monster.spawn_base(self.case.monster, 5 + index)
        self.target.wild = True
        self.session.player.tuxepedia.register_seen(self.target.slug)
        self.party = list(session.player.monsters)
        self.active = 0
        self.selected = 0
        self.canvas = pygame.Surface(SIZE)
        self.font = pygame.font.Font(None, 26)
        self.heading = pygame.font.Font(None, 48)
        self.small = pygame.font.Font(None, 21)
        self.target_image = self.sprite(self.target, "front")
        self.party_images = [
            self.sprite(monster, "back") for monster in self.party
        ]

    @staticmethod
    def sprite(monster, side):
        config = monster.sprite_config
        handler = MonsterSpriteHandler(
            config.slug,
            SpriteLoader().resolve_path(config.sheet_path),
            config.front_rect,
            config.back_rect,
            config.menu1_rect,
            config.menu2_rect,
        )
        return handler.get_sprite(side, scale=2).image

    @property
    def moves(self):
        return [
            move.slug
            for move in self.party[self.active].moves.get_moves()
            if move.slug in LABELS
        ]

    @property
    def choices(self):
        if self.fight.pending:
            return self.fight.step.options
        if self.fight.solved:
            return ("Throw Tuxeball",)
        return tuple(LABELS[move] for move in self.moves)

    def process_event(self, event):
        if not event.pressed:
            return event
        if event.button in (buttons.UP, buttons.DOWN):
            delta = -1 if event.button == buttons.UP else 1
            self.selected = (self.selected + delta) % len(self.choices)
        elif event.button in (buttons.LEFT, buttons.RIGHT):
            if not self.fight.pending and not self.fight.solved:
                delta = -1 if event.button == buttons.LEFT else 1
                self.active = (self.active + delta) % len(self.party)
                self.selected = 0
        elif event.button == buttons.A:
            if self.fight.solved:
                self.capture()
            elif self.fight.pending:
                self.fight.answer(self.selected)
            else:
                self.fight.use(self.moves[self.selected], set(self.moves))
            self.selected = 0
        return None

    def capture(self):
        # Case resolution guarantees a capture, so a random roll cannot gate
        # the next case's required moves.
        self.target.moves.replace_all_moves(
            [Technique.create(move) for move in self.case.reward]
        )
        register_capture(self.session, Item.create("tuxeball"), self.target)
        self.session.player.game_variables.set(
            "debug_cases_cleared", self.index + 1
        )
        self.client.pop_state(self)
        reward = " and ".join(LABELS[move] for move in self.case.reward)
        text = f"{self.target.name} joined your party and knows {reward}."
        if self.index + 1 < len(CASES):
            followup = (
                "Take another step in the grass to find the next encounter."
            )
        else:
            followup = "Debugging Trail complete. All three cases solved!"
        open_dialog(self.client, [text, followup], dialog_speed="max")

    def text(self, value, point, font=None, color="#f1f3dd"):
        self.canvas.blit((font or self.font).render(value, True, color), point)

    def draw(self, surface):
        canvas = self.canvas
        canvas.fill("#122324")
        pygame.draw.rect(canvas, "#243b35", (0, 85, 960, 202))
        pygame.draw.ellipse(canvas, "#405d49", (80, 217, 286, 57))
        pygame.draw.ellipse(canvas, "#405d49", (611, 198, 265, 55))
        pygame.draw.ellipse(canvas, "#6f875b", (92, 220, 262, 38), 2)
        pygame.draw.ellipse(canvas, "#6f875b", (621, 200, 245, 36), 2)

        self.text(
            f"DEBUGGING TRAIL  /  CASE {self.index + 1} OF {len(CASES)}",
            (28, 16),
            self.small,
            "#9cddb5",
        )
        self.text(self.case.title, (28, 39), self.heading)
        self.text(self.case.objective, (446, 53))
        opponent = self.target_image
        ally = self.party_images[self.active]
        canvas.blit(opponent, opponent.get_rect(midbottom=(744, 229)))
        canvas.blit(ally, ally.get_rect(midbottom=(223, 247)))
        self.text(self.party[self.active].name, (35, 101))
        self.text(f"Wild {self.target.name}", (614, 100))
        pygame.draw.rect(
            canvas, "#162b2a", (23, 299, 590, 196), border_radius=10
        )
        pygame.draw.rect(
            canvas, "#162b2a", (624, 299, 313, 196), border_radius=10
        )

        caption = "EVIDENCE" if self.fight.turns else "SYMPTOM"
        self.text(caption, (41, 314), self.small, "#9cddb5")
        lines = [
            part
            for line in self.fight.message.splitlines()
            for part in wrap(line, 60)
        ]
        for index, line in enumerate(lines):
            self.text(line, (41, 339 + index * 22), self.small)
        if self.fight.drops and not self.fight.solved:
            self.text(
                f"Wild move: {self.case.disruption}",
                (41, 468),
                self.small,
                "#f8bd80",
            )
        if self.fight.duplicates:
            self.text(
                f"Duplicate orders: {self.fight.duplicates}",
                (681, 258),
                self.small,
                "#f8bd80",
            )

        if self.fight.pending:
            title = "CHOOSE AN ANSWER"
        elif self.fight.solved:
            title = "CASE SOLVED"
        else:
            title = "CHOOSE A TECHNIQUE"
        self.text(title, (641, 315), self.small, "#9cddb5")
        for index, option in enumerate(self.choices):
            y = 340 + index * 38
            if index == self.selected:
                pygame.draw.rect(
                    canvas, "#426452", (636, y - 5, 289, 36), border_radius=5
                )
            for line_index, line in enumerate(wrap(option, 33)):
                self.text(line, (645, y + line_index * 15), self.small)
        self.text(
            "Up / Down  Select     Enter  Confirm     Left / Right  Switch Tuxemon",
            (28, 511),
            self.small,
        )
        self.text(
            f"Turn {self.fight.turns}   |   Disruptions {self.fight.drops}",
            (740, 511),
            self.small,
        )
        pygame.transform.scale(canvas, surface.get_size(), surface)
