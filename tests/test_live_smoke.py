import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from live_smoke import matches_dispatch


class SmokeEvidenceTests(unittest.TestCase):
    def test_accepts_only_this_invocations_commit_and_unseen_run(self):
        run = {'id': 10, 'head_branch': 'fix/test', 'head_sha': 'abc', 'display_title': 'Runner smoke unique'}
        self.assertTrue(matches_dispatch(run, 'unique', 'fix/test', 'abc', set()))
        self.assertFalse(matches_dispatch(run, 'unique', 'fix/test', 'abc', {10}))
        for change in ({'head_sha': 'old'}, {'head_branch': 'main'}, {'display_title': 'Validate template'}, {'display_title': 'Runner smoke somebody-else'}):
            with self.subTest(change=change):
                self.assertFalse(matches_dispatch(run | change, 'unique', 'fix/test', 'abc', set()))
