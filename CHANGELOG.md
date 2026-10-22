# Changelog

## Unreleased — 22 October 2026

- Updates the public multi-architecture upstream image to Runner 2.338.1 and
  embedded Node24 24.22.1, pinned by index digest.
- Selects embedded Node24 for default shell steps without replacing Node20
  binaries or disabling runner self-updates. Retained EOL runtimes and scanner
  findings are documented explicitly.
- Adds executable runtime inventories, daily update detection, native AMD64/ARM64
  CI, and opt-in real GitHub JavaScript/lifecycle smoke tests.
- Aligns the service name and TOML environment format with the published Dokploy
  catalog; documents the local-service rename and Node18 → Node24 migration.
- Adds an image update runbook and a prepared SimpleDPP rollback/migration plan.


## v0.1.0 — 17 October 2026

First regular release of the community-maintained Dokploy template.

- Deploys independent GitHub repository or organization runners with configurable
  names, labels and existing organization groups.
- Uses the maintained upstream runner image, pinned to
  `2.338.0-ubuntu-noble` and its multi-architecture digest.
- Validates startup configuration and explicitly forwards required Dokploy
  environment values, including the registration PAT.
- Runs as non-root without privileged mode, host Docker socket access or shared
  runner-state volumes.
- Includes automated configuration and offline lifecycle checks, example workflows,
  setup/security documentation and MIT licensing for original files.
- Records successful repository-runner use in Dokploy and repeat job execution
  after Stop → Deploy. Organization groups, parallel live deployments, catalog
  import and full shutdown deregistration remain unverified live.

No runtime configuration or image change was made since `v0.1.0-rc.1`. Docker
container jobs/actions, service containers and local Docker builds are unsupported
by the defaults. See [validation](docs/VALIDATION.md) and [security](SECURITY.md).

## v0.1.0-rc.1 — 17 October 2026

Initial release candidate with automated configuration validation and mocked
container lifecycle tests on ARM64 and AMD64.
