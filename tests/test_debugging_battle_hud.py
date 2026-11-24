# SPDX-License-Identifier: GPL-3.0
import pygame


def new_hud():
    from tuxemon.debugging.battle_hud import BattleHUD

    return BattleHUD(100, 100, 100)


def test_damage_meter_animates_from_previous_health_before_landing():
    hud = new_hud()
    hud.set_health(72, 50)
    assert hud.party.displayed == 100
    assert hud.wild.displayed == 100

    hud.update(0.12)
    assert 72 < hud.party.displayed < 100
    assert 50 < hud.wild.displayed < 100

    hud.update(1)
    assert hud.party.displayed == 72
    assert hud.wild.displayed == 50


def test_retry_restores_health_and_discards_the_previous_outcome():
    hud = new_hud()
    hud.set_health(0, 68)
    hud.set_result("Not effective.", 25, 0)
    hud.update(0.12)
    hud.reset(100, 100)

    assert hud.party.displayed == 100
    assert hud.wild.displayed == 100
    assert hud.outcome == ""


def test_opening_and_combat_hud_fit_the_battle_canvas():
    from tuxemon.debugging.battle_hud import draw_opening

    pygame.font.init()
    canvas = pygame.Surface((960, 540))
    font = pygame.font.Font(None, 26)
    small = pygame.font.Font(None, 21)
    hud = new_hud()
    hud.set_health(75, 70)
    hud.set_result("Super effective!", 25, 30)
    hud.update(1)
    hud.draw_header(
        canvas,
        font,
        small,
        "Checkout Blackout",
        "Checkout Blackout",
        "Diagnose, repair, and verify checkout.",
        3,
        4,
    )
    draw_opening(
        canvas,
        font,
        small,
        "Wild Checkout Blackout Says - Checkout returns an error after a coupon is removed.",
        appearance=False,
    )
    assert canvas.get_at((23, 110)) == pygame.Color("black")
    assert canvas.get_at((36, 306)) != pygame.Color("black")
    assert canvas.get_at((155, 65)) == pygame.Color("#9cddb5")
    assert canvas.get_at((232, 65)) == pygame.Color("#0c201e")
    assert canvas.get_at((820, 65)) == pygame.Color("#9cddb5")
    assert canvas.get_at((908, 65)) == pygame.Color("#0c201e")


def test_caught_name_leaves_space_inside_the_wild_card_right_edge():
    pygame.font.init()
    canvas = pygame.Surface((960, 540))
    font = pygame.font.Font(None, 26)
    small = pygame.font.Font(None, 21)
    hud = new_hud()
    margin = pygame.Rect(926, 17, 34, 24)
    for creature in ("Echo Order", "Checkout Blackout"):
        canvas.fill("black")
        hud.draw_header(
            canvas,
            font,
            small,
            "Dandylion",
            creature,
            "Case solved",
            4,
            4,
            caught=True,
        )
        rendered_margin = pygame.image.tobytes(
            canvas.subsurface(margin), "RGB"
        )
        if creature == "Echo Order":
            empty_margin = rendered_margin
        else:
            assert rendered_margin == empty_margin
