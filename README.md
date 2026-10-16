# dokploy-actions-runner

**Self-hosted GitHub Actions runners, deployed as independent Dokploy Compose services.**

One deployment runs one Linux runner for a repository or organization. Deploy the
template again to add capacity or separate projects, labels and runner groups.
The template uses the maintained
[myoung34/docker-github-actions-runner](https://github.com/myoung34/docker-github-actions-runner)
image; its upstream entrypoint owns registration, execution and deregistration.

- Ubuntu 24.04 image, pinned to runner **2.338.0** and a multi-architecture digest.
- Native `linux/amd64` and `linux/arm64`; no forced architecture or emulation.
- Explicit environment forwarding and validation before registration.
- Non-root execution, all capabilities dropped, privilege escalation disabled.
- No privileged mode, host Docker socket, host directory mounts or published ports.
- No custom runner image, controller, database, autoscaler or shared state.

This MVP targets **GitHub.com**, Dokploy's **Docker Compose** deployment mode and
trusted workflows. It does not support Enterprise Server, Docker Stack/Swarm,
automatic scaling or disposable environments for every job. See
[security and limitations](SECURITY.md) before allowing repositories to use it.

## Deploy in Dokploy

You need a Dokploy server with outbound HTTPS/DNS access, registry access to
`ghcr.io`, permission to administer runners in GitHub, and enough disk, memory and
CPU for your jobs. No inbound runner port or domain is needed. Size the host for
the jobs you run; this template intentionally imposes no universal resource limit.

1. Create a **Docker Compose** service in a Dokploy project. Select **Compose**,
   not Stack, and use the **Raw** source.
2. Paste [docker-compose.yml](blueprints/dokploy-actions-runner/docker-compose.yml)
   into its Compose editor. The entire startup check is inline; there are no extra
   files to mount or images to build.
3. Paste the following into the service's **Environment** editor. Supply your PAT
   and real repository URL. Give every active runner in the same GitHub scope a
   distinct name.

   ```dotenv
   ACCESS_TOKEN=
   RUNNER_SCOPE=repo
   REPO_URL=https://github.com/YOUR-OWNER/YOUR-REPO
   ORG_NAME=
   RUNNER_NAME=dokploy-repo-01
   LABELS=dokploy,repo-ci
   RUNNER_GROUP=Default
   ```

4. Save and deploy. Look for `Listening for Jobs` in the runner logs and verify
   the runner is **Idle** in GitHub → repository **Settings → Actions → Runners**.
   A running or locally healthy container alone does not prove GitHub readiness.
5. Copy [repository-smoke.yml](examples/workflows/repository-smoke.yml) into the
   target repository's `.github/workflows/` directory and run it manually. Its
   labels must match the deployment.

This project is not yet published in Dokploy's template catalog. For catalog
maintainers, the self-contained blueprint also includes
[template.toml](blueprints/dokploy-actions-runner/template.toml),
[meta.json](blueprints/dokploy-actions-runner/meta.json) and an original SVG logo.
Catalog imports generate `dokploy-${uuid}` names and leave the credential and
target blank for you to fill in before deploying.

### Organization runners

Use the same Compose file and change these environment entries:

```dotenv
RUNNER_SCOPE=org
REPO_URL=
ORG_NAME=YOUR-ORG
RUNNER_NAME=dokploy-org-01
LABELS=dokploy,org-ci
RUNNER_GROUP=trusted-builds
```

Create `trusted-builds` in the organization's **Settings → Actions → Runner groups**
first, and grant the intended repositories access. Group availability and policy
depend on your GitHub account. `Default` selects the default group; this template
does not create groups. A custom group applies only to organization runners.
Run [organization-smoke.yml](examples/workflows/organization-smoke.yml) to check
both group and label routing. See GitHub's
[group management](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/manage-access)
and [workflow routing](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/use-in-a-workflow)
guides.

### Credentials

Use a **personal access token**, not the short-lived token from **New self-hosted
runner**. The image obtains fresh runner registration tokens at startup and
shutdown. A manually copied runner token expires after one hour and cannot provide
reliable unattended restarts.

Prefer a fine-grained PAT limited to the intended resource owner:

| Scope | Fine-grained permission | Classic PAT alternative |
| --- | --- | --- |
| Repository | Selected repository, **Administration: Read and write** | `repo` |
| Organization | **Self-hosted runners: Read and write** on the organization | `admin:org`; GitHub also documents `repo` for private repositories |

The token owner needs administrative access to the target. Complete any required
organization approval or SSO authorization. Use an expiry and rotate before it
expires. These are the permissions documented for GitHub's
[runner registration/removal API](https://docs.github.com/en/rest/actions/self-hosted-runners).
Local validation checks token syntax, not authenticity, approval or permissions.

Store the PAT only in Dokploy Environment or an ignored private `.env`. Restrict
Dokploy and Docker administrator access. Never put a PAT in Compose source,
`template.toml`, workflow YAML, a URL or a bug report. Do not print `docker compose
config`, `docker inspect` or `env` output containing real credentials.

### The Dokploy `.env` pitfall

[Dokploy saves UI variables to `.env`](https://docs.dokploy.com/docs/core/docker-compose).
That file supplies Compose interpolation; it does **not** automatically inject
variables into a container. This template explicitly maps `ACCESS_TOKEN` and the
six configuration inputs under `environment:`. Required values use `${VAR:?message}`
so an empty or missing PAT fails before container creation.

Do not remove that mapping or add `env_file: .env`. Forwarding the entire file also
allows unrelated secrets and upstream behavior flags into the runner. The inline
validation uses `$$` so shell variables are expanded inside the container. Preserve
those escapes when pasting the Compose file.

Paste the token value without literal quotes, spaces or line breaks in Dokploy.
Do not set `ACCESS_TOKEN=${ACCESS_TOKEN}` or paste an `export` command. The startup
check rejects unresolved placeholders and malformed values without printing them.

## Configuration

| Input | Required | Contract |
| --- | --- | --- |
| `ACCESS_TOKEN` | Yes | GitHub PAT; letters, digits and underscores only; no whitespace or placeholder |
| `RUNNER_SCOPE` | Yes | Exactly `repo` or `org` |
| `REPO_URL` | For `repo` | `https://github.com/OWNER/REPO`, without `.git`, trailing slash, query or fragment; blank for `org` |
| `ORG_NAME` | For `org` | Organization slug, not a URL; blank for `repo` |
| `RUNNER_NAME` | Yes | Unique in its GitHub scope; 1–64 letters, digits, `.`, `_`, `-`; starts with letter/digit |
| `LABELS` | Yes | Comma-separated custom labels using letters, digits, `.`, `_`, `-`; no spaces; each starts with letter/digit |
| `RUNNER_GROUP` | No | Defaults to `Default`; custom organization group must already exist; 1–100 characters using letters, digits, spaces, `.`, `_`, `-`; starts with letter/digit |

GitHub also adds `self-hosted`, `linux` and the real architecture label. Do not
mislabel an ARM64 host as `x64`. Labels select jobs; they are not access controls.
Runner groups and repository permissions control access.

Upstream behavior flags are deliberately fixed or omitted. Runner auto-updates
remain enabled. `EPHEMERAL` and `DISABLE_AUTO_UPDATE` are **absent**: upstream treats
any nonempty value, including `false`, as enabling those options.

## Multiple runners

Create a separate Dokploy Compose service for every runner. Each gets its own
container, filesystem, configuration and deployment lifecycle. No fixed container
name, shared volume or shared application network is declared.

| Dokploy service | Scope/target | Runner name | Labels | Group |
| --- | --- | --- | --- | --- |
| frontend-ci-01 | repo: `acme/frontend` | `frontend-ci-01` | `dokploy,frontend` | `Default` |
| frontend-ci-02 | repo: `acme/frontend` | `frontend-ci-02` | `dokploy,frontend` | `Default` |
| backend-ci | org: `acme` | `backend-ci-01` | `dokploy,backend` | `trusted-builds` |

The two frontend runners can process two jobs concurrently. Give them the same
labels for a pool, or different labels to route distinct workloads. Each runner
processes one job at a time. Use a separate PAT per trust boundary when practical.

**Do not scale one service with replicas.** Its explicit name is reused and the
upstream `--replace` registration can disconnect another runner with that name.
Avoid overlapping old/new containers during updates. Never deploy two live copies
with the same scope and name.

## Lifecycle and maintenance

On every start the wrapper validates inputs and `exec`s the image's entrypoint.
Upstream obtains a fresh registration token, clears local registration files and
registers the fixed name with `--replace`. No runner configuration volume is used.
This makes restart/recreation recoverable without preserving obsolete credentials.

`restart: unless-stopped` restarts exited containers; a manual stop stays stopped.
The image's `dumb-init` forwards termination signals and reaps children. On normal
exit or `SIGTERM`, upstream attempts deregistration using a fresh token. The
two-minute grace period gives cleanup time; it does not guarantee a running job
will finish. Drain or wait for idle runners before maintenance.

`SIGKILL`, host loss, failed API access or an expired PAT can leave an offline
GitHub record. Restarting with the **same name** uses replacement registration.
After permanent removal or a name change, remove any stale record in GitHub's
runner settings. Stop a deployment gracefully before deleting it or revoking its
token. Rotate by stopping with the old credential, saving the new PAT and
redeploying; verify the runner returns to Idle.

The work directory and tool cache survive container restarts and successive jobs,
but disappear when the container is recreated. There are no durable volumes.
Recreation is not per-job isolation; use workflow artifacts for outputs you need
to retain. The healthcheck verifies the listener process only. Docker Compose does
not automatically restart a container merely because its healthcheck is unhealthy.
Logs rotate at three 10 MB files; monitor workspace disk use as jobs accumulate.

The digest makes deployments reproducible. Auto-update covers the runner binary,
not the OS or tools. Review upstream image releases, update the tag **and digest**,
update the metadata version, validate, and redeploy while idle. Dependabot proposes
image/development dependency updates; CI requires matching metadata, so image
updates may need a manual metadata edit. Do not let a pin become an excuse to stop
updating. GitHub documents update deadlines in its
[runner reference](https://docs.github.com/en/actions/reference/runners/self-hosted-runners).

## Local deployment and validation

For local deployment, copy `.env.example` to `.env`, restrict permissions with
`chmod 600 .env`, then edit it privately. Run from the repository root:

```bash
docker compose --env-file .env -p repo-ci-01 \
  -f blueprints/dokploy-actions-runner/docker-compose.yml up -d
docker compose --env-file .env -p repo-ci-01 \
  -f blueprints/dokploy-actions-runner/docker-compose.yml logs -f runner
```

Use different `-p` project names, environment files and `RUNNER_NAME` values for
independent local deployments. Your shell's variables override `.env` values in
normal Compose commands; clear stale runner variables before deployment.

Development checks require Python 3.11+ and Docker Compose v2+:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python scripts/validate.py
python -m unittest discover -s tests -v
# Optional: validate private deployment syntax without printing credentials.
python scripts/validate.py --env-file .env
# Needs a Docker daemon and registry access to pull the pinned image.
python scripts/test_container.py
```

CI runs the same checks on GitHub-hosted runners without GitHub credentials.
The container tests disable networking and substitute mock configuration, token
and listener commands, while retaining the real pinned image and lifecycle
entrypoint. They verify non-root execution, routing arguments, `.env` forwarding,
token un-export, writable directories, liveness, automatic restart after listener
failure, orderly restart/stop and hard-kill
recovery. They also run the actual shipped runner binary's version command.
They do **not** prove real GitHub registration, deregistration, network availability
or job execution. See [validation evidence and live checklist](docs/VALIDATION.md).

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Compose refuses to deploy | Fill the four required inputs; do not leave the PAT blank. Check the service's Environment editor, not only project-level values. |
| `Configuration error` then restart loop | Correct the named variable, clear the unused target, save and redeploy. No API call happens before this check. Stop the service while investigating. |
| Registration returns 401/403/404 | Check PAT expiry, admin access, exact owner/repository, fine-grained resource selection, org approval, SSO and runner policy. GitHub can hide inaccessible targets behind 404. |
| PAT set in Dokploy but runner cannot authenticate | Keep the explicit `ACCESS_TOKEN: ${ACCESS_TOKEN:?...}` mapping; `.env` is not automatic container injection. Remove literal quotes, placeholders and newlines. |
| Runner group not found | Create the exact group in the organization, check account availability, or use `Default`. Do not set a custom group with `repo` scope. |
| Runner is online but job stays queued | All `runs-on` labels must match; check architecture, group access and whether the single runner is busy. |
| `Cannot connect to the Docker daemon` | Docker builds, Docker actions, job containers and service containers are unsupported by this default. Use shell/JavaScript actions or a separately designed build service. |
| `sudo` or package installation fails | This is expected under non-root execution with no privilege escalation. Use installed tools or setup actions that write to the user/tool-cache directories. Check tool and architecture support. |
| Offline runner remains after deletion | Abrupt termination or failed cleanup leaves a record. Verify no live deployment uses it, then remove it in GitHub settings. |
| Runner keeps disconnecting | Check for another deployment with the same runner name and scope. |
| Container is healthy but GitHub shows Offline | Health is local process liveness. Check outbound DNS/HTTPS, proxy/firewall policy, GitHub status and logs. |

Never include credentials or resolved Compose/inspection output in troubleshooting
reports. Report image tag/digest, architecture, scope and redacted logs.

## Contributing and license

The blueprint follows the upstream per-template directory and metadata layout.
See [CONTRIBUTING.md](CONTRIBUTING.md) for validation and the path to a future
`Dokploy/templates` PR. A live deployment must be tested before that submission.

Original configuration, scripts, documentation and logo are [MIT licensed](LICENSE).
The external image and GitHub runner retain their own upstream licenses; this
project neither distributes a fork nor claims to be an official GitHub image.
