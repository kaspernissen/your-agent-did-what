#!/usr/bin/env python3
"""Trim each element crop to its ink and correct its position in the manifest.

Crops are cut from a measured box plus a safety pad, so most carry a transparent
margin — and a group's box is its container's rect, which can extend well past
anything that paints (the slide 3 timeline's container runs down to where the
labels sit, and the labels are painted out). Trimming to the alpha bounding box
makes every crop exact.

The offsets move with the trim, so x/y/w/h in the manifest are rewritten to match.
Runs on the finished export; no re-rendering.
"""
import json
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
OUT = HERE / 'export'
SCALE = 2

manifest = json.loads((OUT / 'manifest.json').read_text())
trimmed = dropped = 0
for slide in manifest:
    keep = []
    for e in slide['elements']:
        p = OUT / e['file']
        im = Image.open(p).convert('RGBA')
        bbox = im.getbbox()
        if not bbox:
            p.unlink(); dropped += 1; continue          # paints nothing after all
        if bbox != (0, 0, im.width, im.height):
            im.crop(bbox).save(p)
            # the crop began PAD px up and left of the measured box; the trim moves
            # it again, so recompute from the padded origin rather than the box
            ox, oy = max(0, e['x'] - 8), max(0, e['y'] - 8)
            e['x'] = ox + bbox[0] // SCALE
            e['y'] = oy + bbox[1] // SCALE
            e['w'] = (bbox[2] - bbox[0]) // SCALE
            e['h'] = (bbox[3] - bbox[1]) // SCALE
            trimmed += 1
        keep.append(e)
    slide['elements'] = keep

(OUT / 'manifest.json').write_text(json.dumps(manifest, indent=1, ensure_ascii=False))
print(f'trimmed {trimmed}, dropped {dropped} empty, '
      f'{sum(len(s["elements"]) for s in manifest)} remain')
