# Hearing a conversation partner in loud places: technology landscape (research memo)

Compiled 2026-10-18 for the Speech Enhancement Benchmark Lab. The scope covers every form factor: open-ear glasses, neck-worn, clip-on/remote mic, tabletop, phone, distributed/hybrid. In-ear devices appear only as a comparison point.

**Lab context this memo is read against:** single-mic neural denoisers gave no benefit at ≤16 ms latency; a 4-mic online MVDR helped ASR; target-speaker extraction (TSE) gave +16 dB on a competing talker but runs offline.

**Evidence tags:** **[M]** measured (lab or clinical, numbers below). **[V]** vendor-measured (manufacturer white paper, not independent). **[C]** claimed with no published number. **[S]** speculative or research concept. **(excerpt)** means the number comes from a search-result excerpt of the cited page rather than a full read, so verify it before quoting externally.

---

## 0. Bottom line for a founder

1. **Distance beats algorithms.** Remote or tabletop microphones near the talker give the largest measured SNR gains of any approach: **+10 to +22 dB** versus hearing-aid microphones alone. Wearable arrays give about **+2 to +10 dB**. Single-device DNN denoising adds about **+3 to +6 dB** on top of directionality in commercial products (Phonak claims up to 10 dB against an omni baseline).
2. **The latency budget is form-factor dependent.**
   - **Open-ear** devices (glasses, neckband speakers) mix processed sound with the direct acoustic path. They need about **≤5–6 ms** to avoid comb filtering (Stone & Moore 2008), and ideally <1 ms for best quality.
   - **Occluded/ANC** devices tolerate about **10–20 ms**. UW's TSH system ran at 18 ms end-to-end, and Stone & Moore 1999 put the disturbance threshold at ~20 ms.
   - **Remote-mic streaming** tolerates more when the remote signal dominates. Bluetooth-LE phone streaming arrives about 20 ms after the acoustic signal, which only works in very loud rooms.
   - Implication: our finding that single-mic DNNs fail at ≤16 ms matches the field. The products that work at low latency lean on **spatial filtering (more mics, bigger aperture)** plus a DNN post-filter, or they **move the mic closer to the mouth**.
3. **TSE is the frontier, and causal versions now exist at 8–12 ms.** UW TSH: 7.0 dB SI-SNRi at 12 ms algorithmic latency on an embedded CPU. That is well below our offline +16 dB. Expect roughly half the offline gain once causal.
4. **The most defensible product wedges** suggested by the evidence (my inference):
   - **(a) A tabletop or centerpiece array** that streams to open-ear or earbud wearables. This gets the remote-mic SNR win, can run heavy TSE on mains or larger-battery compute, and serves several listeners.
   - **(b) Glasses or a neckband with a large-aperture array** (6–16 mics), with an MVDR/binaural beamformer plus a light DNN post-filter at ≤5 ms.
   - **(c) Hybrid:** wearable array plus phone or table node, using the wireless link for look-ahead.

---

## 1. Open-ear hearing glasses and smart glasses

### Nuance Audio (EssilorLuxottica), 2025; Nuance Audio Plus, Sep 2026
- **How it works:** six microphones in the frame drive frontal beamforming plus noise reduction. Two directional open-ear speakers sit in the temples. FDA-cleared OTC hearing aid for perceived mild-to-moderate loss. It has "Frontal" and "All-around" modes.
- **Best measured benefit [M]:** Western University (Folkeard et al., *Front. Audiol. Otol.*, May 2026; n=21, mean age 75; manufacturer-funded, independent data collection):
  - Matrix SRT50 improved **2.21 dB** (−8.34 → −10.55 dB SNR).
  - CST keyword scores at −3 dB SBR rose **34% → 63%**; at 0 dB SBR **61% → 81%**.
  - Listening effort dropped 1.4–1.8 points on a 7-point scale.
  - The paper puts prior studies at **2.2–4.4 dB** benefit, comparable to directional open-canal hearing aids (2.6 dB).
