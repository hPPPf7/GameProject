import unittest
import pygame
from combat_feedback import CombatFeedback
from ui_effects import UIFeedback, CampfireAtmosphere
from ui_theme import draw_button_face, shake_scene


class InterfaceEffectsTests(unittest.TestCase):
    def test_loading_and_reordering_do_not_look_like_new_rewards(self):
        effect = UIFeedback()
        player = {'inventory': ['stone', 'report'], 'battle_state': {'event_id': 'boar', 'durability': 3}}
        effect.observe(player)
        self.assertFalse(effect.item_times)
        player['inventory'].reverse()
        effect.observe(player)
        self.assertFalse(effect.item_times)
        player['inventory'].append('stone')
        player['battle_state']['durability'] = 2
        effect.observe(player)
        self.assertEqual(set(effect.item_times), {2})
        self.assertEqual(effect.durability_delta, -1)
        effect.update_player(.1)
        effect.observe(player)
        self.assertLess(effect.durability_time, .75, 'Rendering the same result must not retrigger its flash')
        effect.reset_player()
        effect.observe(player)
        self.assertFalse(effect.item_times)
        self.assertEqual(effect.durability_time, 0)

    def test_inventory_overflow_pulses_and_animations_finish(self):
        effect = UIFeedback()
        player = {'inventory': list('abcdef')}
        effect.observe(player)
        player['inventory'].append('g')
        effect.observe(player)
        self.assertGreater(effect.item_pulse(5, overflow=True)[0], 0)
        self.assertEqual(effect.item_pulse(0), (0, 0))
        effect.update_player(1)
        self.assertEqual(effect.item_pulse(5, overflow=True), (0, 0))

    def test_scene_shake_never_moves_ui_or_leaves_bare_edges(self):
        screen = pygame.Surface((80, 80))
        screen.fill((11, 22, 33))
        area = pygame.Rect(10, 10, 50, 40)
        screen.fill((100, 110, 120), area)
        screen.set_at((30, 30), (255, 50, 60))
        for offset in ((3, -2), (-5, 2)):
            with self.subTest(offset=offset):
                result = screen.copy()
                shake_scene(result, area, offset)
                self.assertEqual(result.get_at((30 + offset[0], 30 + offset[1])), (255, 50, 60, 255))
                for y in range(80):
                    for x in range(80):
                        if not area.collidepoint(x, y):
                            self.assertEqual(result.get_at((x, y)), screen.get_at((x, y)))
                self.assertEqual(result.get_at(area.topleft), (100, 110, 120, 255))
        off = screen.copy()
        shake_scene(off, area, (0, 0))
        self.assertEqual(pygame.image.tobytes(off, 'RGB'), pygame.image.tobytes(screen, 'RGB'))

    def test_shake_strength_is_bounded_and_off_preserves_combat_feedback(self):
        effect = CombatFeedback('normal')
        effect.start('victory')
        self.assertNotEqual(effect.camera_offset(), (0, 0))
        for _ in range(40):
            x, y = effect.camera_offset()
            self.assertIsInstance(x, int)
            self.assertLessEqual(abs(x), 5)
            self.assertLessEqual(abs(y), 3)
            effect.update(.01)
        self.assertEqual(effect.camera_offset(), (0, 0))
        effect.set_shake_level('off')
        effect.start('hurt')
        self.assertEqual(effect.camera_offset(), (0, 0))
        self.assertEqual(effect.update(.02), 0, 'Disabling camera shake must retain impact timing')
        effect.set_shake_level([])
        self.assertEqual(effect.shake_level, 'weak')

    def test_button_press_keeps_hit_area_and_panel_texture_stable(self):
        rect = pygame.Rect(8, 8, 120, 40)
        original = rect.copy()
        surface = pygame.Surface((140, 60))
        normal = draw_button_face(surface, rect)
        pixels = pygame.image.tobytes(surface, 'RGB')
        draw_button_face(surface, rect)
        self.assertEqual(pixels, pygame.image.tobytes(surface, 'RGB'))
        pressed = draw_button_face(surface, rect, pressed=True)
        self.assertEqual(rect, original)
        self.assertEqual(pressed.y, normal.y + 1)
        feedback = UIFeedback()
        feedback.press(rect)
        self.assertTrue(feedback.button_state(rect)[1])
        for _ in range(4):
            feedback.update_ui(.05, True)
        self.assertFalse(feedback.button_state(rect)[1])
        self.assertEqual(feedback.modal_progress, 1)
        feedback.update_ui(.05, False)
        self.assertGreater(feedback.modal_progress, 0)
        feedback.update_ui(.05, False)
        self.assertEqual(feedback.modal_progress, 0)

    def test_menu_effect_stays_local_and_does_not_modify_background(self):
        background = pygame.Surface((512, 847))
        background.fill((15, 25, 35))
        source = pygame.image.tobytes(background, 'RGB')
        atmosphere = CampfireAtmosphere()
        first = background.copy()
        atmosphere.draw(first, pygame.Rect(-256, -88, 1024, 1024))
        for _ in range(10):
            atmosphere.update(.1)
        second = background.copy()
        atmosphere.draw(second, pygame.Rect(-256, -88, 1024, 1024))
        self.assertNotEqual(pygame.image.tobytes(first, 'RGB'), pygame.image.tobytes(second, 'RGB'))
        self.assertEqual(pygame.image.tobytes(background, 'RGB'), source)
        self.assertEqual(first.get_at((10, 10)), background.get_at((10, 10)))
