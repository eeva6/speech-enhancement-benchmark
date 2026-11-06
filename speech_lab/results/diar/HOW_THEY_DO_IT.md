# How Zoom, Meet, Teams and note-taker bots work out "who said what"

Short research note for the diarization track (2026-10-24). Every claim below comes from a page I opened; the URLs are listed at the end.

## 1. Video-call platforms: the speaker label comes from the network

In a video call, each person's microphone is a separate stream on the media server before anything is mixed. So the platform already knows who is talking, and none of this needs voice biometrics.

- **Zoom (Meeting SDK raw data).** A bot can subscribe to two kinds of audio: `onMixedAudioRawDataReceived` (the session-wide mix that participants hear) and `onOneWayAudioRawDataReceived` (per-user audio tagged with a user id). Telephone participants get no per-user stream. Raw access needs the host's local-recording or live-streaming permission, and everyone sees a consent dialog. [Z1]
- **Zoom active speaker events.** Recall.ai's speaker-timeline docs say Zoom's active speaker events "are produced based on the underlying audio of the participant", so they fire often, even during one monologue. The other platforms only send an event when a *new* participant starts speaking. [R2]
- **Google Meet Media API.** This is in Developer Preview and no longer accepting signups. A client must offer exactly three audio media descriptions. The server (an SFU, which forwards streams without mixing them) sends the three loudest participants over three fixed SSRCs (RTP stream ids). The true speaker of each packet is in the RTP CSRC header, a per-participant id that stays the same until that person leaves. So Meet gives "top-3 loudest, unmixed and labelled" rather than one stream per person. [G1]
- **Microsoft Teams real-time media bots.** Audio arrives as 20 ms frames of 16 kHz, 16-bit PCM. The platform reports *active speakers*, meaning who is heard in each received audio frame, and *dominant speakers*, the most active participants in the conversation. Microsoft now steers AI-agent use cases away from raw-media bots and toward Graph meeting transcripts. [T1]

## 2. Note-taker bots: they use platform metadata first and acoustic diarization only as a fallback

Recall.ai is the meeting-bot infrastructure many note-takers build on. Its docs name four attribution methods [R1]:

1. **Perfect diarization.** Each participant's separate audio stream is transcribed on its own, so overlapping speech stays apart and labels are participant names. Supported on Zoom, Teams and Meet, not Webex. This is the recommended default. The catch is that it cannot split several people sharing one device or room mic. Real-time cost is about 1.8× the transcription credits, because overlapping streams are each transcribed.
2. **Speaker-timeline diarization.** One mixed stream is transcribed, and words are mapped to whichever participant the platform's active-speaker events name for that time range. Recall says this "can sometimes be inaccurate or incomplete (e.g. noise, missed speaker changes, or overlapping speech)", and that it fails for conference rooms.
3. **Machine diarization.** A speech-to-text provider (Deepgram, AssemblyAI, Speechmatics and others) clusters voices on the mixed stream and returns generic labels (A/B/C). Recall warns it is less accurate when voices sound similar.
4. **Hybrid diarization.** Perfect diarization per stream, then machine diarization *inside* any stream that holds several voices. Streams with one acoustic label get the participant's name; streams with several keep generic labels.

Product behaviour matches this:
- **Otter.** In meetings, the Notetaker labels speakers with participant names from the video platform where a speaker turn can be matched; unmatched turns become "Speaker 1/2" or "unknown". For ad-hoc or uploaded recordings there is no participant data, so speakers stay generic unless voice enrolment ("speaker learning" from voices the user has tagged) is enabled. Diarization into turns always runs. [O1]
- **Circleback (Aug 2025).** When several people join from one device or a conference room, Circleback "detects multiple voices from the same source and separates them into distinct participants". Renamed participants' voices are remembered for future meetings, which is enrolment-based naming. In practice this is hybrid diarization plus voiceprints. [C1]

**Takeaway.** On a call, "who said what" is mostly a routing problem the platform solves. Acoustic diarization only matters for shared mics, in-room meetings, phone dial-ins and uploaded files, and that is exactly the case a wearable or table-top mic array is in.

## 3. In-room / single-mic diarization (what the lab has to do)

