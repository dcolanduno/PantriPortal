# Medicine and household pharmacy

Open **Organize → Medicine** after signing in. Each account has one personal cabinet; name it with **Name my cabinet**. Cabinet information is stored on the server for use on your other signed-in devices, and is not saved in browser local storage.

## Personal records

- **Doctors:** name, practice, specialty, phone, email, address and notes. Link a saved doctor to prescriptions or appointments to see contact details beside the record.
- **Prescriptions:** medicine name, label strength and directions, quantity/unit on hand, remaining refills, last fill, next refill date, prescription expiration, pharmacy contacts and prescription number. Update quantities and refill information with Edit prescription. These are manually entered records; the application does not change prescribed instructions, calculate doses, request refills or connect to pharmacies.
- **Appointments:** date/time, explicit time zone, clinic/address or video visit information, contact phone, linked doctor and notes. The next upcoming visit appears above the cabinet tabs. Dates are stored with the entered time zone and a UTC equivalent; appointments do not send reminders or book visits.

Search each section. Archive records you no longer need; use **Show archived** and **Restore** to bring them back. Edits carry a revision so a second device cannot silently overwrite a newer edit.

## Household supplies

The **Household pharmacy** tab shows non-food items in the **Medicines and first aid** Home inventory section. This includes OTC medicines, Pepto-Bismol, aspirin, heartburn products, cotton swabs/Q-Tips, bandages and similar supplies when assigned to that section. Add shared supply opens the regular Home inventory form with that section selected. Manage shared stock returns to the filtered Home inventory.

These are the same inventory records, not copies. Changing stock in Home inventory changes what Medicine displays after Refresh. Only approved, enabled household members' stock appears. Existing inventory editing permissions still apply. No existing shared record is automatically converted into a private prescription; enter personal prescription details in your cabinet.

## Doctor office maps

Saved doctor cards with an office address show a small OpenStreetMap preview when scrolled into view. Click the preview or **Open full map** to open that address in Google Maps in a new tab/window. **Get directions** opens Google's directions interface with the destination filled; choose your starting point there. The application does not request your current location.

Previews use the free U.S. Census address geocoder and OpenStreetMap's official embedded map, without a paid API key. Census coverage is the United States, Puerto Rico and U.S. Island Areas. Pins are approximate address-range locations. An unmatched, ambiguous or unsupported address, a blocked map frame, or an unavailable service can prevent the preview; full map and directions links still work for the entered address. Add or correct the doctor's office address using Edit doctor.

Only the office address is sent to the Census service; map tiles receive coordinates. Opening the full map sends the office address to Google Maps. The account, doctor's name, prescription details and notes are not included. The owner-only `/api/medicine/office-map` POST route reads the saved address on the server and ignores client-supplied addresses. Search strings and coordinates are not written to application logs or persistent caches. A bounded, temporary in-memory geocoding cache reduces repeated lookups. It expires after 24 hours for matched addresses or one minute for unavailable results. No personal record or database schema is changed by viewing a map. Existing medicine ownership protections still apply.

## Access and operations

The application only returns or modifies a cabinet, prescription, doctor or appointment for its signed-in owner. There is no household-member or application-administrator override for these personal records. Shared stock and private prescriptions use separate tables and routes. Owner IDs supplied by a client cannot transfer ownership. CSRF and origin checks apply to changes.

Medical names, directions, prescriber contacts, appointment details, request bodies and medicine record IDs are excluded from activity logs. The log records the account, operation, generic Medicine route, result status, error code and request reference. Diagnostic exceptions retain stack locations and error types, not submitted values. Lookup requests send only the typed doctor name and optional city/ZIP, medication name, or selected public product identifier to the reference provider. Cabinet records, account identity, notes, prescription numbers and directions are never included in provider requests. Search terms and reference responses are not persisted in the database cache. No AI service receives cabinet data.

Cabinets and records are kept in the private application database and included in private operational backups. This is application-level ownership protection: authorized host/database operators can access database files and recovery archives. Those files must remain private, outside Git and public exports. Application administrators cannot browse these personal tables through the content-management API.

The additive migration creates `medicine_cabinets` and `medicine_records`. It preserves all existing inventory and user records. The frontend asset is `/medicine.js`; deployment proxies must expose that static asset. Runtime requirements include pinned `tzdata` for consistent time zones on Windows and Linux. Rollback must preserve the new tables and later user records; never restore an older database over new medical entries merely to roll back code.

## Search while entering doctors and medicines

After three characters, the name field searches after a 350 ms pause. Choose a result with the mouse or arrow keys and Enter. Escape dismisses suggestions. Closing the form, changing accounts or typing a newer query discards older responses. Manual entry and saving work during provider outages.

Doctor suggestions use NIH Clinical Tables' CMS NPI individual-provider directory. Add a city, state or ZIP to narrow similar names. Selecting a result fills the available specialty, address and phone; verify the office details before saving. Missing fields remain empty rather than retaining another selected doctor's contacts. Google Maps and Bing search links provide additional manual verification. Practice names and email are not invented when absent from the source.

Optional Google Maps autofill uses Places API (New) Text Search when the operator configures `PANTRY_GOOGLE_PLACES_KEY` in the private service environment. It requires an enabled, appropriately restricted Google Places credential and applicable billing. Keep it outside Git. Google attribution and supplied provider attributions appear beside those suggestions. Without a key, registry search remains available; Bing is a search link, not an automated data feed. No new paid account is provisioned by this change.

