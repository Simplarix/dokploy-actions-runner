FROM ubuntu:24.04@sha256:73b999393d07f2bf65a40373778a44dc9a6d54ad7718d29247d8ff9413c4d6a8 AS base

# Cross-compile the upstream source with locked, patched Go dependencies.
FROM --platform=$BUILDPLATFORM golang:1.27.4-bookworm@sha256:4fa7c968ba93f1635670522dbb01a2c78150443e1385746924566079f36570ea AS git-lfs
ARG TARGETARCH
WORKDIR /src
ADD --checksum=sha256:6ab3e7ffa03014f3ca574f06c1df835ccf9e8c079a3c5c1134b95bdff9c106c0 https://codeload.github.com/git-lfs/git-lfs/tar.gz/refs/tags/v3.8.1 /tmp/source.tar.gz
RUN tar -xzf /tmp/source.tar.gz --strip-components=1 -C /src
COPY git-lfs/go.mod git-lfs/go.sum ./
RUN go mod download && go mod verify
RUN --network=none CGO_ENABLED=0 GOOS=linux GOARCH=$TARGETARCH GOTOOLCHAIN=local \
    go build -mod=readonly -trimpath -buildvcs=false \
    -ldflags="-s -w -X github.com/git-lfs/git-lfs/v3/config.Vendor=Simplarix" -o /git-lfs .

FROM base AS downloads

ARG TARGETARCH
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl python3 xz-utils \
    && rm -rf /var/lib/apt/lists/*

ADD --checksum=sha256:8ad8563b81e71b90ef405b140bccf3ba9b5e7884ab210bd49ee4e2f4bc6f61f5 https://registry.npmjs.org/npm/-/npm-11.21.2.tgz /tmp/npm.tar.gz
ADD --checksum=sha256:22c33cd4bef2815c086323eaa499068494fe5323859c64f43196fa22df0e1453 https://api.nuget.org/v3-flatcontainer/microsoft.aspnetcore.webutilities/8.0.34/microsoft.aspnetcore.webutilities.8.0.34.nupkg /tmp/webutilities.nupkg
ADD --checksum=sha256:8640306430990c01b6647c09cd117f60e3d0a50c54eae08a334eb1682a20def1 https://api.nuget.org/v3-flatcontainer/microsoft.net.http.headers/8.0.34/microsoft.net.http.headers.8.0.34.nupkg /tmp/headers.nupkg
COPY patch_runner.py /tmp/patch_runner.py

RUN set -eu; \
    case "$TARGETARCH" in \
      amd64) arch=x64; runner_sha=baebf204307bac6193480852732f0aba2ae97b6c5597c244f4d5558390147c40; node_sha=4f2b175a6d53a5c617a80dba2676238a0688cef28c6da4eba35c7d844e66fcfb ;; \
      arm64) arch=arm64; runner_sha=670adb2f268fe21dcbb58b3db0e0aa9d5b3bddfe2c651481336e561ff86de945; node_sha=6e51a2ada00f0011cc266f65d98922b403d7ad88f809ca2aa615a5fe1ce6e86c ;; \
      *) echo "Unsupported architecture: $TARGETARCH" >&2; exit 1 ;; \
    esac; \
    runner=2.338.2; node=24.22.3; \
    curl -fsSL --retry 3 -o /tmp/runner.tar.gz "https://github.com/actions/runner/releases/download/v${runner}/actions-runner-linux-${arch}-${runner}.tar.gz"; \
    curl -fsSL --retry 3 -o /tmp/node.tar.xz "https://nodejs.org/dist/v${node}/node-v${node}-linux-${arch}.tar.xz"; \
    printf '%s  %s\n' "$runner_sha" /tmp/runner.tar.gz "$node_sha" /tmp/node.tar.xz | sha256sum -c -; \
    mkdir /actions-runner; \
    tar -xzf /tmp/runner.tar.gz -C /actions-runner --no-same-owner; \
    rm -rf /actions-runner/externals/node20 /actions-runner/externals/node24 /actions-runner/externals/node24_alpine /actions-runner/externals/node20_alpine; \
    mkdir /actions-runner/externals/node24; \
    tar -xJf /tmp/node.tar.xz -C /actions-runner/externals/node24 --strip-components=1 --no-same-owner; \
    rm -rf /actions-runner/externals/node24/lib/node_modules/npm; \
    mkdir /actions-runner/externals/node24/lib/node_modules/npm; \
    tar -xzf /tmp/npm.tar.gz -C /actions-runner/externals/node24/lib/node_modules/npm --strip-components=1 --no-same-owner; \
    python3 /tmp/patch_runner.py /actions-runner/bin /tmp; \
    printf 'v%s\n' "$node" > /runner-node-version

FROM base

LABEL org.opencontainers.image.source="https://github.com/Simplarix/dokploy-actions-runner"

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
        ca-certificates curl git jq libgcc-s1 libgssapi-krb5-2 \
        libicu74 liblttng-ust1t64 libssl3t64 libstdc++6 procps python3 tini \
        unzip xz-utils zip zlib1g \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1001 --shell /bin/bash runner \
    && install -d -o runner -g runner /actions-runner /_work /opt/hostedtoolcache

COPY --from=downloads /actions-runner/ /actions-runner/
COPY --from=git-lfs /git-lfs /usr/local/bin/git-lfs
COPY --from=git-lfs /src/LICENSE.md /usr/local/share/doc/git-lfs/LICENSE.md
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
