from pathlib import Path
import subprocess
import sys
import unittest


class GameplayFlowTests(unittest.TestCase):
    def test_desktop_and_touch_controls_in_real_game_loop(self):
        root = Path(__file__).resolve().parents[1]
        for args in ([], ['--mobile']):
            with self.subTest(input=args or 'mouse'):
                result = subprocess.run(
                    [sys.executable, '-B', str(root / 'tests' / 'gameplay_flow_scenario.py'), *args],
                    cwd=root, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=40,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
