# Speech Enhancement for Intelligibility: Literature & Open-Source Review

*Speech Enhancement Benchmark Lab. Compiled 2026-10-15. Companion file: `comparison_matrix.md`.*

**How the links were checked.** Every arXiv link was resolved against `export.arxiv.org/abs/<id>` and its returned title matched to the paper. Every DOI was resolved through the Crossref API, with title, first author and year matched; JASA and Ear & Hearing abstracts were also read through PubMed. Every GitHub and Hugging Face link returned HTTP 200, and the repo description was checked against the project. Latency, RTF and complexity figures marked "(paper)" were read from the paper's own PDF text. Numbers without that tag are general background knowledge. Treat them as approximate and re-measure them in this lab.

---

## 0. Scope and the one distinction that matters most

"Speech enhancement" here means *signal processing on a captured audio signal*: one or more microphone channels go in, and an estimate of the target speech comes out. The intended endpoint is human intelligibility, meaning the proportion of words or phonemes a listener correctly reports. That is a different endpoint from perceived quality (MOS, PESQ), from ASR word error rate, and from objective proxies such as STOI or SI-SDR. Much of the literature optimises for quality or proxies and then infers intelligibility. Section 9 reviews how weakly that inference holds, particularly for single-channel methods. Section 8 separates signal enhancement from reducing the sound that physically reaches a listener's eardrum.

---

## 1. Classical spectral subtraction

**Key sources.** Boll (1979), *Suppression of acoustic noise in speech using spectral subtraction*, IEEE TASSP, https://doi.org/10.1109/TASSP.1979.1163209 ; Berouti, Schwartz & Makhoul (1979), *Enhancement of speech corrupted by acoustic noise*, ICASSP '79, https://doi.org/10.1109/ICASSP.1979.1170788 .

- **Mechanism.** Take the STFT of the noisy signal. Estimate the noise magnitude (or power) spectrum during non-speech frames. Subtract it from each frame's magnitude, keep the noisy phase, and resynthesise by overlap-add. Berouti added an over-subtraction factor α (larger at low SNR) and a spectral floor β, which trade residual noise against "musical noise", the isolated tonal peaks that subtraction leaves behind.
- **Inputs.** One channel. Needs a noise estimate, usually from a VAD or from leading silence. Assumes the noise is additive, uncorrelated with speech and quasi-stationary.
- **Complexity.** One FFT/iFFT per frame plus O(K) per-bin operations. Negligible on any CPU or MCU.
- **Strengths.** Trivial to implement, transparent, few parameters, and causal latency equal to one frame plus hop (typically 20–32 ms, or less with short frames).
- **Weaknesses.** Musical noise. Speech distortion when the noise is over-estimated. Fails on non-stationary noise (babble, competing talkers), because the noise estimate goes stale. Leaves the phase untouched.
- **Real-time feasibility.** Excellent.
- **Evidence limits.** In listening tests the gains are mostly in perceived noisiness or quality. Hu & Loizou (2007) found spectral-subtractive methods gave **no significant intelligibility improvement** for normal-hearing listeners in almost all conditions (Section 9).

## 2. Statistical estimators, Wiener filtering, noise tracking, adaptive filtering

### 2.1 Wiener and MMSE spectral-amplitude estimators

**Key sources.** Ephraim & Malah (1984), MMSE short-time spectral amplitude (STSA) estimator, https://doi.org/10.1109/TASSP.1984.1164453 ; Ephraim & Malah (1985), MMSE log-spectral amplitude (LSA) estimator, https://doi.org/10.1109/TASSP.1985.1164550 ; Scalart & Vieira Filho (1996), *Speech enhancement based on a priori signal to noise estimation*, ICASSP, https://doi.org/10.1109/ICASSP.1996.543199 .

- **Mechanism.** Model the STFT coefficients of speech and noise as independent (complex Gaussian) random variables. Derive a per-bin gain G(ξ, γ) from the *a priori* SNR ξ and the *a posteriori* SNR γ.
  - The Wiener gain is ξ/(1+ξ).
  - MMSE-STSA minimises the error in amplitude.
  - LSA minimises the error in log-amplitude, which matches loudness perception better and gives less residual noise.
  - Ephraim–Malah introduced the **decision-directed** estimate of ξ: a recursive mix of the previous frame's enhanced amplitude and the current max(γ−1, 0). Scalart & Filho showed that the same decision-directed ξ makes a plain Wiener gain perform close to MMSE-STSA. The heavy smoothing in ξ is what suppresses musical noise.
- **Inputs.** One channel plus a noise PSD estimate, which in practice comes from Section 2.2.
- **Complexity.** O(K) per frame plus an FFT. LSA/STSA need Bessel or exponential-integral functions, usually tabulated. Still far below 1% of a modern CPU core.
- **Strengths.** Principled. Much less musical noise than subtraction. Decades of tuning knowledge. Deterministic and explainable. This is the backbone of commercial hearing-aid and phone noise reduction.
- **Weaknesses.** The Gaussian/stationarity assumptions break for babble and transients. Decision-directed smoothing adds a one-frame lag on onsets, which smears consonants. Quality only as good as the noise tracker.
- **Real-time feasibility.** Excellent. Latency is set by the frame and hop size.
- **Evidence limits.** Robust gains in quality and listening comfort, but not in intelligibility (Hu & Loizou 2007; Kim et al. 2009 summarise the field as "improve speech quality, but not speech intelligibility").

