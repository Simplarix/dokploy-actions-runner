# dokploy-actions-runner

[![Validation](https://github.com/Simplarix/dokploy-actions-runner/actions/workflows/validate.yml/badge.svg)](https://github.com/Simplarix/dokploy-actions-runner/actions/workflows/validate.yml)
[![Release](https://img.shields.io/github/v/release/Simplarix/dokploy-actions-runner)](https://github.com/Simplarix/dokploy-actions-runner/releases)
[![MIT license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Self-hosted GitHub Actions runners for Dokploy, community-maintained by
[Simplarix](https://github.com/Simplarix). Each deployment runs one independent
repository or organization runner using the maintained
[myoung34 image](https://github.com/myoung34/docker-github-actions-runner).

- Ubuntu 24.04, Runner **2.338.1**, pinned to a multi-architecture image digest.
- Native `linux/amd64` and `linux/arm64`; default shell Node **24.22.1**.
- Non-root, all capabilities dropped, `no-new-privileges` enabled.
- No privileged mode, Docker socket, host mounts or published ports.

Use with trusted workflows on **GitHub.com** in Dokploy **Compose** mode.
Docker/container actions, service containers, Docker builds, Enterprise Server,
Stack/Swarm and per-job disposable environments are unsupported. Read
[SECURITY.md](SECURITY.md) before deployment; the image retains known vulnerabilities.

## Deploy in Dokploy

Select **GitHub Actions Runner** from the official
[Dokploy catalog](https://github.com/Dokploy/templates/tree/canary/blueprints/dokploy-actions-runner).
Catalog updates become available after the corresponding Dokploy PR is merged;
existing services require an explicit update. To use this repository revision
instead, create a **Docker Compose → Raw** service and paste
[docker-compose.yml](blueprints/dokploy-actions-runner/docker-compose.yml).

The host needs outbound HTTPS/DNS and access to `ghcr.io`, plus CPU, memory and
disk sized for your jobs. No domain or inbound runner port is required.

1. In Dokploy **Environment**, enter the following and supply your GitHub PAT:

   ```dotenv
   ACCESS_TOKEN=
   RUNNER_SCOPE=repo
   REPO_URL=https://github.com/YOUR-OWNER/YOUR-REPO
   ORG_NAME=
   RUNNER_NAME=dokploy-repo-01
   LABELS=dokploy,repo-ci
   RUNNER_GROUP=Default
   ```

2. Deploy and confirm `Listening for Jobs` in the logs and exactly one **Idle**
   runner under repository **Settings → Actions → Runners**. Local container
   health alone does not prove GitHub readiness.
3. Run [repository-smoke.yml](examples/workflows/repository-smoke.yml) in the target
   repository, matching its `runs-on` labels to your configuration.

Catalog imports generate a unique `dokploy-${uuid}` name and leave the PAT and
target blank. Keep the explicit `environment:` mapping and inline `$$` escapes:
Dokploy's `.env` provides Compose interpolation, not automatic container injection.
Do not add `env_file: .env` or forward unrelated variables. Enter the token without
literal quotes, spaces or line breaks.

### Organization runners and multiple repositories

Use the same Compose file with an org-capable PAT and these environment values:

```dotenv
ACCESS_TOKEN=
RUNNER_SCOPE=org
REPO_URL=
ORG_NAME=YOUR-ORG
RUNNER_NAME=dokploy-org-01
LABELS=dokploy,org-ci
RUNNER_GROUP=Default
```

In organization **Settings → Actions → Runner groups → Default**, configure
**Repository access** for all or selected repositories. A custom group must exist
before setting `RUNNER_GROUP` to its name. Runner groups control access; labels
select jobs. See [GitHub's group guide](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/manage-access).

In each allowed repository, route jobs with:

```yaml
jobs:
  build:
    runs-on:
      group: Default
      labels: [self-hosted, linux, dokploy, org-ci]
    steps:
      - run: node --version
```

The [organization smoke workflow](examples/workflows/organization-smoke.yml) uses
`trusted-builds`; adapt that group and its labels to your deployment.

### Credentials

Create a [fine-grained PAT](https://github.com/settings/personal-access-tokens/new)
in your personal account, using the intended repository owner/organization as
**Resource owner**. The account needs administrative access to the target.

| Scope | Fine-grained permission | Classic PAT alternative |
| --- | --- | --- |
| Repository | Selected repository, **Administration: Read and write** | `repo` |
| Organization | Organization **Self-hosted runners: Read and write** | `admin:org`; GitHub also documents `repo` for private repositories |

Complete required organization approval/SSO and rotate before expiry. The image
uses the PAT to obtain fresh registration/removal tokens. The one-hour token from
**New self-hosted runner** is unsuitable for unattended restarts. See the
[GitHub runner API](https://docs.github.com/en/rest/actions/self-hosted-runners).
Store credentials only in Dokploy Environment or an ignored private `.env` with
mode `0600`; never share resolved Compose, inspection or environment dumps.

## Configuration

| Variable | Contract |
| --- | --- |
| `ACCESS_TOKEN` | Required PAT; letters, digits and underscores; no whitespace or placeholder |
| `RUNNER_SCOPE` | Required: exactly `repo` or `org` |
| `REPO_URL` | Required for `repo`: `https://github.com/OWNER/REPO`, without `.git`, trailing slash, query or fragment; blank for `org` |
| `ORG_NAME` | Required for `org`: organization slug, not a URL; blank for `repo` |
| `RUNNER_NAME` | Required, unique in its scope; 1–64 letters/digits/`.`, `_`, `-`; starts with letter/digit |
| `LABELS` | Required comma-separated labels without spaces; letters/digits/`.`, `_`, `-`; each starts with letter/digit |
| `RUNNER_GROUP` | Defaults to `Default`; existing org group, 1–100 letters/digits/spaces/`.`, `_`, `-`; starts with letter/digit; repo scope must use `Default` |

GitHub adds `self-hosted`, `linux` and the actual architecture label. Each runner
handles **one job at a time**. Add capacity with separate deployments using unique
names; identical labels form a pool. Do not scale replicas with the same name:
upstream replacement registration can disconnect the other runner.

Default shell `node` uses `/actions-runner/externals/node24/bin/node`. Startup
rejects a missing slot, another default path or Node24 below 24.22.1. JavaScript
action runtime selection is controlled separately by GitHub. Prefer Node24 actions;
use `actions/setup-node` with an explicit version for npm or a build runtime.

## Operation

The upstream entrypoint obtains fresh tokens, replaces registration under the
configured name, runs the listener and attempts deregistration on graceful exit.
Runner self-updates remain enabled. Presence-based `EPHEMERAL` and
`DISABLE_AUTO_UPDATE` flags are deliberately omitted; even `false` would enable them.

Wait for Idle before stopping or updating. Keep the PAT valid until deregistration
finishes; the two-minute stop grace period does not guarantee a running job will
finish. For PAT rotation: stop with the old PAT, save the new PAT, deploy and verify
Idle. Abrupt host loss or failed API access can leave an Offline record; reuse the
same name to recover, or remove stale entries after permanent removal.

Workspace and tool cache survive restarts and successive jobs, but disappear on
container recreation. There are no durable volumes or per-job isolation. Use job
artifacts for outputs, monitor disk use, and size resource limits for your host.
The healthcheck checks only the listener; an unhealthy status alone does not cause
Compose to restart a container. Logs rotate at three 10 MB files.

For image updates, migration, rollback and validation, see the
[maintenance guide](docs/MAINTENANCE.md). When upgrading from v0.1.0, stop/remove
the old `runner` service before installing the renamed `dokploy-actions-runner`
service. Default shell Node changes from 18 to 24; test applications/native modules.
Catalog installs already use the new service name.

For a local deployment, copy `.env.example` to `.env`, run `chmod 600 .env` and edit
it privately, then:

```bash
docker compose --env-file .env -p repo-ci-01 \
  -f blueprints/dokploy-actions-runner/docker-compose.yml up -d
```

Use distinct project names, env files and runner names for independent deployments.
Your shell's variables override `.env`; clear stale runner variables first.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Compose/startup rejects configuration | Fill required Environment values; clear the unused target; follow the reported format; keep the explicit environment mapping and `$$` escapes |
| Registration returns 401/403/404 | PAT expiry, target admin access, resource selection, org approval/SSO and runner policy |
| Group missing or jobs remain queued | Group must exist and allow the repository; all job labels must match; runner must be online and idle |
| Docker or sudo operations fail | Unsupported by the security defaults; use shell/JavaScript actions and user/tool-cache installs |
| Runner disconnects or leaves an Offline entry | Check duplicate names, outbound DNS/HTTPS, PAT validity and graceful cleanup |
| Runtime gate fails | Update the image/template; do not bypass the gate or select distro Node18 |

See [CONTRIBUTING.md](CONTRIBUTING.md) for development checks. Original project
files are [MIT licensed](LICENSE); the external image and runner retain their own
licenses. This community template is not an official GitHub image.
