"""Offline regression for alternating citations exhausting the model-call budget."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent import run_agent
from status_tools import StatusTools
from test_lab import FakeProvider, final, tool_call


class SourceTools(StatusTools):
    def execute(self, name, args):
        return {'ok': True, 'url': 'https://example.test/' + args['incident_id'], 'updates': []}


class SourceRevisionTests(unittest.TestCase):
    def setUp(self):
        guard = patch('urllib.request.urlopen', side_effect=AssertionError('Offline only'))
        guard.start()
        self.addCleanup(guard.stop)

    def run_alternating(self, revision):
        calls = tool_call('a', 'get_incident_details', '{"provider":"github","incident_id":"a"}')
        other = tool_call('b', 'get_incident_details', '{"provider":"github","incident_id":"b"}')
        calls['calls'] += other['calls']
        calls['message']['tool_calls'] += other['message']['tool_calls']
        fake = FakeProvider([calls, final('Analysis https://example.test/a'), final(revision)])
        return run_agent('Investigate', fake, SourceTools(), max_steps=3), fake

    def test_alternating_urls_finish_after_one_revision(self):
        result, fake = self.run_alternating('Revised analysis https://example.test/b')
        self.assertEqual(result['status'], 'completed')
        self.assertTrue(result['answer'].startswith('Revised analysis'))
        self.assertIn('https://example.test/a', result['answer'])
        self.assertIn('https://example.test/b', result['answer'])
        self.assertEqual(len(fake.histories), 3)
        request = fake.histories[2][-1]['content']
        self.assertIn('https://example.test/a', request)
        self.assertIn('https://example.test/b', request)
        appended = next(e for e in result['trace'] if e['event'] == 'validation_sources_appended')
        self.assertEqual(appended['urls'], ['https://example.test/a'])

    def test_revision_omitting_all_sources_attaches_only_observed_urls(self):
        result, _ = self.run_alternating('Latest analysis without URLs')
        self.assertEqual(result['status'], 'completed')
        self.assertIn('https://example.test/a', result['answer'])
        self.assertIn('https://example.test/b', result['answer'])
        self.assertEqual(result['answer'].count('https://example.test/'), 2)

    def test_correct_revision_needs_no_append(self):
        result, _ = self.run_alternating('Analysis https://example.test/a https://example.test/b')
        self.assertEqual(result['status'], 'completed')
        self.assertFalse(any(e['event'] == 'validation_sources_appended' for e in result['trace']))


if __name__ == '__main__':
    unittest.main()
