# Runner runtime review — 22 October 2026

## Cause and selected solution

The original index pinned Runner 2.338.0. A pin prevents unnoticed image changes,
but it also keeps OS/tool packages stale until the deployment is recreated with a
new digest. Runner self-updates cover its own `bin`/`externals`, not distro Node.
The previous upstream default was `/usr/bin/node` 18.19.1; embedded Node24 was
24.21.0, before the October security release. Node20 20.20.2 remains EOL.

We select the maintained public upstream **2.338.1-ubuntu-noble** image and set a
fixed PATH preferring its genuine embedded **Node24 24.22.1** for shell steps.
GitHub still selects JavaScript action runtimes independently. No executable is
renamed, replaced or deleted, and no self-update setting is disabled. No custom
image, package publication, application-package dependency or registry credentials are
required. This is a default-execution-path correction, **not removal of every
vulnerable component in the image**.

A custom fork solely to replace Node20 with Node24 would falsify the requested
runtime and be overwritten by self-updates. Removing upstream compatibility slots
would also change behavior. We retain the authentic slots, measure their presence
and document the remaining risks. Installations requiring zero EOL binaries or
zero High/Critical image findings need a different image policy; this PR does not
claim to meet either requirement.

## Verified sources and digests

| Component | Verified source/revision |
| --- | --- |
| Maintainer baseline | `ea5ff91f0b709b30f67f6682e5bbb48edc69f868` |
| Official catalog baseline | `Dokploy/templates:canary`, `e44418a2fc926db93a14335eb7ae9df527ac86aa` |
| Runner source | [v2.338.1](https://github.com/actions/runner/releases/tag/v2.338.1), `e78522a9a7b01c3bcd7ac0da6e3a9bb6cd513a76` |
| Image source tag | [2.338.1](https://github.com/myoung34/docker-github-actions-runner/releases/tag/2.338.1), `6943ec5c8417529c5a5d7d0bd796308b7140b0d5` |
| Selected multiarch index | `sha256:36782fe0e5994b301652408c32113a3562fabb1f0ead865ccc196d3e870f9109` |
| AMD64 child manifest | `sha256:340f69448f36fd361fc50d2aeef41bf3b4f0ddc93acaed858ccb14e7b4906ca2` |
| ARM64 child manifest | `sha256:9c86519e95cf22aa23fabbd674f648baf9aaaa44b25df442efcc4ee9b90436d3` |
| Previous multiarch index | `sha256:2112bde2ee92b7480babfbe3043d0461e322b97ca01e6ac94698895f3dc1f528` |
| Official Runner Linux x64 archive checksum | `08e9ccb3604d2462c24b5e33604dc30810296ca15cc65f23cffd4317eb144c37` |
| Official Runner Linux arm64 archive checksum | `475e0c149fd3b611610127b9664ba5bacf5c6928795cc448ab520bb5f324bede` |

Archive checksums above come from GitHub release metadata; this project consumes
the image and does not rebuild those archives. Runtime hashes are measured in the
image inventories. The index includes upstream attestation manifests; presence is
not signature verification. The image tag can be rebuilt by upstream; the digest
above is the tested snapshot. An empty Docker credential configuration successfully
pulled this digest anonymously. [Index evidence](evidence/2026-10-22/image-index.json).

## Complete Node inventory within the inspected runtime paths

| Path | AMD64 | ARM64 | Actual/default use |
| --- | --- | --- | --- |
| `/usr/bin/node` | 18.19.1 | 18.19.1 | Ubuntu package `18.19.1+dfsg-6ubuntu5`, retained; explicit invocation or overwritten PATH can still use it |
| `externals/node20/bin/node` | 20.20.2 | 20.20.2 | Authentic EOL compatibility binary; upstream flags/explicit paths may select it |
| `externals/node24/bin/node` | 24.22.1 | 24.22.1 | Default shell Node; Node24 actions and runner-internal operations |
| `externals/node20_alpine/bin/node` | 20.20.2 | absent | musl/container-job variant, outside this template’s supported workload |
| `externals/node24_alpine/bin/node` | 24.22.1 | absent | musl/container-job variant, outside this template’s supported workload |

The inventory walks `/actions-runner`, `/usr`, and `/opt` for executable ELF files
named `node`, records architecture and SHA-256, and executes the glibc binaries as
an unprivileged user without networking. It detects no additional Node binaries
in those paths. AMD64 Alpine versions initially come from embedded version strings
and release source, not execution in Ubuntu. See the separate Alpine check below.
Workflows can install additional runtimes afterwards; this is an initial-image
inventory, not a claim about arbitrary job-created files.

[AMD64 inventory](evidence/2026-10-22/runtime-amd64.json),
[ARM64 inventory](evidence/2026-10-22/runtime-arm64.json).

## JavaScript compatibility and self-updates

GitHub’s [Node20 deprecation notice](https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/)
states the Node24 default transition and September 23 removal schedule. The actual
2.338.1 source still packages Node20; the calendar alone does not prove its absence.
[HandlerFactory](https://github.com/actions/runner/blob/v2.338.1/src/Runner.Worker/Handlers/HandlerFactory.cs)
and [NodeUtil](https://github.com/actions/runner/blob/v2.338.1/src/Runner.Common/Util/NodeUtil.cs)
apply service migration flags and legacy opt-outs. Therefore PATH alone cannot
force every JavaScript action to Node24.

Real jobs in the maintainer repository executed both `using: node24` and
`using: node20` fixtures with `/actions-runner/externals/node24/bin/node` 24.22.1
on both architectures, before and after restart. Checkout v7, setup-node v7,
Node24 main/post handlers and runner-internal `hashFiles` passed. The local action
pre handler is not run by GitHub for repository-local actions; it is not claimed
as covered. This demonstrates current routing in the tested repository, not
universal Node20/Node24 compatibility or every organization’s feature-flag state.

[SelfUpdater](https://github.com/actions/runner/blob/v2.338.1/src/Runner.Listener/SelfUpdater.cs)
copies a new `externals` tree, so a local binary overlay would not survive reliably.
The fixed PATH points to that canonical tree. Startup fails closed when Node24
is missing, resolves through another path, or falls below 24.22.1. Future major
runtime transitions need template review. Updates stay enabled; no update was
available during the live test, so actual self-update execution was not observed.
The daily update check and [operator runbook](UPDATING.md) cover image recreation
for system packages, tools and revised image digests.

## Security assessment and remaining findings

[Node’s October advisory](https://nodejs.org/en/blog/vulnerability/october-2026-security-releases)
identifies 24.22.1 as a security release. Node18 and Node20 are
[EOL](https://nodejs.org/en/about/previous-releases) and are **not fixed** by this
change. Do not opt back into insecure runtimes, use `/usr/bin/node` explicitly,
or interpret retained compatibility slots as a security guarantee.

Grype **0.121.0**, database built **2026-10-22T06:29:52Z**, scanned both exact child
manifests. Both architectures report 25 Critical, 181 High, 935 Medium, 138 Low, 11
Negligible and 5 Unknown matches. The retained summaries contain every scanner match, including paths,
fix versions and source URLs; no ignored-match filter was used. Node24 24.22.1 has
zero matches in this database, but other packages do not. Scanner counts can
include multiple copies and are not a count of demonstrated exploitable paths.
No penetration test or complete source audit is claimed.

See [AMD64 scanner findings](evidence/2026-10-22/scan-amd64.json) and
[ARM64 scanner findings](evidence/2026-10-22/scan-arm64.json). Critical/High matches
include preinstalled Go tools and other dependencies. Their presence is not fixed
by PATH and their reachability has not been comprehensively established. The
unused Docker/container toolchain is not a reason to suppress its scan findings.
The user/capability/no-new-privileges/allowlist safeguards remain intact, but do not
make vulnerable tools safe for untrusted jobs.

## Alpine execution check

Both retained AMD64 musl binaries were copied from the exact pinned image and
executed as non-root, without networking, in pinned official
`node:24.22.1-alpine@sha256:06d7adf3e0ef61a13f1d28682726366f97a15aa1888c934d3ecec86c33918b53`.
They returned 20.20.2 and 24.22.1; copied hashes match the inventory. This uses
Rosetta emulation and does not enable container actions in the template.
[Execution evidence](evidence/2026-10-22/alpine-execution.json).

## Reproducing the scanner evidence

With Grype 0.121.0 and a current recorded database:

```bash
grype registry:ghcr.io/myoung34/docker-github-actions-runner@sha256:340f69448f36fd361fc50d2aeef41bf3b4f0ddc93acaed858ccb14e7b4906ca2 -o json --file grype-amd64.json
grype registry:ghcr.io/myoung34/docker-github-actions-runner@sha256:9c86519e95cf22aa23fabbd674f648baf9aaaa44b25df442efcc4ee9b90436d3 -o json --file grype-arm64.json
```

The checked-in summaries retain every match but omit unrelated scanner metadata.
They record the full-output SHA-256 and database source/time. A newer database can
change counts without any image change. Evidence hashes are listed in
[SHA256SUMS](evidence/2026-10-22/SHA256SUMS).

Tracking PRs: [maintainer #3](https://github.com/Simplarix/dokploy-actions-runner/pull/3)
and [Dokploy #1255](https://github.com/Dokploy/templates/pull/1255). The Dokploy PR
is a draft pending an isolated UI import; its CI and published preview-file checks
have passed. The prepared image-upstream proposal is in [docs/upstream](upstream/).
