#!/usr/bin/env python3
"""Report runtime updates; fail for runner/image changes and Node security updates."""
from dataclasses import dataclass
import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path
from validate import load_blueprint


@dataclass(frozen=True)
class Finding:
    level: str
    message: str


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
        messages.append(Finding('error', f'Runner {latest_runner} released {runner_release["published_at"]}; review and deploy promptly (GitHub maximum: 30 days, critical updates sooner).'))
    major = version(policy['default_node'])[0]
    # The public index also includes alpha/RC builds, including other majors.
    # Filter before integer parsing so prereleases cannot break stable monitoring.
    candidates = [entry for entry in node_releases
                  if re.fullmatch(r'v\d+\.\d+\.\d+', entry['version'])
                  and version(entry['version'])[0] == major]
    if not candidates:
        raise ValueError(f'No stable Node {major} releases found in the upstream index')
    # Check every newer release: a later ordinary release must not hide an
    # intervening security release. Only an explicit false permits a warning.
    for entry in sorted(candidates, key=lambda entry: version(entry['version'])):
        if version(entry['version']) <= version(policy['default_node']):
            continue
        security = entry.get('security')
        level = 'warning' if security is False else 'error'
        status = ('security: false' if security is False else
                  'security release' if security is True else
                  'missing or invalid security metadata')
        messages.append(Finding(level, f'Node {entry["version"]} is newer than the tested runtime {policy["default_node"]} ({status}); review https://nodejs.org/en/blog/release/{entry["version"]} and the maintained upstream runner image. The tested runtime baseline is unchanged.'))
    if index_digest != image.split('@', 1)[1]:
        messages.append(Finding('error', 'Upstream rebuilt the pinned tag; inspect OS/tool changes and scan/test the new digest before updating both catalogs.'))
    return messages


def report(messages):
    unchanged = 'Runner, Node24 and upstream tag digest match the reviewed baseline. This is not a vulnerability scan.'
    for finding in messages:
        if os.environ.get('GITHUB_ACTIONS') == 'true':
            message = finding.message.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
            print(f'::{finding.level}::{message}')
        else:
            print(f'{finding.level.upper()}: {finding.message}')
    if not messages:
        print(unchanged)
    if summary := os.environ.get('GITHUB_STEP_SUMMARY'):
        lines = [f'- **{finding.level.title()}**: {finding.message}' for finding in messages]
        with Path(summary).open('a') as stream:
            stream.write('## Runtime update check\n\n' + ('\n'.join(lines) or unchanged) + '\n\n')
            if messages:
                stream.write('Ordinary Node releases are warnings; security releases and unknown security metadata fail the check. Runner/image updates also fail. This is not a vulnerability scan.\n')
    return any(finding.level == 'error' for finding in messages)


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
    return report(messages)


if __name__ == '__main__':
    raise SystemExit(main())
