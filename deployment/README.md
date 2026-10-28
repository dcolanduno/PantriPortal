# Deployment and recovery

GitHub publication does not deploy this application. No deployment credentials, private keys, production databases, household photos or live environment files are included. Configuration examples need review; they are not an installer.

## Source of truth

All development and live application code must come from the GitHub repository. Commit, test and push changes before deployment. Build the release with `python tools/package_release.py --ref HEAD --output work/releases/pantriportal.zip`. The packager requires a clean checkout and a commit reachable from `origin/main`, and reads application files directly from that commit. It flattens `app/` into the deployed layout and includes `release-source.json` with the full commit and per-file hashes plus `RELEASE-SHA256SUMS`. Model weights and private data remain separately managed.

Upload and extract the artifact into a fresh release directory, retain the existing verified models, and follow the activation checks below. Run `sha256sum --check RELEASE-SHA256SUMS` in that release. Verify the active release's `release-source.json` commit against GitHub and the tested development commit. A static follow-up must be committed and packaged through the same process. Never treat a GitHub push alone as evidence that the live site changed.

## Existing installation

The existing site is https://www.pantriportal.com/. Releases are under `/opt/pantry-portal/releases/`; `/opt/pantry-portal/current` selects static files. Private runtime data is `/var/lib/pantry-portal`, shared generator models are `/opt/pantry-portal/image-models`, and loopback application/transfer ports are 8767/8766. Existing service names are `pantry-app`, `pantry-transfer` and `nginx`.

At source-import time the application is 0.10.0 and the active static release is `/opt/pantry-portal/releases/20261020T174843Z-0.10-kitchen-nav`. Earlier releases and backups remain private on the host. Old local deployment scripts contain historical release assumptions and are deliberately not presented as reusable tools.

## Prepare and activate

1. Clone the repository and run its tests. Keep private runtime directories outside the checkout.
2. Create a fresh release directory containing the **contents** of `app/` directly, with `server.py` at the release root. The source repository retains `app/` for development.
3. Install `app/requirements.txt` into a reviewed runtime. Add AI dependencies and verified weights if generation is needed. Reuse compatible existing production runtimes and models.
4. Restore browser recognition files with `tools/setup_recognition_model.py` and place its generated model directory under the release's `models/`. Include Python modules, static assets, vendor scripts, branding, migration scripts, manifests, `builtin-recipes.json`, `error_catalog.json` and the administrator Word guide.
5. Generate and check release hashes. Use an existing SSH identity and pinned known-host verification; never put keys into Git or terminal output.
6. During a maintenance window, record the current symlink and proxy configuration, stop the application, back up database/media/audit verification material privately, and validate the archive. Snapshot hashes/counts of existing records. Initialize additive schemas against the same private data and compare existing records.
7. Atomically select the new release. Review/test Nginx before reload and restart the application. Verify HTTPS health, authentication, protected assets, services, image readiness and audit signatures. Keep previous code/configuration and verified private backups available.

The Nginx example covers the canonical HTTPS origin and HTTP redirect. Existing alternate-domain/IP migration routes need their own reviewed configuration; do not replace the live configuration wholesale with this example. Provision TLS certificates privately. Systemd examples use a dedicated account and `/opt/pantry-portal/venv`; adjust for the verified target and give that account appropriate private data/cache access. Never enable `PANTRY_DEV` in production. A different public origin also requires review of `ORIGINS` and migration rules in Python.

## Administrator and rollback

The existing production `dcolanduno` account is pinned by immutable ID in private configuration. Preserve its access and deletion protections. The name is reserved from public signup; a fresh installation does not gain a privileged owner by submitting that name. Use the private one-time setup flow for an initial administrator. Owner provisioning/recovery requires private host administration and verification of the real owner's existing identity.

Review data compatibility before rolling code back. An older release may ignore new permission, recipe or purchase semantics. Do not overwrite later user purchases or audit records with an earlier database without an explicit recovery decision. Preserve signing key/checkpoint with the corresponding database snapshot.

Install `requirements-dev.txt` to regenerate the handbook with `python tools/build_error_guide.py`; visually review its Word layout before replacing the shipped guide. Private incident and recovery files are not source artifacts.

## Medicine reference search (0.12.0)

