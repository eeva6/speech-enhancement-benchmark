# Speech Enhancement Benchmark Lab

A reproducible CPU benchmark comparing classical, neural, separation/target-speaker-extraction (TSE) and
beamforming approaches for improving the intelligibility of a **target talker in recorded audio**.
(Signal processing of captured audio only — it does not reduce sound physically reaching anyone's ears;
see `docs/literature_review.md` §8.)

## Layout
```
selab/            benchmark package
  mixtures.py     seeded synthetic test-set builder (single-channel + simulated 4-mic array)
  classical.py    spectral subtraction, Wiener (decision-directed), MMSE-LSA, noisereduce; min-statistics noise tracker
  neural.py       Demucs DNS64, MetricGAN+, SepFormer-WHAM16k, Conv-TasNet+ECAPA separate-then-select TSE, hybrid
  beamform.py     delay-and-sum, MVDR (free-field / mask-based / oracle), MVDR + DNN post-filter
  metrics.py      SI-SDR(i), STOI, ESTOI, PESQ-WB
  run.py          run ONE method over a set in its own process (runtime, RTF, peak RSS)
  evaluate.py     score all outputs; --asr adds Whisper base.en WER as an intelligibility proxy
  analyze.py      paired deltas vs unprocessed, bootstrap CIs, figures
  latency.py      streaming latency / per-hop compute
app.py            Gradio demo (upload, process, listen, plots, metrics, export)
scripts/          get_data.sh, run_round1.sh, run_round2.sh
docs/             literature_review.md, comparison_matrix.md
results/<tag>/    metrics.csv, wer.csv, runtime_*.json, summary.md, figs/
listening/        curated original vs processed audio examples
REPORT.md         START HERE: findings, critique, round 2, limitations, next experiments
EXECUTION_LOG.md  what ran, what failed, what could not be run
```

## Setup (tested: Python 3.12, aarch64 Linux, 2 vCPU, no GPU)
```bash
bash scripts/setup_env.sh && source .venv/bin/activate   # builds .venv incl. PESQ without a system compiler
# (or: pip install --extra-index-url https://download.pytorch.org/whl/cpu -c constraints.txt -r requirements.txt)
# exact versions that were used: requirements.lock.txt
bash scripts/get_data.sh          # ~1 GB: Mini LibriSpeech, ESC-50, MUSAN background-noise subset
python -m selab.mixtures --tag r1 # 192 mixtures (deterministic, seed 0)
bash scripts/run_round1.sh        # all methods + scoring + ASR (~3 h on 2 vCPU; SepFormer is the slow one)
python -m selab.analyze --tag r1 --asr_k 3
bash scripts/run_round2.sh        # held-out round 2 with controls
python -m selab.analyze --tag r2 --asr_k 4
python -m selab.latency           # streaming latency (run on an idle machine)
python -m selab.listening --tag r1  # curated listening pack -> listening/index_r1.html
python app.py                     # demo at http://127.0.0.1:7860
```
Model weights download automatically on first use into `models/`.

## Data and licences
| Source | Use | Licence |
|---|---|---|
| Mini LibriSpeech dev-clean-2 (OpenSLR 31) | target, babble and competing talkers, transcripts | CC BY 4.0 |
| ESC-50 engine/train/car_horn/siren | traffic composite | CC BY-NC 3.0 |
| MUSAN free-sound "Background noises" (37 files) | broadband environmental | per MUSAN (CC) |
| synthetic pink noise | stationary broadband control | generated |
| pyroomacoustics image-method rooms | reverberation and array simulation | MIT (tool) |

Pretrained models: facebookresearch/denoiser `dns64` (CC BY-NC 4.0), speechbrain/metricgan-plus-voicebank,
speechbrain/sepformer-wham16k-enhancement, JorisCos/ConvTasNet_Libri2Mix_sepnoisy_16k,
speechbrain/spkrec-ecapa-voxceleb, Systran/faster-whisper-base.en. Check each model card before any non-research use.
PESQ wraps ITU-T P.862 reference code: research use only (ITU withdrew P.862 in 2024 in favour of P.863).

## Round 3 (out-of-domain, low-latency models, streaming, listening test)
```bash
source .venv/bin/activate
bash scripts/get_data.sh             # now also fetches CMU ARCTIC (8 talkers) + MS-SNSD recorded test noise
bash scripts/setup_env.sh            # now also installs pyrnnoise and builds DeepFilterNet3 (user-space Rust + zig linker)
./scripts/run_round3.sh build        # 144 OOD mixtures -> mixtures/r3
./scripts/run_round3.sh fast         # classical, MetricGAN+, RNNoise, DeepFilterNet3, Demucs on r3
./scripts/run_round3.sh tse          # TSE (ECAPA + oracle) on r3
./scripts/run_round3.sh backfill     # RNNoise + DeepFilterNet3 on r1, r2
python -m selab.run --method wiener_stream16 --tag r3      # hop-by-hop streaming Wiener (also _8, _32)
python -m selab.run --method bf_online_ff --tag r1         # online 4-mic MVDR (also bf_online_ff_rnnoise)
./scripts/run_round3.sh score && ./scripts/run_round3.sh asr
python -m selab.analyze_r3           # results/r3/summary_r3.md, latency_budget.csv, generalisation_gap.csv, figs/
```
Each step fits a 20-minute job limit, and every step resumes where it stopped.

### Blinded listening test
```bash
python listening_test.py --build     # 288 RMS-equalised stimuli with opaque names + Latin-square plan
python listening_test.py             # http://127.0.0.1:7861 ; give each listener a distinct participant number 0..N
python listening_test.py --analyze   # per-method word-correct rate + bootstrap CI, human rows only
python listening_test.py --selftest  # pipeline check with Whisper as a stand-in listener (tagged synthetic)
```
`results/listening_test/stimulus_key.json` maps each opaque name to its method. Keep it away from listeners.
