# Round 3 results: out-of-domain test + latency budget

OOD set: 144 mixtures, CMU ARCTIC talkers (Scottish/US/Indian-English targets; disjoint interferer talkers), recorded MS-SNSD test noise, SNR -5/0/+5 dB, 8 utterances per cell. Deltas are paired vs the unprocessed mixture. ASR = Whisper base.en word-correct rate on the first 4 utterances of each cell (72 per method). 95% CIs are bootstrap over mixtures.

## Overall (all six OOD conditions)

| method                |   d_si_sdr |   d_estoi | estoi_ci         |   d_pesq |   d_wcr | wcr_ci         |   rtf |   peak_rss_mb |
|:----------------------|-----------:|----------:|:-----------------|---------:|--------:|:---------------|------:|--------------:|
| tse_convtasnet_oracle |     10.621 |     0.202 | [0.181, 0.223]   |    0.535 | nan     | [nan, nan]     | 0.864 |      1252.17  |
| tse_convtasnet_ecapa  |     10.223 |     0.199 | [0.177, 0.222]   |    0.537 |   0.107 | [0.04, 0.17]   | 0.913 |      1366.47  |
| demucs_dns64          |      7.114 |     0.134 | [0.107, 0.161]   |    0.382 |  -0.016 | [-0.06, 0.02]  | 0.609 |       920.809 |
| deepfilternet3        |      4.879 |     0.103 | [0.083, 0.122]   |    0.361 |  -0.05  | [-0.09, -0.01] | 0.088 |       495.523 |
| rnnoise               |      3.142 |     0.069 | [0.050, 0.088]   |    0.153 |  -0.091 | [-0.14, -0.05] | 0.092 |       290.949 |
| mmse_lsa              |      1.377 |     0.01  | [0.005, 0.016]   |    0.038 |  -0.03  | [-0.15, 0.08]  | 0.009 |       274.035 |
| metricgan_plus        |     -4.321 |     0.009 | [-0.005, 0.022]  |    0.425 |  -0.115 | [-0.17, -0.07] | 0.04  |       318.371 |
| wiener_dd             |      1.403 |     0.009 | [0.003, 0.014]   |    0.034 |  -0.022 | [-0.05, 0.00]  | 0.004 |       273.949 |
| wiener_stream8        |      0.458 |    -0.003 | [-0.006, -0.001] |    0.007 | nan     | [nan, nan]     | 0.024 |       253.992 |
| wiener_stream16       |      0.807 |    -0.011 | [-0.015, -0.007] |    0.013 | nan     | [nan, nan]     | 0.007 |       254.633 |
| wiener_stream32       |      0.73  |    -0.022 | [-0.027, -0.017] |    0.015 | nan     | [nan, nan]     | 0.004 |       255.152 |

## ΔESTOI by condition

| method                |   ood_competing |   ood_reverb_rec_babble |   rec_announcements |   rec_babble |   rec_hvac |   rec_transient |
|:----------------------|----------------:|------------------------:|--------------------:|-------------:|-----------:|----------------:|
| deepfilternet3        |           -0.11 |                    0.04 |                0.18 |         0.16 |       0.22 |            0.13 |
| demucs_dns64          |           -0.13 |                    0    |                0.27 |         0.26 |       0.24 |            0.16 |
| metricgan_plus        |           -0.07 |                   -0.02 |                0.06 |         0.06 |       0.05 |           -0.03 |
| mmse_lsa              |           -0.02 |                   -0    |                0    |         0.01 |       0.07 |           -0    |
| rnnoise               |           -0.05 |                   -0.1  |                0.12 |         0.14 |       0.19 |            0.12 |
| tse_convtasnet_ecapa  |            0.33 |                    0.01 |                0.26 |         0.27 |       0.21 |            0.12 |
| tse_convtasnet_oracle |            0.33 |                    0.03 |                0.26 |         0.27 |       0.2  |            0.12 |
| wiener_dd             |           -0.02 |                   -0    |                0    |         0.01 |       0.07 |           -0    |
| wiener_stream16       |           -0.03 |                   -0.02 |               -0.02 |        -0.01 |       0.02 |           -0.02 |
| wiener_stream32       |           -0.05 |                   -0.03 |               -0.03 |        -0.02 |       0.03 |           -0.04 |
| wiener_stream8        |           -0.01 |                   -0.01 |               -0.01 |         0    |       0.02 |           -0.01 |

## ΔSI-SDR (dB) by condition

