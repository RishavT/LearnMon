# SPDX-License-Identifier: GPL-3.0
"""A turn-based debugging encounter presented inside the Tuxemon RPG."""

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from math import pi, sin

import pygame

from tuxemon.core.effects.capture import register_capture
from tuxemon.debugging.audio import CUES, BattleAudio
from tuxemon.debugging.backpack import BattleBackpack, companion_identity
from tuxemon.debugging.cases import (
    CASES,
    COUNTER_LABELS,
    DOUBLE_STAMP,
    INSPECT,
    LABELS,
    PATCH,
    READ,
    REPEAT_CRASH,
    RETRY,
    STACK_SURGE,
    Encounter,
)
from tuxemon.debugging.visuals import (
    draw_capture,
    draw_crash_echo,
    draw_fault_stack,
    draw_move,
    draw_read_log,
    draw_receipts,
    draw_stack_surge,
    read_log_offsets,
)
from tuxemon.graphics import load_image
from tuxemon.item.item import Item
from tuxemon.monster.monster import Monster
from tuxemon.monster.sprite import MonsterSpriteHandler, SpriteLoader
from tuxemon.platform.const import buttons
from tuxemon.state.state import State
from tuxemon.technique.technique import Technique

SIZE = (960, 540)
ECHO_WINDUP = 0.34
MOVE_DURATION = {READ: 0.90, INSPECT: 0.56, RETRY: 0.66, PATCH: 0.55}
COUNTER_DURATION = {REPEAT_CRASH: 0.43, DOUBLE_STAMP: 0.72, STACK_SURGE: 0.48}