Deploy `medicine_catalog.py` alongside `medicine_ops.py` and `medicine.js` from the same tested release. Reference services require outbound HTTPS to `clinicaltables.nlm.nih.gov` and `api.fda.gov`. Optional Google Places requires `places.googleapis.com` and a private `PANTRY_GOOGLE_PLACES_KEY` service environment setting; never commit it or include it in release metadata. Without that setting the NIH doctor directory remains available. Existing `/api/` proxying and `/medicine.js` static exposure cover these changes. No additional schema tables or packages are introduced; the two optional prescription identity fields are additive JSON properties. Restart the Python application after release activation and check health version 0.12.0 plus the affected signed-in forms.

Optional FineRx nearby price lookup requires an issued API key from FineRx (`https://www.finerxfinder.com/en/developers`). Configure only in the private service environment with `PANTRY_FINERX_ENABLED=1` and `PANTRY_FINERX_API_KEY`; restart `pantry-app` afterward. Without both settings, the existing LowerScript public lookup remains in use. The key is sent in the server-side `X-Api-Key` header to the fixed HTTPS `finerxfinder.com` API endpoint; it is never sent to the browser, placed in a URL, or logged. FineRx requires visible price attribution and an observed-price disclaimer. Price requests contain only the drug name, optional strength and saved ZIP, use the 20-mile radius parameter, and are not cached. Validate a real authorized key and a provider response before claiming FineRx is active. Never add credentials to the release artifact.


## Prescription label scanner (0.13.0)

Expose `/prescription-label.js` and `/prescription-scan.js` through both canonical and compatibility proxy configurations. Use the same commit's bootstrap, medicine frontend and Python modules. The browser uses the existing local ZXing/Tesseract libraries and their recognition-runtime downloads. NDC reference requests use `api.fda.gov/drug/ndc.json`; no photos or raw label text are posted to an OCR backend. The additional saved JSON properties do not rewrite existing records. Check signed-in scanner loading, public product lookup, private save/review, telephone links, and account-change cleanup. Camera hardware requires a real phone test; desktop photo OCR is a separate verification.

## Prescription label OCR recovery (0.15.3)

The live scanner enlarges a center crop and runs whole-frame and label-focused layouts. Preserve useful lower-confidence lines for cross-pass agreement, and show a marked strongest-candidate fallback for manual review instead of silently returning blank. Check the signed-in photo and continuous-camera flows, OCR text review, field extraction and mandatory confirmation. Real bottle/camera OCR still needs physical-device QA; synthetic tests do not prove patient-label accuracy.

## Version footer (0.15.4)

The shared page footer reads the current version and short commit build identifier from `/api/health` with caching disabled. The server derives the build identifier from the deployed `release-source.json`; local source checkouts without release metadata report `local`. Keep the release metadata beside `server.py` when packaging and deploying so the label reflects the active release.

## Continuous GS1 package barcode scan (0.15.8)

Deploy the same commit's `prescription-scan.js`, `prescription-label.js`, `medicine.js`, bootstrap, and Python application. The rear camera is handed directly to ZXing BrowserMultiFormatReader continuous decoding for GS1 DataMatrix or linear package codes as soon as the scanner opens. No repeated app-managed video-frame copies or photo capture are needed to scan. A valid package code fills only its checked NDC or GTIN, expiration, lot and serial values; GTIN lookup uses an exact FDA-harmonized UPC value but returns only a product candidate; it does not infer or fill the package NDC. Barcode data never becomes an Rx number. OCR remains a manual photo fallback. No prescription image or OCR text is uploaded. Preserve all existing private runtime storage; there is no schema migration. Check `/api/health` reports version 0.15.8 and the active commit, all application/transfer/proxy services remain active, the scanner assets match release hashes, signed-in access and review-before-save still work, and health/data/admin protections remain unchanged. A physical-phone camera and accuracy check is still required after rollout.

## Continuous prescription label scanning (0.15.2)

The signed-in label scanner requests the rear camera as soon as it opens, then reads frames locally until stopped. Keep the same NDC privacy boundary: raw images and OCR text never go to the application server. Deploy the same commit's scanner, parser, bootstrap, medicine modules and versioned server. Verify camera permission handling, continuous frame reading, deduplication of unchanged views, multi-view field preservation, explicit review/save and camera shutdown. Physical phone autofocus and actual bottle accuracy still require a real device check.


## Benefits and comparison screens (0.14.0)

Expose `/medicine-benefits.js` in canonical and compatibility Nginx routes. Deploy medicine_benefits.py and medicine_pricing.py with the same commit's frontend, bootstrap and medicine operations. Additive profile/quote tables must remain private in runtime backups. GoodRx partner access is optional and disabled without explicit private configuration; see docs/PHARMACY_PRICING.md. Source tests use synthetic provider responses; no live authenticated pricing claim is permitted until credentials and a real matched request are verified.
