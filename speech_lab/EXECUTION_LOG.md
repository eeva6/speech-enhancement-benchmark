# Execution log

All times CDT, 2026-10-15. Machine: sandbox, 2 vCPU aarch64, 7 GB RAM, no GPU, ~6 GB root disk.
Raw logs live in `logs/`. Nothing below is estimated unless marked so.

## Completed
| Step | Outcome | Evidence |
|---|---|---|
| Literature review (researcher pass) | 53 numbered sources, links checked (arXiv/Crossref/HTTP) | docs/literature_review.md, docs/comparison_matrix.md |
| Environment | torch 2.4.1 CPU, speechbrain 1.1.1, asteroid, denoiser, pystoi, pesq, pyroomacoustics, faster-whisper, gradio | requirements.lock.txt |
| Data download | Mini LibriSpeech dev-clean-2 (1089 utts, 26 speakers), ESC-50, 37 MUSAN background-noise files | scripts/get_data.sh |
| Round-1 test set | 192 mixtures: 6 single-channel conditions x 3 SNRs (-5/0/+5 dB) x 8 utts, plus 2 four-mic array conditions x 3 SNRs x 8 | mixtures/r1/meta.json, logs/mixtures_r1.log |
| Smoke test | all 13 methods ran on 3 files (SepFormer idle RTF 3.10 taken from here) | (smoke outputs deleted) |
| Round-1 processing | 15 methods; 0 processing failures; SepFormer on a 3-utt/cell subset (51 files) | results/r1/runtime_*.json, logs/round1.log, logs/r1_*.log |
| Round-1 scoring | SI-SDR/STOI/ESTOI/PESQ on every output; Whisper base.en ASR on first 3-4 utts/cell | results/r1/metrics.csv, wer.csv |
| Reviewer critique | 11 concerns, see REPORT.md section 5 | REPORT.md |
| Round-2 set | 180 mixtures, unused utterances, seed 1, SNR -10/0/+10, 10 utts/cell | mixtures/r2/meta.json |
| Round-2 processing | 11 method variants incl. 3 oracle-noise controls and demucs_then_tse hybrid | results/r2/ |
| Streaming latency | classical per-hop compute; Demucs via DemucsStreamer (not real-time on this CPU) | results/latency.json |
| Demo app | Gradio app launched and answered HTTP 200; process() and example browser exercised programmatically | logs/app_smoke.log |
| Listening pack | fixed selection rule (index 00 per condition at 0 dB and hardest SNR), offline HTML players | listening/index_r1.html, index_r2.html |

## Failed attempts and fixes
1. **DeepFilterNet install failed** - `deepfilterlib` has no aarch64/py3.12 wheel and needs a Rust toolchain to build (logs/fail_deepfilternet_install.log). Not fixed; DeepFilterNet is excluded and covered in the review only.
2. **First bulk pip install filled the disk** (`Errno 28`): a dependency pulled a CUDA torch build (~3 GB). Fixed with a torch==2.4.1 constraints file and `--no-cache-dir`.
3. **PESQ would not build**: no C compiler in the sandbox and no root. Built with `zig cc` (pip `ziglang`) as the compiler. The first two builds imported fine but **crashed with SIGILL on first call**. Turning off zig's UB sanitizer did not fix it. Targeting `aarch64-linux-gnu.2.41 -mcpu=generic` did, which points to zig's native-CPU feature detection as the cause. Sanity check: PESQ-WB of a lightly noised copy = 4.54.
4. **DEMAND noise corpus (Zenodo) unreachable**: HTTP 502 through the sandbox proxy. Replaced with ESC-50 (traffic composite) and MUSAN background noises. The 'traffic' condition is therefore a composite of engine/train beds with horn/siren events, not a recorded street scene.
5. **First mixture build crashed** on writing meta.json (numpy float32 not JSON serialisable) after 4 min of synthesis. Fixed (`default=float`) and rebuilt; it is deterministic, so output is unchanged.
6. **Classical methods crashed in the smoke test**: an unexpected `enrol` keyword. Fixed with `**_` in their signatures.
7. **Round-1 orchestration was killed at the 20-minute sandbox limit for one background job**, partway through `tse_convtasnet_oracle` (65/192 files). Fixed by adding `--resume` and running each method as its own job. The oracle variant's runtime JSON for the resumed part is `runtime_tse_convtasnet_oracle_resume.json`. Its RTF is not used in any comparison, because it is an oracle.
8. **Process-kill mistake**: a `pkill -f` pattern matched its own shell and killed the edit command. The edit was re-applied.
9. **Sandbox restarted at ~19:09 CDT**, wiping everything outside /workspace (pip packages, compiler wrapper). Fixed with `scripts/setup_env.sh`, which builds a persistent `.venv` inside the project, including the PESQ build. Four `bf_mvdr_mask_pf` outputs and that method's runtime JSON were lost, then recomputed with `--resume`.
10. **SepFormer is slow on CPU** (RTF 3.1 idle). It ran on a 3-utterance-per-cell subset and was split into jobs to fit the 20-minute limit. One job timed out before writing its runtime JSON and before the pink +5 dB cell (3 files), so SepFormer has n = 51. It was not run on the array conditions or in round 2.
11. **ASR was too slow for every file** (about 2-6 s per file on 2 vCPU). It was restricted to the first 3 (r1) or 4 (r2) utterances of each cell, the same files for every method. `clean_ref` was transcribed for all r1 files.
12. **WER was dominated by insertion outliers** (the competing talker transcribed, hallucinated loops; WER > 1 on some files). Word-correct rate (hits/N) was added as the primary ASR measure and WER is kept alongside it.
13. **Gradio app failed its startup self-check** (HTTP 404 via the sandbox HTTP proxy). Fixed by adding localhost to NO_PROXY in app.py.
14. **Three MUSAN files are missing on the HF mirror** (15-byte "Entry not found" stubs). Round 1 never drew them. Round 2's first build crashed on one, so the builder now redraws on unreadable files, which leaves r1 reproducible bit-exactly.
15. **Some RTFs were measured while another job shared the CPU** (r2 TSE 0.90, r2 hybrid 0.86-1.87, r1 SepFormer batch 5.26). REPORT.md uses idle or uncontended r1 timings for comparisons.