- **Plus (2026):** still six mics and two open-ear speakers. Claims "stronger amplification, better clarity in noise," better own-voice perception, about 10 h battery. No new dB figures published [C].
- **Latency:** not published (gap).
- **Maturity:** shipping, FDA-cleared OTC.
- **Constraints:** open ear means comb filtering and limited gain. It only helps for talkers in front.
- Sources:
  - https://media.nuanceaudio.com/cms/caas/v1/media/82480/data/a970f3114db31ccb5178b7a0bfe628aa/westernuniperformance.pdf
  - https://www.prnewswire.com/news-releases/essilorluxottica-unveils-nuance-audio-plus-the-next-generation-of-hearing-glasses-302891793.html
  - https://hearinghealthmatters.org/hearing-technologies/2026/nuance-audio-plus-otc-hearing-glasses

### Meta Ray-Ban / Oakley Meta "Conversation Focus" (announced Sep 2025; early access Dec 2025, v21)
- **How it works:** the glasses' mic array, beamforming and "real-time spatial processing" amplify the person in front. Output goes through the open-ear speakers, and the voice sounds "slightly brighter." Amplification is adjustable by swiping the temple.
- **Benefit:** **no published dB or latency [C].** Meta says it is not a medical device. Usage was capped at **3 h/month free** from July 2026 (UC Today report, not opened). This suggests real compute or battery cost (inference).
- **Maturity:** shipping in the US/Canada as a consumer feature.
- Sources:
  - https://about.fb.com/news/2025/12/updates-to-meta-ai-glasses-conversation-focus-spotify-integration/amp
  - https://www.meta.com/blog/connect-2025-day-one-keynote-ai-glasses-ray-ban-display-neural-band-metaverse-news/
  - https://www.uctoday.com/immersive-workplace-xr-tech/meta-ray-ban-smart-glasses-conversation-focus-limit (excerpt)

### Classic eyeglass arrays: Varibel, Soede/Delft, Widrow
- **Varibel hearing glasses [M]:** a four-mic end-fire array on each temple.
  - Directional benefit **5.3 dB** in asymmetric-fit mode, **6.3 dB** in fully directional bilateral mode.
  - Anterior (temple) mics beat above-pinna mics by 2.6 dB (Boone-group study, 2010) (excerpt).
  - A patent cites a weighted directivity index of **8.2 dB** (excerpt).
- **Soede et al. 1993 (Delft) [M]:** eyeglass arrays improved SRT by about **7 dB** versus an omni mic in diffuse noise (excerpt).
- **Takeaway:** the long array aperture on a temple buys about 2–4 dB over behind-ear directionality. Nuance's measured 2.2 dB is at the low end, likely because of OTC presets, an open fit and older subjects (inference).
- Sources:
  - https://pubmed.ncbi.nlm.nih.gov/21047292
  - https://patents.google.com/patent/EP2320680A2/en
  - https://pubmed.ncbi.nlm.nih.gov/8263830

### Other 2025–2026 launches
- **Cearvol (CES 2026):** Liberte open-ear hearing aid and Lyra smart hearing glasses. Claims "up to 20 dB noise reduction" for its NeuroFlow AI 2.0 platform [C, vendor; not a speech-in-noise SNR benefit]. https://hearingreview.com/hearing-products/hearing-aids/otc/cearvol-showcases-new-ai-powered-hearing-devices-at-ces-2026
- **Bone conduction:** I found no 2025–2026 bone-conduction conversation-in-noise product with measured benefit. Gap; not searched deeply.
- **Bose open-ear:** I found no Bose open-ear hearing-enhancement product. Gap.

