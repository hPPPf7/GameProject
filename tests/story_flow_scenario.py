"""Render and select real endings, and resume revised scenes from temporary saves."""
import copy
import inspect
import os
from pathlib import Path
import runpy
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def scenario(g, pygame):
    import event_manager as events

    log = g['text_log']
    save = g['save_manager']
    present = g['present_game_surface']

    def capture(*args, **kwargs):
        g['_story_frame'] = g['game_surface'].copy()
        present(*args, **kwargs)

    g['present_game_surface'] = capture

    def click(rect):
        view = g['get_render_viewport']()
        pos = (round(view.x + rect.centerx * view.w / g['SCREEN_WIDTH']),
               round(view.y + rect.centery * view.h / g['SCREEN_HEIGHT']))
        return [pygame.event.Event(kind, button=1, pos=pos)
                for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP)]

    def wait(frames=4):
        for _ in range(frames):
            log.finish_typewriter()
            yield []

    def screenshot(name):
        if os.environ.get('STORY_REVIEW_ARTIFACTS'):
            dest = Path(os.environ['STORY_REVIEW_ARTIFACTS'])
            dest.mkdir(parents=True, exist_ok=True)
            pygame.image.save(g['_story_frame'], str(dest / f'{name}.png'))

    for fate, name in ((20, '理性結局'), (50, '正常結局'), (80, '荒謬結局')):
        for index in range(3):
            g['reset_action_playback']()
            player = g['init_player_state']()
            player.update(chapter=5, fate=fate, flags={'accepted_id': True, '回家': True})
            event = events._resolve_event_variants(events.get_event_by_id(name), player)
            g.update(player=player, current_event=event, game_state='main_screen', sub_state='show_event',
                     current_background_name=event['background'], ending_fade_alpha=0, intro_fade_alpha=0)
            g['update_enemy_visuals'](event)
            log.clear_history()
            log.start_event(name)
            log.add(event['text'])

            # Old saves contain the old resolved text/options; reload must replace them.
            if index == 0:
                event['revision'] = 0
                event['text'] = '舊版開場'
                log.clear_history()
                log.start_event(name)
                log.add(event['text'])
                log.finish_typewriter()
                payload = g['game_state_payload']()
                save.save_game(payload)
                assert g['load_saved_adventure']()
                event = g['current_event']
                player = g['player']
                assert '舊版開場' not in [entry.text for entry in log.log_history]
                assert event['text'] in [entry.text for entry in log.log_history]
            yield from wait()
            screenshot(f'{name}_選擇')
            rect = g['get_option_rects'](g['sub_state'], event, player)[index]
            yield click(rect)
            yield from wait()
            expected = event['options'][index]['result']['ending_segments']
            assert g['sub_state'] == 'ending' and player['ending_segments'] == expected
            player['layout_transition'] = {'progress': 1.0}
            for segment_index in range(len(expected)):
                yield from wait()
                assert expected[segment_index] in [entry.text for entry in log.log_history]
                if segment_index == 1:
                    # A cinematic already in progress must resume its exact saved text.
                    payload = g['game_state_payload']()
                    old_segments = copy.deepcopy(player['ending_segments'])
                    payload['current_event']['revision'] = 0
                    save.save_game(payload)
                    assert g['load_saved_adventure']()
                    player = g['player']
                    assert player['ending_segments'] == old_segments
                    assert player['ending_segment_index'] == segment_index + 1
                if segment_index < len(expected) - 1:
                    assert g['advance_ending_segment']()
            screenshot(f'{name}_{index + 1}_收尾')
            assert not g['advance_ending_segment']()
            view = g['get_log_viewport'](g['get_areas_for_mode'](player)['log'], g['FONT'])
            yield click(view.footer)
            assert player['ending_exit_started']

    # A pending legacy chapter exit may not bypass the core on load.
    g['reset_action_playback']()
    player = g['init_player_state']()
    player.update(chapter=4, consumed_events={'終章自問'})
    event = events._resolve_event_variants(events.get_event_by_id('終章自問'), player)
    save.save_game({'player': player, 'current_event': event, 'sub_state': 'show_event'})
    assert g['load_saved_adventure']()
    assert g['current_event']['id'] == '核心機組啟動'
    assert g['current_background_name'] == 'research_core.png'
    yield from wait()
    screenshot('舊存檔_補上核心選擇')

    # Refreshing the same event ID must also discard its saved, obsolete background.
    for name, old_background in (('核心機組啟動', 'bg029.png'), ('變異體暴走', 'bg033.png')):
        player = g['init_player_state']()
        player.update(chapter=4, flags={'visited_outpost': True})
        if name == '變異體暴走':
            player['flags']['accepted_id'] = True
        event = events._resolve_event_variants(events.get_event_by_id(name), player)
        event.update(revision=0, background=old_background)
        save.save_game({'player': player, 'current_event': event, 'sub_state': 'show_event',
                        'current_background_name': old_background})
        assert g['load_saved_adventure']()
        assert g['current_event']['id'] == name
        assert g['current_background_name'] == 'research_core.png', (name, g['current_background_name'])
    assert not list(save._save_file().parent.glob('*.bak'))
    yield [pygame.event.Event(pygame.QUIT)]


def main():
    with tempfile.TemporaryDirectory(prefix='story_flow_') as data:
        os.environ.update(LOCALAPPDATA=data, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy', PYGAME_HIDE_SUPPORT_PROMPT='1')
        import pygame

        elapsed = 0

        class Clock:
            def tick(self, fps):
                nonlocal elapsed
                elapsed += 17
                return 17

        driver = None
        frames = 0

        def inputs():
            nonlocal driver, frames
            frames += 1
            assert frames < 800, 'Story scenario did not complete'
            if driver is None:
                driver = scenario(inspect.currentframe().f_back.f_globals, pygame)
            return next(driver)

        with patch('pygame.event.get', inputs), patch('pygame.time.Clock', Clock), patch('pygame.time.get_ticks', lambda: elapsed):
            try:
                runpy.run_path(str(ROOT / 'main.py'), run_name='__main__')
            except SystemExit as exc:
                assert exc.code in (None, 0)
    print('PASS: all nine ending choices, segment playback, revised saves and missing core recovery')


if __name__ == '__main__':
    main()
