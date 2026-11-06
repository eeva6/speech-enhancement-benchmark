# Round 7, phase 1: EasyCom data and head-orientation steering accuracy

Status: **phase 1 complete** (2026-10-24, about 02:00 to 02:45 UTC). No jobs running. Phase 2 (beamformers and ASR) not started.
License: EasyCom is CC-BY-NC 4.0, for research only. Nothing derived from EasyCom audio may go into any deliverable (see data/easycom/LICENSE_NOTE.txt and mixtures/r7/LICENSE_NOTE.txt).

## Data
- I downloaded the public GitHub release assets, which needed no account, form or fee. Every needed file sits in parts 001-016, because the tar is alphabetical and Main/Video_Compressed starts at the end of part 016. So the download stopped at part 018, and parts 017-033 were never fetched. I extracted by streaming the parts through gzip and tar and kept only:
  - Calibration/
  - Main/{Glasses_Microphone_Array_Audio, Close_Microphone_Audio, Speech_Transcriptions, Tracked_Poses}/Session_{4,10,11,12}
  - Main/Metadata/Session_N.txt. The first filter missed these 4 files. I fetched them from git-lfs, and their sha256 matches the LFS oid.
- That is 628 files and 10.9 GB, each checked against the tar-listed size. Every wav was read fully without error. The parts are deleted.
- Session 4: 29 minutes (12-14 redacted). Session 12: 30. Session 10: 24. Session 11: 23. The glasses wearer is participant 2 in all four sessions.

## Frame convention (results/r7/atf_convention.md)
- The head frame is the rigid-body frame: X left, Y up, Z forward.
- az = atan2(x, z), with + meaning left. ATF Phi equals az, and Theta equals 90 − el.
- How I established this: I compared inter-mic delays from the measured IRs with the README geometry. The median error is 20 µs; the opposite azimuth direction gives 221 µs.
- Pose to head: d_head = R(q)ᵀ (p_talker − p_wearer), with q in x, y, z, w order. On 3 minutes, the SRP check gives a median azimuth error of 3.8° this way and 37.9° with the transposed rotation.
- Assumptions:
  - The talker position is the head-pose centre, not the mouth.
  - Transcript frame f maps to time f/20 s, and pose frame k (0-based) to (k + 0.5)/20 s. There is a possible 50 ms frame-numbering ambiguity.

## Step 1: alignment (results/r7/align.csv, align_summary.json)
- Close mics run at a residual clock error of about −4 ppm against the nominal 48008.6 Hz. Per-session effective rates are 48008.23-48008.41 Hz.
- Minute files have their own clock offsets (std about 3 ms within a session), so I fit each (minute, talker) pair separately. There are 293 pairs:
  - 115 fit a full line (offset plus slope).
  - 92 fit an offset and use the session slope.
  - 66 use the minute's shared clock offset plus the pose distance divided by c.
  - 20 use the session median offset.