| method                |   ood_competing |   ood_reverb_rec_babble |   rec_announcements |   rec_babble |   rec_hvac |   rec_transient |
|:----------------------|----------------:|------------------------:|--------------------:|-------------:|-----------:|----------------:|
| deepfilternet3        |            -4.2 |                    -0.1 |                 6.1 |          4.9 |       10.6 |            12   |
| demucs_dns64          |            -5.3 |                     0.2 |                11   |          9.7 |       12.4 |            14.6 |
| metricgan_plus        |            -4.6 |                    -7   |                -5.2 |         -5.7 |       -3.2 |            -0.1 |
| mmse_lsa              |            -0.1 |                     0.6 |                 0.8 |          0.9 |        5.3 |             0.7 |
| rnnoise               |            -1.6 |                    -3.1 |                 3.8 |          3.9 |        6.3 |             9.5 |
| tse_convtasnet_ecapa  |            16.2 |                     0.5 |                11.4 |         10.4 |       11.2 |            11.7 |
| tse_convtasnet_oracle |            16.2 |                     2.7 |                11.4 |         10.4 |       11.4 |            11.7 |
| wiener_dd             |            -0.1 |                     0.5 |                 0.8 |          0.9 |        5.5 |             0.7 |
| wiener_stream16       |            -0.5 |                     0.2 |                 0.3 |          0.2 |        4.1 |             0.5 |
| wiener_stream32       |            -0.8 |                     0.1 |                 0.2 |          0.1 |        4.5 |             0.3 |
| wiener_stream8        |            -0.1 |                     0.2 |                 0.1 |          0.2 |        2.2 |             0.2 |

## Δ ASR word-correct rate by condition

| method               |   ood_competing |   ood_reverb_rec_babble |   rec_announcements |   rec_babble |   rec_hvac |   rec_transient |
|:---------------------|----------------:|------------------------:|--------------------:|-------------:|-----------:|----------------:|
| deepfilternet3       |           -0.06 |                   -0.08 |               -0.04 |        -0.04 |       0    |           -0.08 |
| demucs_dns64         |           -0.1  |                   -0.02 |               -0.03 |         0.06 |       0.04 |           -0.04 |
| metricgan_plus       |           -0.03 |                   -0.11 |               -0.14 |        -0.05 |      -0.11 |           -0.24 |
| mmse_lsa             |           -0.03 |                  nan    |              nan    |       nan    |     nan    |          nan    |
| rnnoise              |           -0.12 |                   -0.18 |               -0.15 |        -0.03 |       0.03 |           -0.1  |
| tse_convtasnet_ecapa |            0.54 |                    0    |                0.01 |         0.14 |       0.01 |           -0.07 |
| wiener_dd            |           -0.03 |                   -0.04 |               -0.07 |        -0.02 |       0.03 |           -0.01 |

## In-domain (LibriSpeech + ESC-50/MUSAN/synthetic, r1+r2 pooled) vs OOD (ARCTIC + recorded MS-SNSD), roughly matched noise types

Matches are approximate: pink->recorded HVAC/vacuum (stationary), environmental->recorded transients, babble->recorded babble, competing->competing. In-domain SNRs span -10..+10 dB, OOD -5..+5 dB.

