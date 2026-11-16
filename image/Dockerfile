FROM ubuntu:24.04@sha256:73b999393d07f2bf65a40373778a44dc9a6d54ad7718d29247d8ff9413c4d6a8 AS base

FROM base AS downloads

ARG TARGETARCH
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl xz-utils \
    && rm -rf /var/lib/apt/lists/*

RUN set -eu; \
    case "$TARGETARCH" in \
      amd64) arch=x64; runner_sha=baebf204307bac6193480852732f0aba2ae97b6c5597c244f4d5558390147c40; node_sha=48cc0e21e048790e54c0cf5749c2725005313d652651c40b7a21feb9697aaf75 ;; \
      arm64) arch=arm64; runner_sha=670adb2f268fe21dcbb58b3db0e0aa9d5b3bddfe2c651481336e561ff86de945; node_sha=eb187837a2230d4047161ac0be008584e16b46f726e9c9490ee35dc6b17d9ba8 ;; \
      *) echo "Unsupported architecture: $TARGETARCH" >&2; exit 1 ;; \
    esac; \
    runner=2.338.2; node=24.22.2; \
    curl -fsSL --retry 3 -o /tmp/runner.tar.gz "https://github.com/actions/runner/releases/download/v${runner}/actions-runner-linux-${arch}-${runner}.tar.gz"; \
    curl -fsSL --retry 3 -o /tmp/node.tar.xz "https://nodejs.org/dist/v${node}/node-v${node}-linux-${arch}.tar.xz"; \
    printf '%s  %s\n' "$runner_sha" /tmp/runner.tar.gz "$node_sha" /tmp/node.tar.xz | sha256sum -c -; \
    mkdir /actions-runner; \
    tar -xzf /tmp/runner.tar.gz -C /actions-runner --no-same-owner; \
    rm -rf /actions-runner/externals/node24 /actions-runner/externals/node24_alpine /actions-runner/externals/node20_alpine; \
    mkdir /actions-runner/externals/node24; \
    tar -xJf /tmp/node.tar.xz -C /actions-runner/externals/node24 --strip-components=1 --no-same-owner; \
    printf 'v%s\n' "$node" > /runner-node-version

FROM base

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates curl git git-lfs jq libgcc-s1 libgssapi-krb5-2 \
        libicu74 liblttng-ust1t64 libssl3t64 libstdc++6 procps python3 tini \
        unzip xz-utils zip zlib1g \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1001 --shell /bin/bash runner \
    && install -d -o runner -g runner /actions-runner /_work /opt/hostedtoolcache

COPY --from=downloads /actions-runner/ /actions-runner/
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
