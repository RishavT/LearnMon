# SPDX-License-Identifier: GPL-3.0
"""Party selection overlay for a Debugging Trail encounter."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pygame

from tuxemon.debugging.cases import LABELS
from tuxemon.graphics import load_image

if TYPE_CHECKING:
    from tuxemon.debugging.cases import Case
    from tuxemon.monster.monster import Monster


@dataclass(frozen=True)
class CompanionIdentity:
    role: str
    description: tuple[str, str]


COMPANION_IDENTITIES = {
    "dandylion": CompanionIdentity(
        "Log tracker", ("Follows the trail back", "to the line that failed.")
    ),
    "agnite": CompanionIdentity(
        "Request runner", ("Traces a request, then", "checks it with a retry.")
    ),
    "aardart": CompanionIdentity(
        "Receipt stamper", ("Turns its receipt stamp", "into a code patch.")
    ),
    "ampystoma": CompanionIdentity(
        "Checkout fixer", ("Tracks failed checkouts", "and patches the cause.")
    ),
}
UNKNOWN_IDENTITY = CompanionIdentity("", ("", ""))


def companion_identity(slug: str) -> CompanionIdentity:
    return COMPANION_IDENTITIES.get(slug, UNKNOWN_IDENTITY)


class BattleBackpack:
    def __init__(
        self,
        party: Sequence[Monster],
        portraits: Sequence[pygame.Surface],
        *,
        case: Case,
    ) -> None:
        self.party = party
        self.portraits = portraits
        self.case = case
        self.icon = pygame.transform.scale_by(
            load_image("gfx/ui/menu/backpack.png"), 2
        )
        self.active = 0
        self.selected = 0
        self.is_open = False

    def open(self, active: int) -> None:
        self.active = self.selected = active
        self.is_open = bool(self.party)

    def select(self, delta: int) -> None:
        if self.is_open:
            self.selected = (self.selected + delta) % len(self.party)

    def close(self) -> None:
        self.is_open = False

    def move_label(self, move: str) -> str:
        earned_label = LABELS[move]
        battle_label = self.case.move_label(move)
        if battle_label == earned_label:
            return earned_label
        return f"{earned_label} ({battle_label})"

    def draw(
        self,
        canvas: pygame.Surface,
        font: pygame.font.Font,
        small: pygame.font.Font,
    ) -> None:
        if not self.is_open:
            return

        dim = pygame.Surface(canvas.get_size(), pygame.SRCALPHA)
        dim.fill((8, 18, 16, 190))
        canvas.blit(dim, (0, 0))
        panel_height = max(358, 136 + len(self.party) * 53)
        panel = pygame.Rect(0, 0, 720, panel_height)
        panel.center = canvas.get_rect().center
        pygame.draw.rect(canvas, "#182d2a", panel, border_radius=12)
        pygame.draw.rect(canvas, "#698a70", panel, width=2, border_radius=12)

        def text(
            value: str,
            point: tuple[int, int],
            face: pygame.font.Font = small,
            color: str = "#f1f3dd",
        ) -> None:
            canvas.blit(face.render(value, True, color), point)

        canvas.blit(self.icon, (panel.x + 22, panel.y + 17))
        text("Backpack", (panel.x + 64, panel.y + 20), font)
        text(
            "Choose a companion", (panel.x + 64, panel.y + 44), color="#b7d2b3"
        )

        preview = pygame.Rect(panel.x + 21, panel.y + 78, 205, 216)
        pygame.draw.rect(canvas, "#203b35", preview, border_radius=8)
        pygame.draw.ellipse(
            canvas, "#426452", (preview.x + 21, preview.y + 104, 163, 30)
        )
        portrait = self.portraits[self.selected]
        canvas.blit(
            portrait,
            portrait.get_rect(midbottom=(preview.centerx, preview.y + 121)),
        )
        identity = companion_identity(self.party[self.selected].slug)
        text(identity.role, (preview.x + 15, preview.y + 147), font, "#f9d88d")
        for index, line in enumerate(identity.description):
            text(line, (preview.x + 15, preview.y + 175 + 16 * index))

        row = pygame.Rect(panel.x + 243, panel.y + 78, 455, 48)
        for index, monster in enumerate(self.party):
            focused = index == self.selected
            pygame.draw.rect(
                canvas,
                "#426452" if focused else "#203b35",
                row,
                border_radius=6,
            )
            if focused:
                pygame.draw.rect(
                    canvas, "#f9d88d", row, width=2, border_radius=6
                )
                pygame.draw.polygon(
                    canvas,
                    "#f9d88d",
                    [
                        (row.x + 10, row.y + 12),
                        (row.x + 17, row.y + 17),
                        (row.x + 10, row.y + 22),
                    ],
                )
            text(monster.name, (row.x + 26, row.y + 5), font)
            if index == self.active:
                marker = small.render("In battle", True, "#f9d88d")
                canvas.blit(
                    marker,
                    marker.get_rect(topright=(row.right - 13, row.y + 7)),
                )
            moves = "  /  ".join(
                self.move_label(move.slug)
                for move in monster.moves.get_moves()
                if move.slug in LABELS
            )
            text(moves, (row.x + 26, row.y + 28), color="#c2dfbd")
            row.y += 53

        text(
            "Arrow keys  Browse     Enter  Choose     Shift / Esc  Back",
            (panel.x + 22, panel.bottom - 33),
        )
