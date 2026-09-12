import os
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame
import sound_manager
import text_log
from paths import res_path


class TypewriterSoundTests(unittest.TestCase):
    def setUp(self):
        settings = patch('settings_manager.load_settings', return_value={})
        settings.start()
        self.addCleanup(settings.stop)
        text_log.reset()
        text_log.set_typewriter_override(True)

    def test_chinese_letters_tick_but_spaces_and_punctuation_do_not(self):
        text_log.add('你， 好！')
        self.assertTrue(text_log.update_typewriter(.025))
        self.assertFalse(text_log.update_typewriter(.05))
        self.assertTrue(text_log.update_typewriter(.035))
        self.assertFalse(text_log.update_typewriter(.1))
        self.assertFalse(text_log.update_typewriter(.1))

    def test_ticks_are_limited_without_delaying_text_or_bursting_after_a_stall(self):
        for fps in (20, 60):
            with self.subTest(fps=fps):
                text_log.clear_history()
                text_log.add('字' * 200)
                times = [(i + 1) / fps for i in range(fps) if text_log.update_typewriter(1 / fps)]
                self.assertTrue(times)
                self.assertLessEqual(len(times), 13)
                self.assertTrue(all(b - a >= .079 for a, b in zip(times, times[1:])))
                self.assertAlmostEqual(text_log._active_progress, 40)
        self.assertTrue(text_log.update_typewriter(10))
        self.assertFalse(text_log.update_typewriter(.1))

    def test_pause_skip_and_instant_text_never_replay_hidden_characters(self):
        text_log.add('這是一段測試文字' * 5)
        self.assertTrue(text_log.update_typewriter(.025))
        self.assertFalse(text_log.update_typewriter(0))
        text_log.finish_typewriter()
        self.assertFalse(text_log.update_typewriter(.5))
        text_log.set_typewriter_override(False)
        text_log.add('直接顯示文字')
        self.assertFalse(text_log.update_typewriter(.5))

    def test_mixer_uses_normal_typing_gain_with_independent_mute(self):
        pygame.mixer.init()
        self.addCleanup(pygame.mixer.quit)
        clicks = {name: pygame.mixer.Sound(res_path('assets', 'sounds', 'sfx', filename))
                  for name, filename in [('ui_click', 'button_click.wav'), ('typewriter', 'typewriter_tick.wav')]}
        self.assertLess(clicks['typewriter'].get_length(), text_log.TYPEWRITER_SOUND_INTERVAL)
        with patch.object(sound_manager, '_sfx_cache', clicks):
            for volume in (1.0, 0.5, 0.0, 1.0):
                with patch.object(sound_manager, '_sfx_volume', volume), patch.object(sound_manager, '_typewriter_volume', volume):
                    sound_manager._apply_sfx_volume()
                    if volume:
                        self.assertGreater(clicks['typewriter'].get_volume(), 0)
                        self.assertEqual(clicks['typewriter'].get_volume(), clicks['ui_click'].get_volume())
                    else:
                        self.assertEqual(clicks['typewriter'].get_volume(), 0)
            with patch.object(sound_manager, '_sfx_volume', 0), patch.object(sound_manager, '_typewriter_volume', 1):
                sound_manager._apply_sfx_volume()
                self.assertEqual(clicks['ui_click'].get_volume(), 0)
                self.assertGreater(clicks['typewriter'].get_volume(), 0)
            with patch.object(sound_manager, '_sfx_volume', 1), patch.object(sound_manager, '_typewriter_volume', 0):
                sound_manager._apply_sfx_volume()
                self.assertGreater(clicks['ui_click'].get_volume(), 0)
                self.assertEqual(clicks['typewriter'].get_volume(), 0)

    def test_old_preferences_inherit_then_save_an_independent_typing_volume(self):
        with patch.multiple(sound_manager, _bgm_volume=1.0, _sfx_volume=1.0, _typewriter_volume=1.0):
            for old_volume in (0.0, .4, 1.0):
                with patch('settings_manager.load_settings', return_value={'sfx_volume': old_volume}):
                    sound_manager._load_volumes()
                    self.assertEqual(sound_manager.get_typewriter_volume(), old_volume)
            with patch('settings_manager.save_settings') as save, patch.object(sound_manager, '_apply_sfx_volume'):
                sound_manager.set_typewriter_volume(.3)
                saved = save.call_args.args[0]
                self.assertAlmostEqual(saved['typewriter_volume'], .3)
                self.assertEqual(sound_manager.get_sfx_volume(), 1)
            saved['sfx_volume'] = .8
            with patch('settings_manager.load_settings', return_value=saved):
                sound_manager._load_volumes()
                self.assertAlmostEqual(sound_manager.get_typewriter_volume(), .3)
                self.assertAlmostEqual(sound_manager.get_sfx_volume(), .8)

    def test_loading_story_uses_current_preference_in_both_directions(self):
        for current in (False, True):
            with self.subTest(current=current), patch('settings_manager.load_settings', return_value={'typewriter_enabled': current}), patch('settings_manager.save_settings') as write:
                saved = {'typewriter_enabled': not current,
                         'active_entry': {'text': '正在閱讀'}, 'active_progress': 2}
                text_log.load_state(saved)
                self.assertEqual(text_log.is_typewriter_enabled(), current)
                self.assertEqual(text_log.is_typewriter_animating(), current)
                if not current:
                    self.assertEqual(text_log.log_history[-1].text, '正在閱讀')
                write.assert_not_called()

    def test_preview_is_short_replaces_pending_ticks_and_respects_mute_and_focus(self):
        from unittest.mock import Mock
        tick = Mock()
        with patch.object(sound_manager, '_sfx_cache', {'typewriter': tick}), patch.object(sound_manager, '_typewriter_volume', 1), patch.object(sound_manager, '_paused', False), patch.object(sound_manager, '_bgm_fade_state', None), patch('pygame.mixer.get_init', return_value=(44100, -16, 2)), patch('pygame.mixer.pause') as pause, patch('pygame.mixer.music.pause'), patch('pygame.mixer.unpause') as resume, patch('pygame.mixer.music.unpause'):
            self.addCleanup(sound_manager.cancel_typewriter_preview)
            sound_manager.preview_typewriter()
            sound_manager.update(.04)
            sound_manager.preview_typewriter()
            for _ in range(30):
                sound_manager.update(.02)
            self.assertEqual(tick.play.call_count, 3)
            sound_manager._typewriter_volume = 0
            sound_manager.preview_typewriter()
            sound_manager.update(1)
            self.assertEqual(tick.play.call_count, 3)
            sound_manager._typewriter_volume = 1
            sound_manager.preview_typewriter()
            sound_manager.set_paused(True)
            sound_manager.update(10)
            sound_manager.play_sfx('typewriter')
            self.assertEqual(tick.play.call_count, 3)
            pause.assert_called_once()
            sound_manager.set_paused(False)
            sound_manager.update(1)
            self.assertEqual(tick.play.call_count, 3, 'Returning to the game must not replay queued preview sounds')
            resume.assert_called_once()
