#!/usr/bin/env bash
# verification-gated superdirective (added after the panel diagnosis) on all 144 items
cd "$(dirname "$0")/.."; . .venv/bin/activate
python -m selab.run_r6 --tag r5 --items all --methods sd8_rt --suffix r1000m --fkw '{"ramp_ms": 1000.0, "fallback": "mic0"}'
python -m selab.run_r6 --tag r5 --items all --methods sd8_rt,sd4_rt --tname v2 --suffix v15m --fkw '{"verify": 0.15, "fallback": "mic0"}'
python -m selab.run_r6 --tag r5 --items all --methods gm8_rt --tname v2 --suffix v15m --fkw '{"verify": 0.15, "fallback": "mic0"}'
