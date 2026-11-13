#!/usr/bin/env python3
"""Builds the spoken channel-name tag and mixes it into the song.

    python voice_tag.py --recording voice/reditor_voice.wav --song song_raw.wav --out song.wav
    python voice_tag.py --voice test_voice.onnx --song song_raw.wav --out song.wav

The word is either a recording (--recording) or synthesised with Piper (neural TTS,
runs offline) and deepened with Praat.  It is then designed like a producer tag: a
noise-vocoded whisper layer for air, a wide double, a dark plate and a reverse-reverb
swell that rises into the word.  The music is ducked under the word and released on
the drop.
"""
import argparse
import json
import math
import os
import sys

import numpy as np
import scipy.signal as ss
import soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SR = 48000


def db(x):
    return 10.0 ** (x / 20.0)


def rms_db(a):
    return 20.0 * math.log10(float(np.sqrt(np.mean(np.square(a)))) + 1e-12)


def synth(voice_path, text):
    from piper import PiperVoice
    from piper.config import SynthesisConfig
    v = PiperVoice.load(voice_path, config_path=voice_path + ".json")
    chunks = list(v.synthesize(text, syn_config=SynthesisConfig(length_scale=1.3)))
    a = np.concatenate([c.audio_float_array for c in chunks]).astype(np.float64)
    sr = chunks[0].sample_rate
    env = np.abs(a)
    idx = np.where(env > 0.02 * env.max())[0]
    a = a[max(idx[0] - int(0.01 * sr), 0):idx[-1] + int(0.03 * sr)]
    return a / np.abs(a).max(), sr


def deepen(a, sr, pitch_median, formant_ratio, stretch):
    """Praat 'Change gender': lower pitch + longer vocal tract + slower delivery."""
    import parselmouth
    snd = parselmouth.Sound(a, sr)
    out = parselmouth.praat.call(snd, "Change gender", 70, 500, formant_ratio, pitch_median, 0.9, stretch)
    b = out.values[0]
    return b / np.abs(b).max()


def band(lo, hi, x, order=4):
    sos = ss.butter(order, [lo, hi], btype="band", fs=SR, output="sos")
    return ss.sosfilt(sos, x)


def envelope(x, ms=8.0):
    n = int(SR * ms / 1000.0)
    k = np.hanning(2 * n + 1)
    return np.convolve(np.abs(x), k / k.sum(), mode="same")


def whisper(x, rng, n_bands=22):
    """Noise vocoder: the voice's band envelopes drive band-limited noise (a whisper)."""
    edges = np.geomspace(220.0, 7400.0, n_bands + 1)
    out = np.zeros_like(x)
    top_env = None
    for lo, hi in zip(edges[:-1], edges[1:]):
        e = envelope(band(lo, hi, x))
        out += band(lo, hi, rng.standard_normal(len(x))) * e
        if lo > 3800:
            top_env = e if top_env is None else top_env + e
    # a 16 kHz voice has nothing above 8 kHz: let its top bands drive some air up there
    out += band(8000.0, 13500.0, rng.standard_normal(len(x))) * top_env * 0.45
    return out / (np.abs(out).max() + 1e-9)


def plate(x, seconds, rng, bright=6000.0, predelay=0.02):
    """Stereo reverb by convolution with exponentially decaying, darkening noise."""
    n = int(SR * seconds)
    t = np.arange(n) / SR
    out = []
    for _ in range(2):
        ir = rng.standard_normal(n) * np.exp(-6.9 * t / seconds)
        ir = ss.sosfilt(ss.butter(2, bright, btype="low", fs=SR, output="sos"), ir)
        ir = ss.sosfilt(ss.butter(2, 180.0, btype="high", fs=SR, output="sos"), ir)
        ir[:int(0.004 * SR)] *= np.linspace(0, 1, int(0.004 * SR))
        ir = np.concatenate([np.zeros(int(predelay * SR)), ir])
        y = ss.fftconvolve(x, ir)
        out.append(y)
    y = np.stack(out, axis=1)
    return y / (np.abs(y).max() + 1e-9)


def load_voice(path):
    """A recorded voice instead of the synthetic one: mono, trimmed to the word."""
    a, sr = sf.read(path, always_2d=True)
    a = a.mean(axis=1)
    env = envelope_at(a, sr)
    idx = np.where(env > 0.05 * env.max())[0]
    a = a[max(idx[0] - int(0.01 * sr), 0):idx[-1] + int(0.03 * sr)]
    return a / np.abs(a).max(), sr


