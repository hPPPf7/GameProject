"""Resize geometry and native Windows callback regression checks."""

from pathlib import Path
import subprocess
import sys
import unittest

from window_resize import constrain_drag_rect


class AspectResizeTests(unittest.TestCase):
    base = (512, 847)
    minimum = (307, 508)

    def test_all_handles_preserve_client_ratio_and_opposite_anchor(self):
        for frame in ((16, 39), (24, 58)):
            for edge in range(1, 9):
                with self.subTest(frame=frame, edge=edge):
                    source = (-500, 100, 100, 800)
                    left, top, right, bottom = constrain_drag_rect(source, edge, self.base, self.minimum, frame)
                    width, height = right - left - frame[0], bottom - top - frame[1]
                    self.assertAlmostEqual(width / 512, height / 847, delta=1 / 512)
                    if edge in (1, 4, 7):
                        self.assertEqual(right, source[2])
                    if edge in (2, 5, 8):
                        self.assertEqual(left, source[0])
                    if edge in (3, 4, 5):
                        self.assertEqual(bottom, source[3])
                    if edge in (6, 7, 8):
                        self.assertEqual(top, source[1])
                    if edge in (1, 2):
                        self.assertAlmostEqual((top + bottom) / 2, (source[1] + source[3]) / 2, delta=.5)
                    if edge in (3, 6):
                        self.assertAlmostEqual((left + right) / 2, (source[0] + source[2]) / 2, delta=.5)

    def test_minimum_remains_proportional_for_every_handle(self):
        for edge in range(1, 9):
            with self.subTest(edge=edge):
                left, top, right, bottom = constrain_drag_rect((10, 20, 35, 55), edge, self.base, self.minimum, (16, 39))
                self.assertGreaterEqual(right - left - 16, self.minimum[0])
                self.assertGreaterEqual(bottom - top - 39, self.minimum[1])
                self.assertAlmostEqual((right - left - 16) / 512, (bottom - top - 39) / 847, delta=1 / 512)

    def test_drag_near_original_size_is_continuous_without_snap_band(self):
        sizes = []
        for width in range(488, 537):
            left, top, right, bottom = constrain_drag_rect((0, 0, width, 847), 2, self.base, self.minimum)
            sizes.append((right - left, bottom - top))
        self.assertEqual(len(set(sizes)), 49)
        for first, second in zip(sizes, sizes[1:]):
            self.assertEqual(second[0] - first[0], 1)
            self.assertIn(second[1] - first[1], (1, 2))

    def test_system_maximum_cannot_clip_only_one_dimension(self):
        for edge in range(1, 9):
            with self.subTest(edge=edge):
                left, top, right, bottom = constrain_drag_rect(
                    (0, 0, 1800, 2500), edge, self.base, self.minimum, (16, 39), (1920, 1061),
                )
                width, height = right - left - 16, bottom - top - 39
                self.assertLessEqual(width, 1920)
                self.assertLessEqual(height, 1061)
                self.assertAlmostEqual(width / 512, height / 847, delta=1 / 512)

    @unittest.skipUnless(sys.platform == "win32", "Requires a native Windows window")
    def test_native_hidden_window_resize_and_callback_cleanup(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, "-B", str(root / "tests/window_resize_scenario.py")],
            cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
