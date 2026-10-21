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

## Access and operations

The application only returns or modifies a cabinet, prescription, doctor or appointment for its signed-in owner. There is no household-member or application-administrator override for these personal records. Shared stock and private prescriptions use separate tables and routes. Owner IDs supplied by a client cannot transfer ownership. CSRF and origin checks apply to changes.

Medical names, directions, prescriber contacts, appointment details, request bodies and medicine record IDs are excluded from activity logs. The log records the account, operation, generic Medicine route, result status, error code and request reference. Diagnostic exceptions retain stack locations and error types, not submitted values. No public catalog or AI service receives private cabinet data.

Cabinets and records are kept in the private application database and included in private operational backups. This is application-level ownership protection: authorized host/database operators can access database files and recovery archives. Those files must remain private, outside Git and public exports. Application administrators cannot browse these personal tables through the content-management API.

The additive migration creates `medicine_cabinets` and `medicine_records`. It preserves all existing inventory and user records. The frontend asset is `/medicine.js`; deployment proxies must expose that static asset. Runtime requirements include pinned `tzdata` for consistent time zones on Windows and Linux. Rollback must preserve the new tables and later user records; never restore an older database over new medical entries merely to roll back code.
