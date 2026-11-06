
## Round 6 (2026-10-22): causal low-latency multichannel front-ends on the real LibriCSS items

Plan (checklist in results/r6/CHECKLIST_R6.md): robust causal tracker -> low-latency filters (time-domain DS 0.62 ms; superdirective, coherence-gated MVDR and online RTF/GEVD-MVDR at 4 ms and 8 ms) -> combinations incl. reference-direction upper bounds -> 48-item panel vs round-5 baselines -> critique (held-out sessions, warm start, Whisper brittleness) -> twin -> idle timing -> report, listening pack, app tab.

| Step | What | Where |
|---|---|---|
| Code | selab/r6.py (tracker + filters), run_r6.py (resumable runner, tracker cache, --warm), score_r6.py, analyze_r6.py, summary_r6.py, trk_eval_r6.py, holdout_r6.py, ctx_r6.py, timing_r6.py, listening_r6.py | selab/ |
| Driver | scripts/run_round6.sh (resumable steps); queue helpers r6_queue*.sh, r6_ramp.sh, r6_asr2.sh used during the run | scripts/ |
| Tracker dev | grid on sessions 0-2 only (frame-level SRP was too noisy: 24-51% of single frames within 10 deg even with one talker -> long-map candidates + short-map dominance); chose long-map forgetting 0.99, 20 deg gate | work_r6/trk_grid*.csv |
| Warm-start data | mixtures/r6ctx: all 144 items re-cut from the raw recordings with 2 s of preceding audio; cut-back error 0.0 on every item | mixtures/r6ctx/meta.json |

Failures and fixes (round 6):
1. **Single-frame SRP-PHAT is unusable for tracking on this array** (4.25 cm radius, reverberant room): even on single-talker items only ~25% of 32-ms frames peak within 10 deg. Fixed by tracking peaks of a long running map and using a short map only to decide frame dominance among the candidate tracks.
2. **Background jobs and `pgrep -f`**: a queue script that waited on `pgrep -f <pattern>` never advanced, and a `pkill -f r6_queue.sh` killed the calling shell itself (its own command line matched). Replaced with file-count waits and explicit PIDs.
3. **Sandbox restart at about 13:13** (uptime reset; /tmp wiped). All steps resumed from their outputs; an integrity pass (work_r6/integrity.py) re-read every round-6 npz and wav: 0 corrupt files.
4. **Duplicate baseline transcriptions**: score_r6 initially re-transcribed unprocessed/round-5-DS files already transcribed in round 5 (identical, deterministic). Fixed: round-5 rows now count as done.
