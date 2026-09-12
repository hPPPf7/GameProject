import unittest
import pygame
from combat_feedback import CombatFeedback


class CombatFeedbackTests(unittest.TestCase):
    def test_pause_consumes_time_and_defeat_fades_without_modifying_source(self):
        effect = CombatFeedback()
        source = pygame.Surface((20, 20), pygame.SRCALPHA)
        source.fill((40, 80, 120, 255), (4, 4, 10, 10))
        original = pygame.image.tobytes(source, "RGBA")
        effect.start("victory")
        self.assertEqual(effect.update(.02), 0)
        self.assertAlmostEqual(effect.update(.05), .025)
        flash, _ = effect.sprite(source, "enemy")
        self.assertGreater(flash.get_at((5, 5)).r, source.get_at((5, 5)).r)
        self.assertEqual(flash.get_at((0, 0)).a, 0)
        effect.update(.6)
        vanished, _ = effect.sprite(source, "enemy")
        self.assertEqual(vanished.get_alpha(), 0)
        self.assertEqual(pygame.image.tobytes(source, "RGBA"), original)
        effect.reset()
        restored, _ = effect.sprite(source, "enemy")
        self.assertIs(restored, source)
