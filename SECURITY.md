# Security model

Use this template only for repositories and workflows you trust. Restrict runner
groups to intended repositories/workflows and review workflow changes. Untrusted
fork and `pull_request_target` code can compromise a self-hosted runner; see
[GitHub's secure use reference](https://docs.github.com/en/actions/reference/security/secure-use).

## Container and job boundary

The runner uses a non-root account, drops all capabilities and enables
`no-new-privileges`. There is no privileged mode, Docker socket, host mount,
inbound port or host networking. The root filesystem stays writable for
registration, runner updates and user-level tooling.

Jobs share the same account, workspace and tool cache over time. A container is
not a VM or a per-job isolation boundary. Separate trust domains onto dedicated
hosts/VMs where needed; patch the host kernel, Docker and runner image. Dokploy
network isolation does not block access to private networks, host services or
cloud metadata; apply an appropriate egress policy. Labels are not authorization.

Docker/container actions, job containers, service containers and local Docker
builds are unsupported. A Docker CLI is not a daemon. Mounting its socket grants
effective host control even with a read-only mount; privileged Docker-in-Docker
adds another high-risk boundary. Review such workloads separately.

## Credentials

The seven operator inputs are explicitly allowlisted. Invalid configuration is
rejected without printing values. The upstream entrypoint un-exports the PAT
before launching the listener, reducing ordinary workflow environment exposure.
This is not secret isolation: Docker/Dokploy administrators and malicious code in
the same container may recover startup environment, process memory, arguments or
runner credentials. Do not share credentials across unrelated trust domains.

`UNSET_CONFIG_VARS` remains `false` because clearing the PAT breaks the inspected
upstream deregistration trap. Keep `.env` ignored/private with mode `0600`; never
publish real tokens, resolved Compose, inspection or environment dumps. Automated
offline tests use dummy credentials.

## Runtime and image limits

The fixed PATH selects the genuine embedded Node24 for shell steps. Startup
rejects a missing slot, a different default path or Node24 below 24.22.1. GitHub
selects JavaScript action runtimes separately; successful migration of a Node20
action does not establish compatibility for every legacy action. Prefer actions
that declare Node24 and avoid insecure-runtime opt-outs.

The image still contains EOL distro Node18, genuine Node20 compatibility binaries,
AMD64 Alpine slots and vulnerabilities in other tools. They are not patched or
removed by PATH, and explicit paths/workflow overrides can still select them.
This template does not satisfy a zero-EOL or zero-High/Critical-image policy.
See the [reviewed baseline and findings](docs/MAINTENANCE.md#reviewed-baseline).

Runner self-updates remain enabled and replace `bin`/`externals`; the initial
image digest does not attest the post-update filesystem. No local binary overlays
are applied. Check versions after updates and follow the
[maintenance process](docs/MAINTENANCE.md) for OS/tool fixes and runtime-major changes.
The startup gate checks startup/restart; it does not police a running workflow.

## Reporting

Use private GitHub vulnerability reporting if enabled, or contact the maintainers
through their GitHub profile. Include the image digest, platform, affected
configuration and a redacted reproduction. Do not publish active credentials.
Image/runner defects may also need reporting to their upstream maintainers.
