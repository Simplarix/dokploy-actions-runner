# Maintenance

Maintainers own the image pin and template tests; operators own deployment updates.
Keep this blueprint and the official `Dokploy/templates:canary` catalog entry in sync.

## Reviewed baseline

Reviewed on **22 October 2026**:

| Component | Result |
| --- | --- |
| Upstream image | `ghcr.io/myoung34/docker-github-actions-runner:2.338.1-ubuntu-noble` |
| Multi-architecture index | `sha256:36782fe0e5994b301652408c32113a3562fabb1f0ead865ccc196d3e870f9109` |
| Runner / default shell Node | 2.338.1 / 24.22.1 via `externals/node24/bin/node` |
| Retained runtimes | Distro Node18 18.19.1, embedded Node20 20.20.2; AMD64 also has Node20/24 musl slots; ARM64 has no Alpine slots |
| Scanner | Grype 0.121.0, database built 2026-10-22T06:29:52Z |
| Scanner matches, each architecture | 25 Critical, 181 High, 935 Medium, 138 Low, 11 Negligible, 5 Unknown; zero matches for Node24 24.22.1 in that database |

The old image had embedded Node24 24.21.0 and default shell Node18. The update
selects patched Node24 and guards its startup version; it does not remove the
other vulnerable components. Match counts include duplicate components and do not
establish exploitability or complete vulnerability freedom. See [SECURITY.md](../SECURITY.md).
The exact runtime executable expectations are maintained in
[runtime-policy.json](../runtime-policy.json).

