# Who said what: diarization results

Status 2026-10-24 05:40 UTC:
- **EasyCom: complete.** Test sessions 10/11, every variant.
- **LibriCSS: running.** The resumable chain `results/diar/run_all2.sh` is computing features, then the tuning on sessions 0-2, then the test on sessions 3-5. When it finishes it writes `results/diar/tables.md` with the full tables for both datasets; the LibriCSS section below must then be filled in from it. The CLI already runs end to end on a real LibriCSS 7-mic recording (`results/diar/cli_smoke/`).

How the platforms do it is in `HOW_THEY_DO_IT.md`. Code is in `selab/diar/`. Hyper-parameters were tuned only on the held-out sessions (EasyCom 4/12, LibriCSS 0-2) and frozen in `frozen_diar.json` before testing.

## Systems compared
| id | what it is |
|---|---|
| platform | **The "Zoom path".** Each participant has their own stream. EasyCom uses the aligned close-talk mics with Silero VAD and cross-talk dominance. The wearer has no close mic, so wearer speech is array speech while no close mic is active; P1 also has no close mic. LibriCSS uses the dry loudspeaker feeds with energy VAD. Words from the mixed-stream ASR are attributed by this timeline, like Recall.ai's speaker-timeline diarization. |
| A_spectral | Single channel: Silero VAD → ECAPA-TDNN on 1.5 s windows with 0.5 s hop → NME-SC spectral clustering (speaker count from the eigengap) → centroid refinement → Hann-weighted frame voting with ≥ 0.25 s runs → Whisper word timestamps. |
| A_ahc | Same, but average-linkage AHC on cosine distance with a tuned threshold. |
| *_oracleVAD | Reference speech regions replace Silero, which isolates clustering errors from VAD errors. |
| A_spectral_oracleK | True number of speakers given. |
| B_* | Spatial: SRP-PHAT azimuth per window. EasyCom uses the measured glasses ATF (el = 0 row); LibriCSS uses free-field 7-mic steering. A von Mises angle kernel is fused into the affinity, S = (1-β)·cos + β·A_doa. EasyCom variants: `head` = raw head-frame DOA. `world` = head DOA + head yaw from the tracked pose, labelled **pose-oracle** (a real device would need an IMU). `max` = max of the world and head kernels, so the wearer, who is fixed in the head frame, stays coherent. `gated` = `world` with the DOA kernel weighted by SRP-peak sharpness. |

Metrics:
- **DER** is frame-based (10 ms) per the NIST definition, with overlapped speech scored. c0.25 = ±0.25 s no-score collar; c0 = no collar. It agrees with pyannote.metrics within 0.02 on 40 random tests (`selab/diar/tests_metrics.py`).
- **JER** comes from pyannote.metrics.
- **cpWER** is concatenated minimum-permutation WER (Hungarian matching over speakers).
- **WER (speaker-agnostic)** is the same ASR scored without speakers. It is the floor for cpWER.
- **Speaker count** = clusters with ≥ 5 s of speech.

