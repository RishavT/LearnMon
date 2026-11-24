# SPDX-License-Identifier: GPL-3.0
"""A turn-based debugging encounter presented inside the Tuxemon RPG."""

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from math import sin

import pygame

from tuxemon.core.effects.capture import register_capture
from tuxemon.debugging.cases import (
    CASES,
    INSPECT,
    LABELS,
    PATCH,
    RETRY,
    Encounter,
)
from tuxemon.debugging.visuals import draw_capture, draw_move
from tuxemon.item.item import Item
from tuxemon.monster.monster import Monster
from tuxemon.monster.sprite import MonsterSpriteHandler, SpriteLoader
from tuxemon.platform.const import buttons
from tuxemon.state.state import State
from tuxemon.technique.technique import Technique
from tuxemon.tools import open_dialog

SIZE = (960, 540)


@dataclass
class BattleEffect:
    name: str
    duration: float
    complete: Callable[[], None]
    elapsed: float = 0.0

    @property
    def progress(self) -> float:
        return min(1.0, self.elapsed / self.duration)


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
        self.effect: BattleEffect | None = None
        self.elapsed = 0.0
        self.disruption_time = 0.0
        self.feedback = ""
        self.feedback_is_warning = False
        self.canvas = pygame.Surface(SIZE)
        self.font = pygame.font.Font(None, 26)
        self.heading = pygame.font.Font(None, 48)
        self.small = pygame.font.Font(None, 21)
        self.target_image = self.sprite(self.target, "front")
        self.party_images = [
            self.sprite(monster, "back") for monster in self.party
        ]

    def play_effect(
        self, name: str, duration: float, complete: Callable[[], None]
    ) -> None:
        self.effect = BattleEffect(name, duration, complete)

    def update(self, dt: float) -> None:
        super().update(dt)
        self.elapsed += dt
        self.disruption_time = max(0.0, self.disruption_time - dt)
        effect = self.effect
        if effect is not None:
            effect.elapsed += dt
            if effect.progress == 1.0:
                self.effect = None
                effect.complete()

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
        if self.effect is not None:
            return None
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
                self.play_effect("capture", 0.85, self.capture)
            elif self.fight.pending:
                self.answer(self.selected)
            else:
                move = self.moves[self.selected]
                if move == PATCH:
                    self.apply_move(move)
                else:
                    duration = 0.64 if move == RETRY else 0.52
                    self.play_effect(
                        move, duration, partial(self.apply_move, move)
                    )
            self.selected = 0
        return None

    def apply_move(self, move: str) -> None:
        before = self.fight.drops
        expected = self.fight.step.move
        self.fight.use(move, set(self.moves))
        self.feedback_is_warning = move != expected
        self.feedback = self.fight.message if self.feedback_is_warning else ""
        if self.fight.drops > before:
            self.disruption_time = 0.32

    def answer(self, index: int) -> None:
        step = self.fight.step
        if step.move == PATCH and index == step.answer:
            self.play_effect(PATCH, 0.5, partial(self.apply_answer, index))
        else:
            self.apply_answer(index)

    def apply_answer(self, index: int) -> None:
        self.feedback_is_warning = index != self.fight.step.answer
        self.fight.answer(index)
        self.feedback = self.fight.message

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

    def evidence_for_panel(self) -> str:
        notes = self.fight.evidence_notes
        evidence = (
            (notes or [self.case.symptom])[-1]
            if self.feedback
            else self.fight.message
        )
        if (
            notes
            and self.case.steps[0].move == INSPECT
            and evidence != notes[0]
        ):
            request = notes[0].splitlines()[0]
            return f"Original request: {request}\n{evidence}"
        return evidence

    def wrapped_lines(self, message: str, width: int) -> list[str]:
        lines = []
        for paragraph in message.splitlines():
            if self.small.size(paragraph)[0] <= width:
                lines.append(paragraph)
                continue
            line = ""
            for word in paragraph.split():
                candidate = f"{line} {word}" if line else word
                if line and self.small.size(candidate)[0] > width:
                    lines.append(line)
                    line = word
                else:
                    line = candidate
            lines.append(line)
        return lines

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
        entry = max(0.0, 1 - self.elapsed / 0.34) ** 2
        ally_rect = ally.get_rect(
            midbottom=(
                223 - round(230 * entry),
                247 + round(2 * sin(self.elapsed * 5)),
            )
        )
        target_rect = opponent.get_rect(
            midbottom=(
                744 + round(240 * entry),
                229 + round(2 * sin(self.elapsed * 5 + 1)),
            )
        )
        if self.disruption_time:
            target_rect.x += round(5 * sin(70 * self.disruption_time))
        if self.effect and self.effect.name == "capture":
            vanish = max(0.05, min(1.0, (1 - self.effect.progress) / 0.34))
            opponent = pygame.transform.scale_by(opponent, vanish)
            target_rect = opponent.get_rect(midbottom=target_rect.midbottom)
        canvas.blit(opponent, target_rect)
        canvas.blit(ally, ally_rect)
        if self.effect:
            if self.effect.name == "capture":
                draw_capture(canvas, self.effect.progress)
            else:
                draw_move(
                    canvas, self.effect.name, self.effect.progress, target_rect
                )
        self.text(self.party[self.active].name, (35, 101))
        self.text(f"Wild {self.target.name}", (614, 100))
        pygame.draw.rect(
            canvas, "#162b2a", (23, 292, 590, 208), border_radius=10
        )
        pygame.draw.rect(
            canvas, "#162b2a", (624, 292, 313, 208), border_radius=10
        )

        caption = "EVIDENCE" if self.fight.turns else "SYMPTOM"
        self.text(caption, (41, 305), self.small, "#9cddb5")
        lines = self.wrapped_lines(self.evidence_for_panel(), 550)
        for index, line in enumerate(lines):
            self.text(line, (41, 331 + index * 19), self.small)
        if self.feedback:
            start = 338 + len(lines) * 19
            for index, line in enumerate(
                self.wrapped_lines(self.feedback, 550)
            ):
                self.text(
                    line,
                    (41, start + index * 19),
                    self.small,
                    "#f8bd80" if self.feedback_is_warning else "#9cddb5",
                )
        if self.fight.drops and not self.fight.solved:
            self.text(self.case.disruption, (35, 262), self.small, "#f8bd80")
        if self.fight.duplicates:
            self.text(
                f"Duplicate orders: {self.fight.duplicates}",
                (681, 258),
                self.small,
                "#f8bd80",
            )

        if self.effect:
            title = (
                "THROWING TUXEBALL"
                if self.effect.name == "capture"
                else LABELS[self.effect.name].upper()
            )
        elif self.fight.pending:
            title = "CHOOSE AN ANSWER"
        elif self.fight.solved:
            title = "CASE SOLVED"
        else:
            title = "CHOOSE A TECHNIQUE"
        self.text(title, (641, 305), self.small, "#9cddb5")
        for index, option in enumerate(
            self.choices if self.effect is None else ()
        ):
            y = 340 + index * 38
            if index == self.selected:
                pygame.draw.rect(
                    canvas, "#426452", (636, y - 5, 289, 36), border_radius=5
                )
            for line_index, line in enumerate(self.wrapped_lines(option, 270)):
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
