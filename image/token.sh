#!/bin/bash
set -euo pipefail

[[ "$ACCESS_TOKEN" =~ ^[A-Za-z0-9_]+$ ]] || exit 64
case "$1" in
  registration|remove) operation=$1 ;;
  *) exit 64 ;;
esac
case "$RUNNER_SCOPE" in
  repo) target="repos/${REPO_URL#https://github.com/}" ;;
  org) target="orgs/$ORG_NAME" ;;
  *) exit 64 ;;
esac

# Pass authorization through stdin so it does not appear in curl's arguments.
printf 'header = "Authorization: Bearer %s"\n' "$ACCESS_TOKEN" |
  env -u ACCESS_TOKEN curl -q --config - --fail --silent --show-error --max-time 20 \
    --request POST --header 'Accept: application/vnd.github+json' \
    --header 'X-GitHub-Api-Version: 2026-03-10' \
    "https://api.github.com/$target/actions/runners/$operation-token"
