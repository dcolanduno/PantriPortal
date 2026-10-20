# Third party notices

This import does not assign a new open-source license to the original PantriPortal application or branding. Third-party components and assets retain their own licenses and rights.

- `app/vendor/tesseract.min.js`: Tesseract.js 5.1.1, verified against its published jsDelivr distribution. Bundled notices are retained in `app/vendor/tesseract.min.js.LICENSE.txt`. [Source](https://github.com/naptha/tesseract.js).
- `app/vendor/zxing-browser.min.js`: @zxing/browser 0.1.5, verified against its published jsDelivr UMD distribution. License retained in `app/vendor/zxing-browser.LICENSE`. [Source](https://github.com/zxing-js/browser).
- Transformers.js, OCR workers/language data and ONNX browser components may download from configured public hosts. Models are separate downloads; see `docs/MODELS.md`.
- Food data comes from Open Food Facts and TheMealDB. Open Food Facts data uses ODbL and product photos use CC BY-SA; attribution and provider limitations are in the interface and kitchen documentation.
- Bundled image provenance is in `specifications/IMAGE-SOURCES.md` and `specifications/PRODUCT-IMAGE-SOURCES.md`. Product names, logos, packaging and source photos retain their owners' rights. A source link records provenance, not a transfer of rights.
- Python dependencies are recorded in `app/requirements*.txt`. The AI lock is an environment snapshot, not a guarantee for every platform or accelerator.
