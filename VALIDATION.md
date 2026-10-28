# Pantry Portal — implementation and validation

## 0.12.1 Doctor office maps (October 23, 2026)

Added lazy-loaded OpenStreetMap previews to saved doctor cards. A thumbnail click and full-map link open Google Maps; a directions link pre-fills the office destination. The free U.S. Census geocoder receives only the owner's saved office address. Unmatched or ambiguous locations and provider failures retain the full-map/directions links without inventing a pin. No paid credentials or schema migration is required.

Three new integration tests cover owner/admin isolation, CSRF, minimal outbound payloads, address edits, bounded in-memory reuse, missing/ambiguous/invalid locations, provider failures and absence of address/record ID/notes in audit logs. Preview rendering is checked with a synthetic account and a public example address; no real medical records are created or changed for testing.

All 53 Python and six JavaScript tests passed. Browser checks verified map tiles and attribution, a 390px layout without horizontal overflow, and a thumbnail opening the correct address in a separate Google Maps tab with its Directions interface available.

## 0.12.0 Doctor and drug references (October 21, 2026)

Integrated the merged GitHub doctor/medication search feature and reviewed it locally. Doctor searches use NIH/CMS public contact data; optional Google Places requires an operator-configured key, while Google Maps and Bing links remain available without it. Improved title normalization and name-match ordering. Medication names and strengths come from NIH RxTerms. Product-label choices use openFDA, prefer newer label dates, and expose source-linked uses, warnings, side effects and other returned sections without modifying prescribed directions. DailyMed remains available during reference-provider failures.

All 50 Python tests and six JavaScript tests passed. Public live reference checks returned provider contacts, medication forms and product-label sections. Isolated browser checks verified suggestions, keyboard selection, doctor autofill, medication/strength selection, and label choice/readability. No real user's medical records were created or changed during testing. Search text is sent only to the documented reference providers, separate from private cabinet saves, and excluded from application audit/cache records.

## 0.11.0 Medicine area (October 21, 2026)

Added per-account cabinets, owner-scoped prescriptions/refill information, prescriber contacts and time-zone-aware appointments. Household pharmacy reads the existing non-food Medicines and first aid inventory records without duplicating quantities. Records can be archived/restored; stale edits receive conflict errors. Personal medicine records have no application-administrator override. Medicine audit entries contain generic outcomes, not clinical fields or record IDs.

All 41 Python tests and six JavaScript tests passed. Six new integration tests exercise same-household administrator isolation, doctor ownership, prescriptions, appointment time zones and invalid dates, cabinet naming, shared stock identity/updates, disabled-user filtering, edit conflicts, CSRF, unauthenticated access and log privacy. Desktop/mobile browser checks used only synthetic data in an isolated database. See docs/MEDICINE.md for workflow and operational privacy boundaries.

## 0.10.1 navigation update (October 20, 2026)

Renamed Overview to Home and grouped Inventory, Recipes and Locations under Organize. Account contains personal/household links and permission-controlled Administration. Explicit hidden-control styling fixes component display rules overriding hidden attributes. Backend administrative authorization remains enforced.

All 35 Python and six JavaScript tests passed. Browser checks used an isolated temporary database: guests see sign-in only under Account; ordinary users (including household owners) do not see Administration; administrators can open the admin center. Inventory navigation closes the menu, and Home inventory mode hides Recipes. Native disclosure menus provide keyboard and touch controls with Escape dismissal.

Date: October 16, 2026. Scope: continued implementation in the existing Pantriportal project, followed by authorized production deployment.

## Implemented

- Barcode camera scanning, barcode-photo decoding and typed lookup, with product choices, catalog photos and a quantity confirmation form.
- Private browser photo recognition using a quantized CLIP model and package-text OCR. Low-confidence OCR results are discarded. Suggestions lead to catalog searches; users confirm the match.
- Catalog photos, uploaded photos, and free locally generated SD-Turbo illustrations. Missing-image saves look for catalog photos first. Users can reject unsuitable photos and continue with generation. Images are labeled as temporary illustrations and can be replaced later.
- Atomic quantity merging, with separate entries for different storage locations, units and unbarcoded package sizes. Repeat imports are idempotent and preserve totals.
- User registration/sign-in/sign-out, separate saved inventories, salted password hashing, protected sessions, CSRF/origin checks and private media access.
- One-time administrator bootstrap, additional administrator role management, and protection against removing the last administrator.
- Administrator image audits, exact-barcode repairs, review of ambiguous matches, manual photo replacement, optional generated-image fallback, and preservation of concurrent photo changes.

