"""Typography and frame furniture that sit on top of (or inside) the footage.

Stages (see engine.Renderer.frame):
    scene - composited in linear light before bloom, so it glows and flares like the footage
    lens  - after bloom
    final - on the graded 8-bit frame (letterbox, fades)
"""
import json
import math
import os

import cv2
import numpy as np

from engine import Type, bf, blur_spin, blur_zoom, clamp, e_out, smooth


# ------------------------------------------------------------- helpers ------
def attach(layer, mods, W, H):
    """Move a text layer with the picture: the transition's zoom / roll / travel and the drum shakes."""
    z, rot, dx, dy = mods["z"], mods["rot"], mods["dx"], mods["dy"]
    if abs(z - 1.0) < 1e-4 and abs(rot) < 1e-3 and abs(dx) < 1e-5 and abs(dy) < 1e-5:
        return layer
    ax, ay = mods["ax"] * W, mods["ay"] * H
    th = math.radians(rot)
    c, s = z * math.cos(th), z * math.sin(th)
    M = np.array([[c, -s, ax - c * ax + s * ay + dx * W], [s, c, ay - s * ax - c * ay + dy * W]], dtype=np.float64)
    return cv2.warpAffine(layer, M, (W, H), flags=cv2.INTER_LINEAR)


def moved(pt, mods, W, H):
    """Where a point of the settled picture is right now (same transform as `attach`)."""
    ax, ay = mods["ax"] * W, mods["ay"] * H
    th = math.radians(mods["rot"])
    c, s = mods["z"] * math.cos(th), mods["z"] * math.sin(th)
    x, y = pt[0] - ax, pt[1] - ay
    return ax + c * x - s * y + mods["dx"] * W, ay + s * x + c * y + mods["dy"] * W


def occlusion(img, clip, ctx, W, H):
    """Matte of what stands in front of depth-composited text.

    clip.occ = dict(lum=(lo, hi), discs=[track, ...], soft=edge): `lum` hides the text behind bright footage
    (a star's glare); each track follows one body through the clip as [(u, cx, cy, r), ...] with u = 0..1 and
    the circle in frame widths, so that its night side hides the text too (see tools/fitdisc.py).
    """
    occ = getattr(clip, "occ", None)
    if not occ:
        return None
    m = np.zeros((H, W), np.float32)
    lum = occ.get("lum")
    if lum:
        lo, hi = lum
        m = np.clip((img.max(axis=2) - lo) / (hi - lo), 0.0, 1.0)
        m = m * m * (3.0 - 2.0 * m)
    mods = ctx["mods"]
    n = max(clip.f1 - clip.f0, 1)
    p = (ctx["f"] - clip.f0) / n
    yy, xx = np.ogrid[0:H, 0:W]
    soft = occ.get("soft", 0.004)
    for track in occ.get("discs", []):                           # track = [(u, cx, cy, r), ...] along the clip
        us = [k[0] for k in track]
        cx, cy, r = (float(np.interp(p, us, [k[i] for k in track])) for i in (1, 2, 3))
        qx, qy = moved((cx * W, cy * W), mods, W, H)
        rr = r * W * mods["z"]
        dist = np.sqrt((xx - qx) ** 2 + (yy - qy) ** 2)
        m = np.maximum(m, np.clip((rr - dist) / (soft * W) + 0.5, 0.0, 1.0).astype(np.float32))
    for track in occ.get("horizons", []):                        # [(u, a, b, c), ...]: limb y = a + b x + c x^2
        us = [k[0] for k in track]
        a, b, c = (float(np.interp(p, us, [k[i] for k in track])) for i in (1, 2, 3))
        xs = np.arange(W, dtype=np.float32)
        ys = np.arange(H, dtype=np.float32)
        ang = math.radians(mods["rot"])
        if abs(mods["z"] - 1.0) < 1e-4 and abs(ang) < 1e-5:
            limb = (a + b * (xs / W) + c * (xs / W) ** 2) * W + mods["dy"] * W
            hm = np.clip((ys[:, None] - limb[None, :]) / (soft * W) + 0.5, 0.0, 1.0)
        else:                                                    # undo the transition's move, then test
            ax, ay = mods["ax"] * W, mods["ay"] * H
            co, si = math.cos(-ang) / mods["z"], math.sin(-ang) / mods["z"]
            X = xs[None, :] - ax - mods["dx"] * W
            Y = ys[:, None] - ay - mods["dy"] * W
            sx, sy = ax + co * X - si * Y, ay + si * X + co * Y
            hm = np.clip((sy - (a + b * (sx / W) + c * (sx / W) ** 2) * W) * mods["z"] / (soft * W) + 0.5, 0.0, 1.0)
        m = np.maximum(m, hm.astype(np.float32))
    return cv2.GaussianBlur(m.astype(np.float32), (0, 0), 1.0 * W / 1920.0)


