"""Review sheets from a rendered file: one row per cut, frames around the cut.
   usage: cutsheet.py video.mp4 outdir [edit.py]"""
import sys, os, cv2, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import engine
video, outdir = sys.argv[1], sys.argv[2]
edit = engine.load_edit(sys.argv[3] if len(sys.argv) > 3 else None)
fps = 60
engine.layout(edit.CLIPS, fps)
cap = cv2.VideoCapture(video)
frames = []
while True:
    ok, fr = cap.read()
    if not ok: break
    frames.append(cv2.resize(fr, (192, 108), interpolation=cv2.INTER_AREA))
print(len(frames), "frames")
OFFS = [-6, -4, -2, -1, 0, 1, 2, 4, 6, 9, 13, 20]
rows = []
for c in edit.CLIPS:
    tiles = []
    for o in OFFS:
        f = min(max(c.f0 + o, 0), len(frames) - 1)
        t = frames[f].copy()
        if o == 0: cv2.rectangle(t, (0, 0), (191, 107), (0, 255, 0), 1)
        tiles.append(t)
    row = np.hstack(tiles)
    lab = np.zeros((14, row.shape[1], 3), np.uint8)
    cv2.putText(lab, f"{c.id}  beat {c.k0:.2f}  f{c.f0}  t={c.f0 / fps:.2f}s  {type(c.tin).__name__ if c.tin is not None else '-'}   offsets {OFFS}",
                (4, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (120, 255, 255), 1)
    rows.append(np.vstack([row, lab]))
os.makedirs(outdir, exist_ok=True)
per = 11
for i in range(0, len(rows), per):
    p = os.path.join(outdir, f"cuts_{i // per:02d}.jpg")
    cv2.imwrite(p, np.vstack(rows[i:i + per]), [cv2.IMWRITE_JPEG_QUALITY, 86]); print(p)
