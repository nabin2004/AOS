#!/usr/bin/env bash
# Continuous collect_traces waves until unique success prompts reach TARGET.
# Run under tmux/systemd from apps/agents:
#
#   ./sft_data_gen/run_waves.sh
#   TARGET=5000 CONCURRENCY=4 LIMIT=200 ./sft_data_gen/run_waves.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TARGET="${TARGET:-5000}"
CONCURRENCY="${CONCURRENCY:-4}"
LIMIT="${LIMIT:-200}"
SLEEP_BETWEEN="${SLEEP_BETWEEN:-30}"

echo "Wave runner: target=${TARGET} concurrency=${CONCURRENCY} limit=${LIMIT}"

while true; do
  remaining="$(
    uv run python sft_data_gen/status.py --target "$TARGET" --concurrency "$CONCURRENCY" \
      | awk '/Remaining to target:/ {print $NF}'
  )"
  echo "Remaining to target: ${remaining}"
  if [[ "${remaining}" =~ ^[0-9]+$ ]] && (( remaining <= 0 )); then
    echo "Target reached."
    uv run python sft_data_gen/status.py --target "$TARGET" --concurrency "$CONCURRENCY"
    exit 0
  fi

  echo "Starting wave: collect_traces --fast --resume --concurrency ${CONCURRENCY} --limit ${LIMIT}"
  uv run python sft_data_gen/collect_traces.py \
    --fast \
    --resume \
    --convert-after-local \
    --concurrency "${CONCURRENCY}" \
    --limit "${LIMIT}" \
    || true

  uv run python sft_data_gen/status.py --target "$TARGET" --concurrency "$CONCURRENCY"
  sleep "${SLEEP_BETWEEN}"
done
