#!/usr/bin/env bash
cd "$(dirname "$0")/.."; . .venv/bin/activate
python -m selab.run_r6 --tag r5 --items all --methods sd8_rt --suffix r1000 --fkw '{"ramp_ms": 1000.0}'
python -m selab.run_r6 --tag r5 --items all --methods sd8_rt --suffix r500 --fkw '{"ramp_ms": 500.0}'
python -m selab.run_r6 --tag r5 --items all --methods sd8_rt --suffix r2000 --fkw '{"ramp_ms": 2000.0}'
python -m selab.run_r6 --tag r5 --items all --methods sd4_rt --suffix r1000 --fkw '{"ramp_ms": 1000.0}'
python -m selab.run_r6 --tag r5 --items all --methods sd4_rt --suffix r2000 --fkw '{"ramp_ms": 2000.0}'
python -m selab.run_r6 --tag r5 --items s012 --methods sd8_rt
