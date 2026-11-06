# Round 5 checklist (kept current during the run)

- [x] Read README, REPORT, REPORT_R4, EXECUTION_LOG
- [x] LibriCSS licence and size: code MIT (github chenzhuo1011/libri_css), audio = LibriSpeech test-clean (CC BY 4.0) replayed; full zip 6.0 GB on Google Drive
- [x] Partial download via HTTP range reads of the zip: 24 recordings (0S/OV10/OV20/OV40 x sessions 0-5), ~2.2 GB
- [x] Build 144 real items + system-identification references (target image, reference DOA)
- [x] DOA reference validated (same loudspeaker in independent recordings agrees within 3 deg)
- [x] DOA estimation error (SRP-PHAT blind / target-only / causal; pyroomacoustics SRP and MUSIC cross-check)
- [x] Methods on real set (14)
- [x] Simulated twin (stats, room fit, simulation) + methods on twin
- [x] Scoring: objective (estimated ref) + Whisper WER / word-correct
- [x] Analysis with cluster bootstrap CIs; sim-vs-real
- [x] DFN3 Rust build (deep-filter + libdf C API) and frame timing
- [x] Listening test: one-command launch + instructions + r5 stimulus set
- [x] listening/r5 mp3 pairs + zip
- [x] app.py: multichannel tab + real-recordings tab; HTTP 200 smoke test
- [x] Independent critique, fixes, rerun
- [x] REPORT_R5.md + PDF, EXECUTION_LOG append
- Cut: full-144 ASR for DFN3/cascades; twin secondary methods; mask-MVDR; PESQ
