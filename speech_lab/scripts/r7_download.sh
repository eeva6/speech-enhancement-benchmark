#!/bin/bash
# Resumable sequential download of EasyCom v1.0.0 release parts.
# A part is complete when renamed from .partial to final name (size-checked).
cd "$(dirname "$0")/../data/easycom/parts" || exit 1
B=https://github.com/facebookresearch/EasyComDataset/releases/download/v1.0.0/EasyComDataset.tar.gz
for i in $(seq -w 1 33); do
  n=$(printf "%03d" $((10#$i)))
  f=EasyComDataset.tar.gz.$n
  [ -f STOP ] && { echo "STOP file present, exiting"; exit 0; }
  [ -f "$f" ] && continue
  [ -f "$f.deleted" ] && continue
  want=$(curl -sIL "$B.$n" | grep -i '^content-length' | tail -1 | tr -dc 0-9)
  for attempt in 1 2 3 4 5 6; do
    curl -sSL --retry 5 --retry-delay 5 -C - -o "$f.partial" "$B.$n"
    have=$(stat -c %s "$f.partial" 2>/dev/null || echo 0)
    if [ -n "$want" ] && [ "$have" = "$want" ]; then mv "$f.partial" "$f"; echo "$(date -u +%FT%TZ) done $f $have"; break; fi
    echo "$(date -u +%FT%TZ) incomplete $f have=$have want=$want attempt=$attempt"; sleep 10
  done
done
echo "$(date -u +%FT%TZ) ALL DONE"
