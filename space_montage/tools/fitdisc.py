"""Fit the body (planet disc) in a title shot from its lit limb, at the first and last frame of the clip.
   usage: fitdisc.py edit.py clip_id[:mode[:samples]] ...     mode = lit (default) | ridge
   prints occ discs in frame-width units and writes a check sheet."""
import sys, os, math, numpy as np, cv2
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import engine
edit = engine.load_edit(sys.argv[1])
edit.HITS = []
edit.overlays = lambda r: []
W, H, fps = 960, 540, 60
r = engine.Renderer(edit, W, H, fps, 0.0)
rng = np.random.default_rng(1)

def circle3(p):
    (x1, y1), (x2, y2), (x3, y3) = p
    a = np.array([[x1 - x2, y1 - y2], [x1 - x3, y1 - y3]], float) * 2
    b = np.array([x1**2 - x2**2 + y1**2 - y2**2, x1**2 - x3**2 + y1**2 - y3**2], float)
    if abs(np.linalg.det(a)) < 1e-6: return None
    cx, cy = np.linalg.solve(a, b)
    return cx, cy, math.hypot(x1 - cx, y1 - cy)

def ransac(pts, tol=1.5, n=4000):
    best, bi = None, -1
    for _ in range(n):
        c = circle3(pts[rng.choice(len(pts), 3, replace=False)])
        if c is None or c[2] > 6000: continue
        d = np.abs(np.hypot(pts[:, 0] - c[0], pts[:, 1] - c[1]) - c[2])
        k = int((d < tol).sum())
        if k > bi: best, bi = c, k
    cx, cy, rr = best
    inl = pts[np.abs(np.hypot(pts[:, 0] - cx, pts[:, 1] - cy) - rr) < tol]
    A = np.c_[2 * inl[:, 0], 2 * inl[:, 1], np.ones(len(inl))]          # least squares on the inliers
    sol, *_ = np.linalg.lstsq(A, (inl ** 2).sum(1), rcond=None)
    cx, cy = sol[0], sol[1]
    return cx, cy, math.sqrt(sol[2] + cx * cx + cy * cy), bi, len(pts)

def limb_points(img, mode):
    lum = cv2.GaussianBlur(img.max(axis=2), (0, 0), 1.5)
    gy, gx = np.gradient(lum)
    g = np.hypot(gx, gy)
    if mode == "ridge":                       # horizon: strongest dark-above / bright-below edge per column
        pts = []
        for x in range(4, W - 4, 3):
            col = gy[int(0.25 * H):, x]
            y = int(np.argmax(col)); 
            if col[y] > 0.004: pts.append((x, y + int(0.25 * H)))
        return np.array(pts, float)
    m = (lum > max(0.035, 0.12 * np.percentile(lum, 99.5))).astype(np.uint8)
    n, lab, st, cen = cv2.connectedComponentsWithStats(m)
    i = 1 + int(np.argmax(st[1:, 4]))
    cs, _ = cv2.findContours((lab == i).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=len)[:, 0, :]
    c = c[(c[:, 0] > 3) & (c[:, 0] < W - 4) & (c[:, 1] > 3) & (c[:, 1] < H - 4)]
    gv = g[c[:, 1], c[:, 0]]
    return c[gv > np.percentile(gv, 55)].astype(float)      # the limb is the sharp part of the outline

tiles = []
out = {}
for spec in sys.argv[2:]:
    cid, mode, nk = (spec.split(":") + ["", ""])[:3]
    nk = int(nk or 2)
    c = next(x for x in r.clips if x.id == cid)
    post = int((c.tin.post if c.tin is not None else 0) * fps) + 2
    fa, fb = c.f0 + post, c.f1 - 2
    n = c.f1 - c.f0
    track = []
    for i in range(nk):
        f = int(round(fa + (fb - fa) * i / (nk - 1)))
        img, mm = r.layer(c, f)
        if mode == "horizon":                 # a nearly flat limb: y = a + b x + c x^2 (frame widths), robust fit
            pts = limb_points(img, "ridge") / W
            w = np.ones(len(pts))
            for _ in range(6):
                co = np.polyfit(pts[:, 0], pts[:, 1], 2, w=w)
                res = np.abs(np.polyval(co, pts[:, 0]) - pts[:, 1])
                w = 1.0 / (1.0 + (res / 0.002) ** 2)
            track.append([round((f - c.f0) / n, 4)] + [round(float(v), 5) for v in co[::-1]])
            if i in (0, nk // 2, nk - 1):
                vis = np.clip(img ** (1 / 2.2) * 255, 0, 255).astype(np.uint8)[..., ::-1].copy()
                xs_ = np.arange(W)
                ys_ = np.polyval(co, xs_ / W) * W
                for x_, y_ in zip(xs_[::2], ys_[::2]):
                    if 0 <= y_ < H: vis[int(y_), x_] = (0, 255, 0)
                cv2.putText(vis, f"{cid} f{f}", (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                tiles.append(vis)
            continue
        cx, cy, rr, k, npts = ransac(limb_points(img, mode or "lit"))
        track.append([round((f - c.f0) / n, 4), round(float(cx) / W, 4), round(float(cy) / W, 4), round(float(rr) / W, 4)])
        if i in (0, nk - 1):
            vis = np.clip(img ** (1 / 2.2) * 255, 0, 255).astype(np.uint8)[..., ::-1].copy()
            cv2.circle(vis, (int(round(cx)), int(round(cy))), int(round(rr)), (0, 255, 0), 1)
            cv2.putText(vis, f"{cid} f{f} inl {k}/{npts}", (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            tiles.append(vis)
    # extend to the ends of the clip (the fit avoids the transition frames)
    a, b = track[0], track[1]
    track.insert(0, [0.0] + [round(float(a[j] + (b[j] - a[j]) * (0 - a[0]) / (b[0] - a[0])), 4) for j in (1, 2, 3)])
    a, b = track[-2], track[-1]
    track.append([1.0] + [round(float(a[j] + (b[j] - a[j]) * (1 - a[0]) / (b[0] - a[0])), 4) for j in (1, 2, 3)])
    out[cid] = [tuple(k) for k in track]
    print(f'    "{cid}": {out[cid]},')
    xs = [0.2, 0.37, 0.5, 0.64, 0.79]
    if mode == "horizon":
        for k in track:
            print("       u=%.2f limb y/H at x=S,P,A,C,E:" % k[0], " ".join("%.3f" % ((k[1] + k[2] * x + k[3] * x * x) * 16 / 9) for x in xs))
        continue
    for k in (track[0], track[len(track) // 2], track[-1]):
        ys = [(k[2] - math.sqrt(max(k[3] ** 2 - (x - k[1]) ** 2, 0))) * 16 / 9 if abs(x - k[1]) < k[3] else float("nan") for x in xs]
        print("       u=%.2f limb y/H at x=S,P,A,C,E:" % k[0], " ".join("%.3f" % y for y in ys))
for s_ in r.src.values():
    if hasattr(s_, "close"): s_.close()
if len(tiles) % 2:
    tiles.append(np.zeros_like(tiles[0]))
rows = [np.hstack(tiles[i:i + 2]) for i in range(0, len(tiles), 2)]
cv2.imwrite(os.environ.get("FITDISC_SHEET", "fitdisc_check.jpg"), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 85])
