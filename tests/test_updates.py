import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_updates import findings
from runtime_inventory import verify


class UpdateTests(unittest.TestCase):
    def test_every_update_channel_is_independent(self):
        policy = {'runner': '2.338.1', 'default_node': 'v24.22.1'}
        image = 'image:2.338.1@sha256:old'
        release = {'tag_name': 'v2.338.1', 'published_at': '2026-10-22T14:14:46Z'}
        nodes = [{'version': 'v26.12.1'}, {'version': 'v24.22.1'}]
        self.assertEqual(findings(policy, image, release, nodes, 'sha256:old'), [])
        self.assertEqual(len(findings(policy, image, release | {'tag_name': 'v2.339.0'}, nodes, 'sha256:old')), 1)
        self.assertEqual(len(findings(policy, image, release, nodes + [{'version': 'v24.22.2'}], 'sha256:old')), 1)
        self.assertEqual(len(findings(policy, image, release, nodes, 'sha256:new')), 1)

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
