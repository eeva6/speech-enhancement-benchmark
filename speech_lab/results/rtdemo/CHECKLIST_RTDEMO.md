# Real-time demo checklist (2026-10-24)

## Engine
- [x] Causal 2 ms block engine, reusing lab code (bf_r7, onset_r7, r6). Matches lab outputs (tracker/hybrid identical; filter diff 1.8e-9)
- [x] R7 frozen params used (front ch2, ref idx 1, WNG -6 dB, X 20, thr 8); sd4 chosen (4 ms <= 5 ms target; sd8 = 8 ms cap)
- [x] Channel count verified: EasyCom = 6 ch (4 frame + 2 in-ear), not 7; LibriCSS = 7
- [x] Licence-clean scenes: sim_street, sim_restaurant (LibriSpeech + synthetic), libricss_ov40 (CC BY 4.0)
- [x] Per-block compute measured (mean/median/p95/p99/max), RTF, with load average: results/rtdemo/latency_compute.md
- [ ] Re-measure bench + live loop on an idle machine (after results/r7/PIPELINE_DONE): commands in README / final report

## Modes
- [x] (a) raw front mic (+ in-ear mics on EasyCom)
- [x] (b) head-steered superdirective 4 ms (+ head-steered DS 0.6-0.75 ms)
- [x] (c) tracker-steered (R6 rtn tracker) + R7 head-prior hybrid
- [x] (d) neural post-filter: skipped, documented (RNNoise 20 / DFN3 40 / Demucs 41 ms > 8 ms cap)
- [x] (e) SIMULATED noise-cut, labelled; restaurant curve cuts talkers too

## Interface
- [x] WebAudio page with instant switching: scene picker, play/pause, seek, A/B toggle, blind A/B -> CSV, azimuth dial + timeline, limiter, level match
- [x] Mounted in app.py (new tab + /rtdemo/ on port 7860); standalone server option
- [x] Pre-render bit-identical to live block processing (32/32 single-mode re-runs; live paced loop bit-identical)
- [x] Genuinely live path: selab.rtdemo.live (paced loop; --device for sound card, untested here: no PortAudio)
- [ ] Real-browser test by J (only a node smoke test with stubs was possible here)

## Clips and docs
- [x] 16 s before/after pairs for 5 scenes, raw + loudness-matched, + SIMULATED track; clip list with licence/external flags
- [x] Licence-clean zip (no EasyCom)
- [x] README_DEMO.md (what it shows and does not show)
- [x] EXECUTION_LOG.md "Real-time demo" section
- [ ] If R7 final analysis names a different winner than hs/hyb sd8~sd4, revisit mode (b) (interim: hyb_sd8 .413 > hs_sd8 .409 > hs_sd4 .404)
