# Latency and compute (measured on this sandbox)

## Isolated per-block benchmark `bench_under_r7_load.json`

3000 consecutive real 2 ms blocks per mode (fresh engine running only that mode, 1 s warm-up, GC off), aarch64 2 vCPU, nice 19, OMP_NUM_THREADS=1. Load average before 4.44/3.86/2.95, after 4.86/4.03/3.05; round-7 pipeline running: True -> True.

| array | mode | alg. latency ms | + block buffer ms | compute/block mean | median | p95 | p99 | max (ms) | RTF mean | RTF p95 |
|---|---|---|---|---|---|---|---|---|---|---|
| easycom | unprocessed front mic | 0.00 | 2 | 0.0058 | 0.0039 | 0.0041 | 0.0042 | 4.084 | 0.0029 | 0.0020 |
| easycom | head-steered DS (time domain) | 0.75 | 2 | 0.0411 | 0.0183 | 0.0633 | 1.1298 | 4.105 | 0.0205 | 0.0317 |
| easycom | head-steered superdirective 4 ms | 4.00 | 0 | 0.0406 | 0.0234 | 0.0571 | 0.7328 | 2.314 | 0.0203 | 0.0286 |
| easycom | tracker-steered superdirective 4 ms | 4.00 | 0 | 0.0476 | 0.0246 | 0.0503 | 0.0882 | 4.166 | 0.0238 | 0.0252 |
| easycom | head-prior hybrid tracker sd 4 ms | 4.00 | 0 | 0.0454 | 0.0243 | 0.0480 | 0.0777 | 5.314 | 0.0227 | 0.0240 |
| easycom | SIMULATED noise-cut (fixed FIR) | 0.00 | 2 | 0.0177 | 0.0113 | 0.0116 | 0.0137 | 4.115 | 0.0089 | 0.0058 |
| easycom | unprocessed in-ear mics | 0.00 | 2 | 0.0083 | 0.0049 | 0.0051 | 0.0103 | 4.079 | 0.0042 | 0.0026 |
| easycom | **all modes at once** (live path) | - | - | 0.1884 | 0.1106 | 0.1697 | 4.2141 | 8.283 | 0.0942 | - |
| easycom | tracker step (every 16 ms, shared by trk/hyb) | 0 (control only) | - | 1.4751 | 0.9603 | 5.0719 | 5.1868 | 10.221 | 0.0922 | - |
| easycom | **total live engine (all modes + tracker)** | | | | | | | | **0.1864** | |
| libricss7 | unprocessed front mic | 0.00 | 2 | 0.0061 | 0.0040 | 0.0042 | 0.0100 | 2.838 | 0.0031 | 0.0021 |
| libricss7 | head-steered DS (time domain) | 0.62 | 2 | 0.0416 | 0.0262 | 0.0312 | 0.0590 | 5.000 | 0.0208 | 0.0156 |
| libricss7 | head-steered superdirective 4 ms | 4.00 | 0 | 0.0575 | 0.0261 | 0.1220 | 0.8916 | 4.613 | 0.0288 | 0.0610 |
| libricss7 | tracker-steered superdirective 4 ms | 4.00 | 0 | 0.0737 | 0.0288 | 0.1281 | 1.2749 | 4.424 | 0.0368 | 0.0641 |
| libricss7 | head-prior hybrid tracker sd 4 ms | 4.00 | 0 | 0.0548 | 0.0279 | 0.0818 | 1.2172 | 3.532 | 0.0274 | 0.0409 |
| libricss7 | SIMULATED noise-cut (fixed FIR) | 0.00 | 2 | 0.0190 | 0.0113 | 0.0137 | 0.0952 | 2.707 | 0.0095 | 0.0069 |
| libricss7 | **all modes at once** (live path) | - | - | 0.2098 | 0.1211 | 0.2773 | 2.7637 | 4.499 | 0.1049 | - |
| libricss7 | tracker step (every 16 ms, shared by trk/hyb) | 0 (control only) | - | 2.2748 | 1.5246 | 5.5314 | 5.7825 | 6.507 | 0.1422 | - |
| libricss7 | **total live engine (all modes + tracker)** | | | | | | | | **0.2471** | |
| lin4 | unprocessed front mic | 0.00 | 2 | 0.0078 | 0.0040 | 0.0042 | 0.0043 | 4.940 | 0.0039 | 0.0021 |
| lin4 | head-steered DS (time domain) | 0.67 | 2 | 0.0271 | 0.0182 | 0.0186 | 0.0323 | 4.096 | 0.0136 | 0.0093 |
| lin4 | head-steered superdirective 4 ms | 4.00 | 0 | 0.0398 | 0.0247 | 0.0261 | 0.0648 | 4.664 | 0.0199 | 0.0130 |
| lin4 | tracker-steered superdirective 4 ms | 4.00 | 0 | 0.0458 | 0.0258 | 0.0564 | 0.0988 | 4.821 | 0.0229 | 0.0282 |
| lin4 | head-prior hybrid tracker sd 4 ms | 4.00 | 0 | 0.0718 | 0.0264 | 0.0984 | 0.4843 | 8.424 | 0.0359 | 0.0492 |
| lin4 | SIMULATED noise-cut (fixed FIR) | 0.00 | 2 | 0.0275 | 0.0175 | 0.0179 | 0.0275 | 4.173 | 0.0137 | 0.0089 |
| lin4 | **all modes at once** (live path) | - | - | 0.1924 | 0.1145 | 0.1640 | 4.2132 | 5.027 | 0.0962 | - |
| lin4 | tracker step (every 16 ms, shared by trk/hyb) | 0 (control only) | - | 1.3760 | 0.9175 | 5.0302 | 5.1248 | 6.295 | 0.0860 | - |
| lin4 | **total live engine (all modes + tracker)** | | | | | | | | **0.1822** | |

