# 3. What was built (all causal, frame by frame, on the same real items)

## 3.1 Steering trackers (32 ms frames every 16 ms; frame *j* uses samples up to *j*·256 + 512 only)

| Name | What it does | Speaker check |
|---|---|---|
| R5 tracker | Round-5 running SRP-PHAT map (forgetting 0.97, all bins 200-5000 Hz), argmax per frame. Re-implemented on strictly causal frames so it can be compared step by step. | none |
| track+hyst. | PHAT SRP on the 30% highest-energy bins of each frame. A long map (forgetting 0.99, ~1.6 s) gives up to 3 candidate directions (local maxima ≥ 0.35 of the peak, ≥ 25° apart); candidates feed persistent tracks (20° gate, dropped after 1 s unseen). A short map (forgetting 0.8) decides which track dominates each frame (ratio ≥ 1.2). The steered track changes only if another has 1.3× more (decayed) dominant frames. | none |
| track+ECAPA | Same tracks. Each keeps the last 1.5 s of mic-0 audio from frames it dominated; every 256 ms, once it has ≥ 0.5 s (≥ 0.25 s new), an ECAPA-TDNN embedding is compared with the enrolment embedding (cosine, smoothed). The steered track is the best-scoring one; it switches only on a margin of 0.1. Falls back to track+hyst. until some track has a score. | ECAPA vs a 3-15 s enrolment of the target recorded by the same array |
| REF dir. | System-identification azimuth (round 5), constant. **Oracle geometry, upper bound only.** | — |
| blind whole-seg. | Whole-segment SRP-PHAT argmax (round-5 DS used this). **Non-causal steering**, comparison only. | — |

The tracker only chooses filter weights; it adds no delay to the audio path. Its hyper-parameters (long-map forgetting 0.99, 20° gate) were chosen on sessions 0-2 only (`work_r6/trk_grid*.csv`).

## 3.2 Filters and their exact algorithmic latency

Algorithmic latency = the delay from an input sample to the output sample that represents it, excluding compute time. For a sqrt-Hann weighted-overlap-add STFT with window *N* and hop *N*/2 it is *N* samples (round-5 convention).

| Name | Filter | Algorithmic latency |
|---|---|---|
| ds_td | Time-domain delay-and-sum: 21-tap Kaiser-windowed-sinc fractional delays per mic, 2 ms blocks, 2 ms crossfade when the steering changes | 8 + r/c·fs = 9.98 samples = **0.62 ms** |
| sd4 / sd8 | Superdirective MVDR for a diffuse field (coherence sinc(2πfd/c)), diagonal loading found per bin by bisection so the white-noise gain is ≥ 0 dB (WNG floor), fixed weights per direction (1° grid) | **4 ms** (64-sample window, 2 ms hop) / **8 ms** (128, 4 ms hop) |
| gm4 / gm8 | Adaptive MVDR, free-field steering; noise covariance updated recursively (τ = 0.5 s) on bins whose smoothed coherence with the steering vector is < 0.5 and on frames the tracker marks not-target; loading 1% of trace; WNG ≥ 0 dB enforced by a closed-form blend toward delay-and-sum; weights every 8 ms | **4 ms / 8 ms** |
| rtf4 / rtf8 | Online RTF-MVDR: R_x updated while the tracker says the target dominates, R_n only while it is inactive or another track dominates (48 ms hangover); RTF = R_n·(principal generalised eigenvector of (R_x, R_n)), normalised to mic 0, via Cholesky whitening; per-bin fallback to the free-field vector when immature or inconsistent with the tracked direction (coherence < 0.6); MVDR + loading + WNG ≥ 0 dB (blend toward h/‖h‖²) | **4 ms / 8 ms** |

Variants added after the panel diagnosis (section 5), with parameters fixed a priori: **[warm start]** the same causal pipeline run over 2 s of the preceding recording (`mixtures/r6ctx`, all 144 items re-cut from the raw LibriCSS audio; cut-back error 0.0); **[1 s ramp]** after the start and after every lock switch the weights blend from delay-and-sum (or mic 0) to the filter's own over 1 s; **[ECAPA-verified gate]** the superdirective weights are used only while the steered track's ECAPA score is ≥ 0.15, otherwise the unprocessed mic 0 (250 ms crossfade).

## 3.3 Measurement

Same as round 5: faster-whisper base.en int8, greedy, no timestamps; word-correct = hits / reference words, WER; SI-SDR and ESTOI against the **estimated** reverberant target image at mic 0 (indicative only, its own floor is about −10 dB). 95% CIs by cluster bootstrap over recordings (24 clusters on the panel), 2000 resamples. Holm correction within the round-6 family, per group and per comparison. Outputs are aligned to mic 0 by subtracting each method's known algorithmic delay before scoring.
