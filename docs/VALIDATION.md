# Validation evidence

## Local checks performed — 17 October 2026

Environment: macOS ARM64 host, Docker Desktop Linux engine **29.8.2**, Docker
Compose **5.6.0**, Python **3.12.14**, PyYAML **6.0.3**. The runtime scenarios ran
natively on the image's **linux/arm64** variant. GitHub CI subsequently exercised
the **linux/amd64** variant as documented below. Neither platform has been tested
with live Dokploy deployment or real GitHub runner registration.

| Check | Result and boundary |
| --- | --- |
| `python scripts/validate.py` | Passed: JSON/TOML/YAML, metadata version/ID/logo, allowlist, security settings, Compose model and valid startup fixture. |
| `python -m unittest discover -s tests -v` | Passed: 9 test methods including 33 invalid-input cases and 8 missing/empty required-input cases; both scopes, project separation, `.env` forwarding, fixed security flags and redacted diagnostics. |
| `python scripts/test_container.py` | Passed against the pinned image: actual runner binary version, non-root user, writable work/tool cache, real wrapper and upstream entrypoint, mock target/label/group arguments, token un-export, liveness command, automatic restart after listener failure, graceful restart/stop and SIGKILL recovery for repo and org. Scenario networking disabled; token/config/listener commands mocked. |
| Current upstream `node build-scripts/generate-meta.js --check` | Passed in a temporary upstream-shaped directory against this blueprint: `1 templates validated`. The downloaded upstream validator is not vendored. |
| Image manifest resolution | Verified the pinned digest exists and advertises amd64/arm64; no claim about image vulnerability scanning. |

## Successful GitHub CI — 17 October 2026

The following `Validate template` runs on `main` completed successfully. Dates in
this document use Europe/Berlin; the linked GitHub logs also contain UTC times.