## Not executed / out of reach
- Human listening tests: none were possible. Listening material is supplied and the ASR proxy is labelled as a proxy.
- Real multichannel recordings: none were available. Beamforming is evaluated on image-method simulation only.
- PESQ commercial licence status: not established (research use only).
- GPU timings: no GPU.
- tse_convtasnet_oracle in round 2: skipped for CPU budget (in r1 ECAPA chose the oracle stream in 95.8% of files).
- DeepFilterNet / RNNoise: not buildable here (no Rust toolchain / no C toolchain for its build system).
- Out-of-domain speech corpus and recorded noise (DEMAND, WHAM!): Zenodo unreachable, WHAM! too large for the time budget.

---

# Round 3 (2026-10-15, 21:14-23:xx CDT): execution of the recommended next experiments

## Completed
| Item | What ran | Evidence |
|---|---|---|
| Rust toolchain + DeepFilterNet3 | rustup (minimal profile) into `.rust/`; `deepfilterlib` built from source with zig as the linker via `.venv/ccbin/rustlink` | logs/pip_deepfilternet_rust2.log ("Successfully installed deepfilterlib-0.5.6") |
| RNNoise | `pyrnnoise` 0.4.5 manylinux2014_aarch64 wheel (no build needed) | selab/neural.py `run_rnnoise` |
| Out-of-domain corpus | CMU ARCTIC (8 talkers, festvox.org) + MS-SNSD recorded test noise (MIT licence, git sparse checkout) | data/arctic, data/mssnsd/noise_test |
| OOD mixtures (r3) | 144 = 6 conditions x SNR {-5,0,+5} x 8; seed 3; target talkers awb/clb/ksp/slt, disjoint interferers bdl/jmk/rms/aew | mixtures/r3/meta.json, `build_ood()` |
| r3 processing | 12 methods incl. RNNoise, DeepFilterNet3, three streaming Wiener variants; zero failures | results/r3/runtime_*.json |
| Backfill | RNNoise and DeepFilterNet3 on r1 (192) and r2 (180) | results/r1, results/r2 metrics.csv |
| Streaming implementations | `selab/streaming.py`: hop-by-hop Wiener (8/16/32 ms windows, online minimum statistics), online 4-mic MVDR, online MVDR + RNNoise | results/r3/latency_budget.csv |
| Scoring | SI-SDR / STOI / ESTOI / PESQ-WB on all new outputs; Whisper ASR on 4 utts per cell (r3), 3 (r1), 4 (r2) | metrics.csv, wer.csv |
| Analysis | `python -m selab.analyze_r3` -> summary_r3.md, generalisation_gap.csv, latency_budget.csv, two figures | results/r3/ |
| Blinded listening test | `listening_test.py`: Gradio app, Latin-square assignment (each listener hears each sentence once and each method 8 times), opaque stimulus names, RMS-normalised stimuli, word-correct scoring identical to the ASR proxy, CSV logging, bootstrap analysis | results/listening_test/plan.json, 288 stimuli; app answered HTTP 200 |

