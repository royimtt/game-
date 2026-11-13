#!/usr/bin/env python3
"""Beat-synced montage renderer (v2).

A timeline of clips (video or stills) is rendered frame by frame in linear light:
retimed sources (optical-flow slow motion, shutter-integrated fast motion), a virtual
camera with real motion blur (zoom / spin / whip blur computed from the camera's
velocity), two-sided transitions that hide the cut inside the blur, drum-driven
reactions, depth-composited titles, bloom / halation / streaks, grade and grain.

    python engine.py board  --outdir board           # three frames per clip
    python engine.py frames 17.6 --count 8           # full-size frames at given times
    python engine.py strip  --beat 16 --n 40         # contact strip of consecutive frames
    python engine.py render --out out.mp4            # chunked, resumable render
"""
import argparse
import math
import os
import subprocess
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CLIPS = os.environ.get("SM_CLIPS", os.path.join(HERE, "clips"))
STILLS = os.environ.get("SM_STILLS", os.path.join(HERE, "stills"))
SONG = os.environ.get("SM_SONG", os.path.join(HERE, "song.wav"))

# ---------------------------------------------------------------- timing ----
BPM = 56.0
BEAT = 60.0 / BPM          # dotted-quarter pulse of the 12/8 groove
BEAT0 = 0.455              # time of beat 0 (first kick) in the song
DURATION = 54.0            # picture length; the music ends at 53.06 s


def bt(k):
    """Time in seconds of beat k (k + 1/3 is the second eighth of the beat)."""
    return BEAT0 + k * BEAT


def bf(k, fps):
    """Output frame on which beat k lands."""
    return int(math.floor(bt(k) * fps + 0.35))


# ---------------------------------------------------------------- maths -----
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def e_in(p, k=3.0):
    """0 -> 1, accelerating."""
    return clamp(p) ** k


def e_out(q, k=4.0):
    """1 -> 0, decelerating (fastest at q = 0)."""
    return (1.0 - clamp(q)) ** k


EASE = {
    "lin": lambda x: x,
    "io": smooth,
    "in": lambda x: x * x * x,
    "out": lambda x: 1 - (1 - x) ** 3,
    "out5": lambda x: 1 - (1 - x) ** 5,
    "in5": lambda x: x ** 5,
}

GAMMA = 2.2
_LIN_LUT = ((np.arange(256, dtype=np.float32) / 255.0) ** GAMMA).astype(np.float32)


def to_lin(u8):
    return cv2.LUT(u8, _LIN_LUT)


def frand(*key):
    """Deterministic pseudo-random float in [-1, 1] from integer keys."""
    h = 1469598103934665603
    for k in key:
        h = ((h ^ (int(k) & 0xFFFFFFFF)) * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    h ^= h >> 29
    h = (h * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
    h ^= h >> 32
    return (h & 0xFFFFFF) / float(0x7FFFFF) - 1.0


# -------------------------------------------------------------- sources -----
_probe_cache = {}


def probe(path):
    if path not in _probe_cache:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
             "stream=width,height,r_frame_rate", "-show_entries", "format=duration",
             "-of", "csv=p=0", path], capture_output=True, text=True).stdout.split()
        w, h, fr = out[0].split(",")[:3]
        num, den = fr.split("/")
        _probe_cache[path] = (int(w), int(h), float(num) / float(den), float(out[1]))
    return _probe_cache[path]


