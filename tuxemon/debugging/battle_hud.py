# SPDX-License-Identifier: GPL-3.0
"""Readouts and opening messages for the debugging arena."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil

import pygame

INK = "#f1f3dd"
MINT = "#9cddb5"
GOLD = "#f8bd80"
PANEL = "#192f2e"
EDGE = "#4a645c"
METER_TWEEN_SECONDS = 0.34


@dataclass
class HealthMeter:
    target: int
    start: float
    elapsed: float = METER_TWEEN_SECONDS

    @property
    def displayed(self) -> float:
        progress = min(1.0, self.elapsed / METER_TWEEN_SECONDS)
        return self.target + (self.start - self.target) * (1 - progress) ** 2

    def set(self, health: int) -> None:
        if health != self.target:
            self.start = self.displayed
            self.target = health
            self.elapsed = 0.0


class BattleHUD:
    def __init__(self, party_hp: int, wild_hp: int, max_hp: int) -> None:
        self.max_hp = max_hp
        self.reset(party_hp, wild_hp)

    def reset(self, party_hp: int, wild_hp: int) -> None:
        self.party = HealthMeter(party_hp, party_hp)
        self.wild = HealthMeter(wild_hp, wild_hp)
        self.set_result("", 0, 0)

    def set_health(self, party_hp: int, wild_hp: int) -> None:
        self.party.set(party_hp)
        self.wild.set(wild_hp)

    def set_result(
        self, outcome: str, party_damage: int, wild_damage: int
    ) -> None:
        self.outcome = outcome
        self.party_damage = party_damage
        self.wild_damage = wild_damage

    def update(self, dt: float) -> None:
        for meter in (self.party, self.wild):
            meter.elapsed = min(METER_TWEEN_SECONDS, meter.elapsed + dt)

    def draw_header(
        self,
        canvas: pygame.Surface,
        font: pygame.font.Font,
        small: pygame.font.Font,
        ally_name: str,
        wild_name: str,
        objective: str,
        progress: int,
        total: int,
        *,
        caught: bool = False,
    ) -> None:
        width = canvas.get_width()
        party_card = pygame.Rect(23, 12, 240, 66)
        wild_card = party_card.copy()
        wild_card.right = width - party_card.left
        self.draw_meter(
            canvas,
            font,
            small,
            party_card,
            ally_name,
            "Party HP",
            self.party,
            self.party_damage,
        )
        self.draw_meter(
            canvas,
            font,
            small,
            wild_card,
            f"Caught {wild_name}" if caught else wild_name,
            "Wild HP",
            None if caught else self.wild,
            self.wild_damage,
        )
        center = width // 2
        label = small.render(f"CASE PROGRESS  {progress}/{total}", True, MINT)
        canvas.blit(label, label.get_rect(midtop=(center, 9)))
        title = font.render(objective, True, INK)
        title_width = wild_card.left - party_card.right - 20
        if title.get_width() > title_width:
            title = small.render(objective, True, INK)
        canvas.blit(title, title.get_rect(midtop=(center, 29)))
        if self.outcome:
            warning = bool(self.party_damage and not self.wild_damage)
            color = GOLD if warning else MINT
            badge = font.render(self.outcome, True, color)
            rect = badge.get_rect(midtop=(center, 52))
            outline = rect.inflate(20, 5)
            pygame.draw.rect(canvas, PANEL, outline, border_radius=5)
            pygame.draw.rect(canvas, color, outline, 1, border_radius=5)
            canvas.blit(badge, rect)

    def draw_meter(
        self,
        canvas: pygame.Surface,
        font: pygame.font.Font,
        small: pygame.font.Font,
        card: pygame.Rect,
        name: str,
        label: str,
        meter: HealthMeter | None,
        damage: int,
    ) -> None:
        pygame.draw.rect(canvas, PANEL, card, border_radius=8)
        pygame.draw.rect(canvas, EDGE, card, 1, border_radius=8)
        canvas.blit(
            font.render(name, True, INK), (card.left + 11, card.top + 6)
        )
        if meter is None:
            return
        bar = pygame.Rect(card.x + 11, card.y + 50, card.width - 22, 9)
        color = GOLD if meter.target <= self.max_hp * 0.35 else MINT
        pygame.draw.rect(canvas, "#0c201e", bar, border_radius=3)
        if meter.displayed:
            fill = bar.copy()
            fill.width = min(
                bar.width, ceil(bar.width * meter.displayed / self.max_hp)
            )
            pygame.draw.rect(canvas, color, fill, border_radius=3)
        pygame.draw.rect(canvas, EDGE, bar, 1, border_radius=3)
        hp_text = small.render(
            f"{label}  {ceil(meter.displayed)}/{self.max_hp}", True, INK
        )
        canvas.blit(hp_text, (bar.left, card.y + 29))
        if damage:
            lost = small.render(f"−{damage} HP", True, GOLD)
            canvas.blit(lost, lost.get_rect(topright=(bar.right, card.y + 29)))

    @staticmethod
    def draw_statement(
        canvas: pygame.Surface, small: pygame.font.Font, statement: str
    ) -> None:
        text = small.render(statement, True, INK)
        rect = text.get_rect(midtop=(canvas.get_width() // 2, 87))
        panel = rect.inflate(20, 9)
        pygame.draw.rect(canvas, PANEL, panel, border_radius=5)
        pygame.draw.rect(canvas, EDGE, panel, 1, border_radius=5)
        canvas.blit(text, rect)


def draw_opening(
    canvas: pygame.Surface,
    font: pygame.font.Font,
    small: pygame.font.Font,
    text: str,
    *,
    appearance: bool,
) -> None:
    panel = pygame.Rect(23, 292, 590, 208)
    pygame.draw.rect(canvas, PANEL, panel, border_radius=10)
    font = font if appearance else small
    line = ""
    y = panel.top + 18
    for word in text.split():
        next_line = f"{line} {word}" if line else word
        if line and font.size(next_line)[0] > panel.width - 36:
            canvas.blit(font.render(line, True, INK), (panel.left + 18, y))
            y += font.get_linesize()
            line = word
        else:
            line = next_line
    canvas.blit(font.render(line, True, INK), (panel.left + 18, y))
