#!/usr/bin/env python3
"""Opt-in real GitHub smoke jobs on disposable local runner containers.

Requires an already authenticated gh CLI with runner administration and workflow
permissions. Uses its token only in memory/container configuration. Never run
against an unreviewed workflow ref. This does not deploy to Dokploy.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import uuid
from validate import COMPOSE, FIXTURE, INPUTS


def command(args, **kwargs):
    result = subprocess.run(args, capture_output=True, text=True, timeout=kwargs.pop('timeout', 90), **kwargs)
    if result.returncode:
        # gh/Docker errors and logs can contain credentials. Do not echo them.
        raise RuntimeError(f'{args[0]} command failed (exit {result.returncode}); inspect privately')
    return result.stdout.strip()


def api(path, method='GET', data=None):
    args = ['gh', 'api', path, '--method', method]
    if data is not None:
        args += ['--input', '-']
    value = command(args, input=json.dumps(data) if data is not None else None)
    return json.loads(value) if value else None


def until(check, description, seconds=300):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        result = check()
        if result:
            return result
        time.sleep(5)
    raise RuntimeError('Timed out: ' + description)


def matches_dispatch(run, label, ref, commit, seen):
    return (run['id'] not in seen and run.get('head_branch') == ref
            and run.get('head_sha') == commit
            and run.get('display_title') == 'Runner smoke ' + label)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--ref', required=True, help='Reviewed, pushed branch containing validate.yml')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    label = 'runner-smoke-' + uuid.uuid4().hex[:12]
    token = command(['gh', 'auth', 'token'])
    report = {'repository': args.repo, 'ref': args.ref, 'label': label, 'runs': [], 'cleanup': False,
              'platforms': ['linux/arm64 (native Docker Desktop VM)', 'linux/amd64 (Rosetta emulation)']}
    base = f'repos/{args.repo}'
    projects = []
    seen = set()
    dispatched = []
    commit = api(base + '/commits/' + args.ref)['sha']
    report['expected_commit'] = commit
    try:
        with tempfile.TemporaryDirectory(prefix='runner-live-') as directory:
            for arch in ['arm64', 'amd64']:
                project = label + '-' + arch
                override = Path(directory) / (arch + '.json')
                override.write_text(json.dumps({'services': {'dokploy-actions-runner': {
                    'platform': 'linux/' + arch, 'cpus': 2, 'mem_limit': '2g', 'pids_limit': 256}}}))
                environment = {key: value for key, value in os.environ.items()
                               if key not in INPUTS and not key.startswith('COMPOSE_')}
                environment.update(FIXTURE | {'ACCESS_TOKEN': token, 'REPO_URL': 'https://github.com/' + args.repo,
                                              'RUNNER_NAME': project, 'LABELS': label})
                dc = ['docker', 'compose', '-p', project, '--env-file', os.devnull,
                      '-f', str(COMPOSE), '-f', str(override)]
                projects.append((dc, environment, project))
                command([*dc, 'up', '-d', '--pull', 'never'], env=environment)
            def runners():
                return [r for r in api(base + '/actions/runners')['runners'] if r['name'].startswith(label)]
            def ready():
                current = runners()
                return len(current) == 2 and all(r['status'] == 'online' and not r['busy'] for r in current)
            until(ready, 'both architectures online')
            report['initial_registration'] = [{k: r[k] for k in ('id', 'name', 'os', 'status')} for r in runners()]
            print('Both disposable runner architectures registered and online', flush=True)
            for cycle in ('initial', 'after-restart'):
                if cycle == 'after-restart':
                    until(ready, 'idle before restart')
                    for dc, environment, _ in projects:
                        command([*dc, 'restart'], env=environment, timeout=180)
                    until(ready, 'both runners online after restart')
                api(base + '/actions/workflows/validate.yml/dispatches', 'POST',
                    {'ref': args.ref, 'inputs': {'live_smoke': 'true', 'runner_label': label}})
                def new_run():
                    return next((r for r in api(base + '/actions/workflows/validate.yml/runs?event=workflow_dispatch&per_page=20')['workflow_runs']
                                 if matches_dispatch(r, label, args.ref, commit, seen)), None)
                run = until(new_run, 'smoke workflow created')
                seen.add(run['id'])
                dispatched.append(run['id'])
                print(f'{cycle}: {run["html_url"]}', flush=True)
                def finished():
                    current = api(base + '/actions/runs/' + str(run['id']))
                    return current if current['status'] == 'completed' else None
                result = until(finished, 'smoke jobs completed', seconds=600)
                jobs = api(base + '/actions/runs/' + str(run['id']) + '/jobs')['jobs']
                report['runs'].append({'cycle': cycle, 'url': result['html_url'], 'id': result['id'],
                                       'commit': result['head_sha'], 'conclusion': result['conclusion'],
                                       'jobs': [{k: j[k] for k in ('name', 'conclusion', 'runner_name')} for j in jobs]})
                live_jobs = [j for j in jobs if j['name'].startswith('live-smoke (')]
                if (len(live_jobs) != 2 or {j['runner_name'] for j in live_jobs} != {p[2] for p in projects}
                        or any(j['conclusion'] != 'success' for j in live_jobs)):
                    raise RuntimeError('Both smoke jobs must succeed on this invocation’s runners')
                if result['conclusion'] != 'success':
                    raise RuntimeError('GitHub smoke workflow did not succeed; see the recorded run URL')
            for dc, environment, _ in projects:
                command([*dc, 'stop'], env=environment, timeout=180)
            until(lambda: not runners(), 'graceful deregistration')
            report['graceful_deregistration'] = True
    finally:
        # Override files may have gone away; cleanup by unique Compose project.
        cleanup_errors = []
        for run_id in dispatched:
            try:
                run = api(base + '/actions/runs/' + str(run_id))
                if run['status'] != 'completed':
                    api(base + '/actions/runs/' + str(run_id) + '/cancel', 'POST')
            except RuntimeError:
                cleanup_errors.append('workflow-' + str(run_id))
        for _, environment, project in projects:
            try:
                command(['docker', 'compose', '-p', project, '--env-file', os.devnull,
                         '-f', str(COMPOSE), 'down', '--timeout', '120'], env=environment, timeout=180)
            except RuntimeError:
                cleanup_errors.append(project)
        try:
            remaining = [r for r in api(base + '/actions/runners')['runners'] if r['name'].startswith(label)]
            for runner in remaining:
                # Only registrations created by this invocation can be removed.
                if runner['name'] in {p[2] for p in projects}:
                    api(base + '/actions/runners/' + str(runner['id']), 'DELETE')
        except RuntimeError:
            cleanup_errors.append('github-registrations-' + label)
        report['cleanup'] = not cleanup_errors
        report['manual_cleanup_names'] = cleanup_errors
        args.output.write_text(json.dumps(report, indent=2) + '\n')
        token = None
    if not report['cleanup']:
        raise RuntimeError('Test cleanup needs attention; see recorded identifiers')
    print('Real GitHub jobs, restart, graceful deregistration and cleanup: OK')


if __name__ == '__main__':
    main()
