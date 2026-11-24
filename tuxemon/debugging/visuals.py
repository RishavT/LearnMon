# SPDX-License-Identifier: GPL-3.0
"""Short visual effects that mirror simulated debugging actions."""

from math import pi, sin

import pygame

from tuxemon.debugging.cases import INSPECT, PATCH, RETRY, Receipt

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


def draw_move(
    canvas: pygame.Surface,
    move: str,
    progress: float,
    font: pygame.font.Font,
    *,
    compare: bool = False,
    patched: bool = False,
    patch_visible: bool = False,
) -> None:
    if move == INSPECT and compare:
        # One sweep links the same attempt line on both receipts.
        x = 344 + round(166 * progress)
        pygame.draw.rect(canvas, MINT, (343, 170, 167, 71), 2, border_radius=5)
        pygame.draw.line(canvas, MINT, (x, 174), (x, 236), 2)
    elif move == INSPECT:
        x = round(282 + 353 * sin(pi * progress))
        y = round(202 - 45 * sin(pi * progress))
        pygame.draw.arc(canvas, MINT, (270, 152, 377, 113), 0, pi, 2)
        pygame.draw.circle(canvas, MINT, (x, y), 9, 3)
        pygame.draw.circle(canvas, MINT, (x, y), 3)
    elif move == RETRY:
        # A new outgoing POST, followed by a separate response.
        if progress < 0.56:
            travel = (progress / 0.56) ** 2
            tag, color = "POST", MINT
        else:
            travel = 1 - ((progress - 0.56) / 0.44)
            tag, color = "RESPONSE", GOLD
        x = round(295 + 384 * travel)
        y = round(210 - 50 * sin(pi * travel))
        label = font.render(tag, True, "#162b2a")
        badge = label.get_rect(center=(x, y)).inflate(14, 8)
        pygame.draw.rect(canvas, color, badge, border_radius=4)
        canvas.blit(label, label.get_rect(center=badge.center))
    elif move == PATCH:
        if patch_visible:
            _draw_patch(canvas, progress, font, patched=patched)
        else:
            label = font.render("?", True, GOLD)
            canvas.blit(label, label.get_rect(center=(481, 192)))
    elif move == "switch":
        spread = round(5 + 37 * progress)
        pygame.draw.ellipse(
            canvas,
            MINT,
            (223 - spread, 238 - spread // 4, 2 * spread, spread // 2),
            2,
        )


def _draw_patch(
    canvas: pygame.Surface,
    progress: float,
    font: pygame.font.Font,
    *,
    patched: bool,
) -> None:
    code = pygame.Rect(386, 160, 207, 73)
    pygame.draw.rect(canvas, "#162b2a", code, border_radius=5)
    pygame.draw.rect(canvas, MINT, code, 2, border_radius=5)
    before = font.render("coupon.amount", True, GOLD)
    after = font.render("coupon?.amount ?? 0", True, MINT)
    canvas.blit(before, before.get_rect(midtop=(code.centerx, code.top + 12)))
    if not patched:
        pygame.draw.line(
            canvas,
            MINT,
            (code.left + 12, code.top + 33),
            (code.left + 12 + round(183 * progress), code.top + 33),
            2,
        )
        return
    landing = min(1.0, progress / 0.58)
    x = code.centerx - round(209 * (1 - landing) ** 2)
    if landing == 1.0:
        canvas.blit(
            after, after.get_rect(midtop=(code.centerx, code.top + 41))
        )
        pygame.draw.line(
            canvas,
            GOLD,
            (code.centerx - before.get_width() // 2, code.top + 20),
            (code.centerx + before.get_width() // 2, code.top + 20),
            2,
        )
    else:
        pygame.draw.rect(canvas, MINT, (x - 13, 205, 26, 15), border_radius=3)


def draw_receipts(
    canvas: pygame.Surface,
    receipts: tuple[Receipt, ...],
    font: pygame.font.Font,
    *,
    comparison: bool,
    stamp_time: float | None = None,
    retry_progress: float | None = None,
) -> None:
    if stamp_time is not None and stamp_time < 0.08:
        flight = min(1.0, max(0.0, (stamp_time + 0.34) / 0.42))
        tag = font.render("POST", True, "#162b2a")
        badge = tag.get_rect(center=(round(366 + 344 * flight), 151))
        pygame.draw.rect(canvas, MINT, badge.inflate(16, 8), border_radius=4)
        canvas.blit(tag, badge)
        return

    visible = min(2, 1 + int(stamp_time is None or stamp_time >= 0.27))
    for index, receipt in enumerate(receipts[:visible]):
        delay = 0.08 if index == 0 else 0.27
        rect = pygame.Rect(350 + 81 * index, 178, 73, 56)
        _draw_receipt(canvas, rect, receipt, font, comparison=comparison)
        if stamp_time is not None and stamp_time - delay < 0.15:
            spread = round((stamp_time - delay) * 60)
            pygame.draw.rect(
                canvas,
                GOLD,
                rect.inflate(spread * 2, spread * 2),
                2,
                border_radius=4,
            )
    if len(receipts) > 2:
        height = (
            round(40 * (1 - retry_progress) ** 2)
            if retry_progress is not None
            else 0
        )
        rect = pygame.Rect(532, 178 - height, 73, 56)
        for offset in reversed(range(1, min(4, len(receipts) - 2))):
            pygame.draw.rect(
                canvas,
                "#cb895e",
                rect.move(offset * 3, -offset * 3),
                border_radius=3,
            )
        _draw_receipt(canvas, rect, receipts[-1], font, comparison=False)
        extras = font.render(f"+{len(receipts) - 2} from retry", True, GOLD)
        canvas.blit(extras, extras.get_rect(midtop=(rect.centerx, 240)))
    if visible == 2:
        pygame.draw.line(canvas, GOLD, (386, 171), (468, 171), 2)
        tag = font.render("One checkout", True, GOLD)
        canvas.blit(tag, tag.get_rect(midbottom=(427, 167)))


def _draw_receipt(
    canvas: pygame.Surface,
    rect: pygame.Rect,
    receipt: Receipt,
    font: pygame.font.Font,
    *,
    comparison: bool,
) -> None:
    paper = "#fbe4b5" if not comparison else "#c4ebce"
    pygame.draw.rect(canvas, paper, rect, border_radius=3)
    for x in range(rect.left + 6, rect.right - 2, 7):
        pygame.draw.circle(canvas, "#162b2a", (x, rect.bottom), 2)
    for text, y in (
        (f"#{receipt.order_id}", 7),
        ("Same cart", 23),
        (receipt.request_id, 38),
    ):
        label = font.render(text, True, "#162b2a")
        canvas.blit(label, label.get_rect(midtop=(rect.centerx, rect.top + y)))


def draw_stack_surge(
    canvas: pygame.Surface,
    progress: float,
    failures: int,
    font: pygame.font.Font,
) -> None:
    if not failures:
        return
    x = 557 + round(111 * (1 - progress) ** 2)
    for index in range(min(4, failures)):
        y = 243 - index * 12
        rect = pygame.Rect(x - index * 4, y, 70, 12)
        pygame.draw.rect(canvas, "#8e4d52", rect, border_radius=2)
        pygame.draw.line(canvas, GOLD, rect.topleft, rect.topright, 2)
    label = font.render(f"{failures} failed", True, GOLD)
    canvas.blit(label, label.get_rect(midtop=(x + 30, 261)))


def draw_fault_stack(
    canvas: pygame.Surface, faults: int, font: pygame.font.Font
) -> None:
    rect = pygame.Rect(452, 237, 94, 29)
    for offset in reversed(range(1, min(faults, 4))):
        pygame.draw.rect(
            canvas,
            "#c68260",
            rect.move(offset * 4, -offset * 4),
            border_radius=3,
        )
    pygame.draw.rect(canvas, GOLD, rect, border_radius=3)
    label = font.render(f"TypeError ×{faults}", True, "#162b2a")
    canvas.blit(label, label.get_rect(center=rect.center))


def draw_crash_echo(
    canvas: pygame.Surface, progress: float, opponent: pygame.Rect
) -> None:
    """A second fault leaves the opponent and lands beside the result."""
    for lag in (0.17, 0.0):
        travel = min(1.0, max(0.0, (progress - lag) / (1.0 - lag)))
        x = round(opponent.centerx + (499 - opponent.centerx) * travel)
        y = round(opponent.centery + (251 - opponent.centery) * travel)
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
