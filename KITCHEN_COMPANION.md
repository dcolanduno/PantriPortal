# Recipes meal plans and shopping

Version 0.10.0 adds a guided recipe builder and a mobile shopping companion. Sign in, refresh the site, then open **Plan & shop**. The Recipes page also has **Create a recipe** and **Plan this meal** buttons.

## Create and edit recipes

1. Enter a title, servings, preparation and cooking times, and private or household visibility. An optional finished-dish photo can be uploaded.
2. Add every ingredient, including seasoning, oils and water. Choose a pantry match or search public food databases. Enter its amount, unit and any preparation notes. Decimals and fractions such as `1/2` or `1 1/2` are accepted.
3. Write the complete instructions one step at a time. Each step can have an uploaded photo. Steps can be reordered or removed.
4. Review and save. Saved recipes appear in the recipe library and pantry-based suggestions. Use **Edit your recipe**, or **My dashboard → Your recipe library → Edit recipe**, to update one.

Ingredient references retain their source, barcode when present, image and available description. Pantry references are limited to the approved household. Public catalog references are recorded by the server rather than accepted as user-supplied assertions. Generic ingredients do not necessarily have barcodes; a shopper can select an exact packaged product later. A catalog listing does not establish availability at a particular store. Database coverage and response times vary.

Public sources: [TheMealDB ingredient API](https://www.themealdb.com/api.php) and [Open Food Facts product API](https://openfoodfacts.github.io/documentation/docs/Product-Opener/v2/products/get-product-by-code/). Open Food Facts provides ODbL data and CC BY-SA product photos. No provider credentials are collected. TheMealDB's public developer endpoint is used; an app-store release would require its supporter key under its published API guidance.

## Plan meals and build a grocery list

Choose **Plan this meal** on a suggested or saved recipe, then select a date, meal and servings. The planner defaults to the coming seven days, with editable date boundaries. Select the meals to include and choose **Review grocery needs**. Planned meals retain recipe snapshots; later edits do not silently alter existing plans. Remove and replan a meal to use an updated recipe.

Recipe amounts scale by servings, aggregate across selected meals, and subtract matching pantry stock once. Grams/kilograms/ounces/pounds convert within mass, and milliliters/liters/US cups/spoons convert within volume. The system does not assume how much flour is in a box or convert mass into volume. Unknown amounts, package sizes and older imported or built-in recipes without structured quantities are marked for review. Existing recipe suggestions remain usable; they are not silently assigned invented amounts.

Add the results to a new or existing named list. Meals added in separate batches are combined and recalculated together so they do not reuse the same pantry quantity. Repeating the same generation does not duplicate its entries. Return pending planned products to Needed or finish checkout before adding more meals to a list with planned products already in the basket. Review marked amounts and use **Edit needed amount** to adjust what to buy. Add other groceries using **Add grocery item**.

Plans and shopping lists are private to the signed-in account and saved on the server for access on other devices. Sharing a recipe with a household is an explicit separate choice. A network connection is required; private lists and photos are not cached by the service worker.

## Shop and confirm purchases

Open the list on a phone. Use **Scan actual product** beside a needed ingredient, or **Scan / find an item in store**. The rear-camera scanner, barcode-photo decoder and typed barcode lookup are supported. Confirm the correct database result and review the actual amount, inventory unit, package size and storage location. If a scanned product exactly matches a single needed line, the global scanner reuses that line. Otherwise it adds a separate basket entry.

The workflow is **Needed → In basket → Purchased**. Scanning or marking a product In basket never changes home inventory. After paying at the store, select the purchased basket lines, open checkout review, tick the purchase affirmation and choose **Confirm purchased and add to inventory**. This records a purchase; it does not process a payment.

The server validates and commits all selected purchases in one transaction, merges matching product/location/unit entries and records household activity. Repeating or concurrently retrying the same completed purchase does not add it twice. Generic ingredient links are carried into purchased inventory so an exact packaged product can satisfy the recipe's generic ingredient later. A package such as one 500 g bag remains one bag unless its inventory amount is entered as 500 g; package conversion is intentionally reviewed by the user.

## Release verification

Active release: `/opt/pantry-portal/releases/20261020T174843Z-0.10-kitchen-nav`. The static navigation follow-up uses the same 0.10.0 application code and wraps the expanded desktop menu.

Private backup: `/var/backups/pantry-portal/kitchen-20261020T174250Z`.

35 Python tests passed locally and in isolated databases on the production host; six JavaScript tests passed. Checks include ingredient validation and access, step-photo ownership and retention, stale edits, meal scaling, unit conversions, ambiguous packages, separate meal batches, shopping-list privacy, atomic checkout and concurrent retry safety. A generic-to-barcoded-product purchase retained its ingredient link after an inventory edit.

An isolated browser walkthrough created and saved a recipe, planned a meal, generated a list, staged a basket item and completed purchase confirmation. The explicit purchase checkbox was required. Public ingredient search returned actual TheMealDB records. A synthetic EAN-13 barcode image decoded to its expected digits. At a 390-pixel viewport, the shopping page had no horizontal overflow. Physical phone camera focus and real supermarket conditions have not been tested.

Deployment checksums and before/after hashes of every pre-existing table matched. The protected main administrator remained unchanged. No local QA recipe, list, account or purchase was imported into production. Existing services are active, public health reports 0.10.0, new assets return 200, anonymous kitchen API routes return 401, and private source/catalog files return 404.
