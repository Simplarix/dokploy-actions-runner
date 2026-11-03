# Maintenance

Maintainers own the image pin and template tests; operators own deployment updates.
Keep this blueprint and the official `Dokploy/templates:canary` catalog entry in sync.

## Reviewed baseline

Reviewed on **2 November 2026** for **v0.2.0**:

| Component | Result |
| --- | --- |
| Upstream image | `ghcr.io/myoung34/docker-github-actions-runner:2.338.2-ubuntu-noble` |
| Multi-architecture index | `sha256:23e3a4a1da30de5b462ad0ae13d901288e803a688075c3b9b5bb79b7148c07fa` |
| Runner / default shell Node | 2.338.2 / 24.22.1 via `externals/node24/bin/node` |
| Retained runtimes | Distro Node18 18.19.1, embedded Node20 20.20.2; AMD64 also has Node20/24 musl slots; ARM64 has no Alpine slots |
| Scanner | Grype 0.121.1, database built 2026-11-02T06:26:52Z |
| Scanner matches, each architecture | 26 Critical, 170 High, 980 Medium, 137 Low, 11 Negligible; zero matches for Node24 24.22.1 in that database |

Version 0.1.0 used embedded Node24 24.21.0 and default shell Node18. The updated
PATH and startup guard select patched Node24 but do not remove other vulnerable
components. Scan counts include duplicate components and are not proof of
exploitability or vulnerability freedom; database changes affect comparisons.
See [SECURITY.md](../SECURITY.md) and the expected executable inventory in
[runtime-policy.json](../runtime-policy.json).

**Validation:** 15 regression tests and native AMD64/ARM64 offline lifecycle CI
[passed](https://github.com/Simplarix/dokploy-actions-runner/actions/runs/41537288411).
Real GitHub jobs [before](https://github.com/Simplarix/dokploy-actions-runner/actions/runs/41538035551)
and [after restart](https://github.com/Simplarix/dokploy-actions-runner/actions/runs/41538568183)
passed with checkout/setup-node, Node24 main/post handlers, a Node20
declaration routed to Node24, internal hashFiles, restart and graceful deregistration.
Live ARM64 runs natively in Docker Desktop and AMD64 uses Rosetta; this is separate
from native CI. All Node executable hashes, including AMD64 Alpine variants, match
the versions tested on 22 October; the previous musl execution proof still applies.

The tester confirmed all six Dokploy import/operation acceptance steps for the
2.338.1 preview on 22 October. The 2.338.2 preview files and metadata are verified,
but a fresh Dokploy UI deployment of 2.338.2 is not claimed. The tester's architecture
and repo/org scope were unspecified. Live custom-group routing, native AMD64 live
jobs and an actual runner self-update remain unverified.

Current per-architecture manifests, inventories, full scanner-match summaries,
GitHub smoke results and checksums are attached to the
[v0.2.0 release](https://github.com/Simplarix/dokploy-actions-runner/releases/tag/v0.2.0).
The [22 October snapshot](https://github.com/Simplarix/dokploy-actions-runner/tree/8aecb91b31c83ad48d64aec146616206e962ed97/docs)
retains the earlier review and prepared upstream proposal. Keep future large
reports in release/CI artifacts and only their current summary here.

## Detect and review updates

- After merge to the default branch, `check-updates.yml` checks daily for newer
  Runner Core/Node24 releases and a rebuilt upstream tag digest. Runner/image
  changes and newer Node releases marked `security: true` fail the check. Node
  releases explicitly marked `security: false` produce visible workflow warnings
  and a job summary without failing it; review these for adoption through a maintained
  upstream image. Missing/invalid security metadata and network/parser errors fail
  the check. Every newer stable release in the current Node major is checked, so a
  later ordinary release cannot hide an intervening security release. Alpha/RC
  entries are excluded before stable-version parsing. Subscribe to failures and keep schedules enabled; GitHub
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

The monitor currently reports a genuine upstream gap: Node 24.22.2 is
available, but Runner 2.338.2 still bundles 24.22.1. This remains tracked in
[issue #6](https://github.com/Simplarix/dokploy-actions-runner/issues/6) and is shown
as a workflow warning because Node's index explicitly marks 24.22.2 as
`security: false`. That flag is not a blanket safety assessment or a vulnerability
scan. The tested baseline stays at the actual bundled 24.22.1; warnings do not
change runtime policy, the startup floor or deployed binaries. Adopt the update
through a tested maintained upstream image rather than a local binary overlay.

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
