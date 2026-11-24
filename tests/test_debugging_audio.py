# SPDX-License-Identifier: GPL-3.0
from unittest.mock import Mock

import pygame

from tuxemon.audio import MusicPlayerState, SoundManager, SoundWrapper
from tuxemon.database.bootstrap import bootstrap_database
from tuxemon.database.registry import validator
from tuxemon.debugging.audio import (
    BATTLE_TRACK,
    CUES,
    REWARD_TRACK,
    BattleAudio,
)


def test_battle_music_follows_capture_and_keeps_player_volume(monkeypatch):
    music = MusicPlayerState()
    load = Mock()
    monkeypatch.setattr(music, "load", load)
    monkeypatch.setattr(
        "tuxemon.audio.platform.mixer.music.set_volume", Mock()
    )
    music.play("music_city_park", volume=0.27)
    music.mute()
    sounds = Mock()
    battle = BattleAudio(music, sounds)

    battle.enter()
    battle.enter()
    assert music.current_song == BATTLE_TRACK
    sounds.play.assert_called_once_with("debug_battle_start")

    music.set_volume(0.46)
    battle.reward()
    battle.reward()
    assert music.current_song == REWARD_TRACK
    assert load.call_args.args[:3] == (REWARD_TRACK, 0.0, 0)

    battle.leave()
    battle.leave()
    assert [call.args[0] for call in load.call_args_list] == [
        "music_city_park",
        BATTLE_TRACK,
        REWARD_TRACK,
        "music_city_park",
    ]
    assert music.get_volume() == 0.0
    music.unmute()
    assert music.get_volume() == 0.46


def test_double_stamp_repeats_the_same_impact():
    assert CUES["double_stamp"] == (
        (0.08, "debug_stamp"),
        (0.27, "debug_stamp"),
    )


def test_debug_audio_assets_play_through_pygame(monkeypatch):
    monkeypatch.setattr(validator, "_instance", None)
    db = bootstrap_database()
    for table in ("music", "sounds"):
        db.preload(table)
        db.load(table)
    monkeypatch.setattr("tuxemon.audio.db", db)

    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    own_mixer = pygame.mixer.get_init() is None
    if own_mixer:
        pygame.mixer.init()

    try:
        sounds = SoundManager()
        slugs = {slug for cues in CUES.values() for _, slug in cues}
        for slug in slugs | {"debug_battle_start"}:
            wrapper = sounds.load_sound(slug)
            assert isinstance(wrapper, SoundWrapper)
            assert wrapper.sound is not None
            assert 0.05 < wrapper.sound.get_length() < 0.35

        music = MusicPlayerState()
        for track in (BATTLE_TRACK, REWARD_TRACK):
            pygame.mixer.music.load(music.get_path(track))
            pygame.mixer.music.play()
            assert pygame.mixer.music.get_busy()
    finally:
        pygame.mixer.music.stop()
        if own_mixer:
            pygame.mixer.quit()
