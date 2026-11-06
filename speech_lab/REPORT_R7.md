---
title: "Head-Orientation Steering on Real Glasses Recordings (EasyCom)"
subtitle: "Speech Intelligibility Benchmark Lab, Round 7 (6-ch glasses, restaurant, 6DOF head poses; held-out test sessions 10, 11)"
date: "2026-10-24"
---

# 1. Bottom line

1. **Question.** Does steering a causal ≤ 8 ms beamformer by the wearer's head orientation beat steering it by the round-6 acoustic tracker, on real recordings from glasses in a noisy restaurant?
2. **Yes, clearly.** On the held-out test (434 items with words, sessions 10-11), head-steered superdirective 8 ms gains **+0.066 [+0.029, +0.106]** word-correct over the unprocessed front mic (Holm p < 0.001). The tracked version **loses** (−0.064 [−0.090, −0.039]). Head-prior hybrid SD 8 ms: **+0.070 [+0.029, +0.116]**. Oracle reference direction (REF, SD 8 ms): **+0.173 [+0.147, +0.197]**.
3. **But it only ties round-5 delay-and-sum.** Head-steered SD 8 ms vs R5 DS (non-causal, 32 ms): +0.001 [−0.043, +0.050]; hybrid +0.005 [−0.042, +0.057]. So a causal 8 ms filter with a free head prior matches what a 32 ms blind-direction filter gives; it does not beat it. Time-domain DS (0.75-1 ms) with head steering gives nothing (+0.004).
4. **Overlap and wearer-addressed speech.** Overlapped items (n = 248): head SD 8 ms +0.034 [+0.005, +0.066], hybrid +0.038 [+0.005, +0.074], neither survives Holm (p = 0.08-0.11), and both are below R5 DS (−0.044, −0.040). Items addressed to the wearer (n = 85): head SD 8 ms +0.072 [+0.021, +0.136] (Holm p = 0.063), tracked −0.033. The oracle gains +0.164 on overlap and +0.135 to the wearer.
5. **Onsets.** Head azimuth is within 30° of the talker in **54% of 0-0.25 s frames after a turn starts** (71% when addressed to the wearer; 46% on overlapped turns), vs **35%** for the tracker (56% to the wearer). After 4 s the tracker catches up on 10°: 49% vs 27% for head. The ceiling is that the head is only a coarse (±30°) cue: within 10° only 21% at onset.
6. **Steering error drives the gain.** Items steered within 10° gain +0.156 (SD 8 head) over front; 45-90° error loses −0.069. Spearman(error, gain) ≈ −0.37.
7. **Caveat.** ASR is Whisper base.en as a proxy for intelligibility, not human listeners. EasyCom audio is CC-BY-NC and is not in any deliverable. References and DOA are built from poses and close mics, and 20 test items were flagged as poorly aligned (kept in the main table; the table without them is in section 4).

# 2. What ran

- **Data:** EasyCom (Main + Calibration, 6-ch glasses: ch1-4 frame mics, ch5-6 ear-canal mics), 16 kHz. Tune on val sessions 4/12 (sub-sample of 300 items), test once on sessions 10/11 (472 items; 434 with words).
- **Methods:** hs = head-steered (ATF-interpolated look direction from the 6DOF head pose); trk = round-6 causal SRP tracker adapted to ch1-4; hyb = head prior plus tracker when it is confident (window ±20°, threshold 8); ref = oracle direction from poses; each with DS time-domain, SD 4 ms, SD 8 ms. R5 DS and unprocessed mics as baselines.
- **Frozen on val before test:** front mic = ch2; WNG floor −6 dB; hybrid window ±20°, threshold 8 (results/r7/frozen_r7.json).
- **Scoring:** faster-whisper base.en, word-correct = hits / reference words; cluster bootstrap over turns' recordings, 95% CI; Holm within family. Objective SI-SDR and ESTOI also computed (summary_r7.md).

# 3. Methods and latencies

Algorithmic latency (excluding compute): time-domain DS 0.75 ms (head) to 1.07 ms (tracked/ref, crossfade); SD 4 ms = 4 ms; SD 8 ms = 8 ms; R5 DS = 32 ms. Measured compute per hop (idle-ish, load ≈ 0.8, one thread):

| component | per hop (ms) | p99 (ms) | hop (ms) | CPU fraction |
|---|---|---|---|---|
| head DS td | 0.015 | 0.016 | 2 | 0.007 |
| head SD 4 ms | 0.020 | 0.024 | 2 | 0.010 |
| head SD 8 ms | 0.022 | 0.028 | 4 | 0.006 |
| tracked SD 8 ms | 0.024 | 0.028 | 4 | 0.006 |
| tracker step (ATF) | 0.86 | 0.96 | 16 | 0.054 |
| hybrid logic | 0.012 | n/a | 16 | 0.001 |

