import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")
MENU = (ROOT / "menu.html").read_text(encoding="utf-8")
DATA = (ROOT / "js" / "menu-data.js").read_text(encoding="utf-8")
MENU_JS = (ROOT / "js" / "menu.js").read_text(encoding="utf-8")
PAGES = INDEX + "\n" + MENU


class VisitOnlySiteTests(unittest.TestCase):
    def test_locked_phone_and_address(self):
        self.assertIn("(905) 633-8388", INDEX)
        self.assertIn("tel:+19056338388", INDEX)
        self.assertIn("2405 Fairview St, Unit 3", INDEX)
        self.assertIn("Burlington", INDEX)

    def test_monday_closed(self):
        self.assertRegex(INDEX, r"Closed Mon")
        self.assertIn("Closed Mondays", MENU)

    def test_native_menu_exists(self):
        self.assertIn("menu.html", INDEX)
        self.assertIn("P9", DATA)
        self.assertIn("Dear Saigon Pho", DATA)
        self.assertIn("SP1", DATA)
        self.assertIn("Dear Saigon Platter", DATA)
        self.assertIn("id=\"menuApp\"", MENU)

    def test_menu_search_and_vegetarian_filter(self):
        self.assertIn('id="menuSearch"', MENU)
        self.assertIn('id="vegFilter"', MENU)
        self.assertIn('id="menuChips"', MENU)
        self.assertGreaterEqual(DATA.count('"veg"'), 6)
        self.assertIn("Tofu Fresh Rolls", DATA)
        self.assertIn("Tofu Pad Thai", DATA)

    def test_no_transactional_checkout(self):
        blob = PAGES.lower()
        for banned in (
            "stripe",
            "checkout",
            "add to cart",
            "order online",
            "clover.com",
            "doordash",
            "ubereats",
            "skipthedishes",
        ):
            self.assertNotIn(banned, blob, banned)

    def test_no_published_prices(self):
        self.assertIsNone(re.search(r"\$\d", PAGES))
        self.assertIsNone(re.search(r"\$\d", DATA))

    def test_call_and_directions_actions(self):
        self.assertIn("tel:+19056338388", MENU)
        self.assertIn("maps.google.com", INDEX)
        self.assertIn("Get directions", INDEX)

    def test_pdf_still_available_from_menu(self):
        self.assertIn("dear-saigon-menu.pdf", MENU)

    def test_mapped_photos_only_reference_local_assets(self):
        for match in re.findall(r'photo:\s*"([^"]+)"', DATA):
            self.assertTrue(match.startswith("assets/"))
            self.assertTrue((ROOT / match).exists(), match)

    def test_skip_link_and_focus_styles(self):
        self.assertIn('class="skip"', INDEX)
        css = (ROOT / "css" / "site.css").read_text(encoding="utf-8")
        self.assertIn(":focus-visible", css)
        self.assertIn("prefers-reduced-motion", css)

    def test_menu_item_codes_are_unique_and_tags_are_scoped(self):
        codes = re.findall(r'code:\s*"([^"]+)"', DATA)
        self.assertGreaterEqual(len(codes), 40)
        duplicates = [code for code in codes if codes.count(code) > 1]
        self.assertEqual(duplicates, [], f"duplicate menu codes: {duplicates}")
        for raw in re.findall(r"tags:\s*\[([^\]]*)\]", DATA):
            tags = [part.strip().strip('\"') for part in raw.split(",") if part.strip()]
            for tag in tags:
                self.assertIn(tag, {"veg", "spicy"}, tag)

    def test_menu_renderer_escapes_dynamic_html(self):
        self.assertIn("function esc(s)", MENU_JS)
        self.assertIn('"&": "&amp;"', MENU_JS)
        self.assertIn('"<": "&lt;"', MENU_JS)
        self.assertIn('">": "&gt;"', MENU_JS)
        self.assertIn("'\"': \"&quot;\"", MENU_JS)
        self.assertIn("\"'\": \"&#39;\"", MENU_JS)
        for field in (
            "esc(item.photo)",
            "esc(item.name)",
            "esc(item.code)",
            "esc(item.note)",
            "esc(cat.id)",
            "esc(cat.label)",
        ):
            self.assertIn(field, MENU_JS, field)
        self.assertIn("root.innerHTML = html", MENU_JS)
        self.assertNotIn("eval(", MENU_JS)
        self.assertNotIn("fetch(", MENU_JS)
        self.assertNotIn("XMLHttpRequest", MENU_JS)
        self.assertNotIn("document.write", MENU_JS)

    def test_menu_external_destinations_are_allowlisted(self):
        hrefs = re.findall(r'<a\b[^>]*href="([^"]+)"', MENU)
        allowed = (
            "index.html",
            "menu.html",
            "dear-saigon-menu.pdf",
            "tel:+19056338388",
            "https://www.google.com/maps/dir/?api=1&destination=Dear+Saigon+",
        )
        self.assertGreaterEqual(len(hrefs), 6)
        for href in hrefs:
            if href.startswith("#"):
                self.assertEqual(href, "#main", href)
                continue
            self.assertTrue(
                href.startswith(allowed),
                f"unapproved menu destination: {href!r}",
            )

    def test_menu_scripts_are_local_only(self):
        self.assertEqual(
            re.findall(r'<script[^>]+src="([^"]+)"', MENU),
            ["js/menu-data.js", "js/menu.js", "js/site.js"],
        )
        self.assertNotIn("<form", MENU.lower())
        self.assertIn("This page does not take payments", MENU)

    def test_unpublished_promo_assets_are_not_linked(self):
        phone = (ROOT / "phone-ai.html").read_text(encoding="utf-8")
        public = INDEX + "\n" + MENU + "\n" + phone
        for banned in ("ig/", "loyalty.png", "launch-promo.png"):
            self.assertNotIn(banned, public, banned)

    def test_menu_category_chips_match_data(self):
        chips = re.findall(r'data-cat="([^"]+)"', MENU)
        categories = re.findall(r'^\s*id:\s*"([^"]+)"', DATA, re.M)
        self.assertEqual(chips[0], "all")
        self.assertEqual(chips[1:], categories)
        self.assertGreaterEqual(len(categories), 8)

    def test_menu_data_has_no_checkout_fields(self):
        self.assertNotIn("price:", DATA)
        self.assertNotIn("href:", DATA)
        self.assertNotIn("http://", DATA)
        self.assertNotIn("https://", DATA)
        for banned in ("stripe", "clover.com", "checkout", "doordash"):
            self.assertNotIn(banned, DATA.lower(), banned)


if __name__ == "__main__":
    unittest.main()
