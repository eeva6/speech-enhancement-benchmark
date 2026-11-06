
### libricss (test)

| variant | DER c0.25 | DER c0 | miss | FA | conf | JER | spk count err (abs / signed) | cpWER | WER (speaker-agnostic) |
|---|---|---|---|---|---|---|---|---|---|

### easycom (test)

| variant | DER c0.25 | DER c0 | miss | FA | conf | JER | spk count err (abs / signed) | cpWER | WER (speaker-agnostic) |
|---|---|---|---|---|---|---|---|---|---|
| platform | 27.7 | 36.2 | 21.5 | 5.0 | 9.8 | 45.2 | 1.00 / -1.00 | 72.8 | 50.0 |
| A_spectral | 38.0 | 50.3 | 30.8 | 8.0 | 11.5 | 47.0 | 1.00 / +1.00 | 59.4 | 50.0 |
| A_ahc | 39.4 | 51.5 | 28.8 | 10.4 | 12.3 | 47.0 | 2.00 / +2.00 | 59.2 | 50.0 |
| A_spectral_oracleK | 38.6 | 48.9 | 30.8 | 8.0 | 10.1 | 50.0 | 0.00 / +0.00 | 56.7 | 50.0 |
| A_spectral_oracleVAD | 23.0 | 33.1 | 18.1 | 0.0 | 15.0 | 37.0 | 1.00 / +1.00 | 58.3 | 50.0 |
| A_ahc_oracleVAD | 32.0 | 41.0 | 18.1 | 0.0 | 23.0 | 45.6 | 2.00 / +2.00 | 65.4 | 50.0 |
| B_spatial_spectral | 51.4 | 60.3 | 30.8 | 8.0 | 21.5 | 63.9 | 1.00 / +0.00 | 74.0 | 50.0 |
| B_spatial_ahc | 44.2 | 55.0 | 28.8 | 10.4 | 15.8 | 51.2 | 2.50 / +2.50 | 67.2 | 50.0 |
| B_spatial_spectral_oracleVAD | 35.3 | 42.5 | 18.1 | 0.0 | 24.4 | 53.1 | 1.00 / +1.00 | 68.4 | 50.0 |
| B_head_rawDOA | 40.9 | 52.5 | 28.8 | 10.4 | 13.4 | 48.7 | 2.00 / +2.00 | 60.1 | 50.0 |
| B_world_poseOracle | 44.9 | 55.7 | 28.8 | 10.4 | 16.5 | 51.6 | 3.00 / +3.00 | 68.4 | 50.0 |
| B_max_poseOracle | 44.2 | 55.0 | 28.8 | 10.4 | 15.8 | 51.2 | 2.50 / +2.50 | 67.2 | 50.0 |
| B_head_rawDOA_oracleVAD | 28.6 | 37.6 | 18.1 | 0.0 | 19.6 | 42.2 | 2.00 / +2.00 | 59.9 | 50.0 |
| B_max_poseOracle_oracleVAD | 31.3 | 39.7 | 18.1 | 0.0 | 21.7 | 44.7 | 2.50 / +2.50 | 66.5 | 50.0 |
| B_gated_spectral | 37.9 | 49.1 | 30.8 | 8.0 | 10.3 | 47.8 | 1.00 / +1.00 | 58.0 | 50.0 |
| B_gated_ahc | 45.5 | 55.5 | 28.8 | 10.4 | 16.3 | 54.1 | 1.50 / +1.50 | 66.9 | 50.0 |
| B_gated_spectral_oracleVAD | 28.0 | 35.3 | 18.1 | 0.0 | 17.2 | 46.0 | 0.50 / -0.50 | 59.6 | 50.0 |
| B_gated_ahc_oracleVAD | 37.6 | 44.8 | 18.1 | 0.0 | 26.8 | 51.2 | 2.50 / +2.50 | 72.8 | 50.0 |

### LibriCSS DER (collar 0, overlap scored) by overlap condition

| variant |  |
|---|

### Failure breakdown (collar 0)

| dataset | variant | DER single-talker frames | DER overlap frames | overlap share of ref speech | acc turns <1 s | 1-3 s | >3 s |
|---|---|---|---|---|---|---|---|
| easycom | A_spectral | 28.9 | 68.9 | 33.6 | 21.3 | 55.2 | 64.2 |
| easycom | A_spectral_oracleVAD | 16.6 | 65.4 | 33.6 | 26.8 | 65.9 | 73.5 |
| easycom | B_spatial_spectral | 45.1 | 67.6 | 33.6 | 27.2 | 44.5 | 52.3 |
| easycom | platform | 25.7 | 46.4 | 33.6 | 55.1 | 77.4 | 66.3 |

### Speaker-count estimates per test recording (clusters with >= 5 s)

| recording | n_ref | A_ahc | A_spectral | B_spatial_spectral |
|---|---|---|---|---|
| ec_s10 | 4 | 5 | 6 | 5 |
| ec_s11 | 5 | 8 | 5 | 4 |

### Runtime (1 CPU thread, nice 19, shared 2-vCPU box; RTF = compute s / audio s)

| dataset | stage | audio min | RTF |
|---|---|---|---|
| easycom | asr | 47 | 0.090 |
| easycom | emb | 105 | 0.262 |
| easycom | plat | 105 | 0.025 |
| easycom | srp | 105 | 0.005 |
| easycom | vad | 105 | 0.012 |
| libricss | emb | 40 | 0.579 |
| libricss | plat | 40 | 0.004 |
| libricss | srp | 40 | 0.006 |
| libricss | vad | 50 | 0.011 |