Compute is a non-issue; head steering needs no tracker at all.

# 4. Test results (word-correct, Δ vs unprocessed front mic and vs R5 DS)

### Word-correct, All test items with words (align_suspect kept) (n = 434)

| method | word-correct | Δ vs unproc_front [95% CI] | Holm p | Δ vs R5 DS [95% CI] | Holm p |
|---|---|---|---|---|---|
| Unprocessed frame mic (frozen best of ch1-4) | 0.343 |  |  | -0.065 [-0.086, -0.043] |  |
| Ear-canal mics mean ch5/6 (reference only) | 0.267 | -0.076 [-0.110, -0.045] |  | -0.142 [-0.178, -0.108] |  |
| R5 DS, blind whole-utt. dir., 32 ms STFT (reference baseline) | 0.408 | +0.065 [+0.044, +0.085] |  |  |  |
| Head-steered DS, time-domain (ATF delays) | 0.347 | +0.004 [-0.031, +0.036] | 1.000 | -0.062 [-0.102, -0.021] | 0.010 |
| Head-steered superdirective 8 ms | 0.409 | +0.066 [+0.029, +0.106] | <0.001 | +0.001 [-0.043, +0.050] | 1.000 |
| Head-steered superdirective 4 ms | 0.404 | +0.061 [+0.024, +0.102] | 0.003 | -0.004 [-0.048, +0.042] | 1.000 |
| Tracked DS time-domain | 0.309 | -0.034 [-0.053, -0.015] | <0.001 | -0.099 [-0.122, -0.077] | <0.001 |
| Tracked SD 8 ms | 0.279 | -0.064 [-0.090, -0.039] | <0.001 | -0.129 [-0.160, -0.097] | <0.001 |
| Tracked SD 4 ms | 0.282 | -0.061 [-0.089, -0.036] | <0.001 | -0.126 [-0.160, -0.095] | <0.001 |
| Head-prior hybrid DS time-domain | 0.340 | -0.003 [-0.039, +0.033] | 1.000 | -0.069 [-0.110, -0.028] | 0.006 |
| Head-prior hybrid SD 8 ms | 0.413 | +0.070 [+0.029, +0.116] | <0.001 | +0.005 [-0.042, +0.057] | 1.000 |
| Head-prior hybrid SD 4 ms | 0.403 | +0.060 [+0.021, +0.098] | <0.001 | -0.005 [-0.050, +0.043] | 1.000 |
| REF-DOA SD 8 ms (oracle) | 0.515 | +0.173 [+0.147, +0.197] | <0.001 | +0.107 [+0.078, +0.136] | <0.001 |
| REF-DOA DS time-domain (oracle) | 0.457 | +0.114 [+0.094, +0.132] | <0.001 | +0.049 [+0.028, +0.072] | <0.001 |


### Word-correct, Without align_suspect items (n = 414)

| method | word-correct | Δ vs unproc_front [95% CI] | Holm p | Δ vs R5 DS [95% CI] | Holm p |
|---|---|---|---|---|---|
| Unprocessed frame mic (frozen best of ch1-4) | 0.352 |  |  | -0.068 [-0.088, -0.045] |  |
| Ear-canal mics mean ch5/6 (reference only) | 0.273 | -0.079 [-0.112, -0.046] |  | -0.147 [-0.183, -0.113] |  |
| R5 DS, blind whole-utt. dir., 32 ms STFT (reference baseline) | 0.419 | +0.068 [+0.045, +0.089] |  |  |  |
| Head-steered DS, time-domain (ATF delays) | 0.355 | +0.003 [-0.032, +0.037] | 1.000 | -0.064 [-0.106, -0.021] | 0.030 |
| Head-steered superdirective 8 ms | 0.420 | +0.068 [+0.026, +0.109] | 0.007 | +0.000 [-0.044, +0.048] | 1.000 |
| Head-steered superdirective 4 ms | 0.416 | +0.064 [+0.023, +0.108] | 0.008 | -0.003 [-0.051, +0.046] | 1.000 |
| Tracked DS time-domain | 0.318 | -0.034 [-0.053, -0.014] | 0.007 | -0.101 [-0.126, -0.077] | <0.001 |
| Tracked SD 8 ms | 0.287 | -0.065 [-0.091, -0.039] | <0.001 | -0.132 [-0.165, -0.099] | <0.001 |
| Tracked SD 4 ms | 0.291 | -0.061 [-0.088, -0.034] | <0.001 | -0.129 [-0.163, -0.096] | <0.001 |
| Head-prior hybrid DS time-domain | 0.349 | -0.003 [-0.039, +0.035] | 1.000 | -0.070 [-0.114, -0.024] | 0.030 |
| Head-prior hybrid SD 8 ms | 0.424 | +0.072 [+0.030, +0.118] | 0.007 | +0.004 [-0.044, +0.059] | 1.000 |
| Head-prior hybrid SD 4 ms | 0.415 | +0.063 [+0.023, +0.105] | 0.008 | -0.005 [-0.055, +0.047] | 1.000 |
| REF-DOA SD 8 ms (oracle) | 0.528 | +0.176 [+0.149, +0.202] | <0.001 | +0.108 [+0.079, +0.140] | <0.001 |
| REF-DOA DS time-domain (oracle) | 0.470 | +0.118 [+0.098, +0.137] | <0.001 | +0.050 [+0.029, +0.071] | <0.001 |


