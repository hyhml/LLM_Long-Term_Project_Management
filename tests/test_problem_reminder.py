"""TASK-006: operational failure counts never imply acceptance or project authority."""
import concurrent.futures
import json
from support import ROOT, ProjectTestCase, run


class ProblemReminderTest(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.store = self.temp / 'operator' / 'issues.json'

    def cli(self, *args, expected=0):
        return run(ROOT / 'scripts/problem_reminder.py', '--store', self.store, *args, expected=expected)

    def submit(self, key):
        self.cli('submit', key, '--title', 'Synthetic issue', '--criterion', 'Criterion '+key,
                 '--environment', 'Synthetic test environment')

    def record(self, key, eid, result, **kwargs):
        return self.cli('record', key, '--event-id', eid, '--result', result,
                        '--approach', 'Synthetic approach', '--evidence', 'Synthetic observation', **kwargs)

    def issue(self, key):
        return json.loads(self.store.read_text())['issues'][key]

    def test_read_only_empty_listing_does_not_create_registry(self):
        self.cli('list')
        self.assertFalse(self.store.parent.exists())

    def test_third_failure_review_pending_and_acceptance_rounds(self):
        self.submit('a'); self.submit('b')
        for number in range(3):
            output = self.record('a', f'f{number}', 'failed').stdout
            self.assertEqual('提醒：' in output, number == 2)
        self.assertEqual(self.issue('a')['status'], 'needs-review')
        self.assertEqual(self.issue('b')['failures'], 0)
        self.record('a', 'waiting', 'pending')
        self.assertEqual(self.issue('a')['failures'], 3)
        self.record('a', 'verified', 'passed')
        self.assertEqual(self.issue('a')['status'], 'resolved')
        self.assertNotIn('a:', self.cli('list').stdout)
        self.assertIn('a:', self.cli('list', '--all').stdout)
        self.record('a', 'recurrence', 'failed')
        self.assertEqual(self.issue('a')['round'], 2)
        self.assertEqual(self.issue('a')['failures'], 1)
        self.assertEqual(len(self.issue('a')['events']), 6)

    def test_retry_and_concurrent_observation_deduplication(self):
        self.submit('a')
        with concurrent.futures.ThreadPoolExecutor(4) as pool:
            list(pool.map(lambda _: self.record('a', 'one-observation', 'failed'), range(4)))
        self.assertEqual(self.issue('a')['failures'], 1)
        self.assertEqual(len(self.issue('a')['events']), 1)
        original = self.store.read_bytes()
        self.record('a', 'one-observation', 'passed', expected=1)
        self.assertEqual(self.store.read_bytes(), original)

    def test_matching_criterion_and_environment_reuses_issue(self):
        self.submit('a')
        self.cli('submit', 'different-id', '--title', 'Other title', '--criterion', 'Criterion a',
                 '--environment', 'Synthetic test environment', expected=1)
        self.assertEqual(len(json.loads(self.store.read_text())['issues']), 1)

    def test_malformed_registry_is_not_overwritten(self):
        self.store.parent.mkdir()
        for content in ['{broken', '[]', '{"schema":1,"issues":{"a":{}}}', '{"schema":99,"issues":{}}']:
            self.store.write_text(content)
            self.cli('submit', 'a', '--title', 'A', '--criterion', 'C', '--environment', 'E', expected=1)
            self.assertEqual(self.store.read_text(), content)