### 2.2 Noise PSD estimation

**Key sources.** Martin (2001), *Noise power spectral density estimation based on optimal smoothing and minimum statistics*, IEEE TSAP, https://doi.org/10.1109/89.928915 ; Cohen (2003), *Noise spectrum estimation in adverse environments: improved minima controlled recursive averaging (IMCRA)*, IEEE TSAP, https://doi.org/10.1109/TSA.2003.811544 .

- **Mechanism.**
  - **Minimum statistics** tracks the minimum of an optimally smoothed periodogram over a sliding window of about 1–2 s. Speech pauses between syllables let the minimum fall to the noise floor. A bias-compensation factor converts the minimum into a mean estimate. No VAD is needed.
  - **IMCRA** uses the minima to compute a speech-presence probability, then performs recursive averaging gated by that probability. It reacts to noise-level changes faster than plain minimum statistics.
- **Complexity.** O(K) per frame plus small buffers.
- **Weaknesses.** The tracking delay is roughly the minimum-search window, so a rising noise floor is under-estimated for up to a second or two. Speech-like noise (babble) gets partly classified as speech.
- **Why it matters for intelligibility.** Under-estimating noise leaves residual noise. Over-estimating it removes weak consonant energy, and weak consonants are exactly the cues that carry place-of-articulation information.

### 2.3 Adaptive noise cancelling (LMS/NLMS)

**Key sources.** Widrow et al. (1975), *Adaptive noise cancelling: principles and applications*, Proc. IEEE, https://doi.org/10.1109/PROC.1975.10036 ; Kuo & Morgan (1999), *Active noise control: a tutorial review*, Proc. IEEE, https://doi.org/10.1109/5.763310 .

- **Mechanism.** A *reference* microphone picks up noise that is correlated with the noise in the primary channel but contains little target speech. An FIR filter adapted by LMS (or step-size-normalised NLMS) predicts the noise component in the primary channel, and the prediction is subtracted.
- **Inputs.** ≥2 sensors with a usable noise-only reference. That is the hard requirement and is rarely met for diffuse noise or nearby competing talkers.
- **Complexity.** O(L) multiply-adds per sample for an L-tap filter. Trivial on a DSP.
- **Strengths.** Can produce very large SNR gains when a clean reference exists (engine noise, echo cancellation, a known interferer feed). Sample-by-sample processing gives near-zero algorithmic latency.
- **Weaknesses.** Target leakage into the reference cancels speech. Convergence is slow when the input is coloured. Performance collapses in reverberant or diffuse fields because coherence between the microphones drops.
- **Electrical vs. acoustic.** The same LMS family, run as FxLMS with a loudspeaker as actuator, is the core of *acoustic* active noise control. That application is a physically different problem (Section 8).

## 3. Neural single-channel enhancement

**Overview source.** Wang & Chen (2018), *Supervised speech separation based on deep learning: an overview*, https://arxiv.org/abs/1708.07524 .

Common traits of this family:

- **Inputs.** One channel at 16 or 48 kHz.
- **Training data.** Parallel clean/noisy data, typically synthetic mixtures such as DNS-Challenge or VoiceBank-DEMAND.
- **Output.** Either a time-frequency mask/filter applied to the STFT, or a direct waveform.
- **Main generalisation risk.** A mismatch between the training noise and the deployment noise, room or microphone.

### 3.1 Representative models

- **SEGAN** (Pascual, Bonafonte & Serrà, 2017), https://arxiv.org/abs/1703.09452 . Code: https://github.com/santi-pdp/segan (TensorFlow).
  - Fully convolutional waveform U-Net generator trained adversarially with an L1 term.
  - Historically important as an end-to-end waveform GAN.
  - Non-causal, with a ~1 s window. Its objective scores are now surpassed by later models.
- **Demucs denoiser** (Défossez, Synnaeve & Adi, 2020), *Real Time Speech Enhancement in the Waveform Domain*, https://arxiv.org/abs/2006.12847 . Code: https://github.com/facebookresearch/denoiser .
  - Causal encoder–LSTM–decoder on the raw waveform with a multi-resolution STFT loss.
  - Paper: 40 ms frame and 16 ms stride, including 3 ms lookahead. RTF 0.6 for H=48 (0.8 single-core) and 1.05 for H=64 on a laptop CPU.
  - Strong waveform baseline, but heavier than the mask-based models below.
- **MetricGAN+** (Fu et al., 2021), https://arxiv.org/abs/2104.03538 . Pretrained model: https://huggingface.co/speechbrain/metricgan-plus-voicebank .
  - A discriminator learns to predict PESQ, and the generator (a BLSTM mask estimator) is trained to maximise it.
  - Paper: PESQ 3.15 on VoiceBank-DEMAND.
  - **Caution.** Optimising directly for PESQ inflates that metric. PESQ is a quality model and was never validated as an intelligibility predictor.