The classic cascade is VAD → speaker embeddings on short windows → clustering → resegmentation → alignment of ASR words to turns.
- **VAD** finds speech, and its misses and false alarms go straight into DER.
- **Embeddings** are x-vector, ECAPA-TDNN or TitaNet vectors on 1.5–3 s windows. NeMo's docs describe the trade-off: longer windows give cleaner speaker identity but coarser time resolution. With overlapping windows, single-scale systems resolve only about 0.75–1.5 s. That hurts speaker counting and the alignment of ASR words to speakers. [N1]
- **Clustering.** Spectral clustering estimates the speaker count from the eigengap. AHC with a threshold or VBx resegmentation are the alternatives.
- **NeMo's cascaded system** runs MarbleNet VAD, extracts TitaNet embeddings at several window scales, clusters them, and then applies a neural **Multi-Scale Diarization Decoder (MSDD)**. MSDD compares each step's multi-scale embeddings with the cluster-average embeddings, weights the scales with a 1-D CNN, and feeds the weighted cosine similarities to an LSTM. The LSTM outputs per-speaker activity, which handles overlap. NeMo also ships **Sortformer**, an end-to-end diarizer trained with an arrival-time "Sort Loss", plus a streaming variant with a speaker cache. [N1]
- **pyannote 3.x** uses a local neural segmentation model (powerset loss, so it outputs overlap directly) on short chunks, embeddings per local speaker, and global clustering. Full-protocol DER (no collar, overlap scored): AMI headset-mix 18.8%, AMI single distant mic 22.4%, AISHELL-4 12.2%, AliMeeting channel 1 24.4%, DIHARD-3 21.7%, VoxConverse 11.3%. **The models are gated:** you must accept user conditions on Hugging Face and use an access token. I did not use them; they are a possible upgrade that needs J's OK. [P1]
- **DiariZen (BUT, 2025)** follows the same EEND-VC scheme (local end-to-end neural diarization plus vector clustering). It replaces pyannote's local model with WavLM + Conformer (pruned) and clusters with pyannote's machinery. Reported DER without collar: AMI-SDM 13.9%, AISHELL-4 10.1%, AliMeeting far 10.8%, NOTSOFAR-1 16.7%, DIHARD-3 14.5%, VoxConverse 9.1% (Large-s80-v2). A Jan 2026 update added multi-channel WavLM. The weights are CC-BY-NC, research use only. [D1]
- **Word alignment.** ASR word timestamps are mapped to whichever diarized speaker covers each word. Coarse diarization boundaries move words across turn changes; NeMo names this as a main reason for finer temporal resolution. [N1]

**Typical DER.** Benchmark-grade cascades (embeddings plus clustering) land around 20–30% full DER on far-field meetings. Modern local-EEND + clustering systems reach about 10–17%. A forgiving 0.25 s collar and ignoring overlap reduce the numbers a lot, so always state the protocol.

## 4. What this means for the lab's build
- The **platform path** (a separate stream per participant, Recall's "perfect" or "speaker timeline") is our upper bound. On EasyCom the close mics play the role of Zoom's per-user streams; on LibriCSS the dry loudspeaker feeds do.
- The **in-room path** is the ungated cascade: Silero VAD + SpeechBrain ECAPA + spectral (NME-SC) or AHC clustering + Whisper word timestamps.
- The lab's edge is the **mic array**. Direction of arrival (DOA) is a second, voice-independent cue, much as the network stream id is for the platforms. On head-worn glasses it only helps if head rotation is compensated.

## Sources (opened 2026-10-24)
- [Z1] Zoom Meeting SDK (Windows), "Use raw data": https://developers.zoom.us/docs/meeting-sdk/windows/default-ui/advanced-features/raw-data/
- [R1] Recall.ai docs, "Diarization": https://docs.recall.ai/docs/diarization
- [R2] Recall.ai docs, "Speaker Timelines": https://docs.recall.ai/docs/speaker-timeline
- [G1] Google Meet Media API, "Manage virtual media streams": https://developers.google.com/workspace/meet/media-api/guides/virtual-streams
- [T1] Microsoft Learn, "Real-time media calls and meetings with Microsoft Teams": https://learn.microsoft.com/en-us/microsoftteams/platform/bots/calls-and-meetings/real-time-media-concepts
- [O1] Otter Help Center, "Disable Speaker Learning" (includes the speaker-labelling table): https://help.otter.ai/hc/en-us/articles/40643231903639-Disable-Speaker-Learning
- [C1] Circleback release note, "Automatic participant identification for hybrid meetings" (2025-08-06): https://circleback.ai/releases/automatic-participant-identification-for-hybrid-meetings
- [N1] NVIDIA NeMo docs, Speaker Diarization "Models" (MSDD, Sortformer): https://docs.nvidia.com/nemo-framework/user-guide/latest/nemotoolkit/asr/speaker_diarization/models.html
- [P1] pyannote/speaker-diarization-3.1 model card: https://huggingface.co/pyannote/speaker-diarization-3.1
- [D1] DiariZen repository README (benchmarks, licence): https://github.com/BUTSpeechFIT/DiariZen