## Automated validation

All **12 isolated integration tests passed**. They cover concurrent quantity updates, unit/package separation, account isolation, private uploads, authentication, invalid input, CSRF and origin rejection, import merging/idempotence, edit conflicts, generation jobs and failures, role management, one-time administrator setup, audits and provider failures, static-file restrictions, and preservation of real product photos when quantities merge. New tests verify exactly three distinct choices, fresh regeneration without cached repeats, private choices, selection during creation and editing, no replacement before selection, and conflict protection when an image changes concurrently.

## Three-image chooser update

The creation/editing form and administrator replacement controls now say **Generate New Image**. They show three distinct AI image choices and a **generate new options** button. Every set uses fresh random seeds and varied viewpoints. Generation and cancellation do not replace an existing image. Normal item editing keeps the selection in the draft until Save item; administrator replacement requires an explicit selection. Automatic missing-image fallback also uses this chooser.

The picker heading is now **Choose an alternative image.**

## Kitchen and Home inventory modes

The switch changes both the inventory scope and the appearance. Kitchen has food, drinks and recipe views with warm green styling. Home inventory has household supplies with blue/lilac styling, a different banner graphic, household storage defaults and a low-stock summary. Mode selection is remembered in the browser. All original records stay in the same database and exports include both modes. Users can reclassify a record with Item belongs to.

Three additional JavaScript tests passed for legacy classification, mode partitioning without record/quantity mutation, and mode-specific storage locations including existing custom locations. These use the bundled Node runtime's test runner.

External image-generation and catalog calls are controlled in those integration tests. Actual model inference and a real catalog lookup were also tested separately. Python compilation and JavaScript syntax checks passed.

## Browser validation

- Created an ordinary local test account and saved inventory; entries survived reload.
- Real barcode `3017620422003` returned Nutella with manufacturer, package size, catalog photo and package details.
- A barcode image fixture decoded to that same barcode and produced the catalog match.
- Adding three more units of the same scanned product merged the existing quantity from two to five, without a second inventory row.
- Package-label OCR recovered `HEINZ TOMATO KETCHUP` from a clear text fixture.
- The final CLIP matcher ranked an apple first for the apple-photo fixture, with alternative suggestions. That score compares candidate labels and is not a verified probability of correctness.
- The real local SD-Turbo generator produced a 512 × 512 image. Generation also worked through the app's background job and form; the saved image retained its AI label after page reload.
- The no-image save path looked for real catalog photos and offered them for review before allowing the user to proceed with an illustration.
- After rejecting unsuitable catalog photos, automatic fallback generated an illustration and saved the previously imageless item successfully.
- The three-choice gallery generated three real local images, then regenerated three fresh URLs. Selecting option 2 during editing saved the selected image and survived reload. Selecting option 3 during creation updated the draft; canceling left inventory unchanged.
- The renamed chooser heading was verified in the browser.
- Kitchen showed three food records and eight units. Home inventory showed only a newly saved Shampoo demo, defaulted to Personal care / Bathroom, with one unit. Switching back preserved the food quantities and hid the household item; the selected mode survived reload. Recipes were visible only in Kitchen.
- Both mode themes and banner graphics were checked at the narrow preview width, with no horizontal page overflow.
- All three inventory images loaded in the browser. The narrow preview showed no horizontal overflow of the page (the navigation has its own horizontal scroll area).

The preview contains local QA inventory only. Historical and live customer inventories were not changed.

## Handoff

Preview: `http://127.0.0.1:8767/`. Active source: `app/`. Setup, administrator bootstrap, model download and runtime details: `DEVELOPMENT.md`.

The free image generator is installed on this computer, with model files in `work/models/sd-turbo/`. It uses no paid inference API or API key. Model downloads were verified against ModelScope's SHA-256 metadata, and provenance is stored alongside the files. Browser recognition assets are served locally. The source package includes the required browser model but excludes the multi-gigabyte generation cache, credentials, sessions, databases, uploaded/generated media and historical conversations.

## Limits

