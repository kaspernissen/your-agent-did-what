#!/usr/bin/env python3
"""Export every visual element of the deck as a PNG, for rebuilding in Google Slides.

Renders each slide through the deck's own component — the same goTo(i) path every
verified screenshot in this project uses — at 2x, opaque, then crops the elements
out of that render using geometry measured by export-model.html.

Two earlier attempts failed and are worth not repeating:
  * splitting index.html into sections with a regex and rendering them standalone.
    Without deck-stage.js the section has no height, so it collapsed to its header;
    and the splitter silently misaligned slide N's geometry with slide M's pixels.
  * knocking the background out for transparent crops. The deck has exactly two
    grounds, so opaque crops on a matching slide background are indistinguishable,
    and the knockout was the source of most of the breakage.

Index alignment is not assumed: goTo(i) was verified against model[i] by rendering.
"""
import json, re, subprocess, unicodedata
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
OUT = HERE / 'export'
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
SCALE = 2
PAD = 6          # bleed in slide px, so antialiased edges and soft shadows survive
GROUND = {'ground-paper': '#FAF7F2', 'ground-ink': '#10142E'}

def slug(s, n=40):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return (re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', s.lower())).strip('-') or 'slide')[:n]

def main():
    model = json.loads(Path('/tmp/model.json').read_text())
    base = (HERE / 'index.html').read_text()
    assert len(model) == 72, len(model)
    for d in ('slides', 'elements', 'footers'):
        (OUT / d).mkdir(parents=True, exist_ok=True)

    spoken = next(m['n'] for m in model if m['label'] == 'Divider — Appendix') - 1
    shot, manifest = HERE / '_shot.html', []

    for i, m in enumerate(model):
        tag = f"{m['n']:02d}-{slug(m['label'])}"
        shot.write_text(base.replace('</body>',
            f'<script>addEventListener("load",()=>{{document.querySelector("deck-stage").goTo({i});}});'
            '</script></body>', 1))
        plate = OUT / 'slides' / f'{tag}.png'
        subprocess.run([CHROME, '--headless', '--disable-gpu', '--hide-scrollbars',
                        '--allow-file-access-from-files', f'--force-device-scale-factor={SCALE}',
                        '--virtual-time-budget=6000', '--window-size=1920,1080',
                        f'--screenshot={plate}', f'file://{shot}'], check=True, capture_output=True)
        im = Image.open(plate).convert('RGB')
        assert im.size == (1920 * SCALE, 1080 * SCALE), im.size

        d = OUT / 'elements' / tag
        d.mkdir(exist_ok=True)
        kept = []
        for k, e in enumerate(m['elements'], 1):
            x, y = max(0, e['x'] - PAD), max(0, e['y'] - PAD)
            r, b = min(1920, e['x'] + e['w'] + PAD), min(1080, e['y'] + e['h'] + PAD)
            src = Path(e['src']).stem if e.get('src') else ''
            fn = f"{k:02d}-{e['kind']}{'-' + slug(src, 24) if src else ''}.png"
            im.crop((x * SCALE, y * SCALE, r * SCALE, b * SCALE)).save(d / fn)
            kept.append({'file': f'elements/{tag}/{fn}', 'kind': e['kind'],
                         'x': e['x'], 'y': e['y'], 'w': e['w'], 'h': e['h']})

        # the footer rail and its mascot ride on a ::after, so they have no element box
        if 'deck-footer' in base:
            variant = 'capybara'
            fp = OUT / 'footers' / f'{variant}-{m["ground"]}.png'
            if not fp.exists():
                im.crop((0, 915 * SCALE, 1920 * SCALE, 1080 * SCALE)).save(fp)

        manifest.append({'n': m['n'], 'label': m['label'], 'slug': slug(m['label']),
                         'part': 'spoken' if m['n'] <= spoken else 'appendix',
                         'ground': GROUND[m['ground']], 'plate': f'slides/{tag}.png',
                         'elements': kept, 'text': m['text'], 'note': m['note']})
        print(f'  {tag}: {len(kept)}', flush=True)

    shot.unlink(missing_ok=True)
    (HERE / '_base.html').unlink(missing_ok=True)
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=1, ensure_ascii=False))
    print(f'\n{len(manifest)} slides, {sum(len(x["elements"]) for x in manifest)} element PNGs')

if __name__ == '__main__':
    main()
