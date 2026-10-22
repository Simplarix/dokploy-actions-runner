# Security model

This template is for workflows and repositories you trust. A self-hosted runner
executes repository-controlled code. Use private repositories with reviewed
workflow changes and restrict organization runner groups to the intended
repositories/workflows. GitHub's
[secure use reference](https://docs.github.com/en/actions/reference/security/secure-use)
explains why public pull requests and other untrusted contributions can compromise
self-hosted runners. Do not route untrusted fork or `pull_request_target` code here.

## Container boundary

The container runs as the image's `runner` user with all capabilities dropped and
`no-new-privileges`. No host Docker socket, privileged mode, host paths, inbound
ports or host networking are configured. The root filesystem remains writable so
the runner can register, auto-update and install user-level tools.

Container isolation is not a VM boundary. Jobs share a container and account over
time, can modify the workspace and tool cache, and can attack the runner process.
Separate trust domains onto separate hosts/VMs as appropriate. Keep Docker, the
host kernel and images patched. Dokploy's per-service networks do not block
outbound access to the host, private services or cloud metadata endpoints; apply
host/network egress policy for the workload. Never treat labels as authorization.

## Credentials

Only seven inputs are forwarded from Dokploy. The startup check rejects missing,
placeholder or malformed inputs without logging their contents. The upstream
entrypoint un-exports `ACCESS_TOKEN` before launching the listener, so ordinary
workflow environment inheritance does not include the PAT.

This is exposure reduction, **not a secret isolation guarantee**. The PAT is stored
in Dokploy's deployment environment and Docker container configuration. Docker
administrators can inspect it. Code in the same container may recover startup
environment/process memory, runner credentials or transient command arguments.
A malicious workflow must be assumed capable of compromising the runner and its
registration credential. Never share a credential across unrelated trust domains.

`UNSET_CONFIG_VARS` stays `false`: in the inspected upstream entrypoint, enabling
it clears the PAT used by the deregistration trap. Do not enable it as a supposed
security fix while expecting reliable cleanup. No real credentials are needed by
this repository's automated tests. Keep `.env` private, ignored and mode `0600`;
do not paste `docker inspect`, resolved Compose or environment dumps into reports.

## Deliberately unsupported Docker workloads

Docker/container actions, job `container:`, `services:`, local Docker builds and
Docker-based deployment actions require a reachable daemon and are unavailable
with these defaults. A Docker CLI in the image is not a running daemon.

Mounting `/var/run/docker.sock` gives workflows effective control over the Docker
host, including other Dokploy services and their secrets. A read-only socket mount
does not make Docker API commands read-only. Privileged Docker-in-Docker adds a
different high-risk boundary. Neither is a supported toggle in this template.
Design and review such workloads separately, preferably on dedicated build hosts
or a properly authenticated remote build service.

## Reporting

For a suspected vulnerability, use the repository's private GitHub vulnerability
reporting feature if enabled, or contact the maintainers through their GitHub
profile. Do not publish an exploit containing active credentials. Include the
image digest, platform, affected configuration and a redacted reproduction. Image
or runner vulnerabilities may also need reporting to their respective maintainers.

## Runtime baseline and retained vulnerabilities

The reviewed initial image is Runner 2.338.1 with embedded Node24 24.22.1.
A fixed environment PATH makes that binary the default for shell steps. This
avoids the distro Node18 default; it does not patch or remove `/usr/bin/node`,
`libnode109`, Node20 20.20.2, or AMD64 Alpine slots. They remain upstream binaries,
are inventoried, and must not be described as fixed. Node18 and Node20 are EOL.
Explicit paths, workflow PATH changes, or upstream insecure runtime opt-outs can
select them. This template is for trusted jobs, not an enforcement boundary
against a malicious workflow.

JavaScript action runtime selection belongs to GitHub’s runner, independently of
PATH. An action declaring Node20 is not proof that Node20 executes: GitHub’s
migration flags can select Node24. Conversely, a successful smoke action is not
proof of compatibility for every legacy action. Upgrade actions to Node24 and
verify your own workflows. The template never places Node24 in a Node20 slot.
Alpine slots are used for container jobs; those jobs are unsupported here.

The image scanner also reports vulnerabilities in additional shipped tools. See
[the dated review and unfiltered finding summaries](docs/RUNTIME-REVIEW.md).
A clean Node24 scan is not a clean-image claim or proof of non-exploitability.
A deployment requiring removal of all EOL binaries or zero High/Critical image
findings does not meet that policy with this template.

Self-updates remain enabled and replace the upstream `externals` tree. Local
binary replacements would be overwritten; this template makes none. Check the
running versions after an update, because the initial digest does not attest the
post-update filesystem. Follow [the image update process](docs/UPDATING.md) for OS
and tool fixes as well as the [GitHub deadlines](https://docs.github.com/en/actions/reference/runners/self-hosted-runners).

A startup runtime gate fails closed if the Node24 slot disappears, default `node`
resolves elsewhere, or its version falls below 24.22.1. This prevents silent
fallback after self-update/restart; it does not police workflow changes during a
job. Future runtime-major migrations require a reviewed template update.
