#!/usr/bin/env python3
"""Export every visual element of the deck as a transparent PNG.

Per slide:
  slides/NN-slug.png                 the whole slide, opaque, as reference
  backgrounds/NN-slug.png            the slide with every word removed — ground
                                     furniture only, transparent
  elements/NN-slug/NN-kind.png       each element that paints, transparent
  elements/NN-slug/group-NN.png      each top-level block, so composites like the
                                     s3 timeline arrive whole as well as in pieces

Rendering goes through the deck's own component with goTo(i) — the path every
verified screenshot in this project uses. Two earlier approaches failed: splitting
index.html with a regex and rendering sections standalone (no deck-stage.js means
no height, so the section collapsed to its header), and trusting a fixed selector
list for elements (it caught none of the gradient rules or bordered nodes).

Transparency needs three overrides. deck-stage paints twice inside its shadow root
(:host and .canvas) and the section paints its ground on top; miss one and the
render comes back fully opaque.
"""
import json, re, subprocess, unicodedata
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
OUT = HERE / 'export'
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
SCALE = 2
PAD = 8
GROUND = {'ground-paper': '#FAF7F2', 'ground-ink': '#10142E'}
RGB = {'ground-paper': (250, 247, 242), 'ground-ink': (16, 20, 46)}

CLEAR = '''
  const ds = document.querySelector("deck-stage");
  ds.style.setProperty("background","transparent","important");
  const st = document.createElement("style");
  st.textContent = ".canvas{background:transparent!important}";
  ds.shadowRoot.appendChild(st);
  sec.style.setProperty("background","transparent","important");
'''
STRIP = '''
  /* Do not DELETE the text — card and panel heights are content-driven, so
     removing it collapses every box and the measured crop rectangles no longer
     match what is on screen. Painting it transparent keeps the layout identical
     to the real slide while nothing renders. Diagram labels inside an <svg> are
     artwork rather than copy, so they stay. Nothing in this deck derives a
     border or a mask from currentColor, which is what makes this safe. */
  const t = document.createElement("style");
  t.textContent = "deck-stage > section, deck-stage > section *:not(svg):not(svg *)" +
    "{color:transparent!important;-webkit-text-fill-color:transparent!important}";
  document.head.appendChild(t);
'''

def slug(s, n=40):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return (re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', s.lower())).strip('-') or 'slide')[:n]

def render(base, shot, i, out, extra=''):
    shot.write_text(base.replace('</body>',
        f'<script>addEventListener("load",()=>{{'
        f'document.querySelector("deck-stage").goTo({i});'
        f'const sec=document.querySelectorAll("deck-stage > section")[{i}];'
        f'{CLEAR}{extra}}});</script></body>', 1))
    subprocess.run([CHROME, '--headless', '--disable-gpu', '--hide-scrollbars',
                    '--allow-file-access-from-files', f'--force-device-scale-factor={SCALE}',
                    '--default-background-color=00000000', '--virtual-time-budget=6000',
                    '--window-size=1920,1080', f'--screenshot={out}', f'file://{shot}'],
                   check=True, capture_output=True)
    im = Image.open(out).convert('RGBA')
    assert im.size == (1920 * SCALE, 1080 * SCALE), im.size
    return im

def main():
    model = json.loads(Path('/tmp/model.json').read_text())
    base = (HERE / 'index.html').read_text()
    assert len(model) == 72, len(model)
    for d in ('slides', 'backgrounds', 'backgrounds-flat', 'elements'):
        (OUT / d).mkdir(parents=True, exist_ok=True)

    spoken = next(m['n'] for m in model if m['label'] == 'Divider — Appendix') - 1
    shot, manifest = HERE / '_shot.html', []

    for i, m in enumerate(model):
        tag = f"{m['n']:02d}-{slug(m['label'])}"

        # one transparent render carries both the reference plate and every crop
        full = render(base, shot, i, OUT / 'slides' / f'{tag}.png')
        plate = Image.new('RGBA', full.size, RGB[m['ground']] + (255,))
        plate.alpha_composite(full)
        plate.convert('RGB').save(OUT / 'slides' / f'{tag}.png')

        # everything cropped below comes from the text-free render, so no element
        # ships with copy baked into it
        live = render(base, shot, i, OUT / 'backgrounds' / f'{tag}.png', STRIP)
        flat = Image.new('RGBA', live.size, RGB[m['ground']] + (255,))
        flat.alpha_composite(live)
        flat.convert('RGB').save(OUT / 'backgrounds-flat' / f'{tag}.png')

        d = OUT / 'elements' / tag
        d.mkdir(exist_ok=True)
        kept = []
        items = ([('group', k, g) for k, g in enumerate(m['groups'], 1)] +
                 [('el', k, e) for k, e in enumerate(m['elements'], 1)])
        for what, k, e in items:
            if e['kind'] == 'deck-footer':
                continue                      # its mascot is a ::after outside the box; see footers/
            x, y = max(0, e['x'] - PAD), max(0, e['y'] - PAD)
            r, b = min(1920, e['x'] + e['w'] + PAD), min(1080, e['y'] + e['h'] + PAD)
            crop = live.crop((x * SCALE, y * SCALE, r * SCALE, b * SCALE))
            if not crop.getbbox():
                continue                      # a layout box that paints nothing on its own
            src = Path(e['src']).stem if e.get('src') else ''
            fn = (f'group-{k:02d}.png' if what == 'group'
                  else f"{k:02d}-{e['kind']}{'-' + slug(src, 24) if src else ''}.png")
            crop.save(d / fn)
            kept.append({'file': f'elements/{tag}/{fn}', 'kind': e['kind'] if what == 'el' else 'group',
                         'x': e['x'], 'y': e['y'], 'w': e['w'], 'h': e['h']})

        manifest.append({'n': m['n'], 'label': m['label'], 'slug': slug(m['label']),
                         'part': 'spoken' if m['n'] <= spoken else 'appendix',
                         'ground': GROUND[m['ground']], 'plate': f'slides/{tag}.png',
                         'background': f'backgrounds/{tag}.png',
                         'background_flat': f'backgrounds-flat/{tag}.png',
                         'elements': kept, 'text': m['text'], 'note': m['note']})
        print(f'  {tag}: {len(kept)}', flush=True)

    shot.unlink(missing_ok=True)
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=1, ensure_ascii=False))
    print(f'\n{len(manifest)} slides, {sum(len(x["elements"]) for x in manifest)} element PNGs')

if __name__ == '__main__':
    main()