## Failures and fixes (round 3)
16. **CMU ARCTIC tarballs would not extract**: no `bzip2` binary. Extracted with Python `tarfile` instead.
17. **First Rust build failed**: zig's linker rejects `--fix-cortex-a53-843419`, which rustc passes on aarch64. Fixed with a linker wrapper that drops that one flag.
18. **The DeepFilterNet install downgraded numpy to 1.26**, which broke scipy 1.18 (`np.long` AttributeError). Restored numpy 2.5.4 from the lock file with `--no-deps`. DeepFilterNet3 runs correctly on numpy 2.5.4 (smoke test: SI-SDR -0.02 -> 10.05 dB on a pink-noise file).
19. **RNNoise output is delayed by 320 samples (20 ms at 16 kHz)**, which would wreck any sample-aligned metric. The delay is measured by cross-correlation on a probe signal and compensated before scoring. DeepFilterNet3's `enhance(pad=True)` compensates its own delay.
20. **Parallel jobs hit the 20-minute limit** (r3 TSE oracle, r2 backfill). Finished with `--resume`. The resume pass that had nothing left to do **overwrote the r3 `tse_convtasnet_ecapa` runtime JSON with an empty record**. That record was restored from the job's stdout, and `run.py` now refuses to overwrite a runtime record when a pass processes 0 files.
21. **The r3 Demucs pass left 4 files unwritten** (ood_reverb_rec_babble +5 dB, 04-07) and its runtime JSON was missing, even though its stdout reported completion. Cause not established (possibly a lost write on the network filesystem). The 4 files were regenerated with `--resume`, the runtime record was transcribed from the job's stdout, and the 4 files were scored.
22. **RTF contamination**: the r1 and r2 backfill ran alongside other jobs (RNNoise r1 0.17, r2 0.36; DeepFilterNet3 r1 0.68, r2 0.39). The **uncontended r3 figures (RNNoise 0.092, DeepFilterNet3 0.088)** are the ones REPORT.md uses.
23. **ASR on r3 hit the 20-minute limit** after 300 transcriptions. It was resumed in method-priority batches. The streaming Wiener variants (8 and 32 ms) and the TSE oracle were not transcribed (CPU budget). They have objective metrics only.
24. **The `analyze.py` condition list is hard-coded for r1/r2**, so a separate `selab/analyze_r3.py` was written. The pandas markdown export needed `tabulate` (installed).
25. **The listening-test smoke check returned HTTP 000** because the curl request went through the sandbox proxy. With `--noproxy` it returned 200.

## Still not executable here
- **Human listening data**: the test is built and verified, but needs real listeners. Rows from `--selftest` are tagged `listener_type=synthetic` (Whisper as a stand-in listener) and kept separate in the analysis. They are not human results.
- **Real multichannel recordings**: none available in reach. The online MVDR is still evaluated on simulated rooms only.
- **DeepFilterNet3 frame-by-frame streaming timing**: its real-time path lives in the Rust `libDF` C API / LADSPA plugin and is not exposed in Python. Its RTF here is offline batch, and its latency (40 ms) comes from its config.

## Round 5 (2026-10-21/22): real LibriCSS 7-mic recordings, simulated twin, DOA, DFN3 frame timing
Completed: 144 real items from 24 LibriCSS recordings (range-read from the 6 GB zip) with system-identified references; DOA error analysis (n=122); real-set processing for the core methods plus cascades (48-item panel); twin (r5sim); Whisper ASR on the panel; cluster-bootstrap CIs and Holm correction; context-window, enrolment, reference-quality and idle-RTF sensitivity checks; DFN3 libdf C-API frame timing (12 files, 7,923 frames); listening/r5 pack and round5_listening.zip; listening_test --set r5 build (90 stimuli); app.py round-5 tabs (HTTP 200); REPORT_R5.md/pdf. Full results and the critique are in REPORT_R5.md.
Failures and fixes: the co-tenant lab drove load to 9-15 and the OOM killer stopped 4 jobs; the sandbox restarted 3 times (wiped /tmp, so the Rust builds were redone); linking on the workspace FS crashed, so builds moved to /tmp with a zig wrapper; a gain-staging bug (the recordings sit at -53 dBFS, so DFN3 erased speech) was fixed by normalising neural inputs to -26 dBFS (old outputs kept as *_rawlevel); RTFs measured under load were inflated 3-9x and were remeasured idle.
Cut: full-144 ASR for DFN3, the cascades, DS, MVDR and TSE; twin secondary methods; mask-MVDR variants; PESQ.
Still not executable: human listening data; in-ear acoustic measurement; live (non-loudspeaker) talkers.

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
5. **Twin rows overwrote real rows in the analysis** (found 2026-10-22 ~14:48 UTC): `load_wer("r5")` globbed `wer_r5*.csv`, which also matched the twin's `wer_r5sim*.csv`; once the twin was transcribed, sim word-correct replaced real word-correct for the same item ids (e.g. panel ds_td tracked read −0.024 instead of +0.042; held-out ds_td tracked −0.000 instead of −0.008). Fixed with exact patterns (`wer_<tag>.csv`, `wer_<tag>.part*.csv`) in analyze_r6.load_wer, score_r6 (both done-checks) and score_r5; summary regenerated. Panel numbers quoted before the twin existed were unaffected.
6. **Duplicate method in the held-out ASR list**: ds_td_rt was listed twice (baseline + frozen pick), so its items would have been transcribed twice. De-duplicated in holdout_r6.methods_for before the test ASR resumed.
7. **Forest plot crash**: `errorbar(ecolor=<list>)` is not accepted; now one errorbar call per point (summary_r6). Title/xlabel clipping fixed with bbox_inches="tight".
8. **Sandbox restart at 14:20 UTC**: nothing of round 6 was running; held-out processing was already complete (re-run was a no-op) and ASR resumed from the part files.

