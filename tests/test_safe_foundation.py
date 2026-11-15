from html.parser import HTMLParser
from pathlib import Path
import re
import unittest
import json


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "index.html").read_text(encoding="utf-8")
CSS = (ROOT / "css" / "site.css").read_text(encoding="utf-8")
WATCHDOG = (ROOT / ".github" / "workflows" / "watchdog.yml").read_text(encoding="utf-8")


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self._href = None
        self._text = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href = dict(attrs).get("href", "")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.links.append((" ".join(" ".join(self._text).split()), self._href))
            self._href = None
            self._text = []


class SafeFoundationTests(unittest.TestCase):
    def test_transactional_language_is_fail_closed(self):
        prohibited = (
            "order online",
            "order direct",
            "ready in ~20 min",
            "no app fees",
            "25–30%",
            "buy 9, get your 10th free",
            "book catering",
            "checkout",
            "pay now",
        )
        lower = HTML.lower()
        for phrase in prohibited:
            self.assertNotIn(phrase.lower(), lower)
        self.assertIn("Online ordering is not enabled on this page.", HTML)

    def test_no_price_is_published(self):
        self.assertIsNone(re.search(r"\$\s*\d", HTML))

    def test_order_like_links_do_not_route_to_google(self):
        parser = LinkParser()
        parser.feed(HTML)
        for label, href in parser.links:
            if any(word in label.lower() for word in ("order", "checkout", "pay")):
                self.fail(f"transactional link remains: {label!r} -> {href!r}")

    def test_external_actions_are_limited_to_known_public_destinations(self):
        parser = LinkParser()
        parser.feed(HTML)
        allowed_external_prefixes = (
            "https://maps.google.com/?cid=7779167624269607469",
            "https://www.google.com/maps/dir/?api=1&destination=Dear+Saigon+",
            "https://instagram.com/dearsaigonburlington",
            "https://facebook.com/dearsaigonburlington",
            "tel:+19056338388",
        )
        for label, href in parser.links:
            if href.startswith(("http://", "https://", "tel:")):
                self.assertTrue(
                    href.startswith(allowed_external_prefixes),
                    f"unapproved external destination remains: {label!r} -> {href!r}",
                )

    def test_recorded_public_facts_are_present(self):
        self.assertIn("2405 Fairview St, Unit 3, Burlington, ON L7R 2E4", HTML)
        self.assertIn("Closed Mon", HTML)
        self.assertIn("Tue–Thu 11am–9pm", HTML)
        self.assertIn("Fri–Sat 11am–10pm", HTML)
        self.assertIn("Sun 11am–9pm", HTML)
        self.assertIn("tel:+19056338388", HTML)
        self.assertIn("menu.html", HTML)

    def test_live_status_does_not_ignore_holiday_or_temporary_exceptions(self):
        unsafe_runtime_claims = (
            "Checking hours",
            "Open now",
            "Closed — opens",
            "always has current hours",
            "<h3>Current hours</h3>",
        )
        menu = (ROOT / "menu.html").read_text(encoding="utf-8")
        site_js = (ROOT / "js" / "site.js").read_text(encoding="utf-8")
        for claim in unsafe_runtime_claims:
            self.assertNotIn(claim, HTML)
            self.assertNotIn(claim, menu)
            self.assertNotIn(claim, site_js)
        self.assertNotIn("data-hours-pill", menu)
        self.assertNotIn("data-hours-pill", site_js)
        self.assertIn("Regular schedule · holiday hours may differ", HTML)
        self.assertIn("Regular schedule · holiday hours may differ", menu)

    def test_takeout_availability_is_not_inferred_from_restaurant_hours(self):
        self.assertNotIn("Takeout follows the regular restaurant hours", HTML)
        self.assertIn("Call the restaurant to confirm current takeout availability", HTML)

    def test_customer_identity_and_internal_boundaries_are_preserved(self):
        self.assertIn("DEAR SAIGON", HTML)
        self.assertNotIn("America/Toronto", HTML)

    def test_structured_data_uses_only_scoped_public_facts(self):
        match = re.search(
            r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>',
            HTML,
            re.DOTALL,
        )
        self.assertIsNotNone(match)
        payload = json.loads(match.group(1))
        self.assertEqual(payload["name"], "Dear Saigon")
        self.assertIn(payload["telephone"], ("+19056338388", "+1-905-633-8388"))
        self.assertIn("2405 Fairview St", payload["address"]["streetAddress"])
        self.assertNotIn("priceRange", payload)

    def test_accessibility_baseline(self):
        self.assertIn('class="skip" href="#main"', HTML)
        self.assertIn('<main id="main" tabindex="-1">', HTML)
        self.assertIn("main, section[id] { scroll-margin-top: 5.5rem; }", CSS)
        self.assertIn('class="info-phone-link" href="tel:+19056338388"', HTML)
        self.assertIn(".info-phone-link { display: inline-flex; align-items: center; min-height: 44px;", CSS)

    def test_referenced_local_images_exist(self):
        for source in re.findall(r'<img[^>]+src="([^"]+)"', HTML):
            if source.startswith(("http://", "https://", "data:")):
                continue
            self.assertTrue((ROOT / source).is_file(), f"missing image: {source}")

    def test_below_fold_menu_images_are_lazy_and_dimensioned(self):
        menu_images = re.findall(
            r'<img[^>]+src="assets/menu/[^"]+"[^>]*>',
            HTML,
        )
        self.assertGreaterEqual(len(menu_images), 2)
        for tag in menu_images:
            self.assertIn('loading="lazy"', tag)
            self.assertIn('width="1200"', tag)
            self.assertIn('height="900"', tag)

    def test_native_menu_names_remain_without_prices(self):
        self.assertIn("Dear Saigon Pho", HTML)
        self.assertIn("Dear Saigon Platter", HTML)
        self.assertIsNone(re.search(r"\$\s*\d", HTML))

    def test_core_content_does_not_fail_hidden(self):
        self.assertIn(".reveal, .reveal.in { opacity: 1; transform: none; }", CSS)
        self.assertIn(".hero-copy > * { opacity: 1; animation: none; }", CSS)
        self.assertIn(".hero-media { opacity: 1; animation: none; }", CSS)

    def test_review_build_is_fail_closed_by_policy(self):
        self.assertIn("connect-src 'none'", HTML)
        self.assertIn("form-action 'none'", HTML)
        self.assertIn("This site does not take payments.", HTML)

    def test_watchdog_does_not_mislabel_google_listing_links_as_orders(self):
        self.assertNotIn("Order buttons still point to the Google listing", WATCHDOG)
        self.assertNotIn("30% apps", WATCHDOG)
        self.assertIn("Visit-only safety wording present", WATCHDOG)
        self.assertIn("This check does not authorize a Pages or DNS change.", WATCHDOG)


if __name__ == "__main__":
    unittest.main()
