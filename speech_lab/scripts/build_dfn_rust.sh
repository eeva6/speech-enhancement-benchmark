#!/usr/bin/env bash
# Build DeepFilterNet's Rust `deep-filter` binary and the libDF C API (libdf.so) with the user-space Rust
# toolchain in .rust/ and zig as the linker (no system C toolchain). Resumable: cargo keeps finished crates.
set -u
cd "$(dirname "$0")/.."
L=$PWD
export RUSTUP_HOME=$L/.rust/rustup CARGO_HOME=$L/.rust/cargo CARGO_TARGET_DIR=${DF_TARGET:-/tmp/df_target}   # local disk: zig/lld mmap of outputs on the FUSE workspace gave SIGBUS
export PATH=$L/.rust/cargo/bin:$L/.venv/ccbin:$PATH CARGO_BUILD_JOBS=2
export AR=$L/.venv/ccbin/ar_df
export CARGO_TARGET_AARCH64_UNKNOWN_LINUX_GNU_LINKER=$L/.venv/ccbin/rustlink CC=$L/.venv/ccbin/cc_df   # cc_df drops rust-style --target= that zig rejects (tract-linalg .S files)
[ -d third_party/DeepFilterNet ] || git clone --depth 1 https://github.com/Rikorose/DeepFilterNet.git third_party/DeepFilterNet
cd third_party/DeepFilterNet
[ -x $CARGO_TARGET_DIR/release/deep-filter ] || [ -x $L/third_party/df_bin/deep-filter ] || cargo build --release -p deep_filter --bin deep-filter --features "bin tract wav-utils transforms default-model" 2>&1 | tail -25
cargo rustc --release -p deep_filter --lib --crate-type cdylib --features "capi" 2>&1 | tail -15
mkdir -p $L/third_party/df_bin && cp -f $CARGO_TARGET_DIR/release/deep-filter $CARGO_TARGET_DIR/release/libdf.so $L/third_party/df_bin/ 2>&1; ls -la $L/third_party/df_bin
