#!/usr/bin/env python3
"""Prepares the pictures that are not used as downloaded.

    python tools/prepare_stills.py stills_src stills

* planet portraits -> pl__<name>.jpg: every globe centred on a black 3840x2160 canvas with the same
  radius, so the solar-system tour can cut from disc to disc without the disc moving;
* the Sgr A* image -> pad__sgra.jpg: the square image feathered into a black 16:9 canvas;
* everything else in stills_src is linked into stills unchanged.
"""
import os
import shutil
import sys

import cv2
import numpy as np

CW, CH = 3840, 2160
R = 0.31 * CH

# name: (source file, mask everything outside the limb?, crop (x0, y0, x1, y1) or None, globe (cx, cy, r) or None)
PLANETS = {
    "pluto": ("pl__pluto.jpg", True, None, None),
    "neptune": ("pl__neptune.jpg", True, None, None),
    "uranus": ("pl__uranus.jpg", False, None, (988, 961, 525)),             # the globe inside its rings
    "saturn": ("pl__saturn.jpg", False, None, (4605.1, 2238.7, 1371.3)),
    "jupiter": ("pl__jupiter.jpg", True, None, None),
    "jupiterw": ("pl__jupiterw.jpg", True, None, None),
    "mars": ("pl__mars.jpg", True, None, None),
    "moon": ("pl__moon.jpg", True, None, None),
    "earth": ("pl__earth.jpg", True, None, None),
}


def find_disc(img, thr=18):
    g = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (0, 0), 3)
    m = cv2.morphologyEx((g > thr).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    (x, y), r = cv2.minEnclosingCircle(max(cs, key=cv2.contourArea))
    return x, y, r


def planet(src, dst, mask, crop, globe):
    img = cv2.imread(src, cv2.IMREAD_COLOR)
    if crop:
        img = img[crop[1]:crop[3], crop[0]:crop[2]]
    h, w = img.shape[:2]
    if not mask:                                    # lift the picture's own background to true black
        edge = np.concatenate([img[:12].reshape(-1, 3), img[-12:].reshape(-1, 3), img[:, :12].reshape(-1, 3),
                               img[:, -12:].reshape(-1, 3)])
        bg = np.percentile(edge, 90, axis=0).astype(np.float32) + 2.0
        img = np.clip((img.astype(np.float32) - bg) * (255.0 / (255.0 - bg)), 0, 255).astype(np.uint8)
    x, y, r = globe or find_disc(img)
    s = R / r
    if s < 0.5:                                     # big reductions: prefilter first
        k = int(1 / s)
        img = cv2.resize(img, (w // k, h // k), interpolation=cv2.INTER_AREA)
        x, y, w, h, s = x / k, y / k, w / k, h / k, s * k
    M = np.array([[s, 0, CW / 2 - s * x], [0, s, CH / 2 - s * y]])
    can = cv2.warpAffine(img, M, (CW, CH), flags=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC,
                         borderMode=cv2.BORDER_CONSTANT, borderValue=0).astype(np.float32)
    yy, xx = np.mgrid[0:CH, 0:CW].astype(np.float32)
    if mask:                                        # keep the limb, remove everything outside it
        d = np.sqrt((xx - CW / 2) ** 2 + (yy - CH / 2) ** 2)
        a = np.clip((R * 1.012 - d) / (R * 0.012) + 0.5, 0, 1)
    else:                                           # feather the picture's own rectangle so its border never shows
        x0, y0, x1, y1 = CW / 2 - s * x, CH / 2 - s * y, CW / 2 + s * (w - x), CH / 2 + s * (h - y)
        a = np.clip((xx - x0) / 40, 0, 1) * np.clip((x1 - xx) / 40, 0, 1) * np.clip((yy - y0) / 40, 0, 1) * \
            np.clip((y1 - yy) / 40, 0, 1)
    cv2.imwrite(dst, (can * a[..., None]).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 95])


def pad_sgra(src, dst, cx=0.480, cy=0.503):
    a = cv2.imread(src)
    h, w = a.shape[:2]
    cw = int(h * 16 / 9)
    x0 = (cw - w) // 2
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - cx * w) / (0.5 * w)) ** 2 + ((yy - cy * h) / (0.5 * h)) ** 2)
    m = np.clip((0.98 - d) / 0.30, 0, 1)
    m = m * m * (3 - 2 * m)
    can = np.zeros((h, cw, 3), np.float32)
    can[:, x0:x0 + w] = a.astype(np.float32) * m[..., None]
    cv2.imwrite(dst, can.astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 95])


def main():
    src, dst = sys.argv[1], sys.argv[2]
    os.makedirs(dst, exist_ok=True)
    special = {v[0] for v in PLANETS.values()} | {"pad__sgra.jpg"}
    for name, (fn, mask, crop, globe) in PLANETS.items():
        planet(os.path.join(src, fn), os.path.join(dst, fn), mask, crop, globe)
        print("registered", fn)
    pad_sgra(os.path.join(src, "pad__sgra.jpg"), os.path.join(dst, "pad__sgra.jpg"))
    print("padded pad__sgra.jpg")
    for fn in sorted(os.listdir(src)):
        if fn not in special and fn.lower().endswith((".jpg", ".png")):
            shutil.copyfile(os.path.join(src, fn), os.path.join(dst, fn))


if __name__ == "__main__":
    main()
