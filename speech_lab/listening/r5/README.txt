ROUND 5 LISTENING PACK - real meeting-room recordings (LibriCSS, 7-mic array, mic 0 shown)
Each pair: a = BEFORE (unprocessed centre mic), b = AFTER. Loudness matched. Use headphones.
These are recordings; a device that processes audio in the room is a different situation (see REPORT_R5).
Clips were chosen by rule from the measured ASR scores (best / worst cases), so they are NOT typical:
typical effects are in REPORT_R5.pdf.

01  OV10 overlap: online MVDR (estimated direction) then target-speaker extraction
    item OV10_s3_6829-68771-0018  (7.8 s, 16% of the sentence overlapped)
    target sentence: "for a moment beth stood staring while the new maid regarded her with composure and a slight smile upon her beautiful face"
    Whisper heard BEFORE: "as well as first"  (word-correct 0.00)
    Whisper heard AFTER:  "she was quite stunned and staring while the new man regarded her with a composure and a slight smile upon her beautiful face"  (word-correct 0.73)

02  OV20 overlap: online MVDR (estimated direction) then target-speaker extraction
    item OV20_s4_3570-5694-0013  (5.2 s, 17% of the sentence overlapped)
    target sentence: "this differentiation is furthered by the inheritance of wealth and the consequent inheritance of gentility"
    Whisper heard BEFORE: "this differentiation is furthered by the inheritance of wealth and the consequent inheritance of children"  (word-correct 0.93)
    Whisper heard AFTER:  "this differentiation is furthered by the inheritance of wealth and the consequent inheritance of wealth"  (word-correct 0.93)
    NOTE: no scored item in this cell improved with this method; this is the least-bad one.

03  OV40 overlap: online MVDR (estimated direction) then target-speaker extraction
    item OV40_s1_237-134500-0011  (3.1 s, 93% of the sentence overlapped)
    target sentence: "aren't you splashed look at the spider webs all over the grass"
    Whisper heard BEFORE: "are you glad"  (word-correct 0.08)
    Whisper heard AFTER:  "aren't you splashed look at the spider breath on the grass"  (word-correct 0.75)

04  overlap: online MVDR alone, fully causal, 32 ms, estimated direction
    item OV20_s2_2961-961-0011  (7.0 s, 25% of the sentence overlapped)
    target sentence: "the genealogies which you have recited to us out of your own annals solon are a mere children's story"
    Whisper heard BEFORE: "and the allergies to have decided to us out of your own end of solon our immune children's story"  (word-correct 0.58)
    Whisper heard AFTER:  "the genealogies which you have to be cited to us out of your own animal salad out of your children's story"  (word-correct 0.68)

05  overlap: DeepFilterNet3 alone (a noise suppressor) - expect little change to the second voice
    item OV40_s2_1284-1181-0020  (6.2 s, 56% of the sentence overlapped)
    target sentence: "dear me what a chatterbox you're getting to be unc remarked the magician who was pleased with the compliment"
    Whisper heard BEFORE: "dear me what a chatterbox you're getting to be young for a box of a magician who was the leadist author of the fact that"  (word-correct 0.68)
    Whisper heard AFTER:  "and the two beat one of chatterboxer getting to be on"  (word-correct 0.16)

06  FAILURE case: largest measured loss for the cascade
    item OV20_s1_5105-28241-0003  (3.3 s, 34% of the sentence overlapped)
    target sentence: "steam up and canvas spread the schooner started eastwards"
    Whisper heard BEFORE: "steve up and canvas spread the schooner started easily"  (word-correct 0.78)
    Whisper heard AFTER:  "and see them"  (word-correct 0.11)

07  no overlap (control): TSE on clean single-talker speech
    item 0S_s4_1995-1826-0023  (7.7 s, 0% of the sentence overlapped)
    target sentence: "goobers don't grow on the tops of vines but underground on the roots like yams is that so"
    Whisper heard BEFORE: "googles don't grow on the tops of vines but on the ground on the woods like games is that so"  (word-correct 0.78)
    Whisper heard AFTER:  "this was the one that tops the bags but the ground on the looks so"  (word-correct 0.28)

Source: LibriCSS (Chen et al., ICASSP 2020; recordings of LibriSpeech test-clean, CC BY 4.0).
Nothing here is a human listening result; the word-correct figures are Whisper base.en (an ASR proxy).