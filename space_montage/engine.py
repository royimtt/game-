#!/usr/bin/env python3
"""Beat-synced montage renderer.

Footage is decoded through ffmpeg pipes, composited per frame in linear light
with numpy/OpenCV (virtual camera, speed ramps with accumulation motion blur,
zoom/whip blur, flashes, bloom, light rays, chromatic aberration, title
typography, grade, grain) and piped back to ffmpeg/x264.

    python engine.py board                 # storyboard sheets of every shot
    python engine.py render --out x.mp4    # full render (parallel by shot groups)
    python engine.py frames 17.6 17.65     # dump single frames at given times
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
SONG = os.environ.get("SM_SONG", os.path.join(HERE, "song.wav"))

# ---------------------------------------------------------------- timing ----
BPM = 56.0
BEAT = 60.0 / BPM          # dotted-quarter pulse of the 12/8 groove
BEAT0 = 0.455              # time of beat 0 (first kick) in the song
AUDIO_LEN = 53.06          # length of the supplied audio
DURATION = 54.0            # picture runs slightly past the music for the fade


def bt(k):
    """Time in seconds of beat k (may be fractional: k + 1/3 is the 2nd eighth)."""
    return BEAT0 + k * BEAT


# ------------------------------------------------------------- colour i/o ---
GAMMA = 2.2
_LIN_LUT = ((np.arange(256, dtype=np.float32) / 255.0) ** GAMMA).astype(np.float32)


def to_lin(u8):
    return cv2.LUT(u8, _LIN_LUT)


class Reader:
    """Sequential reader of source frames (relative index 0 = frame at t_in)."""

    def __init__(self, path, t_in, w, h, crop=None, hflip=False, vflip=False):
        vf = []
        if crop:
            vf.append("crop=" + crop)
        vf.append(f"scale={w}:{h}:flags=lanczos:in_color_matrix=bt709:in_range=tv")
        if hflip:
            vf.append("hflip")
        if vflip:
            vf.append("vflip")
        cmd = ["ffmpeg", "-v", "error", "-ss", f"{max(t_in, 0):.4f}", "-i", path,
               "-an", "-sn", "-vf", ",".join(vf), "-pix_fmt", "rgb24",
               "-f", "rawvideo", "-"]
        self.p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                  bufsize=w * h * 3 * 2)
        self.w, self.h, self.n = w, h, w * h * 3
        self.idx = -1
        self.cur = None
        self.prev = None
        self.eof = False
        self._cache_key = None
        self._cache = None

    def _next(self):
        if self.eof:
            return False
        buf = self.p.stdout.read(self.n)
        if len(buf) < self.n:
            self.eof = True
            return False
        self.prev = self.cur
        self.cur = np.frombuffer(buf, np.uint8).reshape(self.h, self.w, 3)
        self.idx += 1
        return True

    def blend(self, i, fr):
        """Linear-light mix of source frames i and i+1 (slow motion below 1 frame/step)."""
        key = ("b", i, round(fr, 3))
        if key == self._cache_key:
            return self._cache
        while self.idx < i + 1 and self._next():
            pass
        if self.cur is None:
            self._next()
        if self.idx >= i + 1 and self.prev is not None and fr > 0.02:
            out = cv2.addWeighted(to_lin(self.prev), 1.0 - fr, to_lin(self.cur), fr, 0.0)
        elif self.idx >= i + 1 and self.prev is not None:
            out = to_lin(self.prev)
        else:
            out = to_lin(self.cur)
        self._cache_key, self._cache = key, out
        return out

    def window(self, p0, p1):
        """Linear-light box-shutter integral of the source over [p0, p1) (in source frames)."""
        key = ("w", round(p0, 4), round(p1, 4))
        if key == self._cache_key:
            return self._cache
        ia = int(math.floor(p0 + 1e-9))
        ib = max(int(math.ceil(p1 - 1e-9)) - 1, ia)
        parts = []
        for i in range(ia, ib + 1):
            w = min(i + 1.0, p1) - max(float(i), p0)
            if w < 0.02 and ib > ia:
                continue
            if i == self.idx - 1 and self.prev is not None:
                frame = self.prev
            else:
                while self.idx < i and self._next():
                    pass
                if self.cur is None:
                    self._next()
                frame = self.cur
            parts.append((frame, w))
        wsum = sum(w for _, w in parts)
        if len(parts) == 1:
            acc = to_lin(parts[0][0])
        else:
            acc = None
            for frame, w in parts:
                lin = to_lin(frame)
                if acc is None:
                    acc = lin
                    acc *= w / wsum
                else:
                    cv2.scaleAdd(lin, w / wsum, acc, acc)
        self._cache_key, self._cache = key, acc
        return acc

    def close(self):
        try:
            self.p.stdout.close()
            self.p.kill()
            self.p.wait()
        except Exception:
            pass


# ------------------------------------------------------------------ shots ---
SHOT_DEFAULTS = dict(
    step=1.0,            # source frames consumed per output frame at 60 fps
    ramp=0.0,            # extra speed at shot start: step * (1 + ramp * exp(-t/ramp_tau))
    ramp_tau=0.12,
    crop=None, hflip=False, vflip=False,
    z0=1.02, z1=1.08,    # slow push across the shot (zoom factor)
    c0=(0.5, 0.5), c1=None,   # normalised source point kept at the frame centre
    rot0=0.0, rot1=0.0,       # degrees
    tin="flash",         # flash | whip_l | whip_r | whip_u | whip_d | spin_l | spin_r | cut | fade
    fade_in=0.55,        # seconds, for tin="fade"
    flash=1.6,           # exposure burst on entry
    zp=0.22,             # zoom punch on entry
    tout="zoom",         # zoom | none | whip (follows next shot's whip) | fade
    zo=0.30,             # zoom acceleration on exit
    fo=0.9,              # exposure pre-flash on exit
    ca=0.010,            # chromatic aberration burst on entry
    shake=0.006,         # entry camera shake (fraction of width)
    pulse=0.0,           # eighth-note exposure pulses inside the shot
    accent=0.0,          # exposure / zoom bump on every whole beat inside the shot
    exposure=1.0, sat=1.0, tint=(1.0, 1.0, 1.0), black=0.0, gamma=1.0,
    keys=None,           # [(frac, zoom, cx, cy, ease)] overrides z0/z1/c0/c1
    bloom=0.55, rays=0.0, rays_at=None,
    streak=0.25,
    note="",
)


class Shot:
    def __init__(self, sid, clip, t_in, k0, k1, **kw):
        self.id, self.clip, self.t_in, self.k0, self.k1 = sid, clip, t_in, k0, k1
        d = dict(SHOT_DEFAULTS)
        bad = set(kw) - set(d)
        if bad:
            raise KeyError(f"unknown shot option(s) {bad} in {sid}")
        d.update(kw)
        self.__dict__.update(d)
        if self.c1 is None:
            self.c1 = self.c0
        self.f0 = self.f1 = 0     # output frame range, filled by layout()

    @property
    def path(self):
        return os.path.join(CLIPS, self.clip)


def layout(shots, fps):
    """Assign output frame ranges; cuts land on the frame nearest each beat."""
    total = int(round(DURATION * fps))
    for i, s in enumerate(shots):
        s.f0 = 0 if i == 0 else int(math.floor(bt(s.k0) * fps + 0.35))
    for i, s in enumerate(shots):
        s.f1 = shots[i + 1].f0 if i + 1 < len(shots) else total
        s.index = i
        s.prev = shots[i - 1] if i else None
        s.next = shots[i + 1] if i + 1 < len(shots) else None
    return total


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


def step_positions(shot, fps):
    """Source frame position at the start of every output frame of the shot."""
    J = shot.f1 - shot.f0
    k = 60.0 / fps
    j = np.arange(J + 1, dtype=np.float64)
    st = shot.step * k * (1.0 + shot.ramp * np.exp(-j / (shot.ramp_tau * fps)))
    pos = np.concatenate([[0.0], np.cumsum(st[:-1])])
    base = shot.step * k
    for q in (1.0, 0.5):
        if abs(base / q - round(base / q)) < 1e-6:
            # land on whole (or half) source frames once the ramp has settled, so steady
            # frames stay sharp instead of sitting on an arbitrary blend
            pos = np.maximum(pos - (pos[-1] - math.floor(pos[-1] / q + 1e-6) * q), 0.0)
            break
    return pos


# ---------------------------------------------------------------- effects ---
def ease_io(x):
    return x * x * (3 - 2 * x)


class Look:
    """Frame-size dependent precomputed fields (vignette, grain)."""

    def __init__(self, W, H, seed=7):
        self.W, self.H = W, H
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        nx = (xx - W / 2) / (W / 2)
        ny = (yy - H / 2) / (W / 2)
        r2 = nx * nx + ny * ny
        self.vig = (1.0 - 0.30 * np.clip(r2, 0, 2) ** 1.25).astype(np.float32)
        self.vig3 = cv2.merge([self.vig] * 3)
        rng = np.random.default_rng(seed)
        self.grain = []
        for _ in range(6):
            g = rng.standard_normal((H + 96, W + 96)).astype(np.float32)
            g = cv2.GaussianBlur(g, (0, 0), 0.62 * W / 1920.0 + 0.25)
            g /= g.std()
            self.grain.append(g)
        self.rng = rng

    def grain_field(self):
        g = self.grain[int(self.rng.integers(len(self.grain)))]
        oy, ox = (int(v) for v in self.rng.integers(0, 96, 2))
        return g[oy:oy + self.H, ox:ox + self.W]


def affine(sw, sh, W, H, z, cx, cy, rot_deg, dx, dy):
    """Inverse map (output px -> source px) for cv2.warpAffine(WARP_INVERSE_MAP)."""
    b = sw / float(W)
    s = b / z
    th = math.radians(rot_deg)
    co, si = math.cos(th) * s, math.sin(th) * s
    ox, oy = W / 2.0 + dx, H / 2.0 + dy
    m = np.array([[co, -si, cx * sw - co * ox + si * oy],
                  [si, co, cy * sh - si * ox - co * oy]], dtype=np.float64)
    return m


def clamp_center(z, cx, cy):
    hw = 0.5 / z
    return min(max(cx, hw), 1 - hw), min(max(cy, hw), 1 - hw)


WHIP_DIR = {"whip_l": (1.0, 0.0), "whip_r": (-1.0, 0.0), "whip_u": (0.0, 1.0), "whip_d": (0.0, -1.0)}
WHIP_IN = (0.55, 0.075)     # travel (frame widths) and time constant of the incoming whip
WHIP_OUT = (0.45, 0.045)    # ... of the outgoing one


def whip_terms(shot, tau, u):
    """Whip-pan displacement (dx, dy) and speed (vx, vy), in frame widths (per second)."""
    dx = dy = vx = vy = 0.0
    d = WHIP_DIR.get(shot.tin)
    if d:
        k = 1.0 if d[0] else 9.0 / 16.0
        amt = WHIP_IN[0] * k * math.exp(-tau / WHIP_IN[1])
        dx += d[0] * amt
        dy += d[1] * amt
        vx += abs(d[0]) * amt / WHIP_IN[1]
        vy += abs(d[1]) * amt / WHIP_IN[1]
    if shot.next is not None and shot.tout == "whip":
        d = WHIP_DIR.get(shot.next.tin)
        if d:
            k = 1.0 if d[0] else 9.0 / 16.0
            amt = WHIP_OUT[0] * k * math.exp(-max(u, 0.0) / WHIP_OUT[1])
            dx -= d[0] * amt
            dy -= d[1] * amt
            vx += abs(d[0]) * amt / WHIP_OUT[1]
            vy += abs(d[1]) * amt / WHIP_OUT[1]
    return dx, dy, vx, vy


def camera_state(shot, j, fps, sub=0.0):
    """Zoom / centre / rotation / offset of the virtual camera at output frame j+sub."""
    J = shot.f1 - shot.f0
    tau = (j + sub) / fps
    u = (J - (j + sub)) / fps
    p = min(max((j + sub) / max(J - 1, 1), 0.0), 1.0)
    if shot.keys:
        ks = shot.keys
        a = ks[0]
        b = ks[-1]
        for i in range(len(ks) - 1):
            if ks[i][0] <= p <= ks[i + 1][0]:
                a, b = ks[i], ks[i + 1]
                break
        f = 0.0 if b[0] == a[0] else (p - a[0]) / (b[0] - a[0])
        e = b[4] if len(b) > 4 else "io"
        f = {"in": f * f * f, "out": 1 - (1 - f) ** 3, "lin": f}.get(e, ease_io(f))
        z = math.exp(math.log(a[1]) + (math.log(b[1]) - math.log(a[1])) * f)
        # move the centre so the target glides to its place while zooming (dolly feel)
        g = f if b[1] == a[1] else (1.0 / a[1] - 1.0 / z) / (1.0 / a[1] - 1.0 / b[1])
        cx = a[2] + (b[2] - a[2]) * g
        cy = a[3] + (b[3] - a[3]) * g
    else:
        z = shot.z0 + (shot.z1 - shot.z0) * p
        cx = shot.c0[0] + (shot.c1[0] - shot.c0[0]) * p
        cy = shot.c0[1] + (shot.c1[1] - shot.c0[1]) * p
    rot = shot.rot0 + (shot.rot1 - shot.rot0) * p
    if shot.accent > 0 and tau > 0.3:
        ph = ((shot.f0 + j + sub) / fps - BEAT0) % BEAT
        z *= 1.0 + 0.06 * shot.accent * math.exp(-ph / 0.10)
    tin = shot.tin
    if tin == "flash":
        z *= 1.0 + shot.zp * math.exp(-tau / 0.085)
    elif tin in WHIP_DIR:
        z *= 1.0 + 0.5 * shot.zp * math.exp(-tau / 0.085)
    elif tin.startswith("spin"):
        ang = 16.0 * math.exp(-tau / 0.085) * (1.0 if tin == "spin_l" else -1.0)
        rot += ang
        z *= 1.0 + shot.zp * math.exp(-tau / 0.085) + 0.030 * min(abs(ang), 8.0)
    if shot.next is not None:
        nt = shot.next.tin
        if shot.tout == "zoom" or (shot.tout == "whip" and nt not in WHIP_DIR and not nt.startswith("spin")):
            z *= 1.0 + shot.zo * math.exp(-max(u, 0) / 0.05)
        elif shot.tout == "whip" and nt.startswith("spin"):
            ang = 12.0 * math.exp(-max(u, 0) / 0.045) * (-1.0 if nt == "spin_l" else 1.0)
            rot += ang
            z *= 1.0 + shot.zo * math.exp(-max(u, 0) / 0.05) + 0.030 * min(abs(ang), 8.0)
    dx, dy, _, _ = whip_terms(shot, tau, u)
    # zoom in just enough that most of the whip travel stays inside the picture
    z *= 1.0 + 2.0 * min(max(abs(dx), abs(dy) * 16.0 / 9.0), 0.22)
    return z, cx, cy, rot, dx, dy


def render_camera(shot, src, j, fps, W, H, rng):
    """Warp the linear source frame through the virtual camera with motion blur."""
    sh, sw = src.shape[:2]
    J = shot.f1 - shot.f0
    tau = j / fps
    shutter = 0.7
    z_a, cx_a, cy_a, rot_a, dx_a, dy_a = camera_state(shot, j, fps, 0.0)
    z_b, cx_b, cy_b, rot_b, dx_b, dy_b = camera_state(shot, j, fps, shutter)
    # zoom / rotation travel during the shutter decides the number of blur samples
    travel = abs(z_b / z_a - 1.0) * W * 0.5 + abs(math.radians(rot_b - rot_a)) * W * 0.5
    n = int(min(max(math.ceil(travel / 2.5), 1), 14))
    ca = shot.ca * math.exp(-tau / 0.11) if shot.tin not in ("cut", "fade") else 0.0
    ca += 0.0009   # constant, barely visible lens fringe
    sx = sy = 0.0
    if shot.shake > 0 and shot.tin not in ("cut", "fade"):
        a = shot.shake * math.exp(-tau / 0.12) * W
        sx, sy = (float(v) * a for v in rng.uniform(-1, 1, 2))
    acc = None
    interp = cv2.INTER_CUBIC if n <= 2 else cv2.INTER_LINEAR
    for i in range(n):
        f = 0.5 if n == 1 else i / (n - 1.0)
        z = z_a + (z_b - z_a) * f
        cx = cx_a + (cx_b - cx_a) * f
        cy = cy_a + (cy_b - cy_a) * f
        rot = rot_a + (rot_b - rot_a) * f
        dx = (dx_a + dx_b) * 0.5 * W + sx
        dy = (dy_a + dy_b) * 0.5 * W + sy
        cx, cy = clamp_center(z, cx, cy)
        if ca > 2e-4:
            chans = []
            for c, zc in enumerate((z * (1 + ca), z, z * (1 - ca))):
                m = affine(sw, sh, W, H, zc, cx, cy, rot, dx, dy)
                chans.append(cv2.warpAffine(src[:, :, c], m, (W, H),
                                            flags=interp | cv2.WARP_INVERSE_MAP,
                                            borderMode=cv2.BORDER_REFLECT_101))
            out = cv2.merge(chans)
        else:
            m = affine(sw, sh, W, H, z, cx, cy, rot, dx, dy)
            out = cv2.warpAffine(src, m, (W, H), flags=interp | cv2.WARP_INVERSE_MAP,
                                 borderMode=cv2.BORDER_REFLECT_101)
        if acc is None:
            acc = out
        else:
            acc += out
    if n > 1:
        acc *= 1.0 / n
    # whip pans: long directional streaks (two box passes = triangular shutter)
    _, _, vx, vy = whip_terms(shot, tau + 0.5 * shutter / fps, (J - j - 0.5 * shutter) / fps)
    for v, horiz in ((vx, True), (vy, False)):
        L = int(min(v * W / fps * 1.5, 0.45 * W))
        if L > 2:
            k = (L | 1, 1) if horiz else (1, L | 1)
            acc = cv2.blur(cv2.blur(acc, k), k)
    np.clip(acc, 0.0, None, out=acc)     # cubic overshoot
    return acc


_bright_cache = {}


def shot_brightness(shot):
    """How bright the shot's first frame already is (cached), used to tame flashes."""
    key = (shot.path, round(shot.t_in, 3), shot.crop)
    if key not in _bright_cache:
        vf = (("crop=" + shot.crop + ",") if shot.crop else "") + "scale=64:36"
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{shot.t_in:.3f}", "-i", shot.path,
                              "-frames:v", "1", "-vf", vf, "-pix_fmt", "rgb24", "-f", "rawvideo", "-"],
                             capture_output=True).stdout
        a = np.frombuffer(raw, np.uint8)
        if a.size:
            lum = to_lin(a).reshape(-1, 3).max(axis=1)
            # a bright body on black (planet, lunar surface) counts as bright, not as "mostly dark"
            _bright_cache[key] = max(float(lum.mean()), 0.75 * float(np.percentile(lum, 85)))
        else:
            _bright_cache[key] = 0.1
    return _bright_cache[key]


