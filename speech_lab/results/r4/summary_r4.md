# Round 4 summary (21 scenes x 2 input SNRs)

## Benefit by form factor (shortest delay)
| form                           |   delay_ms |   gain_db |   benefit_db |    lo |    hi |
|:-------------------------------|-----------:|----------:|-------------:|------:|------:|
| Glasses, 6 mics                |        3   |         0 |        -0.83 | -1.28 | -0.41 |
| Glasses, 6 mics                |        3   |        10 |         3.82 |  3.58 |  4.07 |
| Glasses, 6 mics                |        3   |        20 |         4.72 |  4.48 |  4.98 |
| Neckband, 6 mics               |        3   |         0 |        -0.95 | -1.38 | -0.56 |
| Neckband, 6 mics               |        3   |        10 |         3.22 |  2.96 |  3.48 |
| Neckband, 6 mics               |        3   |        20 |         4.22 |  3.96 |  4.5  |
| Tabletop, 8-mic ring           |        4.5 |         0 |        -0.27 | -0.46 | -0.07 |
| Tabletop, 8-mic ring           |        4.5 |        10 |         3.55 |  3.26 |  3.83 |
| Tabletop, 8-mic ring           |        4.5 |        20 |         5.28 |  4.93 |  5.63 |
| Phone/clip mic at friend       |        7   |         0 |         1.52 |  1.26 |  1.78 |
| Phone/clip mic at friend       |        7   |        10 |         4.92 |  4.59 |  5.26 |
| Phone/clip mic at friend       |        7   |        20 |         6.25 |  5.9  |  6.58 |
| Plain amplifier (1 mic at ear) |        3   |         0 |        -2.13 | -2.47 | -1.82 |
| Plain amplifier (1 mic at ear) |        3   |        10 |        -0.46 | -0.54 | -0.37 |
| Plain amplifier (1 mic at ear) |        3   |        20 |        -0.21 | -0.28 | -0.13 |
| Ideal: perfectly clean voice   |        1   |         0 |         1.25 |  1.04 |  1.46 |
| Ideal: perfectly clean voice   |        1   |        10 |         9.81 |  9.67 |  9.96 |
| Ideal: perfectly clean voice   |        1   |        20 |        19.68 | 19.48 | 19.89 |

## Benefit vs delay (+10 dB)
| config         |   D_ms |   benefit_db |
|:---------------|-------:|-------------:|
| ear_amp_sd2ms  |    3   |        -0.46 |
| ear_amp_sd2ms  |    6   |        -0.77 |
| ear_amp_sd2ms  |   10   |        -1.69 |
| ear_amp_sd2ms  |   17   |        -3.03 |
| glasses_sd2ms  |    3   |         3.82 |
| glasses_sd2ms  |    6   |         3.36 |
| glasses_sd2ms  |   10   |         2.13 |
| glasses_sd2ms  |   17   |         0.95 |
| glasses_sd2ms  |   32   |        -1.37 |
| ideal_clean    |    1   |         9.81 |
| ideal_clean    |    4   |         8.77 |
| ideal_clean    |    8   |         7.02 |
| ideal_clean    |   15   |         4.51 |
| ideal_clean    |   30   |         0.59 |
| neckband_sd2ms |    3   |         3.22 |
| neckband_sd2ms |    6   |         2.99 |
| neckband_sd2ms |   10   |         2.08 |
| neckband_sd2ms |   17   |         0.89 |
| neckband_sd2ms |   32   |        -1.55 |
| remote_mic     |    7   |         4.92 |
| remote_mic     |   12   |         3.9  |
| remote_mic     |   22   |         1.75 |
| remote_mic     |   32   |         0.4  |
| remote_mic     |   52   |        -2.99 |
| tabletop_sd2ms |    4.5 |         3.55 |
| tabletop_sd2ms |    7   |         4.03 |
| tabletop_sd2ms |   12   |         3.62 |
| tabletop_sd2ms |   22   |         1.03 |
| tabletop_sd2ms |   32   |        -0.33 |