### Apple AirPods Pro 2/3: comparison point, in-ear
- **Features:** Hearing Aid feature (FDA-authorized OTC software, 2024), Conversation Boost (beam toward the talker in front), automatic Conversation Boost (iOS 26), and Live Listen (iPhone as remote mic).
- **Benefit:** Apple publishes **no dB SNR benefit or latency** in its white paper [C].
- **Note:** this is occluding plus ANC, so a different latency regime from open-ear.
- Sources:
  - https://www.apple.com/health/pdf/Hearing_Health_Features_on_AirPods_Pro_2_October_2024.pdf
  - https://support.apple.com/en-us/102479

---

## 2. Beamforming wearables: head, chest/neck and binaural arrays

### Neck/chest arrays (relevant to the neckband form factor)
- **Widrow/Luo "Hearingpoint" necklace array (2003) [M]:**
  - Six mics in a planar V on the chest, beam about 60°, link to hearing aids by telecoil neck loop.
  - HINT SNR improvement **>10 dB on average** (n=9). Word scores rose about **25% → 75%**.
  - Sidelobes sit 20–35 dB down. Feedback drops about 15 dB because the mics are far from the receivers.
  - The user aims their body at the talker.
  - https://isl.stanford.edu/~widrow/papers/j2003microphonearrays.pdf
- **Radiant Beam Array (six-mic broadfire necklace, Widrow patent) [M]:** best mean HINT improvement **7.5 dB** (speech 0°, noise 180°, sharp beam) (excerpt). https://www.audiologyonline.com/articles/clinical-results-with-six-microphone-1285
- **Etymotic/Delft assistive array (Ear & Hearing 2004):** a fixed delay-and-sum array. It is a precursor of today's table and neck arrays. https://www.phonak.com/content/dam/phonak/en/evidence-library/journal-article/Better_Speech_Perception_in_Noise_With_an_Assistive_Multimicrophone%20Array_for_Hearing_Aids.pdf
- **Consumer neck devices today:**
  - BeHear PROXY: a neck speaker plus personal amplifier with no beamforming data [C].
  - Generic "neckband hearing amplifiers" with remote mics [C].
  - Bose SoundWear and Sony neck speakers are playback speakers. I found no conversation-enhancement mode or data (not verified).
  - **White space:** a modern neckband pairing a Widrow-class array (6–8 mics, chest aperture about 15–20 cm) with an MVDR+DNN and open-ear neck speakers or earbuds appears unoccupied commercially (inference).
  - https://wearandhear.com/products/behear-proxy-neck-speaker-personal-amplifier

### Binaural beamformers and spatial-cue preservation
- **Binaural vs bilateral [M]:**
  - Binaural beamforming improved SRT about **6 dB**, bilateral about **4 dB**.
  - Individual range: 1.9–9.9 dB binaural, 0.3–7.4 dB bilateral (simulated classroom, HI listeners) (excerpt).
  - Commercial binaural beamformer: **5.0 dB** versus omni (excerpt).
  - Sources: https://pmc.ncbi.nlm.nih.gov/articles/PMC8744079 ; https://www.audiologyonline.com/articles/speech-recognition-benefit-obtained-from-14338
- **Trade-off:**
  - A binaural MVDR preserves the target's ITD/ILD but collapses the cues of noise and interferers.
  - Variants that preserve cues partially (MVDR-IC, BLCMV, BMVDR-RTF) restore spatial quality with little intelligibility loss (Gössling et al. 2020) (excerpt).
  - Sources: https://pmc.ncbi.nlm.nih.gov/articles/PMC7225838 ; https://pub.dega-akustik.de/DAGA_2026/files/upload/paper/395.pdf
- **Real-time binaural DNN beamformer (GCFSnet, Westhausen et al. 2024) [M]:**
  - 4 mics (2 per ear), 2 ms frames, 168k weights, sized for a hearing-aid chip.
  - With spatial maskers, SRT80 improved **5.9 dB vs unaided** and **1.3 dB better than ADM**. It beat the binaural MVDR.
  - In diffuse cafeteria noise it was **no better than classic ADM/MVDR**.
  - Algorithmic latency 5.4 ms (14.1 ms total including lab audio hardware).
  - Assumes a zero-delay ear-to-ear link.
  - **This is close to our 4-mic MVDR finding:** a neural spatial filter wins with discrete interferers, not in diffuse babble.
  - https://arxiv.org/pdf/2405.01967

