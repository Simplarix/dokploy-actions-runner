#!/usr/bin/env python3
"""Exercise patched tools offline, including a real Git LFS clean/smudge round trip."""
import argparse
import subprocess

PROBE = r'''
import hashlib, json, pathlib, subprocess, tempfile

def run(*args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, **kwargs).stdout

assert run('npm', '--version', text=True).strip() == '11.21.2'
lfs = run('git-lfs', 'version', text=True).strip()
assert 'git-lfs/3.8.1 (Simplarix; linux ' in lfs and 'go 1.27.4' in lfs, lfs
bin_dir = pathlib.Path('/actions-runner/bin')
for manifest in bin_dir.glob('*.deps.json'):
    data = json.loads(manifest.read_text())
    for name in ('Microsoft.AspNetCore.WebUtilities', 'Microsoft.Net.Http.Headers'):
        keys = [key for key in data['libraries'] if key.startswith(name + '/')]
        if keys:
            assert keys == [name + '/8.0.34'], (manifest.name, keys)
            assert (bin_dir / (name + '.dll')).is_file()

with tempfile.TemporaryDirectory() as temp:
    root = pathlib.Path(temp)
    def git(*args):
        return run('git', '-C', temp, *args)
    git('init', '-q')
    git('lfs', 'install', '--local')
    git('lfs', 'track', '*.bin')
    content = bytes(range(256)) * 8192
    sample = root / 'sample.bin'
    sample.write_bytes(content)
    git('add', '.gitattributes', 'sample.bin')
    pointer = git('show', ':sample.bin').decode()
    assert 'oid sha256:' + hashlib.sha256(content).hexdigest() in pointer
    sample.unlink()
    git('checkout', '--', 'sample.bin')
    assert sample.read_bytes() == content, 'Git LFS smudge did not restore the original object'
print(json.dumps({'npm': '11.21.2', 'git_lfs': lfs, 'lfs_round_trip': 'passed',
                  'runner_servicing_packages': '8.0.34'}))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--platform', required=True, choices=['linux/amd64', 'linux/arm64'])
    parser.add_argument('--image', required=True)
    args = parser.parse_args()
    subprocess.run(['docker', 'run', '--rm', '--pull', 'never', '--platform', args.platform,
                    '--network', 'none', '--read-only', '--user', 'runner', '--cap-drop', 'ALL',
                    '--security-opt', 'no-new-privileges:true', '--memory', '512m', '--cpus', '2',
                    '--pids-limit', '64', '--tmpfs', '/tmp:rw,nosuid,nodev,size=64m,mode=1777',
                    '--env', 'HOME=/tmp', '--entrypoint', 'python3', '-i', args.image, '-'],
                   input=PROBE, text=True, check=True, timeout=120)


if __name__ == '__main__':
    main()