@dataclass
class BattleEffect:
    name: str
    duration: float
    complete: Callable[[], None] | None
    elapsed: float = 0.0
    cues: tuple[tuple[float, str], ...] = ()

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
        self.target.name = self.case.title
        self.target.wild = True
        self.session.player.tuxepedia.register_seen(self.target.slug)
        self.party = list(session.player.monsters)
        self.active = 0
        self.selected = 0
        self.caught = False
        self.audio = BattleAudio(client.current_music, client.sound_manager)
        self.entered = False
        self.effect: BattleEffect | None = None
        self.elapsed = 0.0
        self.trace_revealed_at: float | None = None
        self.feedback = ""
        self.feedback_is_warning = False
        self.canvas = pygame.Surface(SIZE)
        grass = load_image("gfx/ui/combat/grass_background.png")
        scaled = pygame.transform.scale_by(grass, SIZE[0] / grass.get_width())
        self.backdrop = pygame.Surface((960, 202))
        self.backdrop.blit(scaled, (0, -85))
        shade = pygame.Surface(self.backdrop.get_size(), pygame.SRCALPHA)
        shade.fill((18, 35, 36, 155))
        self.backdrop.blit(shade, (0, 0))
        self.font = pygame.font.Font(None, 26)
        self.heading = pygame.font.Font(None, 48)
        self.small = pygame.font.Font(None, 21)
        self.tiny = pygame.font.Font(None, 17)
        self.target_image = self.sprite(self.target, "front")
        self.party_images = [
            self.sprite(monster, "back") for monster in self.party
        ]
        self.backpack = BattleBackpack(
            self.party,
            [self.sprite(monster, "front") for monster in self.party],
            case=self.case,
        )

    def resume(self) -> None:
        super().resume()
        if self.entered:
            return
        self.entered = True
        self.audio.enter()
        if self.case.opening_receipts:
            self.play_counter(DOUBLE_STAMP)

    def shutdown(self) -> None:
        self.audio.leave()
        super().shutdown()

    def play_counter(self, counter: str) -> None:
        windup = ECHO_WINDUP if counter == DOUBLE_STAMP else 0.0
        self.play_effect(
            counter,
            COUNTER_DURATION[counter] + windup,
            cues=tuple(
                (time + windup, sound) for time, sound in CUES[counter]
            ),
        )

    def play_effect(
        self,
        name: str,
        duration: float,
        complete: Callable[[], None] | None = None,
        *,
        cues: tuple[tuple[float, str], ...] = (),
    ) -> None:
        self.effect = BattleEffect(name, duration, complete, cues=cues)

    def update(self, dt: float) -> None:
        super().update(dt)
        self.elapsed += dt
        effect = self.effect
        if effect is not None:
            previous = effect.elapsed
            effect.elapsed += dt
            for time, sound in effect.cues:
                if previous < time <= effect.elapsed:
                    self.client.sound_manager.play(sound)
            if effect.progress == 1.0:
                self.effect = None
                if effect.complete is not None:
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
        if self.caught:
            return ("Return to City Park",)
        if self.fight.pending:
            return self.fight.step.options
        if self.fight.solved:
            return ("Throw Tuxeball",)
        return tuple(self.case.move_label(move) for move in self.moves)

    def process_event(self, event):
        if not event.pressed:
            return event
        if self.effect is not None:
            return None
        if self.backpack.is_open:
            self.process_backpack(event.button)
            return None
        if event.button in (buttons.UP, buttons.DOWN):
            delta = -1 if event.button == buttons.UP else 1
            selected = (self.selected + delta) % len(self.choices)
            if selected != self.selected:
                self.client.sound_manager.play("sound_menu_select")
            self.selected = selected
        elif event.button in (buttons.LEFT, buttons.RIGHT, buttons.X):
            if not self.fight.pending and not self.fight.solved:
                self.backpack.open(self.active)
                self.client.sound_manager.play("sound_menu_select")
        elif event.button == buttons.A:
            if self.caught:
                self.client.pop_state(self)
                return None
            if self.fight.solved:
                self.play_effect(
                    "capture", 1.15, self.capture, cues=CUES["capture"]
                )
            elif self.fight.pending:
                self.answer(self.selected)
            else:
                move = self.moves[self.selected]
                self.play_effect(
                    move,
                    MOVE_DURATION[move],
                    partial(self.apply_move, move),
                    cues=CUES[move],
                )
            self.selected = 0
        return None

    def process_backpack(self, button: int) -> None:
        if button in (buttons.B, buttons.BACK, buttons.X):
            self.backpack.close()
        elif button in (buttons.UP, buttons.DOWN, buttons.LEFT, buttons.RIGHT):
            delta = -1 if button in (buttons.UP, buttons.LEFT) else 1
            previous = self.backpack.selected
            self.backpack.select(delta)
            if self.backpack.selected != previous:
                self.client.sound_manager.play("sound_menu_select")
        elif button == buttons.A:
            chosen = self.backpack.selected
            self.backpack.close()
            if chosen != self.active:
                self.active = chosen
                self.selected = 0
                self.play_effect("switch", 0.30, cues=CUES["switch"])

    def apply_move(self, move: str) -> None:
        before = self.fight.drops
        receipts = len(self.fight.receipts)
        expected = self.fight.step.move
        self.fight.use(move, set(self.moves))
        self.feedback_is_warning = move != expected
        self.feedback = self.fight.message if self.feedback_is_warning else ""
        if not self.feedback_is_warning and move in (READ, INSPECT):
            self.trace_revealed_at = self.elapsed
        if len(self.fight.receipts) > receipts:
            self.play_retry_receipt()
        elif self.fight.drops > before and self.case.counter != DOUBLE_STAMP:
            self.play_counter(self.case.counter)

    def answer(self, index: int) -> None:
        step = self.fight.step
        if step.move == PATCH and index == step.answer:
            self.play_effect(
                PATCH,
                MOVE_DURATION[PATCH],
                partial(self.apply_answer, index),
                cues=CUES[PATCH],
            )
        else:
            self.client.sound_manager.play(
                "sound_confirm" if index == step.answer else "sfx_crumble2"
            )
            self.apply_answer(index)

    def apply_answer(self, index: int) -> None:
        receipts = len(self.fight.receipts)
        self.feedback_is_warning = index != self.fight.step.answer
        self.fight.answer(index)
        self.feedback = self.fight.message
        if len(self.fight.receipts) > receipts:
            self.play_retry_receipt()

    def play_retry_receipt(self) -> None:
        self.play_effect(
            "retry_receipt", 0.42, cues=((0.22, CUES[DOUBLE_STAMP][0][1]),)
        )

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
        self.caught = True
        self.audio.reward()
        self.selected = 0
        reward = " and ".join(LABELS[move] for move in self.case.reward)
        self.feedback = (
            f"{self.target.name} joined your party and knows {reward}."
        )
        if self.index + 1 == len(CASES):
            self.feedback += (
                "\nDebugging Trail complete. All three cases solved!"
            )
        self.feedback_is_warning = False

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
        canvas.blit(self.backdrop, (0, 85))
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
        self.text(self.case.objective, (28, 39), self.heading)
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
        if self.effect and self.effect.name == READ:
            ally_offset, target_offset = read_log_offsets(self.effect.progress)
            ally_rect.x += ally_offset
            target_rect.x += target_offset
        if self.effect:
            progress = self.effect.progress
            if self.effect.name == REPEAT_CRASH:
                target_rect.x -= round(17 * abs(sin(2 * pi * progress)))
            elif self.effect.name == DOUBLE_STAMP:
                for hit, _ in self.effect.cues:
                    lead = hit - self.effect.elapsed
                    target_rect.y -= round(
                        23 * sin(pi * min(1.0, max(0.0, lead / 0.17)))
                    )
            elif self.effect.name == STACK_SURGE:
                target_rect.y -= round(19 * sin(pi * progress))
            elif self.effect.name == "switch":
                ally_rect.x -= round(131 * (1 - progress) ** 2)
        if self.effect and self.effect.name == "capture":
            vanish = max(0.05, min(1.0, (1 - self.effect.progress) / 0.34))
            opponent = pygame.transform.scale_by(opponent, vanish)
            target_rect = opponent.get_rect(midbottom=target_rect.midbottom)
        if not self.caught:
            canvas.blit(opponent, target_rect)
        canvas.blit(ally, ally_rect)
        self.draw_arena_effects(ally_rect, target_rect)
        ally_monster = self.party[self.active]
        self.text(ally_monster.name, (35, 101))
        self.text(
            companion_identity(ally_monster.slug).role,
            (35, 126),
            self.small,
            "#9cddb5",
        )
        name = f"{'Caught' if self.caught else 'Wild'} {self.target.name}"
        role = companion_identity(self.target.slug).role
        self.text(name, (932 - self.font.size(name)[0], 17))
        self.text(
            role,
            (932 - self.small.size(role)[0], 44),
            self.small,
            "#9cddb5",
        )
        pygame.draw.rect(
            canvas, "#162b2a", (23, 292, 590, 208), border_radius=10
        )
        pygame.draw.rect(
            canvas, "#162b2a", (624, 292, 313, 208), border_radius=10
        )

        if self.trace_revealed_at is not None:
            reveal = max(
                0.0, 1.0 - (self.elapsed - self.trace_revealed_at) / 0.38
            )
            if reveal:
                color = pygame.Color("#162b2a").lerp("#9cddb5", reveal)
                pygame.draw.rect(
                    canvas, color, (23, 292, 590, 208), 3, border_radius=10
                )

        caption = "EVIDENCE" if self.fight.turns else "SYMPTOM"
        self.text(caption, (41, 305), self.small, "#9cddb5")
        if self.fight.crash_count > 1:
            self.text(
                f"TypeError ×{self.fight.crash_count}",
                (454, 305),
                self.small,
                "#f8bd80",
            )
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
        if self.effect:
            title = self.effect_title()
        elif self.fight.pending:
            title = "CHOOSE AN ANSWER"
        elif self.caught:
            title = "TUXEMON CAUGHT"
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
        if self.caught:
            controls = "Enter  Return to City Park"
        elif self.effect:
            controls = ""
        elif self.fight.solved:
            controls = "Enter  Throw Tuxeball"
        elif self.fight.pending:
            controls = "Up / Down  Select     Enter  Answer"
        else:
            controls = "Up / Down  Select     Enter  Confirm     Left / Right  Backpack"
        self.text(controls, (28, 511), self.small)
        self.text(
            f"Turn {self.fight.turns}   |   Disruptions {self.fight.drops}",
            (740, 511),
            self.small,
        )
        if self.backpack.is_open:
            self.backpack.draw(canvas, self.font, self.small)
        pygame.transform.scale(canvas, surface.get_size(), surface)

    def effect_title(self) -> str:
        assert self.effect is not None
        name = self.effect.name
        if name in LABELS:
            return self.case.move_label(name).upper()
        if name in COUNTER_LABELS:
            return COUNTER_LABELS[name].upper()
        return {
            "capture": "THROWING TUXEBALL",
            "switch": f"GO, {self.party[self.active].name.upper()}!",
            "retry_receipt": "ANOTHER ORDER",
        }[name]

    def draw_arena_effects(
        self, ally: pygame.Rect, target: pygame.Rect
    ) -> None:
        effect = self.effect
        if self.case.opening_receipts:
            stamp_time = (
                effect.elapsed - ECHO_WINDUP
                if effect and effect.name == DOUBLE_STAMP
                else None
            )
            retry_progress = (
                effect.progress
                if effect and effect.name == "retry_receipt"
                else None
            )
            draw_receipts(
                self.canvas,
                self.fight.receipts,
                self.tiny,
                comparison=bool(self.fight.revealed),
                stamp_time=stamp_time,
                retry_progress=retry_progress,
            )
        elif self.case.counter == STACK_SURGE and not self.fight.solved:
            progress = (
                effect.progress if effect and effect.name == STACK_SURGE else 1
            )
            draw_stack_surge(
                self.canvas, progress, self.fight.drops, self.small
            )
        elif self.fight.crash_count > 1:
            draw_fault_stack(self.canvas, self.fight.crash_count, self.tiny)
        if effect is None:
            return
        if effect.name == "capture":
            draw_capture(self.canvas, effect.progress)
        elif effect.name == READ:
            draw_read_log(self.canvas, effect.progress, ally, target)
        elif effect.name == REPEAT_CRASH:
            draw_crash_echo(self.canvas, effect.progress, target)
        elif effect.name not in (DOUBLE_STAMP, STACK_SURGE, "retry_receipt"):
            draw_move(
                self.canvas,
                effect.name,
                effect.progress,
                self.small,
                compare=bool(self.case.opening_receipts),
                patched=self.fight.pending,
                patch_visible=effect.name == PATCH
                and self.fight.step.move == PATCH,
            )
