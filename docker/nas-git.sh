#!/bin/sh
set -eu

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if [ "$#" -eq 0 ]; then
  set -- status --short --branch
fi

docker run --rm \
  -v "$BASE_DIR:/repo" \
  -w /repo \
  alpine/git \
  -c safe.directory=/repo \
  "$@"
