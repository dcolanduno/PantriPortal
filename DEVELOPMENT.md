# Pantry Portal 0.5 local development

The active development source is `app/`. The preserved `history/` and original downloads have not been rewritten. The production application and data were preserved during the October 16, 2026 deployment; an October 17 UI-only release added the responsive dashboard presentation and supplied brand artwork.

## Run locally

Run `Start-Pantry-Local.ps1` from PowerShell, then open `http://127.0.0.1:8767/`. The development server listens only on this computer. The existing preview may already be running on that port.

The installed environment is `work/venv/`. It uses Python 3.12. Minimal server dependencies are listed in `app/requirements.txt`; the AI dependency set is in `app/requirements-ai.txt` and the verified environment versions are in `app/requirements-ai-lock.txt`.

If rebuilding on another computer:

1. Create the Python environment and install the AI dependency set.
2. Run `tools/setup_image_model.py` for the free local image generator, and `tools/setup_recognition_model.py` for the browser photo matcher. These installers download public model files and check every file's SHA-256 against the model host's metadata. They do not send inventory, prompts or photos.
3. Start the local server. The generation model cache and runtime data are excluded from version control; browser recognition models are application assets.

## Accounts and images

Accounts belong to a household. Creating a new account without an invite code creates a household and makes that user its household administrator. An existing member can share the household's invite code; accounts created with that code stay pending and cannot sign in until a household administrator approves them. Approved members share inventory, recipes, and household images. Inventory additions, quantity changes, edits, removals, and recipe imports are attributed to the member in the household activity feed. Usernames are case-insensitive. Passwords are salted and hashed with scrypt; session tokens are hashed at rest. Requests that change saved data require an accepted origin and a CSRF token.

The first system administrator uses a one-time setup token written into the private runtime directory at first start. Run `tools/open_local_admin.py` locally to open its setup page without printing the token, then choose the administrator username and password in the page. Once used, that token is invalidated and its file removed. System administrators can promote or demote system roles through the account panel. The last system administrator cannot be demoted. Household member approval is managed separately in the Household page. No default administrator password was created.

The local preview uses development cookies on loopback HTTP. Production defaults keep Secure cookies and accept only the existing HTTPS origins. Do not enable `PANTRY_DEV` on a public server.

## Feature behavior

- **Modes:** the visible switch selects **Kitchen** (food, drinks, recipes; warm green styling) or **Home inventory** (cleaning, bathroom supplies, personal care and other household items; blue/lilac styling). The banner, overview, totals, item list, locations and default entry fields follow the selected mode. Recipes use food items only and are hidden in Home inventory. Switching modes filters the view without changing or deleting saved data. The selection is remembered in this browser. The Item belongs to field moves an item between the two modes when saved. Older records without that field use their existing category, with household-name hints as a fallback. Export all items still exports both modes.

- **Barcode:** rear-camera scanning, decoding a barcode photo, or typing the digits. Product results come from free catalog tiers and are shown for confirmation, including package size and available catalog photos.
- **Photo:** package-label OCR and a quantized CLIP model run in the browser. CLIP compares common food and household item descriptions; its scores are suggestions, not verification of a brand, package size, ingredients or allergens. The user confirms a catalog match or creates the item manually. The photo is not sent to an external vision service. Catalog searches send the chosen search words or barcode.
- **Images:** use a real catalog image or upload a photo. **Generate New Image** opens a chooser with three freshly generated SD-Turbo images based on the item name. **generate new options** creates another set with fresh seeds and viewpoints. Selecting an image inserts it into the current creation/editing draft; Save item applies the choice. Cancel leaves the previous image unchanged. Administrator replacements also show three choices and apply only the selected image. Missing-image saves first check catalog photos, then open the same chooser. Generated images are labeled and their provenance is recorded by the server.
- **Merging:** matching barcodes, storage locations and units add quantities atomically. Unbarcoded items additionally match normalized name, brand and package size. Different units or locations stay separate. Editing into a duplicate returns a conflict rather than silently merging. An actual product photo is preserved when an additional item carries only a generated illustration.
- **Import:** repeated imports of the same browser snapshot are idempotent. Quantities merge once, including duplicate entries in a single import. Browser originals are retained in the legacy backup. A failed import leaves the user signed in and explains that the original backup is preserved.
- **Admin image checks:** audit saved accounts for broken or missing images. Only an unambiguous matching barcode photo is repaired automatically. Ambiguous matches remain for review. Optional AI fallback supplies illustrations when a catalog search finds no image; provider failures remain retryable. Generated images are revisited on later audits so real photos can replace them. Concurrent uploads are preserved.
- **Households:** each account has one home. New members sign up with that home's invite code and remain pending until approved by a household admin. Existing accounts are migrated into separate homes to preserve their existing private inventories. The Household page shows the invite code, member status, and recent per-account activity.
- **Storage locations:** built-in Pantry, Refrigerator, Freezer, Bathroom, Utility closet, Laundry room, Garage, and Other locations remain available. Approved household members can add custom locations for either Kitchen or Home inventory mode. Custom locations are shared in the household and can be removed after their items have been moved elsewhere.
- **Recipe library:** household-visible recipes are shared with approved members; private imports are visible only to their owner. The profile control and **My dashboard** page manage each account's recipe sources, import history, personal recipes, and diet, allergen, serving, and cook-time preferences. The searchable service directory covers Pepperplate, Allrecipes, Epicurious, The Kitchn, Budget Bytes, Paprika, AnyList, Copy Me That, NYT Cooking, Food Network, BBC Good Food, Serious Eats, Taste of Home, Simply Recipes, Martha Stewart, Tasty, Recipe Keeper, CookBook, and other services. Import methods include public recipe URLs with Schema.org Recipe JSON-LD, JSON/CSV files, provider ZIP exports (Paprika archives/HTML, Pepperplate text ZIP, CookBook recipe ZIP, and compatible recipe HTML/text ZIPs), and a structured copy/paste form. The directory links to provider export instructions where verified. No recipe-provider passwords are collected. No public, authorized recipe-library OAuth/API sync is configured; a true background sync needs an official provider API and an approved app registration. An imported URL must be publicly reachable and expose structured recipe details. Imports are private by default; account holders may choose household sharing. The preferences filter suggestions by title, listed ingredients, and available time; they are not a safety check for allergies or dietary restrictions. System administrators can review and remove recipes across households. It matches recipe ingredient text against current food stock. Recipe cards show finished-dish thumbnails and open a dedicated detail view with a large image, ingredients, steps, time, yield, source, and any imported category, cuisine, author, rating, keywords, or nutrition details. The six built-in recipes have individual dish images. Imported source photos are retained; when an imported recipe has no photo, PantriPortal creates and saves a locally generated dish image when the recipe is first opened, while showing a branded fallback.

