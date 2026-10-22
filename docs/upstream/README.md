# Prepared upstream contribution

Target: `myoung34/docker-github-actions-runner`, reviewed tag `2.338.1`.
The adjacent patch makes shell `node` follow the maintained embedded Node24,
matching the downstream correction. It preserves genuine Node20 slots and runner
self-updates. `git apply --check` validates applicability to the reviewed tag.
This is a prepared proposal, not a submitted or accepted upstream fix.

Reproduction: inspect the exact reviewed index in `RUNTIME-REVIEW.md` as user
`runner`; `node --version` is 18.19.1, while
`/actions-runner/externals/node24/bin/node --version` is 24.22.1 on AMD64 and ARM64.
The downstream template’s fixed PATH passes native offline checks and real GitHub
jobs on both image variants. These tests do not validate every upstream image
flavor or its root/Docker-in-Docker modes.

Compatibility: default shell Node changes major version. Explicit `/usr/bin/node`
continues selecting the retained distro version. This patch does not remove the
Ubuntu nodejs/libnode packages, solve every tool CVE or claim Node20 compatibility.
Before upstream merge, update their version assertions, run their required
pre-commit/shellcheck/goss matrix for all supported distributions/architectures,
and document setup-node for workflow runtime selection. A subsequent upstream
base-image cleanup should remove EOL distro Node and dependency chains after
reviewing package consumers. GitHub Runner itself owns eventual removal of the
Node20 and Alpine compatibility slots.
