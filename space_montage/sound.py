#!/usr/bin/env python3
"""Builds the soundtrack: the song, the spoken channel tag and the sound design of the cuts.

    python sound.py --song song_raw.wav --voice voice/reditor_voice_v2.wav --out song.wav

The tag is one spoken word on the last beat before the drop. It is treated like a producer
tag (a wide double, a dark plate, one echo, a reverse swell rising into it) and the music
dips under it. The sound design is synthesised here from filtered noise and sine sweeps and
is placed from the edit itself: an air movement under every whip / zoom / spin, risers into
the title, the drop and the way home, low impacts where the picture bursts open.
"""
import argparse
import json
import math
import os
import sys

import numpy as np
import scipy.signal as ss
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import engine  # noqa: E402
import voice_tag as vt  # noqa: E402

SR = vt.SR


def db(x):
    return 10.0 ** (x / 20.0)


def rms(a):
    return float(np.sqrt(np.mean(np.square(a))) + 1e-12)


# ------------------------------------------------------------ synthesis -----
def shaped_noise(dur, fc, bw, rng, stereo=0.6):
    """Stereo noise whose pass band follows fc(t) in Hz (bw in octaves); filtered in the STFT domain."""
    n = int(dur * SR)
    common = rng.standard_normal(n)
    out = []
    for _ in range(2):
        x = math.sqrt(1.0 - stereo) * common + math.sqrt(stereo) * rng.standard_normal(n)
        f, t, Z = ss.stft(x, SR, nperseg=1024, noverlap=768)
        c = np.interp(t, np.linspace(0.0, dur, len(fc)), fc)
        lf = np.log2(np.maximum(f, 20.0))[:, None]
        g = np.exp(-0.5 * ((lf - np.log2(c)[None, :]) / bw) ** 2)
        _, y = ss.istft(Z * g, SR, nperseg=1024, noverlap=768)
        out.append(y[:n] if len(y) >= n else np.pad(y, (0, n - len(y))))
    return np.stack(out, axis=1)


def pan(sig, p):
    """Equal-power pan of a stereo signal; p(t) in -1 (left) .. 1 (right)."""
    a = (np.asarray(p) + 1.0) * (math.pi / 4.0)
    return np.stack([sig[:, 0] * np.cos(a) * math.sqrt(2.0), sig[:, 1] * np.sin(a) * math.sqrt(2.0)], axis=1)