- **RNNoise** (Valin, 2018), *A Hybrid DSP/Deep Learning Approach to Real-Time Full-Band Speech Enhancement*, https://arxiv.org/abs/1709.08243 . Code: https://github.com/xiph/rnnoise .
  - Small GRU network predicting 22 Bark-like band gains, plus a pitch-based comb filter that cleans harmonics between bands.
  - Paper: 48 kHz full-band, 20 ms windows with 50% overlap (10 ms hop), about 40 MFLOPS, about 1.3% of one x86 core in non-vectorised C.
  - Strengths: extremely cheap and production-proven.
  - Weaknesses: coarse band resolution limits suppression between harmonics and in babble, and it causes speech attenuation at low SNR.
- **DeepFilterNet 1/2/3** (Schröter et al.).
  - Papers:
    - DFN1: https://arxiv.org/abs/2110.05588
    - DFN2: https://arxiv.org/abs/2205.05474
    - DFN3: *Perceptually Motivated Real-Time Speech Enhancement*, https://arxiv.org/abs/2305.08227
  - Code: https://github.com/Rikorose/DeepFilterNet (Rust/LADSPA real-time path).
  - Two stages: ERB-band gains for the spectral envelope, then a complex multi-frame "deep filter" below about 5 kHz that restores periodic structure.
  - Paper: 48 kHz, 20 ms window, 10 ms hop, 2-frame lookahead, for **40 ms algorithmic latency**. Real-time factor 0.04 (DFN2) and 0.19 single-threaded (DFN3) on a notebook i5.
  - The best current open quality/complexity trade-off for full-band real-time denoising.
- **DCCRN** (Hu et al., 2020), https://arxiv.org/abs/2008.00264 . Code: https://github.com/huyanxin/DeepComplexCRN .
  - Complex-valued convolutional recurrent U-Net estimating a complex ratio mask, so it is phase-aware.
  - Paper: 3.7 M parameters, ranked first in the DNS 2020 real-time track. The semi-causal variant uses 37.5 ms total latency, inside the 40 ms DNS limit.
- **FullSubNet** (Hao et al., 2021), https://arxiv.org/abs/2010.15508 . Code: https://github.com/Audio-WestlakeU/FullSubNet .
  - A full-band LSTM supplies global spectral context, and a sub-band LSTM per frequency (with neighbouring bins) models local stationarity.
  - Outputs a cIRM. The paper's real-time configuration uses a small future-frame output delay.
  - Follow-up: FullSubNet+ https://arxiv.org/abs/2203.12188 .

### 3.2 DNS Challenge papers (benchmarks, data, latency rules)

- Interspeech 2020 DNS: https://arxiv.org/abs/2005.13981
- ICASSP 2021 DNS: https://arxiv.org/abs/2009.06122
- Interspeech 2021 DNS: https://arxiv.org/abs/2101.01902
- ICASSP 2023 DNS: https://arxiv.org/abs/2303.11510
- Data and scripts: https://github.com/microsoft/DNS-Challenge

These provide large synthetic training sets, blind real-recording test sets and crowdsourced ITU-T P.808/P.835 subjective ratings. Their latency rules are covered in Section 7.

### 3.3 Family assessment

- **Strengths.** Handles non-stationary noise far better than statistical estimators. At 40 ms latency, mask/filter models (RNNoise, DFN) run in real time on one CPU core.
- **Weaknesses.**
  - Domain mismatch with the training data.
  - Hallucination and over-suppression at very low SNR. Generative models can produce plausible but wrong phonemes.
  - Speech distortion that quality metrics only partly penalise.
  - Training cost.
- **Evidence limits.** Nearly all results are PESQ/STOI/DNSMOS on synthetic test sets, or MOS. Controlled word-recognition studies of these specific open models are rare. The strongest human intelligibility evidence for DNN masking comes from the Healy/Wang line of studies (Section 9), which used lab-trained models in matched noise types.

## 4. Single-channel source separation

- **Conv-TasNet** (Luo & Mesgarani, 2019), https://arxiv.org/abs/1809.07454 . Reference code: https://github.com/kaituoxu/Conv-TasNet (unofficial PyTorch).
  - A learned 1-D conv encoder replaces the STFT. A stacked dilated TCN estimates masks per source, and a decoder resynthesises.
  - Short encoder windows (about 2 ms) allow low algorithmic latency.
  - Paper: 15.3 dB SI-SNRi on WSJ0-2mix (non-causal). The causal variant scores substantially lower.
- **DPRNN** (Luo, Chen & Yoshioka, 2020), https://arxiv.org/abs/1910.06379 . Splits long sequences into chunks and alternates intra-chunk and inter-chunk RNNs. Matched the prior state of the art with a model about 20× smaller (paper).
- **SepFormer** (Subakan et al., 2021), *Attention is All You Need in Speech Separation*, https://arxiv.org/abs/2010.13154 . Pretrained models: https://huggingface.co/speechbrain/sepformer-wsj02mix and https://huggingface.co/speechbrain/sepformer-wham .
  - Dual-path transformer.
  - Paper: 22.3 dB SI-SNRi on WSJ0-2mix.
  - Non-causal, with a heavy compute load.
- **Toolkits.**
  - **Asteroid**: https://arxiv.org/abs/2005.04132 , https://github.com/asteroid-team/asteroid
  - **SpeechBrain**: https://arxiv.org/abs/2106.04624 , https://github.com/speechbrain/speechbrain