### Gaze- and head-steered beamforming
- **Kidd et al. "Visually Guided Hearing Aid" (VGHA, BU, 2013– ) [M, lab]:**
  - A head-band array (reported as 4×4 = 16 mics (excerpt)) steered by an eyeglass eye-tracker.
  - Beamforming benefits held up in dynamic tasks where the target moved, for both normal-hearing and hearing-impaired listeners.
  - A simulated beamformer gave 8 dB (wide) or 12 dB (narrow) noise attenuation in a gaze-vs-head study (excerpt).
  - Lab prototype only.
  - Sources: https://pubmed.ncbi.nlm.nih.gov/23464129 ; https://pubmed.ncbi.nlm.nih.gov/29252977 ; https://pmc.ncbi.nlm.nih.gov/articles/PMC6763936 ; https://www.optometrytimes.com/view/visually-guided-hearing-aid-hearing-in-plain-sight
- **Related work:**
  - Hart et al. 2009 (eye-gaze steering) is cited in the above.
  - "Cochlearity" (UC Davis 2018): an open-source eight-mic glasses array on Android with gaze steering. https://millerlab.faculty.ucdavis.edu/wp-content/uploads/sites/240/2018/07/AndersonEtAl_IEEE_2018preprint.pdf
- **Maturity [S→M]:** proven in the lab. Eye tracking in commercial glasses (Meta Ray-Ban Display, etc.) makes this newly plausible (inference).

### EEG / attention-decoding ("neuro-steered") hearing aids [S]
- **CNN locus-of-attention decoding:** about **81% median accuracy with 1–2 s windows** (64-ch lab EEG). https://pmc.ncbi.nlm.nih.gov/articles/PMC8143791
- **Real-time CCA hearing-instrument control (J. Neural Eng. 2025):** 70–80% accuracy at **6–8 s** windows. https://iopscience.iop.org/article/10.1088/1741-2552/ad867c
- **Fully in-ear EEG:** **61% at 60 s** windows. https://arxiv.org/html/2505.14478v1
- **Verdict:** seconds-scale switching latency and wet/dense electrodes. Years from product. Gaze or a "look once" enrollment is the practical selector today.

---

## 3. Low-latency neural enhancement and TSE for hearables

