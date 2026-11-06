#!/bin/bash
# Re-launch pipeline.sh until PIPELINE_DONE (max 10 relaunches). Waits for any running pipeline first.
W=/workspace/projects/c0456480-404e-411d-9bbf-8a91e17c5aa8/venture/03_EXPERIMENTS/ab_set_work
cd /workspace/projects/8ab30c5b-4a43-47d2-af42-980fa05ae57f/speech_lab
for i in $(seq 1 10); do
  while pgrep -f "^/bin/bash selab/venture_ab/pipeline.sh" > /dev/null; do sleep 20; done
  grep -q PIPELINE_DONE $W/pipeline.log && exit 0
  echo "== watchdog relaunch $i $(date)" >> $W/pipeline.log
  selab/venture_ab/pipeline.sh
done
