FROM ubuntu:24.04@sha256:73b999393d07f2bf65a40373778a44dc9a6d54ad7718d29247d8ff9413c4d6a8 AS base

FROM base AS downloads

ARG TARGETARCH
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl xz-utils \
    && rm -rf /var/lib/apt/lists/*

RUN set -eu; \
    case "$TARGETARCH" in \
      amd64) arch=x64; runner_sha=baebf204307bac6193480852732f0aba2ae97b6c5597c244f4d5558390147c40; node_sha=4f2b175a6d53a5c617a80dba2676238a0688cef28c6da4eba35c7d844e66fcfb; lfs_sha=e72cf723a4a660438862282e8aecf3885fc8123e88bfcad534cf6b941a354b75 ;; \
      arm64) arch=arm64; runner_sha=670adb2f268fe21dcbb58b3db0e0aa9d5b3bddfe2c651481336e561ff86de945; node_sha=6e51a2ada00f0011cc266f65d98922b403d7ad88f809ca2aa615a5fe1ce6e86c; lfs_sha=67895dd77b63329796bc5efdd47b57f218e1f7b98717ebaf936a8238dbcaec0f ;; \
      *) echo "Unsupported architecture: $TARGETARCH" >&2; exit 1 ;; \
    esac; \
    runner=2.338.2; node=24.22.3; lfs=3.8.1; \
    curl -fsSL --retry 3 -o /tmp/runner.tar.gz "https://github.com/actions/runner/releases/download/v${runner}/actions-runner-linux-${arch}-${runner}.tar.gz"; \
    curl -fsSL --retry 3 -o /tmp/node.tar.xz "https://nodejs.org/dist/v${node}/node-v${node}-linux-${arch}.tar.xz"; \
    curl -fsSL --retry 3 -o /tmp/git-lfs.tar.gz "https://github.com/git-lfs/git-lfs/releases/download/v${lfs}/git-lfs-linux-${TARGETARCH}-v${lfs}.tar.gz"; \
    printf '%s  %s\n' "$runner_sha" /tmp/runner.tar.gz "$node_sha" /tmp/node.tar.xz "$lfs_sha" /tmp/git-lfs.tar.gz | sha256sum -c -; \
    tar -xzf /tmp/git-lfs.tar.gz -C /tmp --strip-components=1 "git-lfs-${lfs}/git-lfs"; \
    mkdir /actions-runner; \
    tar -xzf /tmp/runner.tar.gz -C /actions-runner --no-same-owner; \
    rm -rf /actions-runner/externals/node20 /actions-runner/externals/node24 /actions-runner/externals/node24_alpine /actions-runner/externals/node20_alpine; \
    mkdir /actions-runner/externals/node24; \
    tar -xJf /tmp/node.tar.xz -C /actions-runner/externals/node24 --strip-components=1 --no-same-owner; \
    printf 'v%s\n' "$node" > /runner-node-version

FROM base

LABEL org.opencontainers.image.source="https://github.com/Simplarix/dokploy-actions-runner"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates curl git jq libgcc-s1 libgssapi-krb5-2 \
        libicu74 liblttng-ust1t64 libssl3t64 libstdc++6 procps python3 tini \
        unzip xz-utils zip zlib1g \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1001 --shell /bin/bash runner \
    && install -d -o runner -g runner /actions-runner /_work /opt/hostedtoolcache

COPY --from=downloads /actions-runner/ /actions-runner/
COPY --from=downloads /tmp/git-lfs /usr/local/bin/git-lfs
COPY --from=downloads /runner-node-version /etc/runner-node-version
COPY --chmod=755 entrypoint.sh token.sh /
RUN chown runner:runner /actions-runner

ENV PATH=/actions-runner/externals/node24/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    HOME=/home/runner \
    AGENT_TOOLSDIRECTORY=/opt/hostedtoolcache
WORKDIR /actions-runner
USER runner
ENTRYPOINT ["/usr/bin/tini", "--", "/entrypoint.sh"]
CMD ["./bin/Runner.Listener", "run", "--startuptype", "service"]