| method               | in_domain     | ood           |   d_estoi_in |   d_estoi_ood |   d_sisdr_in |   d_sisdr_ood |
|:---------------------|:--------------|:--------------|-------------:|--------------:|-------------:|--------------:|
| wiener_dd            | competing     | ood_competing |       -0.023 |        -0.02  |       -0.034 |        -0.132 |
| rnnoise              | competing     | ood_competing |       -0.079 |        -0.052 |       -2.657 |        -1.558 |
| deepfilternet3       | competing     | ood_competing |       -0.044 |        -0.113 |       -1.477 |        -4.243 |
| demucs_dns64         | competing     | ood_competing |       -0.092 |        -0.128 |       -3.813 |        -5.27  |
| metricgan_plus       | competing     | ood_competing |       -0.074 |        -0.075 |       -4.23  |        -4.57  |
| tse_convtasnet_ecapa | competing     | ood_competing |        0.288 |         0.333 |       15.832 |        16.221 |
| wiener_dd            | babble        | rec_babble    |       -0.002 |         0.009 |        0.548 |         0.916 |
| rnnoise              | babble        | rec_babble    |       -0.079 |         0.138 |       -5.481 |         3.881 |
| deepfilternet3       | babble        | rec_babble    |        0.046 |         0.158 |       -1.248 |         4.91  |
| demucs_dns64         | babble        | rec_babble    |        0.072 |         0.264 |        0.913 |         9.696 |
| metricgan_plus       | babble        | rec_babble    |        0.015 |         0.062 |       -5.983 |        -5.73  |
| tse_convtasnet_ecapa | babble        | rec_babble    |        0.124 |         0.268 |        3.392 |        10.363 |
| wiener_dd            | broadband_env | rec_transient |        0.034 |        -0.005 |        4.26  |         0.748 |
| rnnoise              | broadband_env | rec_transient |        0.14  |         0.118 |        6.893 |         9.517 |
| deepfilternet3       | broadband_env | rec_transient |        0.173 |         0.133 |        9.727 |        11.958 |
| demucs_dns64         | broadband_env | rec_transient |        0.203 |         0.158 |       12.103 |        14.564 |
| metricgan_plus       | broadband_env | rec_transient |        0.027 |        -0.032 |       -1.914 |        -0.129 |
| tse_convtasnet_ecapa | broadband_env | rec_transient |        0.171 |         0.12  |       10.434 |        11.678 |
| wiener_dd            | pink          | rec_hvac      |        0.062 |         0.068 |        3.665 |         5.506 |
| rnnoise              | pink          | rec_hvac      |        0.173 |         0.186 |        8.039 |         6.282 |
| deepfilternet3       | pink          | rec_hvac      |        0.206 |         0.225 |       10.252 |        10.571 |
| demucs_dns64         | pink          | rec_hvac      |        0.21  |         0.241 |       11.608 |        12.436 |
| metricgan_plus       | pink          | rec_hvac      |       -0.007 |         0.054 |       -2.199 |        -3.226 |
| tse_convtasnet_ecapa | pink          | rec_hvac      |        0.152 |         0.21  |        6.896 |        11.195 |

## Latency budget (algorithmic latency vs benefit)

rtf = processing time / audio duration on 2 vCPU aarch64 (offline batch unless per_hop_ms is given, in which case it was processed hop by hop and per_hop_ms is the mean compute per hop). Single-channel rows are on the OOD set; bf_* rows on the round-1 simulated 4-mic array conditions (array_babble, array_competing).

| method               |   algo_latency_ms | set      |   d_estoi |   d_si_sdr |   d_wcr |   rtf |   per_hop_ms |   hop_ms | note                                                             |
|:---------------------|------------------:|:---------|----------:|-----------:|--------:|------:|-------------:|---------:|:-----------------------------------------------------------------|
| wiener_stream8       |               8   | r3       |    -0.003 |      0.458 | nan     | 0.024 |        0.055 |        4 | streamed frame by frame here                                     |
| wiener_stream16      |              16   | r3       |    -0.011 |      0.807 | nan     | 0.007 |        0.046 |        8 | streamed                                                         |
| rnnoise              |              20   | r3       |     0.069 |      3.142 |  -0.091 | 0.092 |      nan     |      nan | measured 320-sample delay @16 kHz (10 ms frame + 10 ms)          |
| wiener_stream32      |              32   | r3       |    -0.022 |      0.73  | nan     | 0.004 |        0.051 |       16 | streamed                                                         |
| wiener_dd            |              32   | r3       |     0.009 |      1.403 |  -0.022 | 0.004 |      nan     |      nan | offline loop, same 32 ms STFT                                    |
| deepfilternet3       |              40   | r3       |     0.103 |      4.879 |  -0.05  | 0.088 |      nan     |      nan | 20 ms window + 2x10 ms lookahead (config.ini); run offline here  |
| demucs_dns64         |              41.3 | r3       |     0.134 |      7.114 |  -0.016 | 0.609 |      nan     |      nan | streaming wrapper, 1-frame (RTF 2.52: not real-time on this CPU) |
| tse_convtasnet_ecapa |             nan   | r3       |     0.199 |     10.223 |   0.107 | 0.913 |      nan     |      nan | non-causal checkpoint, whole utterance                           |
| bf_online_ff         |              32   | r1-array |     0.035 |      0.082 |   0.235 | 0.033 |        0.229 |       16 | 4-mic online MVDR, streamed frame by frame                       |
| bf_online_ff_rnnoise |              52   | r1-array |    -0.076 |     -2.663 |  -0.099 | 0.16  |        0.233 |       16 | online MVDR + RNNoise                                            |
| bf_mvdr_ff           |             nan   | r1-array |     0.061 |      1.122 |   0.305 | 0.009 |      nan     |      nan | offline (utterance-level covariance)                             |
