#!/usr/bin/env bash
# One-time DVC onboarding for the data-insights repo.
#
# Idempotent: re-runs are safe. Operates in the repo root.
# Reads credentials from the file pointed to by DVC_ENV_FILE
# (default: /etc/dvc-env) and configures the B2 S3 remote.
#
# What it does:
#   1. dvc init --no-scm (idempotent: does nothing if .dvc/ exists)
#   2. Source the env file, set AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY
#      so DVC's boto3 backend can authenticate against the S3 endpoint.
#      (The .dvc/config stays clean of secrets; only the URL + endpoint
#      are committed.)
#   3. dvc remote add b2 (idempotent: detects existing remote and updates it)
#   4. dvc remote modify b2 {url, endpointurl}
#
# To use this with the snapshot script, ensure DVC_ENV_FILE is set
# in the cron host's environment, and `source` it before running dvc.
#
# This script is also called by _scripts/snapshot.py at first run
# if .dvc/config is missing.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${DVC_ENV_FILE:-/etc/dvc-env}"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: env file not found at $ENV_FILE" >&2
    echo "  Copy _scripts/dvc.env.example to /etc/dvc-env, fill in" >&2
    echo "  the B2 key/secret, and chmod 600." >&2
    exit 1
fi

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

: "${B2_APPLICATION_KEY_ID:?missing in $ENV_FILE}"
: "${B2_APPLICATION_KEY:?missing in $ENV_FILE}"
: "${B2_S3_ENDPOINT:?missing in $ENV_FILE}"
: "${B2_BUCKET:?missing in $ENV_FILE}"

cd "$REPO_ROOT"

# dvc init is idempotent: if .dvc/ exists, it's a no-op.
if [[ ! -d .dvc ]]; then
    echo "  running: dvc init --no-scm"
    dvc init --no-scm
fi

# Export the credentials as standard AWS env vars (boto3 reads these).
export AWS_ACCESS_KEY_ID="$B2_APPLICATION_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$B2_APPLICATION_KEY"

# Configure the remote. Only the URL + endpoint are committed; the
# creds are read from the environment at runtime.
echo "  setting default remote: b2"
dvc remote add -d b2 "s3://$B2_BUCKET/snapshots" 2>/dev/null \
    || dvc remote default b2 2>/dev/null \
    || dvc remote modify --local b2 url "s3://$B2_BUCKET/snapshots"

echo "  setting endpointurl: $B2_S3_ENDPOINT"
dvc remote modify b2 endpointurl "$B2_S3_ENDPOINT"
# Extract region from endpoint URL (e.g. https://s3.ca-east-006.backblazeb2.com -> ca-east-006)
_B2_REGION="$(echo "$B2_S3_ENDPOINT" | sed 's|https\?://s3\.\([^.]*\)\.backblazeb2.*|\1|')"
if [[ -n "$_B2_REGION" ]]; then
    echo "  setting region: $_B2_REGION"
    dvc remote modify b2 region "$_B2_REGION"
fi
# Remove any credential entries from .dvc/config and .dvc/config.local.
# Empty-string creds in config shadow the AWS_ACCESS_KEY_ID /
# AWS_SECRET_ACCESS_KEY env vars, causing 403 on push.
# dvc remote modify writes to config.local by default, which persists
# even after the main config is cleaned up.
rm -f .dvc/config.local
# Remove key fields from the shared config. These commands will fail if
# the b2 remote doesn't exist yet (e.g. on a fresh clone where
# .dvc/config was not committed), which is fine — skip silently.
for _cred_field in access_key_id secret_access_key; do
    if dvc remote list 2>/dev/null | grep -q "b2"; then
        dvc remote modify b2 "$_cred_field" 2>/dev/null || true
    fi
done

echo
echo "DVC onboarding complete."
echo "  remote: s3://$B2_BUCKET/snapshots"
echo "  endpoint: $B2_S3_ENDPOINT"
echo "  credentials: from \$AWS_ACCESS_KEY_ID / \$AWS_SECRET_ACCESS_KEY (loaded from $ENV_FILE)"
echo
echo "Test with:"
echo "  echo 'hello' > /tmp/dvc-test.txt && dvc add /tmp/dvc-test.txt && dvc push"
