#!/usr/bin/env bash
# (Re)launch the lab app (Gradio + the real-time demo page) on port 7860, local only, detached.
# Page: http://127.0.0.1:7860/rtdemo/   (also embedded in the app's "Real-time demo (Conversation Bubble)" tab)
cd "$(dirname "$0")/.."
if [ -f results/rtdemo/app.pid ] && ps -p "$(cat results/rtdemo/app.pid)" > /dev/null 2>&1; then
  echo "already running: PID $(cat results/rtdemo/app.pid)"; exit 0; fi
(setsid nohup bash -c "source .venv/bin/activate && OMP_NUM_THREADS=1 nice -n 19 python app.py" > logs/rtdemo_app.log 2>&1 < /dev/null & echo $! > results/rtdemo/app.pid)
echo "started PID $(cat results/rtdemo/app.pid); open http://127.0.0.1:7860/rtdemo/"
