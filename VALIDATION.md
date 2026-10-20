# Pantry Portal — implementation and validation

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
