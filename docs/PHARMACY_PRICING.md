# Medical profiles and pharmacy prices

Version 0.14.0 adds scan access inside Add/Edit prescription, private insurance/discount cards, ZIP-based pharmacy lookup and a comparison table with a cash column and a separate column for each active saved program. Medical profile is available in the personal dashboard and Medicine. Cards support plan, member ID, group, RxBIN, RxPCN, phone, public HTTPS website and notes. List views mask card IDs; edit reveals them only in the signed-in owner's form. Archive/restore does not delete quote history.

## Price accuracy and privacy

Each saved quote records prescription identity (name, strength, NDC), pharmacy/address, payment program, total USD price, exact dosage form, fill quantity/unit, days supply, quoted date and source. The user affirms the product/manufacturer and fill. The exact-fill table excludes prices with different fill details or an edited medicine identity. The browse-first view described below intentionally lists separately labeled strengths for the same drug name. Zero is a valid quoted amount; missing is unknown. Old quotes remain in history, while each cell shows the most recently dated matching quote. Updating a quote creates a new record. A recorded quote is not a checkout guarantee, coverage determination, network confirmation, stock check or prescription transfer.

Profiles and quotes are owner-only even within the same household and for application administrators. New tables `medicine_benefit_entries` and `medicine_benefit_profiles` are additive; no prior rows are rewritten. Authenticated CSRF-protected routes remain under `/api/medicine/`, whose audit values exclude medical bodies, search terms and record IDs. As with medicine cabinets, host/database operators can access private runtime data and backups. No claim of medical-record certification or additional encryption is made.

The directory searches NIH Clinical Tables NPI organizations by five-digit ZIP, restricted to pharmacy taxonomy. It returns at most 100 registered pharmacies, not all geographically nearby branches. Google Maps supplies a link to find more. ZIP is sent only on explicit search; member identifiers, prescription details and medications are excluded. Map links contain a pharmacy ZIP query, never card identifiers. Public program tools open separately; the user enters their exact medication and coverage there.

## Official API options researched October 24, 2026

| Provider | Available official interface | Access and application status |
| --- | --- | --- |
| GoodRx | V2 Price Compare and Coupon APIs | Partner application, API key and shared signing secret required. Signed Price Compare adapter implemented; disabled until approved access is privately configured. Production account credentials were not present. Live provider requests could not be validated. |
| CVS Health / Caremark | Pharmacy Benefit Manager developer products | Developer access request and approved member/benefit integration required. No public anonymous plan copay endpoint verified; no integration or automatic insurance adjudication claimed. |
| SingleCare | Official partnership program and consumer comparison tool | Partnership route verified; public self-service pricing API documentation/access was not verified. Official tool linked; no private endpoints scraped. |
| AARP / Optum Rx | AARP pharmacy comparison tool and Optum member pricing tools | Consumer/member tools linked. No approved public API for this site's member-specific prices was available. |
| Medicare / Medicaid | Medicare Plan Compare and insurer/state benefit tools | Plan, pharmacy and eligibility affect the price. Saved enrollment details alone do not establish copays. No consumer member-price API integration claimed. |

Sources:
- https://www.goodrx.com/developer
- https://www.goodrx.com/developer/v2-documentation
- https://www.goodrx.com/developer/documentation
- https://www.goodrx.com/developer/apply
- https://developer.cvshealth.com/
- https://www.singlecare.com/partners
- https://aarppharmacy.com/
- https://www.medicare.gov/plan-compare/
- https://clinicaltables.nlm.nih.gov/apidoc/npi_org/v3/doc.html

## Configure approved GoodRx partner access

After GoodRx approves the site's usage and applicable agreement, the host operator sets `PANTRY_GOODRX_ENABLED=1`, `PANTRY_GOODRX_API_KEY` and `PANTRY_GOODRX_SECRET` in the private service environment and restarts the service. Never place these values in Git, the frontend, profile forms, output, URLs visible to users or release metadata. The documented upstream API itself requires a signed query containing its API key; application logs must not include that URL. Requests use a fixed HTTPS host, bounded response size, no redirects, timeout, per-account rate limits and generic failure messages. No provider accounts, contracts, purchases or emails were created by this work.

