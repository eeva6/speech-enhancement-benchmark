#!/usr/bin/env bash
# after the 3rd sandbox restart (~05:59 UTC): machine idle -> idle runtime check, then DFN3 Rust build + timing
cd "$(dirname "$0")/.."; . .venv/bin/activate
echo "== $(date -u +%T) rtf_cpu idle"; python -m selab.rtf_cpu_r5 3 2>&1 | grep -v -i warn | grep -E "^\w+ \{" ; cp results/r5/rtf_cpu_r5.json results/r5/rtf_cpu_r5_idle.json
echo "== $(date -u +%T) dfn rust build"; timeout 3300 ./scripts/build_dfn_rust.sh > logs/r5_dfn_build9.log 2>&1; tail -n 6 logs/r5_dfn_build9.log
echo "== $(date -u +%T) dfn timing"; python -m selab.dfn_timing 2>&1 | grep -v -i warn | tail -n 40
echo "== $(date -u +%T) DONE"