| Commit | Evidence |
| --- | --- |
| `ba57bc6` — explicit pip cache dependency path | [Successful run](https://github.com/Simplarix/dokploy-actions-runner/actions/runs/38980800402) |
| `ff75d93` — setup-python v7.0.0 | [Successful run](https://github.com/Simplarix/dokploy-actions-runner/actions/runs/38981645584) |
| `0038e5a` — checkout v7.0.1 with setup-python v7.0.0 | [Successful run and step logs](https://github.com/Simplarix/dokploy-actions-runner/actions/runs/38981814785) |

The last run used a GitHub-hosted **Ubuntu 24.04 x64** runner and **Python 3.12.15**.
All configuration checks, the nine unit test methods, both offline container
scenarios and the action cleanup steps passed. The container tests pulled the
unchanged pinned image, ran its actual runner binary's version command and used
the actual upstream entrypoint. Registration-token exchange, configuration/removal
and the job listener were **mocked**, with scenario networking disabled.

Together with the local checks, this establishes mock lifecycle coverage on
arm64 and amd64. It does **not** establish GitHub authentication, actual runner
registration/removal, organization permissions, group access, job routing, real
workflow execution, runner auto-update or Dokploy import/redeployment behavior.
No live Dokploy instance, real PAT or production deployment was used. Configuration
syntax checks do not prove token validity. Mock cleanup checks prove the upstream
trap invokes removal with a refreshed token; they do not prove GitHub accepts it.

The initial CI failed during pip cache setup before reaching the tests; the cache
path fix and successful runs above supersede that result. A release candidate
must also pass CI on its own final commit before its annotated tag is created.

## Live acceptance checklist

**Pending: none of the steps below has been performed for this release candidate.**
Use an isolated Dokploy test project, disposable **private** GitHub targets and
short-lived, scoped PATs. These instructions authorize no production deployment.
Complete and record the results before a production rollout or upstream template
PR. Keep an evidence record with Dokploy version, host architecture, release tag
and commit, image digest, runner names, test times, workflow URLs and redacted logs.

1. **Prepare the exact release candidate.** Download or check out
   `v0.1.0-rc.1`. Create a Dokploy project named `runner-rc-validation` and a private
   repository such as `YOUR-ORG/runner-rc-test`. Ensure outbound DNS/HTTPS and
   `ghcr.io` access. Follow the [README credential setup](../README.md#credentials)
   for repository and organization PAT permissions; do not use a short-lived token
   copied from GitHub's New runner page. Record the pinned image tag/digest.

2. **Deploy repository runner A.** Create a Raw Docker Compose service named
   `rc-repo-01`, using the release's
   [Compose file](../blueprints/dokploy-actions-runner/docker-compose.yml).
   Paste the following into Dokploy's Environment editor and fill the PAT and
   actual repository URL privately. Keep the Compose environment mapping and `$$`
   escapes intact; use no `env_file`, Docker socket or privileged setting.

   ```dotenv
   ACCESS_TOKEN=
   RUNNER_SCOPE=repo
   REPO_URL=https://github.com/YOUR-ORG/runner-rc-test
   ORG_NAME=
   RUNNER_NAME=rc-repo-01
   LABELS=dokploy,repo-ci,rc-repo-01
   RUNNER_GROUP=Default
   ```

   Deploy and wait for `Listening for Jobs`. In repository Settings → Actions →
   Runners, require exactly one **Idle** `rc-repo-01` with the real architecture,
   default labels and all configured custom labels. Record its GitHub runner ID.
   A healthy container alone does not pass this step.

3. **Execute a real repository workflow.** Copy
   [repository-smoke.yml](../examples/workflows/repository-smoke.yml) into the test
   repository's `.github/workflows/` on its default branch. For this test, add
   `rc-repo-01` to `runs-on`, then dispatch it from Actions. Require a successful
   run on `rc-repo-01`; the existing assertions check a non-root account, no socket
   and no PAT in the ordinary job environment. Save the workflow URL. This does
   not prove protection against malicious code recovering credentials.

4. **Deploy runner B and verify parallel execution.** Create a second independent
   Dokploy Compose service, `rc-repo-02`, with the same repository URL, a distinct
   `RUNNER_NAME=rc-repo-02` and `LABELS=dokploy,repo-ci,rc-repo-02`. Keep the group
   `Default`. Require both runners to be Idle. Add this temporary workflow to the
   private test repository and dispatch it:

   ```yaml
   name: Parallel runner validation
   on:
     workflow_dispatch:
   permissions: {}
   jobs:
     parallel:
       strategy:
         fail-fast: false
         max-parallel: 2
         matrix:
           target: [rc-repo-01, rc-repo-02]
       runs-on: [self-hosted, linux, dokploy, repo-ci, "${{ matrix.target }}"]
       timeout-minutes: 5
       steps:
         - name: Verify routing and overlapping execution
           env:
             EXPECTED_RUNNER: ${{ matrix.target }}
           run: |
             set -euo pipefail
             test "$RUNNER_NAME" = "$EXPECTED_RUNNER"
             printf 'Runner: %s\n' "$RUNNER_NAME"
             date -u
             sleep 60
             date -u
   ```

   Require both jobs to succeed on their respective named runners, with overlapping
   execution times. Stop runner A while idle and repeat a smoke run targeted to B;
   B must keep working. Restart A and require it to return to Idle.

5. **Deploy an organization runner.** Create the `trusted-builds` runner group in
   the test organization, allowing only the private test repository. Create a third
   Dokploy service, `rc-org-01`, with a PAT permitted to administer org runners:

   ```dotenv
   ACCESS_TOKEN=
   RUNNER_SCOPE=org
   REPO_URL=
   ORG_NAME=YOUR-ORG
   RUNNER_NAME=rc-org-01
   LABELS=dokploy,org-ci,rc-org-01
   RUNNER_GROUP=trusted-builds
   ```

   Require exactly one Idle org runner in that group. Copy
   [organization-smoke.yml](../examples/workflows/organization-smoke.yml) to the
   private test repository; add `rc-org-01` to its labels and dispatch it. Require
   a successful run on `rc-org-01`. Verify the group's selected-repository policy
   and that it is unavailable to an excluded test repository. Record membership,
   policy and the successful workflow URL.

6. **Exercise restart and recreation for both scopes.** Wait for each runner to
   become Idle, then restart its Dokploy service. Require a single returning Idle
   runner with the same configured name, labels and group, without duplicate
   records. Run the matching smoke workflow again. Separately redeploy with
   container recreation (use `--force-recreate` in Dokploy's full Compose command
   if necessary), verify the container ID changed, and repeat those checks. Check
   that the other independent services remain usable throughout.

7. **Verify actual deregistration and deletion.** Stop an idle repository runner
   and the idle organization runner gracefully. Require their entries to disappear
   from GitHub; merely showing Offline is a failed cleanup check. Start them again,
   require successful re-registration and smoke jobs, then stop before deleting
   those test services. Confirm final removal. Leave the PAT valid until cleanup
   has finished. Record timestamps and runner IDs before/after.

8. **Test recovery and failure cases on a disposable runner.** Hard-kill the test
   container without graceful shutdown, restart/start it with the same scope and
   name, and require one working runner plus a successful smoke job. Permanent
   host loss can leave a stale record needing manual removal. On a separate stopped
   test service, verify a blank PAT fails Compose interpolation and malformed scope,
   target or labels fail startup before registration. Test a revoked or insufficient
   PAT, stop the resulting failed deployment, restore valid credentials and verify
   recovery. For rotation, stop using the old valid PAT, replace it, redeploy and
   check both job execution and subsequent deregistration. Save only redacted logs.

9. **Check workload boundaries and finish cleanup.** Run representative shell,
   JavaScript and user-level setup actions needed by the intended workload. Confirm
   no root/sudo escalation or Docker daemon access. Record whether an actual runner
   auto-update was observed; writable directories alone do not prove an update.
   Stop every remaining test service while its credential is valid, verify GitHub
   removal, then delete the test deployments and revoke the test PATs. Record any
   unobserved behavior or failed step as pending; do not claim full live acceptance.

10. **Validate the upstream import path when available.** Before a
    `Dokploy/templates` submission, test its PR preview/catalog import as well as
    the Raw Compose path. Confirm UUID defaults differ across two imports and all
    registration/workflow/restart/cleanup checks still pass. This project is not
    yet in that catalog; preview import remains a separate pending check. Publish
    `v0.1.0` only after reviewing the recorded live results and unresolved issues.