## Open vs in-ear (+10 dB)
| config            |   D_ms |   in_ear |   open |
|:------------------|-------:|---------:|-------:|
| ear_amp_sd2ms     |    3   |    -0.17 |  -0.46 |
| ear_amp_sd2ms     |    6   |    -0.72 |  -0.77 |
| ear_amp_sd2ms     |   10   |    -1.61 |  -1.69 |
| ear_amp_sd2ms     |   17   |    -3.15 |  -3.03 |
| ear_amp_sd2ms_pf  |   11   |    -2.11 |  -1.46 |
| ear_amp_sd2ms_pf  |   14   |    -2.78 |  -2.12 |
| ear_amp_sd2ms_pf  |   18   |    -3.64 |  -2.64 |
| ear_amp_sd2ms_pf  |   25   |    -5.06 |  -3.86 |
| ear_amp_sd8ms     |    9   |    -1.41 |  -1.86 |
| ear_amp_sd8ms     |   12   |    -2.04 |  -1.9  |
| ear_amp_sd8ms     |   16   |    -2.91 |  -2.85 |
| ear_amp_sd8ms     |   23   |    -4.43 |  -4.16 |
| glasses_sd2ms     |    3   |     4.84 |   3.82 |
| glasses_sd2ms     |    6   |     4.22 |   3.36 |
| glasses_sd2ms     |   10   |     3.16 |   2.13 |
| glasses_sd2ms     |   17   |     1.52 |   0.95 |
| glasses_sd2ms     |   32   |    -1.85 |  -1.37 |
| glasses_sd2ms_pf  |   11   |     2.86 |   2.6  |
| glasses_sd2ms_pf  |   14   |     2.09 |   1.66 |
| glasses_sd2ms_pf  |   18   |     1.17 |   1.13 |
| glasses_sd2ms_pf  |   25   |    -0.48 |  -0.32 |
| glasses_sd2ms_pf  |   40   |    -3.88 |  -3.1  |
| glasses_sd8ms     |    9   |     3.7  |   2.3  |
| glasses_sd8ms     |   12   |     3    |   2.4  |
| glasses_sd8ms     |   16   |     2.05 |   1.41 |
| glasses_sd8ms     |   23   |     0.39 |   0.18 |
| glasses_sd8ms     |   38   |    -2.98 |  -2.19 |
| ideal_clean       |    1   |    27.37 |   9.81 |
| ideal_clean       |    4   |    20.58 |   8.77 |
| ideal_clean       |    8   |    14.37 |   7.02 |
| ideal_clean       |   15   |     8.71 |   4.51 |
| ideal_clean       |   30   |     2    |   0.59 |
| neckband_sd2ms    |    3   |     4.37 |   3.22 |
| neckband_sd2ms    |    6   |     3.84 |   2.99 |
| neckband_sd2ms    |   10   |     2.85 |   2.08 |
| neckband_sd2ms    |   17   |     1.34 |   0.89 |
| neckband_sd2ms    |   32   |    -1.88 |  -1.55 |
| neckband_sd2ms_pf |   11   |     2.38 |   2.14 |
| neckband_sd2ms_pf |   14   |     1.65 |   1.26 |
| neckband_sd2ms_pf |   18   |     0.89 |   0.91 |
| neckband_sd2ms_pf |   25   |    -0.65 |  -0.4  |
| neckband_sd2ms_pf |   40   |    -3.98 |  -2.95 |
| neckband_sd8ms    |    9   |     3.52 |   2.1  |
| neckband_sd8ms    |   12   |     2.79 |   2.08 |
| neckband_sd8ms    |   16   |     1.97 |   1.28 |
| neckband_sd8ms    |   23   |     0.55 |   0.23 |
| neckband_sd8ms    |   38   |    -2.73 |  -1.92 |
| remote_mic        |    7   |     6.4  |   4.92 |
| remote_mic        |   12   |     5.15 |   3.9  |
| remote_mic        |   22   |     2.92 |   1.75 |
| remote_mic        |   32   |     0.77 |   0.4  |
| remote_mic        |   52   |    -4.18 |  -2.99 |
| remote_mic_pf     |   15   |     4.31 |   3.99 |
| remote_mic_pf     |   20   |     3.24 |   3.1  |
| remote_mic_pf     |   30   |     1.01 |   0.93 |
| remote_mic_pf     |   40   |    -1.33 |  -1.22 |
| remote_mic_pf     |   60   |    -7.77 |  -7.24 |
| tabletop_sd2ms    |    4.5 |     5.63 |   3.55 |
| tabletop_sd2ms    |    7   |     5.18 |   4.03 |
| tabletop_sd2ms    |   12   |     4.02 |   3.62 |
| tabletop_sd2ms    |   22   |     1.82 |   1.03 |
| tabletop_sd2ms    |   32   |    -0.32 |  -0.33 |
| tabletop_sd2ms_pf |   12.5 |     3.72 |   3.65 |
| tabletop_sd2ms_pf |   15   |     3.16 |   3.01 |
| tabletop_sd2ms_pf |   20   |     2.06 |   1.98 |
| tabletop_sd2ms_pf |   30   |    -0.12 |  -0.11 |
| tabletop_sd2ms_pf |   40   |    -2.46 |  -2.33 |
| tabletop_sd8ms    |   10.5 |     4.55 |   2.88 |
| tabletop_sd8ms    |   13   |     3.99 |   3.12 |
| tabletop_sd8ms    |   18   |     2.86 |   2.11 |
| tabletop_sd8ms    |   28   |     0.74 |   0.41 |
| tabletop_sd8ms    |   38   |    -1.58 |  -1.34 |

