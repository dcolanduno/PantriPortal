# PantriPortal

Kitchen and home inventory, recipes, meal planning and grocery shopping, with household accounts and permission-controlled administration.

The current application version is **0.15.10**. The production site is [www.pantriportal.com](https://www.pantriportal.com/). This repository contains the maintained source, assets, tests, setup tools and documentation. Pushing to GitHub does not automatically deploy the website.

This GitHub repository is the source of truth for development and production. Changes are tested, committed and pushed before deploying the matching Git commit. Release artifacts record that commit and file hashes; see [deployment workflow](deployment/README.md) and [working agreement](AGENTS.md).

## Features

- Search-as-you-type doctor contacts (NIH/CMS, plus optional configured Google Maps), medication names/strengths (NIH RxTerms), and a product-label reader for uses, side effects and warnings (openFDA).
- Saved doctor cards include free office map previews, a full Google Maps link and directions.
- Medicine area with owner-only personal cabinets, prescriptions and refill details, doctor contacts, appointments with time zones, and household pharmacy supplies linked to Home inventory. See [Medicine guide and access boundaries](docs/MEDICINE.md).
- Compact navigation: Home, Organize (Inventory, Recipes and Locations), Plan & shop, and Account. Administration appears under Account only for users with administrative permissions. Home inventory mode hides the kitchen recipe link. Menus support keyboard Escape, outside-click dismissal and mobile layouts.
- Kitchen and Home inventory modes, storage locations, quantities and custom Home sections.
- Barcode scanning, package text recognition and browser photo matching.
- Product photos, uploads and three locally generated alternative image choices.
- Household accounts, approved membership and private or household recipes.
- Guided recipes with ingredient references, amounts, ordered instructions and optional step photos.
- Meal plans, serving adjustments, grocery requirements and multiple shopping lists.
- Pending store baskets and explicit purchase confirmation before inventory changes, with repeat-safe checkout.
- Administrator permissions, diagnostics, private backups, searchable audit/error logs and a Word error guide.
- Protected main administrator identity for the existing dcolanduno account.

## Run locally

Use Python 3.12 or newer. From the repository root on Windows:

```powershell
python -m venv work/venv
work/venv/Scripts/python.exe -m pip install -r app/requirements.txt
$env:PANTRY_DEV = '1'
work/venv/Scripts/python.exe app/server.py
```

On Linux or macOS:

```sh
python3 -m venv work/venv
work/venv/bin/python -m pip install -r app/requirements.txt
PANTRY_DEV=1 work/venv/bin/python app/server.py
```

Open [127.0.0.1:8767](http://127.0.0.1:8767/). The server binds to loopback. The PowerShell convenience launcher `Start-Pantry-Local.ps1` also works; it installs the larger AI dependency set when creating a new environment.

A fresh database and private media directory are created under `work/runtime/`. After starting the server, run `tools/open_local_admin.py` with the same Python environment to open the private first-administrator setup link without printing its token. Production data, passwords and sessions are not included. The reserved main administrator name is not a public signup mechanism; see [administration](ADMINISTRATION.md) and [deployment](deployment/README.md).

## Optional AI and recognition models

For local image generation, install `app/requirements-ai.txt`, then run `tools/setup_image_model.py`. For browser object recognition, run `tools/setup_recognition_model.py`. Both scripts use the repository's Python environment, download public model files and verify upstream checksums. Model weights, virtual environments and caches are excluded from Git.

Basic inventory, recipe planning and shopping work without generation weights. Camera features require a supported browser and secure origin. See [model setup](docs/MODELS.md) and [third-party notices](THIRD_PARTY_NOTICES.md).

## Tests

Run from the repository root using the configured Python environment and Node.js:

```sh
python -m pip install -r app/requirements.txt
python -m unittest discover -s tests -p 'test*.py'
node --test tests/*.test.cjs
```

Tests use isolated temporary databases and mock image generation. They do not require model weights or production credentials. The current application passed 74 Python tests and 20 JavaScript tests. Physical phone cameras and real-store conditions remain separate validation tasks. GitHub Actions runs the tests without deploying the site.

## Project files

- `app/`: Python/SQLite backend, frontend, public assets and protected administrator error handbook.
- `tests/`: inventory, account, administrator, recipe, planning and purchase checks.
- `tools/`: model setup, local administrator setup and error-handbook generation.
- `deployment/`: example Nginx/systemd configuration and a manual release runbook.
- `specifications/`: original requirements and image provenance; specifications can describe work beyond the implemented release.
- [KITCHEN_COMPANION.md](KITCHEN_COMPANION.md): recipe, planning and shopping usage and limitations.
- [ADMINISTRATION.md](ADMINISTRATION.md): permissions, audit tools and recovery.
- [DEVELOPMENT.md](DEVELOPMENT.md) and [VALIDATION.md](VALIDATION.md): implementation and dated release evidence.
- [Repository import](docs/REPOSITORY_IMPORT.md): included and excluded material.

Historical snapshots, archives, conversations, private databases, uploaded household photos and local operational work remain preserved outside version control. Publishing source does not change live services or upload household data.