Round 6 completion (2026-10-22, 14:20-15:00 UTC):
- Held-out test (sessions 3-5, 72 items) ASR for 8 methods; twin (r5sim) ASR for all 6 planned methods on 48 items (not cut); objective metrics (11 methods, panel); idle timing (load avg 0.65; a first run right after the objective job, load ~2.7, gave the same means and is kept in work_r6/timing_loaded/).
- New: selab/onset_r6.py (tracker accuracy vs time since target-turn / overlap onset -> results/r6/tracker_onset.csv, figs/tracker_onset.png); work_r6/holdout_brittle.py (results/r6/whisper_brittleness_holdout.csv); work_r6/holdout_fig.py (figs/holdout_forest.png).
- Held-out, overlapped (n = 54, 9 recordings), Δ word-correct vs unprocessed: R5 DS +0.062 [+0.033, +0.098]; ds_td tracked −0.008 [−0.036, +0.020]; sd4 (+6 dB WNG) tracked −0.004 [−0.041, +0.037]; sd8 tracked −0.028 [−0.086, +0.021]; ds_td REF +0.054 [+0.006, +0.100]; sd4 REF +0.071 [+0.022, +0.133]; sd8 REF +0.096 [+0.039, +0.162] (vs R5 DS +0.034 [−0.007, +0.096], Holm p = 0.53).
- Panel correction: sd4 REF vs R5 DS (+0.057 [+0.013, +0.113]) does not survive Holm (p = 0.23); sd8 REF vs R5 DS does (+0.082, p < 0.001).
- listening_r6 now writes 4 versions per set (unprocessed, R5 DS, sd8 tracked, sd8 REF); 6 sets, 24 mp3 + README; round6_listening.zip passes `unzip -t`.
- app.py: round-6 4 ms option now uses the frozen +6 dB WNG floor; smoke test (work_r6/app_smoke_r6.py) ran both superdirective options on OV20_s0_6930-76324-0005 with and without enrolment (finite, non-silent outputs); HTTP 200 on localhost:7860.
- REPORT_R6.md / REPORT_R6.pdf (8 pages; rendered to PNG and checked; table column widths fixed). `ρ` added to docs/pdf_header.tex.
Cut: gm8/rtf8/ds_td REF in the twin; held-out objective metrics; full-144 ASR for non-frozen configurations; native-code timing and overrun counts.
Still not executable: human listening data; in-ear measurement; live talkers.