## EasyCom (test sessions 10 + 11, about 47 min, mean of 2 sessions)
| variant | DER c0.25 | DER c0 | miss | FA | conf | JER | spk-count err abs / signed | cpWER | WER (spk-agnostic) |
|---|---|---|---|---|---|---|---|---|---|
| **platform (close mics)** | **27.7** | **36.2** | 21.5 | 5.0 | 9.8 | 45.2 | 1.0 / −1.0 | 72.8 | 50.0 |
| A_spectral | 38.0 | 50.3 | 30.8 | 8.0 | 11.5 | 47.0 | 1.0 / +1.0 | 59.4 | 50.0 |
| A_ahc | 39.4 | 51.5 | 28.8 | 10.4 | 12.3 | 47.0 | 2.0 / +2.0 | 59.2 | 50.0 |
| A_spectral_oracleK | 38.6 | 48.9 | 30.8 | 8.0 | 10.1 | 50.0 | 0 / 0 | **56.7** | 50.0 |
| A_spectral_oracleVAD | **23.0** | **33.1** | 18.1 | 0.0 | 15.0 | 37.0 | 1.0 / +1.0 | 58.3 | 50.0 |
| A_ahc_oracleVAD | 32.0 | 41.0 | 18.1 | 0.0 | 23.0 | 45.6 | 2.0 / +2.0 | 65.4 | 50.0 |
| B_head_rawDOA (AHC) | 40.9 | 52.5 | 28.8 | 10.4 | 13.4 | 48.7 | 2.0 / +2.0 | 60.1 | 50.0 |
| B_world_poseOracle (AHC) | 44.9 | 55.7 | 28.8 | 10.4 | 16.5 | 51.6 | 3.0 / +3.0 | 68.4 | 50.0 |
| B_max_poseOracle (AHC) | 44.2 | 55.0 | 28.8 | 10.4 | 15.8 | 51.2 | 2.5 / +2.5 | 67.2 | 50.0 |
| B_spatial_spectral (world, ungated) | 51.4 | 60.3 | 30.8 | 8.0 | 21.5 | 63.9 | 1.0 / 0 | 74.0 | 50.0 |
| B_gated_spectral (world, gated) | 37.9 | 49.1 | 30.8 | 8.0 | 10.3 | 47.8 | 1.0 / +1.0 | 58.0 | 50.0 |
| B_head_rawDOA_oracleVAD | 28.6 | 37.6 | 18.1 | 0.0 | 19.6 | 42.2 | 2.0 / +2.0 | 59.9 | 50.0 |
| B_max_poseOracle_oracleVAD | 31.3 | 39.7 | 18.1 | 0.0 | 21.7 | 44.7 | 2.5 / +2.5 | 66.5 | 50.0 |
| B_gated_spectral_oracleVAD | 28.0 | 35.3 | 18.1 | 0.0 | 17.2 | 46.0 | 0.5 / −0.5 | 59.6 | 50.0 |

Per-session rows are in `test_rows.csv`; tuning grids are in `tune_easycom*.csv`. With only 2 test sessions the per-session spread is large: A_spectral DER c0.25 is 37.1 / 38.8, and B_spatial_spectral is 38.3 / 64.4. Read differences under about 3 points as noise.

**What EasyCom says:**
1. **The platform path wins on timing (DER 27.7 vs 38.0) but loses on words (cpWER 72.8 vs 59.4).** Close mics pick up the wearer's turn onsets as cross-talk, so the first word of a turn goes to the wrong person (`transcripts/platform/ec_s10.txt`: "P6: I / glasses: don't know you guys told me…"). P1 and the wearer share the "glasses device", so the platform finds one speaker too few (signed −1.0). These are the two failure modes Recall.ai documents for speaker-timeline diarization: overlap/cross-talk and several people on one device. Per-stream ASR ("perfect diarization") would fix the first; it was not run, because of CPU limits.
2. **VAD is the biggest single error source.** The glasses' ch2 mic in restaurant-noise playback gives Silero a recall of 0.34 at threshold 0.5 against the transcript frames. Tuning drove the threshold to 0.02 with gap bridging. Oracle VAD alone cuts DER from 38.0 to 23.0 (c0.25).
3. **Raw DOA on a head-worn array does not help diarization, and pose compensation fixes the talkers but breaks the wearer.** On single-talker windows the wearer's DOA is tight in the head frame (±2–11°) but smeared after yaw compensation (±13–21°). Some talkers tighten with compensation (e.g. session 4 P3: ±15° → ±6°). Others are unusable (P1/P4/P5: ±40–80°). Several talkers sit within about 15° of each other and of the wearer's mouth direction. Ungated world-frame fusion collapsed on session 11 (DER 64.4, wearer split into many clusters). Gating by SRP sharpness removes the collapse (37.9 ≈ A_spectral 38.0) but gives no net gain. With oracle VAD the raw head-frame DOA helped on session 10 (24.1 vs 26.5) and hurt on session 11, so the DOA cue is not reliable on this array.
4. **ASR dominates cpWER.** Speaker-agnostic WER is already 50% (base.en on a far-field glasses mic in noise). Attribution adds about 7–9 points for A_spectral.

## LibriCSS (test sessions 3-5 × 0S/OV10/OV20/OV40, real 7-mic recordings)
Reference times come from `meeting_info.txt`, mapped to the recording clock with the round-5 offset/drift fit (`results/diar/cache/lc_*.clock.json`). The platform path uses the dry loudspeaker feeds. The ASR is the centre mic (ch0) with base.en.

### libricss (test)

