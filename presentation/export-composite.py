#!/usr/bin/env python3
"""Hand-picked composites: a whole diagram as one PNG, words out, icons in.

The deck draws several icons as text characters — the arrows between slide 7's
boxes, the loop glyph in each card's label, the reversal glyph under the bracket.
The normal text-free export paints those out with the prose, which leaves the
boxes bare and the arrows missing. Here the glyphs are whitelisted by codepoint
and re-inked after the blanket transparency is applied, so the composite carries
the drawing and none of the copy.

Everything is auto-trimmed to its alpha bounding box, so the crop is exactly the
diagram — which is why the footer rail has to be hidden first, or the trim would
stretch the crop down to it.
"""
import subprocess
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
OUT = HERE / 'export' / 'composites'
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
S = 2

# The characters this deck uses as iconography rather than as words:
#   U+2192 →   U+21BA ↺   U+2726 ✦   U+2699 ⚙   U+21C6 ⇆   U+21C4 ⇄
# U+21C6 is the MCP box's glyph (&#8646;) and is easy to confuse with U+21C4 —
# getting it wrong silently drops one icon out of the composite.
ICONS = r'\\u2192\\u2190\\u21BA\\u21BB\\u2726\\u2699\\u21C6\\u21C4\\u21D2\\u21E2'

SETUP = '''
  const sec = document.querySelectorAll("deck-stage > section")[__IDX__];
  const ds = document.querySelector("deck-stage");
  ds.style.setProperty("background","transparent","important");
  const sh = document.createElement("style");
  sh.textContent = ".canvas{background:transparent!important}";
  ds.shadowRoot.appendChild(sh);
  sec.style.setProperty("background","transparent","important");
  const foot = sec.querySelector(".deck-footer");
  if (foot) foot.style.display = "none";      // else the trim reaches down to it

  // wrap every icon glyph so it can be re-inked once the words go transparent
  const ICON = new RegExp("[__ICONS__]", "u");
  const marks = [];
  const walk = document.createTreeWalker(sec, NodeFilter.SHOW_TEXT);
  const nodes = []; while (walk.nextNode()) nodes.push(walk.currentNode);
  for (const n of nodes) {
    if (!n.textContent || !ICON.test(n.textContent)) continue;
    if (n.parentElement && n.parentElement.closest("svg")) continue;
    const frag = document.createDocumentFragment();
    for (const part of n.textContent.split(new RegExp("([__ICONS__])", "gu"))) {
      if (!part) continue;
      if (ICON.test(part)) {
        const sp = document.createElement("span");
        sp.textContent = part;
        sp.dataset.icon = "1";
        frag.appendChild(sp);
        marks.push(sp);
      } else {
        frag.appendChild(document.createTextNode(part));
      }
    }
    n.parentNode.replaceChild(frag, n);
  }
  const inks = marks.map(m => getComputedStyle(m).color);   // capture before blanking

  const t = document.createElement("style");
  t.textContent = "deck-stage > section, deck-stage > section *:not(svg):not(svg *)" +
    "{color:transparent!important;-webkit-text-fill-color:transparent!important}";
  document.head.appendChild(t);

  marks.forEach((m, i) => {
    m.style.setProperty("color", inks[i], "important");
    m.style.setProperty("-webkit-text-fill-color", inks[i], "important");
  });
'''.replace('__ICONS__', ICONS)

COMPOSITES = {
    # slide 7: the four boxes, the arrows between them, the dashed bracket under
    # model/MCP/tools, and the loop glyph beneath it — as one drawing
    '07-agent-loop': (6, None),
}

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    base = (HERE / 'index.html').read_text()
    shot = HERE / '_composite.html'
    for name, (idx, _) in COMPOSITES.items():
        shot.write_text(base.replace('</body>',
            f'<script>addEventListener("load",()=>{{'
            f'document.querySelector("deck-stage").goTo({idx});'
            f'{SETUP.replace("__IDX__", str(idx))}}});</script></body>', 1))
        path = OUT / f'{name}.png'
        subprocess.run([CHROME, '--headless', '--disable-gpu', '--hide-scrollbars',
                        '--allow-file-access-from-files', f'--force-device-scale-factor={S}',
                        '--default-background-color=00000000', '--virtual-time-budget=6000',
                        '--window-size=1920,1080', f'--screenshot={path}', f'file://{shot}'],
                       check=True, capture_output=True)
        im = Image.open(path).convert('RGBA')
        bbox = im.getbbox()
        assert bbox and bbox != (0, 0, im.width, im.height), f'{name}: nothing to trim'
        im.crop(bbox).save(path)
        print(f'  {name:20} {Image.open(path).size}  at slide px '
              f'({bbox[0]//S},{bbox[1]//S})')
    shot.unlink(missing_ok=True)

if __name__ == '__main__':
    main()
