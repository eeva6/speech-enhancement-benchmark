# Round 7, phase 1 checklist: EasyCom data acquisition and preparation

- [x] Download the 33 release parts resumably (scripts/r7_download.sh -> data/easycom/parts, logs/r7_download.log)
- [x] Streaming selective extraction (selab/extract_r7.py -> data/easycom/{Main,Calibration}, logs/r7_extract.log)
- [x] Verify extraction (file counts and sizes vs tar listing, wav headers readable)
- [x] LICENSE_NOTE.txt in data/easycom and mixtures/r7 (CC-BY-NC 4.0, no redistribution)
- [x] Clone EasyCom repo (README) and spear-tools (reference) into third_party/
- [x] ATF analysis: head/array frame convention (Phi direction, Theta) from the measured IRs
- [x] Step 1: resample to 16 kHz; close mic drift correction + per-minute xcorr lag check; alignment residual
- [x] Step 2: per-50 ms reference DOA of every participant in the wearer head frame; SRP (ATF) validation
- [x] Step 3: items (>=1 s, close-mic talkers) with 2 s context, transcript, aligned reference, overlap flag, time since turn onset -> mixtures/r7/{val,test} + meta.json
- [x] Step 4: head-orientation steering accuracy vs time since turn onset (results/r7/head_onset.csv + figure)
- [x] Step 4b (if feasible): round-6 causal tracker adapted to ch1-4 on val sessions, same onset curve
- [x] Delete parts after verified extraction
- [x] EXECUTION_LOG.md updated

Status 2026-10-24 ~02:45 UTC: all phase-1 items done (details and numbers in results/r7/PHASE1_SUMMARY.md). Not done / open:
- Phase 2 (beamformers + ASR) not started (separate agent).
- Elevation of the reference DOA is not validated beyond "SRP elevation is coarse/biased" (array nearly horizontal); azimuth is validated.
- Talker position = head-pose centre (no mouth offset); transcript/pose frame numbering ambiguity <= 50 ms.
- align_suspect items (36 val / 27 test) are mostly fully-overlapped; phase 2 may exclude or re-align them per item.

## Phase 2 (beamformers + ASR)
- [x] ATF steering (interpolated), ATF diffuse coherence, ATF fractional delays (selab/bf_r7.py)
- [x] Filters: hs/trk/hyb/ref x ds_td/sd8/sd4 (ref: sd8, ds_td), r5ds baseline, unproc_front, unproc_ear
- [x] Processing/scoring/pipeline code (selab/run_r7.py), analysis (selab/analyze_r7.py), timing (selab/timing_r7.py)
- [~] Val tuning (sub300): front mic = ch2, ref mic = ch2 DONE (stage A); WNG floor (stage B) running; hybrid X/thr (stage C) queued -> results/r7/frozen_r7.json
  (state + resume commands: results/r7/PHASE2_STATE.md)
- [ ] Test run once (472 items, 434 with words for ASR) for every frozen method
- [ ] Objective metrics (align_suspect excluded) and ASR with/without align_suspect
- [ ] Analysis: deltas vs unproc_front and r5ds, Holm, breakdowns, steering error vs gain (python -m selab.analyze_r7)
- [ ] Timing (python -m selab.timing_r7, idle machine)
- [ ] REPORT_R7, listening folder, summary (finish agent)

Status 2026-10-24 20:35 UTC: Phase 2 DONE. Test run, ASR, objective metrics, analysis, timing (load<1.5), summary_r7 and REPORT_R7.md/pdf (13 pages, page checked as PNG) complete.