## Runtime and recovery

By default, the new local data lives in `work/runtime/`: `inventory.sqlite3`, private `media/`, and the initial administrator setup token. Original runtime data from the earlier project was not imported. The model cache is under `work/models/`; browser recognition weights are under `app/models/`.

`PANTRY_DATA`, `PANTRY_PORT`, `PANTRY_MODEL_CACHE`, and `PANTRY_IMAGE_MODEL` can override local paths or model selection. A future deployment must preserve the complete database and media directory separately from application releases. The JSON inventory export contains item records and image references; it is not a complete backup of image bytes.

Model downloads use ModelScope's public mirrors because direct Hugging Face downloads reset connections in this environment. Provenance and checksum manifests are retained next to the downloaded models. Upstream documentation and license terms remain applicable: [SD-Turbo](https://huggingface.co/stabilityai/sd-turbo), [CLIP browser model](https://huggingface.co/Xenova/clip-vit-base-patch32), [Transformers.js](https://huggingface.co/docs/transformers.js/api/models).

## Validation and remaining limits

Run `work/venv/Scripts/python.exe -m unittest discover -s tests -v` for isolated integration tests. They use temporary accounts and a temporary database, not live customer data. The test suite covers quantity concurrency, units/package separation, import idempotence, account/media isolation, CSRF/origin rejection, role management, administrator bootstrap, image-generation job behavior, catalog failure handling and preservation of real photos.

See the release validation report for browser results. Physical phone-camera testing still needs a real device over HTTPS. Free catalog availability and exact photo-match accuracy vary. Password recovery and separate household invitations are not included. Production deployment details are below.


## Current production deployment — October 20, 2026

Version 0.9.0 is live at https://www.pantriportal.com/. Release `/opt/pantry-portal/releases/20261019T230144Z-0.9-admin` adds the administration dashboard, permission controls, audit and error reporting, protected Word guide and customizable Home inventory sections. See ADMINISTRATION.md for operational instructions and validation limits. Private backup `/var/backups/pantry-portal/admin-20261019T230144Z` contains configuration, pre-release database/media, record digests, final host test results and rollback instructions. Every pre-existing table record was verified unchanged across activation.

The dated sections below describe earlier releases and are retained as deployment history.

## Production deployment — October 16, 2026

Live site: https://www.pantriportal.com/. Active release: `/opt/pantry-portal/releases/20261017T054249Z-0.5-ui`, selected by `/opt/pantry-portal/current`; the October 16 application release remains `/opt/pantry-portal/releases/20261016T193808Z-0.5`. Nginx serves approved public assets; the application listens only on loopback. Existing IP/bare-domain encrypted browser transfers and the transfer service were retained. `bootstrap.js` waits for the migration guard before loading the application.

The October 17 UI-only release added the 1140px responsive layout, tablet and phone breakpoints, supplied logo and hero artwork, and dashboard header/metric markup. It did not change application services or persistent data. The previous release and Nginx configurations are backed up under `/var/backups/pantry-portal/ui-responsive-20261017T054249Z/`; `rollback.sh` restores the previous release and configuration.

