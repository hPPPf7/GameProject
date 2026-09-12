"""Run with: python -m unittest discover -s tests"""

import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

from sprite_sheet import Playback, SheetSettings, SpriteSheet, settings_path


class SpriteSheetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "walk.png"
        image = pygame.Surface((48, 32), pygame.SRCALPHA)
        # Six identifiable silhouettes with different foot positions and alpha noise.
        for index in range(6):
            x, y = (index % 3) * 16, (index // 3) * 16
            image.fill((30 + index * 30, 80, 120, 255), (x + 5, y + 3, 5, 8 + index % 3))
            image.set_at((x, y), (80, 80, 80, 1))
        pygame.image.save(image, str(self.path))

    def write_settings(self, **overrides):
        data = {"columns": 3, "rows": 2, "fps": 10, "frame_order": [1, 2, 3, 4, 5, 6], "offsets": {}}
        data.update(overrides)
        settings_path(self.path).write_text(json.dumps(data), encoding="utf-8")

    def test_default_sheet_preserves_alpha_and_reads_rows_in_order(self):
        sheet = SpriteSheet.load(self.path)
        self.assertEqual(sheet.frame_size, (16, 16))
        self.assertEqual(sheet.settings.fps, 10)
        self.assertEqual([sheet.frame(i).get_at((6, 5)).r for i in range(1, 7)], [30, 60, 90, 120, 150, 180])
        self.assertEqual(sheet.frame(1).get_at((15, 15)).a, 0)

    def test_saved_order_and_offsets_are_used_by_game_scaled_frames(self):
        self.write_settings(fps=6, frame_order=[6, 1, 6, 2], offsets={"6": [2, -1]})
        sheet = SpriteSheet.load(self.path)
        frames = sheet.scaled_frames(16)
        self.assertEqual(sheet.settings.fps, 6)
        self.assertEqual(len(frames), 4)
        self.assertEqual(frames[0].get_at((7, 2)), (180, 80, 120, 255))
        self.assertEqual(frames[0].get_at((5, 3)).a, 0)
        self.assertEqual(pygame.image.tobytes(frames[0], "RGBA"), pygame.image.tobytes(frames[2], "RGBA"))
        self.assertEqual(frames[1].get_at((6, 5)).r, 30)

    def test_save_round_trip_keeps_original_image_unchanged(self):
        before = hashlib.sha256(self.path.read_bytes()).hexdigest()
        sheet = SpriteSheet.load(self.path)
        sheet.settings.fps = 4.5
        sheet.settings.frame_order = [2, 3, 2, 1]
        sheet.settings.offsets[2] = (-2, 1)
        sheet.save()
        reloaded = SpriteSheet.load(self.path)
        self.assertEqual(reloaded.settings.to_dict(), sheet.settings.to_dict())
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(), before)
        self.assertFalse(settings_path(self.path).with_suffix(".json.tmp").exists())

    def test_alignment_ignores_alpha_noise_and_preserves_horizontal_offsets(self):
        sheet = SpriteSheet.load(self.path)
        sheet.settings.offsets[2] = (2, 0)
        sheet.align_feet(1)
        self.assertEqual(sheet.settings.offsets[2][0], 2)
        bottoms = [sheet.bounds(number).bottom + sheet.settings.offsets[number][1] for number in range(1, 7)]
        self.assertEqual(bottoms, [11] * 6)
        self.assertFalse(any(sheet.clipped(number) for number in range(1, 7)))
        sheet.settings.offsets[1] = (-9, 0)
        self.assertTrue(sheet.clipped(1))

    def test_invalid_layout_and_settings_report_errors(self):
        with self.assertRaisesRegex(ValueError, "無法平均切成"):
            SpriteSheet.load(self.path, columns=5, rows=2)
        for invalid in ({"fps": 0}, {"fps": float("nan")}, {"frame_order": [0, 7]}, {"columns": 0}, {"offsets": {"1": [0.5, 1]}}):
            with self.subTest(invalid=invalid):
                self.write_settings(**invalid)
                with self.assertRaises(ValueError):
                    SpriteSheet.load(self.path)

    def test_grid_limit_is_explicit(self):
        with self.assertRaisesRegex(ValueError, "256"):
            SheetSettings(columns=64, rows=64).validate()

    def test_independent_regions_keep_pixels_across_nominal_grid_boundaries(self):
        # The first pose crosses the regular x=24 boundary; the next pose starts at 34.
        image = pygame.Surface((48, 32), pygame.SRCALPHA)
        image.fill((200, 50, 30, 255), (20, 8, 8, 12))
        image.fill((30, 80, 200, 255), (35, 13, 7, 9))
        pygame.image.save(image, str(self.path))
        self.write_settings(
            columns=2, rows=1, frame_order=[2, 1],
            frame_rects=[[16, 4, 16, 20], [34, 10, 12, 16]],
            canvas_size=[24, 24], offsets={"1": [1, 2], "2": [3, 1]},
        )
        sheet = SpriteSheet.load(self.path)
        self.assertEqual(sheet.frame_size, (24, 24))
        self.assertEqual(pygame.mask.from_surface(sheet.frame(1)).count(), 96)
        self.assertEqual(pygame.mask.from_surface(sheet.frame(2)).count(), 63)
        self.assertEqual(sheet.frame(1).get_at((12, 17)), (200, 50, 30, 255))
        self.assertEqual(sheet.frame(2).get_at((4, 4)), (30, 80, 200, 255))
        sheet.settings.fps = 15
        sheet.save()
        reloaded = SpriteSheet.load(self.path)
        self.assertEqual(reloaded.settings.to_dict(), sheet.settings.to_dict())
        self.assertEqual(pygame.image.tobytes(reloaded.frame(1), "RGBA"), pygame.image.tobytes(sheet.frame(1), "RGBA"))

    def test_invalid_independent_regions_are_rejected(self):
        base = {"columns": 1, "rows": 1, "frame_order": [1], "frame_rects": [[0, 0, 12, 12]], "canvas_size": [16, 16]}
        for changes in (
            {"canvas_size": None}, {"frame_rects": []}, {"canvas_size": [8, 8]},
            {"frame_rects": [[-1, 0, 12, 12]]}, {"frame_rects": [[45, 0, 12, 12]]},
        ):
            with self.subTest(changes=changes):
                self.write_settings(**(base | changes))
                with self.assertRaises(ValueError):
                    SpriteSheet.load(self.path)


class PlaybackTests(unittest.TestCase):
    def test_elapsed_time_can_advance_multiple_frames_without_slowing_animation(self):
        playback = Playback([1, 2, 3, 4, 5, 6])
        playback.advance(0.45, 10)
        self.assertEqual(playback.current, 5)
        playback.advance(0.15, 10)
        self.assertEqual(playback.current, 1)
        self.assertAlmostEqual(playback.elapsed, 0)

    def test_manual_step_wraps_and_repeated_frames_hold(self):
        playback = Playback([1, 2, 2, 3])
        playback.advance(0.1, 10)
        self.assertEqual(playback.current, 2)
        playback.advance(0.1, 10)
        self.assertEqual(playback.current, 2)
        playback.step(1)
        self.assertEqual(playback.current, 3)
        playback.step(1)
        self.assertEqual(playback.current, 1)
        playback.step(-1)
        self.assertEqual(playback.current, 3)


if __name__ == "__main__":
    unittest.main()