- **Datasets.**
  - **WHAM!** (noisy two-speaker): https://arxiv.org/abs/1907.01160
  - **WHAMR!** (noisy + reverberant): https://arxiv.org/abs/1910.10279
  - **LibriMix** (Cosentino et al., built for better generalisation): https://arxiv.org/abs/2005.11262 , https://github.com/JorisCos/LibriMix

Family assessment:

- **Mechanism.** Unlike denoisers, separators output *N* streams (speakers, and sometimes noise). The training objective is permutation-invariant (PIT).
- **Inputs.** One channel, typically at 8 kHz in the benchmarks.
- **Complexity.** Conv-TasNet is about 5 M parameters. SepFormer is about 26 M parameters with quadratic attention per chunk. Both are GPU-oriented in practice.
- **Strengths.** The only single-channel family that addresses *speech-on-speech* masking, which is the case statistical denoisers cannot handle at all.
- **Weaknesses.**
  - The output is unordered, so something downstream must choose which stream the listener wants. That is the motivation for target-speaker extraction (Section 6).
  - Large performance drops from anechoic 8 kHz WSJ0-2mix to noisy, reverberant or real recordings (WHAMR!, LibriMix exist to quantify this).
  - SepFormer and DPRNN are evaluated non-causally.
- **Evidence limits.**
  - SI-SNRi on synthetic mixtures dominates the literature.
  - The WSJ0-2mix speaker overlap between training and test inflates results (motivation stated in the LibriMix paper).
  - There is little human intelligibility testing. Healy et al. (2019) is the strongest example, using a BLSTM ratio mask against a competing talker plus reverberation.

## 5. Multichannel beamforming

**Key sources.**
- Capon (1969), *High-resolution frequency-wavenumber spectrum analysis*, Proc. IEEE, https://doi.org/10.1109/PROC.1969.7278 . The origin of the MVDR / minimum-variance distortionless beamformer.
- Warsitz & Haeb-Umbach (2007), *Blind acoustic beamforming based on generalized eigenvalue decomposition* (GEV / max-SNR), https://doi.org/10.1109/TASL.2007.898454 .
- Heymann, Drude & Haeb-Umbach (2016), *Neural network based spectral mask estimation for acoustic beamforming*, ICASSP, https://doi.org/10.1109/ICASSP.2016.7471664 .

Code:
- **pyroomacoustics**: https://arxiv.org/abs/1710.04196 , https://github.com/LCAV/pyroomacoustics . Room simulation (image source method), DAS/MVDR beamformers, DOA estimation, STFT tools.
- **pb_bss** (Paderborn): https://github.com/fgnt/pb_bss . Mask-based beamforming, cACGMM.
- **nara_wpe** dereverberation front-end: https://github.com/fgnt/nara_wpe .

The beamformers:

- **Delay-and-sum (DAS).** Time-align the channels toward a steering direction, then average them.
  - Gain against spatially white noise is 10·log10(M) dB for M microphones.
  - Gain against diffuse noise is small at low frequencies for compact arrays, because the beam is wide when the aperture is small relative to the wavelength.
- **MVDR.** Minimise output power subject to a distortionless response toward the target steering vector or relative transfer function: w = Φ_nn⁻¹ d / (dᴴ Φ_nn⁻¹ d). Needs a noise spatial covariance Φ_nn and a target RTF or DOA.
- **GEV / max-SNR.** Maximise wᴴΦ_xx w / wᴴΦ_nn w via the principal generalised eigenvector. Needs a post-filter, such as blind analytic normalisation, to undo spectral colouring.
- **Mask-based beamforming (Heymann 2016).** A neural network estimates per-T-F speech and noise masks. The masks weight covariance estimates, which feed MVDR or GEV. This combines DNN robustness with *linear* spatial filtering, and became the dominant CHiME front end.

Family assessment:

- **Inputs.** ≥2 synchronised microphones with known or estimable geometry. Inter-channel clock sync is essential.
- **Complexity.** DAS costs O(MK) per frame. MVDR adds an M×M inverse per frequency bin, which is cheap for M ≤ 8. Mask estimation adds the network cost.
- **Strengths.**
  - Linear spatial filters introduce little nonlinear speech distortion, which is good for both intelligibility and ASR.
  - Performance grows with the number of microphones and the aperture.
  - Multichannel processing is the intervention with the strongest real-world intelligibility record in hearing aids. Directional microphones are an established benefit, although this review does not cite a specific trial.
- **Weaknesses.**
  - Steering errors, reverberation and RTF mismatch cause target cancellation (MVDR is sensitive to this).
  - Compact arrays give little gain at low frequencies against diffuse noise.
  - A moving talker or a moving head requires tracking.
  - Covariance estimation needs time, which conflicts with fast adaptation.
- **Real-time feasibility.** Yes on CPU. Latency is set by the STFT frame. Time-domain DAS has essentially zero latency.
- **Evidence limits.** Most open evaluations are ASR WER (CHiME) or simulated rooms. Intelligibility gains for human listeners depend heavily on array placement relative to the head and the talker.

## 6. Target-speaker extraction (TSE)

