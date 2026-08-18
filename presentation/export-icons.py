#!/usr/bin/env python3
"""Every icon, logo and mascot in the deck, as a transparent PNG.

SVGs are rasterised through Chrome at their natural aspect ratio, longest side
2048px. Raster assets are copied as they are.

The two employer marks are not plain images: trace.css paints them as CSS masks
in a token colour, so the file on disk is a silhouette and the slide shows a
solid shape in muted-ink or on-ink-dim. Both painted variants are exported
alongside the raw silhouette, because pulling dash0-logo.svg straight into Slides
gets you the mask, not the mark as the deck draws it.
"""
import re, shutil, subprocess
from pathlib import Path
from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
OUT = HERE / 'export' / 'icons'
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
LONGEST = 1024          # css px; doubled by the device scale factor
S = 2

MARKS = {   # class -> (svg, aspect from its viewBox, per trace.css)
    'dash0':     ('dash0-logo.svg', 267 / 51),
    'dynatrace': ('dynatrace-logo.svg', 800 / 142),
}
PAINT = {'on-dark': '#8A93BC', 'on-light': '#5B6180'}   # on-ink-dim / muted-ink

def aspect(svg_text):
    m = re.search(r'viewBox\s*=\s*["\']\s*[\d.-]+\s+[\d.-]+\s+([\d.]+)\s+([\d.]+)', svg_text)
    if m:
        return float(m.group(1)) / float(m.group(2))
    w = re.search(r'\bwidth\s*=\s*["\']([\d.]+)', svg_text)
    h = re.search(r'\bheight\s*=\s*["\']([\d.]+)', svg_text)
    return (float(w.group(1)) / float(h.group(1))) if w and h else 1.0

def shoot(html, w, h, path):
    page = HERE / '_icon.html'
    page.write_text('<!doctype html><html><head><meta charset="utf-8">'
                    '<link rel="stylesheet" href="trace.css">'
                    '<style>html,body{margin:0;background:transparent}</style></head>'
                    f'<body>{html}</body></html>')
    subprocess.run([CHROME, '--headless', '--disable-gpu', '--hide-scrollbars',
                    '--allow-file-access-from-files', f'--force-device-scale-factor={S}',
                    '--default-background-color=00000000', '--virtual-time-budget=5000',
                    f'--window-size={w},{h}', f'--screenshot={path}', f'file://{page}'],
                   check=True, capture_output=True)
    page.unlink(missing_ok=True)
    im = Image.open(path).convert('RGBA')
    bbox = im.getbbox()
    if bbox and bbox != (0, 0, im.width, im.height):
        im.crop(bbox).save(path)                    # trim the transparent margin
        im = Image.open(path)
    return im.size, bbox != (0, 0, im.width, im.height)


def plain_qr(svg, out, module_px=32, quiet=4):
    """Rebuild a crisp, standard-polarity QR from the SVG's module coordinates.

    Rasterising the artwork gives round modules that decoders struggle with. The
    geometry is a plain grid, so read the painted cells straight out of the file
    — they are the dark modules — and redraw them as squares. Refuses to write a
    code it cannot read back.
    """
    import numpy as np, cv2
    text = svg.read_text()
    n = int(float(re.search(r'viewBox="[\d.\s]*?([\d.]+)\s+[\d.]+"', text).group(1)))
    grid = np.zeros((n, n), bool)
    for m in re.finditer(r'<rect\b[^>]*>', text):
        t = m.group(0)
        g = lambda k, d='0': float((re.search(rf'\b{k}="([\d.]+)"', t) or [None, d])[1])
        x, y, w, h = g('x'), g('y'), g('width', '1'), g('height', '1')
        grid[int(y):int(y + h), int(x):int(x + w)] = True
    for m in re.finditer(r'<circle\b[^>]*>', text):
        t = m.group(0)
        g = lambda k: float(re.search(rf'\b{k}="([\d.]+)"', t).group(1))
        grid[int(g('cy')), int(g('cx'))] = True

    canvas = np.full((n + 2 * quiet, n + 2 * quiet), 255, np.uint8)
    canvas[quiet:quiet + n, quiet:quiet + n] = np.where(grid, 0, 255)
    big = np.kron(canvas, np.ones((module_px, module_px), np.uint8))
    data, *_ = cv2.QRCodeDetector().detectAndDecode(np.stack([big] * 3, -1))
    assert data, f'{svg.name}: rebuilt code does not decode — do not ship it'
    Image.fromarray(big).save(out)
    return out, data

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (HERE / 'export' / 'mascots').mkdir(parents=True, exist_ok=True)
    rows = []

    for svg in sorted((HERE / 'assets').glob('*.svg')):
        a = aspect(svg.read_text())
        w, h = (LONGEST, round(LONGEST / a)) if a >= 1 else (round(LONGEST * a), LONGEST)

        # The QR SVGs paint the DARK modules in paper cream and leave the light
        # cells transparent, so on an ink slide they read as an inverted code —
        # light modules on a dark field. Both places the deck uses them are dark
        # slides, so that is right on stage, invisible previewed on white, and the
        # wrong polarity for a scanner on a light background.
        #
        # The stylised rendering (round modules) is also hard on decoders: rendered
        # straight, Adriana's decodes and Kasper's does not, in either polarity.
        # So the scannable export is rebuilt from the module coordinates rather
        # than rasterised from the artwork, and the decode is asserted here — the
        # data in both files is intact, it is the styling that defeats the reader.
        if svg.stem.startswith('qr-'):
            size, alpha = shoot(f'<img src="assets/{svg.name}" style="display:block;'
                                f'width:{w}px;height:{h}px">', w, h,
                                OUT / f'{svg.stem}-on-dark.png')
            rows.append((svg.stem + '-on-dark.png', size, alpha))
            path, url = plain_qr(svg, OUT / f'{svg.stem}.png')
            rows.append((svg.stem + '.png', Image.open(path).size, False))
            print(f'    {svg.stem} decodes -> {url}')
            continue

        size, alpha = shoot(f'<img src="assets/{svg.name}" style="display:block;'
                            f'width:{w}px;height:{h}px">', w, h, OUT / f'{svg.stem}.png')
        rows.append((svg.stem + '.png', size, alpha))

    for cls, (_, a) in MARKS.items():
        for tone, colour in PAINT.items():
            h = round(LONGEST / a)
            size, alpha = shoot(
                f'<div class="employer-mark is-{cls}" style="width:{LONGEST}px;height:{h}px;'
                f'aspect-ratio:auto;margin:0;background-color:{colour}"></div>',
                LONGEST, h, OUT / f'{cls}-mark-{tone}.png')
            rows.append((f'{cls}-mark-{tone}.png', size, alpha))

    for raster in sorted((HERE / 'assets').glob('*')):
        if raster.suffix.lower() in ('.png', '.jpg', '.jpeg'):
            shutil.copy2(raster, OUT / raster.name)
            rows.append((raster.name, Image.open(raster).size, raster.suffix == '.png'))

    n = 0
    for m in sorted((HERE / 'img' / 'mascots').glob('*.png')):
        shutil.copy2(m, HERE / 'export' / 'mascots' / m.name); n += 1

    print(f'{len(rows)} icons -> export/icons/ · {n} mascots -> export/mascots/\n')
    for name, size, alpha in rows:
        print(f'  {name:34} {str(size):14} {"alpha" if alpha else "opaque"}')

if __name__ == '__main__':
    main()
