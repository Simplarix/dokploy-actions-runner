#!/usr/bin/env python3
"""Exercise the real pinned image/entrypoint with mock GitHub calls, offline."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import uuid

from validate import COMPOSE, FIXTURE, INPUTS, load_blueprint

MOCKS = {
    "token.sh": """#!/bin/bash
set -eu
test "$ACCESS_TOKEN" = test_only_not_a_real_token
printf 'token:%s\\n' "$RUNNER_SCOPE" >> /_work/test-events
printf '{"token":"offline_token"}\\n'
""",
    "config.sh": """#!/bin/bash
set -eu
if [[ "$1" == remove ]]; then
  test "$2" = --token
  test "$3" = offline_token
  printf 'removed\\n' >> /_work/test-events
  rm -f .runner
  exit 0
fi
test ! -f .runner
url= name= labels= group= replace= work=
while (( $# )); do
  case "$1" in
    --url) url="$2"; shift 2 ;;
    --name) name="$2"; shift 2 ;;
    --labels) labels="$2"; shift 2 ;;
    --runnergroup) group="$2"; shift 2 ;;
    --work) work="$2"; shift 2 ;;
    --token) test "$2" = offline_token; shift 2 ;;
    --replace) replace=yes; shift ;;
    --unattended) shift ;;
    *) echo 'Unexpected configuration argument' >&2; exit 70 ;;
  esac
done
if [[ "$RUNNER_SCOPE" == org ]]; then
  test "$url" = "https://github.com/$ORG_NAME"
else
  test "$url" = "$REPO_URL"
fi
test "$name" = "$RUNNER_NAME"
test "$labels" = "$LABELS"
test "$group" = "$RUNNER_GROUP"
test "$work" = /_work
test "$replace" = yes
touch .runner
printf 'configured:%s\\n' "$name" >> /_work/test-events
""",
    "Runner.Listener": """#!/bin/bash