- **SpeakerBeam** (Žmolíková et al., 2019), *Speaker aware neural network for target speaker extraction in speech mixtures*, IEEE JSTSP, https://doi.org/10.1109/JSTSP.2019.2922820 .
  - Time-domain follow-up: https://arxiv.org/abs/2001.08378 . Code (time-domain, built on Asteroid): https://github.com/BUTSpeechFIT/speakerbeam .
  - A few seconds of enrolment speech yields a speaker embedding, and an adaptation layer modulates a mask-estimation network so it outputs only that speaker.
- **VoiceFilter** (Wang et al., 2019), https://arxiv.org/abs/1810.04826 .
  - A d-vector from a speaker-verification net conditions a CNN-LSTM spectrogram masker.
  - No official code. Unofficial: https://github.com/maum-ai/voicefilter .
- **SpEx / SpEx+** (Xu et al. / Ge et al., 2020): https://arxiv.org/abs/2004.08326 , https://arxiv.org/abs/2005.04686 . Multi-scale time-domain encoder and a jointly trained speaker encoder, which avoids STFT phase issues.
- **WeSep toolkit** (2024), https://arxiv.org/abs/2409.15799 , https://github.com/wenet-e2e/wesep . Scalable TSE recipes (e.g. BSRNN-based) with online data simulation. The README marks pretrained-model release and CLI as "coming soon" as of fetch, so treat it as a training toolkit for now.

Family assessment:

- **Mechanism.** Separation conditioned on a speaker cue: enrolment audio, or a spatial or visual cue. It solves the output-selection problem that separation leaves open.
- **Inputs.** The mixture plus an enrolment clip of the target talker, typically 3–10 s.
- **Complexity.** Similar to separation networks, plus an embedding network that runs once per enrolment.
- **Strengths.** Directly addresses "I want to hear *this* person". Robust to an unknown number of interferers.
- **Weaknesses.**
  - **Target confusion.** When the enrolment matches poorly, or the voices are similar (same-gender pairs), the model extracts the wrong talker or switches mid-utterance. That is worse for intelligibility than no processing.
  - Enrolment logistics.
  - Most models are non-causal.
- **Evidence limits.** Results are almost entirely SI-SDRi on synthetic WSJ0/Libri mixtures. I found no controlled human-intelligibility studies of open TSE models in this review. That gap should be stated in any lab claims.

## 7. Real-time operation and latency

- **DNS Challenge rules (paper).**
  - Interspeech 2020: real-time track total algorithmic latency T ≤ 40 ms (frame + lookahead), processed in under the stride time for a 20 ms frame on an Intel quad-core i5.
  - ICASSP 2021: frame + stride + lookahead ≤ 40 ms. Worked examples: 20 ms frame / 10 ms hop = 30 ms (passes), 32/16 = 48 ms (fails).
  - These are *telephony* budgets. They exclude buffering, device and network delay.
- **Measured systems (paper).**
  - RNNoise: 10 ms hop, about 1.3% of a core.
  - DeepFilterNet: 40 ms, RTF 0.04–0.19 on an i5.
  - Demucs: 40 ms, RTF 0.6–1.05.
  - DCCRN: 37.5 ms.
- **Hearing-device latency tolerance** (Stone & Moore and colleagues, Ear & Hearing). These budgets are much tighter.
  - **Closed fitting.** Stone & Moore (1999), part I, https://doi.org/10.1097/00003446-199906000-00002 : delays were rated "disturbing" at **20–30 ms** for mild-to-moderate simulated losses, and the authors conclude disturbance becomes likely above **20 ms**.
  - **Open canal fitting.** Stone, Moore, Meisenbacher & Derleth (2008), part V, https://doi.org/10.1097/AUD.0b013e3181734ef2 : the direct airborne sound mixes with the delayed processed sound, producing comb filtering. A "just acceptable" rating was reached at only **about 5–6 ms**.
  - **Correction to the brief.** The commonly quoted "~10 ms" lies between these two findings. It is not a single Stone & Moore threshold. Use ≤5–6 ms for open fits and ≲10–20 ms for occluding fits.
