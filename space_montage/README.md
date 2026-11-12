# SPACE — beat-synced space montage

A 54-second space montage cut to the supplied *Snowman* excerpt (56 BPM, 12/8).
Everything on screen is real mission footage or official scientific visualisation
from NASA, ESA/Hubble, ESA/Webb and ESO — nothing is AI-generated.

| | |
|---|---|
| Picture | 1920×1080, 60 fps, H.264 High, BT.709 |
| Sound | the supplied track plus a one-second spoken channel tag before the drop (AAC 256 kb/s); picture runs 0.9 s past the music for the fade |
| Cuts | 53, every one on the frame nearest a beat (−4.5 ms … +9.8 ms from the drum hit) |

## Structure

| Beats | Time | What happens |
|---|---|---|
| pickup | 0.0–0.5 s | Webb deep field fades in |
| 0–8 | 0.5–9.0 s | four nebula flights, one cut per kick |
| 8–13 | 9.0–14.4 s | **S · P · A · C · E** — one letter and one new world per beat |
| 13–15 | 14.4–16.5 s | the word ignites over a black hole, then falls into its shadow |
| 15–16 | 16.5–17.6 s | **signature**: the channel name appears inside the event horizon on the last beat before the drop, spoken once |
| 16–32 | 17.6–34.7 s | montage: a cut on every beat, an eighth-note triplet burst closing each bar (stars → exoplanets → solar system → black holes) |
| 32–40 | 34.7–43.3 s | supernova, then the solar system: Sun, Jupiter, Saturn, Moon |
| 40–50 | 43.3–54.0 s | home: Earth from the ISS, then pulling away to a pale blue dot |

## Files

- `edit.py` — the edit decision list: every shot, its in-point, the beat it lands on, camera move and transition.
- `engine.py` — the renderer. Decodes footage through ffmpeg, composites each frame in linear light
  (speed ramps with shutter-integrated motion blur, virtual camera, whip/spin/zoom transitions,
  flashes, bloom, light rays, anamorphic streaks, chromatic aberration, typography, grade, grain)
  and encodes with x264.
- `voice_tag.py` — builds the spoken tag and mixes it into the song (see below).
- `voice/` — the voice take used, the finished tag stem and its loudness curve (drives the logo's glow).
- `sources.tsv` — download URL of every clip used.
- `CREDITS.md` — per-shot footage credits and licences.

## Re-rendering

```bash
pip install numpy scipy soundfile opencv-python-headless pillow   # plus ffmpeg on PATH
mkdir clips && while IFS=$'\t' read -r name url _; do   # ~5 GB
  case "$name" in \#*|nasa__iss_*) continue;; esac; curl -L -o "clips/$name" "$url"; done < sources.tsv
# ISS shots are stream-copied segments of the Expedition 65 film, e.g.
#   ffmpeg -ss 1150 -t 65 -i exp65.mp4 -c copy -an clips/nasa__iss_1150.mp4
#   (starts/lengths: 168/30 1150/65 2170/40 2245/20 2840/30)
ffmpeg -i your_song.mp4 -vn song_raw.wav
python voice_tag.py --recording voice/reditor_voice.wav --song song_raw.wav \
       --out song.wav --plain-out song_no_voice.wav        # song.wav = music + spoken tag

python engine.py board  --outdir board            # storyboard: 3 frames per shot
python engine.py render --out space_1080p60.mp4   # full render, 4 processes
python engine.py render --out space_2160p60.mp4 --width 3840 --crf 18
```

`SM_CLIPS` and `SM_SONG` override the clip folder and the audio file
(`SM_SONG=song_no_voice.wav` gives the same picture without the spoken tag).
The titles use Inter Display; adjust the font paths at the top of `edit.py` if it is installed elsewhere.

## The signature and the voice tag

The channel name lands on beat 15, the last beat before the drop: the title has just fallen into a black
hole, the frame is dark, and the name is struck inside the event horizon with a flare, a shock ring that
refracts the picture behind it, and a fine line of light under the word. Its glow follows the loudness of
the spoken tag (`voice/song_tag.json`), and it rushes the camera into the drop.

The tag itself is one word, mixed like a producer tag: a reverse-reverb swell rises into it, the music
dips 5.5 dB under it and swells back into the drop.

- The voice in `voice/reditor_voice.wav` is synthetic: Piper TTS (MIT) with the 16 kHz test voice that ships
  in the Piper repository, pronounced "REH-di-tor" (`[[ ɹˈɛdɪtˌɔːɹ ]]`), then lowered and slowed with Praat.
  `pip install piper-tts praat-parselmouth` and `--voice test_voice.onnx` regenerate it.
- To use a real voice instead, record the name and pass it with `--recording your.wav`; the swell, doubling,
  reverb, ducking and the logo's glow are rebuilt around it.

## Rights

- NASA footage is public domain (NASA media usage guidelines; no endorsement implied).
- ESO, ESA/Hubble and ESA/Webb footage is CC BY 4.0 — the credit must stay visible. The video ends with a
  credit line; when posting, also paste the short credit from `CREDITS.md` into the description.
- Typeface: Inter Display (SIL Open Font License).
- The music is **not** cleared by this project. *Snowman* is a commercial recording; on platforms such as
  TikTok, Instagram or YouTube use the platform's licensed version of the sound or expect a claim.
