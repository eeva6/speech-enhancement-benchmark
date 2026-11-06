# Round 7 phase 2 summary: ATF beamformers + ASR on EasyCom (test sessions 10, 11)

EasyCom is CC-BY-NC 4.0 (research only); no audio in any deliverable.

## Frozen parameters (tuned on val sub300, frozen before test)

- front mic: ch2; reference mic: ch2; WNG floor: -6 dB; hybrid window ±20°, confidence threshold 8 (decayed dominant-frame count)
- frozen at 2026-10-24 05:02:03 UTC; rule: argmax mean word-correct on the val tuning set; sequential: front mic and ref mic (WNG 0 dB), then WNG floor, then hybrid X/thr
- val word-correct: front {'front1': 0.3798, 'front2': 0.4124, 'front3': 0.39, 'front4': 0.3713}; ref mic {'hs_sd8__r0w0': 0.4196, 'hs_sd8__r1w0': 0.4209, 'hs_sd8__r2w0': 0.4026, 'hs_sd8__r3w0': 0.4065}; WNG {'hs_sd8__r1w-3': 0.4206, 'hs_sd8__r1w-6': 0.4362, 'hs_sd8__r1w0': 0.4209, 'hs_sd8__r1w3': 0.4148, 'hs_sd8__r1w6': 0.4127}; hybrid {'hyb_sd8__X20t1': 0.4221, 'hyb_sd8__X20t3': 0.4263, 'hyb_sd8__X20t8': 0.4394, 'hyb_sd8__X30t1': 0.4105, 'hyb_sd8__X30t3': 0.4174, 'hyb_sd8__X30t8': 0.4364, 'hyb_sd8__X45t1': 0.4135, 'hyb_sd8__X45t3': 0.4211, 'hyb_sd8__X45t8': 0.4366}

## Word-correct, All test items with words (align_suspect kept) (n = 434)

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

## Word-correct, Without align_suspect items (n = 414)

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

## Word-correct, Overlapped items (n = 248)

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

## Word-correct, Non-overlapped items (n = 186)

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

## Word-correct, Addressed to the wearer (n = 85)

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

## Word-correct, Addressed to the group (n = 125)

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

## Word-correct, Target: other (n = 123)

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

## Word-correct, Target: none (n = 101)

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

## Word-correct, < 0.5 s since turn onset (n = 371)

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

## Word-correct, 0.5-2 s since turn onset (n = 11)

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

## Word-correct, > 2 s since turn onset (n = 52)

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

## SI_SDR (align_suspect excluded, n = 445)

| method | mean | Δ vs unproc_front [95% CI] | Δ vs R5 DS |
|---|---|---|---|
| Unprocessed frame mic (frozen best of ch1-4) | -11.42 |  | -0.92 [-1.21, -0.62] |
| Ear-canal mics mean ch5/6 (reference only) | -11.21 | +0.21 [-0.15, +0.56] | -0.70 [-1.15, -0.29] |
| R5 DS, blind whole-utt. dir., 32 ms STFT (reference baseline) | -10.50 | +0.92 [+0.61, +1.21] |  |
| Head-steered DS, time-domain (ATF delays) | -10.89 | +0.53 [+0.22, +0.85] | -0.39 [-0.79, +0.01] |
| Head-steered superdirective 8 ms | -10.59 | +0.83 [+0.25, +1.47] | -0.09 [-0.81, +0.68] |
| Head-steered superdirective 4 ms | -10.48 | +0.94 [+0.33, +1.55] | +0.02 [-0.69, +0.74] |
| Tracked DS time-domain | -11.23 | +0.19 [-0.07, +0.44] | -0.73 [-1.04, -0.43] |
| Tracked SD 8 ms | -12.64 | -1.22 [-1.69, -0.72] | -2.13 [-2.64, -1.63] |
| Tracked SD 4 ms | -12.51 | -1.09 [-1.57, -0.62] | -2.01 [-2.52, -1.47] |
| Head-prior hybrid DS time-domain | -10.86 | +0.56 [+0.26, +0.85] | -0.36 [-0.77, +0.03] |
| Head-prior hybrid SD 8 ms | -10.58 | +0.84 [+0.19, +1.48] | -0.08 [-0.82, +0.69] |
| Head-prior hybrid SD 4 ms | -10.48 | +0.94 [+0.35, +1.57] | +0.02 [-0.72, +0.74] |
| REF-DOA SD 8 ms (oracle) | -7.53 | +3.89 [+3.56, +4.19] | +2.97 [+2.60, +3.32] |
| REF-DOA DS time-domain (oracle) | -9.52 | +1.90 [+1.64, +2.14] | +0.98 [+0.68, +1.30] |

## ESTOI (align_suspect excluded, n = 445)