- **Implication.** Every STFT model reviewed here (DFN's 40 ms, DNS-compliant models at 30–40 ms, RNNoise at about 20 ms of window) exceeds open-fit hearing-aid tolerance. They suit telephony, conferencing, recorded audio and closed-headphone monitoring, not transparent hearing devices. Low-latency variants need short frames, asymmetric windows or time-domain encoders, and they lose separation quality as a result (the Conv-TasNet paper discusses this trade-off explicitly).

## 8. Signal enhancement vs. physically reducing sound at the ear

This is the most frequently conflated issue, and it matters for any intelligibility claim.

1. **What a DSP pipeline changes.** Enhancement produces a new *electrical or digital* signal with a higher estimated SNR. A listener benefits only if that output is what reaches the eardrum *instead of* the original sound field:
   - listening to a recording or a call;
   - closed headphones or an insert earphone with a good seal;
   - a hearing aid in an occluding fitting;
   - a cochlear implant (direct electrical stimulation).
2. **The direct acoustic path is untouched.** In any open or partially occluding situation (open-fit hearing aids, earbuds with transparency, vents, a loudspeaker in a room), the ambient sound still arrives through leakage paths, attenuated only by whatever passive or active isolation exists. The eardrum receives *direct sound plus processed sound*. Two consequences:
   - A pipeline reporting +15 dB output SNR yields an effective SNR at the ear limited by the direct-path SNR, wherever the leakage is comparable to or louder than the processed signal. Open fits provide "little attenuation of external air-borne sounds" (Stone et al. 2008), and that is especially true at low frequencies.
   - The processed path must also be fast. Otherwise the two paths comb-filter (Section 7).
3. **Passive attenuation.** Earplugs and earmuffs reduce sound physically through mass, seal and absorption. Attenuation is limited by leaks and, ultimately, by **bone conduction**. Berger, Kieper & Gauger (2003), https://doi.org/10.1121/1.1605415 , review bone-conduction limits of roughly **40–60 dB** (mean, 125 Hz–8 kHz). No signal processing changes sound that reaches the cochlea through the skull.
4. **Active noise control (ANC/ANR)** is *acoustic* cancellation. A loudspeaker emits anti-noise, computed by FxLMS-type controllers (Kuo & Morgan 1999), so that pressure cancels in a small zone, typically the ear canal or cup.
   - Effective mainly at low frequencies, below about 1 kHz. The quiet zone shrinks as wavelength shortens, and causality and latency limits bound the high-frequency performance.
   - ANC reduces both noise *and* speech in the cancelled band unless the speech is passed through separately.
   - It is a separate system from speech enhancement. Its success is measured as sound-pressure-level reduction at the ear (dB insertion loss), not as output SNR.
5. **Practical reporting rule for this lab.**
   - Report enhancement results as *signal-domain* metrics (SI-SDR, STOI, PESQ, WER) on *processed audio*.
   - Never describe them as "noise reduction at the listener" or as hearing protection.
   - Any claim about what a person hears in a live acoustic setting must specify the delivery path (seal, vent, ANC), its attenuation, and end-to-end latency.
   - Output-SNR gains from software do **not** reduce noise exposure dose.

## 9. Metrics, and evidence that enhancement improves human intelligibility

### 9.1 Objective metrics

- **STOI** (Taal et al., 2011), https://doi.org/10.1109/TASL.2011.2114881 .
  - Correlates short-time (~384 ms) one-third-octave envelopes of clean and processed speech.
  - Validated on time-frequency-weighted (masked) noisy speech.
  - Intrusive: it needs the clean reference.
  - Code: https://github.com/mpariente/pystoi .
- **ESTOI** (Jensen & Taal, 2016), https://doi.org/10.1109/TASLP.2016.2585878 . Extends STOI to modulated maskers by correlating spectro-temporal patterns. Prefer it for fluctuating noise and babble.
- **PESQ** (ITU-T P.862 family), https://www.itu.int/rec/T-REC-P.862 .
  - A *quality* model (MOS-LQO). It is not an intelligibility measure.
  - **Status.** The ITU page states P.862, P.862.1, P.862.2 and P.862.3 "are out of date and were deleted on 5 January 2024. Please refer to P.863" (POLQA).
  - **Licensing.** The ITU reference implementation was distributed with IPR/licence conditions for commercial use. I did not obtain the current licence text, so verify with the ITU or rights holders before any commercial use.
  - The widely used Python wrapper https://github.com/ludlows/PESQ is MIT-licensed as a wrapper, but it wraps the ITU reference C code. The wrapper's licence does not clear the underlying IPR.
  - Use PESQ for research comparison only and say so.
- **SI-SDR** (Le Roux et al., 2019), *SDR – half-baked or well done?*, https://arxiv.org/abs/1811.02508 .
  - Shows that BSS-eval SDR can be gamed by filtering. Proposes a scale-invariant SDR that projects the estimate onto the reference.
  - The standard separation metric. It is not perceptual, and it penalises harmless linear filtering and phase shifts.
- **DNSMOS** (Reddy et al.), https://arxiv.org/abs/2010.15258 ; P.835 version (SIG/BAK/OVRL) https://arxiv.org/abs/2110.01763 ; code in https://github.com/microsoft/DNS-Challenge/tree/master/DNSMOS .
  - Non-intrusive, trained to predict crowdsourced MOS.
  - Useful on real recordings without references.
  - It predicts *quality*, not intelligibility, and can be exploited by models trained on similar data.

**Metric caveat.** STOI and ESTOI were validated on classical and masking distortions. Generative and neural artefacts (hallucinated phonemes, over-suppression) can score well on STOI while being misheard. ASR WER and human word scores remain the arbiter.

### 9.2 Human-listener evidence

- **Hu & Loizou (2007)**, *A comparative intelligibility study of single-microphone noise reduction algorithms*, JASA, https://doi.org/10.1121/1.2766778 .
  - Eight algorithms (spectral-subtractive, subspace, statistical-model, Wiener) were tested on IEEE sentences and consonants in babble, car, street and train noise at 0 and 5 dB SNR, with normal-hearing listeners.
  - "With the exception of a single noise condition, no algorithm produced significant improvements in speech intelligibility."
  - Quality rankings did not predict intelligibility rankings.
  - This is the canonical negative result for classical single-channel enhancement.
- **Kim, Lu, Hu & Loizou (2009)**, JASA, https://doi.org/10.1121/1.3184603 .
  - A Bayesian classifier estimating a *binary mask* gave large intelligibility gains: over 60 percentage points in −5 dB babble, for normal-hearing listeners.
  - Evidence that *accurate per-T-F SNR estimation*, not smoother gain functions, is what makes intelligibility gains possible.
  - Caveat: trained and tested on the same noise types.
- **Healy, Yoho, Wang & Wang (2013)**, JASA, https://doi.org/10.1121/1.4820893 .
  - DNN-estimated binary masks increased intelligibility in all conditions (speech-shaped noise and babble).
  - Gains were larger for hearing-impaired listeners and at low SNRs, with some going from near 0% to above 70%.
- **Healy et al. (2015)**, JASA, https://doi.org/10.1121/1.4929493 . A DNN ratio mask generalised to *unseen segments of the same noise type* (babble, cafeteria) with substantial gains for hearing-impaired listeners.
- **Healy, Delfarah, Johnson & Wang (2019)**, JASA, https://doi.org/10.1121/1.5093547 . A BLSTM ratio mask against a competing talker plus reverberation gave an average benefit of 56 percentage points for hearing-impaired listeners at the least favourable target-to-interferer ratio.

**Evidence limits to state plainly:**
1. Most positive DNN intelligibility results use offline, non-causal or matched-noise-type models in the lab, with few listeners (usually about 10 per group).
2. Results for open real-time models (RNNoise, DFN, Demucs) in human word-recognition tests are scarce. Their papers report MOS and objective metrics.
3. Hearing-impaired listeners often rate processed signals similarly regardless of algorithm: Huber et al. (2018), *Int J Audiol*, https://doi.org/10.1080/14992027.2017.1279758 . Quality preference and intelligibility benefit are separate endpoints.
4. Comfort and listening-effort benefits from classical noise reduction are real but are not intelligibility gains.

---

## 10. Implications for the benchmark lab

1. **Keep three metric tiers separate.**
   - Intelligibility proxies: ESTOI and STOI, plus ASR WER with a fixed recogniser.
   - Quality: PESQ (research use only), DNSMOS.
   - Separation fidelity: SI-SDR.
   - Do not report a single "improvement" number.
2. **Report latency as algorithmic (frame + lookahead) and measured RTF.** Classify each system against three budgets: telephony (≤40 ms, DNS), occluding hearing devices (≲20 ms) and open fit (≲5–6 ms).
3. **Baselines.** Wiener-DD with minimum-statistics or IMCRA noise tracking is the honest classical baseline. RNNoise and DeepFilterNet3 are the real-time neural baselines. Demucs and MetricGAN+ round out the comparison. Add SepFormer or ConvTasNet for multi-talker conditions, and SpeakerBeam/WeSep for TSE.
4. **Include a babble/competing-talker condition and a reverberant condition** (WHAMR!-style). This is where single-channel statistical methods fail and where the families separate.
5. **Wording.** "Improves objective intelligibility proxies on processed audio" is supportable. "Improves what listeners hear in the room" is not, without a listening test and a specified acoustic delivery path (Section 8).

---

## References (all links verified 2026-10-15)

| # | Reference | Link |
|---|---|---|
| 1 | Boll 1979, Spectral subtraction | https://doi.org/10.1109/TASSP.1979.1163209 |
| 2 | Berouti, Schwartz, Makhoul 1979 | https://doi.org/10.1109/ICASSP.1979.1170788 |
| 3 | Ephraim & Malah 1984, MMSE-STSA | https://doi.org/10.1109/TASSP.1984.1164453 |
| 4 | Ephraim & Malah 1985, MMSE-LSA | https://doi.org/10.1109/TASSP.1985.1164550 |
| 5 | Scalart & Vieira Filho 1996, a priori SNR / DD Wiener | https://doi.org/10.1109/ICASSP.1996.543199 |
| 6 | Martin 2001, Minimum statistics | https://doi.org/10.1109/89.928915 |
| 7 | Cohen 2003, IMCRA | https://doi.org/10.1109/TSA.2003.811544 |
| 8 | Widrow et al. 1975, Adaptive noise cancelling | https://doi.org/10.1109/PROC.1975.10036 |
| 9 | Kuo & Morgan 1999, ANC tutorial | https://doi.org/10.1109/5.763310 |
| 10 | Wang & Chen 2018, Supervised separation overview | https://arxiv.org/abs/1708.07524 |
| 11 | SEGAN 2017 | https://arxiv.org/abs/1703.09452 · https://github.com/santi-pdp/segan |
| 12 | Défossez et al. 2020, Demucs denoiser | https://arxiv.org/abs/2006.12847 · https://github.com/facebookresearch/denoiser |
| 13 | MetricGAN+ 2021 | https://arxiv.org/abs/2104.03538 · https://huggingface.co/speechbrain/metricgan-plus-voicebank |
| 14 | Valin 2018, RNNoise | https://arxiv.org/abs/1709.08243 · https://github.com/xiph/rnnoise |
| 15 | DeepFilterNet (1) | https://arxiv.org/abs/2110.05588 · https://github.com/Rikorose/DeepFilterNet |
| 16 | DeepFilterNet2 | https://arxiv.org/abs/2205.05474 |
| 17 | DeepFilterNet3 | https://arxiv.org/abs/2305.08227 |
| 18 | DCCRN 2020 | https://arxiv.org/abs/2008.00264 · https://github.com/huyanxin/DeepComplexCRN |
| 19 | FullSubNet 2021 | https://arxiv.org/abs/2010.15508 · https://github.com/Audio-WestlakeU/FullSubNet |
| 20 | FullSubNet+ 2022 | https://arxiv.org/abs/2203.12188 |
| 21 | Interspeech 2020 DNS Challenge | https://arxiv.org/abs/2005.13981 · https://github.com/microsoft/DNS-Challenge |
| 22 | ICASSP 2021 DNS Challenge | https://arxiv.org/abs/2009.06122 |
| 23 | Interspeech 2021 DNS Challenge | https://arxiv.org/abs/2101.01902 |
| 24 | ICASSP 2023 DNS Challenge | https://arxiv.org/abs/2303.11510 |
| 25 | Conv-TasNet 2019 | https://arxiv.org/abs/1809.07454 · https://github.com/kaituoxu/Conv-TasNet |
| 26 | DPRNN 2020 | https://arxiv.org/abs/1910.06379 |
| 27 | SepFormer 2021 | https://arxiv.org/abs/2010.13154 · https://huggingface.co/speechbrain/sepformer-wham |
| 28 | Asteroid 2020 | https://arxiv.org/abs/2005.04132 · https://github.com/asteroid-team/asteroid |
| 29 | SpeechBrain 2021 | https://arxiv.org/abs/2106.04624 · https://github.com/speechbrain/speechbrain |
| 30 | WHAM! 2019 | https://arxiv.org/abs/1907.01160 |
| 31 | WHAMR! 2020 | https://arxiv.org/abs/1910.10279 |
| 32 | LibriMix 2020 | https://arxiv.org/abs/2005.11262 · https://github.com/JorisCos/LibriMix |
| 33 | Capon 1969, MVDR origin | https://doi.org/10.1109/PROC.1969.7278 |
| 34 | Warsitz & Haeb-Umbach 2007, GEV | https://doi.org/10.1109/TASL.2007.898454 |
| 35 | Heymann et al. 2016, Mask-based beamforming | https://doi.org/10.1109/ICASSP.2016.7471664 · https://github.com/fgnt/pb_bss |
| 36 | Pyroomacoustics 2018 | https://arxiv.org/abs/1710.04196 · https://github.com/LCAV/pyroomacoustics |
| 37 | nara_wpe (dereverberation) | https://github.com/fgnt/nara_wpe |
| 38 | Žmolíková et al. 2019, SpeakerBeam | https://doi.org/10.1109/JSTSP.2019.2922820 |
| 39 | Delcroix et al. 2020, Time-domain SpeakerBeam | https://arxiv.org/abs/2001.08378 · https://github.com/BUTSpeechFIT/speakerbeam |
| 40 | Wang et al. 2019, VoiceFilter | https://arxiv.org/abs/1810.04826 · https://github.com/maum-ai/voicefilter (unofficial) |
| 41 | SpEx 2020 | https://arxiv.org/abs/2004.08326 |
| 42 | SpEx+ 2020 | https://arxiv.org/abs/2005.04686 |
| 43 | WeSep 2024 | https://arxiv.org/abs/2409.15799 · https://github.com/wenet-e2e/wesep |
| 44 | Stone & Moore 1999, Tolerable HA delays I | https://doi.org/10.1097/00003446-199906000-00002 |
| 45 | Stone et al. 2008, Tolerable HA delays V (open canal) | https://doi.org/10.1097/AUD.0b013e3181734ef2 |
| 46 | Berger, Kieper, Gauger 2003, Bone-conduction limits of HPDs | https://doi.org/10.1121/1.1605415 |
| 47 | Taal et al. 2011, STOI | https://doi.org/10.1109/TASL.2011.2114881 · https://github.com/mpariente/pystoi |
| 48 | Jensen & Taal 2016, ESTOI | https://doi.org/10.1109/TASLP.2016.2585878 |
| 49 | ITU-T P.862 (PESQ) status page | https://www.itu.int/rec/T-REC-P.862 · https://github.com/ludlows/PESQ |
| 50 | Le Roux et al. 2019, SI-SDR | https://arxiv.org/abs/1811.02508 |
| 51 | DNSMOS 2021 | https://arxiv.org/abs/2010.15258 |
| 52 | DNSMOS P.835 2022 | https://arxiv.org/abs/2110.01763 · https://github.com/microsoft/DNS-Challenge/tree/master/DNSMOS |
| 53 | Hu & Loizou 2007, Intelligibility of single-mic NR | https://doi.org/10.1121/1.2766778 |
| 54 | Kim, Lu, Hu, Loizou 2009, Binary-mask intelligibility | https://doi.org/10.1121/1.3184603 |
| 55 | Healy et al. 2013, DNN for HI listeners | https://doi.org/10.1121/1.4820893 |
| 56 | Healy et al. 2015, Novel noise segments | https://doi.org/10.1121/1.4929493 |
| 57 | Healy et al. 2019, Competing talker + reverberation | https://doi.org/10.1121/1.5093547 |
| 58 | Huber et al. 2018, HI listeners and SMNR schemes | https://doi.org/10.1080/14992027.2017.1279758 |
