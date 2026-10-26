# Prescription label capture and OCR

Version 0.15.0 reads prescription photos locally in the browser. Images and full label text are never sent to a recognition service. NDC reference lookup remains explicit and sends only the chosen code.

## Curved bottles

Open Scan / photograph prescription bottle from Add prescription, Edit prescription, or the cabinet's Scan prescription label button. Use Open live phone camera or the native Take label photo option. Capture one readable face, turn the same bottle slightly and capture another face with overlapping text. Add another photo preserves reviewed fields and fills blanks. The scanner accepts up to eight readable views; start over before scanning a different bottle. A single view cannot reveal hidden text around the back or reconstruct characters lost to blur or glare.

Adjust label crop / rotate photo removes background and unreadable curved edges before recognition. The preview shows the crop. Four trim sliders and a 90-degree rotation control are available, followed by Read adjusted label. Original pixels are retained in memory up to 3600 pixels on the longest side; OCR crops have a white border and are rescaled within bounded dimensions. Three OCR passes use original layout, enhanced contrast and sparse text. A fourth pass approximates cylindrical horizontal distortion; it can be disabled for flat paperwork. The original passes remain available because no assumed curvature fits every bottle.

Readable lines are filtered by per-line OCR confidence rather than rejecting every line when a whole-image score is low. Separate views and passes contribute missing structured fields. Conflicting readings are explicitly named for review. Existing form values, including user corrections, are not overwritten by another view. Medication names, numbers, strength and directions are not guessed or spelling-corrected against a drug list. Review the actual label and confirm before handing the draft to the cabinet form; saving there remains separate.

Live camera uses HTTPS/browser permission, prefers the rear camera and requests continuous autofocus when supported. Capture is deliberate, not a background video recording. Camera tracks stop on Stop camera, cancellation, account changes and dialog close. Photos, crops, recognized text and candidates are cleared on start over/close/account changes. No new dependency or server storage is added. Native photo/file selection remains available when a browser cannot open a live stream.

## Validation limits

Desktop synthetic-label OCR, angled front/side views, field preservation, conflicts and cancellation can be tested automatically/in a browser. They do not prove focus performance on a particular phone or accuracy on a real curved prescription bottle. A real phone test remains necessary; do not describe this as guaranteed recognition of every field. If information is not printed or legible, it remains blank for review.

Recognition guidance: https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html and https://github.com/naptha/tesseract.js/blob/master/docs/api.md .
