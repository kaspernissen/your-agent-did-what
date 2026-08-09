import unittest
from importlib.machinery import SourceFileLoader

check = SourceFileLoader("check_deck", "check-deck.py").load_module()

CLEAN_HTML = """
<deck-stage width="1920" height="1080">
  <section data-label="One" class="ground-ink"><h1 class="title">A</h1>
    <div class="span-bar is-amber" data-emphasis="amber"></div></section>
</deck-stage>
<script type="application/json" id="speaker-notes">["note one"]</script>
"""
CLEAN_CSS = ":root{--ink:#10142E}"


class TestCheckDeck(unittest.TestCase):
    def test_clean_deck_has_no_violations(self):
        self.assertEqual(check.check_deck(CLEAN_HTML, CLEAN_CSS), [])

    def test_flags_missing_data_label(self):
        html = CLEAN_HTML.replace(' data-label="One"', "")
        self.assertTrue(any("data-label" in v for v in check.check_deck(html, CLEAN_CSS)))

    def test_flags_note_count_mismatch(self):
        html = CLEAN_HTML.replace('["note one"]', '["a","b"]')
        self.assertTrue(any("notes" in v.lower() for v in check.check_deck(html, CLEAN_CSS)))

    def test_flags_bullets(self):
        html = CLEAN_HTML.replace("<h1 class=\"title\">A</h1>", "<ul><li>x</li></ul>")
        self.assertTrue(any("bullet" in v.lower() for v in check.check_deck(html, CLEAN_CSS)))

    def test_flags_raw_hex_in_slide_markup(self):
        html = CLEAN_HTML.replace('class="title"', 'class="title" style="color:#FF0000"')
        self.assertTrue(any("hex" in v.lower() for v in check.check_deck(html, CLEAN_CSS)))

    def test_svg_hex_exempt_but_chrome_hex_still_flagged(self):
        """Both halves of the SVG exemption, on one slide.

        Inline <svg> artwork may carry raw hex (outline.md lifts the five
        provider/attribute pairs straight out of presentation/index.html:292-296).
        Slide chrome outside the SVG is still governed.
        """
        art = ('<svg viewBox="0 0 10 10"><g stroke="#BDBDBD">'
               '<rect fill="#F0EFEF" stroke="#D3D3D3"/></g>'
               '<text fill="#595959">x</text></svg>')
        html = CLEAN_HTML.replace('<h1 class="title">A</h1>',
                                  f'<h1 class="title">A</h1>{art}')
        self.assertEqual(check.check_deck(html, CLEAN_CSS), [])

        dirty = CLEAN_HTML.replace(
            '<h1 class="title">A</h1>',
            f'<h1 class="title" style="color:#FF0000">A</h1>{art}')
        hexes = [v for v in check.check_deck(dirty, CLEAN_CSS) if "hex" in v.lower()]
        self.assertEqual(len(hexes), 1, hexes)
        self.assertIn("#FF0000", hexes[0])

    def test_svg_exemption_survives_several_and_nested_svgs(self):
        art = ('<svg><rect fill="#F0EFEF"/><svg x="1"><rect fill="#D3D3D3"/></svg>'
               '<text fill="#595959">x</text></svg>'
               '<svg fill="#123456"/>'
               '<svg><path stroke="#ABCDEF"/></svg>')
        html = CLEAN_HTML.replace('<h1 class="title">A</h1>',
                                  f'<h1 class="title">A</h1>{art}<p>after</p>')
        self.assertEqual(check.check_deck(html, CLEAN_CSS), [])

        after = html.replace('<p>after</p>', '<p style="color:#0F0F0F">after</p>')
        hexes = [v for v in check.check_deck(after, CLEAN_CSS) if "hex" in v.lower()]
        self.assertEqual(len(hexes), 1, hexes)
        self.assertIn("#0F0F0F", hexes[0])

    def test_unclosed_svg_does_not_swallow_the_rest_of_the_slide(self):
        html = CLEAN_HTML.replace(
            '<h1 class="title">A</h1>',
            '<svg><rect fill="#F0EFEF"/><p style="color:#0F0F0F">after</p>')
        hexes = [v for v in check.check_deck(html, CLEAN_CSS) if "hex" in v.lower()]
        self.assertTrue(any("#0F0F0F" in v for v in hexes), hexes)

    def test_flags_two_amber_emphases_on_one_slide(self):
        html = CLEAN_HTML.replace(
            '<div class="span-bar is-amber" data-emphasis="amber"></div>',
            '<div data-emphasis="amber"></div><div data-emphasis="amber"></div>')
        self.assertTrue(any("emphasis" in v.lower() for v in check.check_deck(html, CLEAN_CSS)))

    def test_flags_pure_white_or_black_in_css(self):
        self.assertTrue(any("pure" in v.lower()
                            for v in check.check_deck(CLEAN_HTML, ":root{--x:#ffffff}")))

    def test_flags_two_mascots_on_one_slide(self):
        html = CLEAN_HTML.replace("<h1 class=\"title\">A</h1>",
                                  '<img class="mascot"><img class="mascot">')
        self.assertTrue(any("mascot" in v.lower() for v in check.check_deck(html, CLEAN_CSS)))


    def test_issue_reference_in_prose_is_not_a_color(self):
        """GitHub issue refs are not hex colors — the rule scans style attrs only."""
        html = CLEAN_HTML.replace(
            '<h1 class="title">A</h1>',
            '<p>Donation issue #46069, open PR #185, epics #8416 and #7827.</p>')
        self.assertEqual(check.check_deck(html, CLEAN_CSS), [])

    def test_hex_in_a_style_attribute_is_still_flagged(self):
        html = CLEAN_HTML.replace(
            '<h1 class="title">A</h1>',
            '<p>Issue #46069</p><h1 class="title" style="color:#FF0000">A</h1>')
        v = check.check_deck(html, CLEAN_CSS)
        hexes = [x for x in v if "hex" in x.lower()]
        self.assertEqual(len(hexes), 1, v)
        self.assertIn("#FF0000", hexes[0])


if __name__ == "__main__":
    unittest.main()
