from html.parser import HTMLParser
from pathlib import Path
import re
import unittest
import json


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "index.html").read_text(encoding="utf-8")
CSS = (ROOT / "css" / "site.css").read_text(encoding="utf-8")
WATCHDOG = (ROOT / ".github" / "workflows" / "watchdog.yml").read_text(encoding="utf-8")
VERCEL = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.anchors = []
        self._href = None
        self._class = ""
        self._text = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            attrs_d = dict(attrs)
            self._href = attrs_d.get("href", "")
            self._class = attrs_d.get("class", "")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            label = " ".join(" ".join(self._text).split())
            self.links.append((label, self._href))
            self.anchors.append(
                {"label": label, "href": self._href, "class": self._class}
            )
            self._href = None
            self._class = ""
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
        for claim in unsafe_runtime_claims:
            self.assertNotIn(claim, HTML)
        self.assertIn("Regular schedule · holiday hours may differ", HTML)

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

    def test_homepage_does_not_mount_live_hours_widgets(self):
        self.assertNotIn("data-hours-pill", HTML)
        self.assertNotIn("status-text", HTML)
        self.assertIn("status-pill is-schedule", HTML)
        self.assertIn("Regular weekly hours are shown below", HTML)

    def test_order_styled_homepage_ctas_are_not_google_destinations(self):
        parser = LinkParser()
        parser.feed(HTML)
        order_buttons = [
            a for a in parser.anchors if "btn-order" in a["class"].split()
        ]
        self.assertGreaterEqual(len(order_buttons), 3)
        allowed = ("tel:+19056338388", "menu.html", "index.html")
        for anchor in order_buttons:
            self.assertTrue(
                anchor["href"].startswith(allowed),
                f"order-styled CTA routes away from visit-only actions: "
                f"{anchor['label']!r} -> {anchor['href']!r}",
            )

    def test_content_security_policy_is_restrictive(self):
        csp = re.search(
            r'<meta http-equiv="Content-Security-Policy" content="([^"]+)"',
            HTML,
        )
        self.assertIsNotNone(csp)
        policy = csp.group(1)
        for directive in (
            "default-src 'self'",
            "script-src 'self'",
            "connect-src 'none'",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'none'",
        ):
            self.assertIn(directive, policy)
        self.assertNotIn("*", policy)
        self.assertIn('name="referrer" content="strict-origin-when-cross-origin"', HTML)
        self.assertNotIn("<form", HTML.lower())
        external_scripts = re.findall(r'<script[^>]+src="([^"]+)"', HTML)
        self.assertEqual(external_scripts, ["js/site.js"])

    def test_json_ld_omits_monday_and_prices(self):
        match = re.search(
            r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>',
            HTML,
            re.DOTALL,
        )
        payload = json.loads(match.group(1))
        days = []
        for spec in payload["openingHoursSpecification"]:
            value = spec["dayOfWeek"]
            days.extend(value if isinstance(value, list) else [value])
        self.assertNotIn("Monday", days)
        self.assertIn("Tuesday", days)
        self.assertIn("Sunday", days)
        self.assertNotIn("priceRange", payload)
        self.assertNotIn("acceptsReservations", payload)

    def test_watchdog_keeps_analytics_and_order_destination_checks(self):
        self.assertIn(
            "posthog|google-analytics|assets.emergent.sh|session.?record",
            WATCHDOG,
        )
        self.assertIn(
            r"stripe|clover\.com|doordash|ubereats|skipthedishes",
            WATCHDOG,
        )
        order_grep = re.search(
            r"grep -Eiq '([^']+)' /tmp/p\.html",
            WATCHDOG,
        )
        self.assertIsNotNone(order_grep)
        self.assertNotIn("order online", order_grep.group(1).lower())

    def test_watchdog_dns_observation_does_not_open_alerts(self):
        self.assertNotIn("add it under repo Settings", WATCHDOG)
        self.assertNotIn("time to set it as the GitHub Pages custom domain", WATCHDOG)
        alert_lines = [
            line for line in WATCHDOG.splitlines() if "alerts=" in line
        ]
        joined = "\n".join(alert_lines)
        self.assertNotIn("$DOMAIN", joined)
        self.assertNotIn("Pages", joined)
        self.assertIn(
            "No action is authorized by this check.",
            WATCHDOG,
        )

    def test_deploy_headers_remain_fail_closed(self):
        header_map = {
            item["key"]: item["value"]
            for item in VERCEL["headers"][0]["headers"]
        }
        self.assertEqual(
            header_map["Access-Control-Allow-Origin"],
            "https://dearsaigon.com",
        )
        self.assertNotEqual(header_map["Access-Control-Allow-Origin"], "*")
        self.assertEqual(header_map["X-Content-Type-Options"], "nosniff")
        self.assertEqual(header_map["X-Frame-Options"], "SAMEORIGIN")
        self.assertEqual(
            header_map["Referrer-Policy"],
            "strict-origin-when-cross-origin",
        )
        self.assertIn("camera=()", header_map["Permissions-Policy"])
        self.assertIn("microphone=()", header_map["Permissions-Policy"])
        self.assertIn("geolocation=()", header_map["Permissions-Policy"])

    def test_concept_phone_page_stays_isolated_and_non_transactional(self):
        phone = (ROOT / "phone-ai.html").read_text(encoding="utf-8")
        menu = (ROOT / "menu.html").read_text(encoding="utf-8")
        self.assertNotIn("phone-ai.html", HTML)
        self.assertNotIn("phone-ai.html", menu)
        self.assertIn('name="robots" content="noindex,nofollow"', phone)
        self.assertIn("Concept preview", phone)
        self.assertIn("not a live product", phone.lower())
        self.assertNotIn("<form", phone.lower())
        self.assertNotIn("data-hours-pill", phone)
        self.assertNotIn("Checking hours", phone)
        self.assertNotIn("Open now", phone)
        blob = phone.lower()
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
        parser = LinkParser()
        parser.feed(phone)
        allowed = (
            "index.html",
            "tel:+19056338388",
            "https://maps.google.com/?q=2405+Fairview+St+Burlington",
        )
        for label, href in parser.links:
            if not href:
                continue
            self.assertTrue(
                href.startswith(allowed),
                f"concept page leaks destination: {label!r} -> {href!r}",
            )
        self.assertEqual(re.findall(r'<script[^>]+src="([^"]+)"', phone), [])

    def test_menu_order_styled_ctas_are_phone_only(self):
        menu = (ROOT / "menu.html").read_text(encoding="utf-8")
        parser = LinkParser()
        parser.feed(menu)
        order_buttons = [
            a for a in parser.anchors if "btn-order" in a["class"].split()
        ]
        self.assertGreaterEqual(len(order_buttons), 2)
        for anchor in order_buttons:
            self.assertTrue(
                anchor["href"].startswith("tel:+19056338388"),
                f"menu order-styled CTA is not the restaurant phone: "
                f"{anchor['label']!r} -> {anchor['href']!r}",
            )

    def test_pr_safety_workflow_runs_the_python_suite(self):
        workflow = (ROOT / ".github" / "workflows" / "pr-safety.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("python3 -m unittest discover -s tests -v", workflow)
        self.assertIn("contents: read", workflow)
        self.assertIn("git diff --check", workflow)
        self.assertNotIn("issues: write", workflow)

    def test_homepage_does_not_load_menu_runtime(self):
        self.assertNotIn("js/menu-data.js", HTML)
        self.assertNotIn("js/menu.js", HTML)
        self.assertEqual(re.findall(r'<script[^>]+src="([^"]+)"', HTML), ["js/site.js"])

    def test_catering_cta_stays_phone_only(self):
        parser = LinkParser()
        parser.feed(HTML)
        catering = [
            a
            for a in parser.anchors
            if "catering" in a["label"].lower() or a["href"].endswith("#catering")
        ]
        self.assertGreaterEqual(len(catering), 1)
        for anchor in catering:
            if anchor["href"].endswith("#catering"):
                continue
            self.assertTrue(
                anchor["href"].startswith("tel:+19056338388"),
                f"catering CTA is not the restaurant phone: "
                f"{anchor['label']!r} -> {anchor['href']!r}",
            )

    def test_reveal_transition_delay_is_capped(self):
        site_js = (ROOT / "js" / "site.js").read_text(encoding="utf-8")
        self.assertIn("Math.min(group, 6)", site_js)
        self.assertIn("prefers-reduced-motion: reduce", site_js)
        self.assertNotIn("Math.min(group, 12)", site_js)

    def test_json_ld_public_contact_matches_visible_facts(self):
        match = re.search(
            r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>',
            HTML,
            re.DOTALL,
        )
        self.assertIsNotNone(match)
        payload = json.loads(match.group(1))
        self.assertEqual(payload["telephone"], "+19056338388")
        self.assertIn("tel:+19056338388", HTML)
        self.assertEqual(
            payload["address"]["streetAddress"],
            "2405 Fairview St, Unit 3",
        )
        self.assertIn("2405 Fairview St, Unit 3", HTML)
        self.assertTrue(str(payload["hasMenu"]).endswith("menu.html"))
        self.assertIn("menu.html", HTML)

    def test_json_ld_hours_match_visible_schedule(self):
        match = re.search(
            r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>',
            HTML,
            re.DOTALL,
        )
        payload = json.loads(match.group(1))
        by_day = {}
        for spec in payload["openingHoursSpecification"]:
            days = spec["dayOfWeek"]
            if isinstance(days, str):
                days = [days]
            for day in days:
                by_day[day] = (spec["opens"], spec["closes"])
        self.assertNotIn("Monday", by_day)
        self.assertEqual(by_day["Tuesday"], ("11:00", "21:00"))
        self.assertEqual(by_day["Wednesday"], ("11:00", "21:00"))
        self.assertEqual(by_day["Thursday"], ("11:00", "21:00"))
        self.assertEqual(by_day["Sunday"], ("11:00", "21:00"))
        self.assertEqual(by_day["Friday"], ("11:00", "22:00"))
        self.assertEqual(by_day["Saturday"], ("11:00", "22:00"))
        self.assertIn("Tue–Thu 11am–9pm", HTML)
        self.assertIn("Fri–Sat 11am–10pm", HTML)
        self.assertIn("Sun 11am–9pm", HTML)

    def test_deploy_config_has_no_order_redirects(self):
        self.assertNotIn("redirects", VERCEL)
        self.assertNotIn("rewrites", VERCEL)
        blob = json.dumps(VERCEL).lower()
        for banned in (
            "stripe",
            "clover",
            "doordash",
            "ubereats",
            "skipthedishes",
            "checkout",
        ):
            self.assertNotIn(banned, blob, banned)

    def test_new_windows_use_noopener(self):
        pages = {
            "index.html": HTML,
            "menu.html": (ROOT / "menu.html").read_text(encoding="utf-8"),
            "phone-ai.html": (ROOT / "phone-ai.html").read_text(encoding="utf-8"),
        }
        found_blank = 0
        for name, html in pages.items():
            self.assertIsNone(
                re.search(r"\son[a-z]+\s*=", html, re.I),
                f"{name} has an inline event handler",
            )
            for tag in re.findall(r"<a\b[^>]*>", html, re.I):
                self.assertNotIn("javascript:", tag.lower())
                if re.search(r'target\s*=\s*["\']_blank["\']', tag, re.I):
                    found_blank += 1
                    rel = re.search(r'rel\s*=\s*["\']([^"\']+)["\']', tag, re.I)
                    self.assertIsNotNone(rel, f"{name} blank target missing rel: {tag}")
                    self.assertIn("noopener", rel.group(1).split(), tag)
        self.assertGreaterEqual(found_blank, 8)

    def test_watchdog_observes_github_pages_landing(self):
        self.assertIn(
            'SITE="https://skywalker8888.github.io/dear-saigon-landing/"',
            WATCHDOG,
        )
        self.assertIsNone(
            re.search(
                r'SITE="https?://[^"]*(stripe|clover|doordash|ubereats|skipthedishes)',
                WATCHDOG,
                re.I,
            )
        )

    def test_runtime_js_has_no_network_or_storage_side_channels(self):
        site_js = (ROOT / "js" / "site.js").read_text(encoding="utf-8")
        menu_js = (ROOT / "js" / "menu.js").read_text(encoding="utf-8")
        self.assertNotIn("innerHTML", site_js)
        for blob in (site_js, menu_js):
            for banned in (
                "fetch(",
                "XMLHttpRequest",
                "WebSocket",
                "navigator.sendBeacon",
                "document.cookie",
                "localStorage",
                "sessionStorage",
                "eval(",
                "new Function",
            ):
                self.assertNotIn(banned, blob, banned)

    def test_responsive_image_candidates_exist(self):
        for source in re.findall(r'\bsrcset="([^"]+)"', HTML):
            for candidate in source.split(","):
                path = candidate.strip().split()[0]
                if path.startswith(("http://", "https://", "data:")):
                    continue
                self.assertTrue((ROOT / path).is_file(), f"missing srcset image: {path}")


if __name__ == "__main__":
    unittest.main()

