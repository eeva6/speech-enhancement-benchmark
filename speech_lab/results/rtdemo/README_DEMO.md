# Conversation Bubble: real-time voice-boost listening demo

**What it is.** A causal streaming engine (`selab/rtdemo/engine.py`) processes multi-mic recordings in 2 ms blocks (32 samples at 16 kHz). Each block uses only that block and past state. The engine reuses the lab's round-6 and round-7 filters and tracker; nothing was rebuilt. A WebAudio page lets you switch modes instantly while audio plays.

**Open it.** `scripts/run_rtdemo_app.sh` starts the lab app, then go to **http://127.0.0.1:7860/rtdemo/**. The page is also embedded in the app's tab "Real-time demo (Conversation Bubble)". To run it without Gradio: `python -m selab.rtdemo.server --port 7861`. Everything is local only; no share link is used.

## What is live and what is pre-rendered (be precise about this)
- **The page plays pre-rendered tracks.** The tracks were produced by the same streaming engine, fed block by block. Every mode's audio plays in sync and the toggle only moves gains, which is why switching is seamless. Two checks back this up:
  - **Bit-identical, 32 of 32 modes × scenes.** Each mode was re-run alone in a fresh engine with lazily designed weights and compared to the all-modes render: `results/rtdemo/verify_single_mode.json`.
  - **Bit-identical to a real-time-paced live run.** See `results/rtdemo/live/*.json`.
- **The genuinely live path is `python -m selab.rtdemo.live`.** It paces 2 ms blocks against a wall clock, computes every mode, switches on a schedule or on keys typed into stdin, logs deadline misses, and checks its output against the pre-render. `--device` streams to a sound card through sounddevice. That path is **untested** because this sandbox has no PortAudio. In every case the input is a recorded file standing in for the mic array.

## Modes
| mode | what it does | algorithmic latency |
|---|---|---|
| Unprocessed front mic | ch2 (EasyCom, R7 frozen), centre mic (LibriCSS), mic 2 (sim) | 0 ms + 2 ms block |
| Unprocessed in-ear (EasyCom only) | average of the ch5 and ch6 in-ear mics | 0 ms + 2 ms block |
| Head-steered DS | time-domain delay-and-sum, ATF steering to 0° (EasyCom) | 0.75 / 0.62 / 0.67 ms + 2 ms block |
| **Head-steered superdirective 4 ms** (best causal) | MVDR with diffuse coherence and a WNG floor. EasyCom: ATF steering, ref ch2, WNG −6 dB (R7 frozen) | **4 ms** (includes its 2 ms hop) |
| Tracker-steered sd 4 ms | round-6 rtn tracker (ATF on EasyCom), 16 ms steering updates | 4 ms; steering adds no audio delay |
| Head-prior hybrid sd 4 ms | R7 hybrid with X = 20°, thr = 8 (frozen), falling back to head direction | 4 ms |
| **SIMULATED noise-cut** | fixed minimum-phase FIRs built from the lab's *simulated* ANC spectra (see below) | n/a (simulated) |
| Neural post-filter | **skipped.** The lab's options measured 20 ms (RNNoise), 40 ms (DeepFilterNet3) and 41 ms (Demucs), all over the 8 ms cap. No causal model at or under 8 ms exists in the lab | none |

- **Why sd4 and not sd8.** R7 froze its parameters on sd8, but 8 ms equals the hard cap and misses the 5 ms target.
- **Interim R7 test evidence** (raw means over 434 items, not the official analysis): front .343, hs_sd4 .404, hs_sd8 .409, hyb_sd4 .403, hyb_sd8 .413, and **trk_sd4 .282, which is worse than unprocessed**.
- **The tracker mode often follows the wrong talker or the noise.** Listen for that; it is the known turn-onset weakness.
- **Output limiter.** Every mode has an engine-side causal block peak limiter at −1 dBFS that adds no latency; it never engaged on these scenes. The page adds a WebAudio limiter (−6 dB, ratio 20) and an optional level match, which equalises gated RMS to the raw track. The SIMULATED track keeps its level drop.

