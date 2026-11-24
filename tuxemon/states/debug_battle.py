# SPDX-License-Identifier: GPL-3.0
"""Play debugging objectives through Tuxemon's native combat presentation."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, Any, ClassVar, cast

from tuxemon.combat.machine import CombatPhase
from tuxemon.core.core_effect import ItemEffectResult
from tuxemon.core.effects.capture import register_capture
from tuxemon.debugging.cases import CASES, LABELS, Encounter
from tuxemon.item.item import Item
from tuxemon.states.combat_menus import MainCombatMenuState
from tuxemon.states.combat_state import CombatState
from tuxemon.technique.technique import Technique
from tuxemon.tools import open_choice_dialog, open_dialog
from tuxemon.ui.menu_options import ChoiceOption, MenuOptions

if TYPE_CHECKING:
    from tuxemon.base_client import BaseClient
    from tuxemon.combat.combat_context import CombatContext
    from tuxemon.monster.monster import Monster


class DebugCombatMenuState(MainCombatMenuState):
    name: ClassVar[str] = "DebugCombatMenuState"

    def __init__(self, client: BaseClient, **kwargs: Any) -> None:
        super().__init__(client=client, **kwargs)

    def create_new_menu_items_group(self) -> None:
        super().create_new_menu_items_group()
        self.menu_items.rectangular = True

    def get_menu_profile(self) -> tuple[dict[str, str], dict[str, bool]]:
        return (
            {
                "menu_fight": "open_technique_menu",
                "menu_monster": "open_swap_menu",
                "debug_case_notes": "open_case_notes",
            },
            {
                "menu_fight": True,
                "menu_monster": True,
                "debug_case_notes": True,
            },
        )

    def open_case_notes(self) -> None:
        cast(DebugBattleState, self.combat).show_case_notes()


class DebugBattleState(CombatState):
    """Use native encounters and animation, with a case as the win condition."""

    name: ClassVar[str] = "DebugBattleState"

    def __init__(
        self, client: BaseClient, context: CombatContext, index: int
    ) -> None:
        self.index = index
        self.case = CASES[index]
        self.fight = Encounter(self.case, message=self.case.symptom)
        self.target = context.teams[1].monsters[0]
        self._capturing = False
        self._capture_complete = False
        super().__init__(client, context)

    def next_combat_phase(self) -> CombatPhase | None:
        if self.phase == CombatPhase.DECISION:
            return None
        return super().next_combat_phase()

    def transition_phase(self, phase: CombatPhase) -> None:
        if phase == CombatPhase.DECISION:
            self.show_pages(
                [
                    f"{self.case.title}. {self.case.objective}",
                    self.case.symptom,
                ]
            )
        else:
            super().transition_phase(phase)

    def update_phase(self) -> None:
        if self.phase != CombatPhase.DECISION:
            super().update_phase()
            return
        if self.client.current_state is not self:
            return
        if self._capture_complete:
            self.end_combat()
            return
        if self._capturing:
            return
        queue = self.combat_session.action_queue
        if not queue.is_empty():
            action = queue.pop()
            self.perform_action(action.user, action.method, action.target)
        elif self.fight.pending:
            self.show_answers()
        elif self.fight.solved:
            self.show_choices(
                [ChoiceOption("capture", "Throw Tuxeball", self.capture)]
            )
        else:
            player = self.session.player
            active = self.combat_session.field_monsters.get_monsters(player)[0]
            self.client.push_state(
                "DebugCombatMenuState",
                session=self.session,
                combat=self,
                character=player,
                monster=active,
            )

    def _handle_monster_technique(
        self, user: Monster, method: Technique, target: Monster
    ) -> None:
        if method.slug == "swap":
            super()._handle_monster_technique(user, method, target)
            return

        before = self.fight.drops
        self.fight.use(
            method.slug, {move.slug for move in user.moves.get_moves()}
        )
        delay = self.play_technique(method, target)
        pages = self.fight.message.splitlines()
        if self.fight.drops > before:
            self.task(
                partial(self.play_disruption, user, pages), interval=delay
            )
        else:
            self.task(partial(self.show_pages, pages), interval=delay)

    def play_technique(self, method: Technique, target: Monster) -> float:
        self.event_bus.publish(
            "play_sound_combat",
            sound=method.sound.sfx,
            value=method.sound.volume,
        )
        self.event_bus.publish(
            "play_animation_combat", method, target, None, 0.0
        )
        sprite = self._method_cache.get(method, False)
        return 0.6 + (
            sprite.animation.duration if sprite and sprite.animation else 0.0
        )

    def play_disruption(self, user: Monster, pages: list[str]) -> None:
        self._on_combat_dialog(self.case.disruption, dialog_speed="max")
        delay = self.play_technique(Technique.create("muddle"), user)
        self.task(
            partial(self.show_pages, [*pages, self.case.disruption]),
            interval=delay,
        )

    def show_pages(self, pages: list[str]) -> None:
        open_dialog(self.client, pages, dialog_speed="max")

    def show_case_notes(self) -> None:
        pages = [
            f"{self.case.title}. {self.case.objective}",
            self.case.symptom,
        ]
        for clue in self.fight.evidence_notes:
            pages.extend(clue.splitlines())
        if self.fight.duplicates:
            pages.append(
                f"Duplicate orders caused by retry: {self.fight.duplicates}."
            )
        self.show_pages(pages)

    def show_choices(self, options: list[ChoiceOption]) -> None:
        open_choice_dialog(self.client, MenuOptions(options))

    def show_answers(self) -> None:
        self._on_combat_dialog(
            self.fight.step.evidence.splitlines()[-1], dialog_speed="max"
        )
        options = [
            ChoiceOption(str(index), text, partial(self.answer, index))
            for index, text in enumerate(self.fight.step.options)
        ]
        options.append(
            ChoiceOption("review", "Review evidence", self.review_evidence)
        )
        self.show_choices(options)

    def review_evidence(self) -> None:
        self.client.remove_state_by_name("ChoiceState")
        self.show_case_notes()

    def answer(self, index: int) -> None:
        self.client.remove_state_by_name("ChoiceState")
        self.fight.answer(index)
        self.show_pages(self.fight.message.splitlines())

    def capture(self) -> None:
        self.client.remove_state_by_name("ChoiceState")
        self._capturing = True
        item = Item.create("tuxeball")
        sprite = self._method_cache.get(item, False)
        if sprite is None:
            raise RuntimeError("The Tuxeball capture animation is missing.")
        self._on_combat_dialog("Throwing Tuxeball!", dialog_speed="max")
        self.event_bus.publish(
            "play_sound_combat", sound=item.sound.sfx, value=item.sound.volume
        )
        self.animate_capture_monster(
            ItemEffectResult(name=item.name, success=True, num_shakes=2),
            self.target,
            item,
            sprite,
            ("Gotcha!", f"{self.target.name} joined your party.", ""),
        )

    def _on_capture_finished(
        self, monster: Monster, is_captured: bool
    ) -> None:
        if (
            not is_captured
            or monster is not self.target
            or self._capture_complete
        ):
            return
        monster.moves.replace_all_moves(
            [Technique.create(move) for move in self.case.reward]
        )
        monster.get_owner().party.remove_monster(monster)
        register_capture(self.session, Item.create("tuxeball"), monster)
        self.session.player.game_variables.set(
            "debug_cases_cleared", self.index + 1
        )
        self._capture_complete = True
        reward = " and ".join(LABELS[move] for move in self.case.reward)
        followup = "Take another step in the grass to find the next encounter."
        if self.index + 1 == len(CASES):
            followup = "Debugging Trail complete. All three cases solved!"
        self.show_pages([f"{monster.name} knows {reward}.", followup])