### Word-correct, Overlapped items (n = 248)

| method | word-correct | Δ vs unproc_front [95% CI] | Holm p | Δ vs R5 DS [95% CI] | Holm p |
|---|---|---|---|---|---|
| Unprocessed frame mic (frozen best of ch1-4) | 0.256 |  |  | -0.078 [-0.098, -0.056] |  |
| Ear-canal mics mean ch5/6 (reference only) | 0.217 | -0.040 [-0.071, -0.006] |  | -0.117 [-0.148, -0.085] |  |
| R5 DS, blind whole-utt. dir., 32 ms STFT (reference baseline) | 0.334 | +0.078 [+0.055, +0.098] |  |  |  |
| Head-steered DS, time-domain (ATF delays) | 0.250 | -0.007 [-0.036, +0.025] | 0.714 | -0.084 [-0.110, -0.054] | <0.001 |
| Head-steered superdirective 8 ms | 0.290 | +0.034 [+0.005, +0.066] | 0.084 | -0.044 [-0.077, -0.005] | 0.064 |
| Head-steered superdirective 4 ms | 0.288 | +0.032 [+0.006, +0.059] | 0.108 | -0.046 [-0.078, -0.012] | 0.064 |
| Tracked DS time-domain | 0.232 | -0.024 [-0.052, +0.005] | 0.354 | -0.102 [-0.125, -0.075] | <0.001 |
| Tracked SD 8 ms | 0.216 | -0.041 [-0.062, -0.018] | <0.001 | -0.119 [-0.143, -0.093] | <0.001 |
| Tracked SD 4 ms | 0.219 | -0.037 [-0.060, -0.012] | 0.024 | -0.115 [-0.136, -0.090] | <0.001 |
| Head-prior hybrid DS time-domain | 0.239 | -0.017 [-0.043, +0.013] | 0.460 | -0.095 [-0.121, -0.062] | <0.001 |
| Head-prior hybrid SD 8 ms | 0.294 | +0.038 [+0.005, +0.074] | 0.108 | -0.040 [-0.076, -0.001] | 0.064 |
| Head-prior hybrid SD 4 ms | 0.285 | +0.028 [+0.001, +0.057] | 0.136 | -0.049 [-0.084, -0.012] | 0.064 |
| REF-DOA SD 8 ms (oracle) | 0.421 | +0.164 [+0.130, +0.201] | <0.001 | +0.087 [+0.054, +0.124] | <0.001 |
| REF-DOA DS time-domain (oracle) | 0.369 | +0.113 [+0.083, +0.140] | <0.001 | +0.035 [+0.013, +0.056] | <0.001 |


### Word-correct, Non-overlapped items (n = 186)

