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
