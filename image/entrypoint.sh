#!/bin/bash
set -euo pipefail

node=/actions-runner/externals/node24/bin/node
if [[ "$(command -v node)" != "$node" || "$("$node" --version)" != "$(cat /etc/runner-node-version)" ]]; then
  echo 'The embedded Node runtime differs from the image policy' >&2
  exit 64
fi

group=()
case "$RUNNER_SCOPE" in
  repo) url=$REPO_URL ;;
  org)
    url="https://github.com/$ORG_NAME"
    group=(--runnergroup "${RUNNER_GROUP:-Default}")
    ;;
  *) echo 'RUNNER_SCOPE must be repo or org' >&2; exit 64 ;;
esac

# Keep the PAT in the supervisor for removal and export it only to the token helper.
export -n ACCESS_TOKEN
get_token() {
  ACCESS_TOKEN="$ACCESS_TOKEN" /token.sh "$1" | jq -er '.token | strings | select(length > 0)'
}

registered=false
listener=
stop=false
shutdown() {
  stop=true
  if [[ -n "$listener" ]]; then
    kill -TERM "$listener" 2>/dev/null || true
  fi
}
cleanup() {
  if [[ "$registered" == true ]]; then
    local token
    if ! token=$(get_token remove) || ! ./config.sh remove --token "$token"; then
      echo 'Runner deregistration failed. Check the runner record in GitHub.' >&2
    fi
  fi
}
trap shutdown TERM INT
trap cleanup EXIT

# Recover from a forced stop by replacing the GitHub record with the same name.
rm -f .runner .credentials .credentials_rsaparams
token=$(get_token registration)
if [[ "$stop" == true ]]; then
  exit 0
fi
./config.sh --unattended --disableupdate --replace --url "$url" --token "$token" \
  --name "$RUNNER_NAME" --labels "$LABELS" --work /_work "${group[@]}"
unset token
registered=true
if [[ "$stop" == true ]]; then
  exit 0
fi

"$@" &
listener=$!
if [[ "$stop" == true ]]; then
  shutdown
fi
status=0
wait "$listener" || status=$?
if [[ "$stop" == true ]]; then
  # A signal interrupts Bash's wait before the listener necessarily exits.
  wait "$listener" || true
  exit 0
fi
exit "$status"
