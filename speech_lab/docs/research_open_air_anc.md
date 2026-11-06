# Reducing perceived noise in a small open-air region without earbuds
*Research brief for the "hear your friends in loud bars / restaurants / streets" product. Compiled 2026-10-18. Every number below comes from a source I opened unless it is marked **[theory]** (standard acoustics I worked out myself), **[excerpt]** (seen only in a search snippet or vendor copy, not checked against the full text), or **[speculative]**.*

---

## 0. Bottom line

1. **Physics caps open-air ANC for speech-band noise.** A local "zone of quiet" (≥10 dB of reduction) is only about λ/10 across: about **34 cm at 100 Hz, 6.8 cm at 500 Hz, 3.4 cm at 1 kHz, 1.7 cm at 2 kHz** [theory; the 3.4 cm @ 1 kHz figure is stated in Elliott et al. 2018 and Lam et al. 2020]. Speech intelligibility sits mostly between 500 Hz and 4 kHz. To quiet a 1–4 kHz zone at someone's ear without earbuds, you need something right next to the ear, plus head tracking, plus lookahead.
2. **Restaurant babble is close to the worst case for ANC.** It comes from many uncorrelated sources in a diffuse field. One upstream reference mic cannot predict it, and deep-learning noise prediction loses performance quickly beyond about 6 ms of lookahead, even in simulation (Zhang, Pandey & Wang 2023). Published ANC results on real multi-source babble at a person's head, without earbuds, are close to nil.
3. **Open-air ANC is real, but only below about 1 kHz and in contained geometries.** Lab results: about 20 dB at a headrest from 300 Hz to 1 kHz with head tracking (Elliott 2018). About 10 dB across a whole room through an open window, 500 Hz–1 kHz, using 24 speakers (Lam 2020). In production: about 3 dB of road noise in cars (Hyundai/Harman RANC 2020) and "up to 10 dBA, 30–1000 Hz" from Silentium's headrest "Quiet Bubble". These numbers suit bass and rumble (bar music, traffic, HVAC), not chatter from the next table.
4. **The lever that works for "hearing friends" is raising SNR, not removing noise.** That means picking up the talker close to the mouth (table or worn mic arrays) and delivering their voice to the listener's ear, as Phonak Roger, Orsana, TableTalk and hearing glasses do. Remote mics typically take listeners from about 27% to 83% speech understanding in noise [excerpt, Phonak]. The unsolved part is delivering that voice **without earbuds** and **without making the room louder**, since amplification feeds the Lombard spiral. Near-field neck or chair speakers, head-tracked beamforming, and parametric beams are the candidates.
5. **My recommendation for form factor:** a **shared table hub** (beamforming mic array, AI speech separation, voice-lift) paired with **per-person near-ear delivery** (neckband near-field array, chair-back or headrest array, or open-ear glasses). Bass-band ANC in a chair-back or booth is optional. The ANC part of that stack is incremental. The SNR-delivery part is the product.

---

## 1. The numbers that set the constraints

| Quantity | Value | Source |
|---|---|---|
| Zone of quiet (≥10 dB), diffuse field | ≈ λ/10 diameter; 3.4 cm at 1 kHz | Elliott, Jung & Cheer 2018, Sci Rep https://pmc.ncbi.nlm.nih.gov/articles/PMC5876390 |
| λ/10 by frequency | 100 Hz → 34 cm; 250 Hz → 13.6 cm; 500 Hz → 6.8 cm; 2 kHz → 1.7 cm; 4 kHz → 0.85 cm | [theory] c = 340 m/s |
| Head movement that breaks a fixed ZoQ | ~5 cm | Elliott 2018 |
| Headphone ANC timing budget | ≈ 30 µs (ref mic to speaker < 1 cm) | Shen et al., MUTE, SIGCOMM 2018 https://sens.epfl.ch/documents/papers/sigcomm18mute.pdf |
| Lookahead per metre of path difference | ≈ 3 ms/m (sound vs. RF) | MUTE 2018 |
| Causality rule | T_ANC ≤ T_primary − T_secondary | Zhang, Pandey & Wang 2023 https://haozhang6720.github.io/doc/papers/ANC_journal_2023.pdf |
| Car RANC budget | noise path ≈ 9 ms, DSP 2 ms | Hyundai https://www.hyundaimotorgroup.com/en/story/CONT0000000000090151 |
| Restaurant occupied levels | 45–82 dBA in 10 eating places (Hodgson 2007); 63–77 dBA LAeq in 5 Omaha restaurants (Paine, UNL); instantaneous 58–97.5 dBA in Orlando (CDC summary) | https://pubmed.ncbi.nlm.nih.gov/17471719 ; https://digitalcommons.unl.edu/cgi/viewcontent.cgi?article=1069&context=archengdiss ; https://stacks.cdc.gov/view/cdc/223002/cdc_223002_DS1.pdf |
| Lombard slope | speech level rises 0.5–0.7 dB per dB of noise above ~45 dB | Rindel 2012 https://odeon.dk/pdf/C116-BNAM_2012_Rindel_29.pdf |
| Disturbance / vocal-effort onset | 52.2 dBA (disturbance), 57.3 dBA (vocal effort rises) | Bottalico 2018 via UIUC https://www.shs.illinois.edu/2019/07 |
| Rindel "acoustic capacity" | past capacity, ambient > ~71 dB means communication is "insufficient" | Rindel EuroNoise 2015 https://odeon.dk/pdf/C127-Keynote%20EuroNoise%202015%20Rindel.pdf |