## Device SNR advantage over the ear
| config            |   device_snr_minus_ear_snr_dB |
|:------------------|------------------------------:|
| ear_amp_sd2ms     |                         -2.47 |
| ear_amp_sd2ms_pf  |                        nan    |
| ear_amp_sd8ms     |                         -2.46 |
| glasses_sd2ms     |                          1.5  |
| glasses_sd2ms_pf  |                        nan    |
| glasses_sd8ms     |                          1.81 |
| ideal_clean       |                        121.22 |
| neckband_sd2ms    |                          1.3  |
| neckband_sd2ms_pf |                        nan    |
| neckband_sd8ms    |                          1.9  |
| remote_mic        |                          5.27 |
| remote_mic_pf     |                        nan    |
| tabletop_sd2ms    |                          2.23 |
| tabletop_sd2ms_pf |                        nan    |
| tabletop_sd8ms    |                          2.57 |
| unaided           |                        nan    |

## Post-filter effect (min delay, +10 dB)
| config            |   benefit_at_min_delay |
|:------------------|-----------------------:|
| ear_amp_sd2ms     |                  -0.46 |
| ear_amp_sd2ms_pf  |                  -1.46 |
| ear_amp_sd8ms     |                  -1.86 |
| glasses_sd2ms     |                   3.82 |
| glasses_sd2ms_pf  |                   2.6  |
| glasses_sd8ms     |                   2.3  |
| ideal_clean       |                   9.81 |
| neckband_sd2ms    |                   3.22 |
| neckband_sd2ms_pf |                   2.14 |
| neckband_sd8ms    |                   2.1  |
| remote_mic        |                   4.92 |
| remote_mic_pf     |                   3.99 |
| tabletop_sd2ms    |                   3.55 |
| tabletop_sd2ms_pf |                   3.65 |
| tabletop_sd8ms    |                   2.88 |