def exposure_env(shot, j, fps):
    """Exposure multiplier and bloom boost from entry flash / exit pre-flash / pulses."""
    J = shot.f1 - shot.f0
    tau = j / fps
    u = (J - j) / fps
    g = shot.exposure
    boost = 0.0
    if shot.tin == "flash" or shot.tin.startswith(("whip", "spin")):
        fl = shot.flash * min(max(1.2 - 2.6 * shot_brightness(shot), 0.35), 1.0)
        g *= 1.0 + fl * math.exp(-tau / 0.065)
        boost += 0.9 * fl * math.exp(-tau / 0.13)
    elif shot.tin == "fade":
        g *= ease_io(min((tau + 1.0 / fps) / shot.fade_in, 1.0))
    if shot.next is not None and shot.tout in ("zoom", "whip"):
        g *= 1.0 + shot.fo * math.exp(-u / 0.045)
        boost += 0.8 * shot.fo * math.exp(-u / 0.06)
    elif shot.tout == "fade":
        g *= ease_io(min(max(u / 1.1, 0.0), 1.0))
    t_abs = (shot.f0 + j) / fps - BEAT0
    if shot.pulse > 0:
        ph = t_abs % (BEAT / 3.0)
        g *= 1.0 + shot.pulse * math.exp(-ph / 0.06)
    if shot.accent > 0 and tau > 0.3:
        ph = t_abs % BEAT
        g *= 1.0 + shot.accent * math.exp(-ph / 0.09)
        boost += 1.5 * shot.accent * math.exp(-ph / 0.2)
    return g, boost