set -eu
test "$1" = run
test "$2" = --startuptype
test "$3" = service
test "$(id -u)" != 0
test -z "${ACCESS_TOKEN:-}"
test "$(node --version)" = v24.22.1
test ! -S /var/run/docker.sock
touch /_work/writable
touch /opt/hostedtoolcache/writable
printf 'listening\\n' >> /_work/test-events
trap 'exit 0' TERM INT
while true; do sleep 1; done
""",
}


def run(args, **kwargs):
    result = subprocess.run(args, text=True, capture_output=True, timeout=kwargs.pop("timeout", 60), **kwargs)
    if result.returncode:
        # Fixtures contain no real credentials; still avoid dumping config/env.
        raise RuntimeError(f"Command failed: {' '.join(args[:3])}\n{result.stderr}")
    return result.stdout.strip()


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def scenario(scope, platform):
    project = "runner-offline-" + uuid.uuid4().hex[:12]
    with tempfile.TemporaryDirectory(prefix="runner-offline-") as directory:
        folder = Path(directory)
        env_file = folder / ".env"
        values = FIXTURE | {"RUNNER_NAME": project}
        if scope == "org":
            values.update(RUNNER_SCOPE="org", REPO_URL="", ORG_NAME="example-org", RUNNER_GROUP="Trusted Builds")
        env_file.write_text("\n".join(f"{key}={value}" for key, value in values.items()))
        mounts = []
        for name, content in MOCKS.items():
            path = folder / name
            path.write_text(content)
            path.chmod(0o755)
            destination = {"token.sh": "/token.sh", "config.sh": "/actions-runner/config.sh",
                           "Runner.Listener": "/actions-runner/bin/Runner.Listener"}[name]
            mounts.append({"type": "bind", "source": str(path), "target": destination, "read_only": True})
        override = folder / "offline.json"
        override.write_text(json.dumps({"services": {"dokploy-actions-runner": {"network_mode": "none", "platform": platform, "volumes": mounts,
                                                "cpus": 2, "mem_limit": "1g", "pids_limit": 128}}}))
        environment = {k: v for k, v in os.environ.items()
                       if k not in INPUTS and not k.startswith("COMPOSE_")}
        compose = ["docker", "compose", "-p", project, "--env-file", str(env_file),
                   "-f", str(COMPOSE), "-f", str(override)]

        def dc(*args):
            return run([*compose, *args], env=environment)

        def events():
            return run(["docker", "exec", container, "cat", "/_work/test-events"])

        def await_listening(count):
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                try:
                    if events().count("listening") >= count:
                        return
                except RuntimeError:
                    pass
                time.sleep(0.3)
            raise AssertionError("Mock listener did not start: " + dc("logs", "--no-color"))

        try:
            dc("up", "-d", "--pull", "never")
            container = dc("ps", "-q", "dokploy-actions-runner")
            await_listening(1)
            # Exercise the template's actual liveness command in the container.
            health = load_blueprint()["services"]["dokploy-actions-runner"]["healthcheck"]["test"][1]
            run(["docker", "exec", container, "/bin/sh", "-c", health])
            security = json.loads(run(["docker", "inspect", container]))[0]
            check(security["Config"]["User"] == "runner", "Image is not running as runner")
            check(not security["HostConfig"]["Privileged"], "Privileged mode unexpectedly enabled")
            check(security["HostConfig"]["CapDrop"] == ["ALL"], "Capabilities are not dropped")
            # Graceful restart must deregister, fetch a fresh token, then configure.
            dc("restart", "dokploy-actions-runner")
            await_listening(2)
            log = events()
            check(log.count("configured:") == 2, "Restart did not configure again")
            check(log.count("removed") == 1, "Restart did not deregister exactly once")
            check(log.count("token:") == 3, "Restart did not obtain fresh registration/shutdown tokens")
            check(log.index("removed") < log.rindex("configured:"), "Deregistration occurred out of order")
            # Unexpected listener failure must also restart without an operator.
            run(["docker", "exec", container, "/bin/bash", "-c",
                 "kill -KILL $(pgrep -x 'Runner[.]Listener')"])
            await_listening(3)
            check(events().count("removed") == 2, "Listener failure did not invoke exit cleanup")
            state = json.loads(run(["docker", "inspect", container]))[0]
            check(state["RestartCount"] >= 1, "Docker did not automatically restart the container")
            # Hard-kill bypasses traps. Fixed names + --replace recover on restart.
            dc("kill", "-s", "SIGKILL", "dokploy-actions-runner")
            dc("start", "dokploy-actions-runner")
            await_listening(4)
            check(events().count("removed") == 2, "SIGKILL incorrectly appeared to deregister")
            dc("stop", "dokploy-actions-runner")
            # docker cp works after stop; do not restart just to inspect shutdown.
            run(["docker", "cp", f"{container}:/_work/test-events", str(folder / "events")])
            log = (folder / "events").read_text()
            check(log.count("configured:") == 4 and log.count("removed") == 3,
                  "Final graceful stop did not deregister")
            logs = dc("logs", "--no-color")
            check(FIXTURE["ACCESS_TOKEN"] not in logs, "PAT leaked to container logs")
            print(f"{scope}: non-root startup, routing arguments, .env injection, token un-export, "
                  "liveness, automatic restart, graceful restart/stop and SIGKILL recovery: OK (mock GitHub)")
        finally:
            dc("down", "--timeout", "10", "--remove-orphans")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", required=True, choices=["linux/amd64", "linux/arm64"])
    args = parser.parse_args()
    image = load_blueprint()["services"]["dokploy-actions-runner"]["image"]
    # No image pull/authentication occurs inside tests. Only this explicit step
    # needs registry access; all scenario containers have networking disabled.
    run(["docker", "pull", "--platform", args.platform, image], timeout=600)
    # Verify the shipped runner binary before replacing it with a mock listener.
    version = run(["docker", "run", "--rm", "--platform", args.platform, "--network", "none", "--user", "runner",
                   "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true",
                   "--entrypoint", "./bin/Runner.Listener", image, "--version"])
    check(version == image.split(":", 1)[1].split("-", 1)[0], "Runner binary version differs from image tag")
    for scope in ("repo", "org"):
        scenario(scope, args.platform)


if __name__ == "__main__":
    main()