- No physical phone-camera test was possible in this desktop session. Camera capture still needs a real-device check over HTTPS before public release.
- Recognition and generated illustrations can differ from the real product. Exact brand, package size, ingredients and allergens require user confirmation. Real photos remain preferable.
- Catalog coverage and free-provider availability vary. Provider failures remain retryable and do not erase inventory.
- Password recovery and separate household invitations are not included.
- Production was updated with preserved database/media, TLS, browser migration and a private recovery backup. Physical phone-camera checks remain outstanding.


## Production verification — October 16, 2026

- Deployed release `/opt/pantry-portal/releases/20261016T193808Z-0.5` to https://www.pantriportal.com/; public health reports version 0.5.0 over normally validated HTTPS.
- All 12 integration tests passed against the staged Linux runtime. Six JavaScript tests passed locally: the three mode tests and three additional migration/bootstrap ordering and failure tests. Total: 18 automated checks.
- Actual CPU generation on the host produced three distinct private images; choosing one succeeded. The cold-start set took 152 seconds. Test data stayed in a separate staging directory. Generated samples were visually checked.
- Saved-record hashes matched before and after activation: 6 users, 6 sessions, 18 items and 3 media records. Private data and configuration backups remain on the server, outside the public website.
- The public browser retained all 13 locally saved items totaling 35 units: Kitchen showed 12 records / 33 units; Home inventory showed Dish soap / 2 units. Mode selection survived reload, and old-IP navigation returned to the canonical site without duplicating these records.
- The public chooser DOM contains Choose an alternative image. and Generate New Image. The three-choice creation/editing workflow was previously checked locally; real generation/selection was additionally tested through the staged server API.
- Public application scripts, migration script and required CLIP model returned 200. Unauthenticated inventory GET returned 401; server source returned 404. Nginx, the application and the browser-transfer service are active. Production development mode is disabled.
- Source files were verified with SHA-256 on the server. Model files were checked against the public mirror's SHA-256 metadata. No credentials, private databases, sessions or uploaded/generated production media are included in the source deliverable.

Recovery and runtime details: DEVELOPMENT.md, Production deployment section. Both existing administrator accounts were preserved; deployment did not create or disclose an administrator credential.


## Production responsive UI update — October 17, 2026

- Activated `/opt/pantry-portal/releases/20261017T054249Z-0.5-ui` on https://www.pantriportal.com/. It is based on the October 16 release and updates only static UI assets and markup plus explicit Nginx allowlist routes. The application service was not restarted and household data was not changed.
- Verified the live page at 360, 390, 768, 1024 and 1140 CSS-pixel viewport widths. The document had no horizontal overflow at any width; the logo and hero artwork loaded at each width. The centered main shell reached 1125 CSS pixels at a 1140px viewport (the remaining width is the browser scrollbar).
- Live API health returned `ok`, all three new public assets returned HTTP 200, and `/server.py` remained unavailable (404).
- The previous release and Nginx configuration were preserved in `/var/backups/pantry-portal/ui-responsive-20261017T054249Z/`, with a rollback script. No automated test suite was rerun for this static UI-only deployment.

## Production administration update — October 20, 2026

Version 0.9.0 is live at https://www.pantriportal.com/, release `/opt/pantry-portal/releases/20261019T230144Z-0.9-admin`. Twenty-two Python tests passed both locally and on the host with isolated fixtures; six JavaScript tests passed. Release checksums matched. All pre-existing table hashes matched across activation (7 users, 8 sessions, 20 items, 6 media records). Application, transfer and Nginx services are active. HTTPS health and new assets passed. Anonymous admin and Word guide requests returned 401, and private source/catalog URLs returned 404. Host diagnostics passed database integrity, disk, assets, private permissions, image model dependencies and audit signatures. The public authenticated Home dashboard displayed all six default sections. Full production administrator browser coverage remains unverified; those workflows passed isolated browser checks and automated tests. The 133-reference Word guide rendered to 20 pages and was visually reviewed. See ADMINISTRATION.md for scope, permissions and limitations.

## Protected main administrator — October 20, 2026

Published version 0.9.1 at https://www.pantriportal.com/, active release `/opt/pantry-portal/releases/20261020T134250Z-0.9.1-primary-admin`. The existing dcolanduno account was changed from user to administrator and pinned by account ID. Full application permissions cannot be removed by overrides; application guards and database triggers protect deletion, disabling, renaming, demotion and loss of approval. The main account name cannot be registered again. Passwords and sessions were retained. A private pre-change archive and record snapshot are at `/var/backups/pantry-portal/primary-admin-20261020T134250Z`.