| System | Mics / platform | Benefit | Latency | Status |
|---|---|---|---|---|
| **UW Target Speech Hearing / "Look Once to Hear"** (CHI 2024) | 2 binaural mics on Sony ANC headset; Orange Pi 5B CPU | **7.01 dB SI-SNRi** with noisy 5 s enrollment (clean enrollment 7.40 dB); MOS overall 2.09→3.40 | 8 ms chunk + 4 ms look-ahead = **12 ms algorithmic**; 6.24 ms compute; **18.24 ms end-to-end** | Research, code open [M] |
| **Semantic Hearing** (UIST 2023) | binaural, phone | **7.17 dB** average across 20 sound classes | **6.56 ms** runtime per 10 ms chunk (iPhone 11) | Research [M] (excerpt) |
| **Sound Bubbles** (Nature Electronics, Nov 2024) | up to **6 mics** on headset; embedded CPU | suppresses sources outside a 1–2 m radius by **49 dB** | 8 ms chunks processed in **6.36 ms** | Research [M] (project-page excerpt) |
| **ClearBuds** (MobiSys 2022) | 2 synchronized earbuds + iPhone | separation SI-SDR gains up to ~6.9 dB in background-voices task (excerpt) | 21.4 ms runtime, **109 ms end-to-end** (telephony, not live hearing) | Research [M] |
| **Phonak Audéo Sphere Infinio "Spheric Speech Clarity"** (Aug 2024) | 2 mics/ear + dedicated **DEEPSONIC** DNN chip | **5.9 dB** vs open ear (default; beats competitors by 2.6–3.7 dB); **up to 10 dB** vs omni with no NR; DNN alone adds **5.8–6.9 dB** at any speech angle; 2× odds of understanding speech; tolerates 2.9 dB worse SNR at equal effort | **not published (gap)** | Shipping Rx hearing aid [V] |
| **Phonak Roger On Sphere** (remote mic, mid-Nov 2026) | Roger remote mic + DNN | **+3 dB** over the previous Roger On | "low-latency" (no figure) | Launching [V] |
| **Oticon Intent / Own SI (DNN 2.0)** (2024–25) | hearing aid | "up to 12 dB suppression of unwanted sounds"; Own SI up to **5.4 dB** SNR enhancement | n/a | Shipping [V] |
| **Starkey Edge AI** (2025) | hearing aid with DNN | brochure chart of SNR improvement at 0/−3/−6 dB babble; numbers not extracted | n/a | Shipping [V] |
| **GCFSnet** (Oldenburg 2024) | 4 mics binaural | SRT80 −5.9 dB vs unaided | 5.4 ms algorithmic | Research [M] |
| **Google sub-ms SE** (Dementyev et al. 2024) | min-phase FIR, low-power DSP | modest SE (see paper) | **0.32–1.25 ms algorithmic, 3.35 ms end-to-end**, 376 MIPS | Research [M] (abstract) |
| **RT-Tango** (2026) | distributed binaural DNN + SDW-MWF | competitive | 8 ms, 0.49 MMAC/frame | Research (excerpt) |
| **Causal TSE for HI listeners** (2025, PMC12340209) | speaker-conditioned, causal | subjective benefit with HI listeners | low-ms (exact value not extracted) | Research |

Sources:
- https://arxiv.org/html/2405.06289v3
- https://tsh.cs.washington.edu/
- https://arxiv.org/pdf/2311.00320
- https://soundbubble.cs.washington.edu/
- https://www.washington.edu/news/2024/11/14/ai-headphones-sound-bubble-noise-cancelling
- https://homes.cs.washington.edu/~gshyam/Papers/clearbuds.pdf
- https://hearingreview.com/hearing-products/hearing-aids/speech-in-noise/leveraging-deep-neural-networks-in-hearing-aids
- https://hearingreview.com/hearing-products/amplification/assistive-devices/phonak-launches-roger-on-sphere-an-ai-powered-remote-microphone-with-real-time-speech-separation
- https://www.oticon.com/professionals/campaigns-b2b/intent/intent-technology
- https://assets-ue.cas.dgs.com/-/media/oticon-us/main/download-center/own-si/15500-0373-own-si-research-brief.pdf?la=en&rev=D17F
- https://arxiv.org/abs/2409.18239
- https://arxiv.org/pdf/2607.01834
- https://pmc.ncbi.nlm.nih.gov/articles/PMC12340209/

**Reading against our lab results:**
- TSH's causal TSE gets about 7 dB at 12 ms with 2 mics.
- Our offline TSE gets +16 dB.
- The gap of roughly 9 dB is the price of causality and small compute.
- Phonak's DNN gain is about 6 dB, but it sits on top of fixed directionality and is measured on occluded KEMAR, where latency is less constrained.
- None of these validate a **single-mic, open-ear, <5 ms** DNN. That is consistent with our negative result.

**Compute and power budgets:**
- **GreenWaves GAP9** (RISC-V, 22FDX): **330 µW/GOP**. Partner demos: AI-ANC at 1.5 mW per channel, spatial audio at 1.8 mW total.
  - https://www.eenewseurope.com/en/greenwaves-stresses-gap9s-hearing-credentials
  - https://www.eetimes.com/greenwaves-shows-off-advanced-audio-demos
