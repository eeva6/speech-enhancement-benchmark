# Round 5 working notes (scratch; the report is REPORT_R5.md)

## Facts established during the run
- LibriCSS zip: 6.0 GB on Google Drive. Range requests work, so only 24 recordings were pulled (~2.2 GB).
- each_spk.wav holds 8 dry loudspeaker feeds on the playback clock.
  - The recording leads the dry feeds by ~55-60 ms.
  - Clock drift is ~14 ppm (0.22 samples/s).
- Loudspeaker positions are fixed within one session index across its mini-sessions (0S..OV40). They differ between session indices.
  - The lhotse map says the dry-feed channel <-> speaker assignment changes per mini-session.
  - Our azimuth table is keyed by (session, channel), and it agrees within 3 deg across independent recordings.
- System-identification residual at mic 0 is -10 dB (median). So the estimated target image explains ~90% of the energy.
- The RT60 envelope-slope estimate is 0.29-0.62 s, median 0.32 s. Schroeder T20 is biased to ~1.2 s by the LS error floor.
- The first ~1 s of each recording is loud (likely a sync or calibration segment). The room is quiet from 1.0 to 3.0 s.
- Two sandbox events:
  - OOM kills from co-tenant load: another project's lab ran 2-5 heavy jobs on the same 2 vCPU / 8 GB.
  - One sandbox restart at ~03:12 CDT, which wiped /tmp and killed all background jobs.

## Finishing session (2026-10-22 03:56 UTC onward)
- Killed the 2-shard ASR queue and the libdf cdylib build (3 heavy jobs > budget of 2); deep-filter CLI binary was already built and was copied to third_party/df_bin/ (survived the restart).
- Chained methods (mvdr_online_est_dfn3/_tse) now reuse outputs/<tag>/mvdr_online_est/*.wav instead of recomputing the MVDR.
- run_r5 / score_r5 accept --items sub48 (2 items per recording) so core methods finish on a paired subset first.
- **DFN3 gain-staging bug (real finding):** LibriCSS recordings are at ~-53 dBFS (r1-r4 mixtures ~-17 dBFS). DeepFilterNet3 on the raw level attenuated nearly everything: Whisper WER 0.98 on 48 items; SI-SDR -30/-41 dB on two test items. Normalising the input to -26 dBFS RMS (and undoing the gain) restored it (same two items: word-correct 0 -> 1.0 and 0 -> 0.75). TSE output is level-invariant (outputs identical to 88-102 dB). Old outputs kept as *_rawlevel (deepfilternet3, mvdr_online_est_dfn3, rnnoise); WER rows renamed.
- Second sandbox restart at ~04:36 UTC (/tmp wiped, all jobs killed). Lanes restarted: scripts/r5_finish_proc3.sh, scripts/r5_finish_asr2.sh.
- Sensitivity inputs: mixtures/r5ctx (sub48 items with +-2 s real context; cut-back equals mix.wav exactly, max error 0), enrol_dry.wav (studio-clean enrolment, same utterance).
