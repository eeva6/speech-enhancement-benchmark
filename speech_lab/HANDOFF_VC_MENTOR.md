# Handoff to VC Mentor: speech enhancement / loud-room hearing idea (2026-10-18)

J asked VC Mentor to run the speech enhancement idea through a partner evaluation once this lab work is done. The lab work is done and was delivered to J on 2026-10-18.

## Files (project root /workspace/projects/8ab30c5b-4a43-47d2-af42-980fa05ae57f/)
- speech_lab/REPORT_R4.pdf (and .md): round 4, the form-factor simulation plus the solution landscape
- speech_lab/REPORT.pdf: rounds 1-3 denoiser/TSE/latency benchmark
- speech_lab/results/r4/: summary_r4.md, benefit_by_form.csv, benefit_vs_delay.csv, open_vs_inear.csv, capture_sweep_summary.csv, predictive_traffic_summary.csv, figs/
- speech_lab/docs/research_open_air_anc.md and research_hearing_tech.md: sourced research memos with URLs
- bar_open_ear_examples.zip and speech_demo_START_HERE.zip: audio demos

## Simulation summary
Setup: 21 simulated reverberant bars x 2 input SNRs (-5 and 0 dB). The friend talks from 1 m across the table, with 8 babble talkers plus recorded crowd noise. Metric: equivalent SNR benefit at the ear, from ESTOI. Simulation only, with no head model, no feedback model and no human data.
- Open ear, device voice played 10 dB above the direct voice:
  - glasses (6 mics): +3.8 dB at 3 ms
  - neckband (6 mics): +3.2 dB at 3 ms
  - tabletop 8-mic hub: +3.6 dB at 4.5 ms (+4.0 at 7 ms)
  - phone or clip mic on the friend: +4.9 dB at 7 ms
  - plain amplifier: -0.5 dB
- At +20 dB playback: glasses +4.7, neckband +4.2, tabletop +5.3, remote mic +6.3. That playback level is unrealistically loud and risks feedback.
- Validation: the glasses result matches measured Nuance Audio hearing glasses (+2.2 to 4.4 dB on people).
- Delay:
  - an ideal clean voice gives +9.8 dB at 1 ms, +7.0 at 8 ms, +4.5 at 15 ms and +0.6 at 30 ms;
  - real arrays lose about half their benefit by 10-17 ms and go negative past about 30 ms;
  - a Bluetooth-class link (20-50 ms) erases the remote mic's advantage (+4.9 at 7 ms becomes -3.0 at 52 ms).
- An 8 ms AI/Wiener post-filter reduced the benefit on every device (glasses: 3.8 to 2.6 dB). With an open ear, processing must fit in about 5 ms.
- The bottleneck is capture quality: today's beamformers hear the friend only about 1-2 dB better than the ear does. Capture sweep at 5 ms or less:
  - device signal at 10 dB SNR: +7.2 dB (+10 playback) and +10.5 dB (+20 playback);
  - at 15 dB SNR: +8.3 dB and +13.5 dB.
- In-ear isolation adds only about 1 dB with today's beamformers, against about 17 dB with a clean signal.
- Predictive traffic forecast: SI-SDR +3.7 dB vs +0.8 dB for blind tracking; ESTOI +0.023 vs +0.011. It is a comfort feature.
- Design target: capture the friend at 10 dB SNR or better and deliver within 5 ms, for about +7 dB at the open ear. That is roughly double today's hearing glasses.

## Candidate solutions (maturity)
1. Table hub (mic array plus low-latency separation) feeding a neckband or glasses over a custom radio link under 5 ms. The components ship today; no integrated earbud-free product exists. This is the recommended wedge.
2. Smart neckband (6-8 chest mics, near-field speakers, bass ANC). Exists as research prototypes; Widrow measured over 10 dB in 2003. Commercial white space.
3. Gaze-steered open-ear glasses. Lab results of 8-12 dB (BU). The category is shipping and crowded.
4. Chair-back or booth "quiet seat" with headrest ANC (about 10-20 dB at 300 Hz-1 kHz in the lab) and an active aperture. Lab or pre-production; a venue sale.
5. "Duck the DJ": use the venue's music feed as the ANC reference, or duck the speakers locally. Speculative.
6. Predictive noise forecasting. Modest measured benefit; an add-on.
7. Overhead parametric speech-spotlight lamp. The hardware exists (Holosonics); unproven for this use, and ultrasound safety is still to be checked.
8. "Babble thinning" with targeted masking. Speculative.
9. Venue acoustic treatment (up to about 10 dB, vendor claim). Mature; a partnership.

Physics limit: open-air ANC works only below about 1 kHz, and the quiet zone is about lambda/10 (3.4 cm at 1 kHz).

## Prior art and competitors
- Hearing glasses:
  - Nuance Audio ($699) and Nuance Audio Plus (from $829, launched 2026-09-29): FDA OTC, measured +2.2 to 4.4 dB
  - Meta Ray-Ban Conversation Focus: no published data
  - Legato: $12M, out of stealth Aug 2026
  - Cearvol
  - legacy Varibel
- Remote and table mics: Phonak Roger Table Mic and Roger On Sphere (Nov 2026; needs hearing aids), AudioTelligence Orsana, TableTalk Labs, Apple Live Listen.
- DNN hearing aids: Phonak Sphere Infinio, Oticon Intent, Starkey Edge AI.
- Research:
  - UW Target Speech Hearing (7 dB at 12 ms) and Sound Bubbles
  - GCFSnet
  - UIC distributed phones
  - MUTE lookahead ANC (SIGCOMM 2018)
  - Elliott headrest ANC
  - Lam window ANC
- Patent US 12,354,619 "TableConverse" (2025-07-08): table beamforming mics, ML suppression, parametric or overhead speakers, headrest bone conduction, under 15 ms latency. This is key prior art.
- Directional audio and seat ANC: Holosonics, Noveto (likely defunct), Audioscenic, Silentium Quiet Bubble.
