# Maintaining the runner image

The maintainer owns the initial image pin and this template’s tests. Operators own
redeployment of their installed services. The official Dokploy catalog is at
`Dokploy/templates:canary/blueprints/dokploy-actions-runner`.

## Detection and deadlines

- `check-updates.yml` runs daily after merge to the default branch and can be run
  manually. It fails if GitHub releases a newer Runner Core, Node releases a newer
  Node24 version, or upstream rebuilds the pinned tag with a different digest.
  Network/parser failures fail the check too. Maintainers must subscribe to Actions
  failures, review daily, and keep scheduled workflows enabled (GitHub may disable
  schedules on inactive public repositories). This is detection, not deployment.
- Dependabot checks image tags/digests weekly and opens reviewable PRs. Update the
  metadata, policy and documentation in those PRs. Both mechanisms are needed:
  a new runner tag and an OS rebuild of an existing tag are different events.
- Watch [Node security announcements](https://nodejs.org/en/blog/vulnerability),
  [runner releases](https://github.com/actions/runner/releases),
  [image releases](https://github.com/myoung34/docker-github-actions-runner/releases)
  and Ubuntu security updates. A version check does not discover every tool CVE.
  Scan candidate manifests with a current database and record unresolved findings.
- Triage security releases the same day; target tested image/catalog updates within
  48 hours and operator rollout as soon as possible. GitHub requires each runner
  update within 30 days and can stop queuing jobs sooner for critical security
  fixes. These are owner responsibilities, not an automated rollout guarantee.

## Review and release

1. Resolve the latest supported runner/image from primary sources. Inspect the
   multi-architecture index and record its AMD64/ARM64 child manifests. Verify an
   anonymous registry pull with an empty Docker config.
2. Change the Compose tag **and index digest**, `meta.json`, `runtime-policy.json`,
   README and changelog together. Keep all seven operator inputs, capabilities,
   mounts, user and registration safeguards. Do not enable `DISABLE_AUTO_UPDATE`.
3. Run `scripts/runtime_inventory.py --platform linux/amd64` and `linux/arm64`.
   It inventories every executable ELF named `node` under `/actions-runner`,
   `/usr`, and `/opt`, records hashes/architecture, executes glibc versions, and
   identifies Alpine binaries separately. Review new or removed slots explicitly;
   never satisfy a Node20 requirement by copying a Node24 binary into that path.
4. Run configuration tests and `scripts/test_container.py --platform ...` on both
   native architectures. These are mocked, offline lifecycle tests. Rosetta’s
   process naming can make the mock liveness test fail; it is not native proof.
5. Run the manual live workflow on isolated test runners with a reviewed ref:
   `python scripts/live_smoke.py --repo OWNER/REPO --ref BRANCH --output live.json`.
   The tool uses the existing `gh` token, starts two unique local runners, runs
   checkout/Node actions/setup-node/hashFiles before and after restart, verifies
   GitHub deregistration, and removes only its own test registrations. Keep the
   output free of secrets. Native deployment acceptance, org/group routing and
   Dokploy import remain separate checks; record unperformed ones.
6. Check the running listener and default Node again after a real self-update
   whenever one occurs. The updater replaces `bin` and `externals`; a new image
   digest describes only the initial state. The fixed PATH follows the canonical
   `externals/node24/bin` directory. Startup rejects a missing slot or a Node24
   version below 24.22.1; update this floor and its regression tests for future
   security releases. Review major runtime migrations explicitly. Do not apply
   local binary security overlays.
7. Publish the maintainer PR and matching Dokploy PR, using this exact blueprint.
   Run `node build-scripts/generate-meta.js --check` in the official repository.
   Import the PR preview when a Dokploy test instance is available; disclose when
   it is not. A maintainer decision is not evidence of an acceptance test.
8. After review/merge, release with linked evidence. Operators wait for idle,
   gracefully stop, update the pin and recreate; verify one Idle runner, run their
   real jobs, restart and verify removal on final stop. Do not run old/new copies
   with one name. Image recreation is required for OS/tool updates; restarting an
   unchanged digest cannot install them.

## Rollback and older local services

Record the exact previous image, Compose definition and private environment before
rollout. Stop the new runner while its credential works, restore the previous
configuration and recreate. A rollback to a vulnerable image is an emergency
availability measure; isolate it and schedule the forward fix. Do not leave it
running indefinitely.

The old maintainer blueprint used service `runner`; the published catalog uses
`dokploy-actions-runner`. Stop/remove the old service with the **old Compose file**
before installing the renamed one. Use the same scope/name and never overlap them.
Catalog users already have the correct service name. Recreate without preserving
runner credentials or mutable tool caches. See [the migration guide](MIGRATION.md).
