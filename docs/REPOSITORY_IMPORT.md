# Repository import

Destination: https://github.com/dcolanduno/PantriPortal

The repository was empty when inspected. The maintained application, public assets, vendor notices, setup tools, tests, operating guides, deployment examples and product specifications are included. This publishes source; it does not move or restart the live site.

## Preserved locally and excluded

- `history/`, `archives/`, `conversations/`, `consolidation/`: original snapshots, archives, conversation exports and ledgers. These duplicate/predate the active source and may contain private operational context.
- `work/`: databases, uploads, administrator tokens, audit verification keys, model caches, virtual environments, backups, renderers, QA data and host-specific historical deployment scripts.
- `outputs/`: working deliverables and screenshots, including account views; source documentation is included separately.
- `app/models/`: downloaded recognition weights and generated metadata. Setup scripts and a checksum manifest document restoration.
- Python caches, environment files, credentials, private keys and transient files.

No original archive, conversation, private database or uploaded media is deleted. The former root README is preserved locally as `consolidation/README-before-github-import.md`. Historical release evidence remains dated in DEVELOPMENT.md and VALIDATION.md. Specifications describe requested scope, not proof of implementation.

`docs/source-files.sha256` inventories the initial imported files, excluding that manifest itself. Git records the complete tree and commit ID. Future edits should use normal commits and keep private runtime data excluded.

Before publication, all 121 inventoried files matched their canonical Git hashes in an extracted clean checkout. A fresh Python environment containing only Pillow passed all 35 backend tests in that checkout, and all six JavaScript tests passed. The clean-checkout test harness creates its ignored `work/` directory automatically. A staged-file audit checked private runtime paths and recognized credential patterns, including the text inside the Word guide; no findings were detected. This audit is a publication check, not a guarantee against every possible secret format.