| method | mean | Δ vs unproc_front [95% CI] | Δ vs R5 DS |
|---|---|---|---|
| Unprocessed frame mic (frozen best of ch1-4) | 0.306 |  | -0.019 [-0.025, -0.014] |
| Ear-canal mics mean ch5/6 (reference only) | 0.285 | -0.021 [-0.025, -0.016] | -0.039 [-0.046, -0.033] |
| R5 DS, blind whole-utt. dir., 32 ms STFT (reference baseline) | 0.325 | +0.019 [+0.014, +0.024] |  |
| Head-steered DS, time-domain (ATF delays) | 0.308 | +0.002 [-0.005, +0.010] | -0.017 [-0.025, -0.008] |
| Head-steered superdirective 8 ms | 0.344 | +0.038 [+0.026, +0.051] | +0.019 [+0.007, +0.034] |
| Head-steered superdirective 4 ms | 0.336 | +0.030 [+0.019, +0.042] | +0.011 [-0.002, +0.024] |
| Tracked DS time-domain | 0.302 | -0.004 [-0.007, +0.000] | -0.023 [-0.027, -0.019] |
| Tracked SD 8 ms | 0.307 | +0.001 [-0.007, +0.008] | -0.018 [-0.025, -0.012] |
| Tracked SD 4 ms | 0.303 | -0.003 [-0.010, +0.004] | -0.022 [-0.028, -0.016] |
| Head-prior hybrid DS time-domain | 0.309 | +0.003 [-0.003, +0.010] | -0.016 [-0.024, -0.007] |
| Head-prior hybrid SD 8 ms | 0.346 | +0.040 [+0.028, +0.052] | +0.021 [+0.008, +0.035] |
| Head-prior hybrid SD 4 ms | 0.337 | +0.031 [+0.021, +0.042] | +0.012 [-0.000, +0.026] |
| REF-DOA SD 8 ms (oracle) | 0.405 | +0.099 [+0.094, +0.104] | +0.080 [+0.074, +0.085] |
| REF-DOA DS time-domain (oracle) | 0.344 | +0.038 [+0.036, +0.041] | +0.019 [+0.014, +0.024] |

## Steering error (median per item, deg) vs word-correct gain

