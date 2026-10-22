#!/usr/bin/env python3
"""Fail CI when the pinned runner, default Node or image digest needs review."""
import json
import subprocess
import urllib.request
from pathlib import Path
from validate import load_blueprint


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'dokploy-actions-runner-update-check'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def version(value):
    return tuple(int(part) for part in value.lstrip('v').split('.'))


def findings(policy, image, runner_release, node_releases, index_digest):
    messages = []
    latest_runner = runner_release['tag_name'].lstrip('v')
    if version(latest_runner) > version(policy['runner']):
        messages.append(f'Runner {latest_runner} released {runner_release["published_at"]}; review and deploy promptly (GitHub maximum: 30 days, critical updates sooner).')
    major = version(policy['default_node'])[0]
    latest_node = max((entry['version'] for entry in node_releases if version(entry['version'])[0] == major), key=version)
    if version(latest_node) > version(policy['default_node']):
        messages.append(f'Node {latest_node} is newer than the tested runtime; check the security release notes and upstream runner image.')
    if index_digest != image.split('@', 1)[1]:
        messages.append('Upstream rebuilt the pinned tag; inspect OS/tool changes and scan/test the new digest before updating both catalogs.')
    return messages


def main():
    root = Path(__file__).resolve().parents[1]
    policy = json.loads((root / 'runtime-policy.json').read_text())
    image = load_blueprint()['services']['dokploy-actions-runner']['image']
    result = subprocess.run(['docker', 'buildx', 'imagetools', 'inspect', image.split('@', 1)[0], '--format', '{{json .Manifest}}'],
                            capture_output=True, text=True, timeout=90, check=True)
    manifest = json.loads(result.stdout)
    messages = findings(policy, image,
                        fetch('https://api.github.com/repos/actions/runner/releases/latest'),
                        fetch('https://nodejs.org/dist/index.json'), manifest['digest'])
    for message in messages:
        print(message)
    if not messages:
        print('Runner, Node24 and upstream tag digest match the reviewed baseline. This is not a vulnerability scan.')
    return bool(messages)


if __name__ == '__main__':
    raise SystemExit(main())
