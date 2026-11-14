# Dear Saigon safe takeout foundation

Status: `PULL REQUEST REVIEW / NOT PUBLISHED`

This file describes GitHub pull request #1 on branch `codex/takeout-safe-foundation-20260829`. The branch is review-only. No preview or production deployment has been authorized from it.

This branch intentionally fails closed while Clover-native Online Ordering is unavailable in the current merchant dashboard. It now also includes the visit-only native menu site from `main`.

## What this local preview fixes

- Removes every online-order button that currently routes to Google Maps.
- Keeps checkout, payment, price, and third-party order destinations off the public pages.
- Uses the currently recorded regular hours, Burlington public address including Unit 3, and ordinary customer voice line. Owner re-verification remains a release gate.
- Shows regular weekly hours without calculating an unsafe live open/closed claim on the homepage; holiday and temporary exceptions remain outside the homepage's knowledge.
- Publishes the native Burlington menu names without prices. Staff confirm availability.
- States plainly that direct online ordering is not enabled on the page.

## What remains blocked

- Clover-native Online Ordering eligibility or provisioning.
- Current Clover menu identity, prices, taxes, modifiers, availability, and pickup rules.
- Payment, receipt, printer or kitchen-routing test.
- Exact photo reuse and website publication approval.
- A public Clover storefront URL.
- Release owner approval, deployment evidence, rollback evidence, and live verification.

## Activation rule

Do not add or publish an online-order link until an owner-approved Clover storefront has passed private phone and desktop review plus the separately authorized end-to-end order, payment, and printer test.

Pull-request review fixes may be committed to the review branch. Merge, deployment, public edit, account change, order, payment, and customer-data access remain outside this review-readiness pass.
