# Prescription label capture and OCR

Version 0.15.2 opens the rear camera as soon as the signed-in user starts a label scan. OCR keeps sampling the live camera while it is open, so the user can hold one panel steady and slowly turn the bottle to read the next side without taking a separate photo for each view. The same local OCR reads uploaded or camera photos when live access is unavailable. Images and full label text stay in the browser; NDC reference lookup remains explicit and sends only the chosen code.

## Curved bottles

Open Live-scan prescription bottle from Add prescription, Edit prescription, or Scan prescription label from the cabinet. The rear camera opens first where browser permissions allow it. Hold one readable face steady in the view; OCR runs repeatedly and adds new lines as the bottle turns. The scanner accepts up to eight distinct views; start over before scanning a different bottle. A single view cannot reveal hidden text around the back or reconstruct characters lost to blur or glare. If camera access is unavailable, use the photo choices instead.

Adjust label crop / rotate photo removes background and unreadable curved edges before recognition. The preview shows the crop. Four trim sliders and a 90-degree rotation control are available, followed by Read adjusted label. Original pixels are retained in memory up to 3600 pixels on the longest side; OCR crops have a white border and are rescaled within bounded dimensions. Photo scans try original layout, enhanced contrast, sparse text, thresholded contrast and optional cylindrical correction. Live scans use the faster enhanced and thresholded passes plus optional cylindrical correction. The original passes remain available because no assumed curvature fits every bottle.

Readable lines are filtered by per-line OCR confidence and agreement between image passes rather than accepting every plausible-looking character string. Repeated frames are deduplicated; separate views contribute missing structured fields. Conflicting readings are explicitly named for review. Existing form values, including user corrections, are not overwritten by another view. Medication names, numbers, strength and directions are not guessed or spelling-corrected against a drug list. Review the actual label and confirm before handing the draft to the cabinet form; saving there remains separate.

Live camera uses HTTPS/browser permission, prefers the rear camera and requests continuous autofocus when supported. It samples frames locally while the dialog is open; nothing is recorded or uploaded. OCR workers are reused during the scan to avoid reloading recognition for every frame. Camera tracks stop on Stop camera, cancellation, account changes and dialog close. Photos, crops, recognized text and candidates are cleared on start over/close/account changes. A thresholded image pass supplements contrast and curved-label passes. No new dependency or server storage is added.

## Validation limits

Desktop synthetic-label OCR, angled front/side views, field preservation, conflicts and cancellation can be tested automatically/in a browser. They do not prove focus performance on a particular phone or accuracy on a real curved prescription bottle. A real phone test remains necessary; do not describe this as guaranteed recognition of every field. If information is not printed or legible, it remains blank for review.

Recognition guidance: https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html and https://github.com/naptha/tesseract.js/blob/master/docs/api.md .
