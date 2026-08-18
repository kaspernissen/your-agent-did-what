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
DURATION = 4.6          # matches .flow-dot's animation
FRAMES = 46             # 10fps
S = 2
# rows are: label 120..700 | track 700..880 | box 880..1160 | track 1160..1340 | label 1340..
# the right edge must stop at 1340 or the gen_ai.* names bleed into the crop
CROP = (696, 360, 1341, 768)

JS = '''
  const sec = document.querySelectorAll("deck-stage > section")[__SLIDE__];
  // the box keeps its name and loses its config lines
  const box = sec.querySelector(".chamfer");
  [...box.children].slice(1).forEach(c => c.remove());

  // Read the authored per-dot delay FIRST. The override below is an `animation`
  // shorthand, which resets animation-delay to 0s — read after it and every dot
  // reports 0 and the whole flow moves as one.
  const dots = [...sec.querySelectorAll(".flow-dot")];
  const orig = dots.map(d => parseFloat(getComputedStyle(d).animationDelay) || 0);

  // headless may report prefers-reduced-motion, which disables the dots outright
  const on = document.createElement("style");
  on.textContent = ".flow-dot{animation:flow-travel 4.6s cubic-bezier(.5,0,.5,1) infinite!important}";
  document.head.appendChild(on);

  // Seek each dot to its phase at t, then freeze. setProperty(..., "important")
  // matters: the rule above is !important, and a plain inline value loses to it,
  // which pins every dot at 0s and yields an animation that never moves.
  dots.forEach((d, i) => {
    const seek = (((__T__ - orig[i]) % __DUR__) + __DUR__) % __DUR__;
    d.style.setProperty("animation-delay", (-seek) + "s", "important");
    d.style.setProperty("animation-play-state", "paused", "important");
  });
'''

def main():
    TMP.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    base = (HERE / 'index.html').read_text()
    shot = HERE / '_gif.html'
    frames = []
    for i in range(FRAMES):
        t = DURATION * i / FRAMES
        js = (JS.replace('__SLIDE__', str(SLIDE))
                .replace('__T__', f'{t:.4f}')
                .replace('__DUR__', str(DURATION)))
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
                duration=int(1000 * DURATION / FRAMES), loop=0, optimize=True, disposal=2)
    print(f'\n{out.name}  {frames[0].size}  {FRAMES} frames  '
          f'{out.stat().st_size / 1e6:.1f}MB')

if __name__ == '__main__':
    main()