- **Syntiant NDP100:** <200 µW always-on (keyword-class models, not full SE). https://www.syntiant.com/press-release/syntiant-brings-speech-interfaces-to-the-edge-with-new-ultra-low-power-neural-decision-processors/
- **Back-of-envelope (inference):**
  - TSH's streaming TF-GridNet at about **4.6 GMAC/s** would need roughly 1.5–3 mW on GAP9 at its quoted efficiency (≈9 GOP/s × 330 µW). That is plausible for glasses or a neckband, marginal for an in-ear hearing aid.
  - GCFSnet-class models (~0.1–0.5 MMAC/frame) fit hearing-aid chips.

**Latency tolerance (perceptual):**
- **Open-fit:** **5–6 ms** acceptable, Stone, Moore et al. 2008. https://pubmed.ncbi.nlm.nih.gov/18469715
- **Optimal quality** needs about 0.5 ms; modern hearing aids target ≤10 ms. https://pmc.ncbi.nlm.nih.gov/articles/PMC11638989/
- **Occluded:** disturbing beyond about 20 ms (Stone & Moore 1999). https://pubmed.ncbi.nlm.nih.gov/10386846
- **Own-voice production** is affected only beyond 30 ms (2002). https://pubmed.ncbi.nlm.nih.gov/12195175

---

## 4. Remote-mic, tabletop, phone and distributed approaches

### Remote / table microphones streaming to the listener [M]
- **Typical SNR gain:**
  - Remote mics improved SNR **16–22.7 dB** versus omni hearing aids (Rodemerk & Galster 2015, four wireless protocols) (excerpt).
  - Earlier FM work: **14.2–16.7 dB** (excerpt).
  - LE Audio literature cites 15–20 dB for direct delivery (excerpt).
  - For context, severe-to-profound loss needs +15–25 dB SNR to match normal hearing.
  - Sources: https://canadianaudiologist.ca/the-benefit-of-remote-microphones-with-four-different-wireless-protocols-feature ; https://pmc.ncbi.nlm.nih.gov/articles/PMC8072043/ ; https://spectrum.ieee.org/bluetooth-low-energy-audio
- **Phonak Roger clinical benchmark (2026) [V]:** at **−10 dB SNR**, hearing aid alone scored **12%** and HA+Roger **73%**. Benefits of +25 to +59 points across studies (excerpt). https://www.phonak.com/content/dam/phonak/en/evidence-library/field-studies/PH_FieldStudyNews_ClinicalBenchmarkingofRemoteMicrophonePerformanceinAdultswithHearingLoss.pdf
- **Roger Select/Pen in the table center (simulated restaurant, +5 to −10 dB SNR):** up to **61%** (Select) and **45%** (Pen) better recognition than HA/CI alone (excerpt). https://www.phonakpro.com/content/dam/phonakpro/gc_hq/en/resources/evidence/field_studies/documents/fsn_roger_group_setting_speech_recognition_benefit_en.pdf
- **Roger Table Mic (2016, n=18) [V]:** significant gains at 3.0 and 4.5 m. The fetched paper gives no dB numbers. The table mic auto-selects the active talker, and several can be networked. https://www.phonakpro.com/content/dam/phonakpro/gc_hq/en/resources/evidence/field_studies/documents/fsn_roger_improved_speech_recognition.pdf
- **Adaptive gain matters:** in a bench comparison, only Roger beat a 20 cm reference mic in high noise. One competitor fell to 0% at 80 dBA (vendor study). https://www.phonak.com/content/dam/phonak/en/evidence-library/field-studies/PH_FieldStudyNews_BeyondWirelessProtocolsRogerBenchmark_210x297_EN_028-2814-02.pdf
- **Roger On Sphere (Nov 2026):** the first DNN-in-remote-mic product, +3 dB over its predecessor [V]. This validates "put the AI at the table node."

