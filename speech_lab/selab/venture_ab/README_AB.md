# Conversation Bubble: before/after listening set (real 7-mic recordings)

**Open it.** Double-click `START_DEMO.command` (Mac), or run `python3 -m http.server 8766` in this folder, then open
http://localhost:8766/. It needs a local server because browsers block audio loading from file://. No internet is needed.

**Use it.** Pick a clip on the left, press Play, then press **space** (or the big button) to flip between
A = unprocessed centre microphone and B = the processing mode you select. All tracks play in sync, so the switch is instant.
Every track is level-matched to the same gated loudness, so "louder" can't win by itself. The SIMULATED ANC track is the exception: it keeps its level drop.

## What the audio is
- LibriCSS (Chen et al., ICASSP 2020): LibriSpeech read speech replayed over 8 loudspeakers in a real meeting room and recorded
  by a 7-mic circular table array (centre mic plus 6 mics on a 4.25 cm radius). These are real recordings; the talkers are loudspeakers, not people.
- Clips come from held-out sessions 3-5 and the overlapped conditions (OV10/OV20/OV40). They were chosen by a fixed, seeded random
  rule that was written down before any processing. One extra clip, if present, is marked **BEST CASE (post-hoc)**.
- **Single-target clips:** one target talker plus whoever overlaps them, plus the room's own noise.
- **Group (sector) clips:** the target is every talker within ±50° of a chosen direction, and the competition is everyone else.
  This is the closest honest stand-in for "hear that conversation over this one". LibriCSS contains one read-speech meeting per
  recording, never two conversations happening at once.

## Categories (kept strictly separate)
- **A. Captured-audio improvement (measured):** what the array plus processing does to the recorded signal.
- **B. Target vs competing talker(s) (measured):** the change in the target (or target-group) to other-talker ratio, measured over the
  time when both are speaking, separately from noise.
- **C. ANC at the ear: SIMULATED.** Lab simulation curves applied to the recording. Nothing was measured on a head or a device.
- **D. Open-room reduction: NOT claimed.** Nothing here makes the room quieter for anyone.
- Anything marked **ORACLE** uses lab-only knowledge (the true direction or the true signals). It is an upper bound, not a product.

## How the numbers were measured
- The LibriCSS dry loudspeaker feeds and a least-squares system identification (the same method as the lab's round 5) split
  each recording into: target image + other-talker image + residual (the room noise plus model error, about −10 to −12 dB).
- Every mode is linear, so each part was passed through exactly the same filter as the mixture. The output SNR and target-vs-talker
  ratio are therefore measured exactly, not estimated.
- SI-SDR, STOI and ESTOI are measured against the estimated target image at the centre mic.
- Word-correct uses faster-whisper base.en after normalising every signal to −26 dBFS. Whisper is a proxy, not a human listener.
- Full write-up: `03_EXPERIMENTS/ab_set.md` in the venture folder. Per-clip numbers: `metrics.json`.

## Licence and attribution
Audio is derived from LibriCSS and LibriSpeech, both CC BY 4.0. See `ATTRIBUTION.txt`. This set contains no EasyCom (CC BY-NC) audio.
