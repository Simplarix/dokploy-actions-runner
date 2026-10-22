from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from validate import load_blueprint


class RuntimeGateTests(unittest.TestCase):
    def test_fails_closed_after_missing_downgraded_or_wrong_major_runtime(self):
        script = load_blueprint()['services']['dokploy-actions-runner']['entrypoint'][2].replace('$$', '$')
        gate = re.search(r'# Runtime gate:.*?# End runtime gate\.', script, re.S).group()
        for version, expected in [('v24.22.1', 0), ('v24.22.2', 0), ('v24.23.0', 0),
                                  ('v24.22.0', 64), ('v24.9.9', 64), ('v20.20.2', 64),
                                  ('v26.12.1', 64), ('bad', 64), (None, 64)]:
            with self.subTest(version=version), tempfile.TemporaryDirectory() as temp:
                binary = Path(temp) / 'node'
                if version:
                    binary.write_text('#!/bin/sh\nprintf "%s\\n" "' + version + '"\n')
                    binary.chmod(0o755)
                local = gate.replace('/actions-runner/externals/node24/bin/node', str(binary))
                result = subprocess.run(['/bin/bash', '-c', 'set -eu; fail() { exit 64; };\n' + local],
                                        env={'PATH': temp + ':/usr/bin:/bin'}, capture_output=True, timeout=10)
                self.assertEqual(result.returncode, expected)
