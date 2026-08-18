#!/usr/bin/env python3
"""Cover slide furniture — background, diagonal and the horizontal rule, as PNGs.

Text is removed by deleting text nodes on the live slide rather than by hiding
selectors: the cover's words live in four elements, two of which share a parent
with artwork that has to stay.

Transparency needs three overrides, not one. deck-stage paints twice inside its
shadow root — `:host{background:#000}` and `.canvas{background:#fff}` — and the
section paints its own ground on top. Miss any of the three and the render comes
back fully opaque, which is what --default-background-color alone gets you.
"""
import subprocess
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
OUT = HERE / 'export' / 'cover'
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
OUT.mkdir(parents=True, exist_ok=True)

STRIP_TEXT = '''
  const sec = document.querySelectorAll("deck-stage > section")[0];
  const w = document.createTreeWalker(sec, NodeFilter.SHOW_TEXT);
  const dead = []; while (w.nextNode()) dead.push(w.currentNode);
  dead.forEach(n => n.remove());
'''
HIDE = 'sec.querySelectorAll(%s).forEach(e => e.style.display = "none");'
CLEAR = '''
  const ds = document.querySelector("deck-stage");
  ds.style.setProperty("background", "transparent", "important");
  const st = document.createElement("style");
  st.textContent = ".canvas{background:transparent!important}";
  ds.shadowRoot.appendChild(st);
  sec.style.setProperty("background", "transparent", "important");
'''
MARKS = '"img, .qr-tile, .employer-mark"'

VARIANTS = {
    # every mark the cover draws, with the words taken out
    'cover-no-text':            (STRIP_TEXT, False, None),
    # ground, diagonal and the rule — no logos, no QR codes, no mascot
    'cover-background':         (STRIP_TEXT + HIDE % MARKS, False, None),
    # the same, on transparency, to drop over any Slides background
    'cover-background-alpha':   (STRIP_TEXT + HIDE % MARKS + CLEAR, True, None),
    # the horizontal rule and its two nodes alone, tight
    'axis-rule':                (STRIP_TEXT + HIDE % '"img, .diagonal-split, .qr-tile, .employer-mark"'
                                 + CLEAR, True, (0, 756, 1920, 816)),
    # the navy diagonal alone
    'diagonal-panel':           (STRIP_TEXT + HIDE % '"img, .axis, .axis-node, .qr-tile, .employer-mark"'
                                 + CLEAR, True, None),
}

base = (HERE / 'index.html').read_text()
shot = HERE / '_cover.html'
S = 2
for name, (js, alpha, crop) in VARIANTS.items():
    shot.write_text(base.replace('</body>',
        f'<script>addEventListener("load",()=>{{'
        f'document.querySelector("deck-stage").goTo(0);{js}}});</script></body>', 1))
    path = OUT / f'{name}.png'
    cmd = [CHROME, '--headless', '--disable-gpu', '--hide-scrollbars',
           '--allow-file-access-from-files', f'--force-device-scale-factor={S}',
           '--virtual-time-budget=6000', '--window-size=1920,1080',
           f'--screenshot={path}', f'file://{shot}']
    if alpha:
        cmd.insert(-1, '--default-background-color=00000000')
    subprocess.run(cmd, check=True, capture_output=True)
    im = Image.open(path).convert('RGBA')
    if crop:
        im = im.crop(tuple(v * S for v in crop))
        im.save(path)
    bbox = im.getbbox()
    opaque = bbox == (0, 0, im.width, im.height)
    print(f'  {name:26} {im.size}  {"opaque" if opaque else "alpha ok"}')
    if alpha and opaque:
        print(f'    !! expected transparency and did not get it')
shot.unlink(missing_ok=True)