def envelope_at(x, sr, ms=10.0):
    n = max(int(sr * ms / 1000.0), 1)
    k = np.hanning(2 * n + 1)
    return np.convolve(np.abs(x), k / k.sum(), mode="same")


def build_tag(voice_path, text, seed=11, pitch_median=104.0, formant_ratio=0.93, stretch=1.08,
              pre=0.62, tail=1.6, recording=None, presence=0.85, air=0.34, wide=0.42, wet=0.16, swell=0.30):
    """Returns (stereo stem at 48 kHz, index of the word onset, word length in samples, ...)."""
    rng = np.random.default_rng(seed)
    if recording:
        deep16, sr0 = load_voice(recording)      # a real voice is used as it is
    else:
        dry16, sr0 = synth(voice_path, text)
        deep16 = deepen(dry16, sr0, pitch_median, formant_ratio, stretch)
    v = ss.resample_poly(deep16, SR, sr0)
    v = ss.sosfilt(ss.butter(2, 95.0, btype="high", fs=SR, output="sos"), v)
    # presence lift and gentle saturation so it cuts through a dense mix
    v = v + presence * band(1800.0, 5200.0, v, order=2)
    v = np.tanh(1.6 * v / np.abs(v).max()) / np.tanh(1.6)
    fade = int(0.012 * SR)
    v[:fade] *= np.linspace(0, 1, fade)
    v[-fade:] *= np.linspace(1, 0, fade)
    w = whisper(v, rng)
    n = len(v)

    pre_n, tail_n = int(pre * SR), int(tail * SR)
    L = pre_n + n + tail_n
    stem = np.zeros((L, 2))

    def put(sig, start, gain_l, gain_r):
        e = min(start + len(sig), L)
        stem[start:e, 0] += sig[:e - start] * gain_l
        stem[start:e, 1] += sig[:e - start] * gain_r

    put(v, pre_n, 1.0, 1.0)                                   # centre voice
    put(w, pre_n, air, air)                                   # whisper / air
    # wide double: two slightly detuned, slightly late copies
    for cents, delay, gl, gr in ((+9, 0.013, wide, 0.24 * wide), (-9, 0.019, 0.24 * wide, wide)):
        ratio = 2.0 ** (cents / 1200.0)
        d = ss.resample(v, int(round(len(v) / ratio)))
        put(d, pre_n + int(delay * SR), gl, gr)
    # dark plate on the voice + whisper
    rev = plate(v + 0.5 * w, 1.5, rng)
    stem[pre_n:pre_n + len(rev)][:L - pre_n] += rev[:L - pre_n] * wet
    # one eighth-note echo, band-limited, left-right
    echo = band(500.0, 3200.0, v, order=2)
    put(echo, pre_n + int(SR * (60.0 / 56.0) / 3.0), 0.05, 0.13)
    # reverse-reverb swell rising into the word
    sw = plate((v + 0.6 * w)[::-1], 1.1, rng, bright=4500.0, predelay=0.0)[::-1]
    sw = sw[-(n + pre_n):][:pre_n]                            # the part that precedes the word
    ramp = np.linspace(0.0, 1.0, len(sw)) ** 2.2
    hp = ss.butter(2, 320.0, btype="high", fs=SR, output="sos")
    sw = ss.sosfilt(hp, sw * ramp[:, None], axis=0)
    stem[pre_n - len(sw):pre_n] += sw / (np.abs(sw).max() + 1e-9) * swell
    stem /= np.abs(stem).max()
    return stem, pre_n, n, sr0, deep16


