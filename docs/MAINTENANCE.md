# Maintenance

Maintainers own the image pin and template tests; operators own deployment updates.
Keep this blueprint and the official `Dokploy/templates:canary` catalog entry in sync.

## Reviewed baseline

Reviewed on **16 November 2026** for the first-party image.

| Component | Result |
| --- | --- |
| Image | GHCR package `simplarix/dokploy-actions-runner`, tag `2.338.2-node24.22.3-ubuntu-noble-r2` |
| Multi-architecture index | `sha256:67a0863b831643700c8a2870b326d6451e131fd21a69535aa29aa7693b3adad2` |
| Runner and default Node | 2.338.2 and 24.22.3 via `externals/node24/bin/node` |
| Git LFS | 3.8.1 from the official release |
| Scanner | Grype 0.121.1, database built 2026-11-16T06:30:54Z |
| Scanner matches per architecture | 1 Critical, 12 High, 321 Medium, 11 Low, 4 Negligible, 1 Unknown. No matches for the default Node 24.22.3 binary. |

The remaining Critical match is [GO-2026-6612](https://pkg.go.dev/vuln/GO-2026-6612)
in Git LFS's `golang.org/x/net` dependency. The advisory covers HTTP/2 server
handling. The workflow uses Git LFS as a client and the template publishes no
ports. Scanner matches identify components by version and do not establish reachability.

Native AMD64/ARM64 offline and inventory CI passed in the
[validation workflow](https://github.com/Simplarix/dokploy-actions-runner/actions/runs/43953646903).
Real GitHub jobs passed [before](https://github.com/Simplarix/dokploy-actions-runner/actions/runs/43953678601)
and [after restart](https://github.com/Simplarix/dokploy-actions-runner/actions/runs/43953867466).
Those runs tested repository registration, Node24 main/post handlers, a legacy
Node20 declaration routed to Node24, internal hashFiles, setup-node and graceful
deregistration on native ARM64 and emulated AMD64 in Docker Desktop. Org
registration in the Default group, native AMD64 application jobs, graceful
removal and Stop/Deploy were also exercised in Dokploy. The application pilot
uses setup-node to select its own build runtime.

The earlier third-party image review and scans are in the
[v0.2.0 release](https://github.com/Simplarix/dokploy-actions-runner/releases/tag/v0.2.0).

## Detect and review updates

- After merge to the default branch, `check-updates.yml` checks daily for newer
  Runner Core/Node24 releases and a change to the published tag digest. Runner/image
  changes and newer Node releases marked `security: true` fail the check. Node
  releases explicitly marked `security: false` produce visible workflow warnings
  and a job summary without failing it; review these for the next image build. Missing/invalid security metadata and network/parser errors fail
  the check. Every newer stable release in the current Node major is checked, so a
  later ordinary release cannot hide an intervening security release. Alpha/RC
  entries are excluded before stable-version parsing. Subscribe to failures and keep schedules enabled; GitHub
  can disable schedules on inactive public repositories. Detection does not deploy.
- Dependabot proposes weekly Ubuntu base image updates. Also watch
  [Runner](https://github.com/actions/runner/releases), [Node security](https://nodejs.org/en/blog/vulnerability),
  [Git LFS](https://github.com/git-lfs/git-lfs/releases), and Ubuntu announcements.
  Scan OS/tool packages too; a runtime version check is not a vulnerability scan.
- Triage security releases the same day; target tested catalog/image-pin updates
  within 48 hours and prompt operator rollout. GitHub requires runner updates
  within 30 days and can stop queuing jobs sooner for critical fixes; see its
  [runner reference](https://docs.github.com/en/actions/reference/runners/self-hosted-runners).
  These are maintenance responsibilities, not an automatic rollout guarantee.

## Build and test candidates

`image/Dockerfile` uses a digest-pinned Ubuntu 24.04 base and the official
GitHub Runner, Node.js and Git LFS archives, each pinned by SHA-256 per
architecture. We can rebuild the image with a newer Node24 or Ubuntu patch set
while keeping the reviewed GitHub Runner version. Runner releases still come
from GitHub. The candidate ships only the Node24 Linux runtime. GitHub routes
legacy Node20 action declarations to Node24, which the live smoke workflow
checks. Alpine slots are unnecessary for the Ubuntu shell jobs supported here.

The candidate registers with `--disableupdate` so a GitHub Runner self-update
cannot overwrite the Node version installed at build time. The image maintainer
must publish and roll out updated images as GitHub ships Runner fixes. GitHub can
stop queuing jobs if a runner is more than 30 days behind an available update,
or sooner for critical fixes. The PAT remains available to the lifecycle
supervisor for deregistration, so the trust boundary in [SECURITY.md](../SECURITY.md)
still applies to jobs running under the same account.

Build and test a local candidate on either native Linux architecture. Set
`platform` to `linux/arm64` on ARM64.

```bash
platform=linux/amd64
candidate="dokploy-runner-candidate:2.338.2-${platform##*/}"
docker buildx build --load --platform "$platform" -t "$candidate" image
python scripts/test_container.py --platform "$platform" --candidate-image "$candidate"
python scripts/runtime_inventory.py --platform "$platform" --image "$candidate"
```

The validation workflow builds the candidate and exercises the existing Dokploy
configuration with mock registration and shutdown on both architectures. With
both local candidates built and the reviewed workflow pushed, run real jobs with
`python scripts/live_smoke.py --candidate --repo OWNER/REPO --ref BRANCH --output local/live.json`.
Scan both candidate manifests before publishing the tested build to GHCR. Set `init: true`
in the Compose service so an init process reaps orphaned child processes, as in
the candidate lifecycle test. Pin the published multi-architecture digest and update the runtime policy. Replace
the deployed container when updating the image. Keep the previous pin for rollback.

## Validate and publish an image update

1. Update the digests and versions in `image/Dockerfile` from the official
   release sources and build both architectures. Choose a fresh release tag,
   incrementing the `-rN` revision for another build with the same versions.
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
5. Publish both tested architecture manifests to GHCR and combine them into
   one release tag. Verify an anonymous pull for both architectures using an
   empty Docker credential config. Pin that index digest in Compose and update
   its metadata version, runtime policy, tests and README together. A rebuild
   and recreation deliver updates because runner self-updates are disabled.
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
   and reviewed resource limits. Apply the new entrypoint and init settings from
   the complete blueprint. Recreate
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
