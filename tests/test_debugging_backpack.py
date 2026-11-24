# SPDX-License-Identifier: GPL-3.0
from types import SimpleNamespace

import pygame
import pytest

from tuxemon.debugging.cases import CASES, INSPECT, PATCH, READ, RETRY


def companion(slug, name, *moves):
    return SimpleNamespace(
        slug=slug,
        name=name,
        moves=SimpleNamespace(
            get_moves=lambda: [SimpleNamespace(slug=move) for move in moves]
        ),
    )


@pytest.fixture
def backpack():
    from tuxemon.debugging.backpack import BattleBackpack

    if pygame.display.get_surface() is None:
        pygame.display.set_mode((1, 1))
    party = [
        companion("dandylion", "Dandylion", READ),
        companion("agnite", "Crash Loop", INSPECT, RETRY),
        companion("aardart", "Echo Order", PATCH),
    ]
    portraits = []
    for color in ("red", "orange", "yellow"):
        portrait = pygame.Surface((64, 64))
        portrait.fill(color)
        portraits.append(portrait)
    return BattleBackpack(party, portraits, case=CASES[1])


def test_backpack_links_the_receipt_action_to_its_earned_technique(backpack):
    assert backpack.move_label(INSPECT) == "Inspect Request (Compare Receipts)"
    assert backpack.move_label(RETRY) == "Retry Request"


def test_backpack_uses_earned_technique_name_without_an_alias(backpack):
    backpack.case = CASES[2]
    assert backpack.move_label(INSPECT) == "Inspect Request"


def test_backpack_reopens_on_active_companion_after_cancel(backpack):
    backpack.open(active=1)
    assert backpack.is_open
    assert backpack.selected == 1

    backpack.select(1)
    assert backpack.selected == 2
    backpack.close()
    assert not backpack.is_open

    backpack.open(active=1)
    assert backpack.selected == 1


def test_backpack_focus_wraps_across_owned_companions(backpack):
    backpack.open(active=0)
    backpack.select(-1)
    assert backpack.selected == 2
    backpack.select(1)
    assert backpack.selected == 0


def test_backpack_draws_portrait_for_focused_companion(backpack):
    pygame.font.init()
    title = pygame.font.Font(None, 26)
    small = pygame.font.Font(None, 21)
    canvas = pygame.Surface((960, 540))
    backpack.open(active=0)
    backpack.draw(canvas, title, small)
    assert canvas.get_at((243, 245)) == pygame.Color("red")

    backpack.select(-1)
    canvas.fill("black")
    backpack.draw(canvas, title, small)

    assert canvas.get_at((243, 245)) == pygame.Color("yellow")