23 Python tests passed locally and on the host, including deletion/demotion/disable/permission-denial and reserved-name checks; six JavaScript tests and admin.js syntax checks passed. The deployment compared all prior non-audit records, allowing only the specified owner role/access changes, removal of that owner's permission overrides and the new identity configuration. Audit integrity and service health passed. The live authenticated browser showed dcolanduno as Full administrator with 14 permissions and opened Users and permissions, where the Main administrator label and protected editor were verified. No credentials were created or disclosed.

## Kitchen companion — October 20, 2026

Published 0.10.0 from `/opt/pantry-portal/releases/20261020T174250Z-0.10-kitchen`. 35 Python tests passed locally and in isolated production-host fixtures; six JavaScript tests passed. Checksums matched, every pre-existing table digest matched across migration, and dcolanduno retained protected full administration. Public health and all three services are healthy. kitchen.js/kitchen.css return 200, anonymous plans/lists return 401, and kitchen_ops.py/builtin-recipes.json return 404. The authenticated live browser loaded Plan & shop and the six suggested recipe choices. No QA data was imported.

Isolated browser checks covered recipe creation, linked pantry ingredients, required amounts, ordered instructions, a saved meal plan, grocery generation, basket review, blocked checkout without affirmation and successful purchase confirmation. Public search returned actual TheMealDB records. A synthetic EAN-13 image decoded to the expected barcode. The 390px shopping layout showed no horizontal overflow. Step-photo ownership/edit retention, separate meal batches, generic-to-exact purchased-product linking, quantity conversions and concurrent checkout retries passed backend tests. Physical phone camera and real-store scanning remain unverified. See KITCHEN_COMPANION.md for usage and limitations.

The final active symlink is `/opt/pantry-portal/releases/20261020T174843Z-0.10-kitchen-nav`, a static follow-up that wraps the expanded desktop menu. The application code and version remain 0.10.0; the preceding release is preserved. The new stylesheet hash was verified against HTTPS delivery.

## Medicine reference search — October 21, 2026 (historical upstream source checks)

Implemented doctor/medication search while typing, explicit doctor contact selection, RxTerms strength/form suggestions and per-prescription FDA product-label readers. Health version is 0.12.0. Forty-nine Python tests and six JavaScript tests passed, with JavaScript syntax and whitespace checks. Synthetic DOM checks covered stale-response suppression, arrow/Enter selection, doctor contact replacement, medication identity reset when name/strength changes, escaping provider label text and clearing reference content on account change. Live NIH queries returned medication names/paired strengths and provider addresses/phones. A live FDA Lipitor lookup returned one matching candidate and 33 full text sections, including adverse reactions.

No production data was accessed or changed for those upstream tests. That session could not reach the deployment server by SSH, so it did not verify production activation, release hashes, services, backups or live feature behavior. A GitHub source push does not deploy this application. The optional Google Places adapter was tested with synthetic responses; a production Places credential/billing configuration was not provisioned or verified. Bing support is a manual search link. Reference requests are independent of cabinet saves and exclude account identity, notes, directions, prescription numbers and other private record fields.


## Prescription label scanning — October 23, 2026

Version 0.13.0 adds native phone-camera/file selection, local barcode decoding and English OCR, manual correction and two explicit review/save steps. Synthetic browser fixtures verified actual OCR of a full label, preservation of leading Rx-number zeros, separate bottle discard dates, quantities/refills/contacts, successful owner-only save, and a valid refill telephone link without placing a call. A synthetic Code 128 image decoded to its expected prescription number; it was not automatically interpreted as a drug identifier. Cancelling/reopening cleared the photo, raw text and draft fields. Low-confidence barcode-only OCR left the clinical fields blank. No real medical labels or production medical test records were used.

The automated suite covers parsing ambiguity, impossible/two-digit dates, no-refill values, phone-link safety, exact public NDC matches and billing-code ambiguity, authentication/CSRF, private fields, owner isolation, audit redaction, plus existing inventory/admin/recipe/medicine behavior. Physical iOS/Android camera use and real curved pill-bottle labels still require device testing. Source publication and live release verification are recorded separately; this entry alone is not proof of deployment.