| method | word-correct | Δ vs unproc_front [95% CI] | Holm p | Δ vs R5 DS [95% CI] | Holm p |
|---|---|---|---|---|---|
| Unprocessed frame mic (frozen best of ch1-4) | 0.458 |  |  | -0.049 [-0.086, -0.011] |  |
| Ear-canal mics mean ch5/6 (reference only) | 0.333 | -0.126 [-0.171, -0.083] |  | -0.174 [-0.230, -0.124] |  |
| R5 DS, blind whole-utt. dir., 32 ms STFT (reference baseline) | 0.507 | +0.049 [+0.009, +0.083] |  |  |  |
| Head-steered DS, time-domain (ATF delays) | 0.476 | +0.018 [-0.048, +0.072] | 1.000 | -0.031 [-0.112, +0.038] | 0.772 |
| Head-steered superdirective 8 ms | 0.569 | +0.110 [+0.042, +0.169] | 0.010 | +0.061 [-0.011, +0.130] | 0.714 |
| Head-steered superdirective 4 ms | 0.559 | +0.101 [+0.021, +0.165] | 0.016 | +0.052 [-0.024, +0.121] | 0.772 |
| Tracked DS time-domain | 0.411 | -0.047 [-0.075, -0.023] | <0.001 | -0.096 [-0.136, -0.061] | <0.001 |
| Tracked SD 8 ms | 0.364 | -0.094 [-0.134, -0.050] | <0.001 | -0.143 [-0.201, -0.078] | <0.001 |
| Tracked SD 4 ms | 0.366 | -0.092 [-0.132, -0.051] | <0.001 | -0.141 [-0.206, -0.080] | <0.001 |
| Head-prior hybrid DS time-domain | 0.473 | +0.015 [-0.050, +0.079] | 1.000 | -0.034 [-0.110, +0.041] | 0.772 |
| Head-prior hybrid SD 8 ms | 0.571 | +0.113 [+0.039, +0.177] | 0.006 | +0.064 [-0.016, +0.138] | 0.714 |
| Head-prior hybrid SD 4 ms | 0.560 | +0.102 [+0.031, +0.164] | 0.016 | +0.053 [-0.024, +0.125] | 0.772 |
| REF-DOA SD 8 ms (oracle) | 0.642 | +0.183 [+0.141, +0.221] | <0.001 | +0.134 [+0.093, +0.175] | <0.001 |
| REF-DOA DS time-domain (oracle) | 0.575 | +0.116 [+0.082, +0.144] | <0.001 | +0.067 [+0.031, +0.102] | <0.001 |


# 5. Breakdown by Target_of_Speech

### Word-correct, Addressed to the wearer (n = 85)

| method | word-correct | Δ vs unproc_front [95% CI] | Holm p | Δ vs R5 DS [95% CI] | Holm p |
|---|---|---|---|---|---|
| Unprocessed frame mic (frozen best of ch1-4) | 0.274 |  |  | -0.055 [-0.105, +0.001] |  |
| Ear-canal mics mean ch5/6 (reference only) | 0.256 | -0.018 [-0.092, +0.058] |  | -0.073 [-0.139, -0.008] |  |
| R5 DS, blind whole-utt. dir., 32 ms STFT (reference baseline) | 0.329 | +0.055 [+0.001, +0.108] |  |  |  |
| Head-steered DS, time-domain (ATF delays) | 0.313 | +0.039 [-0.004, +0.086] | 0.380 | -0.016 [-0.066, +0.032] | 1.000 |
| Head-steered superdirective 8 ms | 0.346 | +0.072 [+0.021, +0.136] | 0.063 | +0.017 [-0.037, +0.089] | 1.000 |
| Head-steered superdirective 4 ms | 0.328 | +0.054 [-0.003, +0.115] | 0.336 | -0.001 [-0.050, +0.055] | 1.000 |
| Tracked DS time-domain | 0.262 | -0.012 [-0.065, +0.033] | 0.828 | -0.067 [-0.117, -0.021] | 0.027 |
| Tracked SD 8 ms | 0.241 | -0.033 [-0.085, +0.015] | 0.592 | -0.088 [-0.135, -0.041] | 0.011 |
| Tracked SD 4 ms | 0.251 | -0.024 [-0.074, +0.017] | 0.828 | -0.078 [-0.123, -0.040] | 0.011 |
| Head-prior hybrid DS time-domain | 0.295 | +0.021 [-0.027, +0.069] | 0.828 | -0.033 [-0.081, +0.013] | 1.000 |
| Head-prior hybrid SD 8 ms | 0.332 | +0.058 [+0.010, +0.113] | 0.176 | +0.003 [-0.044, +0.060] | 1.000 |
| Head-prior hybrid SD 4 ms | 0.328 | +0.054 [+0.001, +0.113] | 0.329 | -0.001 [-0.050, +0.060] | 1.000 |
| REF-DOA SD 8 ms (oracle) | 0.409 | +0.135 [+0.082, +0.193] | <0.001 | +0.080 [+0.022, +0.143] | 0.056 |
| REF-DOA DS time-domain (oracle) | 0.383 | +0.108 [+0.060, +0.161] | <0.001 | +0.054 [+0.013, +0.106] | 0.077 |


### Word-correct, Addressed to the group (n = 125)

