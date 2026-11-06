# Diarization track checklist (who said what)

- [x] Orient: lab state read. The r7 pipeline is owned by someone else (restarted twice by them); this track never killed or restarted it.
- [x] Ungated deps installed: silero-vad 6.2.3, pyannote.metrics 4.2.0 (metrics only).
- [x] Metrics + unit tests (DER agrees with pyannote.metrics, cpWER, edit distance agrees with jiwer): selab/diar/tests_metrics.py
- [x] HOW_THEY_DO_IT.md (10 sources opened)
- [x] Code: selab/diar/{core,spatial,data,features,score,run,metrics,summarize,report_tables,enrol_eval,demo}.py
- [x] CLI end-to-end on a real recording: results/diar/cli_smoke/ (75 s LibriCSS OV20 s3, --multichannel)
- [x] EasyCom: features, tuning on 4/12, test on 10/11, all variants incl. pose-oracle and gated DOA; failure analysis; demo_easycom.txt
- [x] LibriCSS: features running in results/diar/run_all2.sh -> tune 0-2 -> test 3-5 -> summarize/enrol_eval -> tables.md
- [x] After the chain: copy the LibriCSS tables from tables.md into results.md, then run `python -m selab.diar.demo lc_OV20_s3 A_spectral 120`
- [ ] Optional C: overlap-aware second-speaker assignment (not implemented); enrolment naming implemented (CLI --enrol, enrol_eval runs inside summarize)
