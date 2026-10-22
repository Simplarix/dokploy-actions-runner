# Migrating an existing runner

The tested destination is:

```text
ghcr.io/myoung34/docker-github-actions-runner:2.338.1-ubuntu-noble@sha256:36782fe0e5994b301652408c32113a3562fabb1f0ead865ccc196d3e870f9109
```

It supports AMD64 and ARM64, Runner Core 2.338.1, and default Node24 24.22.1 via the
fixed PATH in the updated Compose file. Use the complete blueprint, not just an
image override: an older deployment can retain `DISABLE_AUTO_UPDATE`, an obsolete
entrypoint or a system-Node PATH otherwise. Original Node20 binaries remain and
GitHub controls legacy action migration; no Node20 compatibility guarantee is made.

1. Privately save the exact old image digest, Compose source, environment and
   service name. Keep the rollback image locally. Never print resolved config or
   credentials. Validate the updated template with the intended private environment.
2. Test representative jobs on a separately named runner first, particularly code
   previously depending on shell Node18 or replaced Node20 slots. Select explicit
   maintained action versions; use setup-node for npm and build runtime pinning.
3. Wait until the installed runner is idle, stop it gracefully with its existing
   credential and verify the GitHub record is removed. Do not overlap old/new
   containers sharing a scope/name. If the old local service is called `runner`,
   remove it with its saved old Compose definition before replacing that definition.
4. Install the new Compose definition, keep the intended scope/name/labels/group
   and resource limits, remove custom binary patches and update-disabling flags,
   and recreate. Do not carry mutable runner directories or credentials forward.
5. Verify one Idle runner; Core 2.338.1; `command -v node` selecting
   `/actions-runner/externals/node24/bin/node`; Node 24.22.1; required jobs; restart;
   and clean deregistration in a maintenance test. The local healthcheck alone
   cannot establish success.
6. On failure, stop/remove the new runner while its token still works, restore the
   saved old Compose/environment/image digest, and recreate the old service.
   Verify exactly one registration. Record why rollback was needed and plan the
   forward fix; rolling back to old runtimes restores their vulnerabilities too.

This document is a prepared procedure, not evidence that an installed service
was changed. Installation-specific source/destination mappings belong in private
operator notes and must not be committed to the public template repository.
