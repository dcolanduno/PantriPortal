# PantriPortal working agreement

The user has designated https://github.com/dcolanduno/PantriPortal.git as the source of truth for all future work.

- Work in this Git checkout. Fetch and inspect the upstream branch before changing code; preserve local work and do not reset or overwrite it.
- Implement and test changes here, then commit and push them. Do not leave a live feature that exists only in a local work directory or on the server.
- Deploy the exact tested, pushed commit. Use `tools/package_release.py` to build its application artifact from Git objects, rather than copying uncommitted working files.
- Record the repository URL, full commit SHA and application file hashes with each live release. Verify those hashes, the active release, health, services and affected behavior before calling a deployment complete.
- Keep production data, credentials, uploaded household photos, audit keys, backups and model weights outside Git. Mirroring means source and deployment parity, not copying private production data into development.
- Preserve originals and release history. Use a new release directory and reviewed rollback procedure; do not patch a running release in place.
- Preserve the protected main administrator and all existing user data. Follow `deployment/README.md` for backup, additive migration and verification requirements.
- GitHub's test workflow does not deploy the site. A source push is not evidence of deployment; report any gap between the pushed and active commits.

The source import inventory in `docs/source-files.sha256` describes the original import commit `9575a93c404c9c59e01c395583dad906d63dbe64`. It is historical. Each new deployable artifact has a current `release-source.json` and `RELEASE-SHA256SUMS` generated from its own Git commit.