The application uses `/opt/pantry-portal/venv-0.5/bin/python` (Python 3.14), with CPU-only Torch 2.14.1 and the tested AI libraries. The production unit sets `PANTRY_DATA=/var/lib/pantry-portal`, `PANTRY_MODEL_CACHE=/opt/pantry-portal/image-models`, `HF_HUB_OFFLINE=1`, and `PANTRY_IMAGE_QUANTIZE=1`. Development mode is disabled. CPU quantization reduces linear-layer weight storage on the 4 GB host; the original local runtime keeps its default precision. An 8 GB private swap file supports initial model loading. The actual three-image generation and selection test completed in 152 seconds on a cold start. Generation can take several minutes on this server.

The private backup is `/var/backups/pantry-portal/release-20261016T193808Z/`: configuration archive, stopped-application database/media archive, before/after record digests, integration-test log, installed dependency versions and `rollback.sh`. Rollback restores the previous application/configuration while retaining current saved data. All six accounts, six sessions, eighteen items and three uploaded-media records had identical hashes immediately before and after activation. No local QA account or media was imported into production.

Both existing administrator accounts were preserved. No administrator credential was created or disclosed by deployment. Setup tokens and passwords are excluded from deliverables.

## Production deployment — October 17, 2026 (households and storage locations)

The active release is `/opt/pantry-portal/releases/20261017T062740Z-0.6-households`, selected through `/opt/pantry-portal/current`. It adds household signup and administrator approval, household activity, public recipe URL and JSON/CSV import, and add/remove controls for custom storage locations. It retains the October 17 responsive dashboard and supplied PantriPortal logo and artwork. Production model assets were reused.

Before activation, the service was stopped and the production database and media were archived to `/var/backups/pantry-portal/20261017T062740Z-0.6-households/data-before.tar.gz`. The archive passed `tar -tzf` integrity verification. The database now has six household records, one for each of the six pre-existing accounts; no new accounts or inventory were created. Pre/post hashes for the existing user credentials, sessions, inventory items, recipe import markers, media records, and media files matched. The before/after snapshots and public health check are in the same private backup directory. The previous code release is `/opt/pantry-portal/releases/20261017T054249Z-0.5-ui`.

## Production deployment — October 19, 2026 (personal recipe dashboard, superseded by 0.8)

Release `/opt/pantry-portal/releases/20261019T132052Z-0.7-user-recipe-dashboard` introduced the account dashboard; it was superseded by 0.8 below. It added the searchable recipe service directory, source import history, personal recipes, and per-user preferences.

Provider account OAuth/API synchronization was not configured. Release 0.8 below adds provider export-file ingestion and its Nginx upload limits.

The prior release was `/opt/pantry-portal/releases/20261017T062740Z-0.6-households`. The data and media backup and record snapshots are under `/var/backups/pantry-portal/20261019T132052Z-0.7-user-recipe-dashboard/`. Seven existing accounts and homes were retained.

## Production deployment — October 19, 2026 (provider recipe exports)

The active release is `/opt/pantry-portal/releases/20261019T134012Z-0.8-recipe-export-imports`, selected through `/opt/pantry-portal/current`. Production reports application version `0.8.0`. The account dashboard now imports Pepperplate's official ZIP of recipe text files, Paprika `.paprikarecipes` and HTML recipe exports, CookBook recipe ZIP exports, and compatible ZIPs containing structured JSON, JSON-LD/hRecipe HTML, or labeled text recipes. JSON/CSV import and public recipe links remain available. ZIP parsing runs in memory, applies per-file and total expansion caps, stores no uploaded archive, and only creates private or shared PantriPortal recipe records after the user confirms an import. Nginx has path-specific upload limits for the parse and import endpoints.

Direct account sync remains unavailable. No provider-issued OAuth app or public authorized recipe-collection API was found for this provider set; PantriPortal does not request or retain provider passwords or scrape private services. A provider may offer a private partner API, but it requires that provider's approval and app credentials before a connector can be built. The export transfers above are one-time imports, not ongoing sync.

The previous release is `/opt/pantry-portal/releases/20261019T132052Z-0.7-user-recipe-dashboard`. The database/media archive, Nginx snapshots, before/after data snapshots, and health response are under `/var/backups/pantry-portal/20261019T134012Z-0.8-recipe-export-imports/`. The public site and service reported version `0.8.0`; account, inventory, household recipe, import-marker, and media hashes matched across activation. Existing image model assets were reused.

## Production kitchen companion release — October 20, 2026

Version 0.10.0 is live at https://www.pantriportal.com/. The release `/opt/pantry-portal/releases/20261020T174250Z-0.10-kitchen` adds guided recipes with ingredient references and step photos, personal meal plans, grocery lists and explicit purchase-to-inventory confirmation. Operational instructions and validation limits are in KITCHEN_COMPANION.md. Private backup `/var/backups/pantry-portal/kitchen-20261020T174250Z` contains stopped-service data/media, configuration, tests, checksums and before/after table digests. All pre-existing records matched before and after additive schema initialization; the protected dcolanduno administrator remains unchanged. Existing AI runtime dependencies were reused. Browser drafts are not server-saved until recipe submission.