## Round 7, phase 1 (2026-10-24 UTC): EasyCom acquisition and preparation
- 02:01 UTC: fresh sandbox, nothing of r7 present. Public release assets reachable without login (HTTP 302 -> 200, 2,146,435,072 B per part). Started scripts/r7_download.sh (sequential curl -C -, size-checked, .partial -> final rename; no wget/pigz on this machine) and selab/extract_r7.py (streams the parts in order through gzip+tar as they complete, extracts only Calibration/ and Main/{Glasses_Microphone_Array_Audio,Close_Microphone_Audio,Speech_Transcriptions,Tracked_Poses,Metadata}/Session_{4,10,11,12}; tar is alphabetical so it stops once it passes Main/Tracked_Poses, i.e. before Main/Video_Compressed).
- Note: a plain `nohup ... &` in the tool shell got killed when the tool call timed out; launching as `(setsid nohup cmd > log 2>&1 < /dev/null & echo $! > pidfile)` survives.
- Cloned third_party/EasyComDataset (README; data files are git-lfs pointers only) and third_party/spear-tools (reference code only; no SPEAR data downloaded).
- Installed h5py into .venv (for Device_ATFs.h5).
- ATF frame convention determined from the measured IRs (results/r7/atf_convention.md): head frame X left, Y up, Z forward; az = atan2(x,z) (+ = left), ATF Phi == az, Theta == 90 - el (median inter-mic delay error vs README geometry 20 us; the opposite Phi direction gives 221 us).
- Tracker steering check (synthetic white noise rendered through the measured ATF at el 0, az 60/300/180): r6 tracker with ATF steering (Theta = 90 row, free-field-referenced complex interpolation to 1 deg) recovers 60/299/180; with FREE-FIELD steering from the README positions it returns 174/236/208. The frame mics are almost collinear (left-right) and the head/frame scatters strongly (ATF phase vs free field off by 20-60 deg at 0.5-1 kHz and up to 180 deg at 4-6 kHz), so free-field steering is not usable on this array; the tracker uses the ATF.
- Code: selab/ec_r7.py (readers, geometry), selab/prep_r7.py (stages resample/align/doa/validate/items), selab/onset_r7.py (head/track/report), selab/extract_r7.py, scripts/r7_download.sh.
- 02:16: 16 kHz array cache written while waiting for transcripts (pass-1 lags deferred until Speech_Transcriptions is extracted).
- 02:17 extraction DONE (624 files; everything needed sits in parts 001-016 — the tar is alphabetical and Main/Video_Compressed starts at the end of part 016). Download stopped at part 018 (STOP file + kill of explicit PIDs 3274/5385); parts 017-033 never needed.
- Main/Metadata was missed by the first extractor filter (files are Main/Metadata/Session_N.txt, not inside a Session_N folder). Fetched the 4 files from the public git-lfs media URL instead; sha256 29847146... equals the LFS oid in the cloned repo (all 12 sessions share one identical metadata file). Filter fixed in extract_r7.py.
- Verification: all 628 wanted members present with the tar-listed sizes (106 glasses minutes, 293 close-mic files, 106 transcription + 106 pose JSONs, Calibration); all wavs then fully read by the resample/align stages without error. Parts deleted (marker files *.deleted keep the downloader from refetching).
- Failure: transcription JSONs are not all UTF-8 (cp1252 accents) -> resample pass 1 crashed after 7 minutes; reader now falls back to cp1252; resumed.
- Format facts learned: Target_of_Speech is a LIST (e.g. [4], ['Group'], ['None'], ['Group', 3]); poses are 1200 frames/min with Frame_Number from 1; the wearer is participant 2 in all four sessions (tracked, transcribed, no close mic).
- Alignment: per-minute clock offsets differ by several ms between minute files (offset std ~3 ms within a session), so every (minute, participant) is fitted separately; residual clock-rate error after the nominal 48008.6 Hz is ~-4 ppm (median effective rate 48008.2-48008.4 Hz per session). Close mics with too little speech in a minute (86 of 293) first fell back to a session-median offset, which is wrong by ~3 ms; replaced by the minute's shared clock offset (other close mics) + pose distance/c ("minute_clock_plus_pose"); out-of-sample check of that model (leave-one-mic-out within a minute): median |error| 0.43 ms, p90 1.53 ms.
- DOA convention check on 3 minutes of session 4: body->world R(q) with direction = R^T (p_talker - p_wearer) gives SRP(ATF) median az error 3.8 deg; the transposed alternative gives 37.9 deg -> R^T used.
- 02:20-02:40: doa (106 minutes), validate (3,827 single-talker 0.5 s blocks, 102 minutes: median az error 4.5 deg, 80% within 15 deg; 3-D 24 deg because SRP elevation is coarse/biased on this array), items (val 762 / test 472), qc (item-level lag median 0.15 / 0.05 ms; 36/27 align_suspect, mostly fully overlapped), head onset (1,565 turns), R6 tracker (rtn) per minute with ATF and free-field steering on all 4 sessions (3.3 s per minute), report + figure.
- Key result: head orientation within +-15/30/45 deg at 0-0.25 s after turn onset = 0.30/0.54/0.70 (to wearer 0.43/0.71/0.85; to group 0.22/0.51/0.68); after 4 s 0.39/0.75/0.86. R6 tracker (ATF, val): 0.21/0.35/0.52 at onset, 0.62/0.73/0.82 after 4 s. Summary: results/r7/PHASE1_SUMMARY.md.
- Phase 1 complete; no jobs left running. Disk: data/easycom/Main 11 GB, r7_16k cache 3.4 GB, mixtures/r7 2.7 GB (all EasyCom-derived, never distribute).

## Round 7, phase 2 (2026-10-24 UTC): ATF beamformers + ASR on EasyCom
- 02:40 UTC: fresh look; phase 1 outputs present, no jobs running. Installed num2words into .venv (text normalisation: numbers as words).
- New code: selab/bf_r7.py (ATF interpolation: free-field-phase residual, bilinear in el/az over the 17x60 grid; RTFs d = h/h[ref];
  ATF diffuse coherence (1020 dirs, sin(theta) weights); ATF fractional delays from the RTF GCC peak; DSTimeATF (21-tap sinc,
  2 ms blocks), SDATF (superdirective + WNG floor, sqrt-Hann WOLA 4/8 ms), r5ds (32 ms STFT, blind SRP over ATF el=0 grid),
  tracker states (r6 rtn via onset_r7.make_tracker('atf')), head-prior hybrid, REF per-50 ms steering);
  selab/run_r7.py (processing, ASR, objective, val-tune -> freeze -> test pipeline, 2 spawn workers, resumable);
  selab/analyze_r7.py (cluster bootstrap 2000 over session_minute, Holm across new methods); selab/timing_r7.py.