## Capture sweep
|   dev_snr |   D_ms |   gain_db |   benefit_db |
|----------:|-------:|----------:|-------------:|
|         0 |      1 |         6 |         1.2  |
|         0 |      1 |        10 |         1.96 |
|         0 |      1 |        20 |         2.64 |
|         0 |      3 |         6 |         0.14 |
|         0 |      3 |        10 |         1.34 |
|         0 |      3 |        20 |         2.3  |
|         0 |      5 |         6 |         1.14 |
|         0 |      5 |        10 |         1.69 |
|         0 |      5 |        20 |         2.12 |
|         0 |     10 |         6 |         0.18 |
|         0 |     10 |        10 |         0.65 |
|         0 |     10 |        20 |         1.03 |
|         0 |     20 |         6 |        -1.45 |
|         0 |     20 |        10 |        -1.43 |
|         0 |     20 |        20 |        -1.4  |
|         5 |      1 |         6 |         3.58 |
|         5 |      1 |        10 |         5.41 |
|         5 |      1 |        20 |         7.39 |
|         5 |      3 |         6 |         2.83 |
|         5 |      3 |        10 |         4.98 |
|         5 |      3 |        20 |         7.04 |
|         5 |      5 |         6 |         3.57 |
|         5 |      5 |        10 |         5.04 |
|         5 |      5 |        20 |         6.62 |
|         5 |     10 |         6 |         2.46 |
|         5 |     10 |        10 |         3.71 |
|         5 |     10 |        20 |         5.01 |
|         5 |     20 |         6 |         0.64 |
|         5 |     20 |        10 |         1.25 |
|         5 |     20 |        20 |         1.9  |
|        10 |      1 |         6 |         4.9  |
|        10 |      1 |        10 |         7.76 |
|        10 |      1 |        20 |        11.85 |
|        10 |      3 |         6 |         4.22 |
|        10 |      3 |        10 |         7.28 |
|        10 |      3 |        20 |        11.27 |
|        10 |      5 |         6 |         4.88 |
|        10 |      5 |        10 |         7.22 |
|        10 |      5 |        20 |        10.55 |
|        10 |     10 |         6 |         3.64 |
|        10 |     10 |        10 |         5.59 |
|        10 |     10 |        20 |         8.21 |
|        10 |     20 |         6 |         1.68 |
|        10 |     20 |        10 |         2.83 |
|        10 |     20 |        20 |         4.41 |
|        15 |      1 |         6 |         5.44 |
|        15 |      1 |        10 |         8.97 |
|        15 |      1 |        20 |        15.52 |
|        15 |      3 |         6 |         4.78 |
|        15 |      3 |        10 |         8.4  |
|        15 |      3 |        20 |        14.54 |
|        15 |      5 |         6 |         5.42 |
|        15 |      5 |        10 |         8.31 |
|        15 |      5 |        20 |        13.49 |
|        15 |     10 |         6 |         4.11 |
|        15 |     10 |        10 |         6.48 |
|        15 |     10 |        20 |        10.39 |
|        15 |     20 |         6 |         2.1  |
|        15 |     20 |        10 |         3.57 |
|        15 |     20 |        20 |         5.98 |
|        20 |      1 |         6 |         5.63 |
|        20 |      1 |        10 |         9.44 |
|        20 |      1 |        20 |        17.92 |
|        20 |      3 |         6 |         4.98 |
|        20 |      3 |        10 |         8.84 |
|        20 |      3 |        20 |        16.56 |
|        20 |      5 |         6 |         5.62 |
|        20 |      5 |        10 |         8.74 |
|        20 |      5 |        20 |        15.23 |
|        20 |     10 |         6 |         4.29 |
|        20 |     10 |        10 |         6.84 |
|        20 |     10 |        20 |        11.6  |
|        20 |     20 |         6 |         2.26 |
|        20 |     20 |        10 |         3.86 |
|        20 |     20 |        20 |         6.78 |
|        30 |      1 |         6 |         5.71 |
|        30 |      1 |        10 |         9.64 |
|        30 |      1 |        20 |        19.58 |
|        30 |      3 |         6 |         5.06 |
|        30 |      3 |        10 |         9.05 |
|        30 |      3 |        20 |        17.87 |
|        30 |      5 |         6 |         5.71 |
|        30 |      5 |        10 |         8.94 |
|        30 |      5 |        20 |        16.3  |
|        30 |     10 |         6 |         4.37 |
|        30 |     10 |        10 |         7.01 |
|        30 |     10 |        20 |        12.34 |
|        30 |     20 |         6 |         2.33 |
|        30 |     20 |        10 |         4.01 |
|        30 |     20 |        20 |         7.23 |