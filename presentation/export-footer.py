#!/usr/bin/env python3
"""The footer — gradient rule and the mascot riding it — as transparent PNGs.

The footer mascot is a CSS ::after with a background-image and a 13deg rotation,
so it has no element box and cannot be cropped out of a slide render by geometry.
It is rendered by hiding everything on the slide except .deck-footer, then
auto-cropping to whatever ink is left.

Two things this has to get right:

  * Transparency needs three overrides. deck-stage paints twice inside its shadow
    root (:host and .canvas) and the section paints its ground on top; miss one
    and the render comes back fully opaque.
  * Resolution. The footer draws the mascot at 96px, so a 2x screenshot
    downsamples the 1260px source to ~190px. The standalone cuts scale the
    ::after itself to ~900px instead. At that size it no longer fits where the
    footer sits and deck-stage clips it, so the footer is stretched to the whole
    slide and the mascot placed well inside — and the crop is asserted not to
    touch an edge, because a clipped mascot loses its legs and still looks fine
    in a thumbnail.
"""
import subprocess
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
OUT = HERE / 'export' / 'footers'
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
S = 4               # composites keep the footer's real proportions, so scale the shot
SLIDE = 16          # any slide carrying a plain .deck-footer

SETUP = '''
  const sec = document.querySelectorAll("deck-stage > section")[%d];
  [...sec.children].forEach(c => { if (!c.classList.contains("deck-footer")) c.style.display = "none"; });
  const ds = document.querySelector("deck-stage");
  ds.style.setProperty("background", "transparent", "important");
  const st = document.createElement("style");
  st.textContent = ".canvas{background:transparent!important}";
  ds.shadowRoot.appendChild(st);
  sec.style.setProperty("background", "transparent", "important");
  const f = sec.querySelector(".deck-footer");
  const css = (t) => { const e = document.createElement("style"); e.textContent = t;
                       document.head.appendChild(e); };
''' % SLIDE

FULL = '.deck-footer{top:0!important;bottom:auto!important;height:1080px!important}'
BIG_CAPY = (FULL + '.deck-footer::after{width:900px!important;height:722px!important;'
            'left:440px!important;top:87px!important;right:auto!important;bottom:auto!important}')
BIG_BEAV = (FULL + '.deck-footer.is-beaver::after{width:740px!important;height:880px!important;'
            'left:590px!important;top:100px!important;right:auto!important;bottom:auto!important}')
NO_RULE = '.deck-footer::before{display:none!important}'
NO_MASCOT = '.deck-footer::after{background-image:none!important}'

VARIANTS = {
    'footer-rule-with-capybara': '',
    'footer-rule-with-beaver':   'f.classList.add("is-beaver");',
    'footer-rule':               f'css(`{NO_MASCOT}`);',
    'footer-capybara':           f'css(`{NO_RULE}{BIG_CAPY}`);',
    'footer-beaver':             f'f.classList.add("is-beaver"); css(`{NO_RULE}{BIG_BEAV}`);',
}

base = (HERE / 'index.html').read_text()
shot = HERE / '_footer.html'
OUT.mkdir(parents=True, exist_ok=True)
for name, js in VARIANTS.items():
    shot.write_text(base.replace('</body>',
        f'<script>addEventListener("load",()=>{{'
        f'document.querySelector("deck-stage").goTo({SLIDE});{SETUP}{js}}});</script></body>', 1))
    path = OUT / f'{name}.png'
    subprocess.run([CHROME, '--headless', '--disable-gpu', '--hide-scrollbars',
                    '--allow-file-access-from-files', f'--force-device-scale-factor={S}',
                    '--default-background-color=00000000', '--virtual-time-budget=6000',
                    '--window-size=1920,1080', f'--screenshot={path}', f'file://{shot}'],
                   check=True, capture_output=True)
    im = Image.open(path).convert('RGBA')
    bbox = im.getbbox()
    assert bbox and bbox != (0, 0, im.width, im.height), f'{name}: no alpha, nothing to crop'
    if 'rule' not in name:
        assert bbox[0] > 0 and bbox[1] > 0 and bbox[2] < im.width and bbox[3] < im.height, \
            f'{name}: clipped at the slide edge, bbox={bbox}'
    im.crop(bbox).save(path)
    print(f'  {name:28} {Image.open(path).size}  transparent')
shot.unlink(missing_ok=True)
