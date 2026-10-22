# Validation

## Current image — 22 October 2026

Runner 2.338.1, index `sha256:36782fe0e5994b301652408c32113a3562fabb1f0ead865ccc196d3e870f9109`.

| Check | Result |
| --- | --- |
| Configuration and update/inventory regression suite | 13 tests pass, including malformed secrets, allowlist bypass attempts, unknown runtimes architecture mismatches and runtime-floor regressions |
| Native AMD64 and ARM64 offline lifecycle CI | [Both pass](https://github.com/Simplarix/dokploy-actions-runner/actions/runs/39816774855); repo/org routing, non-root execution, graceful stop/restart, unexpected exit and hard-kill recovery |
| Actual runner and Node executable inventory | Both architectures pass, including genuine Node20 retention and default Node24 24.22.1 |
| Real GitHub jobs before restart | [Both pass](https://github.com/Simplarix/dokploy-actions-runner/actions/runs/39816886613) |
| Real GitHub jobs after restart | [Both pass](https://github.com/Simplarix/dokploy-actions-runner/actions/runs/39817119686) |
| Live registration and final graceful removal | Two unique repository runners registered; both disappeared from GitHub after stop; temporary containers removed |
| Anonymous public image pull | Pass with empty Docker credential config |
| Image vulnerability scans | Both completed; retained findings, not a clean-image result. See [review](RUNTIME-REVIEW.md) |

The live jobs ran ARM64 natively in Docker Desktop and AMD64 under Rosetta.
Separate offline CI runs used native GitHub-hosted machines for **both**
architectures. Rosetta’s mocked-listener process-name healthcheck failed locally;
the corresponding native AMD64 test passed. Emulated execution is not presented
as native execution.

Live jobs exercised pinned checkout/setup-node actions, Node24 main/post handlers,
a Node20 declaration routed by GitHub to Node24, internal hashFiles, actual
runtime versions, zero effective capabilities, no-new-privileges, non-root
execution, and absence of an inherited PAT or Docker socket. This does not prove
secret isolation from a malicious same-user job. The [structured live evidence](evidence/2026-10-22/live-smoke.json)
records exact commits and runs without credentials.

Remaining unperformed checks: live organization/custom-group registration and
routing (no scoped org-admin credential); fresh Dokploy UI/catalog preview import
(no isolated Dokploy test instance); observed runner self-update (none available);
exhaustive third-party action compatibility; native AMD64 live jobs. The original
17 October observations below concern the **previous image**, not this update.
No existing deployment was changed.

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

### Catalog preview acceptance — 17 October 2026

The tester confirmed completion of the repository-runner preview checklist for
[Dokploy/templates PR #1234](https://github.com/Dokploy/templates/pull/1234):
Base64 import into a separate Compose test service, environment configuration,
registration as one Idle runner, a successful targeted smoke workflow and removal
of the GitHub runner entry after graceful stop. This is tester-confirmed live
acceptance, not an independently captured deployment trace. No private identifiers
or run links are published.

Live organization/group registration, parallel independent deployments, exact
in-place restart behavior and runner auto-update remain unverified. The confirmed
repository shutdown check does not establish cleanup for every scope or failure
condition.

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