### Phone as remote mic (Live Listen, apps)
- **UT Dallas SHARP-2 app (2020) [M]:**
  - iPhone on the table about 1 ft from the talker, streaming to MFi/MFA hearing aids.
  - Benefit of **+22 points** (HI) and **+29–34 points** (normal hearing) word recognition.
  - **Latency caveat:** the Bluetooth-LE stream arrives about **20 ms after** the acoustic sound. They needed circumaural headphones to mask the direct path. Real-world use works only when noise masks the early arrival.
  - https://pmc.ncbi.nlm.nih.gov/articles/PMC7744168
- **Apple Live Listen:** documented but no published latency or benefit. https://support.apple.com/en-us/102479
- **Bluetooth SIG:** echo becomes a problem beyond about 30–40 ms delay. LE Audio plus Auracast enables phone-as-mic and one-to-many broadcast (GN Multi Mic is Auracast-capable). https://www.bluetooth.com/blog/introducing-le-audio-the-use-cases/ ; https://www.gnhearing.com/en/products/auracast-hearing-aids

### Distributed arrays across friends' phones / "smart table" [S→M]
- **UIC Listening Technology Lab (Corey et al., IWAENC 2022):**
  - Each diner puts their phone on the table and wears earbuds or hearing aids.
  - Adaptive crosstalk cancellation removes other diners' voices and own-voice echo from each phone.
  - Adaptive binaural spatialization re-imposes the spatial cues.
  - Demoed with real phones. **No dB in the blog.** They state **Bluetooth is too slow** for real-time listening today.
  - Follow-up work covers cooperative per-table nodes in a multi-table restaurant.
  - https://listeningtech.lab.uic.edu/news-stories/iwaenc2022-conversation ; https://listeningtech.lab.uic.edu/news-stories/cooperative-node-specific
- **Ad-hoc arrays for ASR:** Microsoft PickNet does real-time channel selection across multiple phones, with WER gains over block-online beamforming and a single distant mic. https://arxiv.org/abs/2201.09586
- **Communication-cost-aware mic selection** (Casebeer et al. 2021): streams more mics only when SNR is low. https://arxiv.org/abs/2011.07348
- **Constraints:**
  - Clock sync (ClearBuds managed <64 µs between earbuds).
  - Wireless latency and jitter.
  - Privacy and consent from the other people at the table.
  - Battery.
- **Smart table / centerpiece / lamp:** I found **no commercial product** or study with measured hearing benefit beyond Roger Table Mic-class devices. White space [S].

---

## 5. Predictive and anticipatory ideas

- **Future-frame prediction to cut algorithmic latency [M]:**
  - Predict the next enhanced STFT frame from past frames only. With 50% overlap this gives zero algorithmic latency, leaving only buffer latency.
  - Wu & Braun (ICASSP 2025) compared this against asymmetric and learnable windows under a <5 ms budget.
  - Also used in the iNeuBe-X Clarity CEC2 entry to meet a 5 ms limit.
  - The gain is about one hop (a few ms), not tens of ms.
  - Sources: https://arxiv.org/pdf/2409.10358v1 ; https://arxiv.org/html/2302.07928v1
- **Wireless look-ahead ("faster than sound") [M for ANC, S for speech enhancement]:**
  - A remote mic radios the reference signal to the processor ahead of the acoustic wavefront (radio ≫ 343 m/s).
  - This gives N samples of look-ahead (WLANC, NTU 2024) (excerpt).
  - For a table node 1 m from a noise source and about 1 m from the listener, acoustic travel is about 3 ms per metre. That is real look-ahead budget, enough to run heavier TSE (inference).
  - https://arxiv.org/pdf/2405.12496