def limit(x, ceiling_db=-1.3, lookahead_ms=3.0):
    """Look-ahead peak limiter: never exceeds the ceiling, no make-up gain."""
    from scipy.ndimage import minimum_filter1d, uniform_filter1d
    c = db(ceiling_db)
    peak = np.abs(x).max(axis=1)
    need = np.minimum(1.0, c / np.maximum(peak, 1e-9))
    w = int(SR * lookahead_ms / 1000.0)
    g = minimum_filter1d(need, size=w, origin=-(w // 2))          # see w samples ahead
    g = uniform_filter1d(g, size=w, origin=(w - 1) // 2)          # glide into every reduction
    g = np.minimum(g, need)
    return x * g[:, None], float(20 * np.log10(g.min()))


def mix(song_path, out_path, stem, onset, n_word, t_word, t_drop, tag_over_music_db=5.0, duck_db=-5.5,
        pad_to=None, trim_db=-0.7):
    """Mixes the tag into the song with the music ducked under the word.

    With stem=None only the head fade, trim and limiter are applied, so the plain
    version sits at exactly the same level as the tagged one.
    """
    y, sr = sf.read(song_path, always_2d=True)
    y = ss.resample_poly(y, SR, sr, axis=0)
    if pad_to and len(y) < int(pad_to * SR):
        y = np.concatenate([y, np.zeros((int(pad_to * SR) - len(y), y.shape[1]))])
    N = len(y)
    t = np.arange(N) / SR
    info = {}
    tag = np.zeros_like(y)
    out = y
    if stem is not None:
        word_end = t_word + n_word / SR
        # duck: dip after the snare transient, hold under the word, release into the drop
        g = np.zeros(N)
        a0, a1 = t_word + 0.035, t_word + 0.12
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
        k = db(rms_db(ducked) + tag_over_music_db - rms_db(word))
        i0 = int(round(t_word * SR)) - onset
        s0, s1 = max(i0, 0), min(i0 + len(stem), N)
        tag[s0:s1] = stem[s0 - i0:s1 - i0] * k
        # after the drop the song is alone again: the tag's tail dies under the first hit
        c0, c1 = int((t_drop - 0.02) * SR), int((t_drop + 0.18) * SR)
        tag[c0:c1] *= np.linspace(1, 0, c1 - c0)[:, None]
        tag[c1:] = 0.0
        out = music + tag
        info = dict(tag_gain_db=20 * math.log10(k), word_rms_db=rms_db(word * k),
                    ducked_music_rms_db=rms_db(ducked), word=(t_word, word_end))
    n_in = int(0.012 * SR)
    out = out * db(trim_db)
    out[:n_in] *= np.linspace(0, 1, n_in)[:, None]
    out, reduction = limit(out)
    sf.write(out_path, out, SR, subtype="PCM_24")
    info.update(peak_dbfs=20 * math.log10(float(np.abs(out).max())), max_limiting_db=reduction)
    return info, envelope(tag.mean(axis=1), ms=12.0)


def main():
    import engine
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", help="Piper .onnx voice (its .onnx.json next to it)")
    ap.add_argument("--recording", help="use this recording of the name instead of the synthetic voice")
    ap.add_argument("--song", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--text", default="[[ ɹˈɛdɪtˌɔːɹ ]].",
                    help="what the synthetic voice says; [[ ]] takes IPA, so the name is spoken REH-di-tor")
    ap.add_argument("--beat", type=float, default=15.0)
    ap.add_argument("--drop", type=float, default=16.0)
    ap.add_argument("--plain-out", default=None, help="also write the song without the tag, same processing")
    a = ap.parse_args()
    if not (a.voice or a.recording):
        ap.error("give --voice (Piper model) or --recording (a WAV of the spoken name)")
    stem, onset, n_word, sr0, deep16 = build_tag(a.voice, a.text, recording=a.recording)
    t_word = engine.bt(a.beat) + 0.02
    info, env = mix(a.song, a.out, stem, onset, n_word, t_word, engine.bt(a.drop), pad_to=engine.DURATION)
    base = os.path.splitext(a.out)[0]
    sf.write(base + ".stem.wav", stem, SR, subtype="PCM_24")
    sf.write(base + ".dry16.wav", deep16, sr0, subtype="PCM_16")
    # per-frame (60 fps) loudness of the tag, for the audio-reactive glow of the logo
    fps = 60
    frames = int(engine.DURATION * fps)
    e = np.array([env[int(i * SR / fps):int((i + 1) * SR / fps)].max() if int(i * SR / fps) < len(env) else 0.0
                  for i in range(frames)])
    e = e / (e.max() + 1e-12)
    json.dump(dict(fps=fps, env=[round(float(x), 4) for x in e], **info), open(base + ".json", "w"))
    if a.plain_out:
        plain, _ = mix(a.song, a.plain_out, None, 0, 0, t_word, engine.bt(a.drop), pad_to=engine.DURATION)
        info["plain"] = plain
    print(json.dumps(info, indent=1))


if __name__ == "__main__":
    main()
