# SPDX-License-Identifier: GPL-3.0
"""Audio cues timed to the Debugging Trail animations."""

from tuxemon.audio import MusicPlayerState
from tuxemon.db import MusicStatus
from tuxemon.debugging.cases import (
    DOUBLE_STAMP,
    INSPECT,
    PATCH,
    READ,
    REPEAT_CRASH,
    RETRY,
    STACK_SURGE,
)

BATTLE_TRACK = "debug_battle"
DEFEAT_TRACK = "debug_defeat"
REWARD_TRACK = "debug_recruit"

CUES: dict[str, tuple[tuple[float, str], ...]] = {
    READ: (
        (0.14, "debug_read_sweep"),
        (0.44, "debug_read_tick"),
        (0.75, "debug_read_reveal"),
    ),
    INSPECT: ((0.10, "debug_request_send"), (0.42, "debug_request_return")),
    RETRY: ((0.10, "debug_retry_send"), (0.49, "debug_retry_return")),
    PATCH: ((0.32, "debug_patch_apply"),),
    REPEAT_CRASH: ((0.11, "debug_crash"),),
    DOUBLE_STAMP: ((0.08, "debug_stamp"), (0.27, "debug_stamp")),
    STACK_SURGE: ((0.08, "debug_stack"), (0.27, "debug_stack")),
    "introduction": ((0.10, "debug_battle_start"),),
    "effective": ((0.08, "debug_effective"),),
    "damage": ((0.08, "debug_damage"),),
    "switch": ((0.10, "debug_switch"),),
    "capture": ((0.08, "debug_ball_throw"), (0.76, "debug_ball_latch")),
}


class BattleAudio:
    def __init__(self, music: MusicPlayerState) -> None:
        self.music = music
        self._return_track: str | None = None
        self._return_paused = False
        self._active = False

    def enter(self) -> None:
        if self._active:
            return

        self._active = True
        self._return_track = self.music.current_song
        self._return_paused = self.music.status == MusicStatus.PAUSED
        self._play_battle_track()

    def _play_battle_track(self) -> None:
        self.music.play(
            BATTLE_TRACK,
            volume=self.music.get_volume(ignore_mute=True),
            fade_ms=240,
        )

    def reward(self) -> None:
        if self._active and self.music.current_song == BATTLE_TRACK:
            self.music.play(
                REWARD_TRACK,
                volume=self.music.get_volume(ignore_mute=True),
                loop=0,
                fade_ms=35,
            )

    def defeat(self) -> None:
        if self._active and self.music.current_song == BATTLE_TRACK:
            self.music.play(
                DEFEAT_TRACK,
                volume=self.music.get_volume(ignore_mute=True),
                loop=0,
                fade_ms=35,
            )

    def retry(self) -> None:
        if self._active and self.music.current_song == DEFEAT_TRACK:
            self._play_battle_track()

    def leave(self) -> None:
        if not self._active:
            return

        self._active = False
        if self.music.current_song not in (
            BATTLE_TRACK,
            DEFEAT_TRACK,
            REWARD_TRACK,
        ):
            return

        if self._return_track is None:
            self.music.stop(fadeout_time=0)
            return

        self.music.play(
            self._return_track,
            volume=self.music.get_volume(ignore_mute=True),
            fade_ms=350,
        )
        if self._return_paused:
            self.music.pause()