| method | word-correct | Δ vs unproc_front [95% CI] | Holm p | Δ vs R5 DS [95% CI] | Holm p |
|---|---|---|---|---|---|
| Unprocessed frame mic (frozen best of ch1-4) | 0.378 |  |  | -0.052 [-0.086, -0.013] |  |
| Ear-canal mics mean ch5/6 (reference only) | 0.291 | -0.088 [-0.134, -0.044] |  | -0.140 [-0.183, -0.096] |  |
| R5 DS, blind whole-utt. dir., 32 ms STFT (reference baseline) | 0.430 | +0.052 [+0.016, +0.085] |  |  |  |
| Head-steered DS, time-domain (ATF delays) | 0.348 | -0.030 [-0.064, +0.005] | 0.165 | -0.082 [-0.125, -0.038] | <0.001 |
| Head-steered superdirective 8 ms | 0.426 | +0.047 [+0.009, +0.089] | 0.070 | -0.005 [-0.053, +0.044] | 1.000 |
| Head-steered superdirective 4 ms | 0.416 | +0.037 [-0.000, +0.075] | 0.165 | -0.015 [-0.061, +0.037] | 1.000 |
| Tracked DS time-domain | 0.327 | -0.051 [-0.080, -0.019] | <0.001 | -0.104 [-0.133, -0.073] | <0.001 |
| Tracked SD 8 ms | 0.325 | -0.054 [-0.088, -0.013] | 0.070 | -0.106 [-0.147, -0.063] | <0.001 |
| Tracked SD 4 ms | 0.316 | -0.063 [-0.099, -0.027] | 0.016 | -0.115 [-0.153, -0.075] | <0.001 |
| Head-prior hybrid DS time-domain | 0.351 | -0.027 [-0.064, +0.012] | 0.172 | -0.079 [-0.123, -0.031] | 0.006 |
| Head-prior hybrid SD 8 ms | 0.423 | +0.045 [+0.000, +0.093] | 0.165 | -0.007 [-0.057, +0.050] | 1.000 |
| Head-prior hybrid SD 4 ms | 0.424 | +0.046 [+0.001, +0.095] | 0.165 | -0.006 [-0.063, +0.051] | 1.000 |
| REF-DOA SD 8 ms (oracle) | 0.520 | +0.142 [+0.096, +0.192] | <0.001 | +0.089 [+0.047, +0.137] | <0.001 |
| REF-DOA DS time-domain (oracle) | 0.451 | +0.073 [+0.037, +0.106] | 0.009 | +0.020 [-0.014, +0.056] | 1.000 |


### Word-correct, Target: other (n = 123)

| method | word-correct | Δ vs unproc_front [95% CI] | Holm p | Δ vs R5 DS [95% CI] | Holm p |
|---|---|---|---|---|---|
| Unprocessed frame mic (frozen best of ch1-4) | 0.265 |  |  | -0.085 [-0.125, -0.048] |  |
| Ear-canal mics mean ch5/6 (reference only) | 0.193 | -0.072 [-0.123, -0.024] |  | -0.157 [-0.213, -0.106] |  |
| R5 DS, blind whole-utt. dir., 32 ms STFT (reference baseline) | 0.350 | +0.085 [+0.046, +0.123] |  |  |  |
| Head-steered DS, time-domain (ATF delays) | 0.245 | -0.020 [-0.059, +0.016] | 1.000 | -0.104 [-0.152, -0.056] | <0.001 |
| Head-steered superdirective 8 ms | 0.259 | -0.006 [-0.050, +0.043] | 1.000 | -0.091 [-0.148, -0.025] | 0.024 |
| Head-steered superdirective 4 ms | 0.270 | +0.005 [-0.041, +0.055] | 1.000 | -0.079 [-0.134, -0.021] | 0.024 |
| Tracked DS time-domain | 0.229 | -0.037 [-0.071, +0.001] | 0.366 | -0.121 [-0.159, -0.075] | <0.001 |
| Tracked SD 8 ms | 0.218 | -0.047 [-0.092, -0.005] | 0.264 | -0.132 [-0.175, -0.088] | <0.001 |
| Tracked SD 4 ms | 0.220 | -0.045 [-0.094, +0.000] | 0.350 | -0.130 [-0.177, -0.085] | <0.001 |
| Head-prior hybrid DS time-domain | 0.227 | -0.039 [-0.076, -0.002] | 0.207 | -0.123 [-0.174, -0.073] | <0.001 |
| Head-prior hybrid SD 8 ms | 0.271 | +0.005 [-0.051, +0.064] | 1.000 | -0.079 [-0.136, -0.013] | 0.024 |
| Head-prior hybrid SD 4 ms | 0.256 | -0.009 [-0.062, +0.045] | 1.000 | -0.094 [-0.149, -0.027] | 0.024 |
| REF-DOA SD 8 ms (oracle) | 0.458 | +0.193 [+0.146, +0.245] | <0.001 | +0.108 [+0.063, +0.161] | <0.001 |
| REF-DOA DS time-domain (oracle) | 0.404 | +0.139 [+0.100, +0.180] | <0.001 | +0.054 [+0.023, +0.087] | <0.001 |


### Word-correct, Target: none (n = 101)