def scene_tint(img, amount=0.24):
    """Per-pixel colour for text so that it takes on the light of the scene around it (computed at 1/16 size)."""
    H, W = img.shape[:2]
    small = cv2.resize(img, (W // 16, H // 16), interpolation=cv2.INTER_AREA)
    env = cv2.GaussianBlur(small, (0, 0), 7.0)
    mx = env.max(axis=2, keepdims=True)
    w = amount * np.clip(mx / 0.12, 0.0, 1.0)
    col = 1.0 - w + w * env / (mx + 1e-4)
    return cv2.resize(col, (W, H), interpolation=cv2.INTER_LINEAR)


def comp_text(img, alpha, light, color, glow, s, shadow=0.42, tint=0.24):
    """Lay a text layer into the scene: soft contact shadow, lit fill, halo."""
    sh = cv2.GaussianBlur(alpha, (0, 0), 14 * s)
    k = 1.0 - np.maximum(alpha, shadow * sh)
    halo = cv2.GaussianBlur(light, (0, 0), 26 * s) * (0.07 + 0.45 * glow) + cv2.GaussianBlur(light, (0, 0), 6 * s) * (0.22 * glow)
    add = light + halo
    if tint > 0:
        col = scene_tint(img, tint)
        col *= np.array(color, np.float32)
        return img * k[..., None] + add[..., None] * col
    ch = cv2.split(img)
    return cv2.merge([c * k + add * col for c, col in zip(ch, color)])


def rays(light, center, strength, length=1.55):
    """Light streaming out of a text layer (a zoom blur of its own light, computed at quarter size)."""
    H, W = light.shape[:2]
    small = cv2.resize(light, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    r = blur_zoom(cv2.merge([small, small, small]), (center[0] / 4.0, center[1] / 4.0), length)[..., 0]
    r = cv2.GaussianBlur(r, (0, 0), 1.5)
    return cv2.resize(r, (W, H), interpolation=cv2.INTER_LINEAR) * strength


# --------------------------------------------------------------- title ------
class Title:
    """The word arrives one letter per beat, standing behind the worlds it crosses.

    On `ignite` it flares; from `fall` to `end` it is drawn into the black hole at the centre of the frame:
    the letters shear into arcs, wind around the hole and settle on its photon ring as a ring of light.
    """
    stage = "scene"

    def __init__(self, r, word, font, axes=None, size=0.128, tracking=0.20, y=0.5, beats=(8, 9, 10, 11, 12), full=13,
                 ignite=14.0, fall=14.22, end=15.0, hole=(0.5, 0.5), ring=0.09, ring_z=(1.0, 1.0), level=0.62,
                 color=(0.93, 0.96, 1.0)):
        self.r, self.word, self.beats, self.level, self.color = r, word, beats, level, color
        W, H = r.W, r.H
        self.type = Type(font, size * W, axes)
        xs, total = self.type.layout(word, tracking)
        self.x0 = (W - total) / 2.0
        self.xs = [self.x0 + x for x in xs]
        self.total = total
        self.y = H * y - self.type.cap_h / 2.0
        self.cy = H * y
        self.f_on = [bf(k, r.fps) for k in beats]
        self.f_full, self.f_ign, self.f_fall, self.f_end = (bf(k, r.fps) for k in (full, ignite, fall, end))
        self.hole, self.ring, self.ring_z = hole, ring, ring_z
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.xx, self.yy = xx, yy

    def letters(self, f, K):
        r = self.r
        W, H, fps = r.W, r.H, r.fps
        prog = clamp((f - self.f_on[0]) / max(self.f_fall - self.f_on[0], 1))
        gscale = (1.0 + 0.05 * prog) * (1.0 + 0.010 * K)
        alpha = np.zeros((H, W), np.float32)
        light = np.zeros((H, W), np.float32)
        glow = 0.0
        for ch, x, fon in zip(self.word, self.xs, self.f_on):
            if f < fon:
                continue
            a = (f - fon) / fps
            pop = 1.0 + 0.34 * math.exp(-a / 0.05)
            lvl = self.level + 1.1 * math.exp(-a / 0.20)
            glow = max(glow, 1.7 * math.exp(-a / 0.18))
            gx = W / 2.0 + (x - W / 2.0) * gscale                 # the word breathes about the frame centre
            gy = self.cy + (self.y - self.cy) * gscale
            canvas = np.zeros((H, W), np.float32)
            self.type.draw(canvas, ch, gx, gy, scale=gscale * pop,
                           about=(gx + self.type.adv(ch) * gscale / 2, gy + self.type.cap_h * gscale / 2))
            np.maximum(alpha, canvas, out=alpha)
            np.maximum(light, canvas * lvl, out=light)
        top = self.cy + (self.y - self.cy) * gscale                # lit from above: a little brighter at the cap line
        v = np.clip((self.yy[:, :1] - top) / (self.type.cap_h * gscale), 0.0, 1.0)
        light *= 1.05 - 0.17 * v
        return alpha, light, glow

    def apply(self, img, f, ctx):
        r = self.r
        if f < self.f_on[0] or f >= self.f_end:
            return img
        W, H, fps = r.W, r.H, r.fps
        s = W / 1920.0
        K = float(r.kick[f]) + 0.6 * float(r.snare[f])
        alpha, light, glow = self.letters(f, K)
        if f >= self.f_full:
            b = (f - self.f_full) / fps
            glow = max(glow, 0.9 * math.exp(-b / 0.25)) + 0.15
            q = b / 0.75
            if 0.0 <= q <= 1.0:                                   # one specular sweep across the finished word
                x0 = W * (0.06 + 0.88 * smooth(q))
                light += alpha * np.exp(-(((self.xx + 0.35 * (self.yy - H / 2)) - x0) / (0.035 * W)) ** 2) * 0.9
        if f >= self.f_ign:                                       # the word catches fire
            b = (f - self.f_ign) / fps
            k = math.exp(-b / 0.16)
            light *= 1.0 + 0.8 * k
            glow += 0.9 * k
            light += rays(light, (W / 2.0, self.cy), 0.40 * k + 0.10)
        if f >= self.f_fall:
            e = clamp((f - self.f_fall + 1) / max(self.f_end - self.f_fall, 1))
            alpha, light = self.infall(alpha, light, e)
            glow += 0.8 * e
        mods = ctx["mods"]
        alpha, light = attach(alpha, mods, W, H), attach(light, mods, W, H)
        matte = occlusion(img, ctx["clip"], ctx, W, H)
        if matte is not None:
            keep = 1.0 - matte
            alpha, light = alpha * keep, light * keep
        return comp_text(img, alpha, light, self.color, glow, s)

    def infall(self, alpha, light, e):
        """Letters shear, wind around the hole and pile up on its photon ring (inverse-mapped)."""
        W, H = self.r.W, self.r.H
        cx, cy = self.hole[0] * W, self.hole[1] * H
        R = self.ring * W * (self.ring_z[0] + (self.ring_z[1] - self.ring_z[0]) * e)
        k = max((1.0 - e) ** 2.4, 0.055)                          # radial compression towards the ring
        dx, dy = self.xx - cx, self.yy - cy
        rho = np.sqrt(dx * dx + dy * dy)
        rs = R + (rho - R) / k                                    # where this pixel's light came from
        swirl = (2.4 * e ** 1.5) * np.exp(-np.maximum(rs, 0.0) / (0.30 * W)) + 1.3 * e ** 3
        ang = np.arctan2(dy, dx) - swirl                          # the inside winds faster than the outside
        valid = rs > 0.0
        mx = np.where(valid, cx + rs * np.cos(ang), -10.0).astype(np.float32)
        my = np.where(valid, cy + rs * np.sin(ang), -10.0).astype(np.float32)
        a = cv2.remap(alpha, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        l = cv2.remap(light, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        deg = 105.0 * e ** 2.2                                    # the arcs smear into a ring
        if deg > 1.0:
            l = blur_spin(cv2.merge([l, l, l]), (cx, cy), deg)[..., 0]
            a = blur_spin(cv2.merge([a, a, a]), (cx, cy), deg)[..., 0]
        gain = min(k ** -0.36, 3.0) * (1.0 + 0.3 * e)             # the same light on a thinner band
        return np.minimum(a * (1.0 - 0.75 * e), 1.0), l * gain


# ------------------------------------------------------------ signature -----
class Signature:
    """The channel name, delivered by the black hole.

    A ring of light (what is left of the title) condenses into the word: the word is imaged through a point
    lens at the centre of the hole (beta = theta - thetaE^2 / theta) whose strength falls to zero, with a
    slightly different Einstein radius per colour. Its glow follows the loudness of the spoken tag, and just
    before the drop it implodes into the point the next shot bursts out of.
    """
    stage = "scene"

    def __init__(self, r, text, font, axes=None, size=0.060, tracking=0.02, at=(0.5, 0.5), beat=15.0, end=16.0,
                 ring=0.17, relax=0.40, implode=0.15, color=(0.96, 0.98, 1.0), env_json=None, level=1.0, shear=0.0,
                 line=True):
        self.r, self.color, self.level, self.ring, self.relax, self.implode = r, color, level, ring, relax, implode
        W, H = r.W, r.H
        self.type = Type(font, size * W, axes)
        xs, total = self.type.layout(text, tracking)
        self.at = at
        cx, cy = at[0] * W, at[1] * H
        canvas = np.zeros((H, W), np.float32)
        for ch, x in zip(text, xs):
            self.type.draw(canvas, ch, cx - total / 2.0 + x, cy - self.type.cap_h / 2.0)
        if shear:                                                 # a forward lean
            M = np.array([[1.0, -shear, shear * cy], [0.0, 1.0, 0.0]])
            canvas = cv2.warpAffine(canvas, M, (W, H), flags=cv2.INTER_LINEAR)
        self.canvas, self.total = canvas, total
        self.line_y = cy + self.type.cap_h * 0.5 + 0.022 * W if line else None
        self.f0, self.f1 = bf(beat, r.fps), bf(end, r.fps)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.xx, self.yy = xx, yy
        self.dx, self.dy = xx - cx, yy - cy
        self.rr = np.maximum(np.sqrt(self.dx ** 2 + self.dy ** 2), 0.5)
        self.env = None
        if env_json and os.path.exists(env_json):
            j = json.load(open(env_json))
            e = np.asarray(j["env"], np.float32)
            self.env = np.interp(np.arange(r.total + 1) / r.fps, np.arange(len(e)) / j["fps"], e)

    def lensed(self, canvas, theta_e, scale=1.0):
        cx, cy = self.at[0] * self.r.W, self.at[1] * self.r.H
        k = 1.0 / scale
        if theta_e >= 0.5:
            k = k * (1.0 - (theta_e * theta_e) / (self.rr * self.rr))      # beta / theta
        elif scale == 1.0:
            return canvas
        return cv2.remap(canvas, cx + self.dx * k, cy + self.dy * k, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)

    def apply(self, img, f, ctx):
        if f < self.f0 or f >= self.f1:
            return img
        r = self.r
        W, H, fps = r.W, r.H, r.fps
        s = W / 1920.0
        tau, u = (f - self.f0) / fps, (self.f1 - f) / fps
        voice = float(self.env[f]) if self.env is not None else 0.0
        out_k = clamp((self.implode - u) / self.implode) ** 2.2 if self.implode > 0 else 0.0
        te = self.ring * W * 1.35 * e_out(tau / self.relax, 3.2)
        scale = 1.0 - 0.94 * out_k
        base = self.canvas
        if self.line_y is not None:                               # a hairline that draws itself under the word
            q = 1.0 - e_out((tau - 0.10) / 0.45, 3.0) if tau > 0.10 else 0.0
            half = 0.5 * self.total * q
            cx = self.at[0] * W
            ln = np.clip((half - np.abs(self.xx - cx)) / (0.03 * W), 0.0, 1.0) * \
                np.exp(-((self.yy - self.line_y) / (0.0011 * W)) ** 2)
            base = np.maximum(base, ln.astype(np.float32) * 0.7)
        chans = [self.lensed(base, te * k, scale) for k in (1.06, 1.0, 0.94)]     # colours bend by different amounts
        alpha = chans[1]
        level = self.level * (0.86 + 0.85 * math.exp(-tau / 0.12) + 0.45 * voice + 2.0 * out_k)
        glow = 0.30 + 1.0 * math.exp(-tau / 0.2) + 0.9 * voice + 1.6 * out_k
        fade = clamp((tau + 1.0 / fps) / 0.04)
        mods = ctx["mods"]
        a = attach(alpha * fade, mods, W, H)
        lights = [attach(c * (fade * level), mods, W, H) for c in chans]
        matte = occlusion(img, ctx["clip"], ctx, W, H)
        if matte is not None:
            keep = 1.0 - matte
            a = a * keep
            lights = [l * keep for l in lights]
        sh = cv2.GaussianBlur(a, (0, 0), 12 * s)
        k = 1.0 - np.maximum(np.minimum(a, 1.0), 0.5 * sh)
        g = lights[1]
        halo = cv2.GaussianBlur(g, (0, 0), 24 * s) * (0.10 + 0.22 * glow) + cv2.GaussianBlur(g, (0, 0), 5 * s) * (0.2 * glow)
        if tau < 0.3:                                             # an anamorphic streak through the word on the hit
            st = cv2.blur(cv2.resize(g, (W // 4, H // 4), interpolation=cv2.INTER_AREA), (int(W * 0.07) | 1, 1))
            halo += cv2.resize(st, (W, H), interpolation=cv2.INTER_LINEAR) * (0.5 * math.exp(-tau / 0.08))
        ctx["glow"] = ctx.get("glow", 0.0) + 0.3 * math.exp(-tau / 0.15) + 0.6 * out_k
        ch = cv2.split(img)
        return cv2.merge([c * k + (l + halo) * col for c, l, col in zip(ch, lights, self.color)])


# ------------------------------------------------------------- furniture ----
class Letterbox:
    """Animated cinema bars; `keys` = [(beat, bar height as a fraction of the frame height, seconds), ...]."""
    stage = "final"

    def __init__(self, r, keys):
        self.r, self.keys = r, keys
        fps = r.fps
        self.curve = np.zeros(r.total + 2, np.float32)
        v = keys[0][1]
        start = v
        idx = 0
        for f in range(r.total + 2):
            while idx + 1 < len(keys) and f >= bf(keys[idx + 1][0], fps):
                idx += 1
                start = v                                         # glide from wherever the bars are now
            k, val, dur = keys[idx]
            q = clamp((f - bf(k, fps) + 1) / max(dur * fps, 1.0)) if idx else 1.0
            v = start + (val - start) * (1.0 - (1.0 - q) ** 3)
            self.curve[f] = v

    def frac(self, f):
        return float(self.curve[int(clamp(f, 0, len(self.curve) - 1))])

    def apply(self, out, f, ctx):
        h = self.frac(f) * self.r.H
        n = int(h)
        if n > 0:
            out[:n] = 0
            out[-n:] = 0
        a = h - n                                                 # sub-pixel edge, so the bars glide
        if a > 0.01 and n < self.r.H // 2:
            out[n] = (out[n].astype(np.float32) * (1.0 - a)).astype(np.uint8)
            out[-n - 1] = (out[-n - 1].astype(np.float32) * (1.0 - a)).astype(np.uint8)
        return out


class Mark:
    """A small, steady channel mark at the foot of the picture (it rides just above the lower bar)."""
    stage = "final"

    def __init__(self, r, text, font, axes=None, size=0.0100, tracking=0.55, beat=16.0, until=None, opacity=0.34,
                 margin=0.040, box=None):
        self.r, self.box, self.opacity, self.margin = r, box, opacity, margin
        W, H = r.W, r.H
        ty = Type(font, size * W, axes)
        xs, total = ty.layout(text, tracking)
        pad = int(0.02 * W)
        tw, th = int(total) + 2 * pad, int(ty.cap_h) + 2 * pad
        canvas = np.zeros((th, tw), np.float32)
        for ch, x in zip(text, xs):
            if ch != " ":
                ty.draw(canvas, ch, pad + x, pad)
        self.tile = canvas
        self.shadow = cv2.GaussianBlur(canvas, (0, 0), 3.0 * W / 1920.0)
        self.pad, self.cap = pad, ty.cap_h
        self.f0 = bf(beat, r.fps)
        self.f1 = r.total if until is None else bf(until, r.fps)

    def apply(self, out, f, ctx):
        if f < self.f0 or f >= self.f1:
            return out
        r = self.r
        W, H = r.W, r.H
        k = smooth((f - self.f0) / (0.6 * r.fps)) * smooth((self.f1 - f) / (0.5 * r.fps)) * self.opacity
        bar = self.box.frac(f) if self.box is not None else 0.0
        th, tw = self.tile.shape
        y_cap = H * (1.0 - bar - self.margin) - self.cap          # top of the capitals
        y0 = int(round(y_cap - self.pad))
        x0 = (W - tw) // 2
        if y0 < 0 or y0 + th > H:
            return out
        roi = out[y0:y0 + th, x0:x0 + tw].astype(np.float32)
        roi *= (1.0 - 0.45 * k * np.minimum(self.shadow * 1.6, 1.0))[..., None]
        roi += (self.tile * (k * 255.0))[..., None] * np.array([0.93, 0.95, 1.0], np.float32)
        out[y0:y0 + th, x0:x0 + tw] = np.clip(roi, 0, 255).astype(np.uint8)
        return out


class EndCard:
    """Closing lockup: the name, small and spaced, over the footage credit."""
    stage = "lens"

    def __init__(self, r, lines, beat=48.6, fade=0.8):
        self.r, self.fade = r, fade
        W, H = r.W, r.H
        self.f0 = bf(beat, r.fps)
        layer = np.zeros((H, W), np.float32)
        for ln in lines:
            ty = Type(ln["font"], ln["size"] * W, ln.get("axes"))
            xs, total = ty.layout(ln["text"], ln.get("tracking", 0.2))
            canvas = np.zeros((H, W), np.float32)
            for ch, x in zip(ln["text"], xs):
                if ch != " ":
                    ty.draw(canvas, ch, (W - total) / 2.0 + x, ln["y"] * H)
            layer += canvas * ln.get("level", 0.6)
        self.layer = layer
        self.shadow = cv2.GaussianBlur(np.minimum(layer * 2.0, 1.0), (0, 0), 10.0 * W / 1920.0)

    def apply(self, img, f, ctx):
        if f < self.f0:
            return img
        k = smooth((f - self.f0) / (self.fade * self.r.fps))
        a = self.layer * k
        dim = 1.0 - 0.5 * k * self.shadow
        ch = cv2.split(img)
        return cv2.merge([c * dim + a * col for c, col in zip(ch, (0.93, 0.96, 1.0))])


class Fade:
    """Fade from / to black at the ends of the film (after the grade, so the grain fades too)."""
    stage = "final"

    def __init__(self, r, fade_in=0.0, fade_out=1.0, end=None):
        self.r, self.fin, self.fout = r, fade_in, fade_out
        self.end = r.total if end is None else end

    def apply(self, out, f, ctx):
        fps = self.r.fps
        k = 1.0
        if self.fin > 0 and f < self.fin * fps:
            k = smooth((f + 1) / (self.fin * fps))
        if f > self.end - self.fout * fps:
            k = min(k, smooth((self.end - f - 1) / (self.fout * fps)))
        if k >= 1.0:
            return out
        return (out.astype(np.float32) * max(k, 0.0) + 0.5).astype(np.uint8)
