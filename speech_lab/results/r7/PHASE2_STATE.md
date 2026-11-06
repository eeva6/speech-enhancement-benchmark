# Round 7 phase 2: state at hand-off (2026-10-24 ~03:30 UTC)

Running: `python -m selab.run_r7 pipeline` (PID in results/r7/pids/pipeline.pid, log logs/r7_pipeline.log; 2 spawn workers,
each single-threaded). It is fully resumable; the sandbox restarts often and kills it (happened once at ~03:00).

Pipeline order: stage A (done) -> stage B WNG floor (running) -> stage C hybrid X{20,30,45} x thr{1,3,8} -> writes
results/r7/frozen_r7.json with frozen=true -> test, 14 FINAL methods, all 472 items (ASR on the 434 with words, objective on all,
align_suspect flagged) -> val sub300 for the frozen set -> results/r7/PIPELINE_DONE.
frozen_r7.json is written with frozen=false after stage B (front/ref/wng) and frozen=true after stage C; the pipeline never runs
test before frozen=true.

Stage A results (val sub300 word-correct): front1 .380, front2 .412, front3 .390, front4 .371 -> front = ch2.
hs_sd8 WNG 0 with ref mic ch1/ch2/ch3/ch4: .420/.421/.403/.407 -> ref = ch2 (index 1).

## Check / relaunch (safe to run any time; it skips finished work)
```
cd /workspace/projects/8ab30c5b-4a43-47d2-af42-980fa05ae57f/speech_lab
ps -p $(cat results/r7/pids/pipeline.pid) -o pid,etime || echo dead
tail -5 logs/r7_pipeline.log; cat results/r7/frozen_r7.json; ls results/r7/PIPELINE_DONE
# relaunch if dead:
(setsid nohup bash -c "source .venv/bin/activate && OMP_NUM_THREADS=1 python -m selab.run_r7 pipeline" > logs/r7_pipeline.log 2>&1 < /dev/null & echo $! > results/r7/pids/pipeline.pid)
```
Progress: `cat results/r7/wer_val.part*.csv | wc -l` (wc on the glob can show stale counts on juicefs; cat|wc is reliable),
`cat results/r7/wer_test.part*.csv | wc -l` (target 14 x 434 = 6076 rows + headers), metrics_test.part*.csv (14 x 472).
Throughput ~1.3 ASR items/s total. Remaining at hand-off: ~1000 (B) + 2700 (C) + 6076 test + ~3000 val frozen  => ~2.7 h of ASR.

## After the test stage
```
source .venv/bin/activate
python -m selab.analyze_r7 --split test     # asr_test.csv, asr_wer_test.csv, obj_test.csv, steer_test.csv
python -m selab.timing_r7 --n 12            # ONLY when the pipeline is finished (idle machine) -> timing_r7_summary.csv
python -m selab.summary_r7                  # results/r7/summary_r7.md
python -m selab.analyze_r7 --split val      # optional, after the val frozen stage
```
Files: outputs/r7/<split>/<method>/<id>.wav (scored span only; EasyCom-derived, never distribute);
results/r7/proc/<split>_<method>.<pid>.csv (per-item steering error, head angle, per-hop timing under load);
results/r7/wer_<split>.part{0,1}.csv; results/r7/metrics_<split>.part{0,1}.csv.
Always use exact globs wer_<split>.csv / wer_<split>.part*.csv (run_r7.load_wer does).