def add_bloom(img, strength, streak, rays, rays_at, state, thresh=0.55):
    """Additive glow from the highlights (linear light). Returns the modified image."""
    H, W = img.shape[:2]
    qw, qh = W // 4, H // 4
    small = cv2.resize(img, (qw, qh), interpolation=cv2.INTER_AREA)
    bright = np.maximum(small - thresh, 0.0)
    s = W / 1920.0
    g1 = cv2.GaussianBlur(bright, (0, 0), 5.0 * s)
    tiny = cv2.resize(bright, (qw // 4, qh // 4), interpolation=cv2.INTER_AREA)
    g2 = cv2.GaussianBlur(tiny, (0, 0), 6.0 * s)
    glow = g1 * 0.55 + cv2.resize(g2, (qw, qh), interpolation=cv2.INTER_LINEAR) * 0.75
    if streak > 0:
        hot = np.maximum(small - 0.82, 0.0)
        lum = small.max(axis=2)
        area = cv2.GaussianBlur((lum > 0.45).astype(np.float32), (0, 0), qw / 14.0)
        wgt = np.clip(1.0 - 3.0 * area, 0.0, 1.0)          # big bright bodies do not streak
        hot *= wgt[:, :, None]
        hot = cv2.GaussianBlur(hot, (0, 0), 1.0 * s)
        st = (cv2.blur(hot, (int(qw * 0.07) | 1, 1)) * 0.50
              + cv2.blur(hot, (int(qw * 0.22) | 1, 1)) * 0.32
              + cv2.blur(hot, (int(qw * 0.60) | 1, 1)) * 0.18)
        st[:, :, 0] *= 0.55
        st[:, :, 1] *= 0.80         # cool anamorphic streak
        glow += st * (9.0 * streak)
    if rays > 0:
        if rays_at is None:
            lum = cv2.GaussianBlur(tiny.max(axis=2), (0, 0), 3.0)
            _, _, _, loc = cv2.minMaxLoc(lum)
            lx, ly = (loc[0] + 0.5) / tiny.shape[1], (loc[1] + 0.5) / tiny.shape[0]
            prev = state.get("rays_at")
            if prev is not None:
                lx, ly = prev[0] * 0.85 + lx * 0.15, prev[1] * 0.85 + ly * 0.15
            state["rays_at"] = (lx, ly)
        else:
            lx, ly = rays_at
        px, py = lx * qw, ly * qh
        hot = np.maximum(small - 0.80, 0.0)
        hot = cv2.GaussianBlur(hot, (0, 0), 1.5 * s)
        acc = np.zeros_like(hot)
        wsum = 0.0
        w = 1.0
        for i in range(1, 41):
            sc = 1.0 + 0.016 * i
            m = np.array([[1 / sc, 0, px - px / sc], [0, 1 / sc, py - py / sc]])
            acc += cv2.warpAffine(hot, m, (qw, qh), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP) * w
            wsum += w
            w *= 0.955
        acc = cv2.GaussianBlur(acc / wsum, (0, 0), 1.0 * s)
        glow += acc * (9.0 * rays)
    glow = cv2.resize(glow, (W, H), interpolation=cv2.INTER_LINEAR)
    cv2.scaleAdd(glow, float(strength), img, img)
    return img


def finish(img, look, shot, grain_amp=0.011):
    """Linear float image -> graded 8-bit RGB."""
    cv2.multiply(img, look.vig3, img)
    # soft highlight shoulder
    _, over = cv2.threshold(img - 0.72, 0.0, 0.0, cv2.THRESH_TOZERO)
    rolled = 0.72 + 0.28 * (1.0 - cv2.exp(over * (-1.0 / 0.28)))
    img = cv2.min(img, rolled)
    _, img = cv2.threshold(img, 0.0, 0.0, cv2.THRESH_TOZERO)
    g = cv2.pow(img, (1.0 / GAMMA) * shot.gamma)
    sat = 1.10 * shot.sat
    lw = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    tint = np.array(shot.tint, dtype=np.float32)
    m = (np.eye(3, dtype=np.float32) * sat + (1 - sat) * lw[None, :]) * tint[:, None]
    g = cv2.transform(g, m)
    # gentle S-curve + black point
    np.clip(g, 0.0, 1.0, out=g)
    s = g * g * (3.0 - 2.0 * g)
    g = cv2.addWeighted(g, 0.80, s, 0.20, 0.0)
    b = 0.012 + shot.black
    g = (g - b) * (1.0 / (1.0 - b))
    if grain_amp > 0:
        n = look.grain_field()
        lum = cv2.transform(g, lw.reshape(1, 3))
        wgt = 0.30 + 2.8 * lum * (1.0 - np.minimum(lum, 1.0))
        n = n * wgt * grain_amp
        g += cv2.merge([n, n, n])
    return np.clip(g * 255.0 + 0.5, 0, 255).astype(np.uint8)


# ------------------------------------------------------------------ title ---
class Title:
    """Letter-by-letter title, composited in linear light on top of the glowing picture."""

    def __init__(self, W, H, spec):
        from PIL import Image, ImageDraw, ImageFont
        self.W, self.H, self.spec = W, H, spec
        word = spec["word"]
        size = int(spec.get("size", 0.118) * W)
        font = ImageFont.truetype(spec["font"], size)
        self.ss = 2  # supersample
        fbig = ImageFont.truetype(spec["font"], size * self.ss)
        track = spec.get("tracking", 0.62) * size
        adv = [font.getlength(ch) for ch in word]
        total = sum(adv) + track * (len(word) - 1)
        x = (W - total) / 2.0
        asc, desc = font.getmetrics()
        bbox = font.getbbox("SPACE")
        cap_h = bbox[3] - bbox[1]
        self.cy = H * spec.get("y", 0.5)
        self.letters = []
        for ch, a in zip(word, adv):
            pad = int(size * 0.35)
            gw, gh = int(a) + 2 * pad, int(cap_h) + 2 * pad
            im = Image.new("L", (gw * self.ss, gh * self.ss), 0)
            d = ImageDraw.Draw(im)
            d.text((pad * self.ss, (pad - bbox[1]) * self.ss), ch, font=fbig, fill=255)
            mask = np.asarray(im, dtype=np.float32) / 255.0
            mask = cv2.resize(mask, (gw, gh), interpolation=cv2.INTER_AREA)
            self.letters.append(dict(mask=mask, cx=x + a / 2.0, w=gw, h=gh))
            x += a + track
        self.fps = spec["fps"]

    def layer(self, t):
        """Coverage and brightness layers (H, W) plus glow gain for time t."""
        sp = self.spec
        fps = self.fps

        def tq(k):      # same frame the picture cuts on
            return math.floor(bt(k) * fps + 0.35) / fps

        t = t + 0.25 / fps
        t_on = [tq(k) for k in sp["beats"]]
        t_full, t_exit, t_end = tq(sp["full"]), tq(sp["exit"]), tq(sp["end"])
        if t < t_on[0] or t >= t_end:
            return None, None, 0.0
        W, H = self.W, self.H
        alpha = np.zeros((H, W), np.float32)
        light = np.zeros((H, W), np.float32)
        # slow push over the whole title, then the word collapses into a point
        gp = (t - t_on[0]) / (t_exit - t_on[0])
        gscale = 1.0 + 0.05 * min(max(gp, 0.0), 1.0)
        ax, ay = W / 2.0, self.cy
        opacity = 1.0
        if t >= t_exit:
            e = min(max((t - t_exit) / (t_end - t_exit), 0.0), 1.0)
            tx, ty = sp.get("exit_to", (0.5, 0.5))
            gscale *= 1.0 - 0.985 * e ** 3
            mv = ease_io(e)
            ax += (tx * W - ax) * mv
            ay += (ty * H - ay) * mv
            opacity = 1.0 - e ** 6
        base = sp.get("level", 0.60)
        glow = 0.0
        for L, ton in zip(self.letters, t_on):
            if t < ton:
                continue
            a = t - ton
            pop = 1.0 + 0.50 * math.exp(-a / 0.07)                 # scale pop-in
            fade = 1.0
            glow = max(glow, 1.8 * math.exp(-a / 0.18))
            lvl = base + 0.9 * math.exp(-a / 0.22)                 # newest letter burns brightest
            if t >= t_full:
                lvl = max(lvl, base + 0.25 + 0.8 * math.exp(-(t - t_full) / 0.30))
                pop *= 1.0 + 0.07 * math.exp(-(t - t_full) / 0.10)
            sc = gscale * pop
            cx = ax + (L["cx"] - W / 2.0) * gscale
            m = np.array([[sc, 0, cx - sc * L["w"] / 2.0], [0, sc, ay - sc * L["h"] / 2.0]])
            a_l = cv2.warpAffine(L["mask"], m, (W, H), flags=cv2.INTER_LINEAR) * fade
            alpha = cv2.max(alpha, a_l)
            light = cv2.max(light, a_l * lvl)
        if t >= t_full:
            glow = max(glow, 1.7 * math.exp(-(t - t_full) / 0.22)) + 0.25
            # one specular sweep across the finished word
            q = (t - t_full) / 0.55
            if 0.0 <= q <= 1.0:
                xs = np.arange(W, dtype=np.float32)[None, :] + 0.35 * (np.arange(H, dtype=np.float32)[:, None] - ay)
                x0 = W * (0.12 + 0.76 * q)
                band = np.exp(-((xs - x0) / (0.035 * W)) ** 2)
                light += alpha * band * 1.2
        return alpha * opacity, light * opacity, glow * opacity

    def composite(self, img, t):
        alpha, light, glow = self.layer(t)
        if alpha is None:
            return img
        s = self.W / 1920.0
        col = self.spec.get("color", (0.90, 0.95, 1.0))
        # soft shadow keeps the letters readable over bright footage
        sh = cv2.GaussianBlur(alpha, (0, 0), 16 * s)
        keep = 1.0 - cv2.max(alpha, 0.58 * sh)
        halo = cv2.GaussianBlur(light, (0, 0), 24 * s) * (0.10 + 0.40 * glow) \
            + cv2.GaussianBlur(light, (0, 0), 5 * s) * (0.22 * glow)
        add = light + halo
        ch = cv2.split(img)
        out = [c * keep + add * k for c, k in zip(ch, col)]
        return cv2.merge(out)


# ----------------------------------------------------------------- render ---
class Renderer:
    def __init__(self, edit, W, H, fps, grain=0.011):
        self.W, self.H, self.fps = W, H, fps
        self.shots = edit.SHOTS
        self.total = layout(self.shots, fps)
        self.look = Look(W, H)
        self.grain = grain
        spec = dict(edit.TITLE)
        spec["fps"] = fps
        self.title = Title(W, H, spec)
        self.credit = getattr(edit, "CREDIT", None)
        self.fade_out = getattr(edit, "FADE_OUT", 1.1)
        self._credit_layer = None

    def decode_size(self, shot):
        sw, sh, sfps, dur = probe(shot.path)
        if shot.crop:
            cw, ch = (int(v) for v in shot.crop.split(":")[:2])
            sw, sh = cw, ch
        zmax = max([shot.z0, shot.z1] + [k[1] for k in (shot.keys or [])]) * (1 + shot.zp) * 1.02
        w = int(min(sw, math.ceil(self.W * min(zmax, 1.6) / 16) * 16))
        w = max(w, min(sw, self.W))
        h = int(round(w * 9 / 16 / 2) * 2)
        return w, h

    def credit_layer(self):
        if self._credit_layer is None and self.credit:
            from PIL import Image, ImageDraw, ImageFont
            W, H = self.W, self.H
            im = Image.new("L", (W * 2, H * 2), 0)
            d = ImageDraw.Draw(im)
            f = ImageFont.truetype(self.credit["font"], int(self.credit.get("size", 0.0125) * W * 2))
            txt = self.credit["text"]
            sp = self.credit.get("tracking", 0.22) * f.size
            wtot = sum(f.getlength(c) for c in txt) + sp * (len(txt) - 1)
            x = (W * 2 - wtot) / 2
            y = H * 2 * self.credit.get("y", 0.93)
            for c in txt:
                d.text((x, y), c, font=f, fill=255)
                x += f.getlength(c) + sp
            a = cv2.resize(np.asarray(im, np.float32) / 255.0, (W, H), interpolation=cv2.INTER_AREA)
            self._credit_layer = a
        return self._credit_layer

    def frames(self, f_from, f_to, on_frame):
        rng = np.random.default_rng(1234 + f_from)
        for shot in self.shots:
            if shot.f1 <= f_from or shot.f0 >= f_to:
                continue
            dw, dh = self.decode_size(shot)
            pos = step_positions(shot, self.fps)
            rd = Reader(shot.path, shot.t_in, dw, dh, crop=shot.crop, hflip=shot.hflip, vflip=shot.vflip)
            state = {}
            try:
                for j in range(shot.f1 - shot.f0):
                    f = shot.f0 + j
                    if f >= f_to:
                        break
                    if f < f_from:
                        continue
                    if pos[j + 1] - pos[j] < 0.999:
                        i0 = int(math.floor(pos[j] + 1e-6))
                        src = rd.blend(i0, pos[j] - i0)
                    else:
                        src = rd.window(pos[j], pos[j + 1])
                    on_frame(f, self.compose(shot, j, src, rng, state))
            finally:
                rd.close()

    def compose(self, shot, j, src, rng, state):
        fps, W, H = self.fps, self.W, self.H
        t = (shot.f0 + j) / fps
        img = render_camera(shot, src, j, fps, W, H, rng)
        gain, boost = exposure_env(shot, j, fps)
        if gain != 1.0:
            img *= gain
        img = add_bloom(img, shot.bloom * (1.0 + boost), shot.streak, shot.rays, shot.rays_at, state)
        img = self.title.composite(img, t)
        if self.credit:
            c0, c1 = self.credit["t0"], self.credit["t1"]
            if c0 <= t <= c1:
                a = self.credit_layer() * (self.credit.get("level", 0.5) * ease_io(min((t - c0) / 0.6, 1.0)))
                img += cv2.merge([a * 0.9, a * 0.95, a])
        out = finish(img, self.look, shot, self.grain)
        # fade to black at the very end (after the grade, so the grain fades too)
        fo = self.fade_out
        if t > DURATION - fo:
            k = ease_io(min(max((DURATION - t - 1.0 / fps) / fo, 0.0), 1.0))
            out = (out.astype(np.float32) * k + 0.5).astype(np.uint8)
        return out


def validate(shots, fps):
    """Warn when a shot would run past the end of its source clip."""
    ok = True
    for sh in shots:
        w, h, sfps, dur = probe(sh.path)
        used = step_positions(sh, fps)[-1] / sfps
        if sh.t_in + used > dur - 0.15:
            print(f"WARNING {sh.id}: needs source until {sh.t_in + used:.2f}s but clip is {dur:.2f}s", file=sys.stderr)
            ok = False
    return ok


def x264_cmd(out, W, H, fps, crf, preset):
    return ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
            "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
            "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
            "-profile:v", "high", "-g", str(fps), "-bf", "2",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
            "-color_range", "tv", "-movflags", "+faststart", out]


def render_range(edit, W, H, fps, f_from, f_to, out, crf=16, preset="medium", grain=0.011):
    if isinstance(edit, str):
        edit = load_edit(edit)
    r = Renderer(edit, W, H, fps, grain)
    f_to = min(f_to, r.total)
    enc = subprocess.Popen(x264_cmd(out, W, H, fps, crf, preset), stdin=subprocess.PIPE)

    def put(f, img):
        enc.stdin.write(img.tobytes())

    r.frames(f_from, f_to, put)
    enc.stdin.close()
    enc.wait()
    return out


def load_edit(path=None):
    import importlib.util
    path = path or os.path.join(HERE, "edit.py")
    spec = importlib.util.spec_from_file_location("edit", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cmd_render(a):
    import concurrent.futures as cf
    edit = load_edit(a.edit)
    W, H, fps = a.width, a.width * 9 // 16, a.fps
    shots = edit.SHOTS
    total = layout(shots, fps)
    validate(shots, fps)
    f_from = int(round(a.t0 * fps)) if a.t0 else 0
    f_to = int(round(a.t1 * fps)) if a.t1 else total
    # split on shot boundaries into balanced groups
    bounds = sorted({f_from, f_to} | {s.f0 for s in shots if f_from < s.f0 < f_to})
    target = (f_to - f_from) / float(a.jobs)
    cuts = [f_from]
    for b in bounds[1:-1]:
        if b - cuts[-1] >= target * 0.9 and len(cuts) < a.jobs:
            cuts.append(b)
    cuts.append(f_to)
    tmp = a.out + ".parts"
    os.makedirs(tmp, exist_ok=True)
    jobs = []
    with cf.ProcessPoolExecutor(a.jobs) as ex:
        for i in range(len(cuts) - 1):
            part = os.path.join(tmp, f"part{i:02d}.mp4")
            jobs.append((part, ex.submit(render_range, edit_path(a), W, H, fps, cuts[i], cuts[i + 1],
                                         part, a.crf, a.preset, a.grain)))
        for part, fut in jobs:
            fut.result()
    lst = os.path.join(tmp, "list.txt")
    with open(lst, "w") as fh:
        for part, _ in jobs:
            fh.write(f"file '{part}'\n")
    silent = a.out + ".video.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst,
                    "-c", "copy", silent], check=True)
    t_from = f_from / fps
    dur = (f_to - f_from) / fps
    af = f"afade=t=in:st=0:d=0.012,apad=whole_dur={dur:.4f}"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", silent, "-ss", f"{t_from:.5f}", "-i", SONG,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-af", af, "-c:a", "aac", "-b:a", "256k",
                    "-ar", "48000", "-t", f"{dur:.4f}", "-movflags", "+faststart", a.out], check=True)
    os.remove(silent)
    for part, _ in jobs:
        os.remove(part)
    os.remove(lst)
    os.rmdir(tmp)
    print("wrote", a.out)


