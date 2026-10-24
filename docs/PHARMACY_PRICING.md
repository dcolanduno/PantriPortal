# Medical profiles and pharmacy prices

Version 0.14.0 adds scan access inside Add/Edit prescription, private insurance/discount cards, ZIP-based pharmacy lookup and a comparison table with a cash column and a separate column for each active saved program. Medical profile is available in the personal dashboard and Medicine. Cards support plan, member ID, group, RxBIN, RxPCN, phone, public HTTPS website and notes. List views mask card IDs; edit reveals them only in the signed-in owner's form. Archive/restore does not delete quote history.

## Price accuracy and privacy

Each saved quote records prescription identity (name, strength, NDC), pharmacy/address, payment program, total USD price, exact dosage form, fill quantity/unit, days supply, quoted date and source. The user affirms the product/manufacturer and fill. Prices with different fill details or an edited medicine identity are excluded from the table. Zero is a valid quoted amount; missing is unknown. Old quotes remain in history, while each cell shows the most recently dated matching quote. Updating a quote creates a new record. A recorded quote is not a checkout guarantee, coverage determination, network confirmation, stock check or prescription transfer.

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
