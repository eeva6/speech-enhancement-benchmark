#!/usr/bin/env bash
# Create a persistent virtualenv in ./.venv with every dependency, including a PESQ build that works
# without a system C compiler (uses the ziglang wheel). Tested on aarch64 Linux, Python 3.12, CPU only.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
. .venv/bin/activate
pip install --no-cache-dir -q --upgrade pip
pip install --no-cache-dir -q --extra-index-url https://download.pytorch.org/whl/cpu torch==2.4.1 torchaudio==2.4.1
pip install --no-cache-dir -q -c constraints.txt numpy scipy soundfile librosa pystoi pyroomacoustics matplotlib pandas \
    noisereduce speechbrain==1.1.1 denoiser faster-whisper jiwer gradio ziglang cython
# PESQ: needs a C compiler. If gcc exists, plain `pip install pesq` works; otherwise use zig.
if ! command -v gcc >/dev/null 2>&1; then
  ZIG=$(python -c "import ziglang,os;print(os.path.join(os.path.dirname(ziglang.__file__),'zig'))")
  GV=$(ldd --version | head -1 | grep -oE "[0-9]+\.[0-9]+$")
  mkdir -p .venv/ccbin
  # -mcpu=generic is required: zig's native-CPU build produced SIGILL at runtime (see EXECUTION_LOG.md)
  printf '#!/bin/sh\nexec %s cc -target %s-linux-gnu.%s -mcpu=generic -fno-sanitize=all -O2 "$@"\n' "$ZIG" "$(uname -m)" "$GV" > .venv/ccbin/cc
  chmod +x .venv/ccbin/cc; cp .venv/ccbin/cc .venv/ccbin/gcc
  PATH=$PWD/.venv/ccbin:$PATH CC=cc LDSHARED="cc -shared" pip install --no-cache-dir -q --no-build-isolation --no-deps pesq
else
  pip install --no-cache-dir -q pesq
fi
pip install --no-cache-dir -q -c constraints.txt asteroid
python -c "import pesq,numpy as np;x=np.random.randn(48000)*.1;print('pesq ok',round(pesq.pesq(16000,x,x+.01*np.random.randn(48000),'wb'),2))"
# ---- round 3: RNNoise (prebuilt aarch64/x86 wheel), tabulate, DeepFilterNet3 (Rust build) ----
pip install --no-cache-dir -q pyrnnoise==0.4.5 tabulate
if ! python -c "import df" 2>/dev/null; then
  export RUSTUP_HOME=$PWD/.rust/rustup CARGO_HOME=$PWD/.rust/cargo CARGO_TARGET_DIR=$PWD/.rust/target
  [ -x .rust/cargo/bin/cargo ] || curl -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal --no-modify-path
  LINK=""
  if ! command -v gcc >/dev/null 2>&1; then
    # zig's lld rejects rustc's aarch64 erratum flag; drop it (EXECUTION_LOG item 17)
    printf '#!/usr/bin/env python3\nimport os,sys\nc=open(os.path.join(os.path.dirname(__file__),"cc")).read().split("exec ",1)[1].replace(chr(34)+"$@"+chr(34),"").split()\nos.execv(c[0],c+[a for a in sys.argv[1:] if "fix-cortex-a53-843419" not in a])\n' > .venv/ccbin/rustlink
    chmod +x .venv/ccbin/rustlink
    export CARGO_TARGET_$(uname -m | tr a-z A-Z)_UNKNOWN_LINUX_GNU_LINKER=$PWD/.venv/ccbin/rustlink CC=cc
    export PATH=$PWD/.venv/ccbin:$PATH
  fi
  export PATH=$PWD/.rust/cargo/bin:$PATH CARGO_BUILD_JOBS=2
  NP=$(python -c "import numpy;print(numpy.__version__)")
  pip install --no-cache-dir -c constraints.txt deepfilternet==0.5.6
  pip install --no-cache-dir -q --no-deps "numpy==$NP" "packaging>=24"   # deepfilternet pins numpy<2; it runs fine on 2.x
fi
pip freeze > requirements.lock.txt
echo "env ready: source .venv/bin/activate"