- Checks: ATF interpolation exact on grid nodes; az 90 -> ch1 leads ch2 by 4.3 samples (272 us; phase-1 IR xcorr 240 us);
  ds_td latency 0.75 ms head-steered (fixed direction) / 1.07 ms steerable; smoke test on 10 val items: ref_sd8 SI-SDR +4 dB and
  ESTOI +0.10 over the front mic, so steering/alignment work.
- Scoring conventions: scored span [utt_offset_samples:]; ASR input normalised to -26 dBFS RMS; faster-whisper base.en int8 greedy
  (cpu_threads=1 per worker, same decoding settings as r6); text normalisation strips any single-letter [X] code ([L]/[C]/[T]/[U]/[H]
  and also [X]), '*' and hyphens (fragments like "k-" stay as "k"), numbers -> words (num2words; 4-digit 1100-2099 as years).
  SI-SDR/ESTOI vs aligned close mic with a +-0.5 ms integer lag search (outputs are aligned to the reference mic, the close mic to ch2).
- 02:47 UTC: launched pipeline (PID file results/r7/pids/pipeline.pid, log logs/r7_pipeline.log):
  stage A val sub300 front1-4 + hs_sd8 ref mic 0-3 (WNG 0) -> stage B WNG {-6,-3,0,3,6} -> stage C hybrid X{20,30,45} x thr{1,3,8}
  -> frozen_r7.json -> test (all 472 items, 14 frozen methods, ASR on the 434 with words) -> val sub300 frozen set.
  ASR throughput ~0.9 items/s with 2 workers.
- ~03:00 UTC: sandbox restart killed the pipeline mid stage A (722 ASR rows kept). Added per-item try/except in ASR/objective
  (unreadable output wav -> deleted and re-processed). Relaunched 03:03 (resumes from the per-part CSVs).
- 03:25 UTC: stage A done (val sub300, word-correct): front1 .380, front2 .412, front3 .390, front4 .371 -> unproc_front = ch2;
  hs_sd8 WNG 0 dB with ref mic ch1 .420, ch2 .421, ch3 .403, ch4 .407 -> reference mic = ch2 (index 1).
  Stage B (WNG floor -6/-3/+3/+6 dB with ref ch2) started.
- Analysis/summary/timing code written and dry-run tested on val data with aliased method names (selab/analyze_r7.py,
  selab/summary_r7.py, selab/timing_r7.py); summary needs `tabulate` for to_markdown (check: python -c "import tabulate").

## Diarization track (2026-10-24 UTC): who said what
- 04:12 UTC start. Found the r7 pipeline (PID 708) not running: the sandbox restarted at 04:11 UTC, last pipeline log line 03:59 UTC (stage C started). This track did not restart it (instruction: never kill/restart it); it is resumable via its own command.
- Installed silero-vad 6.2.3 and pyannote.metrics 4.2.0 into .venv (no accounts; no gated pyannote models used).
- New code selab/diar/: core (Silero VAD, ECAPA 1.5 s/0.5 s windows, NME-SC spectral + AHC, frame voting, Whisper word assignment),
  spatial (SRP-PHAT 0.5 s blocks; LibriCSS free-field 7-mic, EasyCom ATF el=0), data (LibriCSS clock-mapped refs; EasyCom session concatenation,
  head yaw from r7 doa cache), metrics (+tests: DER matches pyannote.metrics within 0.02 on 40 random cases), features (cached), score (tune/test), run (CLI).
- Pose check: world az of a talker = head az + head yaw (atan2(fwd_x, fwd_z)); median residual 1.1-1.5 deg on session 12 minute 3 (opposite sign: 28-133 deg).
  Talker world az std ~2.5 deg vs head-frame az std ~12.5 deg within that minute -> raw head-frame DOA smears each talker.
- 04:27 UTC launched features job: results/diar/run_features.sh (nice 19, 1 thread), log logs/diar_features.log, PID file results/diar/pids/features.pid.
  ECAPA cost ~0.12 s per 1.5 s window on 1 thread (RTF ~0.25).
- 04:40 UTC: someone else restarted the r7 pipeline (PID 1420, `python -m selab.run_r7 pipeline`); my jobs stay at nice 19 / 1 thread and I pause
  (SIGSTOP/SIGCONT) my own features job while my tuning runs, so only one of my heavy jobs runs at a time.
- EasyCom finding during tuning: Silero VAD on array ch2 has recall 0.34 at thr 0.5 (0.61 at 0.05) with precision 0.95 against the transcript
  frames, which cover 85% of session-4 time (restaurant-noise playback; utterance-level labels include pauses). Energy VAD is useless (always on).
  -> VAD grid extended to thr {0.02..0.2} and gap bridging min_sil {0.15, 0.5, 1.0}; NME-SC sped up (12 p values, partial eigen-solves) and
  windows > 1500 are clustered on a strided subset and the rest assigned by mean affinity (core.cluster_big).
