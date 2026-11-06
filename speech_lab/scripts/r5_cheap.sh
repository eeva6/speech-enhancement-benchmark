#!/usr/bin/env bash
# numpy-only beamformers (no DNN) on a tag; resumable
cd "$(dirname "$0")/.."; . .venv/bin/activate; TAG=${1:-r5}
for m in ds_est mvdr_online_est mvdr_online_dir_est mvdr_online_ref mvdr_online_dir_ref; do echo "== $TAG $m"; python -m selab.run_r5 --method $m --tag $TAG --resume 2>&1 | grep -E '^\{|FAIL'; done
