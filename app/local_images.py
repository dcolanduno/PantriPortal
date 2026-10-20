"""Free local image generation. No hosted service, subscription or API key."""
import os, threading, hashlib
from pathlib import Path

MODEL = os.environ.get('PANTRY_IMAGE_MODEL', 'stabilityai/sd-turbo')
MODEL_CACHE = Path(os.environ.get('PANTRY_MODEL_CACHE', str(Path(__file__).resolve().parents[1]/'work/models')))
_lock = threading.Lock()
_pipe = None

def ready():
    import importlib.util
    source=Path(MODEL) if Path(MODEL).is_dir() else MODEL_CACHE/'sd-turbo'
    return bool(importlib.util.find_spec('torch') and importlib.util.find_spec('diffusers') and
                all((source/p).is_file() for p in ['model_index.json','text_encoder/model.fp16.safetensors','unet/diffusion_pytorch_model.fp16.safetensors','vae/diffusion_pytorch_model.fp16.safetensors']))

def _get_pipeline():
    global _pipe
    import torch
    from diffusers import DiffusionPipeline
    with _lock:
        if _pipe is None:
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            if device == 'cpu':torch.set_num_threads(max(1,min(4,os.cpu_count() or 1)))
            dtype=torch.float16 if device=='cuda' else torch.float32
            source=str(MODEL_CACHE/'sd-turbo') if MODEL=='stabilityai/sd-turbo' and (MODEL_CACHE/'sd-turbo/model_index.json').is_file() else MODEL
            pipe = DiffusionPipeline.from_pretrained(
                source, cache_dir=str(MODEL_CACHE), use_safetensors=True,
                local_files_only=Path(source).is_dir(),
                dtype=dtype,
                variant='fp16' if MODEL == 'stabilityai/sd-turbo' else None)
            pipe.to(device)
            if device=='cpu' and os.environ.get('PANTRY_IMAGE_QUANTIZE')=='1':
                # Reduce resident weights on small CPU servers; image choices remain generated locally.
                from torch.ao.quantization import quantize_dynamic
                for component in (pipe.text_encoder,pipe.unet):
                    quantize_dynamic(component,{torch.nn.Linear},dtype=torch.qint8,inplace=True)
                import gc
                gc.collect()
                if os.name=='posix':
                    import ctypes
                    trim=getattr(ctypes.CDLL(None),'malloc_trim',None)
                    if trim:trim(0)
            pipe.enable_attention_slicing()
            pipe.set_progress_bar_config(disable=True)
            _pipe=pipe
    return _pipe

def _render(prompt,seed):
    import torch
    pipe=_get_pipeline()
    with _lock:
        with torch.inference_mode():
            result = pipe(prompt,
                               num_inference_steps=1 if MODEL == 'stabilityai/sd-turbo' else 12,
                               guidance_scale=0.0 if MODEL == 'stabilityai/sd-turbo' else 7.0, width=512, height=512,
                               generator=torch.Generator('cpu').manual_seed(seed))
        if getattr(result, 'nsfw_content_detected', None) and any(result.nsfw_content_detected):
            raise ValueError('The illustration could not be generated. Try a simpler product description.')
        return result.images[0].convert('RGB')

def generate(item):
    # Use product type only; generic illustrations never imitate branded labels.
    description = ' '.join(str(item.get(k, '')) for k in ('name', 'food_type', 'category'))[:220]
    views=['front view, balanced studio lighting','three-quarter view, soft side lighting','slightly elevated view, natural soft lighting']
    view=views[item.get('_view',0)%len(views)]
    prompt = ('Product photograph of '+description+', '+view+', single item centered on a plain white background, '
              'generic unbranded packaging, studio lighting, simple clear shape, no writing, no logos')
    seed=item.get('_seed',int(hashlib.sha256(prompt.encode()).hexdigest()[:8], 16))
    return _render(prompt,seed)

def generate_recipe(recipe):
    name=str(recipe.get('name','prepared dish'))[:160]
    ingredients=', '.join(str(x)[:80] for x in recipe.get('ingredients',[])[:12])[:500]
    prompt=('Photorealistic editorial food illustration of '+name+' prepared and ready to eat'
            +(', made with '+ingredients if ingredients else '')
            +', one appetizing plated serving in a shallow ceramic bowl, close three-quarter view, soft natural window light, '
            'warm cream tabletop, crisp detailed ingredients, realistic cooked food, no hands, no writing, no logos, square composition')
    seed=int(hashlib.sha256((name+'|'+ingredients).encode()).hexdigest()[:8],16)
    return _render(prompt,seed)
