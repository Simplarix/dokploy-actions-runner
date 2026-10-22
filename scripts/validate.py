#!/usr/bin/env python3
"""Validate the blueprint and optionally a private .env, without contacting GitHub."""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tomllib

import yaml

ROOT = Path(__file__).resolve().parents[1]
BLUEPRINT = ROOT / "blueprints" / "dokploy-actions-runner"
COMPOSE = BLUEPRINT / "docker-compose.yml"
INPUTS = {"ACCESS_TOKEN", "RUNNER_SCOPE", "REPO_URL", "ORG_NAME",
          "RUNNER_NAME", "LABELS", "RUNNER_GROUP"}
FIXTURE = {
    "ACCESS_TOKEN": "test_only_not_a_real_token",
    "RUNNER_SCOPE": "repo",
    "REPO_URL": "https://github.com/example/project",
    "ORG_NAME": "",
    "RUNNER_NAME": "dokploy-test-01",
    "LABELS": "dokploy,repo-ci",
    "RUNNER_GROUP": "Default",
}
HANDOFF = "exec /entrypoint.sh ./bin/Runner.Listener run --startuptype service"


def load_blueprint():
    return yaml.safe_load(COMPOSE.read_text())


def compose_config(values=None, env_file=None, project="runner-validation"):
    # Host shell variables otherwise take precedence over --env-file. Keep
    # validation deterministic, including when a developer already runs a runner.
    env = {k: v for k, v in os.environ.items()
           if k not in INPUTS and not k.startswith("COMPOSE_")}
    if values is not None:
        env.update(values)
    cmd = ["docker", "compose", "--project-name", project,
           "--env-file", str(env_file or os.devnull), "-f", str(COMPOSE),
           "config", "--format", "json"]
    result = subprocess.run(cmd, env=env, text=True, capture_output=True, timeout=30)
    if result.returncode:
        # Do not print resolved Compose data or arbitrary user input/secrets.
        raise ValueError("Compose rendering failed; check required ACCESS_TOKEN, "
                         "RUNNER_SCOPE, RUNNER_NAME and LABELS and .env syntax")
    return json.loads(result.stdout)


