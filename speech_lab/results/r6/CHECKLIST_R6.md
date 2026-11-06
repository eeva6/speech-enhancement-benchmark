# Round 6 checklist (kept current during the run)

Legend: [x] done, [~] running / partial, [ ] not started, [-] cut

## Setup
- [x] Read REPORT_R5, summary_r5, r5methods, run_r5, score_r5, analyze_r5, doa_r5, round-5 log entry
- [x] Machine check: 2 vCPU, 8 GB, co-tenant lab idle at start; at most 2 heavy jobs of ours
- [x] selab/r6.py: causal tracker (r5t / rtn / rt with ECAPA check) + filters (ds_td, sd4/8, gm4/8, rtf4/8)
- [x] selab/run_r6.py (resumable runner, tracker cache), score_r6.py, analyze_r6.py, trk_eval_r6.py, holdout_r6.py, timing_r6.py
- [x] scripts/run_round6.sh (resumable steps)

## Tracker
- [x] Development on sessions 0-2 only (work_r6/trk_grid*.csv): long-map forgetting 0.99, 20 deg gate chosen
- [x] Accuracy on all 122 items with a reference (results/r6/tracker_r5.csv)
- [x] Onset curve (results/r6/tracker_onset.csv, figs/tracker_onset.png)

## Panel (48 items, real)
- [x] Processing: 17 round-6 methods
- [x] ASR (Whisper base.en) for all 17 (+ variants)
- [x] Objective metrics (SI-SDR / ESTOI vs estimated reference), 11 methods, indicative

## Critique fixes
- [x] Held-out protocol: tune on sessions 0-2 (72 items), freeze, test on sessions 3-5 (72 items) — test ASR done 2026-10-22
- [x] Whisper-brittleness check (panel + held-out)
- [x] Multiple comparisons: Holm within the family of round-6 methods per group

## Twin
- [x] r5sim panel: 6 methods ASR (planned 6 for the twin; not cut), sim-vs-real table

## Compute / latency
- [x] Idle timing benchmark (results/r6/timing_r6*.csv; load avg 0.65)

## Deliverables
- [x] results/r6/summary_r6.md + figs (forest-plot crash fixed; sim-row contamination bug fixed)
- [x] REPORT_R6.md / REPORT_R6.pdf (8 pages rendered to PNG and checked)
- [x] listening/r6 (6 sets x 4 mp3: unprocessed / R5 DS / sd8 tracked / sd8 REF) + round6_listening.zip (unzip -t OK)
- [x] app.py multichannel tab: round-6 superdirective options run on a real 7-mic item; HTTP 200
- [x] EXECUTION_LOG.md round-6 entry

## Cut
- [-] Twin for gm8 / rtf8 / ds_td REF; held-out objective metrics; full-144 ASR for non-frozen configs; native-code timing / overrun counts
