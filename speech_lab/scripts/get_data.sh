#!/usr/bin/env bash
# Download every public source used by the benchmark (~1.0 GB). Run from the repo root.
set -euo pipefail
mkdir -p data && cd data

# 1) Mini LibriSpeech dev-clean-2 (OpenSLR SLR31, CC BY 4.0) - target / babble / competing talkers + transcripts
[ -d LibriSpeech/dev-clean-2 ] || { curl -L -o dev-clean-2.tar.gz https://www.openslr.org/resources/31/dev-clean-2.tar.gz; tar xzf dev-clean-2.tar.gz; rm dev-clean-2.tar.gz; }

# 2) ESC-50 (CC BY-NC 3.0) - engine/train/car_horn/siren clips for the traffic composite
[ -d ESC-50-master ] || { curl -L -o esc50.zip https://github.com/karolpiczak/ESC-50/archive/master.zip; unzip -q esc50.zip; rm esc50.zip; }

# 3) MUSAN noise/free-sound "Background noises" subset (37 files listed in MUSAN's ANNOTATIONS), via HF mirror
mkdir -p musan_bg
BASE=https://huggingface.co/datasets/FluidInference/musan/resolve/main/noise/free-sound
curl -sL -o musan_bg/ANNOTATIONS $BASE/ANNOTATIONS
curl -sL -o musan_bg/LICENSE $BASE/LICENSE
for n in $(tail -n +2 musan_bg/ANNOTATIONS); do
  [ -f musan_bg/$n.wav ] || curl -sL -o musan_bg/$n.wav $BASE/$n.wav
done
# ---- round 3 out-of-domain data: CMU ARCTIC (8 talkers) + MS-SNSD recorded test noise ----
mkdir -p arctic
for s in awb bdl clb jmk ksp rms slt aew; do
  [ -d arctic/cmu_us_${s}_arctic ] && continue
  curl -sL -o arctic/$s.tar.bz2 http://festvox.org/cmu_arctic/packed/cmu_us_${s}_arctic.tar.bz2
  python3 -c "import tarfile,sys;tarfile.open(sys.argv[1]).extractall('arctic')" arctic/$s.tar.bz2 && rm arctic/$s.tar.bz2
done
if [ ! -d mssnsd/noise_test ]; then
  git clone -q --depth 1 --filter=blob:none --sparse https://github.com/microsoft/MS-SNSD.git mssnsd
  (cd mssnsd && git sparse-checkout set noise_test)
fi
echo "data ready"
# Note: DEMAND (Zenodo 1227121) was the first choice for traffic/cafeteria noise but zenodo.org returned
# HTTP 502 from the build sandbox; see EXECUTION_LOG.md.
# NOTE: noise-free-sound-0335/0494/0842 are absent on the HF mirror and download as 15-byte "Entry not found"
# stubs. They are kept on disk on purpose (the builder redraws when it hits one) so that r1 rebuilds bit-exactly.
