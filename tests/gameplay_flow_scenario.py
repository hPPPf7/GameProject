"""Exercise the real game loop with temporary saves and mouse or touch input."""
import inspect
import os
from pathlib import Path
import runpy
import sys
import tempfile
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
MOBILE = '--mobile' in sys.argv
ARTIFACTS = os.environ.get('GAME_REVIEW_ARTIFACTS')
elapsed = 0
next_frame_ms = 17


def scenario(g, pygame):
    global next_frame_ms
    log = g['text_log']
    audio = g['sound_manager']
    save = g['save_manager']
    if ARTIFACTS:
        present = g['present_game_surface']
        def capture():
            g['_review_rendered'] = g['game_surface'].copy()
            present()
        g['present_game_surface'] = capture

    def click(rect):
        x, y = rect.center
        viewport = g['get_render_viewport']()
        wx = viewport.x + x * viewport.w / g['SCREEN_WIDTH']
        wy = viewport.y + y * viewport.h / g['SCREEN_HEIGHT']
        if MOBILE:
            args = dict(x=wx / g['screen'].get_width(), y=wy / g['screen'].get_height(), finger_id=1)
            return [pygame.event.Event(kind, **args) for kind in (pygame.FINGERDOWN, pygame.FINGERUP)]
        return [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(round(wx), round(wy))),
                pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(round(wx), round(wy)))]

    def wait(frames=10):
        for _ in range(frames):
            yield []

    def screenshot(name):
        if ARTIFACTS:
            target = Path(ARTIFACTS)
            target.mkdir(parents=True, exist_ok=True)
            pygame.image.save(g['_review_rendered'], str(target / f'{name}_{"touch" if MOBILE else "desktop"}.png'))

    save.save_game({'player': {'chapter': 3}, 'review_marker': 'original'})
    original = save._save_file().read_bytes()
    g['has_save_file'] = True
    yield click(g['start_button'])
    yield from wait()
    assert g['dialog'].is_open and g['game_state'] == 'start_menu'
    assert save._save_file().read_bytes() == original
    screenshot('new_game_confirmation')
    yield click(g['dialog'].layout(g['SCREEN_RECT'])['cancel'])
    yield from wait()
    assert save._save_file().read_bytes() == original
    yield click(g['start_button'])
    yield from wait()
    yield click(g['settings_button'])  # Outside click cancels without opening settings.
    yield from wait()
    assert not g['show_settings_popup'] and save._save_file().read_bytes() == original
    yield click(g['start_button'])
    yield from wait()
    yield click(g['dialog'].layout(g['SCREEN_RECT'])['confirm'])
    assert g['game_state'] == 'main_screen' and not g['dialog'].is_open
    assert not save.has_save(), 'Only explicit confirmation may discard the old adventure'

    g['reset_action_playback']()
    g['intro_fade_alpha'] = 0
    g['player'] = g['init_player_state']()
    g['player']['inventory'] = ['奇怪的石頭', '草織護符', '塗黑報告']
    g['game_state'] = 'main_screen'
    g['sub_state'] = 'show_event'
    g['current_event'] = {'id': 'review', 'options': []}
    log.clear_history()
    log.set_typewriter_override(True)
    log.add('調查員正在閱讀這段緩慢出現的文字。' * 20)
    yield from wait()
    progress = log._active_progress
    items = list(g['player']['inventory'])
    history = log.export_state()
    yield click(g['get_inventory_slots'](g['player'])[0].rect)
    yield from wait()
    assert g['dialog'].kind == 'item' and g['dialog'].is_open
    assert log.export_state() == history and g['player']['inventory'] == items
    screenshot('item_details')
    yield click(g['dialog'].layout(g['SCREEN_RECT'])['next'])
    assert g['dialog'].item_index == 1
    yield [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)]
    yield from wait()
    assert g['game_state'] == 'main_screen' and not g['dialog'].is_open

    audio.set_typewriter_volume(1)
    audio.set_sfx_volume(.6)
    yield click(g['settings_button'])
    yield from wait()
    progress = log._active_progress
    tick = Mock(wraps=audio._sfx_cache['typewriter'])
    audio._sfx_cache['typewriter'] = tick
    controls = g['get_settings_layout'](True)
    yield click(controls['typewriter_down'])
    yield from wait(30)
    assert tick.play.call_count == 3 and log._active_progress == progress
    assert abs(audio.get_typewriter_volume() - .9) < 1e-6
    assert abs(audio.get_sfx_volume() - .6) < 1e-6
    yield click(controls['typewriter_up'])
    yield [pygame.event.Event(pygame.WINDOWFOCUSLOST)]
    fade_timer = audio._bgm_fade_timer
    yield from wait(60)
    assert audio._paused and audio._bgm_fade_timer == fade_timer
    assert log._active_progress == progress and tick.play.call_count == 3
    screenshot('focus_pause')
    next_frame_ms = 10_000
    yield [pygame.event.Event(pygame.WINDOWFOCUSGAINED)]
    assert not audio._paused and log._active_progress == progress
    assert g['show_settings_popup'], 'Returning focus must preserve an open settings dialog'
    yield click(controls['close'])
    yield from wait()
    assert log._active_progress > progress
    progress = log._active_progress
    yield [pygame.event.Event(pygame.WINDOWFOCUSLOST)]
    yield click(g['settings_button'])  # Background clicks must not reach the game.
    yield from wait(60)
    assert log._active_progress == progress and not g['show_settings_popup']
    next_frame_ms = 10_000
    yield [pygame.event.Event(pygame.WINDOWFOCUSGAINED)]
    assert log._active_progress == progress
    yield from wait()
    assert log._active_progress > progress

    log.set_history([{'text': f'調查紀錄 {n:02}'} for n in range(40)])
    log.set_typewriter_override(True)
    log.add('新發現\n' * 30)
    view = g['get_log_viewport'](g['get_areas_for_mode'](g['player'])['log'], g['FONT'])
    log.set_scroll_offset(999, g['FONT'], view.text_width, view.visible_lines)
    yield from wait(20)
    assert log.get_visible_lines(g['FONT'], view.text_width, view.visible_lines)[0][0] == '調查紀錄 00'
    log.finish_typewriter()
    yield from wait()
    assert log.get_visible_lines(g['FONT'], view.text_width, view.visible_lines)[0][0] == '調查紀錄 00'
    screenshot('reading_history')
    yield click(view.latest_button)
    assert log.log_offset == 0

    # Ending and intro now wait for an explicit click on desktop and mobile.
    for ending in (False, True):
        g['reset_action_playback']()
        g['player'] = g['init_player_state']()
        g['current_event'] = {'id': 'review', 'options': []}
        g['sub_state'] = 'ending' if ending else 'show_event'
        if ending:
            g['player'].update(ending_active=True, ending_segments=['最後一段'], ending_segment_index=1,
                               flags={'ending_cinematic': True})
        else:
            g['player'].update(intro_cinematic_active=True, intro_segments=['最後一段'], intro_segment_index=1)
        log.set_history([{'text': f'劇情段落 {n:02}'} for n in range(12)])
        log.set_typewriter_override(False)
        yield from wait(60)
        assert not g['player'].get('ending_exit_started') and not g['player'].get('intro_cinematic_exiting')
        view = g['get_log_viewport'](g['get_areas_for_mode'](g['player'])['log'], g['FONT'])
        log.set_scroll_offset(999, g['FONT'], view.text_width, view.visible_lines)
        yield click(view.latest_button)
        assert log.log_offset == 0
        assert not g['player'].get('ending_exit_started') and not g['player'].get('intro_cinematic_exiting')
        screenshot('ending_continue' if ending else 'intro_continue')
        yield click(view.footer)
        assert g['player'].get('ending_exit_started' if ending else 'intro_cinematic_exiting')

    assert not list(save._save_file().parent.glob('*.bak'))
    assert not list(save._save_file().parent.glob('*.tmp'))
    yield [pygame.event.Event(pygame.QUIT)]


def main():
    with tempfile.TemporaryDirectory(prefix='game_flow_') as data:
        os.environ.update(LOCALAPPDATA=data, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy', PYGAME_HIDE_SUPPORT_PROMPT='1')
        if MOBILE:
            os.environ['ANDROID_ARGUMENT'] = 'review'
        import pygame

        class Clock:
            def tick(self, fps):
                global elapsed, next_frame_ms
                duration = next_frame_ms
                next_frame_ms = 17
                elapsed += duration
                return duration

        driver = None
        count = 0

        def events():
            nonlocal driver, count
            count += 1
            assert count < 700, 'Scenario did not finish'
            if driver is None:
                driver = scenario(inspect.currentframe().f_back.f_globals, pygame)
            return next(driver)

        with patch('pygame.event.get', events), patch('pygame.time.Clock', Clock), patch('pygame.time.get_ticks', lambda: elapsed):
            try:
                runpy.run_path(str(ROOT / 'main.py'), run_name='__main__')
            except SystemExit as exc:
                assert exc.code in (None, 0)
        print('PASS: save confirmation, inventory, preview, focus pause, anchored reading and cinematic controls', 'touch' if MOBILE else 'desktop')


if __name__ == '__main__':
    main()