- EasyCom tune (sessions 4/12) frozen in results/diar/frozen_diar.json (v1 grid kept as frozen_diar_v1.json / tune_easycom_v1.csv):
  tune DER c0.25: spectral 45.6, AHC 42.4, spatial (pose-compensated 'world') spectral 43.2, AHC 'max' 42.3, platform (close mics) 28.9.
- 05:01 UTC: replaced the single features job by the full chain results/diar/run_all.sh (log logs/diar_all.log, PID file results/diar/pids/run_all.pid):
  features ec_test (+ASR) -> score test (EasyCom) -> features lc_tune/lc_test (+ASR) -> tune libricss -> test both -> summarize -> tables.md.
- 05:20 UTC: EasyCom test (sessions 10/11) scored -> results/diar/test_rows_easycom.csv (first attempt crashed writing platform RTTM with
  string labels; core.write_rttm fixed, re-run with the features job paused).
- DOA diagnostic (single-talker windows, SRP peak az): wearer P2 is tight in the head frame (+-2..11 deg) but smeared in the world frame
  (+-13..21 deg); some talkers tighten after pose compensation (s4 P3 15->6 deg, s12 P6 12->8), others are unusable (P1/P4/P5 +-40..80 deg),
  and several talkers sit within ~15 deg of each other and of the wearer (front of the table) -> DOA helps on s10, hurts on s11.
  Added confidence gating (SRP peak sharpness, percentile 30..80 ramp, both windows must be reliable): score.py `gate` (tune on 4/12, test 10/11).
- 05:29 UTC: sandbox restart killed my chain (and lost a few seconds of unsynced writes: run_gate.sh/log). r7 pipeline was relaunched by someone else
  (PID 703). Relaunched everything as results/diar/run_all2.sh (log logs/diar_all2.log, PID file results/diar/pids/run_all2.pid):
  gate tune+test (EasyCom) -> features (cached, resumes) -> tune LibriCSS -> test both -> summarize (+enrolment naming) -> tables.md.
- 05:34 UTC gated DOA: tune 4/12 DER c0.25 42.2 (spectral, world, beta 0.3, sigma 30); test 10/11 37.9 vs A_spectral 38.0 (fixes the s11 collapse
  of ungated world fusion, 64.4 -> 41.3, but no net gain).
- EasyCom test summary (DER c0.25 / cpWER): platform 27.7 / 72.8, A_spectral 38.0 / 59.4, A_ahc 39.4 / 59.2, oracle-VAD spectral 23.0 / 58.3,
  oracle-K 38.6 / 56.7, raw head DOA (AHC) 40.9 / 60.1, pose-oracle world (AHC) 44.9 / 68.4, gated spectral 37.9 / 58.0; speaker-agnostic WER 50.0.
  Written to results/diar/results.md (+ tables_easycom.md, test_summary.csv, test_failure_frames.csv, test_confusion_pairs.csv, demo_easycom.txt).
