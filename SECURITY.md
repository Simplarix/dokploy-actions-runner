# Security model

Use this template only for repositories and workflows you trust. Restrict runner
groups to intended repositories/workflows and review workflow changes. Untrusted
fork and `pull_request_target` code can compromise a self-hosted runner; see
[GitHub's secure use reference](https://docs.github.com/en/actions/reference/security/secure-use).

## Container and job boundary

The runner uses a non-root account, drops all capabilities and enables
`no-new-privileges`. There is no privileged mode, Docker socket, host mount,
inbound port or host networking. The root filesystem stays writable for
registration and user-level tooling.

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
rejected without printing values. The image entrypoint un-exports the PAT
before launching the listener, reducing ordinary workflow environment exposure.
This is not secret isolation: Docker/Dokploy administrators and malicious code in
the same container may recover startup environment, process memory, arguments or
runner credentials. Do not share credentials across unrelated trust domains.

The lifecycle supervisor retains the PAT for deregistration. Keep the local
.env file private and use dummy credentials for offline testing.

## Runtime and image limits

The fixed PATH selects the embedded Node24 for shell steps. The template
rejects versions below 24.22.3 and the image entrypoint checks its exact
build-time runtime version. GitHub selects JavaScript action runtimes separately
and routes legacy Node20 declarations to Node24. The current image includes
only the Node24 Linux executable.

The image still has scanner findings in other components. The
[maintenance guide](docs/MAINTENANCE.md#reviewed-baseline) documents the scan
and verified runtime. Runner self-updates are disabled to preserve the image's
runtime. Rebuild and redeploy for Runner, Node, Git LFS, or Ubuntu security fixes.
The startup gate runs at process startup and does not police running jobs.

## Reporting

Use private GitHub vulnerability reporting if enabled, or contact the maintainers
through their GitHub profile. Include the image digest, platform, affected
configuration and a redacted reproduction. Do not publish active credentials.
Image/runner defects may also need reporting to their upstream maintainers.