def whoosh(rng, lead=0.30, tail=0.34, lo=450.0, hi=3800.0, direction=0):
    """Air moving past the lens: rises to the cut, falls away after it. Returns (signal, index of the cut)."""
    dur = lead + tail
    n = int(dur * SR)
    t = np.arange(n) / SR
    fc = np.where(t < lead, lo * (hi / lo) ** np.clip(t / lead, 0, 1), hi * (0.3) ** np.clip((t - lead) / tail, 0, 1))
    x = shaped_noise(dur, fc[:: SR // 200], 0.85, rng)
    env = np.where(t < lead, np.clip(t / lead, 0, 1) ** 2.6, np.exp(-(t - lead) / (0.32 * tail)))
    env *= np.clip((dur - t) / 0.03, 0, 1)
    x = x * env[:, None]
    if direction:
        x = pan(x, direction * np.clip((t - lead) / (0.5 * dur), -1, 1) * 0.8)
    return x / (np.abs(x).max() + 1e-9), int(lead * SR)


def riser(rng, dur, lo=260.0, hi=5200.0):
    """Rising air that stops dead on the hit. Returns (signal, index of the hit = its end)."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    fc = lo * (hi / lo) ** (t / dur) ** 1.4
    x = shaped_noise(dur, fc[:: SR // 200], 0.9, rng, stereo=0.8)
    env = (t / dur) ** 2.6 * np.clip((dur - t) / 0.008, 0, 1)
    x = x * env[:, None]
    return x / (np.abs(x).max() + 1e-9), n


def impact(rng, f0=78.0, f1=36.0, decay=0.34, thump=0.5):
    """A low hit: a sine that drops in pitch, plus a short dull thump of noise."""
    n = int(1.4 * SR)
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t / 0.055)
    x = np.sin(2.0 * math.pi * np.cumsum(f) / SR) * np.exp(-t / decay)
    nz = ss.sosfilt(ss.butter(2, 170.0, btype="low", fs=SR, output="sos"), rng.standard_normal(n)) * np.exp(-t / 0.07)
    x = x + thump * nz / (np.abs(nz).max() + 1e-9)
    x = np.tanh(1.4 * x / np.abs(x).max()) / math.tanh(1.4)
    x[: int(0.003 * SR)] *= np.linspace(0, 1, int(0.003 * SR))
    x *= np.clip((n / SR - t) / 0.3, 0, 1) ** 2               # let the tail reach silence
    return np.stack([x, x], axis=1), 0


def blast(rng):
    """The supernova: a burst of noise that darkens as it spreads, over a low impact."""
    dur = 2.2
    n = int(dur * SR)
    t = np.arange(n) / SR
    fc = 180.0 + 3000.0 * np.exp(-t / 0.35)
    env = np.exp(-t / 0.55) * np.clip(t / 0.004, 0, 1) * np.clip((dur - t) / 0.4, 0, 1) ** 2
    x = shaped_noise(dur, fc[:: SR // 200], 1.2, rng, stereo=0.8) * env[:, None]
    x = x / (np.abs(x).max() + 1e-9)
    low, _ = impact(rng, f0=70.0, f1=31.0, decay=0.6)
    x[: len(low)] += 0.9 * low[:n]
    return x / np.abs(x).max(), 0


# ----------------------------------------------------------------- cues -----
def cues(edit):
    """(time of the hit, kind, level in dB relative to the music around it, direction)."""
    out = []
    for c in edit.CLIPS[1:]:
        t = engine.bt(c.k0)
        tr, name = c.tin, type(c.tin).__name__
        soft = 1.0 if 16 <= c.k0 < 32 else 0.0          # the montage is dense: keep its air a little quieter
        if name == "Whip":
            out.append((t, "whoosh", -10.0 - soft, {"l": -1, "r": 1}.get({(-1, 0): "l", (1, 0): "r"}.get(tr.v), 0)))
        elif name in ("Zoom", "Spin"):
            out.append((t, "whoosh", -10.0 - soft, 0))
        elif name == "Iris":
            out.append((t, "impact", -6.0, 0))
            out.append((t, "whoosh", -9.0, 0))
    out += [
        (engine.bt(8), "riser:0.80", -8.0, 0),            # the warp into the title
        (engine.bt(14), "impact", -8.0, 0),               # the black hole
        (engine.bt(16), "riser:0.30", -9.0, 0),           # the name implodes ...
        (engine.bt(32), "blast", -6.0, 0),                # the supernova
        (engine.bt(40), "riser:1.10", -8.0, 0),           # the dive through the hole
    ]
    return sorted(out)


def render_sfx(edit, music, seed=5):
    rng = np.random.default_rng(seed)
    N = len(music)
    bus = np.zeros_like(music)
    log = []
    for t, kind, level, direction in cues(edit):
        if kind == "whoosh":
            sig, at = whoosh(rng, direction=direction)
        elif kind.startswith("riser"):
            sig, at = riser(rng, float(kind.split(":")[1]))
        elif kind == "impact":
            sig, at = impact(rng)
        else:
            sig, at = blast(rng)
        i0 = int(round(t * SR)) - at
        a, b = max(int((t - 0.6) * SR), 0), min(int((t + 0.6) * SR), N)
        ref = rms(music[a:b])                              # how loud the song is around this cut
        loud = sig[np.abs(sig).max(axis=1) > 0.25]         # the part of the effect that carries its level
        g = ref * db(level) / rms(loud)
        s0, s1 = max(i0, 0), min(i0 + len(sig), N)
        if s1 > s0:
            bus[s0:s1] += sig[s0 - i0:s1 - i0] * g
        log.append((round(t, 3), kind, round(20 * math.log10(g * np.abs(sig).max()), 1)))
    return bus, log


# ------------------------------------------------------------------ mix -----
def build(song_path, voice_path, out_path, edit, beat=15.0, drop=16.0, delay=0.05, tag_over_music_db=5.5, duck_db=-5.5,
          trim_db=-1.2, sfx=True, tag=True):
    y, sr = sf.read(song_path, always_2d=True)
    y = ss.resample_poly(y, SR, sr, axis=0)
    total = int(engine.DURATION * SR)
    if len(y) < total:
        y = np.concatenate([y, np.zeros((total - len(y), y.shape[1]))])
    N = len(y)
    t = np.arange(N) / SR
    info = {}
    music = y
    voice = np.zeros_like(y)
    if tag:
        stem, onset, n_word, sr0, dry = vt.build_tag(None, None, recording=voice_path, presence=0.6, air=0.18, wide=0.30,
                                                     wet=0.14, swell=0.26)
        t_word, t_drop = engine.bt(beat) + delay, engine.bt(drop)
        word_end = t_word + n_word / SR
        g = np.zeros(N)                                    # duck: under the word, released into the drop
        a0, a1 = t_word - 0.015, t_word + 0.07
        r0, r1 = max(word_end + 0.02, t_drop - 0.30), t_drop - 0.015
        assert r1 - r0 > 0.08, "the word runs into the drop"
        m = (t >= a0) & (t < a1)
        g[m] = np.linspace(0, 1, int(m.sum()))
        g[(t >= a1) & (t < r0)] = 1.0
        m = (t >= r0) & (t < r1)
        g[m] = 0.5 * (1 + np.cos(np.linspace(0, np.pi, int(m.sum()))))
        music = y * db(duck_db * g)[:, None]
        ducked = music[int(a1 * SR):int(word_end * SR)]
        word = stem[onset:onset + n_word]
        k = db(vt.rms_db(ducked) + tag_over_music_db - vt.rms_db(word))
        i0 = int(round(t_word * SR)) - onset
        s0, s1 = max(i0, 0), min(i0 + len(stem), N)
        voice[s0:s1] = stem[s0 - i0:s1 - i0] * k
        c0, c1 = int((t_drop - 0.02) * SR), int((t_drop + 0.18) * SR)      # the tail dies under the first hit
        voice[c0:c1] *= np.linspace(1, 0, c1 - c0)[:, None]
        voice[c1:] = 0.0
        info.update(word=(round(t_word, 3), round(word_end, 3)), tag_gain_db=round(20 * math.log10(k), 1),
                    word_rms_db=round(vt.rms_db(word * k), 1), ducked_music_rms_db=round(vt.rms_db(ducked), 1))
        base = os.path.splitext(out_path)[0]
        sf.write(base + "_tag.stem.wav", stem, SR, subtype="PCM_24")
        env = vt.envelope(voice.mean(axis=1), ms=12.0)     # per-frame loudness of the tag: drives the logo's glow
        fps = 60
        e = np.array([env[int(i * SR / fps):int((i + 1) * SR / fps)].max() for i in range(int(engine.DURATION * fps))])
        json.dump(dict(fps=fps, env=[round(float(x), 4) for x in e / (e.max() + 1e-12)], **info),
                  open(base + "_tag.json", "w"))
    fx = np.zeros_like(y)
    if sfx:
        fx, log = render_sfx(edit, y)
        info["sfx"] = log
    out = (music + voice + fx) * db(trim_db)
    n_in = int(0.012 * SR)
    out[:n_in] *= np.linspace(0, 1, n_in)[:, None]
    out, reduction = vt.limit(out, ceiling_db=-1.0)
    sf.write(out_path, out, SR, subtype="PCM_24")
    info.update(peak_dbfs=round(20 * math.log10(float(np.abs(out).max())), 2), max_limiting_db=round(reduction, 2))
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--song", required=True)
    ap.add_argument("--voice", default=os.path.join(HERE, "voice", "reditor_voice_v2.wav"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--edit", default=None)
    ap.add_argument("--no-sfx", action="store_true")
    ap.add_argument("--no-tag", action="store_true")
    a = ap.parse_args()
    info = build(a.song, a.voice, a.out, engine.load_edit(a.edit), sfx=not a.no_sfx, tag=not a.no_tag)
    print(json.dumps(info, indent=1))


if __name__ == "__main__":
    main()
