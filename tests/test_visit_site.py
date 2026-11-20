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

    def test_menu_skip_link_targets_main(self):
        self.assertIn('class="skip"', MENU)
        self.assertIn('href="#main"', MENU)
        self.assertIn('id="main"', MENU)

    def test_menu_allergen_disclaimer_is_present(self):
        self.assertIn("Ask staff about allergens", MENU)
        self.assertIn("not a full ingredient list", MENU)
        self.assertIn("staff confirm availability", MENU)

    def test_menu_search_uses_code_name_and_note(self):
        self.assertIn(
            'item.code + " " + item.name + " " + (item.note || "")',
            MENU_JS,
        )
        self.assertIn("hay.indexOf(state.q) !== -1", MENU_JS)
        self.assertIn('state.q = search.value.trim().toLowerCase()', MENU_JS)

    def test_menu_hash_only_selects_known_category_ids(self):
        self.assertIn(
            "cats.some(function (c) { return c.id === hash; })",
            MENU_JS,
        )
        self.assertIn("state.cat = hash", MENU_JS)

    def test_menu_empty_state_is_non_transactional(self):
        self.assertIn("No dishes match that search", MENU_JS)
        self.assertIn("call us and we will help you choose", MENU_JS)
        blob = MENU_JS.lower()
        for banned in ("stripe", "checkout", "add to cart", "order online"):
            self.assertNotIn(banned, blob, banned)

    def test_menu_renderer_does_not_read_price_or_href_fields(self):
        self.assertNotIn("item.price", MENU_JS)
        self.assertNotIn("item.href", MENU_JS)
        self.assertNotIn("cat.href", MENU_JS)
        self.assertNotIn("window.location.assign", MENU_JS)
        self.assertNotIn("window.open", MENU_JS)

    def test_menu_items_are_well_formed(self):
        items = re.findall(
            r'\{ code:\s*"([^"]+)",\s*name:\s*"([^"]+)"',
            DATA,
        )
        self.assertGreaterEqual(len(items), 40)
        self.assertEqual(len({code for code, _ in items}), len(items))
        for code, name in items:
            self.assertTrue(code, "empty menu code")
            self.assertTrue(name, "empty menu name")
            self.assertIsNone(re.search(r"\$\d", name), name)

    def test_menu_items_all_have_scoped_tags_arrays(self):
        codes = re.findall(r'code:\s*"([^"]+)"', DATA)
        tags_arrays = re.findall(r"tags:\s*\[", DATA)
        self.assertEqual(len(codes), len(tags_arrays))
        self.assertGreaterEqual(len(codes), 40)

    def test_menu_veg_filter_uses_veg_tag(self):
        self.assertIn(
            'if (state.veg && item.tags.indexOf("veg") === -1) return false;',
            MENU_JS,
        )
        self.assertIn("state.veg = !state.veg", MENU_JS)
        self.assertIn(
            'veg.setAttribute("aria-pressed", state.veg ? "true" : "false")',
            MENU_JS,
        )
        self.assertIn('e.target.closest("[data-cat]")', MENU_JS)
        self.assertIn('state.cat = btn.getAttribute("data-cat")', MENU_JS)
        self.assertIn("if (!root || !window.DEAR_SAIGON_MENU) return;", MENU_JS)

    def test_menu_category_ids_are_safe_and_unique(self):
        categories = re.findall(r'^\s*id:\s*"([^"]+)"', DATA, re.M)
        self.assertGreaterEqual(len(categories), 8)
        self.assertEqual(len(categories), len(set(categories)))
        for cat_id in categories:
            self.assertRegex(cat_id, r"^[a-z]+$", cat_id)

    def test_menu_item_codes_are_html_id_safe(self):
        codes = re.findall(r'code:\s*"([^"]+)"', DATA)
        self.assertIn("item.code.toLowerCase()", MENU_JS)
        for code in codes:
            self.assertRegex(code, r"^[A-Z][A-Z0-9]*\d+$", code)

    def test_printable_menu_pdf_exists(self):
        self.assertTrue((ROOT / "dear-saigon-menu.pdf").is_file())
        self.assertIn('href="dear-saigon-menu.pdf"', MENU)
        self.assertIsNone(
            re.search(
                r"""href=["']https?://[^"']*dear-saigon-menu\.pdf""",
                MENU,
            )
        )

    def test_menu_photos_are_same_origin_webp(self):
        photos = re.findall(r'photo:\s*"([^"]+)"', DATA)
        self.assertGreaterEqual(len(photos), 10)
        for path in photos:
            self.assertRegex(path, r"^assets/[a-z0-9./-]+\.webp$", path)
            self.assertNotIn("..", path)
            self.assertTrue((ROOT / path).is_file(), path)

    def test_menu_hash_is_not_interpolated_into_html(self):
        self.assertNotIn("+ hash", MENU_JS)
        self.assertNotIn("hash +", MENU_JS)
        self.assertNotIn("${hash}", MENU_JS)
        self.assertNotIn("esc(hash)", MENU_JS)
        self.assertIn("state.cat = hash", MENU_JS)
        self.assertIn("c.id === hash", MENU_JS)

    def test_menu_controls_are_non_submitting_buttons(self):
        self.assertIn('<button class="nav-toggle" type="button"', MENU)
        self.assertIn('<button type="button" class="chip" id="vegFilter"', MENU)
        self.assertIn('id="menuSearch" class="menu-search" type="search"', MENU)
        self.assertNotIn("formaction", MENU.lower())
        self.assertNotIn('type="submit"', MENU.lower())
        chip_buttons = re.findall(r"<button\b[^>]*data-cat=", MENU)
        self.assertGreaterEqual(len(chip_buttons), 9)
        for tag in chip_buttons:
            self.assertIn('type="button"', tag)

    def test_watchdog_domain_is_not_an_order_destination(self):
        watchdog = (ROOT / ".github" / "workflows" / "watchdog.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn('DOMAIN="dearsaigonburlington.com"', watchdog)
        self.assertIsNone(
            re.search(
                r'DOMAIN="[^"]*(stripe|clover|doordash|ubereats|skipthedishes)',
                watchdog,
                re.I,
            )
        )

    def test_menu_tag_labels_are_hardcoded_not_interpolated(self):
        self.assertIn(
            '<span class="tag tag-veg">Vegetarian</span>',
            MENU_JS,
        )
        self.assertIn(
            '<span class="tag tag-spicy">Spicy</span>',
            MENU_JS,
        )
        self.assertNotIn("esc(item.tags", MENU_JS)
        self.assertNotIn("item.tags.join", MENU_JS)
        self.assertNotIn("item.tags.map", MENU_JS)
        self.assertIn('item.tags.indexOf("veg")', MENU_JS)
        self.assertIn('item.tags.indexOf("spicy")', MENU_JS)

    def test_menu_text_fields_have_no_urls_or_prices(self):
        notes = re.findall(r'note:\s*"([^"]*)"', DATA)
        names = re.findall(r'name:\s*"([^"]*)"', DATA)
        self.assertGreaterEqual(len(notes), 20)
        self.assertGreaterEqual(len(names), 40)
        for text in notes + names:
            self.assertIsNone(re.search(r"\$\s*\d", text), text)
            lower = text.lower()
            self.assertNotIn("http://", lower, text)
            self.assertNotIn("https://", lower, text)
            self.assertNotIn("tel:", lower, text)

    def test_menu_app_starts_empty(self):
        match = re.search(r'<div id="menuApp">(.*?)</div>', MENU, re.DOTALL)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1).strip(), "")

    def test_homepage_nav_toggle_is_a_non_submitting_button(self):
        self.assertIn(
            '<button class="nav-toggle" type="button" aria-expanded="false"',
            INDEX,
        )
        self.assertNotIn('type="submit"', INDEX.lower())
        self.assertNotIn("formaction", INDEX.lower())
        self.assertNotIn("<form", INDEX.lower())


if __name__ == "__main__":
    unittest.main()