def edit_path(a):
    return a.edit or os.path.join(HERE, "edit.py")


def cmd_frames(a):
    edit = load_edit(a.edit)
    W, H, fps = a.width, a.width * 9 // 16, a.fps
    r = Renderer(edit, W, H, fps, a.grain)
    os.makedirs(a.outdir, exist_ok=True)
    for t in a.times:
        f = int(round(float(t) * fps))

        def put(fi, img, t=t):
            p = os.path.join(a.outdir, f"f_{fi:05d}.png")
            cv2.imwrite(p, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
            print(p)

        r.frames(f, f + a.count, put)


def cmd_board(a):
    """Storyboard: three frames per shot (early / middle / late), tiled into sheets."""
    from PIL import Image, ImageDraw, ImageFont
    edit = load_edit(a.edit)
    W, H, fps = 480, 270, a.fps
    r = Renderer(edit, W, H, fps, grain=0.0)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
    os.makedirs(a.outdir, exist_ok=True)
    rows = []
    sel = set(a.only.split(",")) if a.only else None
    for shot in r.shots:
        if sel and shot.id not in sel:
            continue
        J = shot.f1 - shot.f0
        want = sorted({min(int(0.13 * fps), J - 1), J // 2, max(J - int(0.1 * fps) - 1, 0)})
        got = {}

        def put(f, img, shot=shot, got=got):
            got[f - shot.f0] = img

        for j in want:
            r.frames(shot.f0 + j, shot.f0 + j + 1, put)
        pos = step_positions(shot, fps)
        sfps = probe(shot.path)[2]
        used = pos[-1] / sfps
        row = Image.new("RGB", (W * 3, H + 16), (12, 12, 12))
        for i, j in enumerate(want):
            row.paste(Image.fromarray(got[j]), (i * W, 0))
        d = ImageDraw.Draw(row)
        d.text((4, H + 1), f"{shot.id}  beats {shot.k0:.2f}-{shot.k1:.2f}  t={shot.f0 / fps:.2f}-{shot.f1 / fps:.2f}s  "
               f"{shot.clip[:34]}  src {shot.t_in:.1f}+{used:.1f}s  {shot.tin}", fill=(255, 255, 120), font=font)
        rows.append(row)
    per = 6
    for s in range(0, len(rows), per):
        chunk = rows[s:s + per]
        sheet = Image.new("RGB", (W * 3, (H + 16) * len(chunk)), (12, 12, 12))
        for i, row in enumerate(chunk):
            sheet.paste(row, (0, i * (H + 16)))
        p = os.path.join(a.outdir, f"board_{s // per:02d}.jpg")
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
    p.add_argument("--crf", type=float, default=16)
    p.add_argument("--preset", default="medium")
    p.add_argument("--jobs", type=int, default=4)
    p.add_argument("--grain", type=float, default=0.011)
    p.add_argument("--t0", type=float, default=0)
    p.add_argument("--t1", type=float, default=0)
    p.set_defaults(fn=cmd_render)
    p = sub.add_parser("frames")
    p.add_argument("times", nargs="+")
    p.add_argument("--count", type=int, default=1)
    p.add_argument("--width", type=int, default=1920)
    p.add_argument("--fps", type=int, default=60)
    p.add_argument("--grain", type=float, default=0.011)
    p.add_argument("--outdir", default="frames")
    p.set_defaults(fn=cmd_frames)
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