## Medical profile and prescription comparisons — October 24, 2026

Version 0.14.0: 61 Python and 12 JavaScript tests passed. Isolated browser testing verified actual synthetic-photo OCR from Add prescription, preservation of existing typed notes, the final save requirement, private program creation/masked card display and ZIP persistence, eight live NIH pharmacy-directory results, separate cash/GoodRx quote columns, zero-price quote handling, and exclusion of quotes when fill quantity changes. The 390px comparison dialog has no horizontal overflow; the wide comparison table scrolls inside its own region. No real medical/insurance test data or actual pharmacy quotes were created in production. Physical phone camera testing remains unverified.

GoodRx signing, NDC11 conversion, zero and membership-fee handling, fixed-domain coupon links, no private identifiers in requests, default-disabled behavior and rejection of mismatched fill responses passed synthetic provider tests. Official GoodRx/CVS/SingleCare/AARP API and partnership options are documented in docs/PHARMACY_PRICING.md. No usable production pricing credential was present, so authenticated upstream prices were not live-tested or claimed active. Provider approval/private setup remain required. Source and live activation checks are separate from this validation entry.


## Browse-first drug prices — October 25, 2026

Version 0.14.1 removes fill-field requirements from browsing. Sixty-five Python tests and twelve JavaScript tests passed. Isolated browser fixtures showed both 10 mg and 20 mg quotes, including cash, coupon and zero-price values, immediately after opening the screen with the exact-fill panel closed and no visible required fill inputs. Drug dose options are source-labeled and ZIP-only pharmacy searches do not require dosage, quantity, unit or days supply. Backend tests cover name-only consent/authentication, exact catalog name matching, multiple provider strengths and standard-fill metadata, missing credentials and preservation of zero prices. Provider responses remain synthetic until partner access is configured. Historical prices are labeled by strength and fill size; the optional exact-fill comparison remains distinct.


The official Cost Plus Drugs public catalog was reachable from both development and production hosts and returned six Lisinopril strengths. Browser testing displayed the supplied cash/sample-fill and total-with-shipping prices automatically, without any fill fields entered. The current public API is used instead of its deprecated predecessor; the full public catalog is downloaded without patient drug queries and cached in memory. Tests cover cache reuse, fixed outbound URL, source-domain filtering, zero prices, branded-generic labeling, private-route authentication/CSRF and outage fallback. These mail-order cash examples are distinct from local pharmacy and insurance prices.
## Automatic nearby prices — October 26, 2026

Version 0.14.2 replaces the pharmacy-directory/call-for-prices flow with automatic LowerScript public MCP price lookup. Local fixture browser testing fetched real Lisinopril prices for five pharmacies in ZIP 30076 with strength 10 mg and supplier fill 30 units/30 days; no quantity or days entry was required. Saved ZIP starts the request automatically. The UI labels the discount card, addresses, distance, fill basis, timestamp and source, with mail-order cash prices separate. No production prescription or quote records were created for this check.

69 Python tests and 12 JavaScript tests passed, plus JS syntax and whitespace checks. New tests cover private-route auth/CSRF, stripping unrelated private payload fields, zero prices, rejection of mismatched drug/ZIP/strength and invalid fill metadata, safe links and global public-provider rate limits. Coverage/outages/allowance limits can produce no local prices; the UI reports that without requiring phone calls or manually sourced quotes. Provider coverage and public usage limits are documented in PHARMACY_PRICING.md. Source publication and live deployment verification are separate checks.


## Twenty-mile price scope — October 26, 2026

Version 0.14.3 explicitly filters local prices to provider-reported ZIP-search distances of 20 miles or less, with counts for farther and unknown-distance results. The interface states that the supplier returns at most ten locations and coverage is incomplete. Tests exercise the exact boundary, farther distances, missing/nonfinite/negative distances, zero prices and preservation of Publix rows. The provider's documented tool schema was inspected: no radius, pagination or larger result-limit argument is available. This change does not claim prices for every pharmacy.

## Curved-label scanner — October 26, 2026

Version 0.15.0 adds live rear-camera capture with supported continuous autofocus, local crop/rotation controls, retained image detail, contrast enhancement, several segmentation passes, an optional cylindrical correction pass and multi-view field reconciliation. Per-line confidence replaces the old whole-image gate; conflicting readings are flagged and subsequent views preserve reviewed form values. Images and label text remain on the device, with existing review-before-save gating.

