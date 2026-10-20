# PantriPortal administration

Version 0.9.1 is live at https://www.pantriportal.com/ as of October 20, 2026.

The existing `dcolanduno` account is the protected main administrator. Its immutable account ID is pinned in the database; it always receives every application permission, including future permissions. Application and database checks prevent deletion, renaming, disabling, demotion, removal of household approval or permission denial. The username is reserved against new registrations. Passwords and existing sessions are retained. The account is labeled **Main administrator** in Users and permissions, with access restrictions unavailable in its editor.

Sign in with an existing administrator account, refresh the page, then open **My dashboard** and **Your administration tools**, or **Administration** in the navigation. Assigned permissions determine which tools appear. Existing administrators retain their permissions; ordinary accounts do not gain administrator access.

The dashboard provides user and role management, fourteen configurable permissions, account suspension and session revocation, inventory and recipe editing, image checks and replacement, database information and private recovery backups, application diagnostics, recipe provider controls, searchable activity logs and an error reference. The last enabled full administrator cannot be disabled or demoted.

In Home inventory mode, items can be organized into personal care, household supplies, clothing and closets, tools and hardware, medicines and first aid, and other home items. Administrators with content management permission can create, rename, reorder or archive custom sections through **Home inventory sections**. Archiving retains existing items. Kitchen mode continues to focus on food and recipes.

**Activity and error logs** supports account, action, date, reference and error-code filtering. Click an error code to read its meaning and suggested checks. **Error reference and Word guide** searches the same catalog and downloads the administrator handbook. Logging begins with this release; it cannot reconstruct earlier activity. Logs omit passwords, session tokens, submitted form contents and URL query strings. Unexpected incident diagnostics record exception types and code locations without raw exception messages or variable values.

The audit sequence and private signed checkpoint detect record changes and tail removal. A host administrator controlling both database and signing key can defeat these protections. Logs are not automatically purged; plan disk monitoring, private retention and secure archives. CSV export is limited to 5,000 events per request.

Recipe connection controls enable or disable supported imports, store administrator notes and test public website availability. They do not establish third-party account OAuth or ongoing private recipe-library synchronization. Supported public recipe URLs and export imports remain available.

Private recovery archives include database, media and audit verification material. Recovery requires private server access and a maintenance window. Credentials and archives must remain private.

## Deployment evidence

Active release: `/opt/pantry-portal/releases/20261020T134250Z-0.9.1-primary-admin`.

The 0.9.1 protection fix passed 23 Python tests locally and on the server and six JavaScript tests. Private pre-change backup: `/var/backups/pantry-portal/primary-admin-20261020T134250Z`. Deployment verified that the intended owner role/configuration changes were the only changes to pre-existing non-audit records, and recorded the assignment in the signed audit log. The following 0.9 evidence describes the original administration release.

Private deployment backup: `/var/backups/pantry-portal/admin-20261019T230144Z`.

Validation: 22 Python tests passed locally and on the production host against isolated test databases; six JavaScript tests passed. Checksums matched. HTTPS health reports version 0.9.0. Application, transfer and Nginx services are active. New public assets return 200; anonymous administrator endpoints and guide downloads return 401; Python sources and the private error catalog return 404.

All pre-existing table records had identical hashes before and after activation, including seven users, eight sessions, twenty items and six media records. No QA account or fixture inventory was imported. Audit integrity passed after activation. The published Home dashboard and default sections were verified in an authenticated browser. Administrator workflows were verified in the isolated local browser fixture and automated tests; a full production browser walkthrough using an administrator account has not been performed.