The UI asks permission before each lookup to share NDC (or name/strength/form), metric fill quantity and ZIP with GoodRx. No member/group IDs, RxBIN/RxPCN, prescription numbers, patient identity, directions, phone or full label is sent. Name-based requests specify `manufacturer_type=match`, dosage and form; NDC requests use validated NDC11 conversion. Unformatted ambiguous ten-digit NDCs are rejected. Only matching returned strength, form, metric quantity and days supply produce estimates; incomplete/mismatched responses produce no prices. The API can return defaults and equivalent products, so users still verify identity/manufacturer before acting.

API results are separate from saved, program-specific quotes. Cash, coupon and membership prices are identified by provider type; separate membership costs are shown. No generic membership estimate is presented as an authenticated GoodRx Gold price or an insurance copay. Provider coupon links must be HTTPS on GoodRx's own domain. Credentials and raw coupon keys are not sent to browsers. No coupon email/SMS or automatic refills, transfers, claims or purchases are performed.

Remaining operator action: obtain approved GoodRx API access through its application page, then configure it privately and validate a real signed request. Other member-price integrations require the corresponding provider's approved interface and access. Manual source-attributed quotes and official provider links work meanwhile.


## Browse-first prices (0.14.1)

Opening Nearby pharmacies & prices immediately displays the owner's saved quotes for the same drug name across strengths, with dose, form, quantity, days supply, pharmacy, date and source visible in every row. No fill fields or ZIP are required to see this list. Matching ignores case, whitespace and recognized NIH route suffixes; it does not merge different brands, generic names or extended-release name modifiers. Historical strengths are deliberate browsing examples, not the price of the current prescription. The exact-fill comparison still retains its strict name/strength/NDC/quantity checks inside the optional Refine section.

Available strengths/forms are retrieved from NIH RxTerms using only the drug name and accepting exact normalized name matches. ZIP-only pharmacy searching is independent of all fill fields. The saved profile ZIP prepopulates the search without transmitting it until Search is selected.

When approved GoodRx access is configured, a separate consent-based name-only browse endpoint uses the official Drug Info API, then fetches standard-fill price examples for up to six strengths/forms, prioritizing pills. Users need not enter dose, form, quantity or supply duration. Returned dose/form must match the queried option; quantity and days supply must be provided by the service and are displayed, never inferred from the personal prescription. Requests are limited to two browse operations per minute/account, at most seven upstream calls per operation, with three simultaneous bounded workers. Missing or failed options are omitted, never represented as zero. Brand/generic matching uses the provider's match mode; the returned product name is shown for verification. No patient/profile identifiers, prescription number, directions or notes are used. No changes are made to saved medicines, program data or quotes. Live upstream prices still require the approved credentials described above; synthetic contract tests are not evidence of a live connection.


### Public Cost Plus Drugs cash catalog

The opening view also fetches the official public Cost Plus Drugs price catalog at `https://api.costplusdrugs.com/pricelist/cpd`. This requires no partner key. The entire public catalog is downloaded with a fixed request and shared in memory for up to one hour; the patient's drug name, account, ZIP and insurance details are never sent to that provider. Results are filtered locally by medication name, with generic alternatives for exact brand references explicitly identified. No user searches are stored in the catalog cache.

Rows show the pharmacy-supplied strength, form and sample fill size, cash price including dispensing, standard shipping when supplied, and the supplier's total-with-shipping example when supplied. No price is calculated from a unit cost or assumed fee. Missing values stay unknown. These are mail-order cash listings, not nearby pharmacy, insurance or coupon prices, and in-stock flags and retrieval time are shown. Product links are limited to HTTPS on the pharmacy's own domains. Source data is read-only; no prescription, order, transfer or account is created. API prices must be verified on the source product page. Current API documentation: https://mccpdc-llc.github.io/pricing-api-documentation/cpd.html. The older documented Cloud Functions API is deprecated and is not used by this implementation.
