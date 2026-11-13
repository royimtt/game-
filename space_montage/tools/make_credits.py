#!/usr/bin/env python3
"""Writes CREDITS.md and sources.tsv from the edit and sources.json.

    python tools/make_credits.py
"""
import json
import os
import sys

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, HERE)
import engine  # noqa: E402

edit = engine.load_edit(None)
engine.layout(edit.CLIPS, 60)
src = json.load(open(os.path.join(HERE, "sources.json"), encoding="utf-8"))

out = [
    "# Footage credits", "",
    "Every picture in the film is real: footage shot from the International Space Station, photographs from Apollo, "
    "Voyager, Viking, Galileo, Cassini and New Horizons, images from the Hubble and James Webb space telescopes, ESO's "
    "telescopes and the Event Horizon Telescope, and official scientific visualisations by NASA, ESA and ESO artists "
    "(the title worlds and the black hole flights). Nothing on screen was generated with AI.", "",
    "**Short credit for a post description**", "",
    "> Footage: NASA (JSC, JPL, Goddard SVS, SDO) · ESA/Hubble · ESA/Webb, CSA, STScI · ESO/M. Kornmesser · "
    "EHT Collaboration. ESO and ESA material used under CC BY 4.0.", "",
    "- NASA material is in the public domain and is used following NASA's media usage guidelines; its use does not imply "
    "endorsement.",
    "- ESO, ESA/Hubble and ESA/Webb material is licensed CC BY 4.0: it may be edited and re-used as long as the credit "
    "stays visible. The film ends on a credit line; keep the short credit above in the post description as well.",
    "- Pictures were trimmed, re-timed, reframed and colour-graded; titles, transitions and motion blur were added.", "",
    "| # | Time | Shot | Source | Credit | Licence |", "|---|---|---|---|---|---|"]
for i, c in enumerate(edit.CLIPS, 1):
    m = src[c.src]
    out.append(f"| {i} | {c.f0 / 60:05.2f} s | `{c.id}` | [{m['title']}]({m['page']}) | {m['credit']} | {m['licence']} |")
out += ["", "Typeface: Unbounded by NaN (SIL Open Font License 1.1).", ""]
open(os.path.join(HERE, "CREDITS.md"), "w", encoding="utf-8").write("\n".join(out))

lines = ["# file name <TAB> download URL <TAB> note   (videos go to clips/, pictures to stills_src/; see README)"]
for name in sorted(src, key=lambda n: (not n.endswith(".mp4"), n)):
    m = src[name]
    lines.append("\t".join([name, m["download"]] + ([m["note"]] if m.get("note") else [])))
open(os.path.join(HERE, "sources.tsv"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
print(len(edit.CLIPS), "shots,", len(src), "sources")