- LibriCSS still computing in run_all2.sh at 05:40 UTC (features at lc_tune; ECAPA RTF ~0.58 while the r7 pipeline's 2 workers run).

## Real-time demo (2026-10-24 UTC): Conversation Bubble voice-boost listening demo
Spec: /workspace/projects/602d514d-.../portfolio/prompts/realtime-listening-demo.md. Code selab/rtdemo/, outputs results/rtdemo/ +
listening/rtdemo/, checklist results/rtdemo/CHECKLIST_RTDEMO.md, one-pager results/rtdemo/README_DEMO.md. All my jobs nice 19, 1 thread,
one at a time; never touched the R7 pipeline (PID 3450) or the diarization chain.
- 18:55 UTC: oriented. EasyCom glasses audio = 6 ch (frame ch1-4 + in-ear ch5-6), NOT 7; LibriCSS = 7. R7 frozen: front ch2, ref idx 1,
  WNG -6, X 20, thr 8 (frozen=true). PIPELINE_DONE not present (pipeline in the val-frozen stage; test stage finished).
- Scenes (selab/rtdemo/scenes.py, 16 s): sim_street, sim_restaurant (LibriSpeech + pyroomacoustics + synthetic car pass-by from the ANC
  lab's own simulation; licence-clean), libricss_ov40 (real, CC BY 4.0), easycom_s10/s11 (real, CC BY-NC, internal only; windows picked
  by max non-wearer talker coverage + overlap, wearer pose valid >= 95%).
- Engine (selab/rtdemo/engine.py): 2 ms blocks; reuses bf_r7.SDATF / DSTimeATF / onset_r7 ATF tracker (EasyCom) and r6.STFTBF / DSTime /
  Tracker rtn (others); incremental port of bf_r7.hybrid. Equivalence vs lab code on 4 s of easycom_s10: tracker az and hybrid az identical
  (max diff 0), hs_sd4/hyb_sd4 outputs equal to bf_r7.run to 1.8e-9 (float32 cast). Chose sd4 (4 ms) over sd8 (8 ms = cap, misses 5 ms target).
- First render showed 2-6 ms per-block spikes when the tracker moved to an uncached direction (lazy weight design): now the sd4 weight
  table (360 directions) is precomputed at start-up (0.6 s) and shared by head/trk/hyb filters. Verified bit-identical vs lazily designed
  weights, each mode alone in a fresh engine: 32/32 (results/rtdemo/verify_single_mode.json).
- SIMULATED noise-cut (selab/rtdemo/anc_sim.py): min-phase 512-tap FIRs from (a) per-1/3-oct d/e reduction of c1_glasses_4mic7_causal
  (7.8 dB(A) pass-by sim), (b) anc_plain_causal restaurant octave curves (companions -5.2, babble -3.7 dB(A)).
- Critique -> fix: sim_street v1 put the road behind the 4-mic LINEAR array (its mirror lobe) and lin4 used R6's WNG +6 dB, which on 4 mics
  is the delay-and-sum limit (10log10 4 = 6.02 dB). v2: road on the wearer's right; lin4 uses the R7 4-mic WNG floor -6 dB. Exact SNR gains
  (results/rtdemo/sim_snr.json): hs_sd4 +0.38 dB street, +0.82 dB restaurant; hs_ds +0.20/+0.37; trk_sd4 -0.86/-1.95; hyb = hs (hybrid
  never reached thr 8 inside the window). WNG sweep (results/rtdemo/sim_wng_sweep.json, v1 street geometry): gains grow only to ~+1.1 dB at
  -10 dB. A 12 cm 4-mic aperture barely helps below ~1.5 kHz: honest expectation is a subtle effect.
  ANC sim: street talker -6.9 / traffic -7.6 dB(A) (SNR +3.7 dB); restaurant talkers -5.3 / babble+other -3.9 dB(A) (SNR -1.6 dB).
- Interim R7 test (raw means of wer_test.part*, 434 items, NOT the official analysis): front .343, hs_sd4 .404, hyb_sd4 .403, hs_sd8 .409,
  hyb_sd8 .413, r5ds .408, trk_sd4 .282, unproc_ear .267.
- Timing (results/rtdemo/latency_compute.md; bench_under_r7_load.json, load 4.4-4.9, nice 19): per-block median 0.004 (raw) to 0.029 ms
  (sd4); all modes 0.11-0.12 ms median, p95 0.16-0.28; tracker step median 0.92-1.52 ms (p95 ~5); total live RTF 0.18-0.25.
  Live paced loop (selab.rtdemo.live, nice 0 for 16 s each, ~0.2-0.35 of one core; load 4.6-5.0): misses 14.4% (easycom_s10), 30.2%
  (libricss_ov40), compute median 0.22 ms, output bit-identical to the pre-render. A nice-19 live run was starved (>100 s for 16 s; aborted).
  Also one 2 s live smoke test at nice 0.
- Interface: WebAudio page selab/rtdemo/web/index.html (synchronised sources, gain switching, A/B, blind A/B -> POST /rtdemo/api/pref ->
  results/rtdemo/blind_prefs.csv, azimuth dial + timeline, level match, limiter), routes in selab/rtdemo/server.py, mounted into app.py
  (new tab + /rtdemo/ on port 7860 via FastAPI + gr.mount_gradio_app; backup of the old app.py in results/rtdemo/app.py.bak_pre_rtdemo).
  JS syntax-checked and smoke-tested in node with DOM/WebAudio stubs (3 scenes, switch, A/B, blind vote); not tested in a real browser.
  App launched 19:16 UTC (scripts/run_rtdemo_app.sh, PID in results/rtdemo/app.pid); /rtdemo/, data, POST pref (test row deleted) and / OK.
- Clips: selab/rtdemo/export.py -> listening/rtdemo/clips/{external_ok,INTERNAL_ONLY_easycom}/, results/rtdemo/clip_list.{csv,md},
  listening/rtdemo/clips_external_ok.zip (no EasyCom audio).
- Neural post-filter skipped: lab-measured RNNoise 20 ms, DeepFilterNet3 40 ms, Demucs 41 ms, all > 8 ms cap.

## Round 7 finish (2026-10-24 ~15:35 CDT)
- Pipeline DONE; ran analyze_r7 --split test, timing_r7 --n 12 (load 0.8), summary_r7. Wrote REPORT_R7.md/pdf (pandoc+pdflatex, docs/pdf_header.tex).
- Headline (434 test items, Whisper base.en): head SD8 +0.066 vs front, hybrid SD8 +0.070, tracked SD8 -0.064, REF SD8 +0.173; head/hybrid vs R5 DS ~0.00 (CI +-0.045). Onset 0-0.25 s within 30 deg: head 54%, tracker 35%.

- 2026-10-25 Diarization: LibriCSS chain finished (ALL DONE); tables in results.md, demo_libricss.txt, REPORT_DIAR.pdf rendered. Track done.
