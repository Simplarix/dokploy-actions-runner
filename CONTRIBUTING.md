# Contributing

Keep the runtime small: a self-contained Compose blueprint around the maintained
runner image. Prefer upstream lifecycle fixes over copying runner scripts here.
Do not add a dashboard, token broker, daemon, database or custom image for the MVP.

Run the README's configuration and offline container checks before submitting a
change. Describe exactly which checks ran and which need live GitHub/Dokploy
access. Never use production PATs for automated tests or commit private `.env`
files. For image updates, update both the tag/digest and `meta.json` version, inspect
upstream lifecycle behavior and rerun the container tests.

Use conventional branch names such as `feat/runner-template`, `fix/token-validation`
or `docs/setup-guide`, without a `codex/` prefix. Commit subjects use the form
`fix: prevents empty runner credentials`: concise English, third-person singular
present-tense verb, lowercase description, no final period.

## Future Dokploy/templates PR

1. Check the current upstream
   [contribution guidelines](https://github.com/Dokploy/templates/blob/canary/CONTRIBUTING.md)
   and target branch again; conventions can change.
2. Copy **only** `blueprints/dokploy-actions-runner/` into the same location in the
   upstream checkout. The Compose file is self-contained. Keep the metadata as a
   single object in that directory; do not add or edit upstream's root `meta.json`.
3. Preserve the logo, matching metadata ID/folder name, image version and links.
   For the upstream copy, name the Compose service `dokploy-actions-runner` to
   match its folder and express `config.env` as an array of `KEY=value` strings.
   The standalone project uses `runner` and the equivalent environment table.
   The image and inline startup/lifecycle behavior must remain identical.
   No domains, custom networks, fixed container names or external scripts are needed.
   Compose uses the current spec without the obsolete top-level `version` field.
4. Run upstream's `node build-scripts/generate-meta.js --check` and validate the
   YAML/TOML. This repository provides additional checks, not a substitute for
   upstream CI.
5. Record the tested Raw Compose path and any remaining checks accurately. A draft
   PR can provide the upstream preview; test that import path before marking the
   contribution ready. Use the [live acceptance checklist](docs/VALIDATION.md)
   with disposable private GitHub targets. Keep customer/project identifiers,
   credentials and internal run links out of public testing notes.

Upstream explicitly requires contributor testing. Passing local mock tests alone
does not justify claiming a fully tested deployment or opening that PR as ready.
