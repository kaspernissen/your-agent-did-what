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


if __name__ == "__main__":
    unittest.main()
