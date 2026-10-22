# Upstream research

For the current image, runtime routing, security findings and source revisions, see
[the 22 October 2026 review](RUNTIME-REVIEW.md). The table below is historical.
The local blueprint now follows the catalog’s service key and env-array format.

Reviewed on **17 October 2026**, before implementation. These sources determined
the configuration; they are not evidence of a live deployment.

| Primary source | Decision |
| --- | --- |
| [Dokploy templates contribution guide](https://github.com/Dokploy/templates/blob/canary/CONTRIBUTING.md) and [metadata generator](https://github.com/Dokploy/templates/blob/canary/build-scripts/generate-meta.js) | Keep `docker-compose.yml`, `template.toml`, `meta.json` and logo in `blueprints/dokploy-actions-runner/`; match ID to folder; no root metadata registry, ports, fixed container name or custom networks. |
| [Dokploy template processor](https://github.com/Dokploy/dokploy/blob/canary/packages/server/src/templates/processors.ts) | Both env arrays and key/value tables are accepted; use `[config.env]`. The processor supports `${uuid}` for unique default names. Empty domains/mounts are valid. |
| [Dokploy Compose documentation](https://docs.dokploy.com/docs/core/docker-compose) | UI Environment becomes `.env` and is not automatically injected. Explicit interpolation allowlists inputs; inline startup checks avoid fragile repository file mounts. Target Compose mode. |
| [Maintained runner image](https://github.com/myoung34/docker-github-actions-runner), [release 2.338.0](https://github.com/myoung34/docker-github-actions-runner/releases/tag/2.338.0), [versioned entrypoint](https://github.com/myoung34/docker-github-actions-runner/blob/2.338.0/entrypoint.sh), [usage](https://github.com/myoung34/docker-github-actions-runner/wiki/Usage) | Use upstream non-root support, runtime PAT exchange, `--replace`, signal cleanup and `dumb-init`; do not reimplement a runner. Do not persist configuration or enable `UNSET_CONFIG_VARS`; omit presence-based ephemeral/disable-update flags. |
| [GitHub self-hosted runner concepts](https://docs.github.com/en/actions/concepts/runners/self-hosted-runners) | Distinguish repository and organization scopes; one persistent runner per deployment, with operator-managed capacity. |
| [GitHub runner API](https://docs.github.com/en/rest/actions/self-hosted-runners) | Prefer scoped fine-grained PAT permissions; registration/removal tokens are short-lived and unsuitable as deployment credentials. |
| [GitHub workflow routing](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/use-in-a-workflow) and [runner groups](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/manage-access) | Supply unique names, custom labels and existing organization groups. Require matching labels/group policies; do not advertise repository-level custom groups. |
| [GitHub runner reference](https://docs.github.com/en/actions/reference/runners/self-hosted-runners) and [security reference](https://docs.github.com/en/actions/reference/security/secure-use) | Keep runner updates enabled, document connectivity and Docker limitations, restrict to trusted workflows, and explicitly distinguish containers from per-job isolation. |

The registry manifest was resolved directly with:

```bash
docker buildx imagetools inspect \
  ghcr.io/myoung34/docker-github-actions-runner:2.338.0-ubuntu-noble
```

The multi-architecture index was
`sha256:2112bde2ee92b7480babfbe3043d0461e322b97ca01e6ac94698895f3dc1f528`,
advertising `linux/amd64` and `linux/arm64`. That exact image was used for local
container tests. Metadata/image versions must move together on update.
