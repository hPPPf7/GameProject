import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import save_manager
from battle_system import EnemyState, get_battle_state, perform_battle_action


class BattleSaveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "save.json"
        patcher = patch("save_manager._save_file", return_value=self.path)
        patcher.start()
        self.addCleanup(patcher.stop)
        audio = patch("sound_manager.play_sfx")
        audio.start()
        self.addCleanup(audio.stop)

    def player(self, enemy):
        return {"consumed_events": {"intro"}, "battle_state": {
            "enemy": enemy, "active": True, "durability": 3, "max_durability": 3,
            "turn_count": 0, "attack_attempts": 0, "max_turns": 3,
        }}

    def test_save_reload_and_win_including_quotes_in_enemy_name(self):
        name = "敵人 'A' \"B\""
        save_manager.save_game({"player": self.player(EnemyState(name))})
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(raw["player"]["battle_state"]["enemy"], {"name": name})
        loaded = save_manager.load_game()["player"]
        self.assertEqual(loaded["consumed_events"], {"intro"})
        outcome = perform_battle_action(loaded, "attack", {"attack_chance": 1})
        self.assertTrue(outcome["victory"])
        self.assertIn(name, outcome["messages"][0])
        self.assertEqual(loaded["battle_state"]["turn_count"], 1)

    def test_legacy_repr_and_dict_saves_continue_a_battle(self):
        for enemy in ("EnemyState(name='野豬')", {"name": "野豬"}, "野豬"):
            with self.subTest(enemy=enemy):
                self.path.write_text(json.dumps({"player": self.player(enemy)}, default=list), encoding="utf-8")
                loaded = save_manager.load_game()["player"]
                self.assertEqual(get_battle_state(loaded)["enemy"].name, "野豬")
                outcome = perform_battle_action(loaded, "attack", {"attack_chance": 1})
                self.assertTrue(outcome["victory"])

    def test_legacy_value_is_never_executed_and_invalid_save_is_ignored(self):
        enemy = EnemyState.from_saved("EnemyState(name=__import__('os').getcwd())")
        self.assertEqual(enemy.name, "未知生物")
        for value in ([], 1, None, {"player": "broken"}):
            self.path.write_text(json.dumps(value), encoding="utf-8")
            self.assertIsNone(save_manager.load_game())
