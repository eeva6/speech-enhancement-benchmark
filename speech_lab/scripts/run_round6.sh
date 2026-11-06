#!/usr/bin/env bash
# Round 6: causal low-latency multichannel front-ends on the real LibriCSS 7-mic items (reuses round-5 data).
# Every step is resumable: re-running skips finished wavs / transcriptions.  Run steps one at a time on a
# shared machine (each is a single process; at most two should run at once).
#   ./scripts/run_round6.sh tracker [r5|r5sim]   # tracker accuracy on all items (caches tracks)
#   ./scripts/run_round6.sh panel   [r5|r5sim]   # all round-6 methods on the 48-item panel
#   ./scripts/run_round6.sh score   [r5|r5sim]   # objective metrics + Whisper ASR for the panel
#   ./scripts/run_round6.sh holdout             # tune on sessions 0-2, freeze, test on sessions 3-5 (all items)
#   ./scripts/run_round6.sh full                # winner(s) + baselines on all 144 items
#   ./scripts/run_round6.sh timing              # idle per-hop compute / RTF benchmark
#   ./scripts/run_round6.sh analyze             # results/r6/summary_r6.md, figs
#   ./scripts/run_round6.sh listening           # listening/r6 mp3 pairs + round6_listening.zip
#   ./scripts/run_round6.sh report              # REPORT_R6.pdf
set -u
cd "$(dirname "$0")/.."
[ -f .venv/bin/activate ] && . .venv/bin/activate
STEP=${1:-all}; TAG=${2:-r5}
PANEL="ds_td_r5t,ds_td_rtn,ds_td_rt,ds_td_ref,ds_td_blind,sd4_rt,sd4_ref,sd8_rt,sd8_ref,gm4_rt,gm4_ref,gm8_rt,gm8_ref,rtf4_rt,rtf4_ref,rtf8_rt,rtf8_ref"
SIM="ds_td_rt,ds_td_ref,sd4_rt,sd4_ref,gm4_rt,gm4_ref,rtf4_rt,rtf4_ref"
[ "$TAG" = r5sim ] && PANEL=$SIM
if [ $STEP = all ] || [ $STEP = tracker ]; then python -m selab.trk_eval_r6 --tag $TAG; fi
if [ $STEP = all ] || [ $STEP = panel ]; then python -m selab.run_r6 --tag $TAG --items sub48 --methods $PANEL; fi
if [ $STEP = all ] || [ $STEP = score ]; then
  python -m selab.score_r6 --tag $TAG --items sub48 --methods $PANEL
  python -m selab.score_r6 --tag $TAG --items sub48 --asr --methods $PANEL
fi
if [ $STEP = all ] || [ $STEP = holdout ]; then python -m selab.holdout_r6 all; fi
if [ $STEP = all ] || [ $STEP = full ]; then python -m selab.holdout_r6 full; fi
if [ $STEP = all ] || [ $STEP = timing ]; then python -m selab.timing_r6; fi
if [ $STEP = all ] || [ $STEP = analyze ]; then python -m selab.summary_r6; fi
if [ $STEP = all ] || [ $STEP = listening ]; then python -m selab.listening_r6; fi
if [ $STEP = all ] || [ $STEP = report ]; then
  pandoc REPORT_R6.md -o REPORT_R6.pdf --pdf-engine=pdflatex -H docs/pdf_header.tex -V geometry:margin=2cm -V fontsize=10pt
fi
