ROUND 6 LISTENING PACK - real meeting-room recordings (LibriCSS, 7-mic array, 4.25 cm radius)
Each set: a = BEFORE (unprocessed centre mic), b = ROUND-5 delay-and-sum (blind direction, 32 ms STFT),
c = ROUND-6 Superdirective+WNG, 8 ms STFT, track+ECAPA (causal, low latency, direction from the causal tracker),
d = ROUND-6 Superdirective+WNG, 8 ms STFT, REF dir. (same filter, steered with the REFERENCE direction: oracle geometry, an upper bound
    for what an intent cue such as head/gaze steering could give; not deployable as is).
Loudness matched (RMS). Use headphones. Clips were chosen by rule from Whisper scores (best, typical, worst),
so 1-3 and 5 are NOT typical; see REPORT_R6.pdf for averages.

01  OV10: largest measured gain of the round-6 method over round-5 delay-and-sum
    item OV10_s5_6930-76324-0013  (4.0 s, 53% of the sentence overlapped)
    target sentence: "it can't hurt anything i'm sure for we won't disturb things at all"
    a BEFORE         Whisper: "he can't hurt anything i'm sure"  (word-correct 0.38)
    b R5_DS          Whisper: "he can't hurt anything i'm sure he'll get out the time"  (word-correct 0.38)
    c R6_sd8_rt      Whisper: "i'm sure if we don't disturb things at all"  (word-correct 0.54)
    d R6_sd8_ref     Whisper: "he can't hurt anything i'm sure he'll get out of the way"  (word-correct 0.38)

02  OV20: largest measured gain of the round-6 method over round-5 delay-and-sum
    item OV20_s1_260-123286-0013  (4.0 s, 50% of the sentence overlapped)
    target sentence: "the shadow of the raft was clearly outlined upon the surface of the waves"
    a BEFORE         Whisper: "the shell of the ground has cooled outlined upon the surface of the waves"  (word-correct 0.71)
    b R5_DS          Whisper: "the shuttle of the ground has clearly outlined upon the surface of the waves"  (word-correct 0.79)
    c R6_sd8_rt      Whisper: "which of the raft was clearly outlined upon the surface of the waves"  (word-correct 0.86)
    d R6_sd8_ref     Whisper: "the shadow of the raft was clearly outlined upon the surface of the waves"  (word-correct 1.00)

03  OV40: largest measured gain of the round-6 method over round-5 delay-and-sum
    item OV40_s0_121-121726-0006  (3.3 s, 107% of the sentence overlapped)
    target sentence: "heredity the cause of all our faults"
    a BEFORE         Whisper: "peredity in his return all our fault"  (word-correct 0.29)
    b R5_DS          Whisper: "he's returned"  (word-correct 0.00)
    c R6_sd8_rt      Whisper: "the cause of all our faults"  (word-correct 0.86)
    d R6_sd8_ref     Whisper: "the cause of all our faults"  (word-correct 0.86)

04  TYPICAL overlapped item: round-6 gain over unprocessed closest to the panel median (+0.00)
    item OV10_s0_260-123288-0022  (3.2 s, 14% of the sentence overlapped)
    target sentence: "they seem to be we are lost but i am not sure"
    a BEFORE         Whisper: "i seem to be we are lost but i am not sure"  (word-correct 0.92)
    b R5_DS          Whisper: "i seem to be we are lost but i am not sure"  (word-correct 0.92)
    c R6_sd8_rt      Whisper: "i seem to be we are lost but i am not sure"  (word-correct 0.92)
    d R6_sd8_ref     Whisper: "they seem to be we are lost but i am not sure"  (word-correct 1.00)

05  FAILURE case: largest measured loss of the round-6 method vs round-5 delay-and-sum
    item OV10_s3_6829-68771-0018  (7.8 s, 16% of the sentence overlapped)
    target sentence: "for a moment beth stood staring while the new maid regarded her with composure and a slight smile upon her beautiful face"
    a BEFORE         Whisper: "as well as first"  (word-correct 0.00)
    b R5_DS          Whisper: "for a moment best at staring while the new maid regarded her with composure and a slight smile upon her beautiful face"  (word-correct 0.91)
    c R6_sd8_rt      Whisper: "as well as for her"  (word-correct 0.05)
    d R6_sd8_ref     Whisper: "for a moment best at staring while the new maid regarded her with composure and a slight smile upon her beautiful face"  (word-correct 0.91)

06  no overlap (control): single talker, check the beamformer does no harm
    item 0S_s0_1320-122617-0005  (3.8 s, 0% of the sentence overlapped)
    target sentence: "the bear shook his shaggy sides and then a well known voice replied"
    a BEFORE         Whisper: "the bear shook his shaggy sides and then a well known voice replied"  (word-correct 1.00)
    b R5_DS          Whisper: "the bear shook his shaggy sides and then a well known voice replied"  (word-correct 1.00)
    c R6_sd8_rt      Whisper: "the bear shook his shaggy sides and then a well known voice replied"  (word-correct 1.00)
    d R6_sd8_ref     Whisper: "the bear shook his shaggy sides and then a well known voice replied"  (word-correct 1.00)

Source: LibriCSS (Chen et al., ICASSP 2020; recordings of LibriSpeech test-clean, CC BY 4.0).
Nothing here is a human listening result; word-correct figures are Whisper base.en (an ASR proxy).