| variant | DER c0.25 | DER c0 | miss | FA | conf | JER | spk count err (abs / signed) | cpWER | WER (speaker-agnostic) |
|---|---|---|---|---|---|---|---|---|---|
| platform | 0.3 | 1.8 | 1.4 | 0.4 | 0.0 | 2.0 | 0.00 / +0.00 | 22.9 | 18.2 |
| A_spectral | 9.3 | 13.0 | 10.3 | 1.2 | 1.5 | 15.2 | 0.00 / +0.00 | 22.3 | 18.2 |
| A_ahc | 10.6 | 14.4 | 10.3 | 1.2 | 2.8 | 17.1 | 0.25 / +0.08 | 24.3 | 18.2 |
| A_spectral_oracleK | 9.3 | 13.0 | 10.3 | 1.2 | 1.5 | 15.2 | 0.00 / +0.00 | 22.3 | 18.2 |
| A_spectral_oracleVAD | 7.7 | 10.2 | 8.9 | 0.0 | 1.3 | 12.3 | 0.00 / +0.00 | 22.1 | 18.2 |
| A_ahc_oracleVAD | 9.1 | 11.5 | 8.9 | 0.0 | 2.7 | 14.3 | 0.25 / +0.08 | 24.1 | 18.2 |
| B_spatial_spectral | 8.8 | 12.3 | 10.3 | 1.2 | 0.7 | 13.7 | 0.00 / +0.00 | 21.7 | 18.2 |
| B_spatial_ahc | 9.0 | 12.6 | 10.3 | 1.2 | 1.1 | 14.2 | 0.08 / +0.08 | 22.3 | 18.2 |
| B_spatial_spectral_oracleVAD | 7.2 | 9.4 | 8.9 | 0.0 | 0.5 | 10.5 | 0.00 / +0.00 | 21.5 | 18.2 |

### LibriCSS DER (collar 0, overlap scored) by overlap condition

| variant | 0S | OV10 | OV20 | OV40 |
|---|---|---|---|---|
| platform | 1.7 | 2.0 | 1.7 | 1.6 |
| A_spectral | 5.0 | 8.5 | 13.6 | 25.1 |
| A_ahc | 5.5 | 9.9 | 16.3 | 25.8 |
| A_spectral_oracleK | 5.0 | 8.5 | 13.6 | 25.1 |
| A_spectral_oracleVAD | 1.6 | 6.1 | 11.3 | 21.6 |
| A_ahc_oracleVAD | 2.2 | 7.6 | 14.0 | 22.2 |
| B_spatial_spectral | 4.0 | 7.9 | 12.6 | 24.5 |
| B_spatial_ahc | 5.0 | 7.9 | 12.8 | 24.6 |
| B_spatial_spectral_oracleVAD | 0.5 | 5.5 | 10.3 | 21.0 |

### Failure breakdown (collar 0)

| dataset | variant | DER single-talker frames | DER overlap frames | overlap share of ref speech | acc turns <1 s | 1-3 s | >3 s |
|---|---|---|---|---|---|---|---|
| easycom | A_spectral | 28.9 | 68.9 | 33.6 | 21.3 | 55.2 | 64.2 |
| easycom | A_spectral_oracleVAD | 16.6 | 65.4 | 33.6 | 26.8 | 65.9 | 73.5 |
| easycom | B_spatial_spectral | 45.1 | 67.6 | 33.6 | 27.2 | 44.5 | 52.3 |
| easycom | platform | 25.7 | 46.4 | 33.6 | 55.1 | 77.4 | 66.3 |
| libricss | A_spectral | 3.4 | 38.8 | 17.6 | 0.0 | 74.7 | 89.0 |
| libricss | A_spectral_oracleVAD | 1.2 | 38.7 | 17.6 | 0.0 | 76.5 | 90.6 |
| libricss | B_spatial_spectral | 2.8 | 37.8 | 17.6 | 0.0 | 76.4 | 89.7 |
| libricss | platform | 0.8 | 3.7 | 17.6 | 0.0 | 95.0 | 98.8 |

### Speaker-count estimates per test recording (clusters with >= 5 s)

