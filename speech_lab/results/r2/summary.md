# Results r2

Paired deltas vs unprocessed mixture (d_*). wcr = Whisper base.en word-correct rate (hits/N, higher better); d_wer = change in WER (negative better). ASR columns use only the first 4 utterances of each condition x SNR cell.

Clean-reference WER ceiling: 0.059

## Single-channel conditions

| method | n | d_si_sdr | d_estoi | d_pesq | wcr | d_wcr | d_wer | rtf | peak_rss_mb | n_params |
|---|---|---|---|---|---|---|---|---|---|---|
| noisy | 180 | 0.000 | 0.000 | 0.000 | 0.556 | 0.000 | 0.000 | 0.026 | 250 |  |
| specsub | 180 | 1.473 | 0.018 | 0.049 |  |  |  | 0.002 | 269 |  |
| wiener_dd | 180 | 1.634 | 0.010 | 0.088 | 0.540 | -0.016 | 0.246 | 0.004 | 271 |  |
| mmse_lsa | 180 | 1.607 | 0.013 | 0.087 |  |  |  | 0.009 | 271 |  |
| specsub_oraclenoise | 180 | 5.240 | 0.047 | 0.167 |  |  |  | 0.002 | 270 |  |
| wiener_dd_oraclenoise | 180 | 6.289 | 0.041 | 0.283 | 0.585 | 0.029 | 0.010 | 0.003 | 271 |  |
| mmse_lsa_oraclenoise | 180 | 6.113 | 0.045 | 0.290 |  |  |  | 0.008 | 269 |  |
| metricgan_plus | 180 | -4.024 | -0.004 | 0.479 | 0.406 | -0.150 | 0.146 | 0.031 | 311 | 1895514 |
| demucs_dns64 | 180 | 4.114 | 0.088 | 0.356 | 0.542 | -0.014 | 0.200 | 0.390 | 867 | 33533569 |
| tse_convtasnet_ecapa | 180 | 6.918 | 0.143 | 0.494 | 0.590 | 0.034 | 0.287 | 0.898 | 1194 | 27217841 |
| demucs_then_tse | 180 | 4.414 | 0.093 | 0.324 | 0.526 | -0.030 | -0.072 | 0.861 | 964 | 60751410 |

## Array conditions (mic-0 for single-channel methods)

| method | n | d_si_sdr | d_estoi | d_pesq | wcr | d_wcr | d_wer | rtf | peak_rss_mb | n_params |
|---|---|---|---|---|---|---|---|---|---|---|

## 95% bootstrap CIs (single-channel)

| method | d_si_sdr_ci | d_estoi_ci | d_pesq_ci | wcr_ci | d_wcr_ci | d_wer_ci |
|---|---|---|---|---|---|---|
| noisy | [0.00, 0.00] | [0.00, 0.00] | [0.00, 0.00] | [0.46, 0.65] | [0.00, 0.00] | [0.00, 0.00] |
| specsub | [1.19, 1.76] | [0.01, 0.02] | [0.02, 0.08] | [nan, nan] | [nan, nan] | [nan, nan] |
| wiener_dd | [1.28, 2.01] | [0.01, 0.01] | [0.05, 0.13] | [0.45, 0.63] | [-0.04, 0.01] | [-0.14, 0.74] |
| mmse_lsa | [1.27, 1.96] | [0.01, 0.02] | [0.05, 0.13] | [nan, nan] | [nan, nan] | [nan, nan] |
| specsub_oraclenoise | [4.79, 5.65] | [0.04, 0.05] | [0.12, 0.21] | [nan, nan] | [nan, nan] | [nan, nan] |
| wiener_dd_oraclenoise | [5.82, 6.73] | [0.04, 0.05] | [0.22, 0.35] | [0.49, 0.67] | [-0.00, 0.06] | [-0.28, 0.36] |
| mmse_lsa_oraclenoise | [5.66, 6.54] | [0.04, 0.05] | [0.23, 0.35] | [nan, nan] | [nan, nan] | [nan, nan] |
| metricgan_plus | [-4.61, -3.44] | [-0.02, 0.01] | [0.41, 0.55] | [0.32, 0.49] | [-0.21, -0.09] | [-0.08, 0.34] |
| demucs_dns64 | [2.76, 5.38] | [0.06, 0.11] | [0.28, 0.43] | [0.45, 0.63] | [-0.06, 0.02] | [-0.17, 0.67] |
| tse_convtasnet_ecapa | [5.80, 8.01] | [0.12, 0.16] | [0.42, 0.58] | [0.51, 0.67] | [-0.03, 0.11] | [-0.22, 0.94] |
| demucs_then_tse | [3.09, 5.79] | [0.07, 0.11] | [0.26, 0.39] | [0.44, 0.62] | [-0.07, 0.01] | [-0.27, 0.05] |