- The reference is aligned to the direct-path arrival at array ch2.
- **Residual**:
  - In-sample (re-measured window lags): median |lag| 0.087 ms, p90 0.39 ms.
  - Out-of-sample (each mic's offset predicted from the other mics in the same minute plus the pose distance): median 0.43 ms, p90 1.53 ms.
  - Per item (GCC over the utterance only, reliable peaks): val median 0.15 ms and p90 0.87 ms over 744 items; test median 0.05 ms and p90 0.79 ms over 463 items.
  - 36 val and 27 test items are flagged `align_suspect` (|lag| > 2 ms). These are mostly fully overlapped items, where the GCC probably locks onto another talker.

## Step 2: reference DOA and validation (results/r7/doa_validation.csv)
- There is a reference DOA every 50 ms for every tracked participant in the wearer's head frame. The cache is data/easycom/r7_16k/Session_N/<seg>.doa.npz.
- I validated it with ATF SRP-PHAT on ch1-4 (300-6000 Hz, 0.5 s blocks where exactly one tracked non-wearer talker speaks). That gave 3,827 blocks over 102 minutes:
  - **Median azimuth error: 4.5°.** 80% of blocks are within 15° and 83% within 30°. The bias is +2.9°.
  - By split: val 4.1° (n = 2,310), test 5.3° (n = 1,517).
  - The median 3-D error is 24°. This comes from elevation: SRP elevation on this nearly horizontal array is coarse and biased upward by about 10°. Azimuth is the reliable quantity.

## Step 3: items (mixtures/r7/{val,test}/<id>/{mix_mc.wav, ref.wav, doa_ref.npz, item.json}, plus meta.json)
- Each item has 6 channels at 16 kHz in float format, with 2 s of preceding context. Scoring covers [utt_offset_samples, n_samples).
- The utterances are by close-mic talkers and at least 1.0 s long.
- Full 2 s context: 708 of 762 val items and 442 of 472 test items. Utterances less than 2 s into a minute file get shorter context, because the minute files are not contiguous.

| split | items | with words | to wearer | to group | other | none | overlapped | speech |
|---|---|---|---|---|---|---|---|---|
| val (4, 12) | 762 | 707 | 97 | 288 | 180 | 197 | 574 | 41.6 min |
| test (10, 11) | 472 | 434 | 85 | 127 | 124 | 136 | 285 | 23.1 min |

- "Overlapped" means any other transcribed talker overlaps, the wearer and backchannels included; ovl_frac gives the fraction.
- Fields per item:
  - transcript text (with [L]/[C]/[T]/[U]/[H] codes) and n_words
  - target_raw and target
  - t_since_turn_onset
  - az_ref_mean and el_ref_mean
  - align_how, item_lag_ms and align_suspect
- Turn definition: a talker's same-talker utterances merge across gaps of 1 s or less, provided no other talker starts in between.

## Step 4: head-orientation steering accuracy (results/r7/head_onset.csv, onset_r7.csv, figs/head_onset.png)
- The steering direction is array forward (az = 0). Each row is one 50 ms frame of a tracked non-wearer talker's utterance.
- Each turn is weighted equally per bin. The CIs are 95% cluster bootstraps over minutes.
- Sessions 4, 10, 11 and 12 together give 1,565 turns.
- Each cell below is the fraction of frames within ±15° / ±30° / ±45°.

| since turn onset | all | to wearer | to group | other/none | R6 tracker (ATF, val) |
|---|---|---|---|---|---|
| −0.5-0 (before onset) | .29/.54/.69 | .41/.72/.85 | .22/.51/.68 | .29/.50/.65 | .20/.34/.52 |
| 0-0.25 s | .30/.54/.70 | .43/.71/.85 | .22/.51/.68 | .30/.51/.66 | .21/.35/.52 |
| 0.25-0.5 | .30/.55/.71 | .42/.71/.85 | .23/.51/.69 | .30/.52/.67 | .24/.38/.56 |
| 0.5-1 | .31/.58/.73 | .43/.73/.87 | .24/.56/.72 | .32/.54/.69 | .27/.43/.59 |
| 1-2 | .36/.63/.77 | .44/.71/.84 | .29/.64/.79 | .38/.60/.72 | .39/.53/.66 |
| 2-4 | .38/.67/.81 | .47/.79/.88 | .33/.67/.81 | .38/.63/.77 | .48/.60/.73 |
| >4 | .39/.75/.86 | .51/.89/.96 | .37/.78/.91 | .38/.63/.77 | .62/.73/.82 |

Head steering, all targets, at ±15° with 95% CI: 0.30 [0.26, 0.34] at 0-0.25 s and 0.39 [0.34, 0.45] after 4 s.

- **Head orientation is already roughly right at turn onset, but coarse.**
  - In the first 0.25 s it is within ±30° for 54% of frames and within ±45° for 70%. The curve is nearly flat: the before-onset bin matches the 0-0.25 s bin.
  - Within ±15°, it is right for only 30% of frames at onset and 39% after 4 s.
  - The median error is 27° at onset and 15° after 4 s.
- **Speech addressed to the wearer** is the best case: 43% within ±15° and 71% within ±30° at onset.
- **Group-addressed speech** is the worst: 22% within ±15°.
- **The round-6 causal tracker** (rtn mode, ATF steering on ch1-4) is worse than the head early on and better late:
  - Val, within ±15°: 21% at 0-0.25 s and 24% at 0.25-0.5 s, rising to 48% at 2-4 s and 62% after 4 s.
  - Within ±10° it reaches 15%, 17%, 40% and 51% across those bins. On LibriCSS loudspeakers it was 18%, 31% and 87-94% after 3 s, so real conversation in 71 dB babble is much harder.
  - Free-field steering gives the same curve within about 0.03 on real data, even though it fails a synthetic ATF-rendered test. The ATF is the principled choice.
- **The two complement each other.** Taking whichever of head or tracker is closer, frame by frame, gives 37% within ±15° at onset and 68% after 4 s. This is an oracle selection and only an upper bound.
- Test sessions show a slightly higher head curve than val: 0.34 versus 0.27 within ±15° at 0-0.25 s.

## Code and commands (all resumable; each skips outputs that exist)
```
source .venv/bin/activate
python -m selab.prep_r7 resample      # 16 kHz array cache + pass-1 lags
python -m selab.prep_r7 align         # aligned close mics, align.csv/align_summary.json
python -m selab.prep_r7 doa           # per-50 ms reference DOA
python -m selab.prep_r7 validate      # SRP(ATF) validation -> doa_validation.csv
python -m selab.prep_r7 items         # mixtures/r7/{val,test} (+ meta.json; re-run qc afterwards: items rewrites meta.json)
python -m selab.prep_r7 qc            # item-level lag QC, n_words, counts -> meta.json
python -m selab.onset_r7 head         # head_onset.csv, head_onset_by_split.csv, head_onset_frames.csv.gz
python -m selab.onset_r7 track --steer atf --sess 4,12,10,11   # R6 tracker per minute -> outputs/r7/tracks/
python -m selab.onset_r7 report       # onset_r7.csv + figs/head_onset.png
```