| recording | n_ref | A_ahc | A_spectral | B_spatial_spectral |
|---|---|---|---|---|
| ec_s10 | 4 | 5 | 6 | 5 |
| ec_s11 | 5 | 8 | 5 | 4 |
| lc_0S_s3 | 8 | 8 | 8 | 8 |
| lc_0S_s4 | 8 | 9 | 8 | 8 |
| lc_0S_s5 | 8 | 8 | 8 | 8 |
| lc_OV10_s3 | 8 | 9 | 8 | 8 |
| lc_OV10_s4 | 8 | 8 | 8 | 8 |
| lc_OV10_s5 | 8 | 8 | 8 | 8 |
| lc_OV20_s3 | 8 | 8 | 8 | 8 |
| lc_OV20_s4 | 8 | 7 | 8 | 8 |
| lc_OV20_s5 | 8 | 8 | 8 | 8 |
| lc_OV40_s3 | 8 | 8 | 8 | 8 |
| lc_OV40_s4 | 8 | 8 | 8 | 8 |
| lc_OV40_s5 | 8 | 8 | 8 | 8 |

### Enrolment-based naming (LibriCSS test, A_spectral; first utterance of each speaker as enrolment)

Mean over 12 sessions: DER with optimal mapping 13.2, DER with names imposed 17.3, clusters named 89/96 (reference speakers 96).



## Failure analysis (EasyCom test; LibriCSS will be added in tables.md)
| variant | DER single-talker frames | DER overlap frames | overlap share of ref speech | frame accuracy on turns < 1 s | 1–3 s | > 3 s |
|---|---|---|---|---|---|---|
| A_spectral | 28.9 | 68.9 | 33.6 | 21.3 | 55.2 | 64.2 |
| A_spectral_oracleVAD | 16.6 | 65.4 | 33.6 | 26.8 | 65.9 | 73.5 |
| B_spatial_spectral | 45.1 | 67.6 | 33.6 | 27.2 | 44.5 | 52.3 |
| platform | 25.7 | 46.4 | 33.6 | 55.1 | 77.4 | 66.3 |

- **Overlap.** A third of EasyCom's reference speech is overlapped. Every clustering system here outputs one speaker per frame, so overlap frames carry about 65–69% DER. The platform path, which has several streams, halves that to 46%. Overlap-aware assignment (part C) is not implemented. The obvious next step is a second label from the second SRP peak or the second-best cluster on overlap frames, or a neural overlap/EEND stage.
- **Short turns.** The 1.5 s windows at 0.5 s hop give about 0.5–0.75 s effective resolution. Turns under 1 s are only 21% correct (vs 64% for turns over 3 s), and backchannels ("yeah") are where most cpWER attribution errors sit. This is the resolution trade-off NeMo's multi-scale decoder (MSDD) targets.
- **Similar voices.** For speaker pairs with ECAPA centroid cosine ≤ 0.3, 1.9% of single-talker frames go to the other speaker; for cosine 0.3–0.5 it is 3.5% (`test_confusion_pairs.csv`). EasyCom has no pair above 0.5. LibriCSS (8 speakers) will stress this more.
- **Speaker count.** NME-SC eigengap is off by +2 on session 10 (6 vs 4) and exact on session 11 (5). AHC over-counts (+2; 8 vs 5 on session 11). Giving the true K improves cpWER (59.4 → 56.7) but not DER, so the residual errors are boundaries and VAD, not the count.

## Runtime (1 thread, nice 19, the 2-vCPU box shared with the round-7 pipeline)
| stage | RTF |
|---|---|
| Silero VAD | 0.012 |
| ECAPA embeddings (1.5 s / 0.5 s) | 0.26 (EasyCom, about 1 free core); 0.58 (LibriCSS, while the r7 pipeline's 2 workers ran) |
| SRP-PHAT (EasyCom ATF, 4 mics / LibriCSS 7 mics) | 0.005 / 0.006 |
| faster-whisper base.en with word timestamps | 0.09 |
| clustering + scoring | < 0.02 |

End-to-end CLI on a 75 s clip: RTF 0.93 including model loading (`cli_smoke/lc_clip75.json`). Embedding extraction is the bottleneck; a hop of 0.75 s or batching on a free core would roughly halve it.

## Demo transcripts
- `demo_easycom.txt`: session 10, A_spectral, first 120 s, system output and human reference side by side. Text only; no EasyCom audio is exported.
- `demo_libricss.txt`: to be generated after the LibriCSS test, with `python -m selab.diar.demo lc_OV20_s3 A_spectral 120`.

## Possible upgrades (need J's OK)
- pyannote 3.1 segmentation + embedding models are gated on Hugging Face (account plus accepted terms). Not used.
- DiariZen's WavLM-Conformer weights are CC-BY-NC, research only. Not used.
