"""Cut named poses out of a character sheet as transparent PNGs.

Background removal is a flood fill from the border, not a global colour key, because the
goose's body is nearly the same white as the paper. The 1px erode afterwards is what stops
the halo: the sheets are JPEG, so every outline has a ring of pixels blended toward white,
and those read as a pale fringe on a dark slide even though they look fine on a light one.
"""
import sys, numpy as np
from PIL import Image

def background_mask(rgb, tol=7):
    # tol is deliberately tight. Measured on these sheets: clear background is min-channel
    # 251-255, the cream body is 227 median and 244 at its lightest. A loose tolerance lets
    # the fill leak through the body and chew its outline from the inside.
    near_white = (rgb.min(axis=2) >= 255 - tol)
    reach = np.zeros(near_white.shape, bool)
    reach[0] |= near_white[0]; reach[-1] |= near_white[-1]
    reach[:, 0] |= near_white[:, 0]; reach[:, -1] |= near_white[:, -1]
    while True:
        before = reach.sum()
        for s in range(4):
            g = np.zeros_like(reach)
            if s == 0: g[1:, :] = reach[:-1, :]
            elif s == 1: g[:-1, :] = reach[1:, :]
            elif s == 2: g[:, 1:] = reach[:, :-1]
            else: g[:, :-1] = reach[:, 1:]
            reach |= g & near_white
        if reach.sum() == before: return reach

def erode(mask):
    """Drop one pixel from the edge of the opaque region — the JPEG fringe lives there."""
    out = mask.copy()
    for s in range(4):
        g = np.ones_like(mask)
        if s == 0: g[1:, :] = mask[:-1, :]
        elif s == 1: g[:-1, :] = mask[1:, :]
        elif s == 2: g[:, 1:] = mask[:, :-1]
        else: g[:, :-1] = mask[:, 1:]
        out &= g
    return out

sheet, outdir = sys.argv[1], sys.argv[2]
POSES = eval(sys.argv[3])

src = Image.open(sheet).convert('RGB')
rgb = np.asarray(src)
opaque = erode(~background_mask(rgb))

rgba = np.dstack([rgb, np.where(opaque, 255, 0).astype(np.uint8)])
for name, (x0, y0, x1, y1) in POSES.items():
    sub = rgba[y0:y1, x0:x1]
    ys, xs = np.nonzero(sub[:, :, 3])
    if not len(ys):
        print(f"  !! {name}: empty"); continue
    sub = sub[ys.min():ys.max()+1, xs.min():xs.max()+1]
    img = Image.fromarray(sub, 'RGBA')
    path = f"{outdir}/{name}.png"
    img.save(path, optimize=True)
    print(f"  {name+'.png':<34} {img.size[0]:>4}x{img.size[1]:<4}  "
          f"{round(len(open(path,'rb').read())/1024):>4}KB  "
          f"opaque {100*(sub[:,:,3]>0).mean():.0f}%")
