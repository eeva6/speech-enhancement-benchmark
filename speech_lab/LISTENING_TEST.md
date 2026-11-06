# Listening test: how to run it with friends (about 10 minutes per person)

**What it measures.** How many words people catch with each kind of processing. Method names are hidden.
Every listener hears each sentence only once. Every processing type is heard equally often (a Latin square,
rotated by participant number).

## 1. Start it (one command)
```bash
./run_listening_test.sh          # round 5: real meeting-room recordings with a second person talking over
./run_listening_test.sh r3       # (optional) round 3: recorded noise such as HVAC, crowds and clatter
```
- Open the printed URL. Use `http://127.0.0.1:7862` on the same computer, or the Wi-Fi address on a phone or laptop on the same network.
- `--share` also prints a temporary public gradio.live link. Use it only if you want remote friends to join. Anyone with the link can open the test.

## 2. Before each listener
1. **Headphones**, in a quiet room. Set the volume once, using the first clip, to a comfortable level. Do not change it afterwards.
2. Give each person a **different participant number**: 0, 1, 2, … With 5 processing types, use multiples of 5 people (5, 10, 15) so every sentence is heard with every processing type equally often.
3. Do not tell them which processing types exist, and do not let them see `stimulus_key.json`.

## 3. What the listener does (read this to them)
> "Each trial first plays the voice you should follow. Then it plays a sentence where another person may talk at the same time. Press play once, then type every word the target voice said. Guessing is fine. Then rate how hard it was to listen, and press Submit."

## 4. Afterwards
```bash
./run_listening_test.sh r5 --analyze
```
- This prints the word-correct rate per processing type with bootstrap 95% CIs, from **human rows only**.
- Rows tagged `synthetic` come from `--selftest`, where Whisper plays the listener. They only check the pipeline and are never mixed into human results.
- Responses are stored in `results/listening_test_r5/responses.csv`. Each participant gets a random code; no names are stored.

## How many people?
- 15 trials per person gives 3 trials per processing type per person.
- About 10 listeners (150 trials) is roughly where a 10-percentage-point difference in word-correct starts to be resolvable.
- Fewer listeners is still useful, but read it as a pilot.

## Honest limits
- These are recordings played over headphones. That is not the same as standing in the room.
- Friends are not a representative sample, and nobody's hearing is screened.
- The test measures word recognition only. It does not measure comfort, latency or naturalness.