Medication suggestions use NIH RxTerms, including brand/generic name and route. Strength/form suggestions appear after selection; users must choose or enter their prescribed label strength. No dose, strength, directions, refills or quantity is inferred. A selected exact strength retains its RxNorm identifier in the owner's record. Changing the name clears the catalog link, and changing strength clears an unmatched identifier.

Each prescription has a **Drug information** section, also available while editing. It retrieves matching FDA product label candidates by RxNorm identifier, or a quoted brand/generic name search for manual entries. The user chooses a manufacturer/route/NDC label before reading it. Name-only searches explicitly require formulation and strength verification. Up to 12 candidate labels are returned; DailyMed search remains available for other products. Matching labels are reference candidates, never a claim that the first label applies to the prescription.

Label sections include uses, adverse reactions, boxed warnings, precautions, contraindications, interactions, label administration, pregnancy/breastfeeding, overdose, storage, patient information and remaining available sections. Text is displayed without HTML execution or section truncation, with source links and effective dates. Missing sections and absent results do not establish that there are no risks. Labeling is not an exhaustive list of off-label uses, and it does not provide a personalized clinical or interaction assessment. Provider failures leave the saved prescription intact.

Public reference routes are authenticated, CSRF-protected POST requests under `/api/medicine/`, keeping search terms out of URL query logs. They have per-account rate limits, bounded response sizes, timeouts and fixed HTTPS destinations with redirects disabled. No new database tables or dependency installations are required.

Reference API documentation:
- https://clinicaltables.nlm.nih.gov/apidoc/npi_idv/v3/doc.html
- https://clinicaltables.nlm.nih.gov/apidoc/rxterms/v3/doc.html
- https://open.fda.gov/apis/drug/label/
- https://developers.google.com/maps/documentation/places/web-service/text-search


## Scan your own prescription bottle

In Medicine, choose **Scan prescription label**, then **Take label photo** on a phone or **Choose label photo**. Use one bottle per scan. **Add another photo of this bottle** reads the other side of a curved label. Supported browsers use the phone's native camera/file picker; actual camera availability and OCR accuracy vary by browser, device and label quality.

Barcode decoding (ZXing) and English OCR (Tesseract.js) run in the browser. The first scan downloads recognition runtime/language files. Label photos, complete recognized text and raw barcodes are never uploaded, saved in inventory media or sent to a public recognition provider. Closing, starting over or changing accounts clears the temporary scan. Recognition must be repeated after reloading the page. No new paid service or API key is needed.

Conservative extraction fills medicine name/printed strength, verbatim directions, explicitly labelled quantity, Rx number (including leading zeros), refills, pharmacy contact/address, printed prescriber and dates. Bottle discard dates stay separate from prescription expiration. Low-confidence recognition leaves fields for manual correction; missing values are not calculated. Dates with two-digit years are not guessed. Quantity printed on a bottle is the dispensed amount: correct it to the amount actually remaining before saving. An OCR score cannot establish clinical accuracy: the user must compare every field against the actual label and affirm that it is their prescription, then review the ordinary form and click Save. This creates an owner-only record; it does not create an inventory item shared with a household.

Pharmacy-specific barcodes can identify a prescription rather than a drug. They are displayed locally and can be used as an Rx number only after explicit selection. Unknown barcode URLs are never opened. **Look up this NDC** sends only the reviewed NDC code to the authenticated server, which queries the fixed public FDA NDC endpoint. Ten-digit legacy formats and common zero-padded billing equivalents are considered; ambiguous padding can produce more than one candidate. Only exact package-code matches are offered. The user chooses a product and verifies its printed name/strength; the lookup does not supply prescription directions or authorize refills. NDC directory inclusion is not proof of FDA approval. See https://open.fda.gov/apis/drug/ndc/.

Saved prescriptions show **Call pharmacy for refill** when there is a valid phone number. The link opens the device's telephone interface; it does not dial automatically or submit a refill, payment or pharmacy-account request. The Rx number and refill details remain available beside it. Pharmacy staff confirm eligibility and any further instructions.

Operators must expose `/prescription-label.js` and `/prescription-scan.js` in addition to `/medicine.js`. Additional prescription JSON fields are additive (`ndc`, `label_prescriber`, `bottle_expires`); no existing rows are rewritten by migration. Raw OCR text/photos are not accepted by a new backend upload route, and medical lookup terms remain excluded from audit values.


## Add-prescription scanner and medical profile (0.14.0)

Add and edit prescription forms include **Scan / photograph prescription bottle**. The scanner opens above the form; cancelling returns to the untouched form. Applying reviewed OCR fills recognized nonempty fields while preserving personal notes. If a different medicine name is scanned, prior label fields and doctor linkage are cleared to prevent mixing two bottles; otherwise unrecognized fields remain for review. Strength changes clear stale product identity, and a new printed prescriber clears the selected doctor for review. It never saves automatically. Medicine and the personal dashboard link to **Medical profile**, where users save private insurance/discount programs. Saved prescription cards and the drug information reader link to nearby pharmacy and price comparisons. See [PHARMACY_PRICING.md](PHARMACY_PRICING.md) for supported fields, official API research, quote matching and access limitations.
