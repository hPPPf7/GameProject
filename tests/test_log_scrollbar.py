import unittest
from unittest.mock import patch
import pygame
import text_log
from log_scrollbar import LogScrollbar, get_log_viewport


class LogScrollbarTests(unittest.TestCase):
    def setUp(self):
        pygame.font.init()
        self.font = pygame.font.Font(None, 20)
        self.settings = patch('settings_manager.load_settings', return_value={})
        self.settings.start()
        self.addCleanup(self.settings.stop)
        text_log.reset()
        text_log.set_typewriter_override(False)
        text_log.set_history([{'text': f'Line {i:02}'} for i in range(40)])
        self.rect = pygame.Rect(32, 400, 448, 160)

    def view(self):
        return get_log_viewport(self.rect, self.font)

    def test_drag_reaches_first_and_last_lines_in_cinematic_layout(self):
        bar = LogScrollbar()
        view = self.view()
        self.assertEqual(view.visible_lines, 5)
        self.assertEqual(view.maximum, 35)
        self.assertEqual(view.thumb.bottom, view.track.bottom)
        bar.begin(view.thumb.center, view, self.font, ('touch', 1))
        self.assertFalse(bar.move((0, 0), view, self.font, ('touch', 2)))
        bar.move((view.thumb.centerx, 0), view, self.font, ('touch', 1))
        view = self.view()
        self.assertEqual(view.offset, view.maximum)
        self.assertEqual(text_log.get_visible_lines(self.font, view.text_width, view.visible_lines)[0][0], 'Line 00')
        bar.move((view.thumb.centerx, 999), view, self.font, ('touch', 1))
        self.assertEqual(text_log.log_offset, 0)
        self.assertFalse(bar.release(('touch', 2)))
        self.assertTrue(bar.release(('touch', 1)))

    def test_arrows_page_click_and_reset_use_actual_visible_count(self):
        bar = LogScrollbar()
        view = self.view()
        bar.begin((view.hit_area.centerx, view.hit_area.top + 2), view, self.font, 'mouse')
        self.assertEqual(text_log.log_offset, 1)
        bar.release('mouse')
        view = self.view()
        bar.begin((view.hit_area.centerx, view.track.top + 4), view, self.font, 'mouse')
        self.assertEqual(text_log.log_offset, 6)
        text_log.set_history([{'text': 'short'}])
        view = self.view()
        self.assertEqual(view.maximum, 0)
        self.assertFalse(bar.begin(view.hit_area.center, view, self.font, 'mouse'))

    def test_typewriter_counts_match_rendering_without_changing_wrap_width(self):
        text_log.clear_history()
        text_log.set_typewriter_override(True)
        text_log.add('abc\n' * 20)
        width = self.view().text_width
        self.assertEqual(self.view().maximum, 0)
        text_log.update_typewriter(1)
        view = self.view()
        self.assertEqual(view.text_width, width)
        self.assertGreater(view.maximum, 0)
        text_log.set_scroll_offset(999, self.font, width, view.visible_lines)
        self.assertEqual(self.view().offset, view.maximum)
        self.assertEqual(len(text_log.get_visible_lines(self.font, width, view.visible_lines)), view.visible_lines)

    def test_history_stays_put_during_typing_completion_and_queued_rewards(self):
        text_log.set_typewriter_override(True)
        text_log.add('New line\n' * 30)
        reward = []
        text_log.add('Reward', category='system', on_show=lambda: reward.append('item'))
        view = self.view()
        text_log.set_scroll_offset(999, self.font, view.text_width, view.visible_lines)
        def first_line():
            view = self.view()
            return text_log.get_visible_lines(self.font, view.text_width, view.visible_lines)[0][0]
        self.assertEqual(first_line(), 'Line 00')
        for dt in (.5, .5, 20):
            text_log.update_typewriter(dt)
            self.assertEqual(first_line(), 'Line 00')
        self.assertEqual(reward, ['item'])
        self.assertGreater(self.view().offset, 0)
        text_log.scroll_to_bottom()
        text_log.add('Latest', category='system')
        self.assertEqual(self.view().offset, 0)

    def test_saved_reading_position_survives_loading_and_finishing_text(self):
        text_log.set_typewriter_override(True)
        text_log.add('New line\n' * 20)
        view = self.view()
        text_log.set_scroll_offset(10, self.font, view.text_width, view.visible_lines)
        before = text_log.get_visible_lines(self.font, view.text_width, view.visible_lines)
        saved = text_log.export_state()
        text_log.load_state(saved)
        text_log.finish_typewriter()
        self.assertEqual(text_log.get_visible_lines(self.font, view.text_width, view.visible_lines), before)

    def test_footer_does_not_cover_text_or_change_geometry_when_scrolling(self):
        view = self.view()
        last_line_bottom = view.text_rect.top + 8 + (view.visible_lines - 1) * 24 + self.font.get_height()
        self.assertLessEqual(last_line_bottom, view.footer.top)
        text_log.set_scroll_offset(5, self.font, view.text_width, view.visible_lines)
        self.assertEqual(view.footer, self.view().footer)
        self.assertFalse(view.latest_button.colliderect(view.hit_area))
