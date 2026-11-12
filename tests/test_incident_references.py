"""Offline tests for following incident references without arbitrary URL access."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent import _incident_references, run_agent
from status_tools import StatusTools
from test_lab import FakeProvider, final, tool_call


class LinkedTools(StatusTools):
    def __init__(self, fail_target=False, cycle=False):
        self.fail_target, self.cycle = fail_target, cycle

    def execute(self, name, args):
        incident = args['incident_id']
        if incident == 'target' and self.fail_target:
            return {'ok': False, 'error': 'TimeoutError'}
        body = 'See https://www.githubstatus.com/incidents/target' if incident == 'start' else ''
        if incident == 'target' and self.cycle:
            body = 'See https://www.githubstatus.com/incidents/start'
        return {'ok': True, 'provider': 'github', 'id': incident,
                'url': f'https://www.githubstatus.com/incidents/{incident}',
                'updates': [{'body': body}]}


def read(incident):
    return tool_call(incident, 'get_incident_details',
                     json.dumps({'provider': 'github', 'incident_id': incident}))


class IncidentReferenceTests(unittest.TestCase):
    def setUp(self):
        guard = patch('urllib.request.urlopen', side_effect=AssertionError('Offline only'))
        guard.start()
        self.addCleanup(guard.stop)

    def test_premature_final_gets_read_request_then_can_complete(self):
        answer = 'Sources https://www.githubstatus.com/incidents/start https://www.githubstatus.com/incidents/target'
        fake = FakeProvider([read('start'), final('Premature claim'), read('target'), final(answer)])
        result = run_agent('Find root cause', fake, LinkedTools(), 4)
        self.assertEqual(result['status'], 'completed')
        self.assertIn('get_incident_details', fake.histories[2][-1]['content'])
        self.assertEqual(fake.histories[2][-1]['role'], 'user')
        self.assertTrue(any(e['event'] == 'validation_unread_incident' for e in result['trace']))
        self.assertEqual([e['step'] for e in result['trace'] if e['event'] == 'tool'], [1, 3])

    def test_budget_exhaustion_does_not_complete_unread_claim(self):
        fake = FakeProvider([read('start'), final('Already read target')])
        result = run_agent('Read related incident', fake, LinkedTools(), 2)
        self.assertEqual(result['status'], 'max_steps')
        self.assertEqual(result['answer'], '')

    def test_failed_reference_can_be_reported_without_retry_loop(self):
        fake = FakeProvider([read('start'), read('target'),
                             final('Target unavailable. https://www.githubstatus.com/incidents/start')])
        result = run_agent('Read related incident', fake, LinkedTools(fail_target=True), 3)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(len(fake.histories), 3)

    def test_cycle_does_not_force_repeated_reads(self):
        fake = FakeProvider([read('start'), read('target'), final(
            'https://www.githubstatus.com/incidents/start https://www.githubstatus.com/incidents/target')])
        result = run_agent('Read related incident', fake, LinkedTools(cycle=True), 3)
        self.assertEqual(result['status'], 'completed')

    def test_external_hosts_credentials_ports_and_malformed_urls_are_ignored(self):
        result = {'updates': [{'body': ' '.join([
            'https://attacker.example/incidents/secret',
            'https://www.githubstatus.com.attacker.example/incidents/secret',
            'https://user@www.githubstatus.com/incidents/secret',
            'https://www.githubstatus.com:444/incidents/secret',
            'https://[bad/incidents/secret',
            'https://www.githubstatus.com/incidents/ok.',
            'https://www.cloudflarestatus.com/incidents/other',
        ])}]}
        self.assertEqual(_incident_references(result), {('github', 'ok'), ('cloudflare', 'other')})

    def test_real_snapshot_redirect_is_discovered_without_network(self):
        tools = StatusTools()
        details = tools.get_incident_details('github', 'h02n9572mx9y')
        self.assertIn(('github', 'xr3myzj7ms51'), _incident_references(details))


if __name__ == '__main__':
    unittest.main()
