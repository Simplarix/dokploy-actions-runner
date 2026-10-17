# Validation

## Live use — 17 October 2026

A repository-scoped runner has been deployed through Dokploy and used successfully
for real CI jobs. Dependency installation, user-level tooling, unit tests, an
application build and artifact handoff completed successfully. After a user-operated
Stop → Deploy cycle, the runner registered again, returned to Idle and executed
another job; only one runner with its configured name was present.

The deployment used the release-candidate blueprint with additional CPU/memory
limits. Project names, credentials, infrastructure details and private run links
are intentionally omitted. These observations establish this repository-runner
path, not every supported configuration or a general performance benchmark.

Live organization/group registration, parallel independent deployments, the
catalog preview/import path, exact in-place restart behavior, runner auto-update
and complete deregistration during shutdown have not been independently verified.
A new registration after Stop → Deploy is not proof of every shutdown step.

## Automated checks

| Check | Coverage |
| --- | --- |
| `python scripts/validate.py` | JSON/TOML/YAML, metadata ID/version/logo, security defaults, explicit environment forwarding, Compose rendering and startup validation. |
| `python -m unittest discover -s tests -v` | Nine test methods, including invalid/missing inputs, both scopes, isolated project configuration, `.env` injection and diagnostics that do not print the token. |
| `python scripts/test_container.py` | Pinned image and actual upstream entrypoint; non-root execution, writable directories, listener liveness, automatic restart, graceful restart/stop and hard-kill recovery with mocked token, registration/removal and listener commands. Scenario networking is disabled. |
| Upstream `node build-scripts/generate-meta.js --check` | Dokploy metadata structure, folder/ID match and logo existence. |

The offline container scenarios passed locally on Linux ARM64 through Docker
Desktop and on GitHub-hosted Ubuntu 24.04 AMD64. They also check the actual shipped
runner binary's version. Mock tests do not authenticate against GitHub, execute
real workflows or prove GitHub accepts registration/removal requests.

Successful project CI evidence:

- [Release-candidate commit validation](https://github.com/Simplarix/dokploy-actions-runner/actions/runs/38982581148)
- [Release-candidate tag validation](https://github.com/Simplarix/dokploy-actions-runner/actions/runs/38982743557)
- [Current validation workflow](https://github.com/Simplarix/dokploy-actions-runner/actions/workflows/validate.yml)

CI is required to pass on the exact commit before publishing a release. No
throughput, percentage speedup or monthly cost-saving claim is made.

## Live acceptance checklist

Use private disposable targets, restricted short-lived PATs and a separate Dokploy
test project. Preserve the Compose environment mapping and `$$` escapes. Follow the
[setup guide](../README.md#deploy-in-dokploy); do not publish secrets or resolved
Compose/inspection output.

1. **Repository:** set `RUNNER_SCOPE=repo`, a real `REPO_URL`, empty `ORG_NAME`, a
   unique `RUNNER_NAME` and matching labels. Deploy and confirm exactly one Idle
   runner in GitHub. Run the [repository smoke workflow](../examples/workflows/repository-smoke.yml).
2. **Organization:** create a restricted group such as `trusted-builds`; set
   `RUNNER_SCOPE=org`, its `ORG_NAME`, empty `REPO_URL` and that `RUNNER_GROUP`.
   Confirm membership and repository access, then run the
   [organization smoke workflow](../examples/workflows/organization-smoke.yml).
3. **Parallel deployment:** deploy a second independent service with a different
   name and a unique additional label. Dispatch a 60-second test job to each
   unique label and verify their execution overlaps. Stop one while idle and
   confirm the other still accepts jobs. Do not scale replicas sharing a name.
4. **Restart/redeploy:** while idle, restart and separately recreate each scope's
   container. Confirm one returning runner with the intended name/labels/group
   and successful subsequent smoke jobs. Record whether a container was recreated;
   do not infer an in-place restart solely from a new GitHub runner ID.
5. **Deregistration:** gracefully stop each scope while its PAT remains valid.
   Confirm its GitHub entry disappears, rather than merely becoming Offline.
   Start and test again; stop before permanently deleting the test service.
6. **Failures/rotation:** on a disposable deployment, test hard-kill recovery with
   the same runner name and credential rotation using Stop → update PAT → Deploy.
   Confirm malformed input is rejected without printing credentials. Remove stale
   GitHub entries manually after permanent host loss when necessary.
7. **Boundaries:** verify representative shell/JavaScript/setup actions, non-root
   execution and absence of Docker daemon access. An inherited-token check does
   not establish isolation from malicious jobs. Record auto-update only if observed.
8. **Catalog:** after an upstream PR preview exists, import it in Dokploy and repeat
   the relevant checks; confirm generated names differ across imports. Mark any
   unperformed check as pending. Stop test services, verify cleanup and revoke PATs.
