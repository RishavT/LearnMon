# SPDX-License-Identifier: GPL-3.0
"""Short visual effects that mirror simulated debugging actions."""

from math import pi, sin

import pygame

from tuxemon.debugging.cases import INSPECT, PATCH, RETRY

ALLY = (223, 227)
TARGET = (744, 207)
MINT = "#9cddb5"
GOLD = "#f8bd80"


def read_log_offsets(progress: float) -> tuple[int, int]:
    """Horizontal ally wind-up and target recoil, in canvas pixels."""
    if progress < 0.17:
        ally = -12 * sin(pi / 2 * progress / 0.17)
    elif progress < 0.38:
        ally = -12 + 53 * sin(pi / 2 * (progress - 0.17) / 0.21)
    else:
        ally = 41 * max(0.0, 1 - (progress - 0.38) / 0.43) ** 2
    recoil = min(1.0, max(0.0, (progress - 0.47) / 0.29))
    target = 22 * sin(pi * recoil) * (1 - recoil / 2)
    return round(ally), round(target)


def draw_read_log(
    canvas: pygame.Surface,
    progress: float,
    ally: pygame.Rect,
    opponent: pygame.Rect,
) -> None:
    source = (ally.right, ally.centery - 10)
    target = opponent.center

    if 0.14 <= progress < 0.47:
        travel = (progress - 0.14) / 0.33
        # Staggered pulses travel from the acting Tuxemon to the bug.
        for lag in (0.15, 0.075, 0.0):
            fraction = travel - lag
            if fraction < 0:
                continue
            x = round(source[0] + (target[0] - source[0]) * fraction)
            y = round(
                source[1]
                + (target[1] - source[1]) * fraction
                - 24 * sin(pi * fraction)
            )
            pygame.draw.circle(canvas, MINT, (x, y), 4 if lag else 7, 2)
    elif 0.47 <= progress < 0.79:
        sweep = (progress - 0.47) / 0.32
        scan = opponent.inflate(26, 18)
        pygame.draw.rect(canvas, MINT, scan, 2, border_radius=6)
        y = scan.top + round(scan.height * sweep)
        pygame.draw.line(canvas, MINT, (scan.left, y), (scan.right, y), 3)
        radius = round(12 + 35 * sweep)
        if sweep < 0.55:
            pygame.draw.circle(canvas, GOLD, target, radius, 2)
    elif progress >= 0.79:
        travel = (progress - 0.79) / 0.21
        # The recovered trace lands where the player will read it.
        x = round(target[0] + (425 - target[0]) * travel)
        y = round(target[1] + (298 - target[1]) * travel)
        pygame.draw.rect(
            canvas, "#bceacb", (x - 12, y - 7, 24, 14), border_radius=3
        )
        for offset in (-3, 1):
            pygame.draw.line(
                canvas, "#162b2a", (x - 7, y + offset), (x + 6, y + offset), 2
            )


def draw_move(canvas: pygame.Surface, move: str, progress: float) -> None:
    if move in (INSPECT, RETRY):
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


def draw_crash_echo(
    canvas: pygame.Surface, progress: float, opponent: pygame.Rect
) -> None:
    """A second fault leaves the opponent and lands beside the result."""
    for lag in (0.17, 0.0):
        travel = min(1.0, max(0.0, (progress - lag) / (1.0 - lag)))
        x = round(opponent.centerx + (511 - opponent.centerx) * travel)
        y = round(opponent.centery + (270 - opponent.centery) * travel)
        pygame.draw.rect(
            canvas, GOLD, (x - 8, y - 6, 16, 12), 2, border_radius=3
        )
        pygame.draw.line(canvas, GOLD, (x - 4, y), (x + 4, y), 2)


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