| method | word-correct | Δ vs unproc_front [95% CI] | Holm p | Δ vs R5 DS [95% CI] | Holm p |
|---|---|---|---|---|---|
| Unprocessed frame mic (frozen best of ch1-4) | 0.452 |  |  | -0.067 [-0.114, -0.024] |  |
| Ear-canal mics mean ch5/6 (reference only) | 0.335 | -0.117 [-0.193, -0.047] |  | -0.184 [-0.280, -0.112] |  |
| R5 DS, blind whole-utt. dir., 32 ms STFT (reference baseline) | 0.519 | +0.067 [+0.024, +0.115] |  |  |  |
| Head-steered DS, time-domain (ATF delays) | 0.497 | +0.045 [-0.076, +0.127] | 0.846 | -0.022 [-0.168, +0.088] | 1.000 |
| Head-steered superdirective 8 ms | 0.625 | +0.174 [+0.079, +0.251] | 0.010 | +0.107 [-0.009, +0.210] | 0.365 |
| Head-steered superdirective 4 ms | 0.618 | +0.166 [+0.065, +0.250] | 0.016 | +0.099 [-0.022, +0.204] | 0.365 |
| Tracked DS time-domain | 0.424 | -0.028 [-0.061, +0.010] | 0.372 | -0.095 [-0.156, -0.047] | <0.001 |
| Tracked SD 8 ms | 0.329 | -0.122 [-0.182, -0.065] | <0.001 | -0.189 [-0.284, -0.094] | <0.001 |
| Tracked SD 4 ms | 0.343 | -0.108 [-0.174, -0.054] | <0.001 | -0.176 [-0.289, -0.087] | <0.001 |
| Head-prior hybrid DS time-domain | 0.500 | +0.049 [-0.077, +0.152] | 0.846 | -0.019 [-0.168, +0.106] | 1.000 |
| Head-prior hybrid SD 8 ms | 0.642 | +0.190 [+0.075, +0.272] | 0.007 | +0.123 [-0.004, +0.229] | 0.276 |
| Head-prior hybrid SD 4 ms | 0.618 | +0.167 [+0.068, +0.246] | 0.007 | +0.100 [-0.016, +0.198] | 0.365 |
| REF-DOA SD 8 ms (oracle) | 0.669 | +0.217 [+0.168, +0.264] | <0.001 | +0.150 [+0.084, +0.217] | <0.001 |
| REF-DOA DS time-domain (oracle) | 0.592 | +0.141 [+0.112, +0.166] | <0.001 | +0.073 [+0.024, +0.116] | 0.014 |


# 6. Time since turn onset

### Word-correct, < 0.5 s since turn onset (n = 371)

| method | word-correct | Δ vs unproc_front [95% CI] | Holm p | Δ vs R5 DS [95% CI] | Holm p |
|---|---|---|---|---|---|
| Unprocessed frame mic (frozen best of ch1-4) | 0.320 |  |  | -0.073 [-0.095, -0.049] |  |
| Ear-canal mics mean ch5/6 (reference only) | 0.258 | -0.062 [-0.092, -0.031] |  | -0.135 [-0.172, -0.103] |  |
| R5 DS, blind whole-utt. dir., 32 ms STFT (reference baseline) | 0.394 | +0.073 [+0.050, +0.094] |  |  |  |
| Head-steered DS, time-domain (ATF delays) | 0.318 | -0.002 [-0.031, +0.024] | 0.904 | -0.075 [-0.105, -0.042] | <0.001 |
| Head-steered superdirective 8 ms | 0.380 | +0.059 [+0.025, +0.095] | <0.001 | -0.014 [-0.051, +0.026] | 1.000 |
| Head-steered superdirective 4 ms | 0.372 | +0.051 [+0.018, +0.086] | 0.006 | -0.022 [-0.058, +0.018] | 1.000 |
| Tracked DS time-domain | 0.289 | -0.031 [-0.054, -0.009] | 0.024 | -0.105 [-0.128, -0.080] | <0.001 |
| Tracked SD 8 ms | 0.267 | -0.053 [-0.078, -0.027] | <0.001 | -0.126 [-0.153, -0.097] | <0.001 |
| Tracked SD 4 ms | 0.263 | -0.057 [-0.086, -0.030] | <0.001 | -0.130 [-0.161, -0.100] | <0.001 |
| Head-prior hybrid DS time-domain | 0.309 | -0.012 [-0.036, +0.015] | 0.746 | -0.085 [-0.114, -0.052] | <0.001 |
| Head-prior hybrid SD 8 ms | 0.381 | +0.061 [+0.024, +0.100] | 0.006 | -0.012 [-0.052, +0.031] | 1.000 |
| Head-prior hybrid SD 4 ms | 0.371 | +0.051 [+0.016, +0.088] | 0.006 | -0.023 [-0.062, +0.019] | 1.000 |
| REF-DOA SD 8 ms (oracle) | 0.497 | +0.177 [+0.147, +0.206] | <0.001 | +0.104 [+0.073, +0.134] | <0.001 |
| REF-DOA DS time-domain (oracle) | 0.431 | +0.111 [+0.089, +0.131] | <0.001 | +0.038 [+0.014, +0.061] | 0.005 |


