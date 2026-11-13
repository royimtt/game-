# SPACE — beat-synced space montage (second cut)

A 54-second space montage cut to the supplied *Snowman* excerpt (56 BPM, 12/8).
Every picture is real: footage from the International Space Station, photographs from
Apollo, Voyager, Viking, Galileo, Cassini and New Horizons, images from the Hubble and
James Webb space telescopes, ESO and the Event Horizon Telescope, and official scientific
visualisations by NASA, ESA and ESO. Nothing on screen is AI-generated.

| | |
|---|---|
| Picture | 1920×1080, 60 fps, H.264 High, BT.709 |
| Sound | the supplied track, a one-word spoken channel tag before the drop and sound design under the cuts (AAC 320 kb/s, 48 kHz) |
| Cuts | 65 shots; every cut sits on a drum hit of the track, including the snare pick-ups between the beats |

## Structure

| Beats | Time | What happens |
|---|---|---|
| 0–8 | 0.0–9.0 s | leaving home: sunrise from the ISS, city lights, aurora, the Moon, Earthrise (Apollo 8), the Sun, then a star field that accelerates into streaks |
| 8–14 | 9.0–15.5 s | **S · P · A · C · E** — one letter per beat, each letter standing *behind* the world it crosses |
| 14–15 | 15.5–16.5 s | the word falls into a black hole: its letters wind around the hole and settle on the photon ring |
| 15–16 | 16.5–17.6 s | **signature** — a gravitational lens passes over the frame and leaves the channel name, spoken once; it implodes into the point the drop bursts out of |
| 16–32 | 17.6–34.7 s | the other side: star birth, star death, galaxies, deep fields — whip, zoom and spin transitions with real motion blur, match cuts on three ring nebulae, a nine-image strobe into the hook |
| 32–34 | 34.7–36.9 s | a supernova, twenty-three seconds of simulation in two beats, dissolving into the black hole it leaves |
| 34–40 | 36.9–43.3 s | the black hole, slowly: the simulation, then the two that have really been photographed (M87\*, Sgr A\*), then a dive through the disc |
| 40–45 | 43.3–48.7 s | the way home: Pluto, Neptune, Uranus, Saturn, Jupiter, Mars, the Moon, Earth — every globe registered on the same circle |
| 45–end | 48.7–54.0 s | low orbit, aurora, and the opening sunrise run backwards as a sunset; name and footage credit |

## Files

- `edit.py` — the edit decision list: every shot, the drum hit it lands on, its camera move and its transition.
- `engine.py` — the renderer. Each frame is composited in linear light: retimed sources (optical-flow slow
  motion, shutter-integrated fast motion), a virtual camera whose velocity produces the motion blur
  (zoom, spin and directional blur), two-sided transitions that hide the cut inside the blur, drum-driven
  reactions, bloom, halation, grade, grain; x264 encode in resumable chunks.
- `overlays.py` — the title (letters composited behind planets with fitted limb mattes, then drawn into the
  black hole), the lensed signature, the animated scope bars, the corner mark and the end card.
- `sound.py`, `voice_tag.py` — the soundtrack: spoken tag (doubling, plate, reverse swell, ducking under the
  word) and synthesised sound design placed from the edit (air under every whip/zoom/spin, risers, impacts).
- `voice/reditor_voice_v2.wav` — the spoken name (see below); `voice/song_tag.*` — the finished tag stem and its
  loudness curve, which drives the glow of the name on screen.
- `tools/` — `prepare_stills.py` (registers the planet portraits), `fitdisc.py` (fits the limb mattes of the title
  shots), `cutsheet.py` (review sheets around every cut), `make_credits.py`.
- `sources.json`, `sources.tsv`, `CREDITS.md` — where every picture comes from, its credit and licence.
- `engine_v1.py`, `edit_v1.py` — the first cut, kept for reference.

## Re-rendering

```bash
pip install numpy scipy soundfile opencv-python-headless pillow     # plus ffmpeg on PATH
mkdir clips stills_src
while IFS=$'\t' read -r name url _; do
  case "$name" in \#*|nasa__iss_*) continue;; *.mp4) d=clips;; *) d=stills_src;; esac
  curl -L -o "$d/$name" "$url"
done < sources.tsv
# ISS shots are stream-copied segments of the Expedition 65 film (start / length in seconds:
# 168/30, 1225/20, 2170/40, 2245/20, 2840/30), e.g.
#   ffmpeg -ss 168 -t 30 -i exp65.mp4 -c copy -an clips/nasa__iss_168.mp4
# and the closing sunset is the sunrise reversed:
#   ffmpeg -ss 2.0 -t 11.6 -i clips/nasa__iss_168.mp4 -an -vf reverse -crf 12 clips/nasa__iss_168_rev.mp4
python tools/prepare_stills.py stills_src stills

ffmpeg -i your_song.mp4 -vn song_raw.wav
python sound.py --song song_raw.wav --out song.wav                  # music + spoken tag + sound design

python engine.py board  --outdir board                              # storyboard: three frames per shot
python engine.py strip  --beat 16 --n 40 --out strip.jpg            # consecutive frames around a cut
python engine.py render --out space_1080p60.mp4                     # full render, 4 processes
python tools/cutsheet.py space_1080p60.mp4 review                   # review sheets of every cut
```

Each parallel chunk needs 1-1.5 GB of RAM at 1080p; lower `--jobs` on small machines. If a run is
interrupted, the same command with `--resume` keeps the chunks that already finished; with `--keep` the chunks
stay on disk, so after an edit only the deleted ones are rendered again.

`SM_CLIPS`, `SM_STILLS`, `SM_SONG` and `SM_FONT` override the folders, the audio file and the typeface.

## The signature and the voice

The channel name is delivered by the black hole. On beat 14 the title is pulled in: its letters shear into
arcs, wind around the hole and pile up on the photon ring. On beat 15, the last beat before the drop, the
name is imaged through a point lens at the centre of the frame (`beta = theta - thetaE² / theta`) whose
strength falls to zero, so a ring of light condenses into the word; its glow follows the loudness of the
spoken tag, and it implodes into the point from which the first shot of the drop opens.

The spoken name uses the voice of the supplied sample. No recording of that voice saying the name exists,
so it was synthesised: the narrator's phrase was isolated from the sample (vocal separation), and the name
was generated with zero-shot voice cloning (ZipVoice, via sherpa-onnx) conditioned on it. Out of about two
hundred takes the one kept is recognised as the word by a speech recogniser both alone and inside the mix,
is among the closest to the sample on two speaker-embedding models, falls at the end like a statement, and
stays inside the sample's pitch range. It was chosen by these measurements, not by ear.
To use a real recording instead, pass it with `--voice your.wav` to `sound.py`.

## Rights

- NASA material is public domain (NASA media usage guidelines; no endorsement implied).
- ESO, ESA/Hubble and ESA/Webb material is CC BY 4.0 — the credit must stay visible. The film ends with a
  credit line; when posting, also paste the short credit from `CREDITS.md` into the description.
- Typeface: Unbounded (SIL Open Font License), included in `fonts/`.
- The music is **not** cleared by this project. *Snowman* is a commercial recording; on TikTok, Instagram or
  YouTube use the platform's licensed version of the sound or expect a claim.
