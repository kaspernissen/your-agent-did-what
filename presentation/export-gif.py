#!/usr/bin/env python3
"""Slide 22's normalizer flow as an animated GIF.

The dots run a 4.6s CSS loop with a per-dot animation-delay. Frames are captured
by SEEKING rather than by waiting: each dot gets a negative animation-delay equal
to its phase at frame time t, and animation-play-state:paused holds it there. The
phase is taken modulo the duration so the last frame joins the first cleanly and
the GIF loops without a jump.

The attribute columns are cropped away — the speaker adds those as live text in
Slides — and the box keeps only its gen_ai_normalizer label, losing the sources
and remove_originals lines.

Rendered on the slide's own ink ground rather than on transparency: GIF alpha is
one bit, so a soft-edged dot on transparency fringes badly. Place it on a
#10142E background.
"""
import subprocess
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
OUT = HERE / 'export' / 'composites'
TMP = Path('/Users/kaspernissen/.claude/jobs/3ed0631d/tmp/gifframes')
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

SLIDE = 21              # 0-based: slide 22
TRAVERSAL = 3.5         # seconds for a dot to cross one track
FPS = 25                # 10fps read as stepping; 25 reads as flow
PARTICLES = 3           # dots per track, evenly spaced around the cycle
INTERVAL = int(1000 / FPS)
FRAMES = round(TRAVERSAL * FPS)
CSS_CYCLE = 4.6         # the authored duration, used only to rescale the row stagger
S = 2
CROP = (696, 360, 1341, 768)

JS = '''
  const sec = document.querySelectorAll("deck-stage > section")[__SLIDE__];
  // the box keeps its name and loses its config lines
  const box = sec.querySelector(".chamfer");
  [...box.children].slice(1).forEach(c => c.remove());

  const TRAVERSAL = __TRAVERSAL__, PARTICLES = __PARTICLES__, CSS_CYCLE = __CSS_CYCLE__;

  /* Give each track a stream rather than a single dot. The authored per-dot delay
     staggers the rows into a cascade, so it is kept — rescaled from the 4.6s CSS
     cycle to the traversal we are rendering — and each extra particle is spaced an
     equal fraction of the cycle behind it. */
  const seeds = [...sec.querySelectorAll(".flow-dot")];
  const parts = [];
  for (const seed of seeds) {
    const base = (parseFloat(getComputedStyle(seed).animationDelay) || 0) * (TRAVERSAL / CSS_CYCLE);
    for (let k = 0; k < PARTICLES; k++) {
      const el = k === 0 ? seed : seed.parentNode.appendChild(seed.cloneNode(true));
      parts.push([el, base + k * TRAVERSAL / PARTICLES]);
    }
  }

  /* Do not try to SEEK the CSS animation. Pausing it at a negative animation-delay
     looked right and was not: headless rendered the phases out of order, so
     consecutive frames put the dot at 176px, 62px, 176px, 3px along a 180px track.
     Position every particle directly — same keyframes, same easing, computed here. */
  function bezier(p1x, p1y, p2x, p2y){
    const cx = 3*p1x, bx = 3*(p2x-p1x)-cx, ax = 1-cx-bx;
    const cy = 3*p1y, by = 3*(p2y-p1y)-cy, ay = 1-cy-by;
    const fx = t => ((ax*t+bx)*t+cx)*t;
    const dfx = t => (3*ax*t+2*bx)*t+cx;
    const fy = t => ((ay*t+by)*t+cy)*t;
    return x => { let t = x;
      for (let i = 0; i < 12; i++){
        const e = fx(t) - x; if (Math.abs(e) < 1e-7) break;
        const d = dfx(t);    if (Math.abs(d) < 1e-7) break;
        t -= e/d;
      }
      return fy(t); };
  }
  const ease = bezier(.5, 0, .5, 1);          // matches .flow-dot's timing function

  for (const [el, off] of parts) {
    const p = ((((__T__ - off) % TRAVERSAL) + TRAVERSAL) % TRAVERSAL) / TRAVERSAL;
    // keyframes: 0% left:0 opacity:0 · 6% opacity:1 · 94% opacity:1 · 100% left:100% opacity:0
    const op = p < 0.06 ? p/0.06 : (p > 0.94 ? (1-p)/0.06 : 1);
    el.style.setProperty("animation", "none", "important");
    el.style.setProperty("left", (ease(p) * 100) + "%", "important");
    el.style.setProperty("opacity", String(op), "important");
  }
'''

def main():
    TMP.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    base = (HERE / 'index.html').read_text()
    shot = HERE / '_gif.html'
    frames = []
    for i in range(FRAMES):
        t = TRAVERSAL * i / FRAMES
        js = (JS.replace('__SLIDE__', str(SLIDE))
                .replace('__T__', f'{t:.4f}')
                .replace('__TRAVERSAL__', str(TRAVERSAL))
                .replace('__PARTICLES__', str(PARTICLES))
                .replace('__CSS_CYCLE__', str(CSS_CYCLE)))
        shot.write_text(base.replace('</body>',
            f'<script>addEventListener("load",()=>{{'
            f'document.querySelector("deck-stage").goTo({SLIDE});{js}}});</script></body>', 1))
        png = TMP / f'f{i:03d}.png'
        subprocess.run([CHROME, '--headless', '--disable-gpu', '--hide-scrollbars',
                        '--allow-file-access-from-files', f'--force-device-scale-factor={S}',
                        '--virtual-time-budget=4000', '--window-size=1920,1080',
                        f'--screenshot={png}', f'file://{shot}'], check=True, capture_output=True)
        im = Image.open(png).convert('RGB').crop(tuple(v * S for v in CROP))
        frames.append(im)
        if i % 10 == 0:
            print(f'  frame {i+1}/{FRAMES}', flush=True)
    shot.unlink(missing_ok=True)

    # a dot has to actually move, or the seek silently did nothing
    distinct = len({f.tobytes() for f in frames})
    assert distinct >= FRAMES * 0.8, f'only {distinct} distinct of {FRAMES} frames — the seek is not taking'

    pal = [f.convert('P', palette=Image.ADAPTIVE, colors=128) for f in frames]
    out = OUT / '22-normalizer-flow.gif'
    pal[0].save(out, save_all=True, append_images=pal[1:],
                duration=INTERVAL, loop=0, optimize=True, disposal=2)
    print(f'\n{out.name}  {frames[0].size}  {FRAMES} frames  '
          f'{FRAMES*INTERVAL/1000:.1f}s loop · {TRAVERSAL}s traversal · {FPS}fps · {PARTICLES}/track  '
          f'{out.stat().st_size / 1e6:.1f}MB')

if __name__ == '__main__':
    main()