### Word-correct, 0.5-2 s since turn onset (n = 11)

| method | word-correct | Δ vs unproc_front [95% CI] | Holm p | Δ vs R5 DS [95% CI] | Holm p |
|---|---|---|---|---|---|
| Unprocessed frame mic (frozen best of ch1-4) | 0.299 |  |  | -0.133 [-0.347, +0.041] |  |
| Ear-canal mics mean ch5/6 (reference only) | 0.330 | +0.030 [-0.103, +0.199] |  | -0.102 [-0.219, +0.017] |  |
| R5 DS, blind whole-utt. dir., 32 ms STFT (reference baseline) | 0.432 | +0.133 [-0.053, +0.346] |  |  |  |
| Head-steered DS, time-domain (ATF delays) | 0.481 | +0.182 [-0.002, +0.399] | 0.470 | +0.049 [-0.020, +0.136] | 1.000 |
| Head-steered superdirective 8 ms | 0.443 | +0.144 [-0.042, +0.367] | 0.900 | +0.011 [-0.101, +0.123] | 1.000 |
| Head-steered superdirective 4 ms | 0.469 | +0.170 [-0.019, +0.380] | 0.846 | +0.037 [-0.060, +0.141] | 1.000 |
| Tracked DS time-domain | 0.301 | +0.002 [-0.034, +0.039] | 0.910 | -0.131 [-0.340, +0.048] | 1.000 |
| Tracked SD 8 ms | 0.214 | -0.085 [-0.196, +0.019] | 0.846 | -0.218 [-0.401, -0.082] | <0.001 |
| Tracked SD 4 ms | 0.226 | -0.074 [-0.195, +0.031] | 0.900 | -0.207 [-0.401, -0.077] | <0.001 |
| Head-prior hybrid DS time-domain | 0.407 | +0.107 [-0.062, +0.322] | 0.900 | -0.026 [-0.117, +0.080] | 1.000 |
| Head-prior hybrid SD 8 ms | 0.435 | +0.135 [-0.045, +0.359] | 0.900 | +0.002 [-0.107, +0.113] | 1.000 |
| Head-prior hybrid SD 4 ms | 0.435 | +0.135 [-0.056, +0.359] | 0.900 | +0.002 [-0.105, +0.103] | 1.000 |
| REF-DOA SD 8 ms (oracle) | 0.470 | +0.171 [-0.035, +0.394] | 0.846 | +0.038 [-0.053, +0.129] | 1.000 |
| REF-DOA DS time-domain (oracle) | 0.528 | +0.229 [+0.085, +0.418] | <0.001 | +0.096 [+0.001, +0.199] | 0.513 |


### Word-correct, > 2 s since turn onset (n = 52)

| method | word-correct | Δ vs unproc_front [95% CI] | Holm p | Δ vs R5 DS [95% CI] | Holm p |
|---|---|---|---|---|---|
| Unprocessed frame mic (frozen best of ch1-4) | 0.513 |  |  | +0.005 [-0.063, +0.057] |  |
| Ear-canal mics mean ch5/6 (reference only) | 0.312 | -0.202 [-0.288, -0.105] |  | -0.197 [-0.332, -0.065] |  |
| R5 DS, blind whole-utt. dir., 32 ms STFT (reference baseline) | 0.509 | -0.005 [-0.059, +0.069] |  |  |  |
| Head-steered DS, time-domain (ATF delays) | 0.521 | +0.008 [-0.132, +0.113] | 1.000 | +0.013 [-0.195, +0.160] | 1.000 |
| Head-steered superdirective 8 ms | 0.616 | +0.102 [-0.005, +0.190] | 0.415 | +0.107 [-0.047, +0.231] | 1.000 |
| Head-steered superdirective 4 ms | 0.624 | +0.110 [-0.002, +0.189] | 0.308 | +0.115 [-0.043, +0.228] | 1.000 |
| Tracked DS time-domain | 0.453 | -0.060 [-0.129, +0.024] | 0.525 | -0.055 [-0.133, +0.040] | 1.000 |
| Tracked SD 8 ms | 0.378 | -0.136 [-0.215, -0.065] | <0.001 | -0.131 [-0.284, -0.026] | 0.010 |
| Tracked SD 4 ms | 0.431 | -0.083 [-0.157, -0.004] | 0.240 | -0.078 [-0.214, +0.021] | 1.000 |
| Head-prior hybrid DS time-domain | 0.548 | +0.035 [-0.083, +0.133] | 1.000 | +0.040 [-0.156, +0.193] | 1.000 |
| Head-prior hybrid SD 8 ms | 0.635 | +0.121 [+0.003, +0.205] | 0.308 | +0.126 [-0.025, +0.246] | 0.968 |
| Head-prior hybrid SD 4 ms | 0.625 | +0.111 [-0.012, +0.195] | 0.415 | +0.116 [-0.044, +0.236] | 1.000 |
| REF-DOA SD 8 ms (oracle) | 0.656 | +0.143 [+0.091, +0.173] | <0.001 | +0.148 [+0.074, +0.209] | <0.001 |
| REF-DOA DS time-domain (oracle) | 0.627 | +0.114 [+0.039, +0.169] | 0.063 | +0.119 [+0.029, +0.198] | 0.117 |