class VideoSource:
    """Sequential decoder with fractional-frame sampling.

    Positions are source frames counted from `start` seconds; requests must not go
    backwards by more than two frames.
    """

    def __init__(self, path, start, w, h, crop=None, flip=False):
        self.path = path
        vf = []
        if crop:
            vf.append("crop=" + crop)
        if flip:
            vf.append("hflip")
        vf.append(f"scale={w}:{h}:flags=lanczos:in_color_matrix=bt709:in_range=tv")
        cmd = ["ffmpeg", "-v", "error", "-ss", f"{max(start, 0):.4f}", "-i", path, "-an", "-sn",
               "-vf", ",".join(vf), "-pix_fmt", "rgb24", "-f", "rawvideo", "-"]
        self.p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=w * h * 3 * 2)
        self.w, self.h, self.n = w, h, w * h * 3
        self.idx = -1
        self.frames = {}
        self.eof = False
        self._flow_key = None
        self._flow = None
        self._dis = None

    def _next(self):
        if self.eof:
            return False
        buf = self.p.stdout.read(self.n)
        if len(buf) < self.n:
            self.eof = True
            return False
        self.idx += 1
        self.frames[self.idx] = np.frombuffer(buf, np.uint8).reshape(self.h, self.w, 3)
        for k in [k for k in self.frames if k < self.idx - 3]:
            del self.frames[k]
        return True

    def frame(self, i):
        i = max(int(i), 0)
        while self.idx < i and self._next():
            pass
        if not self.frames:
            self._next()
        if i in self.frames:
            return self.frames[i]
        return self.frames[min(max(i, min(self.frames)), max(self.frames))]

    def _interp(self, i, a):
        """Motion-compensated in-between frame (dense optical flow, both neighbours warped)."""
        A, B = self.frame(i), self.frame(i + 1)
        if A is B:
            return A
        if self._flow_key != i:
            sc = 640.0 / self.w
            sw, sh = int(self.w * sc), int(self.h * sc)
            ga = cv2.cvtColor(cv2.resize(A, (sw, sh), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2GRAY)
            gb = cv2.cvtColor(cv2.resize(B, (sw, sh), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2GRAY)
            if self._dis is None:
                self._dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
                self._gx, self._gy = np.meshgrid(np.arange(self.w, dtype=np.float32), np.arange(self.h, dtype=np.float32))
            fl = self._dis.calc(ga, gb, None)
            fl = cv2.GaussianBlur(fl, (0, 0), 1.5)
            fl = cv2.resize(fl, (self.w, self.h), interpolation=cv2.INTER_LINEAR) * (1.0 / sc)
            self._flow_key, self._flow = i, fl
        fl = self._flow
        ka, kb = np.float32(a), np.float32(1.0 - a)
        Aw = cv2.remap(A, self._gx - ka * fl[..., 0], self._gy - ka * fl[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        Bw = cv2.remap(B, self._gx + kb * fl[..., 0], self._gy + kb * fl[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        return cv2.addWeighted(Aw, 1.0 - a, Bw, a, 0.0)

    def sample(self, p, span, flow=True, shutter=0.7):
        """Linear-light image at source position p; `span` = source frames per output frame."""
        p, span = max(float(p), 0.0), float(span)
        if span >= 1.3:                      # fast motion: integrate the frames the shutter sees
            p1 = p + span * shutter
            ia, ib = int(math.floor(p)), int(math.ceil(p1 - 1e-6)) - 1
            acc, wsum = None, 0.0
            for i in range(ia, max(ib, ia) + 1):
                w = float(min(i + 1.0, p1) - max(float(i), p))
                if w < 0.03 and ib > ia:
                    continue
                lin = to_lin(self.frame(i))
                acc = lin * np.float32(w) if acc is None else cv2.scaleAdd(lin, w, acc)
                wsum += w
            return acc * np.float32(1.0 / wsum) if abs(wsum - 1.0) > 1e-6 else acc
        i = int(math.floor(p))
        a = p - i
        if a < 0.04:
            return to_lin(self.frame(i))
        if a > 0.96:
            return to_lin(self.frame(i + 1))
        if flow:
            return to_lin(self._interp(i, a))
        return cv2.addWeighted(to_lin(self.frame(i)), 1.0 - a, to_lin(self.frame(i + 1)), a, 0.0)

    def close(self):
        try:
            self.p.stdout.close()
            self.p.kill()
            self.p.wait()
        except Exception:
            pass


_still_cache = {}


class StillSource:
    """A still with a mip pyramid, so zooming out never aliases."""

    def __init__(self, path, max_side=7000):
        img = cv2.imread(path, cv2.IMREAD_COLOR)
        if img is None:
            raise IOError(f"cannot read {path}")
        h, w = img.shape[:2]
        if max(h, w) > max_side:
            s = max_side / float(max(h, w))
            img = cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
        self.levels = [cv2.cvtColor(img, cv2.COLOR_BGR2RGB)]
        self.h, self.w = self.levels[0].shape[:2]

    def level(self, k):
        while len(self.levels) <= k:
            a = self.levels[-1]
            self.levels.append(cv2.resize(a, (max(a.shape[1] // 2, 1), max(a.shape[0] // 2, 1)), interpolation=cv2.INTER_AREA))
        return self.levels[k]


def still(path):
    if path not in _still_cache:
        if len(_still_cache) > 5:
            _still_cache.pop(next(iter(_still_cache)))
        _still_cache[path] = StillSource(path)
    return _still_cache[path]


# ---------------------------------------------------------- transitions -----
IDENT = dict(z=1.0, dx=0.0, dy=0.0, rot=0.0, gain=1.0, glow=0.0, ca=0.0, rgb=0.0, ax=0.5, ay=0.5)


def merge(a, b):
    out = dict(a)
    for k, v in b.items():
        if k in ("z", "gain"):
            out[k] = out.get(k, 1.0) * v
        elif k in ("ax", "ay"):
            out[k] = v
        else:
            out[k] = out.get(k, 0.0) + v
    return out


class Cut:
    """Hard cut. `flash` adds an exposure burst on the first frames of the new shot."""
    pre = 0.0
    mix = None

    def __init__(self, flash=0.0, post=0.12, punch=0.0, rgb=0.0):
        self.flash, self.punch, self.rgb, self.post = flash, punch, rgb, post

    def out(self, p):
        return {}

    def inc(self, q):
        d = {}
        if self.flash:
            d["gain"] = 1.0 + self.flash * e_out(q, 3)
            d["glow"] = 0.8 * self.flash * e_out(q, 2)
        if self.punch:
            d["z"] = 1.0 + self.punch * e_out(q, 4)
        if self.rgb:
            d["rgb"] = self.rgb * e_out(q, 2)
        return d


class Punch(Cut):
    """Cut that lands zoomed-in and settles: the classic beat hit."""

    def __init__(self, punch=0.28, flash=0.9, post=0.34, rgb=0.004):
        Cut.__init__(self, flash=flash, post=post, punch=punch, rgb=rgb)


class Zoom:
    """Fly-through. kind='in': both shots grow (camera moves forward); 'out': both shrink."""
    mix = None

    def __init__(self, kind="in", s_out=2.3, s_in=2.6, pre=0.11, post=0.34, flash=0.7, at=(0.5, 0.5), rot=0.0, dark=0.0):
        self.kind, self.s_out, self.s_in, self.pre, self.post, self.flash, self.at, self.rot, self.dark = \
            kind, s_out, s_in, pre, post, flash, at, rot, dark

    def out(self, p):
        e = e_in(p)
        z = self.s_out ** e if self.kind == "in" else self.s_out ** (-e)
        return dict(z=z, gain=1.0 + 0.9 * self.flash * e, glow=0.6 * self.flash * e, ax=self.at[0], ay=self.at[1],
                    rot=self.rot * e, ca=0.012 * e)

    def inc(self, q):
        e = e_out(q, 5.0)
        z = self.s_in ** (-e) if self.kind == "in" else self.s_in ** e
        gain = (1.0 + self.flash * e_out(q, 3)) * (1.0 - self.dark * e_out(q, 2))     # dark: arrive out of blackness
        return dict(z=z, gain=gain, glow=self.flash * e_out(q, 2), rot=-self.rot * e, ca=0.014 * e,
                    ax=self.at[0], ay=self.at[1])


class Whip:
    """Whip pan: both shots travel the same way; `d` is the direction the camera turns."""
    mix = None
    DIR = {"l": (-1, 0), "r": (1, 0), "u": (0, -1), "d": (0, 1)}

    def __init__(self, d="l", travel=1.15, pre=0.10, post=0.34, flash=0.5, tilt=0.0, zoom=0.12):
        self.v = self.DIR[d]
        self.travel, self.pre, self.post, self.flash, self.tilt, self.zoom = travel, pre, post, flash, tilt, zoom

    def out(self, p):
        e = e_in(p)
        k = self.travel * (1.0 if self.v[0] else 9.0 / 16.0)
        return dict(dx=-self.v[0] * k * e, dy=-self.v[1] * k * e, rot=self.tilt * e, z=1.0 + self.zoom * e,
                    gain=1.0 + 0.6 * self.flash * e, glow=0.4 * self.flash * e)

    def inc(self, q):
        e = e_out(q, 5.0)
        k = self.travel * (1.0 if self.v[0] else 9.0 / 16.0)
        return dict(dx=self.v[0] * k * e, dy=self.v[1] * k * e, rot=-self.tilt * e, z=1.0 + self.zoom * e,
                    gain=1.0 + self.flash * e_out(q, 3), glow=0.7 * self.flash * e_out(q, 2))


class Spin:
    """Roll transition with rotational blur."""
    mix = None

    def __init__(self, deg=60.0, zoom=0.45, pre=0.11, post=0.36, flash=0.6):
        self.deg, self.zoom, self.pre, self.post, self.flash = deg, zoom, pre, post, flash

    def out(self, p):
        e = e_in(p)
        return dict(rot=self.deg * e, z=1.0 + self.zoom * e, gain=1.0 + 0.7 * self.flash * e, glow=0.5 * self.flash * e)

    def inc(self, q):
        e = e_out(q)
        return dict(rot=-self.deg * e, z=1.0 + self.zoom * e, gain=1.0 + self.flash * e_out(q, 3),
                    glow=0.8 * self.flash * e_out(q, 2))


class Dissolve:
    """Cross-dissolve through light; centred on the cut."""
    pre = post = 0.0

    def __init__(self, dur=0.5, glow=0.6):
        self.dur, self.glow = dur, glow
        self.mix = ("xfade", dur / 2.0, dur / 2.0)

    def out(self, p):
        return {}

    def inc(self, q):
        return {}

    def blend(self, a, b, x, ctx):
        k = smooth(x)
        out = cv2.addWeighted(a, 1.0 - k, b, k, 0.0)
        ctx["glow"] = ctx.get("glow", 0.0) + self.glow * math.sin(math.pi * clamp(x))
        return out


class Iris:
    """The new shot opens from a point (a star, an event horizon) behind a glowing rim."""
    pre = post = 0.0

    def __init__(self, at=(0.5, 0.5), dur=0.45, soft=0.035, rim=1.6, color=(0.8, 0.9, 1.0), ease="in", flash=0.0,
                 post=0.0, punch=0.0):
        self.at, self.dur, self.soft, self.rim, self.color, self.ease, self.flash = at, dur, soft, rim, color, ease, flash
        self.post, self.punch = post, punch
        self.mix = ("iris", 0.0, dur)

    def out(self, p):
        return {}

    def inc(self, q):
        if not self.punch:
            return {}
        return dict(z=1.0 + self.punch * e_out(q, 3), ax=self.at[0], ay=self.at[1])

    def blend(self, a, b, x, ctx):
        H, W = a.shape[:2]
        r = ctx["grid_r"](self.at)
        g = e_in(x, 2.2) if self.ease == "in" else 1.0 - (1.0 - clamp(x)) ** 2.4
        rad = (1.25 * g + 0.02 * x) * W
        if self.flash:
            ctx["glow"] = ctx.get("glow", 0.0) + self.flash * (1.0 - clamp(x)) ** 2
        m = np.clip((rad - r) / (self.soft * W) + 0.5, 0.0, 1.0)
        m3 = cv2.merge([m, m, m])
        out = a * (1.0 - m3) + b * m3
        k = self.rim * (1.0 - clamp(x)) ** 1.5
        wd = 0.004 * W + 0.012 * rad
        for i, off in enumerate((0.006, 0.0, -0.006)):                       # the rim splits like a prism
            out[..., i] += np.exp(-((r - rad * (1.0 + off)) / wd) ** 2) * (k * self.color[i])
        out += (np.exp(-((r - rad) / (4.0 * wd)) ** 2) * (0.25 * k))[..., None] * np.array(self.color, np.float32)
        return out


# ---------------------------------------------------------------- clips -----
CLIP_DEFAULTS = dict(
    t_in=0.0,            # source in-point (s) of video clips
    speed=1.0,           # playback rate (1 = real time) or [(u, rate), ...] for a speed ramp
    flow=True,           # optical-flow interpolation for slow motion
    crop=None, flip=False,
    border="mirror",     # what lies beyond the picture when a transition shrinks it: "mirror" or "black"
    keys=None,           # camera keys [(u, zoom, cx, cy, rot, ease)]; default: slow push
    z=(1.03, 1.10), c=(0.5, 0.5), c1=None, rot=(0.0, 0.0), ease="lin",
    tin=None,            # transition into this clip
    exposure=1.0, sat=1.0, gamma=1.0, tone=None, black=0.0,
    sharpen=None,        # overrides the grade's sharpening (noisy night footage wants less)
    bloom=0.5, streak=0.2,
    kick=1.0, snare=1.0,  # strength of the drum reactions on this clip
    occ=None,            # what stands in front of depth-composited text: dict(lum=(lo, hi), discs=[...])
    note="",
)


class Clip:
    def __init__(self, cid, src, k0, k1, **kw):
        self.id, self.src, self.k0, self.k1 = cid, src, k0, k1
        d = dict(CLIP_DEFAULTS)
        bad = set(kw) - set(d)
        if bad:
            raise KeyError(f"unknown clip option(s) {bad} in {cid}")
        d.update(kw)
        self.__dict__.update(d)
        self.kind = "still" if src.lower().endswith((".jpg", ".jpeg", ".png", ".tif")) else "video"
        self.path = os.path.join(STILLS if self.kind == "still" else CLIPS, src)
        if self.keys is None:
            c1 = self.c1 or self.c
            self.keys = [(0.0, self.z[0], self.c[0], self.c[1], self.rot[0]), (1.0, self.z[1], c1[0], c1[1], self.rot[1], self.ease)]

    def cam(self, p):
        ks = self.keys
        a, b = ks[0], ks[-1]
        if len(ks) == 1:
            return a[1], a[2], a[3], a[4]
        if p <= ks[0][0]:
            a, b = ks[0], ks[1]
        elif p >= ks[-1][0]:
            a, b = ks[-2], ks[-1]
        else:
            for i in range(len(ks) - 1):
                if ks[i][0] <= p <= ks[i + 1][0]:
                    a, b = ks[i], ks[i + 1]
                    break
        f = (p - a[0]) / (b[0] - a[0])
        if 0.0 <= f <= 1.0:
            f = EASE[b[5] if len(b) > 5 else "lin"](f)
        z = math.exp(math.log(a[1]) + (math.log(b[1]) - math.log(a[1])) * f)     # outside the keys: keep drifting
        return z, a[2] + (b[2] - a[2]) * f, a[3] + (b[3] - a[3]) * f, a[4] + (b[4] - a[4]) * f


def layout(clips, fps):
    total = int(round(DURATION * fps))
    for i, c in enumerate(clips):
        c.f0 = 0 if i == 0 else bf(c.k0, fps)
    for i, c in enumerate(clips):
        c.f1 = clips[i + 1].f0 if i + 1 < len(clips) else total
        c.index = i
        c.prev = clips[i - 1] if i else None
        c.next = clips[i + 1] if i + 1 < len(clips) else None
        assert c.f1 > c.f0, f"clip {c.id} is empty"
    return total


def speed_at(c, u):
    s = c.speed
    if not isinstance(s, (list, tuple)):
        return float(s)
    if u <= s[0][0]:
        return s[0][1]
    for (u0, s0), (u1, s1) in zip(s, s[1:]):
        if u0 <= u <= u1:
            return s0 + (s1 - s0) * (u - u0) / max(u1 - u0, 1e-9)
    return s[-1][1]


def positions(c, fps, lead, tail):
    """Source frame position (relative to t_in) for output frames f0-lead .. f1+tail."""
    sfps = probe(c.path)[2]
    n = c.f1 - c.f0
    js = np.arange(-lead, n + tail + 1)
    rate = np.array([speed_at(c, clamp(j / max(n, 1))) for j in js]) * sfps / fps
    pos = np.concatenate([[0.0], np.cumsum(rate[:-1])])
    pos -= pos[lead]                     # position 0 at the cut-in frame
    return pos, rate


# ------------------------------------------------------------ blur ops ------
def blur_dir(img, px, horizontal=True):
    L = int(min(abs(px), 0.9 * (img.shape[1] if horizontal else img.shape[0])))
    if L < 3:
        return img
    k = (L | 1, 1) if horizontal else (1, L | 1)
    k2 = ((k[0] // 2) | 1, (k[1] // 2) | 1)
    return cv2.blur(cv2.blur(img, k, borderType=cv2.BORDER_REFLECT_101), k2, borderType=cv2.BORDER_REFLECT_101)


def _far(W, H, cx, cy):
    return max(math.hypot(cx, cy), math.hypot(W - cx, cy), math.hypot(cx, H - cy), math.hypot(W - cx, H - cy))


def _to_polar(img, cx, cy, far, Wr, Ha, log):
    """Polar resampling with reflected borders (cv2.warpPolar leaves samples outside the picture undefined)."""
    i = np.arange(Wr, dtype=np.float32)[None, :]
    th = (np.arange(Ha, dtype=np.float32) * (2.0 * math.pi / Ha))[:, None]
    r = np.exp(i * (math.log(far) / (Wr - 1))) if log else i * (far / (Wr - 1))
    return cv2.remap(img, cx + r * np.cos(th), cy + r * np.sin(th), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)


def _from_polar(pol, W, H, cx, cy, far, log):
    Ha, Wr = pol.shape[:2]
    dx, dy = np.meshgrid(np.arange(W, dtype=np.float32) - np.float32(cx), np.arange(H, dtype=np.float32) - np.float32(cy))
    r = np.sqrt(dx * dx + dy * dy)
    if log:
        i = np.log(np.maximum(r, 1.0)) * ((Wr - 1) / math.log(far))
    else:
        i = r * ((Wr - 1) / far)
    j = np.mod(np.arctan2(dy, dx) * (Ha / (2.0 * math.pi)), Ha) + 2.0
    pol = cv2.copyMakeBorder(pol, 2, 2, 0, 0, cv2.BORDER_WRAP)
    return cv2.remap(pol, i.astype(np.float32), j.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE), r


def blur_zoom(img, center, ratio):
    """Radial motion blur for a zoom by `ratio` during the shutter."""
    H, W = img.shape[:2]
    lr = abs(math.log(max(ratio, 1e-6)))
    cx, cy = center
    far = _far(W, H, cx, cy)
    travel = far * (math.exp(lr) - 1.0)
    if travel < 1.5:
        return img
    if lr < 0.07:                                      # small: a few rescaled copies (stays sharp at the centre)
        n = int(min(max(math.ceil(travel / 3.0), 2), 14))
        acc = np.zeros_like(img)
        for i in range(n):
            s = math.exp(lr * (i / (n - 1.0) - 0.5))
            m = np.array([[s, 0, cx * (1 - s)], [0, s, cy * (1 - s)]], dtype=np.float64)
            acc += cv2.warpAffine(img, m, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
        return acc * (1.0 / n)
    # large: box blur along log-radius in log-polar space
    Wr, Ha = 1024, 1536
    pol = _to_polar(img, cx, cy, far, Wr, Ha, True)
    k = int(max(lr / math.log(far) * Wr, 1)) | 1
    pol = cv2.blur(pol, (k, 1), borderType=cv2.BORDER_REPLICATE)
    out, r = _from_polar(pol, W, H, cx, cy, far, True)
    w = np.clip((r * (math.exp(lr) - 1.0) - 2.0) / 6.0, 0.0, 1.0)     # the round trip is soft near the centre
    w3 = cv2.merge([w, w, w])
    return img * (1.0 - w3) + out * w3


def blur_spin(img, center, deg):
    """Rotational motion blur for a roll of `deg` degrees during the shutter."""
    H, W = img.shape[:2]
    cx, cy = center
    far = _far(W, H, cx, cy)
    if abs(math.radians(deg)) * far < 2.0:
        return img
    Wr, Ha = 900, 2160
    pol = _to_polar(img, cx, cy, far, Wr, Ha, False)
    k = int(max(abs(deg) / 360.0 * Ha, 1)) | 1
    pad = k // 2 + 1
    pol = cv2.copyMakeBorder(pol, pad, pad, 0, 0, cv2.BORDER_WRAP)
    pol = np.ascontiguousarray(cv2.blur(pol, (1, k))[pad:-pad])
    out, r = _from_polar(pol, W, H, cx, cy, far, False)
    w = np.clip((r * abs(math.radians(deg)) - 2.0) / 6.0, 0.0, 1.0)
    w3 = cv2.merge([w, w, w])
    return img * (1.0 - w3) + out * w3


# -------------------------------------------------------------- finishing ---
class Look:
    def __init__(self, W, H, seed=7):
        self.W, self.H = W, H
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.xx, self.yy = xx, yy
        nx = (xx - W / 2) / (W / 2)
        ny = (yy - H / 2) / (W / 2)
        self.r2 = nx * nx + ny * ny
        v = (1.0 - 0.26 * np.clip(self.r2, 0, 2) ** 1.3).astype(np.float32)
        self.vig3 = cv2.merge([v, v, v])
        rng = np.random.default_rng(seed)
        self.grain = []
        for _ in range(6):
            g = rng.standard_normal((H + 96, W + 96)).astype(np.float32)
            g = cv2.GaussianBlur(g, (0, 0), 0.62 * W / 1920.0 + 0.25)
            self.grain.append(g / g.std())

    def grain_field(self, f):
        g = self.grain[f % len(self.grain)]
        oy, ox = int((frand(f, 11) + 1) * 47), int((frand(f, 12) + 1) * 47)
        return g[oy:oy + self.H, ox:ox + self.W]


def add_bloom(img, strength, streak, halation, thresh=0.6):
    """Glow, anamorphic streaks and film halation from the highlights (linear light)."""
    H, W = img.shape[:2]
    qw, qh = W // 4, H // 4
    s = W / 1920.0
    small = cv2.resize(img, (qw, qh), interpolation=cv2.INTER_AREA)
    bright = np.maximum(small - thresh, 0.0)
    g1 = cv2.GaussianBlur(bright, (0, 0), 4.0 * s)
    tiny = cv2.resize(bright, (qw // 4, qh // 4), interpolation=cv2.INTER_AREA)
    g2 = cv2.GaussianBlur(tiny, (0, 0), 5.0 * s)
    g3 = cv2.GaussianBlur(tiny, (0, 0), 16.0 * s)
    glow = g1 * 0.5 + cv2.resize(g2 * 0.6 + g3 * 0.5, (qw, qh), interpolation=cv2.INTER_LINEAR)
    glow *= strength
    if halation > 0:
        hl = cv2.GaussianBlur(np.maximum(small - 0.8, 0.0).max(axis=2), (0, 0), 2.2 * s) * halation
        glow[..., 0] += hl
        glow[..., 1] += hl * 0.32
        glow[..., 2] += hl * 0.08
    if streak > 0:
        hot = np.maximum(small - 0.85, 0.0)
        lum = small.max(axis=2)
        area = cv2.GaussianBlur((lum > 0.5).astype(np.float32), (0, 0), qw / 14.0)
        hot *= np.clip(1.0 - 3.0 * area, 0.0, 1.0)[:, :, None]       # only compact highlights streak
        hot = cv2.GaussianBlur(hot, (0, 0), 1.0 * s)
        st = (cv2.blur(hot, (int(qw * 0.07) | 1, 1)) * 0.5 + cv2.blur(hot, (int(qw * 0.22) | 1, 1)) * 0.32
              + cv2.blur(hot, (int(qw * 0.6) | 1, 1)) * 0.18)
        st[..., 0] *= 0.5
        st[..., 1] *= 0.78
        glow += st * (8.0 * streak)
    glow = cv2.resize(glow, (W, H), interpolation=cv2.INTER_LINEAR)
    cv2.add(img, glow, img)
    return img


def finish(img, look, f, grade, grain_amp):
    """Linear float image -> graded 8-bit RGB."""
    cv2.multiply(img, look.vig3, img)
    _, over = cv2.threshold(img - 0.70, 0.0, 0.0, cv2.THRESH_TOZERO)      # soft highlight shoulder
    img = cv2.min(img, 0.70 + 0.30 * (1.0 - cv2.exp(over * (-1.0 / 0.30))))
    _, img = cv2.threshold(img, 0.0, 0.0, cv2.THRESH_TOZERO)
    g = cv2.pow(img, (1.0 / GAMMA) * grade.get("gamma", 1.0))
    sat = grade.get("sat", 1.0)
    lw = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    if abs(sat - 1.0) > 1e-3:
        g = cv2.transform(g, np.eye(3, dtype=np.float32) * sat + (1 - sat) * lw[None, :])
    np.clip(g, 0.0, 1.0, out=g)
    c = grade.get("contrast", 0.22)                                       # filmic S-curve
    g = cv2.addWeighted(g, 1.0 - c, g * g * (3.0 - 2.0 * g), c, 0.0)
    b = 0.010 + grade.get("black", 0.0)
    g = (g - b) * (1.0 / (1.0 - b))
    sh = grade.get("sharpen", 0.0)
    if sh > 0:
        g = cv2.addWeighted(g, 1.0 + sh, cv2.GaussianBlur(g, (0, 0), 1.1 * look.W / 1920.0), -sh, 0.0)
    if grain_amp > 0:
        n = look.grain_field(f)
        lum = cv2.transform(g, lw.reshape(1, 3))
        n = n * (0.30 + 2.6 * lum * (1.0 - np.minimum(lum, 1.0))) * grain_amp
        g += cv2.merge([n, n, n])
    return np.clip(g * 255.0 + 0.5, 0, 255).astype(np.uint8)


# ----------------------------------------------------------------- type -----
class Type:
    """Rasterised glyphs of one font (supersampled), drawn with per-letter transforms."""

    def __init__(self, font, size, axes=None):
        from PIL import ImageFont
        self.size = size
        self.ss = 2
        self.font = ImageFont.truetype(font, max(int(size * self.ss), 2))
        if axes:
            vals = []
            for a in self.font.get_variation_axes():
                name = a["name"] if isinstance(a["name"], str) else a["name"].decode()
                key = "wght" if "eight" in name else "wdth" if "idth" in name else "opsz" if "ptical" in name else name
                vals.append(axes.get(key, a["default"]))
            self.font.set_variation_by_axes(vals)
        self._g = {}
        l, t, r, b = self.font.getbbox("HEX")
        self.cap_top, self.cap_h = t / self.ss, (b - t) / self.ss

    def adv(self, ch):
        return self.font.getlength(ch) / self.ss

    def glyph(self, ch):
        if ch not in self._g:
            from PIL import Image, ImageDraw
            pad = int(self.size * self.ss * 0.3)
            w = max(int(self.font.getlength(ch)) + 2 * pad, 2)
            h = max(int(self.cap_h * self.ss * 1.5) + 2 * pad, 2)
            im = Image.new("L", (w, h), 0)
            ImageDraw.Draw(im).text((pad, pad - int(self.cap_top * self.ss)), ch, font=self.font, fill=255)
            m = cv2.resize(np.asarray(im, np.float32) / 255.0, (max(w // self.ss, 1), max(h // self.ss, 1)),
                           interpolation=cv2.INTER_AREA)
            self._g[ch] = (m, pad / self.ss, pad / self.ss)
        return self._g[ch]

    def layout(self, text, tracking=0.0):
        """x offsets (left of each advance box) and total width at scale 1."""
        xs, x = [], 0.0
        for ch in text:
            xs.append(x)
            x += self.adv(ch) + tracking * self.size
        return xs, x - tracking * self.size

    def draw(self, canvas, ch, x, y, scale=1.0, gain=1.0, about=None):
        """Max-composite glyph `ch`, advance-box origin at (x, y = cap top), scaled about `about`."""
        m, ox, oy = self.glyph(ch)
        H, W = canvas.shape[:2]
        if about is None:
            about = (x + self.adv(ch) / 2.0, y + self.cap_h / 2.0)
        tx = about[0] + scale * (x - ox - about[0])
        ty = about[1] + scale * (y - oy - about[1])
        M = np.array([[scale, 0, tx], [0, scale, ty]], dtype=np.float64)
        layer = cv2.warpAffine(m, M, (W, H), flags=cv2.INTER_LINEAR)
        if gain != 1.0:
            layer *= gain
        np.maximum(canvas, layer, out=canvas)
        return canvas


# ------------------------------------------------------------- renderer -----
class Renderer:
    def __init__(self, edit, W, H, fps, grain=0.009):
        self.edit, self.W, self.H, self.fps, self.grain = edit, W, H, fps, grain
        self.clips = edit.CLIPS
        self.total = layout(self.clips, fps)
        self.look = Look(W, H)
        self.src = {}
        self.pos = {}
        self.grade = dict(getattr(edit, "GRADE", {}))
        self.shutter = 0.7
        self.kick = np.zeros(self.total + 2, np.float32)
        self.snare = np.zeros(self.total + 2, np.float32)
        for k, kind, s in getattr(edit, "HITS", []):          # (beat, 'k' | 's', strength)
            f0 = bf(k, fps)
            tau = (0.11 if kind == "k" else 0.075) * fps
            arr = self.kick if kind == "k" else self.snare
            for f in range(max(f0, 0), min(f0 + int(6 * tau), self.total)):
                arr[f] = max(arr[f], s * math.exp(-(f - f0) / tau))
        self._rgrid = {}
        self.overlays = edit.overlays(self) if hasattr(edit, "overlays") else []

    def grid_r(self, at):
        key = (round(at[0], 4), round(at[1], 4))
        if key not in self._rgrid:
            if len(self._rgrid) > 6:
                self._rgrid.clear()
            self._rgrid[key] = np.hypot(self.look.xx - at[0] * self.W, self.look.yy - at[1] * self.H)
        return self._rgrid[key]

    # ---- sources
    def lead_tail(self, c):
        lead = tail = 2
        if c.tin is not None and c.tin.mix:
            lead = max(lead, int(math.ceil(c.tin.mix[1] * self.fps)) + 2)
        if c.next is not None and c.next.tin is not None and c.next.tin.mix:
            tail = max(tail, int(math.ceil(c.next.tin.mix[2] * self.fps)) + 2)
        return lead, tail

    def decode_size(self, c):
        sw, sh, sfps, dur = probe(c.path)
        if c.crop:
            sw, sh = (int(v) for v in c.crop.split(":")[:2])
        zmax = max(k[1] for k in c.keys) * 1.12
        w = int(min(sw, math.ceil(self.W * min(zmax, 1.7) / 16) * 16))
        w = max(w, min(sw, self.W))
        return w, int(round(w * sh / sw / 2) * 2)

    def source(self, c, f):
        """Opened lazily at the first frame a worker needs (so chunks can start anywhere)."""
        if c.index not in self.src:
            if c.kind == "still":
                self.src[c.index] = still(c.path)
            else:
                lead, tail = self.lead_tail(c)
                pos, rate = positions(c, self.fps, lead, tail)
                j = int(clamp(f - c.f0 + lead, 0, len(pos) - 1))
                sfps = probe(c.path)[2]
                first = math.floor(max(pos[j] - 2.0, -c.t_in * sfps))     # first source frame this reader decodes
                w, h = self.decode_size(c)
                self.src[c.index] = VideoSource(c.path, c.t_in + first / sfps, w, h, crop=c.crop, flip=c.flip)
                self.pos[c.index] = (pos, rate, lead, first)
        return self.src[c.index]

    def release(self, f):
        for i in [i for i in self.src if self.clips[i].f1 + self.lead_tail(self.clips[i])[1] + 2 < f]:
            s = self.src.pop(i)
            if isinstance(s, VideoSource):
                s.close()
            self.pos.pop(i, None)

    # ---- camera
    def state(self, c, tf):
        fps = self.fps
        n = max(c.f1 - c.f0, 1)
        tau, u = (tf - c.f0) / fps, (c.f1 - tf) / fps
        z, cx, cy, rot = c.cam((tf - c.f0) / n)
        m = dict(IDENT)
        if c.tin is not None and c.tin.post > 0 and tau < c.tin.post:
            m = merge(m, c.tin.inc(max(tau, 0.0) / c.tin.post))
        nx = c.next
        if nx is not None and nx.tin is not None and nx.tin.pre > 0 and u < nx.tin.pre:
            m = merge(m, nx.tin.out(1.0 - max(u, 0.0) / nx.tin.pre))
        fi = int(clamp(math.floor(tf), 0, self.total))
        K, S = float(self.kick[fi]) * c.kick, float(self.snare[fi]) * c.snare
        m["z"] *= 1.0 + 0.045 * K + 0.02 * S
        m["dx"] += 0.0045 * S * frand(fi, 1)
        m["dy"] += 0.0045 * S * frand(fi, 2)
        m["rot"] += 0.35 * S * frand(fi, 3)
        m["gain"] *= 1.0 + 0.10 * K + 0.07 * S
        m["glow"] += 0.35 * K + 0.25 * S
        m["rgb"] += 0.0022 * S
        return z, cx, cy, rot, m

    def matrix(self, sw, sh, z, cx, cy, rot, m):
        """3x3 map from output pixels to source pixels."""
        W, H = self.W, self.H
        b = min(sw / float(W), sh / float(H))
        hw, hh = 0.5 * W * b / z / sw, 0.5 * H * b / z / sh       # keep the base view inside the picture
        cx = clamp(cx, hw, 1 - hw) if hw < 0.5 else 0.5
        cy = clamp(cy, hh, 1 - hh) if hh < 0.5 else 0.5
        th = math.radians(rot)
        s = b / z
        base = np.array([[math.cos(th) * s, -math.sin(th) * s, 0.0], [math.sin(th) * s, math.cos(th) * s, 0.0], [0, 0, 1.0]])
        base[:2, 2] = [cx * sw - base[0, 0] * W / 2 - base[0, 1] * H / 2, cy * sh - base[1, 0] * W / 2 - base[1, 1] * H / 2]
        ax, ay = m["ax"] * W, m["ay"] * H
        tt = math.radians(-m["rot"])
        k = 1.0 / m["z"]
        tr = np.array([[math.cos(tt) * k, -math.sin(tt) * k, 0.0], [math.sin(tt) * k, math.cos(tt) * k, 0.0], [0, 0, 1.0]])
        ox, oy = ax + m["dx"] * W, ay + m["dy"] * W
        tr[:2, 2] = [ax - tr[0, 0] * ox - tr[0, 1] * oy, ay - tr[1, 0] * ox - tr[1, 1] * oy]
        return base @ tr

    def layer(self, c, f):
        """One clip at output frame f: warped through the camera, motion-blurred, exposed."""
        W, H = self.W, self.H
        src = self.source(c, f)
        edge = cv2.BORDER_CONSTANT if c.border == "black" else cv2.BORDER_REFLECT_101
        za, cxa, cya, ra, ma = self.state(c, f)
        zb, cxb, cyb, rb, mb = self.state(c, f + self.shutter)
        zm, cxm, cym, rm, mm = self.state(c, f + self.shutter / 2)
        if c.kind == "still":
            M = self.matrix(src.w, src.h, zm, cxm, cym, rm, mm)
            scale = math.sqrt(abs(M[0, 0] * M[1, 1] - M[0, 1] * M[1, 0]))       # source px per output px
            L = int(clamp(math.floor(math.log2(max(scale, 1e-6))), 0, 6))
            lev = src.level(L)
            k = 1.0 / (1 << L)
            ML = M[:2].copy() * k
            ML[:, 2] += 0.5 * k - 0.5
            img = to_lin(cv2.warpAffine(lev, ML, (W, H), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=edge))
        else:
            pos, rate, lead, first = self.pos[c.index]
            j = int(clamp(f - c.f0 + lead, 0, len(pos) - 2))
            frame = src.sample(pos[j] - first, rate[j], flow=c.flow, shutter=self.shutter)
            sh, sw = frame.shape[:2]
            M = self.matrix(sw, sh, zm, cxm, cym, rm, mm)
            img = cv2.warpAffine(frame, M[:2], (W, H), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=edge)
            np.maximum(img, 0.0, out=img)
        # motion blur from the camera's velocity over the shutter
        anchor = (mm["ax"] * W + mm["dx"] * W, mm["ay"] * H + mm["dy"] * W)
        lr = abs(math.log((zb * mb["z"]) / (za * ma["z"])))
        if mm["z"] < 0.995:                    # shrunk by a transition: its mirrored surround must never read as picture
            lr = max(1.5 * lr, -0.75 * math.log(mm["z"]))
        if lr > 0.0015:
            img = blur_zoom(img, anchor, math.exp(lr))
        dr = (rb + mb["rot"]) - (ra + ma["rot"])
        if abs(dr) > 0.08:
            img = blur_spin(img, anchor, dr)
        bx, by = abs(mb["dx"] - ma["dx"]) * W * 1.5, abs(mb["dy"] - ma["dy"]) * W * 1.5
        bx = max(bx, 0.85 * (abs(mm["dx"]) - 0.012) * W)       # same for a shot that is still sliding in
        by = max(by, 0.85 * (abs(mm["dy"]) - 0.012) * W)
        if bx > 3:
            img = blur_dir(img, bx, True)
        if by > 3:
            img = blur_dir(img, by, False)
        if mm["ca"] > 4e-4 or mm["rgb"] > 4e-4:
            ch = list(cv2.split(img))
            if mm["ca"] > 4e-4:                       # lateral chromatic aberration (red out, blue in)
                for i, sgn in ((0, 1.0), (2, -1.0)):
                    s = 1.0 + sgn * mm["ca"]
                    mat = np.array([[s, 0, W / 2 * (1 - s)], [0, s, H / 2 * (1 - s)]], dtype=np.float64)
                    ch[i] = cv2.warpAffine(ch[i], mat, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
            d = int(round(mm["rgb"] * W))
            if d:                                     # channel split on snare hits
                ch[0] = np.roll(ch[0], d, axis=1)
                ch[2] = np.roll(ch[2], -d, axis=1)
            img = cv2.merge(ch)
        g = c.exposure * mm["gain"]
        if g != 1.0:
            img *= g
        if c.tone:
            img = cv2.merge([x if p == 1.0 else cv2.pow(x, p) for x, p in zip(cv2.split(img), c.tone)])
        return img, mm

    def clip_at(self, f):
        for c in self.clips:
            if c.f0 <= f < c.f1:
                return c
        return self.clips[-1]

    def frame(self, f):
        fps = self.fps
        c = self.clip_at(f)
        self.release(f)
        img, m = self.layer(c, f)
        ctx = dict(grid_r=self.grid_r, glow=m["glow"], clip=c, mods=m, f=f, t=f / fps)
        tr = c.tin
        if tr is not None and tr.mix and c.prev is not None and f < c.f0 + int(round(tr.mix[2] * fps)):
            a, b = int(round(tr.mix[1] * fps)), int(round(tr.mix[2] * fps))
            other, _ = self.layer(c.prev, f)
            img = tr.blend(other, img, (f - (c.f0 - a) + 0.5) / max(a + b, 1), ctx)
        nx = c.next
        if nx is not None and nx.tin is not None and nx.tin.mix and f >= nx.f0 - int(round(nx.tin.mix[1] * fps)):
            a, b = int(round(nx.tin.mix[1] * fps)), int(round(nx.tin.mix[2] * fps))
            other, _ = self.layer(nx, f)
            img = nx.tin.blend(img, other, (f - (nx.f0 - a) + 0.5) / max(a + b, 1), ctx)
        for o in self.overlays:                       # depth-composited elements, in front of the lens effects
            if o.stage == "scene":
                img = o.apply(img, f, ctx)
        img = add_bloom(img, c.bloom * (1.0 + ctx["glow"]), c.streak, self.grade.get("halation", 0.0))
        for o in self.overlays:
            if o.stage == "lens":
                img = o.apply(img, f, ctx)
        grade = dict(self.grade)
        grade["sat"] = grade.get("sat", 1.0) * c.sat
        grade["gamma"] = grade.get("gamma", 1.0) * c.gamma
        grade["black"] = grade.get("black", 0.0) + c.black
        if c.sharpen is not None:
            grade["sharpen"] = c.sharpen
        out = finish(img, self.look, f, grade, self.grain)
        for o in self.overlays:
            if o.stage == "final":
                out = o.apply(out, f, ctx)
        return out

    def frames(self, f_from, f_to, on_frame):
        try:
            for f in range(f_from, min(f_to, self.total)):
                on_frame(f, self.frame(f))
        finally:
            for s in self.src.values():
                if isinstance(s, VideoSource):
                    s.close()
            self.src.clear()
            self.pos.clear()


# ------------------------------------------------------------------ cli -----
def load_edit(path=None):
    import importlib.util
    path = path or os.path.join(HERE, "edit.py")
    spec = importlib.util.spec_from_file_location("edit", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def x264_cmd(out, W, H, fps, crf, preset):
    return ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
            "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p", "-c:v", "libx264", "-preset", preset,
            "-crf", str(crf), "-profile:v", "high", "-g", str(fps), "-bf", "2", "-colorspace", "bt709",
            "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv", "-movflags", "+faststart", out]


def render_range(edit_path, W, H, fps, f_from, f_to, out, crf, preset, grain):
    cv2.setNumThreads(2)
    r = Renderer(load_edit(edit_path), W, H, fps, grain)
    tmp = out + ".tmp.mp4"
    enc = subprocess.Popen(x264_cmd(tmp, W, H, fps, crf, preset), stdin=subprocess.PIPE)

    def put(f, img):
        try:
            enc.stdin.write(img.tobytes())
        except BrokenPipeError:
            raise RuntimeError(f"the encoder for frames {f_from}-{f_to} died at frame {f} (out of memory?)") from None

    r.frames(f_from, f_to, put)
    enc.stdin.close()
    if enc.wait() != 0:
        raise RuntimeError(f"the encoder for frames {f_from}-{f_to} failed")
    os.replace(tmp, out)          # a chunk only gets its final name once it is complete
    return out


def count_frames(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=nb_frames",
                          "-of", "csv=p=0", path], capture_output=True, text=True).stdout
    try:
        return int(out.strip().split(",")[0])
    except ValueError:
        return -1


def cmd_render(a):
    import concurrent.futures as cf
    path = a.edit or os.path.join(HERE, "edit.py")
    edit = load_edit(path)
    W, H, fps = a.width, a.width * 9 // 16, a.fps
    total = layout(edit.CLIPS, fps)
    f_from = int(round(a.t0 * fps)) if a.t0 else 0
    f_to = int(round(a.t1 * fps)) if a.t1 else total
    n_parts = a.parts or max(a.jobs, int(math.ceil((f_to - f_from) / (fps * 4.0))))
    cuts = [f_from + int(round((f_to - f_from) * i / n_parts)) for i in range(n_parts + 1)]
    tmp = a.out + ".parts"
    os.makedirs(tmp, exist_ok=True)
    jobs, failed = [], []
    with cf.ProcessPoolExecutor(a.jobs) as ex:
        for i in range(n_parts):
            part = os.path.join(tmp, f"part{i:03d}_{cuts[i]}-{cuts[i + 1]}.mp4")
            if a.resume and os.path.exists(part) and count_frames(part) == cuts[i + 1] - cuts[i]:
                jobs.append((part, None))
                continue
            jobs.append((part, ex.submit(render_range, path, W, H, fps, cuts[i], cuts[i + 1], part, a.crf, a.preset, a.grain)))
        for part, fut in jobs:
            try:
                if fut is not None:
                    fut.result()
            except Exception as e:      # keep the finished chunks so --resume can pick them up
                failed.append(f"{os.path.basename(part)}: {e}")
    if failed:
        sys.exit("render incomplete:\n  " + "\n  ".join(failed) + f"\nfinished chunks are kept in {tmp}; rerun with --resume")
    lst = os.path.join(tmp, "list.txt")
    with open(lst, "w") as fh:
        for part, _ in jobs:
            fh.write(f"file '{part}'\n")
    silent = a.out + ".video.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", silent], check=True)
    dur = (f_to - f_from) / fps
    if a.silent:
        os.replace(silent, a.out)
    else:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", silent, "-ss", f"{f_from / fps:.5f}", "-i", SONG, "-map", "0:v",
                        "-map", "1:a", "-c:v", "copy", "-af", f"apad=whole_dur={dur:.4f}", "-c:a", "aac", "-b:a", "320k",
                        "-ar", "48000", "-t", f"{dur:.4f}", "-movflags", "+faststart", a.out], check=True)
        os.remove(silent)
    if not a.keep:                 # --keep leaves the chunks, so a later --resume only renders what was deleted
        for part, _ in jobs:
            os.remove(part)
        os.remove(lst)
        os.rmdir(tmp)
    print("wrote", a.out)


def cmd_frames(a):
    W, H, fps = a.width, a.width * 9 // 16, a.fps
    r = Renderer(load_edit(a.edit), W, H, fps, a.grain)
    os.makedirs(a.outdir, exist_ok=True)
    for t in a.times:
        f = int(round(float(t) * fps))

        def put(fi, img):
            p = os.path.join(a.outdir, f"f_{fi:05d}.png")
            cv2.imwrite(p, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
            print(p)

        r.frames(f, f + a.count, put)


def cmd_strip(a):
    """Consecutive frames tiled into one sheet: the way to judge a transition."""
    from PIL import Image, ImageDraw, ImageFont
    fps = a.fps
    r = Renderer(load_edit(a.edit), a.width, a.width * 9 // 16, fps, 0.0)
    f0 = int(round(a.t0 * fps)) if a.t0 is not None else bf(a.beat, fps) - a.before
    got = []
    r.frames(f0, f0 + a.n * a.step, lambda f, img: got.append((f, img)) if (f - f0) % a.step == 0 else None)
    tw, th = a.width, a.width * 9 // 16
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    rows = (len(got) + a.cols - 1) // a.cols
    sheet = Image.new("RGB", (a.cols * tw, rows * (th + 12)), (14, 14, 14))
    d = ImageDraw.Draw(sheet)
    for i, (f, img) in enumerate(got):
        x, y = (i % a.cols) * tw, (i // a.cols) * (th + 12)
        sheet.paste(Image.fromarray(img), (x, y))
        c = r.clip_at(f)
        d.text((x + 2, y + th), f"f{f} {f / fps:.2f}s {c.id if f == c.f0 else ''}",
               fill=(120, 255, 120) if f == c.f0 else (255, 255, 120), font=font)
    sheet.save(a.out, quality=88)
    print(a.out)


def cmd_board(a):
    from PIL import Image, ImageDraw, ImageFont
    W, H, fps = 480, 270, a.fps
    r = Renderer(load_edit(a.edit), W, H, fps, 0.0)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
    os.makedirs(a.outdir, exist_ok=True)
    sel = set(a.only.split(",")) if a.only else None
    rows = []
    for c in r.clips:
        if sel and c.id not in sel:
            continue
        n = c.f1 - c.f0
        post = int((c.tin.post if c.tin is not None else 0) * fps)
        want = sorted({min(post + 2, n - 1), n // 2, max(n - int(0.14 * fps) - 1, 0)})
        got = {}
        for j in want:
            r.frames(c.f0 + j, c.f0 + j + 1, lambda f, img: got.__setitem__(f - c.f0, img))
        row = Image.new("RGB", (W * 3, H + 16), (12, 12, 12))
        for i, j in enumerate(want):
            row.paste(Image.fromarray(got[j]), (i * W, 0))
        ImageDraw.Draw(row).text((4, H + 1), f"{c.id}  beats {c.k0:.2f}-{c.k1:.2f}  t={c.f0 / fps:.2f}-{c.f1 / fps:.2f}s  "
                                 f"{c.src[:40]}  {type(c.tin).__name__ if c.tin is not None else '-'}",
                                 fill=(255, 255, 120), font=font)
        rows.append(row)
    for s in range(0, len(rows), 6):
        chunk = rows[s:s + 6]
        sheet = Image.new("RGB", (W * 3, (H + 16) * len(chunk)), (12, 12, 12))
        for i, row in enumerate(chunk):
            sheet.paste(row, (0, i * (H + 16)))
        p = os.path.join(a.outdir, f"board_{s // 6:02d}.jpg")
        sheet.save(p, quality=88)
        print(p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--edit", default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("render")
    p.add_argument("--out", required=True)
    p.add_argument("--width", type=int, default=1920)
    p.add_argument("--fps", type=int, default=60)
    p.add_argument("--crf", type=float, default=15)
    p.add_argument("--preset", default="slow")
    p.add_argument("--jobs", type=int, default=4)
    p.add_argument("--parts", type=int, default=0)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--keep", action="store_true")
    p.add_argument("--silent", action="store_true")
    p.add_argument("--grain", type=float, default=0.009)
    p.add_argument("--t0", type=float, default=0)
    p.add_argument("--t1", type=float, default=0)
    p.set_defaults(fn=cmd_render)
    p = sub.add_parser("frames")
    p.add_argument("times", nargs="+")
    p.add_argument("--count", type=int, default=1)
    p.add_argument("--width", type=int, default=1920)
    p.add_argument("--fps", type=int, default=60)
    p.add_argument("--grain", type=float, default=0.009)
    p.add_argument("--outdir", default="frames")
    p.set_defaults(fn=cmd_frames)
    p = sub.add_parser("strip")
    p.add_argument("--t0", type=float, default=None)
    p.add_argument("--beat", type=float, default=0)
    p.add_argument("--before", type=int, default=8)
    p.add_argument("--n", type=int, default=40)
    p.add_argument("--step", type=int, default=1)
    p.add_argument("--cols", type=int, default=8)
    p.add_argument("--width", type=int, default=240)
    p.add_argument("--fps", type=int, default=60)
    p.add_argument("--out", default="strip.jpg")
    p.set_defaults(fn=cmd_strip)
    p = sub.add_parser("board")
    p.add_argument("--fps", type=int, default=60)
    p.add_argument("--outdir", default="board")
    p.add_argument("--only", default="")
    p.set_defaults(fn=cmd_board)
    a = ap.parse_args()
    cv2.setNumThreads(2)
    a.fn(a)


if __name__ == "__main__":
    main()