Synthetic full-label browser OCR extracted name, strength, directions, quantity, unit, refills, printed dates, pharmacy/address/phone, prescriber, Rx number and NDC. An angled front panel filled medicine/directions/quantity. Multi-view and cancellation checks are recorded separately in the private release verification. 70 Python tests passed; JavaScript tests include new low-confidence-line, multi-view/conflict, zero-refill/leading-zero and unreadable-text cases. Physical phone autofocus and actual bottle accuracy remain unverified. See docs/PRESCRIPTION_SCANNING.md.

## FineRx nearby-price adapter — October 26, 2026

Version 0.15.1 adds a server-only adapter for FineRx's documented radius-based nearby-price endpoint. It requests a 20-mile ZIP radius, validates the returned drug and requested strength, filters distances, keeps observed dates and attribution, and labels chain prices as estimates that may differ by branch. Existing LowerScript pricing remains the fallback. Four synthetic contract tests cover minimal payload/private-key handling, returned Publix/CVS branches and distance filtering, mismatch rejection, and the disabled-without-key state. 74 Python tests and 16 JavaScript tests passed; syntax, compile and whitespace checks passed. The API schema and terms were inspected, but no live FineRx key or price request was used. FineRx requires a developer key issued on request; comprehensive chain/branch coverage remains provider-dependent. See [PHARMACY_PRICING.md](docs/PHARMACY_PRICING.md).

Version 0.15.2 opens the rear camera immediately and continuously OCRs local video frames while the user holds and turns the bottle. A local browser harness with a generated video stream and synthetic OCR output verified automatic multi-view reading, unchanged-frame deduplication, and camera stop with recognized text preserved. The Tesseract worker stays warm across frames; thresholded contrast supplements the existing layout and curved-label passes. Lines must repeat across OCR passes or score highly before acceptance, and unchanged frames do not inflate the view count. Added views only fill blank medicine fields. Images and OCR text remain on the device. 74 Python tests and 18 JavaScript tests passed; a physical phone test remains necessary to measure autofocus and accuracy on real curved bottles.

## Prescription label OCR recovery — October 27, 2026

Version 0.15.3 enlarges a centered label region and runs whole-frame plus magnified OCR layouts for photos and live frames. The scanner retains more lower-confidence words for agreement across passes and exposes a strongest readable one-pass candidate for correction, instead of silently requiring exact repeated text. New tests cover lower-confidence word recovery and fallback review. Chrome ran the exact bundled Tesseract.js 5.1.1 asset against a generated, high-resolution label and recovered all printed test fields at 93% overall confidence. 74 Python tests and 20 JavaScript tests passed; Python compilation and diff checks passed. This synthetic crisp-label check does not prove performance on a real curved, reflective bottle or the user's phone camera; that remains unverified.

Version 0.15.4 adds a shared footer that fetches the active server's version and short commit identifier without browser caching. The public health response derives the identifier from the release's `release-source.json`, while a local checkout without release metadata reports `local`. Tests verify the footer behavior and health response; live release hash and label verification are required after deployment.

Version 0.15.5 replaces repeated automatic OCR with guided still capture: use the browser's full-resolution still capture when available, otherwise select the sharpest of three nearby video frames. A focused synthetic-browser harness verifies OCR does not run before a user capture, each quick panel capture uses exactly one OCR pass, distinct panel text is retained, and the camera stops cleanly. The detailed multi-pass scan is opt-in; auto-filled fields require at least 75% average Tesseract confidence, while lower-confidence text remains editable. Existing 75 Python tests and 21 JavaScript tests pass. These checks validate interaction and guardrails, not real medicine-label accuracy; physical-phone testing remains necessary.

Version 0.15.6 changes prescription capture to continuous local barcode decoding when the rear camera opens. GS1 identifiers are parsed with check-digit and date validation; exact GTIN/NDC lookup is limited to product codes, while lot, serial and expiry remain local until the user reviews and saves. Barcode values never fill the Rx number, and user-specific pharmacy label fields are never inferred. The FDA lookup uses an exact UPC/GTIN match or exact package NDC. Full test suites pass: 76 Python tests and 25 JavaScript tests; live phone hardware and the user's actual bottle remain unverified.
