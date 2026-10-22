#!/usr/bin/env python3
"""Inventory actual Node executables in the pinned image without credentials/network."""
import argparse
import json
import subprocess
from pathlib import Path
from validate import load_blueprint

# Runs inside a disposable, resource-limited container. Never exports its environment.
PROBE = r'''
import hashlib, json, os, pathlib, re, shutil, struct, subprocess

def output(args):
    p = subprocess.run(args, capture_output=True, text=True, timeout=30)
    return p.returncode, p.stdout.strip()

nodes = []
paths = set()
for root in ('/actions-runner', '/usr', '/opt'):
    for folder, dirs, files in os.walk(root):
        if 'node' in files:
            paths.add(str(pathlib.Path(folder) / 'node'))
for path in sorted(paths):
    p = pathlib.Path(path)
    if not os.access(p, os.X_OK) or not p.is_file():
        continue
    data = p.read_bytes()
    if data[:4] != b'\x7fELF':
        continue
    alpine = '_alpine/' in path
    # musl binaries cannot execute in the glibc image. Record their ELF/hash and
    # version strings; separate Alpine execution is required to prove runtime.
    versions = sorted(set(x.decode() for x in re.findall(rb'(?<![0-9.])v(?:18|20|24)\.[0-9]+\.[0-9]+(?![0-9.])', data)))
    result = {'path': path, 'realpath': str(p.resolve()),
              'sha256': hashlib.sha256(data).hexdigest(),
              'elf_machine': struct.unpack('<H', data[18:20])[0],
              'version_strings': versions, 'execution': 'requires-musl' if alpine else 'executed'}
    if not alpine:
        code, version = output([path, '--version'])
        result.update(exit_code=code, version=version)
    nodes.append(result)
code, runner = output(['/actions-runner/bin/Runner.Listener', '--version'])
_, version = output(['node', '--version'])
_, packages = output(['dpkg-query', '-W', '-f=${binary:Package}\t${Version}\n'])
print(json.dumps({'runner': runner, 'runner_exit_code': code, 'machine': os.uname().machine,
                  'default_node_path': shutil.which('node'), 'default_node_version': version,
                  'nodes': nodes, 'packages': packages.splitlines()}, sort_keys=True))
'''


def inventory(platform, image=None):
    service = load_blueprint()['services']['dokploy-actions-runner']
    args = ['docker', 'run', '--rm', '--pull', 'never', '--platform', platform,
            '--network', 'none', '--user', 'runner', '--cap-drop', 'ALL',
            '--security-opt', 'no-new-privileges:true', '--memory', '1g', '--cpus', '2',
            '--pids-limit', '128']
    if not image:
        args += ['--env', 'PATH=' + service['environment']['PATH']]
    args += ['--entrypoint', 'python3', '-i', image or service['image'], '-']
    result = subprocess.run(args, input=PROBE, text=True, capture_output=True, timeout=180)
    if result.returncode:
        raise RuntimeError('Isolated runtime inventory failed: ' + result.stderr)
    return json.loads(result.stdout)


def verify(data, policy, platform):
    expected = policy['platforms'][platform]
    assert data['runner_exit_code'] == 0 and data['runner'] == policy['runner'], 'Runner version mismatch'
    assert data['default_node_path'] == '/actions-runner/externals/node24/bin/node', 'Unsafe default Node path'
    assert data['default_node_version'] == policy['default_node'], 'Default Node version mismatch'
    actual = {node['path']: node for node in data['nodes']}
    assert set(actual) == set(expected), 'Node executable inventory changed; review every new/missing binary'
    for path, version in expected.items():
        node = actual[path]
        assert node['elf_machine'] == (62 if platform == 'linux/amd64' else 183), path + ': wrong ELF architecture'
        if node['execution'] == 'executed':
            assert node['exit_code'] == 0 and node['version'] == version, path + ': runtime version mismatch'
        else:
            assert version in node['version_strings'], path + ': embedded version differs (not an execution test)'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--platform', required=True, choices=['linux/amd64', 'linux/arm64'])
    parser.add_argument('--output', type=Path)
    parser.add_argument('--image', help='Inventory another image without applying the pinned-image policy')
    args = parser.parse_args()
    data = inventory(args.platform, args.image)
    if not args.image:
        policy = json.loads((Path(__file__).resolve().parents[1] / 'runtime-policy.json').read_text())
        verify(data, policy, args.platform)
    if args.output:
        args.output.write_text(json.dumps(data, indent=2) + '\n')
    print(json.dumps({k: v for k, v in data.items() if k != 'packages'}, indent=2))


if __name__ == '__main__':
    main()
