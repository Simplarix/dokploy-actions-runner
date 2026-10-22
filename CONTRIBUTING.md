# Contributing

Keep the template self-contained and use the upstream image's lifecycle handler.
Avoid adding controllers, token brokers, shared state or a custom image without a
clear requirement. Preserve the documented security defaults and operator inputs.

## Development

Python 3.11+ and Docker Compose v2+ are required:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python scripts/validate.py
python -m unittest discover -s tests -v
```

For image/runtime changes, also follow the native architecture, offline and live
checks in [MAINTENANCE.md](docs/MAINTENANCE.md). Describe which checks ran and their
limits. Use disposable test targets; never commit credentials or private env files.

## Pull requests

Use conventional branches such as `fix/token-validation` or `docs/setup-guide`,
without a `codex/` prefix. Commit subjects use concise English, lowercase and a
third-person present-tense verb, for example `fix: prevents empty credentials`.

For catalog changes, keep `blueprints/dokploy-actions-runner/` identical in this
project and `Dokploy/templates`. Follow the current upstream contribution guide,
run its metadata validator and test the PR preview import before marking ready.
Keep metadata inside the blueprint; never add a root `meta.json`.

Keep user instructions in README, security policy in SECURITY and update/test/
rollback procedures in the single maintenance guide. Summarize reviewed versions,
results and limits there; put large scans/logs in release or CI artifacts and link
them from the PR. Do not add dated investigation folders to the source tree.