**Validation:** 13 regression tests and native AMD64/ARM64 offline lifecycle CI
[passed](https://github.com/Simplarix/dokploy-actions-runner/actions/runs/39819581730).
Real GitHub jobs [before](https://github.com/Simplarix/dokploy-actions-runner/actions/runs/39819634596)
and [after restart](https://github.com/Simplarix/dokploy-actions-runner/actions/runs/39819792280)
passed with checkout/setup-node, Node24 main/post handlers, a Node20 declaration
routed to Node24, internal hashFiles and the security defaults. Both test runners
deregistered and were removed. Live ARM64 was native in Docker Desktop; live AMD64
and separate musl-binary execution used Rosetta. The emulated mock-listener
healthcheck failed locally; the corresponding native AMD64 CI test passed.

The tester confirmed all six Dokploy preview acceptance steps: Base64 import,
configuration/one Idle runner, successful smoke job with Node24, Stop → Deploy and
another successful job without duplicate registration, graceful deregistration,
and service/token cleanup. Test architecture and repo/org scope were not specified.
Live org/custom-group routing beyond that report, native AMD64 live jobs and an
actual runner self-update remain unverified; no self-update was available to observe.

The complete dated review, source revisions, per-architecture manifests, binary
hashes, scans, preview checks and prepared upstream proposal remain in the
[reviewed PR snapshot](https://github.com/Simplarix/dokploy-actions-runner/tree/8aecb91b31c83ad48d64aec146616206e962ed97/docs)
and [PR #3](https://github.com/Simplarix/dokploy-actions-runner/pull/3).
They are historical evidence, not current deployment state. Future large reports
belong in linked release/CI artifacts, with a short summary here.

## Detect and review updates

- After merge to the default branch, `check-updates.yml` checks daily for newer
  Runner Core/Node24 releases and a rebuilt upstream tag digest. Network/parser
  errors also fail it. Subscribe to failures and keep schedules enabled; GitHub
  can disable schedules on inactive public repositories. Detection does not deploy.
- Dependabot proposes weekly image updates. Also watch
  [runner](https://github.com/actions/runner/releases),
  [image](https://github.com/myoung34/docker-github-actions-runner/releases),
  [Node security](https://nodejs.org/en/blog/vulnerability) and Ubuntu announcements.
  Scan OS/tool packages too; a runtime version check is not a vulnerability scan.
- Triage security releases the same day; target tested catalog/image-pin updates
  within 48 hours and prompt operator rollout. GitHub requires runner updates
  within 30 days and can stop queuing jobs sooner for critical fixes; see its
  [runner reference](https://docs.github.com/en/actions/reference/runners/self-hosted-runners).
  These are maintenance responsibilities, not an automatic rollout guarantee.

## Validate and publish an image update

1. Resolve a maintained upstream tag and its exact multi-architecture index and
   AMD64/ARM64 child manifests. Verify an anonymous pull using an empty Docker
   credential config. Update the Compose tag/digest, metadata version, runtime
   policy, runtime floor/tests/workflow expectations, README and changelog together.
2. Run the configuration/regression checks in [CONTRIBUTING.md](../CONTRIBUTING.md).
   Run the following on each native architecture, selecting `linux/amd64` or
   `linux/arm64` to match the host; CI covers both:

   ```bash
   mkdir -p local
   python scripts/test_container.py --platform linux/amd64
   python scripts/runtime_inventory.py --platform linux/amd64 --output local/runtime.json
   ```

   The lifecycle tests mock GitHub and disable networking. The inventory records
   every executable ELF named `node` under `/actions-runner`, `/usr`, `/opt`, its
   SHA-256/architecture and executed glibc version. Alpine versions require a
   separate musl execution check; strings alone are not runtime proof. Review every
   new/removed slot; never put Node24 in a Node20 path to satisfy a version check.
3. Scan both candidate manifests with a recorded scanner/database version. Retain
   unresolved findings without suppression in release/CI artifacts. Scan counts
   can change with the database even when the image is unchanged.
4. Run real jobs on isolated runners with a reviewed, pushed workflow ref:

   ```bash
   mkdir -p local
   python scripts/live_smoke.py --repo OWNER/REPO --ref BRANCH --output local/live.json
   ```

   This uses the authenticated `gh` account, provisions unique local ARM64/AMD64
   runners, dispatches jobs before/after restart and cleans up its registrations.
   Check the actual native/emulated platforms in the report. Record org/group and
   Dokploy acceptance separately. A complete Dokploy preview test covers import,
   configuration, one Idle runner, a targeted job, Stop → Deploy/repeat job, and
   final deregistration/cleanup. Keep secrets and private infrastructure out of reports.
5. Keep self-updates enabled. They replace `bin` and `externals`, so local binary
   overlays would be overwritten and an initial image digest cannot attest the
   updated filesystem. Check actual versions after observed updates. The startup
   floor rejects missing Node24 or versions below 24.22.1; future security floors
   and runtime-major transitions require template/test review.
6. Create matching maintainer/catalog PRs with the identical blueprint. In the
   catalog checkout run `node build-scripts/generate-meta.js --check`, and test the
   published preview import before marking ready. Link results, limits and artifacts
   in the PR/release; keep only the current summary in this guide.

## Deploy, migrate and roll back

1. Privately save the previous exact image digest, Compose, environment, service
   name and resource limits. Keep the rollback image available. Validate the
   intended private environment with `python scripts/validate.py --env-file .env`;
   this checks syntax, not token permissions. Test representative real jobs on a
   separately named canary first, including application/native-module behavior.
2. Wait for Idle, stop gracefully while the old PAT works, and verify GitHub record
   removal. Do not overlap old/new containers with the same scope/name. For old
   local v0.1.0 installs, stop/remove service `runner` using the **old Compose file**
   before replacing it with `dokploy-actions-runner`; catalog installs already use
   that name. Default shell Node changes from 18 to 24.
3. Use the complete updated blueprint, retaining intended scope/name/labels/group
   and reviewed resource limits. Remove custom binary patches, update-disabling
   flags and obsolete entrypoints; an image-only override may retain them. Recreate
   without carrying runner credentials or mutable caches forward. OS/tool updates
   require a new image and recreation, not a restart of the unchanged pin.
4. Verify one Idle runner, the reviewed Runner Core/default Node path/version,
   representative jobs and successful restart. Check graceful deregistration in a
   maintenance test; local listener health alone is insufficient. Rotate credentials
   only after stopping with the old PAT; clean up canaries and revoke test tokens.
5. On failure, stop/remove the new runner with its valid credential, restore the
   saved Compose/environment/digest and recreate the original service. Verify one
   registration and a known job. A rollback restores the old vulnerabilities too;
   record the failure and a forward-fix deadline. Keep installation-specific plans
   private rather than committing customer infrastructure into this repository.