| method    | err_bin                      |   n |   gain_vs_front |   gain_vs_hs |   head_angle_med |
|:----------|:-----------------------------|----:|----------------:|-------------:|-----------------:|
| hs_ds_td  | 0-10                         | 152 |           0.105 |        0     |            4.327 |
| hs_ds_td  | 10-20                        |  82 |           0.011 |        0     |           15.322 |
| hs_ds_td  | 20-45                        | 108 |          -0.072 |        0     |           28.25  |
| hs_ds_td  | 45-90                        |  81 |          -0.104 |        0     |           61.385 |
| hs_ds_td  | 90-181                       |  11 |           0.096 |        0     |          111.628 |
| hs_ds_td  | spearman(err, gain_vs_front) | 434 |          -0.367 |      nan     |          nan     |
| hs_sd8    | 0-10                         | 152 |           0.156 |        0     |            4.327 |
| hs_sd8    | 10-20                        |  82 |           0.119 |        0     |           15.322 |
| hs_sd8    | 20-45                        | 108 |           0.01  |        0     |           28.25  |
| hs_sd8    | 45-90                        |  81 |          -0.069 |        0     |           61.385 |
| hs_sd8    | 90-181                       |  11 |           0.003 |        0     |          111.628 |
| hs_sd8    | spearman(err, gain_vs_front) | 434 |          -0.374 |      nan     |          nan     |
| hs_sd4    | 0-10                         | 152 |           0.153 |        0     |            4.327 |
| hs_sd4    | 10-20                        |  82 |           0.103 |        0     |           15.322 |
| hs_sd4    | 20-45                        | 108 |           0.003 |        0     |           28.25  |
| hs_sd4    | 45-90                        |  81 |          -0.072 |        0     |           61.385 |
| hs_sd4    | 90-181                       |  11 |           0.048 |        0     |          111.628 |
| hs_sd4    | spearman(err, gain_vs_front) | 434 |          -0.369 |      nan     |          nan     |
| trk_ds_td | 0-10                         | 118 |           0.055 |        0.009 |            9.045 |
| trk_ds_td | 10-20                        |  70 |          -0.02  |       -0.074 |            9.841 |
| trk_ds_td | 20-45                        |  75 |          -0.064 |       -0.014 |           25.706 |
| trk_ds_td | 45-90                        |  67 |          -0.096 |       -0.045 |           45.286 |
| trk_ds_td | 90-181                       | 104 |          -0.083 |       -0.079 |           24.228 |
| trk_ds_td | spearman(err, gain_vs_front) | 434 |          -0.216 |      nan     |          nan     |
| trk_sd8   | 0-10                         | 118 |           0.062 |       -0.05  |            9.045 |
| trk_sd8   | 10-20                        |  70 |          -0.015 |       -0.084 |            9.841 |
| trk_sd8   | 20-45                        |  75 |          -0.058 |       -0.075 |           25.706 |
| trk_sd8   | 45-90                        |  67 |          -0.131 |       -0.181 |           45.286 |
| trk_sd8   | 90-181                       | 104 |          -0.199 |       -0.258 |           24.228 |
| trk_sd8   | spearman(err, gain_vs_front) | 434 |          -0.35  |      nan     |          nan     |
| trk_sd4   | 0-10                         | 118 |           0.051 |       -0.062 |            9.045 |
| trk_sd4   | 10-20                        |  70 |          -0.023 |       -0.077 |            9.841 |
| trk_sd4   | 20-45                        |  75 |          -0.055 |       -0.064 |           25.706 |
| trk_sd4   | 45-90                        |  67 |          -0.12  |       -0.174 |           45.286 |
| trk_sd4   | 90-181                       | 104 |          -0.178 |       -0.23  |           24.228 |
| trk_sd4   | spearman(err, gain_vs_front) | 434 |          -0.308 |      nan     |          nan     |
| hyb_ds_td | 0-10                         | 165 |           0.091 |       -0.012 |            4.848 |
| hyb_ds_td | 10-20                        |  79 |           0.005 |        0.02  |           15.483 |
| hyb_ds_td | 20-45                        | 101 |          -0.084 |       -0.016 |           30.509 |
| hyb_ds_td | 45-90                        |  77 |          -0.109 |        0     |           61.472 |
| hyb_ds_td | 90-181                       |  12 |           0.008 |       -0.08  |          110.152 |
| hyb_ds_td | spearman(err, gain_vs_front) | 434 |          -0.358 |      nan     |          nan     |
| hyb_sd8   | 0-10                         | 165 |           0.159 |        0.005 |            4.848 |
| hyb_sd8   | 10-20                        |  79 |           0.1   |        0.01  |           15.483 |
| hyb_sd8   | 20-45                        | 101 |           0.015 |       -0.003 |           30.509 |
| hyb_sd8   | 45-90                        |  77 |          -0.082 |       -0.009 |           61.472 |
| hyb_sd8   | 90-181                       |  12 |           0.086 |        0.083 |          110.152 |
| hyb_sd8   | spearman(err, gain_vs_front) | 434 |          -0.372 |      nan     |          nan     |
| hyb_sd4   | 0-10                         | 165 |           0.151 |        0     |            4.848 |
| hyb_sd4   | 10-20                        |  79 |           0.083 |        0.008 |           15.483 |
| hyb_sd4   | 20-45                        | 101 |           0.001 |       -0.007 |           30.509 |
| hyb_sd4   | 45-90                        |  77 |          -0.078 |       -0.008 |           61.472 |
| hyb_sd4   | 90-181                       |  12 |           0.044 |        0     |          110.152 |
| hyb_sd4   | spearman(err, gain_vs_front) | 434 |          -0.361 |      nan     |          nan     |

## Compute per hop (single thread, weight tables precomputed)

| component       |   per_hop_ms |   p99_ms |   hop_ms |   latency_ms |   load1 |   cpu_fraction |
|:----------------|-------------:|---------:|---------:|-------------:|--------:|---------------:|
| hs_ds_td        |       0.0149 |   0.0158 |        2 |       0.752  |  0.7648 |         0.0074 |
| hs_sd4          |       0.02   |   0.0244 |        2 |       4      |  0.7663 |         0.01   |
| hs_sd8          |       0.0222 |   0.0275 |        4 |       8      |  0.7663 |         0.0055 |
| hyb_ds_td       |       0.0152 |   0.029  |        2 |       1.0723 |  0.7754 |         0.0076 |
| hyb_sd4         |       0.0201 |   0.0253 |        2 |       4      |  0.7771 |         0.01   |
| hyb_sd8         |       0.0224 |   0.0281 |        4 |       8      |  0.7771 |         0.0056 |
| hybrid_logic    |       0.012  | nan      |       16 |     nan      |  0.7548 |         0.0007 |
| ref_ds_td       |       0.0152 |   0.0347 |        2 |       1.0723 |  0.7771 |         0.0076 |
| ref_sd8         |       0.0222 |   0.0278 |        4 |       8      |  0.7771 |         0.0056 |
| tracker_rtn_atf |       0.8593 |   0.9627 |       16 |     nan      |  0.7548 |         0.0537 |
| trk_ds_td       |       0.0159 |   0.0348 |        2 |       1.0723 |  0.7754 |         0.0079 |
| trk_sd4         |       0.0205 |   0.0241 |        2 |       4      |  0.7754 |         0.0102 |
| trk_sd8         |       0.0235 |   0.0281 |        4 |       8      |  0.7754 |         0.0059 |