- **Speech prediction in ANC headphones (IEEE 2025):** frames optimal speech ANC as a non-causal prediction problem (excerpt). https://ieeexplore.ieee.org/document/11123733
- **Anticipatory gain control / traffic-noise event prediction:** I found **no published hearing-device work** forecasting traffic or transient noise events to pre-adjust gain. Oticon Intent's head- and body-motion "4D sensors" adapt support across a **5 dB output-SNR** range by inferred intent. This is the closest commercial analogue (context-predictive, not signal-predictive) [V]. https://assets-ue.cas.dgs.com/-/media/oticon-us/main/download-center---myoticon---product-literature/intent/pi/155000264--rm--h1-2024--intent-product-guide--dc-0224v1.pdf?la=en&rev=7A1A
- **"Negative latency" by forecasting speech waveforms beyond about 1 frame [S]:** no evidence it preserves intelligibility. Speech is predictable at the phoneme level only over a few ms of waveform. Treat as speculative.

---

## 6. Cross-form-factor comparison

| Form factor | Mics / aperture | Best measured SNR benefit | Latency regime | Maturity | Key constraint |
|---|---|---|---|---|---|
| Open-ear glasses (Nuance) | 6 mics, ~temple length | **+2.2 to 4.4 dB** SRT [M] | needs ≤5–6 ms (open fit) | shipping OTC | comb filter, low gain, front-only |
| Eyeglass end-fire arrays (Varibel, Delft) | 4/temple | **+5.3 to 7 dB** [M] | same | discontinued / legacy | aesthetics, front-only |
| Smart glasses (Meta) | multi-mic array (count not published) + AI | no data [C] | unknown | consumer feature, time-capped | not medical |
| Head-band gaze-steered (VGHA) | 16 mics | ~8–12 dB attenuation simulated; benefits kept in dynamic tasks [M] | real-time | lab | needs eye tracker |
| Neck/chest array (Widrow) | 6 mics, chest | **+7.5 to >10 dB** [M] | real-time (analog/telecoil) | legacy product | body-aim, link to ear |
| Binaural hearing-aid beamformer | 4 mics | **+4 to 6 dB** [M] | <10 ms | shipping | cue loss |
| DNN hearing aid (Phonak Sphere) | 4 + DNN chip | **+5.9 dB vs open ear; up to 10 dB vs omni** [V] | undisclosed | shipping Rx | price, power |
| Causal TSE headset (UW TSH) | 2 + ANC | **7 dB SI-SNRi** [M] | 12 ms algo / 18 ms e2e | research | needs occlusion/ANC; enrollment |
| Distance-based (Sound Bubble) | 6 + ANC | **49 dB** outside-bubble suppression [M] | 8 ms chunks | research | headset form |
| Remote / table mic (Roger) | 1–3 near talker | **+14 to 22.7 dB** [M] | low-ms proprietary radio | shipping | talker must wear/face mic; cost |
| Phone on table (SHARP-2, Live Listen) | phone mics | **+22 to 34 points** words [M] | BLE ≈20 ms behind acoustic | app-level | latency vs direct sound |
| Distributed phones (UIC) | N phones + earbuds | demo, no dB | BT too slow today | research | sync, latency, consent |
| EEG-steered | EEG + array | 61–93% decode accuracy; no SNR | 0.5–60 s decisions | research | electrodes |

---

## 7. Gaps and things I could not establish
- I found no published latency for Phonak Sphere, Nuance Audio/Plus, Meta Conversation Focus or Apple Conversation Boost/Live Listen.
- I found no Meta Conversation Focus SNR data.
- I found no published benefit numbers for Nuance Audio Plus.
- I found no bone-conduction or Bose/Sony neck-speaker conversation-enhancement product with data.
- I could not open the Kidd VGHA full text because PMC blocked automated access. Its array size and dB figures come from secondary excerpts.
- Several numbers are marked (excerpt): Varibel, Soede, RBA, binaural vs bilateral, remote-mic 16–22.7 dB, EEG CNN, Sound Bubble specs, Semantic Hearing, Roger clinical benchmark, WLANC. Verify them before external use.
- I found no work on traffic or transient noise-event forecasting for hearing devices.