**Implication [theory]:** in a 75–80 dBA bar the Lombard effect pushes conversational speech up, but SNR at a listener 1 m away still ends up around −5 to +5 dB. Normal-hearing listeners need roughly −6 to −8 dB SNR for 50% sentence recognition in babble. (Mild-to-moderate hearing-loss adults in the Nuance study scored −8.3 dB unaided on a matrix test; that is a different population.) Hearing-impaired listeners need far more: 15–25 dB SNR for severe-to-profound loss [excerpt, Phonak/Baquis]. Each 3–6 dB of SNR gain is worth a lot of intelligibility on the steep part of that curve.

---

## 2. Open-air / free-field ANC

### 2a. Local ANC (headrests, seats): virtual sensing and the remote-microphone technique
- **How it works.** Loudspeakers in a headrest or seat cancel noise at "virtual" ear positions. Pressure at the ear is estimated from fixed monitoring mics (the remote-microphone technique, RMT). Optional head tracking switches the ear-position filters as the head moves.
- **Best measured result.** **About 20 dB broadband, 300 Hz–1 kHz, at the ears of a dummy head.** Setup: 2 headrest speakers, 4 monitoring mics 18–27 cm from the head, Kinect head tracking across 20 grid positions 5 cm apart, 3 kHz sampling, total plant delay about 1.3 ms. Without head tracking, about 10 dB only up to about 600 Hz once the head moved 14 cm. Front-arriving noise needed a 0.7 ms modelling delay to stay causal. (Elliott, Jung & Cheer, Sci Rep 2018, https://pmc.ncbi.nlm.nih.gov/articles/PMC5876390.) Important caveat: the reference signal came straight from the noise source, with a single source in an anechoic room. The authors call this idealised.
- **Aircraft-seat virtual sensing (2023).** A functional-link neural network with linear pressure prediction grew the quiet zone from 10 × 40 cm to **25 × 50 cm**. Some harmonics were reduced by about 20 dB, for tonal engine noise (https://link.springer.com/article/10.1007/s42417-023-01090-5).
- **EU business-jet seat ANC target.** 15 dB, with at least 10 dB at the ~110 Hz engine tones, in a ≤ 9 kg system (CORDIS H2020 717089, https://www.cordis.europa.eu/project/id/717089/reporting/es).
- **Commercial headrest.** Silentium "Quiet Bubble": **"up to 10 dBA, 30–1000 Hz"** from a speaker array in a headrest (vendor claim, https://www.silentium.com/technology-2/quiet-bubble).
- **Maturity.** Lab to pre-production for headrests. In cars, cabin-wide low-frequency ANC is in production (below).
- **Constraints.** Noise must be correlated with a reference, so it works for tonal or structure-borne noise and fails for babble. Only below about 1 kHz. The head must stay within about 5 cm of the trained positions, or be tracked.
- **Form factors.** Chair-back or headrest, high-back restaurant booth, car seat. **Realistic benefit in a restaurant chair: about 5–10 dB of reduction in music bass and HVAC hum below about 500 Hz at the seated head; little to none on speech-band babble** [inferred from the results above].

### 2b. Global or aperture ANC (windows, openings)
- **Lam, Shi, Gan, Elliott, Nishimura, Sci Rep 2020** (https://pmc.ncbi.nlm.nih.gov/articles/PMC7347542). 24 small speakers (4.5 cm) spaced 12.5 cm apart across a 0.45 × 0.93 m opening, 1 reference mic, a fixed filter trained beforehand (no error mics while running), FPGA control. Results: **7.5–10.1 dBA room-averaged reduction** for highway, MRT train and aircraft noise in the 100–1000 Hz band; **about 10 dB above 500 Hz; nothing below 300 Hz** because the speakers are small. For comparison, closing the window passively gave 12.4–13.9 dB.
- **Follow-up listening test** (anti-noise window, 2023): https://arxiv.org/pdf/2307.05533.
- **Survey table in Lam et al. 2021, "Ten questions concerning ANC in the built environment"** (https://www.sciencedirect.com/science/article/pii/S0360132321003322): window results of 4.6–10.5 dB in the 100–700 Hz band; about 15.5 dB below 300 Hz (Carme); about 3 dB on a real aircraft pass-by. It warns about "spillover", meaning noise gets louder outside the controlled zone.
- **Form factors.** Booth openings, a semi-enclosed pod or canopy aperture, a patio screen. **Speculative:** a booth or pod whose open side is an "active aperture" could take about 5–10 dB off the 300 Hz–1 kHz band of incoming sound. That requires sound entering through a defined opening, which an open table does not have.

### 2c. Automotive production systems (the most mature open-air ANC)
- **Hyundai / Harman RANC** (production from 2020 on the Genesis GV80). Accelerometers on the suspension supply a reference that leads the sound. DSP takes 2 ms against a 9 ms noise path. **Road noise reduced by about 3 dB ("up to 50%")** (https://news.harman.com/releases/releases-20200130 ; https://www.analog.com/en/signals/articles/hyundai-noise-cancellation-technology.html).
- **Bose QuietComfort RNC** (2019): same idea, using accelerometers and cabin mics (https://assets.bosecreative.com/m/3a91a2a0d7262c01/original/Bose-Introduces-).
- **Lesson.** Even with structure-borne references that arrive early, a closed cabin and a huge budget, production gains are a few dB, below a few hundred Hz.

### 2d. ANC for open-plan offices
- Real ANC deployments in offices are essentially headphones. Field studies note that ANC headphones handle noise below 1 kHz well but cancel speech less well, because speech is transient (Frontiers 2022, https://www.frontiersin.org/journals/built-environment/articles/10.3389/fbuil.2022.962462/full).
- "Noise-cancelling office chair" work exists (Treyer et al., ICSV 2016, cited in Elliott 2018). I did not find published dB figures for it.
- Office acoustics is dominated by absorption and masking (section 5).

---

## 3. Predictive / lookahead ANC

### 3a. Wireless-forwarded reference (MUTE; Shen, Roy, Guan, Hassanieh, Roy Choudhury, SIGCOMM 2018)
- **How it works.** An IoT relay mic placed toward the noise source forwards audio over a 900 MHz analog FM link. RF arrives about 3 ms per metre ahead of the sound. The lookahead lets the system run longer non-causal inverse filters, and switch filter profiles when speech starts or stops.
- **Result** (https://sens.epfl.ch/documents/papers/sigcomm18mute.pdf). With an **open ear**, MUTE cancelled across **0–4 kHz**; Bose QC35 ANC alone covers only up to about 1 kHz. Below 1 kHz MUTE beat Bose ANC by 6.7 dB. It was only 0.9 dB worse than Bose's ANC plus passive earcups (about −15 dB average). Profile switching added about 3 dB on intermittent speech. The 4 kHz ceiling came from the DSP (TMS320C6713 at 8 kHz sampling).
- **Caveats.** A single dominant source. The relay must sit between source and listener. The speaker sat right next to an error mic at the ear position of a head model, so the "hollow ear device" was never actually built. The paper's own "Personal TableTop" variant (fig. 10a) is very close to this product idea.
- **WINC (2023)** extends this to multiple sources using a network of IoT mics (https://dl.acm.org/doi/fullHtml/10.1145/3583120.3586964). I read only the summary.
- **Form factors.** A tabletop hub as the relay plus an open-ear device, or "smart noise" relays fixed to the noise sources: a speaker system in a bar could broadcast its own feed. **Speculative but promising:** a venue's music feed is a *perfect reference*, available electronically before it plays. Cancelling the house music at a chair-back or neckband is the one bar noise that is fully known ahead of time.

### 3b. Deep-learning ANC (Zhang & Wang)
- **Deep ANC (Neural Networks 2021).** A convolutional recurrent network (CRN) predicts the anti-noise and handles loudspeaker nonlinearity, in simulation (https://pmc.ncbi.nlm.nih.gov/articles/PMC8328877/).
- **Low-latency ARN (IEEE/ACM TASLP 2023)** (https://haozhang6720.github.io/doc/papers/ANC_journal_2023.pdf). Time-domain attentive RNN with 4 ms frames. With revised overlap-add plus 2 ms of prediction, **algorithmic latency was 0 ms at an average NMSE of −11.2 dB**, only 0.47 dB worse than non-causal. Predicting **babble 15 ms ahead cost only about 0.95 dB** (frame-based model). With 4 ms frames, predicting more than about 6 ms ahead caused a "considerable drop". The model was also tested on DEMAND recordings, including PRESTO (a university restaurant) and SPSQUARE (a town square).
- **Caveat.** Everything was simulated: a single reference, a single loudspeaker, one error point, a 3 × 4 × 2 m room with T60 = 0.2 s. These are point-cancellation figures, not quiet zones. The model has about 15.9 M parameters and about 5.2 GMAC per 3 s of audio.
- **Use for the product.** Mainly as a better controller inside a headrest, chair or neckband, and to stretch lookahead by a few ms. It does not change the λ/10 limit.

### 3c. Traffic pass-by and periodic noise
- Periodic noise (engines, HVAC, fans, music beats) is predictable, so causality is not the limit. Narrowband ANC works best on this class, and it is the only class where long prediction is reliable (Zhang 2023 discussion; Lam 2021).
- Traffic pass-by: the anti-noise-window studies show about 7.5–8.7 dB in the 100 Hz–1 kHz band on recorded traffic and aircraft (Lam 2020). Lam 2021 lists about 3 dB on real aircraft pass-bys. I found **no published "predict the next pass-by event" ANC at a person** in open air; the search turned up only traffic-noise monitoring work. Treat that idea as **[speculative]**.

### 3d. Babble: why ANC fails
- **Physics [theory plus sources].** ANC is feedforward: it can only cancel the part of the noise that is *coherent* with a reference. In a diffuse field, coherence between two points falls off roughly like sinc(kr). At 1 kHz it is essentially gone beyond about 17 cm [theory]. Babble also comes from dozens of independent talkers, each needing its own reference (MUTE limitations section; WINC).
- **Perception.** Babble masking is part energetic, part informational. Babble of 2–4 talkers is the most damaging (informational masking peaks). With more talkers it turns into energetic, noise-like masking (https://pmc.ncbi.nlm.nih.gov/articles/PMC3631264/ ; https://doi.org/10.1121/1.1345696 ; open-office study, about 4 talkers: https://arxiv.org/pdf/2304.12817). Partial ANC that thins a crowd into a few audible nearby talkers could **raise** informational masking. That is a non-obvious risk [inferred].
- **Results.** No published open-air (no-earbud) ANC result on real restaurant babble at a moving head that I could find. The closest are Deep ANC simulations (3b) and MUTE's single-talker cancellation (3a).

---

## 4. Personal sound zones and directional delivery

### 4a. Loudspeaker-array sound zones (acoustic contrast control, pressure matching)
- **How it works.** An array is driven so that energy is maximised in a "bright" zone and minimised in a "dark" zone (ACC), or so that target fields are matched (PM).
- **Measured contrast.** About **15 dB in practical set-ups**, which the authors say is "typically not high enough to satisfy the people inside the zones" (Lee et al., https://arxiv.org/pdf/1911.10016). In cars, 15–25 dB between front and rear seats (Cheer & Elliott), 20–40 dB below 1 kHz with 16 speakers (Choi), lower when measured with a dummy head (ICA 2019, https://pub.dega-akustik.de/ICA2019/data/articles/000245.pdf). 2025: relaxed-reverberation PM added more than 3 dB of contrast at 0–2 kHz (JASA, https://pubs.aip.org/asa/jasa/article/157/2/778/3333907). A neural PSZ testbed used 30 speakers on a 1.68 m-radius circle for 0.4 × 0.4 m zones 1 m apart (https://arxiv.org/html/2512.10375v1).
- **Neckband version.** Jeon & Choi (KAIST, JASA 2020): **3 speakers next to each ear on a neckband**, two second-order IIR filters, a broadside differential pattern that boosts near-field sound at the ear relative to the far field. Measured in simulation and experiments (I saw the abstract only; no dB numbers) (https://pubmed.ncbi.nlm.nih.gov/33379876).
- **Head-tracked beamforming and crosstalk cancellation (commercial).** Audioscenic Amphi: a camera tracks the head and two beams go to the ears. Shipped in the Razer Leviathan V2 Pro (CES 2023) and Acer SpatialLabs View (2024) (https://www.audioscenic.com/ ; http://audioscenic.com/about). It is built for spatial audio, not noise, but it proves desktop-scale ear-targeted beams are manufacturable.
- **Constraint.** Sound zones control *where your audio goes*. They do not remove ambient noise. For this product, a sound zone is the **delivery** mechanism for boosted speech, so neighbours are not disturbed and the Lombard spiral is not fed.

### 4b. Parametric / ultrasonic directional speakers
- **Holosonics Audio Spotlight.** A film transducer with a ~60 kHz carrier. AS-168iX: **85 dB SPL @ 1 kHz max; 5° beam; covers 0.5 × 1 m at 2 m**. AS-16iX: 90 dB. AS-24iX: 95 dB (https://www.holosonics.com/dakota-audio ; spec sheet https://www.touchwindow.com/mm5/graphics/00000001/holosonics/Audio_Spotlight_2025_Spec_Sheet_Catalog.pdf). Vendors position them for "quiet environments". Weak bass, and at 85–90 dB max they barely clear a 75–80 dBA bar.
- **Noveto SoundBeamer / i3DS.** Ultrasonic beams with a 3D camera form "two pockets of sound outside the ears". SDK spec: **85 ± 5 dB SPL, up to 2 m, 750 Hz–20 kHz (±6 dB), −20 dB at 1 m to the listener's side, −15 dB behind, 256 actuators, ear tracking at 2–30 fps** (https://www.noveto.com/licensing). Status: soundbars shown at CES 2024 (PR). **PitchBook lists Noveto as "Out of Business / Liquidation"** (https://pitchbook.com/profiles/company/127676-35) [excerpt; CB Insights still shows "alive"]. Treat it as defunct.
- **Single-channel multi-carrier parametric sound zones** (Zhuang et al., arXiv 2504.17440 / ICASSP 2026). Different audio is modulated onto several ultrasonic carriers so one transducer behaves like a multi-channel array. **Simulation only** (https://arxiv.org/abs/2504.17440).
- **Form factors.** Overhead lamp or pendant above a seat, centerpiece aimed upward, table edge. **Realistic:** at ~85–90 dB max, a parametric beam could add speech at about +5 to +10 dB over a 75–80 dBA background at one head position in a beam roughly 0.5 m wide at 2 m. Low-frequency speech energy (below about 500 Hz) is weak, and beams reflect off tables and faces [inferred]. I did not research ultrasound exposure limits; the risk is flagged in section 7.

### 4c. Beam-steered speech reinforcement at a table ("voice lift")
- **TableTalk Labs.** A patented wireless voice-lift device for noise above 75 dB, with directional mics and speakers that boost high frequencies (https://www.tabletalklabs.com/) [vendor copy, no numbers].
- **US Patent 12,354,619 "TableConverse"** (H. Perritt, granted 8 Jul 2025). Beamforming mics in the table perimeter (100 Hz–8 kHz), ML noise suppression, parametric speakers mounted overhead or in the table with laser seat-positioning dots, latency under 15 ms, conversation-group routing, and **bone-conduction transducers in chair headrests and seatbacks** as an alternative. Claims only, no measurements (https://patents.justia.com/patent/12354619). This is relevant prior art for any table-hub plus chair delivery design.
- **Remote/table mics plus worn receivers (the benchmark to beat).** Phonak Roger Table Mic II / Roger Select (MultiBeam, 6 beams; Roger On Sphere adds about 3 dB SNR over Roger On 3 at −15 dB SNR / 80 dB noise). Phonak field studies: 83% vs 27% speech understanding in 60 dBA noise with Roger plus hearing aids versus hearing aids alone; up to 61% improvement in simulated restaurant noise [excerpts from Phonak documents: https://www.phonakpro.com/content/dam/phonakpro/gc_hq/en/resources/evidence/field_studies/documents/PH_FSN_Roger_evaluation_Roger_NeckLoop_plus_different_HI_brands_210x297_EN_V1.00.pdf ; https://www.phonak.com/content/dam/phonak/en/evidence-library/field-studies/PH_Insight_ExpandYourWorldWithRogerOnSphere_210x280_EN_028-2933-02.pdf]. AudioTelligence Orsana: a 6 × 6 cm tabletop unit using blind source separation, LE Audio/Auracast to earbuds, crowdfunded in 2023 (https://audioxpress.com/news/audiotelligence-announces-orsana-le-audio-assistive-listening-device). These all deliver to the ear through earbuds or hearing aids. The open gap is earbud-free delivery.
- **Open-ear hearing glasses (no earbuds, closest shipping competitor).** EssilorLuxottica Nuance Audio: FDA-cleared OTC (Feb 2025), beamforming mics, open-ear speakers in the temples. A 2026 study gave **SRT50 of −10.55 dB SNR aided vs −8.34 dB unaided, about 2.2 dB better**, in mild-to-moderate hearing loss (Frontiers 2026, https://www.frontiersin.org/journals/audiology-and-otology/articles/10.3389/fauot.2026.1822238/full). The company claims "up to 29% better speech understanding" (Jan 2026 PR). Nuance Audio Plus launched 29 Sep 2026. Legato (US) came out of stealth Aug 2026 with $12M for AI voice-isolating open-ear hearing glasses (TechCrunch, https://techcrunch.com/2026/08/26/hearing-tech-startup-legato-emerges-from-stealth-with-12m-and-a-peek-at-its-ai-hearing-glasses/).

---

## 5. Masking, psychoacoustics and passive treatment

- **Sound masking.** Steady broadband noise covers intelligible speech by raising the floor. It is used in offices for privacy, typically 45–51 dBA (Acoustics 2002, https://www.acoustics.asn.au/conference_proceedings/AAS2002/AAS2002/PDF/AUTHOR/AC020071.PDF). **In a bar this works against the goal**: adding noise lowers SNR. The only relevant use is *masking neighbouring tables' intelligible speech*, which reduces informational masking and distraction, at a cost in energetic masking. It is a nuanced lever, and only for speech that is already quieter than your companions' voices [inferred].
- **Informational vs energetic masking.** Covered in 3d. The practical design rule: get the target voice spatially and spectrally distinct and a few dB louder, and informational masking falls away quickly. Different-sex and spatially separated talkers are much easier to follow (Brungart 2001).
- **Lombard feedback.** Any system that radiates amplified speech into the room raises the noise floor for everyone, and diners raise their voices by 0.5–0.7 dB for each dB. Delivery must be near-field or beamed (Rindel 2012).
- **Passive room treatment.** An absorptive ceiling (NRC ≥ 0.8) "can reduce reverberant noise levels by 10 dB" (manufacturer white paper, https://www.tombarrow.com/images/literature/silence-is-golden-optimizing-the-acoustic-environment.pdf) [vendor claim]. Rindel's capacity model (Rindel 2012, 2015) states that the occupied noise level depends on absorption per person, and that ceiling treatment alone may not be enough. Treatment works on the reverberant field and helps everyone, but it is a venue sale, not a personal device. It also reduces the Lombard spiral, so gains compound.
- **Acoustic metamaterials.** BU ultra-open silencer: about 60% open area, **94% transmitted-energy reduction (about 12 dB) in a narrow band around 460 Hz**, in a duct (Ghaffarivardavagh et al., Phys Rev B 2019, https://link.aps.org/doi/10.1103/PhysRevB.99.024302 ; band from https://www.sciencedirect.com/science/article/abs/pii/S0003682X1930845X). It is narrowband and needs a defined aperture. Possible use: ventilated booth walls or canopy panels; little use at an open table.
- **Booths and canopies.** I found no peer-reviewed dB figures for restaurant booths or table canopies. **[theory]:** a high-backed booth or canopy mostly blocks the direct path from nearby tables and adds absorption. A plausible gain is a few dB for sound arriving at head height from the side; the reverberant field is unaffected.

---

## 6. Form-factor map: what each approach can realistically do

| Form factor | Approaches that fit | Realistic benefit for the user | Maturity | Notes |
|---|---|---|---|---|
| **Tabletop hub / centerpiece** | Beamforming mic array plus AI speech separation (pickup); MUTE-style lookahead relay; voice lift | **Pickup SNR gain of about 6–15 dB for tablemates' voices** (Roger/Orsana class) [excerpt]; *still needs* an ear-delivery path | Shipping (Roger, Orsana) with earbuds | Best "brain" of the system. Can also receive the venue music feed electronically as a perfect ANC reference [speculative] |
| **Centerpiece / lamp / pendant (directional out)** | Parametric beam(s), head-tracked crosstalk cancellation (Audioscenic-style) | Speech raised by roughly **+5 to +10 dB at one head**, beam about 0.5 m at 2 m; 85–95 dB max SPL caps it in loud bars | Holosonics shipping; Noveto defunct | No ANC; weak bass; needs tracking for movement. One pendant per seat |
| **Neck-worn (neckband / collar)** | Near-field 3-speaker-per-side personal audio (Jeon & Choi), local ANC with virtual sensing below about 1 kHz, own beamforming mics or a link to the hub | Speech delivered **10–20 cm from the ear** at a modest level (low spill). ANC: maybe **5–10 dB below about 500 Hz** at the ear [speculative; λ/10 at 500 Hz is 6.8 cm and the neckband is about 15 cm from the ear] | Research prototypes; neck speakers exist as consumer products | **My top pick** for earbud-free delivery on a street or at a bar. Follows the user. No head tracking needed because the device moves with the torso; head rotation still shifts the ear |
| **Seat / chair-back / headrest** | Local ANC with virtual sensing plus head tracking; sound-zone delivery; bone conduction (TableConverse claim) | ANC: **about 10–20 dB, 300 Hz–1 kHz** (lab, idealised reference); about 10 dBA, 30 Hz–1 kHz (Silentium claim); delivery: high contrast to neighbours | Car/aircraft seats near production; restaurant chairs speculative | Requires leaning back; diners lean forward to talk, which breaks the geometry (TableConverse claims posture issues too) |
| **Booth / pod / canopy** | Passive absorption plus barrier; active aperture (Lam-style window ANC) on the open side; metamaterial vents; plus any delivery above | Passive: a few dB of direct-path blocking [theory]; active aperture: about **5–10 dB, 300 Hz–1 kHz** for sound entering through the opening (Lam 2020 analogue) | Window ANC is lab/pilot; booths are passive products | A venue sale. Babble enters diffusely, which lowers active gains |
| **Open-ear glasses** | Beamforming mics plus open-ear speakers (Nuance, Legato) | **About 2 dB better SRT** in the measured Nuance study | Shipping, FDA-cleared OTC | Direct competitor for the "without earbuds" promise |
| **Whole venue** | Ceiling absorption, acoustic-capacity management, speaker zoning of the music | Up to about 10 dB reverberant reduction (vendor claim) plus a smaller Lombard spiral | Mature | Partnering opportunity, not a device |

---

## 7. Creative ideas (all **[speculative]** unless noted)

1. **"Duck the DJ" ANC.** The house music is the one loud bar noise available electronically and earlier than it reaches you. A venue-integrated hub could push the music feed to chair-backs or neckbands for feedforward cancellation of its bass (below about 500 Hz), where zones are large (λ/10 ≈ 7–34 cm). Basis: MUTE's "smart noise" variant and the causality analysis. Also cheaper: per-zone EQ or ducking of the venue's own speakers near tables that ask for it.
2. **Table hub plus neckband "virtual headphones".** The hub separates each tablemate's voice (beamforming plus BSS, as in Orsana) and streams it over LE Audio/Auracast to each guest's neckband. The neckband's near-field differential array plays the voice about 15 cm from the ear, about 6–10 dB above the local noise, and spatialises it to the talker's real direction (as in the TableConverse claim). Spill to neighbours stays low, so there is no Lombard escalation. Every block exists today; the integration doesn't. Main risks: latency (keep < 10–15 ms for lip sync and so the direct voice doesn't clash with the delayed copy) and acoustic feedback into the hub mics.
3. **Lamp with a downward ultrasonic beam per seat** (TableConverse claim, Holosonics hardware). Limited by 85–95 dB max SPL and weak low frequencies. Tracking keeps the beam on the head.
4. **High-back "conversation chair".** Headrest ANC for bass (10+ dB, 30 Hz–1 kHz class) plus seat-back near-ear speakers for boosted speech. Works only when people lean back. A posture problem for lively conversation.
5. **Partial-ANC "de-intelligibilizer".** Instead of cancelling babble, make nearby intelligible talkers *less* intelligible: add a few dB of speech-shaped masking only in their direction, or use parametric beams to cut informational masking. It relies on psychoacoustics (IM vs EM). Needs listening tests; it could backfire.
6. **Booth active aperture.** Lam-style distributed small speakers across the open side of a booth (think 12–24 channels). Expect at most about 5–10 dB, 300 Hz–1 kHz, and only for noise that comes in through that opening.

**Risks to flag.** Ultrasonic exposure from parametric arrays (not researched here; check the occupational limits before any near-head design). Acoustic feedback with voice lift. Privacy, since hubs pick up conversations: MUTE kept its relay analogue for this reason. Medical-device rules if marketed for hearing loss: Nuance went the FDA OTC hearing-aid route.

---

## 8. What I could not confirm
- No peer-reviewed dB numbers for: restaurant booths or canopies, the TableTalk device, the TableConverse system (claims only), noise-cancelling office chairs (Treyer 2016), the WINC multi-source results (read the summary only), or the Jeon & Choi neckband contrast (abstract only).
- Noveto status: PitchBook says liquidated, CB Insights says alive. I trust PitchBook more (more recent), but did not verify further.
- Phonak Roger figures come from manufacturer field-study excerpts, not from full texts I read.
- No published open-air ANC at a person on real multi-talker restaurant babble. I believe this is a real gap in the literature, not a gap in my search, but I cannot prove a negative.

## 9. Key sources (all opened unless marked)
- Elliott, Jung, Cheer 2018, head-tracked headrest ANC — https://pmc.ncbi.nlm.nih.gov/articles/PMC5876390
- Lam, Shi, Gan, Elliott, Nishimura 2020, open-window ANC — https://pmc.ncbi.nlm.nih.gov/articles/PMC7347542
- Lam et al. 2021, Ten questions on ANC in the built environment — https://www.sciencedirect.com/science/article/pii/S0360132321003322 (abstract plus table excerpt)
- Shen et al. 2018, MUTE (SIGCOMM) — https://sens.epfl.ch/documents/papers/sigcomm18mute.pdf
- Zhang, Pandey, Wang 2023, low-latency deep ANC — https://haozhang6720.github.io/doc/papers/ANC_journal_2023.pdf ; Deep ANC 2021 — https://pmc.ncbi.nlm.nih.gov/articles/PMC8328877/
- Silentium Quiet Bubble — https://www.silentium.com/technology-2/quiet-bubble
- Hyundai/Harman RANC — https://news.harman.com/releases/releases-20200130 ; https://www.analog.com/en/signals/articles/hyundai-noise-cancellation-technology.html
- Aircraft headrest virtual sensing 2023 — https://link.springer.com/article/10.1007/s42417-023-01090-5 (excerpt)
- Sound zones: https://arxiv.org/pdf/1911.10016 (excerpt); https://pub.dega-akustik.de/ICA2019/data/articles/000245.pdf (excerpt); Jeon & Choi neckband — https://pubmed.ncbi.nlm.nih.gov/33379876
- Parametric: Holosonics spec sheet — https://www.touchwindow.com/mm5/graphics/00000001/holosonics/Audio_Spotlight_2025_Spec_Sheet_Catalog.pdf (excerpt); Noveto — https://www.noveto.com/licensing ; MCPL — https://arxiv.org/abs/2504.17440
- Audioscenic — https://www.audioscenic.com/ ; http://audioscenic.com/about (excerpts)
- TableConverse patent US 12,354,619 — https://patents.justia.com/patent/12354619
- Nuance Audio study — https://www.frontiersin.org/journals/audiology-and-otology/articles/10.3389/fauot.2026.1822238/full (excerpt)
- Restaurant noise and Lombard: Rindel 2012 — https://odeon.dk/pdf/C116-BNAM_2012_Rindel_29.pdf ; Hodgson 2007 — https://pubmed.ncbi.nlm.nih.gov/17471719 ; Bottalico — https://www.shs.illinois.edu/2019/07 (excerpts)
- Masking: https://pmc.ncbi.nlm.nih.gov/articles/PMC3631264/ ; https://doi.org/10.1121/1.1345696 (excerpts)
- Metamaterial: https://link.aps.org/doi/10.1103/PhysRevB.99.024302 (excerpt)