Few items fall after 0.5 s (n = 63), so the later bins are wide and mostly uninformative; most test items are short turn starts.

# 7. Head vs tracker steering accuracy

Share of 50 ms frames with the steering direction within X° of the true talker, by time since the target's turn started (all test and val turns, n = 1565 turns; results/r7/onset_r7.csv, head_onset.csv):

| steering | 0-0.25 s, ≤30° | 0-0.25 s, ≤10° | > 4 s, ≤30° | > 4 s, ≤10° |
|---|---|---|---|---|
| head azimuth, all | 54% | 21% | 75% | 27% |
| head azimuth, to wearer | 71% | 32% | 89% | 31% |
| head azimuth, overlapped | 46% | 15% | 69% | 22% |
| tracker (ATF), all | 35% | 14% | 71% | 49% |
| tracker (ATF), to wearer | 56% | 21% | 78% | 50% |
| best of head or tracker (oracle pick) | 59% | 28% | 84% | 57% |

Head beats tracker for the first seconds and especially at onsets; the tracker is more precise once it has locked on. The "best of" row shows a complementary signal, but my hybrid rule (head prior plus a confidence-gated tracker) realised +0.004 over head alone, not the gap implied.

Figure: results/r7/figs/head_onset.png.

# 8. Steering error vs gain

Per item, median steering error vs word-correct gain over front mic (head SD 8 ms): 0-10° → +0.156 (n = 152); 10-20° → +0.119 (82); 20-45° → +0.010 (108); 45-90° → −0.069 (81). Hybrid SD 8 ms: +0.159 (0-10°, n = 165), +0.100, +0.015, −0.082. Spearman ρ = −0.37. Median head-angle off the talker is 4° for the best bin and 61° for the worst, so a head-centred beam helps only when the wearer is facing the talker, which happens in about 35% of items.

# 9. Critique and limitations

- **Proxy metric.** Whisper base.en word-correct, not human listeners. Truncation of long items by the ASR is not fixed.
- **Reference built from poses.** Talker position = head-pose centre (no mouth offset); alignment of 20 test items was suspect (results with and without them agree).
- **Only a modest tie with R5 DS.** The 8 ms head-steered beam does not beat the non-causal blind direction. The oracle shows +0.107 over R5 DS is available, so direction remains the bottleneck.
- **Small test set.** Two sessions, so the cluster bootstrap CIs are wide. Subgroup gains (overlap, wearer) do not survive Holm correction.
- **Hybrid adds nothing.** The tracker's confidence rarely crosses the threshold in the short items; it may help in longer turns.
- **Geometry.** 4 mics, 12 cm aperture, nearly horizontal; low-frequency gain is small (WNG floor −6 dB).
- **Not tested:** human listening, moving talkers beyond the recorded sessions, closed-loop open-ear leakage.

# 10. Next steps

1. Learn a talker-selection prior from head pose plus voice activity (who is speaking to the wearer) rather than a fixed look direction.
2. Try gaze-like cues (head velocity, turn-taking) in the hybrid to recover the head/tracker complementarity.
3. A human listening test (12+ people) with level-matched head-steered vs front vs R5 DS.
4. Re-bench the real-time demo (idle load) and swap its mode (b) to head-steered SD 8 ms.

# 11. Files

results/r7/summary_r7.md (all tables), results/r7/{head_onset,onset_r7,steer_test,asr_wer_test,timing_r7_summary}.csv, results/r7/frozen_r7.json, results/r7/figs/head_onset.png, selab/{run_r7,analyze_r7,timing_r7,summary_r7,bf_r7}.py. No EasyCom audio is included.
