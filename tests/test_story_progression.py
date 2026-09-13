"""Exercise narrative order, actual choices, and legacy progress recovery."""
import copy
import io
import random
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import event_manager as events
from battle_system import is_battle_active, start_battle
from event_result_handler import handle_event_result
from player_state import init_player_state


class StoryProgressionTests(unittest.TestCase):
    def setUp(self):
        self.messages = []

        def log(message, **kwargs):
            self.messages.append(message)
            if kwargs.get('on_show'):
                kwargs['on_show']()

        for mock in (patch('text_log.add', log), patch('text_log.clear_history'),
                     patch('text_log.set_typewriter_override'), patch('sound_manager.play_sfx'),
                     redirect_stdout(io.StringIO())):
            mock.__enter__()
            self.addCleanup(mock.__exit__, None, None, None)
        rng = random.getstate()
        self.addCleanup(random.setstate, rng)

    def player(self, chapter=3, fate=50, **flags):
        player = init_player_state()
        player.update(chapter=chapter, fate=fate, flags=flags)
        return player

    def resolve(self, name, player):
        return events._resolve_event_variants(events.get_event_by_id(name), player)

    def choose(self, player, event, index=0):
        result = event['options'][index]['result']
        if event['type'] == 'battle':
            start_battle(player, event)
        for _ in range(8):
            forced = handle_event_result(player, result)
            if forced:
                player['forced_event'] = forced
            if event['type'] != 'battle' or not is_battle_active(player):
                return
        self.fail('Battle did not complete')

    def test_all_entry_methods_and_core_decisions_follow_the_same_order(self):
        for fate in (20, 50, 80):
            for entry_index in range(3):
                for core_index in range(2):
                    for guard_index in range(2):
                        with self.subTest(fate=fate, entry=entry_index, core=core_index, guard=guard_index):
                            player = self.player(fate=fate, 歌聲是門鑰匙=entry_index == 2)
                            guard = events.get_random_event(player=player)
                            self.assertEqual(guard['id'], '守衛傀儡戰')
                            self.choose(player, guard, guard_index)
                            entry = events.get_random_event(player=player)
                            self.assertEqual(entry['id'], '研究據點入口')
                            self.assertFalse(player['flags'].get('visited_outpost'))
                            self.choose(player, entry, entry_index)
                            self.assertTrue(player['flags']['visited_outpost'])
                            interior = []
                            while player['chapter'] == 3:
                                event = events.get_random_event(player=player)
                                self.assertIsNotNone(event)
                                interior.append(event['id'])
                                self.choose(player, event)
                                self.assertLessEqual(len(interior), 3)
                            self.assertEqual(set(interior[:2]), {'會議殘影', '樣本日誌'})
                            core = events.get_random_event(player=player)
                            self.assertEqual(core['id'], '核心機組啟動')
                            self.choose(player, core, core_index)
                            self.assertEqual(bool(player['flags'].get('accepted_id')), core_index == 0)
                            self.assertEqual(bool(player['flags'].get('refused_id')), core_index == 1)
                            self.assertNotEqual(events.get_random_event(player=player)['id'], core['id'])

    def test_clues_change_entry_description_without_blocking_the_door(self):
        for flags in ({}, {'got_gray_pit_hint': True}, {'saw_redactions': True},
                      {'got_gray_pit_hint': True, 'saw_redactions': True}):
            player = self.player(**flags)
            player['consumed_events'].add('守衛傀儡戰')
            entry = events.get_random_event(player=player)
            self.assertEqual(entry['id'], '研究據點入口')
            self.assertEqual(len(entry['options']), 2)
            self.assertEqual('灰燼凹地' in entry['text'], len(flags) == 2)

    def test_forced_events_cannot_skip_entry_or_core_or_cross_chapters(self):
        for name in ('會議殘影', '終章自問', '荒謬結局'):
            player = self.player()
            player['forced_event'] = name
            guard = events.get_random_event(player=player)
            self.assertEqual(guard['id'], '守衛傀儡戰')
            self.choose(player, guard)
            entry = events.get_random_event(player=player)
            self.assertEqual(entry['id'], '研究據點入口')
            self.choose(player, entry)
            self.assertEqual(events.get_random_event(player=player)['chapter'], 3)
        player = self.player(chapter=4)
        player['forced_event'] = '終章自問'
        self.assertEqual(events.get_random_event(player=player)['id'], '核心機組啟動')
        for event in events.ALL_EVENTS:
            if event.get('chapter') == 4 and event['id'] != '核心機組啟動':
                self.assertFalse(events.is_event_condition_met(event, player))

    def test_legacy_inside_saves_restore_entry_but_never_invent_identity(self):
        for chapter, consumed in ((3, ['會議殘影']), (3, ['研究據點入口']),
                                  (4, []), (4, ['核心機組啟動'])):
            player = self.player(chapter=chapter)
            player['consumed_events'] = consumed
            event = events.get_random_event(player=player)
            self.assertTrue(player['flags']['visited_outpost'])
            self.assertNotIn(event['id'], ('研究據點入口', '守衛傀儡戰'))
            self.assertFalse(player['flags'].get('accepted_id') or player['flags'].get('refused_id'))
            if chapter == 4:
                self.assertEqual(event['id'], '核心機組啟動')

    def test_old_unanswered_exit_gets_core_first_then_returns_to_question(self):
        player = self.player(chapter=4)
        player['consumed_events'] = {e['id'] for e in events.ALL_EVENTS if e.get('chapter') == 4}
        old = {'id': '終章自問', 'options': [], '_on_enter_applied': True}
        event = events.refresh_saved_event(old, player)
        self.assertEqual(event['id'], '核心機組啟動')
        self.choose(player, event)
        self.assertEqual(events.get_random_event(player=player)['id'], '終章自問')

    def test_refresh_old_choices_preserves_entry_effects_and_does_not_mutate_source(self):
        for name in ('研究據點入口', '正常結局'):
            player = self.player(chapter=5 if name == '正常結局' else 3, 回家=True)
            old = {'id': name, 'options': [], '_on_enter_applied': True}
            updated = events.refresh_saved_event(old, player)
            self.assertTrue(updated['_on_enter_applied'])
            self.assertTrue(updated['options'])
            self.assertEqual(old['options'], [])
            self.assertIs(events.refresh_saved_event(updated, player), updated)
        source = copy.deepcopy(events.get_event_by_id('正常結局'))
        for _ in range(3):
            self.assertEqual(len(self.resolve('正常結局', player)['options'][0]['result']['ending_segments']), 5)
        self.assertEqual(events.get_event_by_id('正常結局'), source)

    def test_ending_openings_follow_the_actual_core_choice_including_legacy_fallback(self):
        for name in ('理性結局', '正常結局', '荒謬結局'):
            openings = set()
            for identity in ('accepted_id', 'refused_id', None):
                player = self.player(chapter=5, fate=80, **({identity: True} if identity else {}))
                event = self.resolve(name, player)
                openings.add(event['text'])
                if identity == 'accepted_id':
                    self.assertNotIn('切斷', event['text'])
                    self.assertNotIn('關閉', event['text'])
                if identity is None:
                    self.assertNotIn('你先前', event['text'])
            self.assertEqual(len(openings), 3)

    def test_nine_distinct_endings_play_the_selected_segments_and_home_stay_epilogues(self):
        for name in ('理性結局', '正常結局', '荒謬結局'):
            all_segments = set()
            tails = set()
            for desire in ('回家', '留下'):
                player = self.player(chapter=5, accepted_id=True, **{desire: True})
                event = self.resolve(name, player)
                for option in event['options']:
                    result = option['result']
                    self.assertTrue(result['end_game'])
                    all_segments.add(tuple(result['ending_segments'][:4]))
                    tails.add(result['ending_segments'][-1])
                    handle_event_result(player, result)
                    self.assertTrue(player['ending_active'])
                    self.assertEqual(player['ending_segments'], result['ending_segments'])
                    self.assertEqual(player['ending_segment_index'], 1)
                    self.assertEqual(self.messages[-1], result['ending_segments'][0])
                    if name == '理性結局':
                        self.assertNotIn('回到基地', ''.join(result['ending_segments']))
            self.assertEqual(len(all_segments), 3)
            self.assertEqual(len(tails), 2)

    def test_final_choice_thresholds_and_mutually_exclusive_desires(self):
        for before, choice, expected in ((35, 0, '理性結局'), (36, 0, '正常結局'),
                                         (64, 1, '正常結局'), (65, 1, '荒謬結局')):
            player = self.player(chapter=4, fate=before, accepted_id=True, 回家=True, 留下=True)
            self.choose(player, self.resolve('終章自問', player), choice)
            self.assertEqual(player['chapter'], 5)
            self.assertEqual(bool(player['flags']['回家']), choice == 0)
            self.assertEqual(bool(player['flags']['留下']), choice == 1)
            self.assertEqual(events.get_random_event(player=player)['id'], expected)

    def test_guard_outcomes_are_visible_and_failed_turns_do_not_claim_escape(self):
        for action, outcome_key in ((0, 'victory_text'), (1, 'escape_text'), (1, 'defeat_text')):
            player = self.player()
            event = self.resolve('守衛傀儡戰', player)
            result = event['options'][action]['result']
            start_battle(player, event)
            if outcome_key == 'defeat_text':
                player['battle_state']['durability'] = 1
            with patch('battle_system.random.random', return_value=.99 if outcome_key == 'defeat_text' else 0):
                handle_event_result(player, result)
            self.assertIn(result[outcome_key], self.messages)
        player = self.player()
        start_battle(player, event)
        self.messages.clear()
        with patch('battle_system.random.random', return_value=.99):
            handle_event_result(player, result)
        self.assertTrue(is_battle_active(player))
        self.assertNotIn(result['escape_text'], self.messages)
        self.assertNotIn(result['defeat_text'], self.messages)

    def test_seeded_adventures_reach_all_three_endings_without_skipping_main_story(self):
        reached = set()
        for seed in range(12):
            for target in (10, 50, 90):
                random.seed(seed)
                player = init_player_state()
                sequence = []
                for _ in range(45):
                    event = events.get_random_event(player=player)
                    self.assertIsNotNone(event, (seed, target, sequence))
                    sequence.append(event['id'])
                    if event.get('on_enter'):
                        handle_event_result(player, event['on_enter'])

                    def distance(option):
                        result = option['result']
                        effect = result.get('effect') or result.get('victory_effect') or result.get('escape_effect') or {}
                        return abs(player['fate'] + effect.get('fate', 0) - target)

                    index = min(range(len(event['options'])), key=lambda i: distance(event['options'][i]))
                    self.choose(player, event, index)
                    if player.get('ending_active'):
                        reached.add(event['id'])
                        break
                self.assertTrue(player.get('ending_active'), (seed, target, sequence))
                order = [sequence.index(name) for name in ('守衛傀儡戰', '研究據點入口', '會議殘影', '核心機組啟動', '終章自問')]
                self.assertEqual(order, sorted(order))
                self.assertEqual(sequence.count('核心機組啟動'), 1)
        self.assertEqual(reached, {'理性結局', '正常結局', '荒謬結局'})
