# SPDX-License-Identifier: GPL-3.0
"""Short visual effects that mirror simulated debugging actions."""

from math import pi, sin

import pygame

from tuxemon.debugging.cases import INSPECT, PATCH, READ, RETRY

ALLY = (223, 227)
TARGET = (744, 207)
MINT = "#9cddb5"
GOLD = "#f8bd80"


def draw_move(
    canvas: pygame.Surface,
    move: str,
    progress: float,
    opponent: pygame.Rect,
) -> None:
    if move == READ:
        # Sweep each sprite from head to foot.
        scan = opponent.inflate(36, 22)
        pygame.draw.rect(canvas, MINT, scan, 2, border_radius=5)
        y = scan.top + round(scan.height * progress)
        pygame.draw.line(canvas, MINT, (scan.left, y), (scan.right, y), 3)
    elif move in (INSPECT, RETRY):
        # The outgoing packet and response travel in opposite directions.
        outgoing = progress < 0.5
        distance = 2 * (progress if outgoing else 1 - progress)
        x = round(ALLY[0] + distance * (TARGET[0] - ALLY[0]))
        y = round(ALLY[1] + distance * (TARGET[1] - ALLY[1]) - 28)
        color = MINT if outgoing else GOLD
        pygame.draw.line(
            canvas,
            "#668074",
            (ALLY[0], ALLY[1] - 28),
            (TARGET[0], TARGET[1] - 28),
            2,
        )
        pygame.draw.rect(
            canvas, color, (x - 11, y - 7, 22, 14), border_radius=3
        )
        pygame.draw.line(canvas, "#162b2a", (x - 6, y - 1), (x + 6, y - 1), 2)
        pygame.draw.line(canvas, "#162b2a", (x - 6, y + 3), (x + 2, y + 3), 2)
        if move == RETRY:
            pygame.draw.arc(
                canvas, GOLD, (211, 175, 24, 24), 0, 2 * pi * progress, 3
            )
    elif move == PATCH:
        code = pygame.Rect(TARGET[0] - 45, TARGET[1] - 64, 90, 43)
        pygame.draw.rect(canvas, "#162b2a", code, border_radius=5)
        pygame.draw.rect(canvas, MINT, code, 2, border_radius=5)
        pygame.draw.line(
            canvas,
            "#668074",
            (code.left + 11, code.top + 12),
            (code.right - 20, code.top + 12),
            3,
        )
        width = round(63 * progress)
        pygame.draw.line(
            canvas,
            MINT,
            (code.left + 11, code.top + 28),
            (code.left + 11 + width, code.top + 28),
            4,
        )


def draw_capture(canvas: pygame.Surface, progress: float) -> None:
    flight = min(1.0, progress / 0.66)
    x = round(ALLY[0] + flight * (TARGET[0] - ALLY[0]))
    y = round(
        ALLY[1] + flight * (TARGET[1] - ALLY[1]) - 105 * sin(pi * flight)
    )
    if progress > 0.66:
        x += round(6 * sin(24 * pi * progress))
    pygame.draw.circle(canvas, "#f4eadb", (x, y), 12)
    pygame.draw.rect(canvas, "#ec8475", (x - 9, y - 7, 18, 7), border_radius=3)
    pygame.draw.line(canvas, "#162b2a", (x - 11, y), (x + 11, y), 3)
    pygame.draw.circle(canvas, "#162b2a", (x, y), 3)
