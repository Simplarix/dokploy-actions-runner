import copy
from contextlib import redirect_stdout
import io
import json
import os
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import check_updates
from check_updates import Finding, findings, report
from runtime_inventory import verify


class UpdateTests(unittest.TestCase):
    def test_prereleases_do_not_break_or_trigger_stable_node_monitoring(self):
        policy = {'runner': '2.338.2', 'default_node': 'v24.22.1'}
        release = {'tag_name': 'v2.338.2', 'published_at': '2026-10-26T14:45:12Z'}
        image = 'image:2.338.2@sha256:old'
        nodes = [{'version': v, 'security': False} for v in ('v27.0.0-alpha.0.0.0', 'v24.23.0-rc.1',
                                          'v24.22.1', 'v24.9.0')]
        self.assertEqual(findings(policy, image, release, nodes, 'sha256:old'), [])
        messages = findings(policy, image, release, nodes + [{'version': 'v24.22.2', 'security': False}], 'sha256:old')
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].level, 'warning')
        self.assertIn('v24.22.2', messages[0].message)

    def test_missing_stable_node_major_fails_instead_of_silently_passing(self):
        with self.assertRaisesRegex(ValueError, 'No stable Node 24 releases'):
            findings({'runner': '2.338.2', 'default_node': 'v24.22.1'},
                     'image:2.338.2@sha256:old',
                     {'tag_name': 'v2.338.2', 'published_at': '2026-10-26T14:45:12Z'},
                     [{'version': 'v27.0.0-alpha.0.0.0'}, {'version': 'v24.23.0-rc.1'}],
                     'sha256:old')

    def test_every_update_channel_is_independent(self):
        policy = {'runner': '2.338.1', 'default_node': 'v24.22.1'}
        image = 'image:2.338.1@sha256:old'
        release = {'tag_name': 'v2.338.1', 'published_at': '2026-10-22T14:14:46Z'}
        nodes = [{'version': 'v26.12.1'}, {'version': 'v24.22.1'}]
        self.assertEqual(findings(policy, image, release, nodes, 'sha256:old'), [])
        self.assertEqual(len(findings(policy, image, release | {'tag_name': 'v2.339.0'}, nodes, 'sha256:old')), 1)
        self.assertEqual(len(findings(policy, image, release, nodes + [{'version': 'v24.22.2'}], 'sha256:old')), 1)
        self.assertEqual(len(findings(policy, image, release, nodes, 'sha256:new')), 1)

    def test_node_security_release_cannot_be_hidden_by_a_later_ordinary_release(self):
        policy = {'runner': '2.338.2', 'default_node': 'v24.22.1'}
        nodes = [{'version': 'v24.22.3', 'security': False},
                 {'version': 'v24.22.2', 'security': True},
                 {'version': 'v24.22.1', 'security': True},
                 {'version': 'v26.12.1', 'security': True}]
        messages = findings(policy, 'image@sha256:old',
                            {'tag_name': 'v2.338.2'}, nodes, 'sha256:old')
        self.assertEqual([message.level for message in messages], ['error', 'warning'])
        self.assertIn('v24.22.2', messages[0].message)
        self.assertIn('security release', messages[0].message)

    def test_unknown_node_security_metadata_fails_closed(self):
        for metadata in ({}, {'security': None}, {'security': 'false'}, {'security': 0}):
            with self.subTest(metadata=metadata):
                messages = findings({'runner': '2.338.2', 'default_node': 'v24.22.1'},
                                    'image@sha256:old', {'tag_name': 'v2.338.2'},
                                    [{'version': 'v24.22.2'} | metadata], 'sha256:old')
                self.assertEqual(messages[0].level, 'error')
                self.assertIn('missing or invalid security metadata', messages[0].message)

    def test_runner_and_digest_updates_still_fail_with_ordinary_node_update(self):
        policy = {'runner': '2.338.2', 'default_node': 'v24.22.1'}
        nodes = [{'version': 'v24.22.2', 'security': False}]
        for runner, digest in [('v2.339.0', 'sha256:old'), ('v2.338.2', 'sha256:new')]:
            with self.subTest(runner=runner, digest=digest):
                messages = findings(policy, 'image@sha256:old',
                                    {'tag_name': runner, 'published_at': '2026-11-03'}, nodes, digest)
                self.assertEqual(sorted(message.level for message in messages), ['error', 'warning'])
                with redirect_stdout(io.StringIO()):
                    self.assertTrue(report(messages))

    def test_main_reports_ordinary_node_update_without_failing_or_changing_policy(self):
        policy_path = Path(__file__).resolve().parents[1] / 'runtime-policy.json'
        baseline = policy_path.read_text()
        policy = json.loads(baseline)
        release = {'tag_name': 'v' + policy['runner']}
        image = check_updates.load_blueprint()['services']['dokploy-actions-runner']['image']
        manifest = SimpleNamespace(stdout=json.dumps({'digest': image.split('@')[1]}))
        major, minor, patch_version = check_updates.version(policy['default_node'])
        next_node = f'v{major}.{minor}.{patch_version + 1}'
        nodes = [{'version': next_node, 'security': False}]
        with tempfile.TemporaryDirectory() as temp:
            summary = Path(temp) / 'summary.md'
            output = io.StringIO()
            with patch.dict(os.environ, {'GITHUB_ACTIONS': 'true', 'GITHUB_STEP_SUMMARY': str(summary)}), \
                    patch('check_updates.fetch', side_effect=[release, nodes]), \
                    patch('check_updates.subprocess.run', return_value=manifest), redirect_stdout(output):
                self.assertFalse(check_updates.main())
            self.assertIn(f'::warning::Node {next_node}', output.getvalue())
            self.assertNotIn('::error::', output.getvalue())
            self.assertIn('**Warning**', summary.read_text())
            self.assertIn('baseline is unchanged', summary.read_text())
        self.assertEqual(policy_path.read_text(), baseline)

    def test_report_exit_status_and_annotations(self):
        cases = [([], False), ([Finding('warning', 'ordinary update')], False),
                 ([Finding('warning', 'ordinary update'), Finding('error', 'security update')], True)]
        for messages, failed in cases:
            with self.subTest(messages=messages), tempfile.TemporaryDirectory() as temp:
                summary = Path(temp) / 'summary.md'
                output = io.StringIO()
                with patch.dict(os.environ, {'GITHUB_ACTIONS': 'true', 'GITHUB_STEP_SUMMARY': str(summary)}), redirect_stdout(output):
                    self.assertEqual(report(messages), failed)
                for finding in messages:
                    self.assertIn(f'::{finding.level}::{finding.message}', output.getvalue())
                    self.assertIn(f'**{finding.level.title()}**: {finding.message}', summary.read_text())
                if not messages:
                    self.assertIn('match the reviewed baseline', summary.read_text())

    def test_network_and_manifest_errors_are_not_downgraded_to_warnings(self):
        with patch('check_updates.subprocess.run', side_effect=OSError('registry unavailable')):
            with self.assertRaisesRegex(OSError, 'registry unavailable'):
                check_updates.main()
        manifest = SimpleNamespace(stdout='{invalid json')
        with patch('check_updates.subprocess.run', return_value=manifest):
            with self.assertRaises(json.JSONDecodeError):
                check_updates.main()
        manifest.stdout = '{"digest": "sha256:old"}'
        with patch('check_updates.subprocess.run', return_value=manifest), \
                patch('check_updates.fetch', side_effect=OSError('release index unavailable')):
            with self.assertRaisesRegex(OSError, 'release index unavailable'):
                check_updates.main()

    def test_runtime_inventory_rejects_fallback_and_unreviewed_binaries(self):
        policy = {'runner': '2.338.1', 'default_node': 'v24.22.1', 'platforms': {'linux/amd64': {'/actions-runner/externals/node24/bin/node': 'v24.22.1'}}}
        node = {'path': '/actions-runner/externals/node24/bin/node', 'elf_machine': 62, 'execution': 'executed', 'exit_code': 0, 'version': 'v24.22.1'}
        data = {'runner_exit_code': 0, 'runner': '2.338.1', 'default_node_path': node['path'], 'default_node_version': 'v24.22.1', 'nodes': [node]}
        verify(data, policy, 'linux/amd64')
        for change in ({'default_node_path': '/usr/bin/node'}, {'default_node_version': 'v18.19.1'}, {'nodes': [node, node | {'path': '/opt/old/node'}]}):
            with self.subTest(change=change), self.assertRaises(AssertionError):
                verify(data | change, policy, 'linux/amd64')
        wrong = copy.deepcopy(data)
        wrong['nodes'][0]['elf_machine'] = 183
        with self.assertRaises(AssertionError):
            verify(wrong, policy, 'linux/amd64')
