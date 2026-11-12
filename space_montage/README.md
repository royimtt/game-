# SPACE — beat-synced space montage

A 54-second space montage cut to the supplied *Snowman* excerpt (56 BPM, 12/8).
Everything on screen is real mission footage or official scientific visualisation
from NASA, ESA/Hubble, ESA/Webb and ESO — nothing is AI-generated.

| | |
|---|---|
| Picture | 1920×1080, 60 fps, H.264 High, BT.709 |
| Sound | the supplied track, untouched (AAC 256 kb/s), picture runs 0.9 s past it for the fade |
| Cuts | 52, every one on the frame nearest a beat (−4.5 ms … +9.8 ms from the drum hit) |

## Structure

| Beats | Time | What happens |
|---|---|---|
| pickup | 0.0–0.5 s | Webb deep field fades in |
| 0–8 | 0.5–9.0 s | four nebula flights, one cut per kick |
| 8–13 | 9.0–14.4 s | **S · P · A · C · E** — one letter and one new world per beat |
| 13–16 | 14.4–17.6 s | the word ignites over a black hole, then falls into its shadow |
| 16–32 | 17.6–34.7 s | montage: a cut on every beat, an eighth-note triplet burst closing each bar (stars → exoplanets → solar system → black holes) |
| 32–40 | 34.7–43.3 s | supernova, then the solar system: Sun, Jupiter, Saturn, Moon |
| 40–50 | 43.3–54.0 s | home: Earth from the ISS, then pulling away to a pale blue dot |

## Files

- `edit.py` — the edit decision list: every shot, its in-point, the beat it lands on, camera move and transition.
- `engine.py` — the renderer. Decodes footage through ffmpeg, composites each frame in linear light
  (speed ramps with shutter-integrated motion blur, virtual camera, whip/spin/zoom transitions,
  flashes, bloom, light rays, anamorphic streaks, chromatic aberration, typography, grade, grain)
  and encodes with x264.
- `sources.tsv` — download URL of every clip used.
- `CREDITS.md` — per-shot footage credits and licences.

## Re-rendering

```bash
pip install numpy opencv-python-headless pillow        # plus ffmpeg on PATH
mkdir clips && while IFS=$'\t' read -r name url _; do   # ~5 GB
  case "$name" in \#*|nasa__iss_*) continue;; esac; curl -L -o "clips/$name" "$url"; done < sources.tsv
# ISS shots are stream-copied segments of the Expedition 65 film, e.g.
#   ffmpeg -ss 1150 -t 65 -i exp65.mp4 -c copy -an clips/nasa__iss_1150.mp4
#   (starts/lengths: 168/30 1150/65 2170/40 2245/20 2840/30)
ffmpeg -i your_song.mp4 -vn song.wav

python engine.py board  --outdir board            # storyboard: 3 frames per shot
python engine.py render --out space_1080p60.mp4   # full render, 4 processes
python engine.py render --out space_2160p60.mp4 --width 3840 --crf 18
```

`SM_CLIPS` and `SM_SONG` override the clip folder and the audio file.
The title uses Inter Display (SIL Open Font License); adjust the font paths at the top of `edit.py` if needed.

## Rights

- NASA footage is public domain (NASA media usage guidelines; no endorsement implied).
- ESO, ESA/Hubble and ESA/Webb footage is CC BY 4.0 — the credit must stay visible. The video ends with a
  credit line; when posting, also paste the short credit from `CREDITS.md` into the description.
- The music is **not** cleared by this project. *Snowman* is a commercial recording; on platforms such as
  TikTok, Instagram or YouTube use the platform's licensed version of the sound or expect a claim.
