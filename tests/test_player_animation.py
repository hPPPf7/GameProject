"""Animation switching must preserve combat and scene-transition completion."""

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame


class PlayerAnimationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((512, 847))
        from player_animation import PlayerAnimator
        cls.animator_class = PlayerAnimator

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.animator = self.animator_class()
        self.sfx = patch("sound_manager.play_sfx").start()
        self.addCleanup(patch.stopall)

    def test_default_and_invalid_saved_styles_use_original_frames(self):
        from paths import res_path
        from sprite_sheet import SpriteSheet
        a = self.animator
        self.assertEqual(a.style, "2d")
        self.assertEqual([len(a.idle_frames), len(a.walk_frames), len(a.attack_frames)], [2, 6, 9])
        original = SpriteSheet.load(res_path("assets", "sprite_sheet", "player_walk.png")).scaled_frames(96)
        self.assertEqual(
            [pygame.image.tobytes(f, "RGBA") for f in a.walk_frames],
            [pygame.image.tobytes(f, "RGBA") for f in original],
        )
        for bad in ("unknown", None, []):
            with self.subTest(style=bad):
                self.assertEqual(self.animator_class(style=bad).style, "2d")

    def test_switch_back_restores_original_bank_and_timing(self):
        a = self.animator
        originals = (a.idle_frames, a.walk_frames, a.attack_frames)
        a.request_style("3d")
        self.assertEqual([len(a.idle_frames), len(a.walk_frames), len(a.attack_frames)], [8, 8, 15])
        for clip in (a.idle_frames, a.walk_frames, a.attack_frames):
            self.assertTrue(all(f.get_size() == (128, 96) for f in clip))
            self.assertTrue(all(f.get_at((0, 0)).a == 0 for f in clip))
            self.assertTrue(all(pygame.Rect(1, 1, 126, 94).contains(f.get_bounding_rect(128)) for f in clip))
        self.assertAlmostEqual(a.attack_frame_time, 1 / 15)
        a.request_style("2d")
        for restored, original in zip((a.idle_frames, a.walk_frames, a.attack_frames), originals):
            self.assertIs(restored, original)
        self.assertAlmostEqual(a.attack_frame_time, 1 / 12)

    def test_walk_switch_waits_through_fade_and_emits_completion(self):
        a = self.animator
        a.start_walk()
        a.update(.2)
        progress = a.walk_progress
        position = a.position[:]
        a.request_style("3d")
        self.assertEqual(a.style, "2d")
        self.assertEqual(a.walk_progress, progress)
        self.assertEqual(a.position, position)
        for _ in range(100):
            a.update(.05)
            if a.walk_finished:
                break
        self.assertTrue(a.walk_finished)
        self.assertEqual(a.style, "3d")
        self.assertEqual(a.state, "idle")
        self.assertIsNone(a.fade_state)

    def test_attack_switch_preserves_completion_at_desktop_and_mobile_rates(self):
        for fps in (20, 60):
            for initial, target in (("3d", "2d"), ("2d", "3d")):
                with self.subTest(fps=fps, initial=initial):
                    a = self.animator_class(style=initial)
                    a.start_attack(enemy_width=100, enemy_position=(320, 200))
                    expected = a.attack_approach_duration + len(a.attack_frames) * a.attack_frame_time + a.attack_return_duration
                    a.request_style(target)
                    self.assertEqual(a.style, initial)
                    for tick in range(fps * 6):
                        a.update(1 / fps)
                        if a.attack_finished:
                            break
                        self.assertEqual(a.style, initial)
                    self.assertTrue(a.attack_finished)
                    self.assertEqual(a.style, target)
                    self.assertEqual(a.position, [a.idle_x, a.base_y])
                    self.assertAlmostEqual((tick + 1) / fps, expected, delta=3 / fps)
                    a.update(1 / fps)
                    self.assertFalse(a.attack_finished)

    def test_sword_sound_occurs_at_strike_once_even_when_frames_are_skipped(self):
        for style in ("2d", "3d"):
            with self.subTest(style=style):
                self.sfx.reset_mock()
                a = self.animator_class(style=style)
                a.start_attack()
                a.update(a.attack_approach_duration + .01)
                self.assertEqual(a.state, "attacking")
                self.sfx.assert_not_called()
                a.update(.2)
                self.sfx.assert_not_called()
                a.update(.3)
                self.sfx.assert_called_once_with("attack")
                a.update(.6)
                self.sfx.assert_called_once_with("attack")
                self.assertEqual(a.state, "attack_return")

    def test_movement_uses_distance_and_retreat_reverses_the_walk_cycle(self):
        a = self.animator
        a.start_attack(enemy_width=100, enemy_position=(250, 200))
        near_duration = a.attack_approach_duration
        near_distance = a.attack_target_x - a.idle_x
        a.start_attack(enemy_width=100, enemy_position=(350, 200))
        self.assertGreater(a.attack_approach_duration, near_duration)
        self.assertAlmostEqual(near_distance / near_duration, (a.attack_target_x - a.idle_x) / a.attack_approach_duration)
        a.update(a.attack_approach_duration + .001)
        a.update(len(a.attack_frames) * a.attack_frame_time + .001)
        before = a.position[0]
        a.update(a.walk_frame_time + .001)
        self.assertEqual(a.frame_index, len(a.walk_frames) - 1)
        self.assertLess(a.position[0], before)

    def test_hit_is_one_pulse_and_reset_clears_transient_state(self):
        a = self.animator
        a.start_attack()
        a.update(a.attack_approach_duration + .001)
        hits = 0
        for _ in range(150):
            a.update(.02)
            hits += a.attack_hit
            if a.attack_finished:
                break
        self.assertEqual(hits, 1)
        a.start_walk()
        a.update(.5)
        a.reset()
        self.assertEqual(a.state, "idle")
        self.assertEqual(a.position, [a.idle_x, a.base_y])
        self.assertFalse(a.attack_hit)
        self.assertIsNone(a.fade_state)

    def test_pending_switch_can_be_cancelled_and_locked_for_enemy_attack(self):
        a = self.animator
        a.style_locked = True
        a.request_style("3d")
        a.update(.1)
        self.assertEqual(a.style, "2d")
        self.assertEqual(a.selected_style, "3d")
        a.request_style("2d")
        self.assertIsNone(a.pending_style)
        a.request_style("3d")
        a.style_locked = False
        a.update(.1)
        self.assertEqual(a.style, "3d")

    def test_sword_reaches_enemy_silhouette_despite_transparent_margins(self):
        for style in ("2d", "3d"):
            with self.subTest(style=style):
                a = self.animator_class(style=style)
                enemy_bounds = pygame.Rect(30, 12, 50, 80)
                a.start_attack(enemy_width=120, enemy_position=(310, 200), enemy_bounds=enemy_bounds)
                reach = max(f.get_bounding_rect(128).right for f in a.attack_frames)
                self.assertEqual(a.attack_target_x + reach, 310 + enemy_bounds.left)

    def test_new_attack_keeps_feet_grounded_and_preserves_complete_silhouettes(self):
        from paths import res_path
        from sprite_sheet import SpriteSheet
        sheet = SpriteSheet.load(res_path("assets", "sprite_sheet", "player_attack.png"))
        self.assertEqual(sheet.image.get_size(), (1254, 1254))
        self.assertEqual(sheet.settings.frame_order, [1, 2, 3, 5, 4, 6, 7, 8, 9])
        for number in range(1, 10):
            with self.subTest(frame=number):
                original_mask = pygame.mask.from_surface(sheet.raw_frames[number - 1], 127)
                frame = sheet.frame(number)
                adjusted_mask = pygame.mask.from_surface(frame, 127)
                self.assertEqual(original_mask.count(), adjusted_mask.count())
                self.assertEqual(len(adjusted_mask.connected_components(100)), 1)
                self.assertFalse(sheet.clipped(number))
                self.assertEqual(frame.get_bounding_rect(128).bottom, 382)
        walk_floor = self.animator.walk_frames[0].get_bounding_rect(128).bottom
        for frame in self.animator.attack_frames:
            self.assertLessEqual(abs(frame.get_bounding_rect(128).bottom - walk_floor), 1)


if __name__ == "__main__":
    unittest.main()