def validate_startup(environment):
    # Run the exact inline validation without calling the upstream runner.
    script = load_blueprint()["services"]["dokploy-actions-runner"]["entrypoint"][2]
    script = script.replace("$$", "$")
    if script.count(HANDOFF) != 1:
        raise ValueError("Unexpected upstream entrypoint handoff")
    script = script.replace(HANDOFF, "exit 0")
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}
    env.update(environment)
    return subprocess.run(["bash", "-c", script], env=env,
                          text=True, capture_output=True, timeout=10)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_project():
    blueprint = load_blueprint()
    require(set(blueprint) == {"services"}, "Unexpected top-level Compose keys")
    require(set(blueprint["services"]) == {"dokploy-actions-runner"}, "Expected exactly one runner service")
    runner = blueprint["services"]["dokploy-actions-runner"]
    require(re.fullmatch(r"ghcr\.io/myoung34/docker-github-actions-runner:"
                         r"\d+\.\d+\.\d+-ubuntu-noble@sha256:[0-9a-f]{64}",
                         runner["image"]), "Runner image must be release/digest pinned")
    require(runner.get("user") == "runner", "Runner must run as non-root")
    require(runner.get("cap_drop") == ["ALL"], "Drop all Linux capabilities")
    require(runner.get("security_opt") == ["no-new-privileges:true"],
            "Privilege escalation must be disabled")
    for key in ("privileged", "volumes", "ports", "container_name", "env_file",
                "networks", "network_mode", "pid", "devices", "build", "deploy"):
        require(key not in runner, f"Unexpected unsafe or shared service setting: {key}")
    environment = runner["environment"]
    fixed = {"RUN_AS_ROOT": "false", "START_DOCKER_SERVICE": "false",
             "DISABLE_AUTOMATIC_DEREGISTRATION": "false", "RUNNER_WORKDIR": "/_work",
             "UNSET_CONFIG_VARS": "false",
             "PATH": "/actions-runner/externals/node24/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"}
    require(set(environment) == INPUTS | fixed.keys(), "Unexpected environment inputs")
    for key, value in fixed.items():
        require(environment[key] == value, f"Unsafe lifecycle setting: {key}")
    for key in INPUTS:
        require(environment[key].startswith("${" + key + ":"),
                f"Explicit Compose interpolation is required for {key}")
    require(runner["restart"] == "unless-stopped", "Expected automatic restart policy")
    require(runner["stop_grace_period"] == "2m", "Expected deregistration grace period")
    require(runner["entrypoint"][:2] == ["/bin/bash", "-c"], "Unexpected validation wrapper")
    require(HANDOFF in runner["entrypoint"][2], "Must exec upstream lifecycle handler")
    # Every shell dollar must be escaped through Compose, including regex anchors.
    require(not re.search(r"(?<!\$)\$(?!\$)", runner["entrypoint"][2]),
            "Unescaped shell dollar in Compose entrypoint")
    with (BLUEPRINT / "template.toml").open("rb") as stream:
        template = tomllib.load(stream)
    require(template["variables"] == {"runner_name": "dokploy-${uuid}"},
            "Dokploy must generate a unique default runner name")
    require(template["config"]["domains"] == template["config"]["mounts"] == [],
            "Runner requires no domains or file mounts")
    entries = template["config"]["env"]
    require(isinstance(entries, list), "Dokploy catalog env must be an array of KEY=value strings")
    template_env = dict(entry.split("=", 1) for entry in entries)
    require(len(entries) == len(template_env) and set(template_env) == INPUTS,
            "Template inputs must match Compose without duplicates")
    require(template_env["ACCESS_TOKEN"] == "", "Never ship a token")
    metadata = json.loads((BLUEPRINT / "meta.json").read_text())
    require(isinstance(metadata, dict), "Metadata must be a single object")
    require(metadata["id"] == BLUEPRINT.name, "Metadata ID must match blueprint folder")
    for key in ("name", "version", "description", "logo", "tags", "links"):
        require(bool(metadata.get(key)), f"Metadata missing {key}")
    require((BLUEPRINT / metadata["logo"]).is_file(), "Metadata logo is missing")
    require(set(metadata["links"]) == {"github", "website", "docs"}, "Metadata links missing")
    require(runner["image"].split(":", 1)[1].split("@", 1)[0] == metadata["version"],
            "Image tag and metadata version must match")
    require(not (ROOT / "meta.json").exists(), "Upstream metadata belongs inside the blueprint")
    for path in [ROOT / ".github/workflows/validate.yml", *sorted((ROOT / "examples/workflows").glob("*.yml"))]:
        require(isinstance(yaml.safe_load(path.read_text()), dict), f"Invalid YAML: {path.name}")
    config = compose_config(FIXTURE)
    require(config["services"]["dokploy-actions-runner"]["environment"]["ACCESS_TOKEN"] == FIXTURE["ACCESS_TOKEN"],
            "Token was not forwarded to the container")
    result = validate_startup(config["services"]["dokploy-actions-runner"]["environment"])
    require(result.returncode == 0, "Default repository fixture fails startup validation")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, help="Also validate deployment configuration (never prints secrets)")
    args = parser.parse_args()
    try:
        validate_project()
        print("Blueprint JSON, TOML, YAML, security defaults and Compose rendering: OK")
        if args.env_file:
            environment = compose_config(env_file=args.env_file.resolve())["services"]["dokploy-actions-runner"]["environment"]
            result = validate_startup(environment)
            if result.returncode:
                # Our wrapper emits constant diagnostic strings, never values.
                raise ValueError(result.stderr.strip())
            print("Deployment environment: OK (syntax only; token permissions not checked)")
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as error:
        print(f"Validation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
