import unittest
from core import Config, fixture_run, patch, replay, review


class SandboxTests(unittest.TestCase):
    def test_repair_and_reflection(self):
        result = fixture_run()
        self.assertFalse(result['first_review']['approved'])
        self.assertTrue(result['review']['approved'])
        self.assertLess(result['before']['accuracy'], result['after']['accuracy'])

    def test_each_fault_requires_relevant_fix(self):
        fixed = Config(True, True, 300, 1)
        for change in ({'tenant_filter': False}, {'current_only': False},
                       {'timeout_ms': 100}, {'retries': 0}):
            self.assertLess(replay(patch(fixed, change))['accuracy'], 1)

    def test_rejects_unbounded_or_unknown_mutations(self):
        for change in ({'retries': 100}, {'shell': 'rm'}, {'timeout_ms': -1},
                       {'tenant_filter': 'true'}, {'retries': True}):
            with self.assertRaises(ValueError):
                patch(Config(), change)

    def test_latency_budget_can_block_accurate_candidate(self):
        result = replay(Config(True, True, 1000, 2))
        result['p95_ms'] = 900
        self.assertFalse(review(replay(Config()), result)['approved'])

    def test_inputs_not_mutated(self):
        initial = Config()
        patch(initial, {'current_only': True})
        self.assertFalse(initial.current_only)


if __name__ == '__main__':
    unittest.main()