## Under load: during the pre-render of each scene (all modes in one engine)

| scene | load avg (1 min) | mode | mean | p95 | p99 | max (ms) | RTF mean |
|---|---|---|---|---|---|---|---|
| easycom_s10 | 2.29 | raw | 0.0045 | 0.0067 | 0.0075 | 0.049 | 0.0022 |
| easycom_s10 | 2.29 | ear | 0.0050 | 0.0053 | 0.0061 | 0.066 | 0.0025 |
| easycom_s10 | 2.29 | hs_ds | 0.0201 | 0.0260 | 0.0388 | 0.823 | 0.0101 |
| easycom_s10 | 2.29 | hs_sd4 | 0.0269 | 0.0404 | 0.0479 | 0.319 | 0.0134 |
| easycom_s10 | 2.29 | trk_sd4 | 0.0251 | 0.0291 | 0.0476 | 1.324 | 0.0126 |
| easycom_s10 | 2.29 | hyb_sd4 | 0.0245 | 0.0263 | 0.0448 | 0.435 | 0.0122 |
| easycom_s10 | 2.29 | anc_sim | 0.0120 | 0.0134 | 0.0267 | 0.062 | 0.0060 |
| easycom_s10 | | tracker step | 0.922 | 1.004 | 1.087 | 1.64 | 0.0576 |
| easycom_s11 | 2.35 | raw | 0.0045 | 0.0066 | 0.0074 | 0.108 | 0.0022 |
| easycom_s11 | 2.35 | ear | 0.0050 | 0.0052 | 0.0055 | 0.349 | 0.0025 |
| easycom_s11 | 2.35 | hs_ds | 0.0203 | 0.0261 | 0.0374 | 1.271 | 0.0101 |
| easycom_s11 | 2.35 | hs_sd4 | 0.0269 | 0.0398 | 0.0504 | 0.501 | 0.0134 |
| easycom_s11 | 2.35 | trk_sd4 | 0.0247 | 0.0281 | 0.0440 | 0.139 | 0.0124 |
| easycom_s11 | 2.35 | hyb_sd4 | 0.0243 | 0.0260 | 0.0430 | 0.246 | 0.0122 |
| easycom_s11 | 2.35 | anc_sim | 0.0120 | 0.0134 | 0.0168 | 0.122 | 0.0060 |
| easycom_s11 | | tracker step | 0.939 | 1.030 | 1.194 | 2.42 | 0.0587 |
| libricss_ov40 | 2.23 | raw | 0.0045 | 0.0071 | 0.0084 | 0.088 | 0.0023 |
| libricss_ov40 | 2.23 | hs_ds | 0.0283 | 0.0346 | 0.0520 | 1.125 | 0.0142 |
| libricss_ov40 | 2.23 | hs_sd4 | 0.0298 | 0.0453 | 0.0561 | 2.369 | 0.0149 |
| libricss_ov40 | 2.23 | trk_sd4 | 0.0267 | 0.0314 | 0.0489 | 1.268 | 0.0134 |
| libricss_ov40 | 2.23 | hyb_sd4 | 0.0262 | 0.0281 | 0.0483 | 0.538 | 0.0131 |
| libricss_ov40 | 2.23 | anc_sim | 0.0118 | 0.0132 | 0.0145 | 0.106 | 0.0059 |
| libricss_ov40 | | tracker step | 1.399 | 1.519 | 1.767 | 4.27 | 0.0875 |
| sim_restaurant | 3.42 | raw | 0.0076 | 0.0083 | 0.0159 | 4.069 | 0.0038 |
| sim_restaurant | 3.42 | hs_ds | 0.0316 | 0.0319 | 0.0995 | 4.183 | 0.0158 |
| sim_restaurant | 3.42 | hs_sd4 | 0.0422 | 0.0623 | 0.1417 | 4.271 | 0.0211 |
| sim_restaurant | 3.42 | trk_sd4 | 0.0384 | 0.0343 | 0.1106 | 4.241 | 0.0192 |
| sim_restaurant | 3.42 | hyb_sd4 | 0.0366 | 0.0305 | 0.1014 | 4.142 | 0.0183 |
| sim_restaurant | 3.42 | anc_sim | 0.0304 | 0.0259 | 0.0904 | 4.125 | 0.0152 |
| sim_restaurant | | tracker step | 1.602 | 4.874 | 5.118 | 5.55 | 0.1001 |
| sim_street | 3.28 | raw | 0.0066 | 0.0070 | 0.0103 | 4.061 | 0.0033 |
| sim_street | 3.28 | hs_ds | 0.0330 | 0.0275 | 0.0601 | 5.355 | 0.0165 |
| sim_street | 3.28 | hs_sd4 | 0.0495 | 0.0493 | 0.1051 | 4.849 | 0.0248 |
| sim_street | 3.28 | trk_sd4 | 0.0398 | 0.0313 | 0.0710 | 4.678 | 0.0199 |
| sim_street | 3.28 | hyb_sd4 | 0.0407 | 0.0284 | 0.0702 | 4.722 | 0.0203 |
| sim_street | 3.28 | anc_sim | 0.0304 | 0.0238 | 0.0576 | 4.119 | 0.0152 |
| sim_street | | tracker step | 1.360 | 5.010 | 5.112 | 6.38 | 0.0850 |

## Live paced loop (selab.rtdemo.live)

| scene | nice | load avg before | blocks | compute mean / p95 / max (ms) | arrival-to-output p95 / max (ms) | deadline misses | RTF | bit-identical to pre-render |
|---|---|---|---|---|---|---|---|---|
| easycom_s10 (easycom_s10_live_nice0) | 0 | 4.60 | 8000 | 0.405 / 1.381 / 11.95 | 3.622 / 11.97 | 1149 (14.4%) | 0.203 | True |
| libricss_ov40 (libricss_ov40_live_nice0) | 0 | 5.00 | 8000 | 0.692 / 4.313 / 10.50 | 5.936 / 10.56 | 2415 (30.2%) | 0.346 | True |