**SIMULATED noise-cut.** It applies two simulated spectra, neither measured on a head:
- **Traffic:** the per-1/3-octave reduction of the best glasses ANC configuration, about 7.8 dB(A) on the simulated pass-by.
- **Restaurant:** plain ANC cut companions by −5.2 dB(A) and babble by −3.7 dB(A).

How it is applied in each scene type:
- **Simulated scenes.** Talkers get the companion curve; noise gets the traffic or babble curve.
  - Street: talker −6.9 dB(A), traffic −7.6 dB(A).
  - Restaurant: talkers −5.3 dB(A), babble and the other talker −3.9 dB(A). **The SNR gets worse by 1.6 dB, because ANC cuts the companions too.**
- **Real recordings.** The sources cannot be separated, so the whole scene is cut with the companion curve, and the simulated SNR loss is not reproduced.

## Scenes and clips (16 s each)
- **sim_street and sim_restaurant: OK for outside listeners.** LibriSpeech (CC BY 4.0), synthetic car noise and pyroomacoustics; 4-mic 4 cm linear array.
- **libricss_ov40: OK for outside listeners** (attribution required). Real 7-mic table array, CC BY 4.0. Its "head" direction is an **oracle** look direction (the target loudspeaker's system-ID azimuth).
- **easycom_s10 and easycom_s11: INTERNAL ONLY.** Real glasses audio, EasyCom CC BY-NC research licence. Never play these to outside people or put them in a zip. Note that **EasyCom is 6 channels (4 frame mics plus 2 in-ear mics), not 7.** Only LibriCSS has 7 mics.
- **Clips:**
  - Folders: `listening/rtdemo/clips/{external_ok,INTERNAL_ONLY_easycom}/<scene>/`.
  - Each scene folder has the raw pair, a loudness-matched `_LM` pair at −23 dB gated RMS, extra steering modes, and the SIMULATED track.
  - Clip list: `results/rtdemo/clip_list.{csv,md}`.
  - `listening/rtdemo/clips_external_ok.zip` holds the licence-clean clips only.

## Measured numbers (`results/rtdemo/latency_compute.md`)
All measured on this 2 vCPU aarch64 sandbox, single-threaded Python, while the R7 pipeline and a diarization job were loading it (load average 4.4-5.0).

- **Compute per 2 ms block, median:**
  - 0.004 ms raw, 0.018-0.026 ms DS, 0.023-0.029 ms sd4.
  - All modes at once: 0.11-0.12 ms (p95 0.16-0.28).
- **Tracker step (every 16 ms):** median 0.92-1.52 ms, p95 about 5 ms.
- **Total live engine RTF:** 0.18-0.25.
- **Maxima of 2-10 ms** come from scheduler pre-emption.
- **Live paced loop at load 4.6-5.0:** 14% of blocks (EasyCom) and 30% (LibriCSS) missed their 2 ms deadline, so **this loaded sandbox does not hold real time reliably.** Compute itself fits: median 0.22 ms per block.
- **Two deadline risks remain:**
  - The tracker on the 7-mic array sits close to one 2 ms block. A device would run it on its own thread with a fixed one-hop steering delay.
  - Python block I/O.

**Sim SNR sanity check** (`results/rtdemo/sim_snr.json`). The SNR changes are exact, from target and noise processed separately. Head-steered sd4 gave **+0.4 dB (street) and +0.8 dB (restaurant)**. The tracker gave −0.9 / −1.9 dB. A 12 cm 4-mic aperture does very little below about 1.5 kHz. **Expect a subtle difference, not a bubble.**

## What this does NOT show
- **No at-ear acoustics.** No head or pinna rendering of the output, and no open-ear leakage: the direct sound through an open-ear device is not mixed in, which would dilute any benefit.
- **No acoustic feedback.**
- **No real ANC.** The noise-cut track is a filter built from simulated spectra.
- **No human intelligibility test.** The Whisper word-correct numbers quoted from R7 are only a proxy.
- **No proof of real-time on a device.** It shows compute headroom in Python on this machine, nothing more.
- **Not a full system.** It assumes the listener faces the talker. On LibriCSS that is an oracle, and the tracker modes show what happens without that assumption.
