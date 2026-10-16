# Validation evidence

## Local checks performed — 17 October 2026

Environment: macOS ARM64 host, Docker Desktop Linux engine **29.8.2**, Docker
Compose **5.6.0**, Python **3.12.14**, PyYAML **6.0.3**. The runtime scenarios ran
natively on the image's **linux/arm64** variant. The registry manifest also
advertises amd64; execution on amd64 remains for CI/live verification.

| Check | Result and boundary |
| --- | --- |
| `python scripts/validate.py` | Passed: JSON/TOML/YAML, metadata version/ID/logo, allowlist, security settings, Compose model and valid startup fixture. |
| `python -m unittest discover -s tests -v` | Passed: 9 test methods including 33 invalid-input cases and 8 missing/empty required-input cases; both scopes, project separation, `.env` forwarding, fixed security flags and redacted diagnostics. |
| `python scripts/test_container.py` | Passed against the pinned image: actual runner binary version, non-root user, writable work/tool cache, real wrapper and upstream entrypoint, mock target/label/group arguments, token un-export, liveness command, automatic restart after listener failure, graceful restart/stop and SIGKILL recovery for repo and org. Scenario networking disabled; token/config/listener commands mocked. |
| Current upstream `node build-scripts/generate-meta.js --check` | Passed in a temporary upstream-shaped directory against this blueprint: `1 templates validated`. The downloaded upstream validator is not vendored. |
| Image manifest resolution | Verified the pinned digest exists and advertises amd64/arm64; no claim about image vulnerability scanning. |

No live Dokploy instance, real PAT, GitHub runner registration or actual workflow
was used. Automated CI is configured but has not been executed on GitHub in this
workspace. Configuration syntax checks do not prove token validity. Mock cleanup
checks prove the upstream trap invokes removal with a refreshed token; they do not
prove GitHub accepts the token or completes deregistration.

## Live acceptance checklist

Use disposable **private** targets and a short-lived, scoped PAT. Complete these
before a production rollout or upstream template PR, and record Dokploy version,
host architecture, image digest and redacted results:

1. **Repository registration:** deploy the raw Compose file with Environment values.
   Confirm exactly one correctly named Idle runner, default labels and custom
   labels. Run the repository smoke workflow successfully.
2. **Organization registration:** import through the intended template path, set
   org scope, clear the repo URL, and choose an existing restricted runner group.
   Confirm membership and repository policy. Run the organization smoke workflow
   from an allowed repository; verify unintended repositories cannot route jobs.
3. **Independent deployments:** deploy two runners in the same scope with different
   names and labels. Route jobs to each, run jobs concurrently, and confirm stopping
   one does not disrupt the other. Check the imported UUID defaults differ.
4. **Graceful restart/redeploy:** wait for idle, restart and redeploy each service.
   Confirm cleanup and exactly one returning Idle runner with the intended name,
   labels and group; no duplicates or stale registration reuse.
5. **Stop/delete:** stop while idle and verify GitHub removes the runner. Start again,
   then stop before deleting the deployment. Confirm final removal.
6. **Abrupt failure:** kill a disposable runner without graceful shutdown, restart
   with the same name, and confirm replacement registration and job execution.
   Document manual cleanup after permanent host loss.
7. **Credential failures/rotation:** test an expired/revoked/under-permissioned PAT,
   confirm no secret in logs, correct it and redeploy. Rotate a valid PAT using the
   documented stop/update/deploy sequence and verify cleanup still works.
8. **Input failures:** blank PAT must fail Compose interpolation; malformed scope,
   target and labels must fail startup before registration. Verify the UI `.env`
   mapping works without `env_file` or manually exporting host variables.
9. **Boundaries/updates:** verify no root/sudo escalation or Docker daemon access,
   representative shell/JavaScript/setup actions work, and runner auto-update can
   write as non-root. Check all required outbound endpoints/firewall rules.
10. **Upstream preview:** repeat import/deploy checks using the Dokploy/templates
    PR preview and upstream CI. Do not submit mock results as live acceptance.
