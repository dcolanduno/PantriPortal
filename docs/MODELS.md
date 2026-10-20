# Model files

Model weights are separate downloads rather than Git files. They are large third-party dependencies with their own licenses. Neither models nor production data are needed to run the isolated tests.

## Browser recognition

Run `tools/setup_recognition_model.py` from the Python environment. It obtains the quantized `Xenova/clip-vit-base-patch32` model, tokenizer and configuration from ModelScope's public mirror, verifies supplied SHA-256 values and writes `app/models/Xenova/clip-vit-base-patch32/`. The frontend uses Transformers.js 3.8.1 with local models enabled and remote models disabled. The backend/proxy must serve the explicit model paths. `docs/model-files.json` records the recognition files present at source-import time; it contains public provenance, not credentials. Older MobileViT configuration files remain preserved locally but are not used by the current CLIP matcher.

## Local image generation

Install `app/requirements-ai.txt` and run `tools/setup_image_model.py`. It downloads SD-Turbo configuration and FP16 safetensors from the `AI-ModelScope/sd-turbo` public mirror and verifies upstream checksums. The default cache is `work/models/sd-turbo/`; no hosted image API key is required.

`PANTRY_MODEL_CACHE` selects another cache. `PANTRY_IMAGE_MODEL` selects an existing model directory or alternate model identifier. `PANTRY_IMAGE_QUANTIZE=1` enables CPU linear-layer quantization used by the existing production host. Loading models needs substantial memory/disk space and is separate from the basic application and tests.

Review upstream model cards and licenses: [SD-Turbo](https://huggingface.co/stabilityai/sd-turbo), [CLIP](https://huggingface.co/openai/clip-vit-base-patch32), [Transformers.js conversion](https://huggingface.co/Xenova/clip-vit-base-patch32). Generated illustrations remain labeled and replaceable with real product photos.
