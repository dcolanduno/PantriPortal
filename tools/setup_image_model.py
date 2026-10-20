"""Recover public SD-Turbo safetensors from ModelScope's model mirror.
No prompts or user photos are transmitted by this installer.
"""
import urllib.request,json,hashlib,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
BASE='https://modelscope.cn'
MODEL='AI-ModelScope/sd-turbo'
ROOT=Path(__file__).resolve().parents[1]/'work/models/sd-turbo'
with urllib.request.urlopen(BASE+'/api/v1/models/'+MODEL+'/repo/files?Revision=master&Recursive=true',timeout=30) as r:meta=json.load(r)
files=meta['Data']['Files']
wanted=[]
for f in files:
 name=f['Path']
 if f.get('Type')=='tree':continue
 if name.endswith(('.json','.txt','.md')) or name in ('text_encoder/model.fp16.safetensors','unet/diffusion_pytorch_model.fp16.safetensors','vae/diffusion_pytorch_model.fp16.safetensors'):
  wanted.append(f)
def get(f):
 name=f['Path'];dest=ROOT/name;dest.parent.mkdir(parents=True,exist_ok=True)
 expected=f.get('Sha256') or f.get('SHA256')
 if dest.exists() and dest.stat().st_size==f.get('Size'):
  if not expected or hashlib.sha256(dest.read_bytes()).hexdigest()==expected:return
 tmp=dest.with_suffix(dest.suffix+'.partial')
 for attempt in range(3):
  try:
   with urllib.request.urlopen(BASE+'/models/'+MODEL+'/resolve/master/'+name,timeout=90) as r,tmp.open('wb') as out:
    while chunk:=r.read(1024*1024):out.write(chunk)
   if expected and hashlib.sha256(tmp.read_bytes()).hexdigest()!=expected:raise ValueError('Checksum mismatch')
   if f.get('Size') and tmp.stat().st_size!=f['Size']:raise ValueError('Size mismatch')
   tmp.replace(dest);print('Verified',name,dest.stat().st_size,flush=True);return
  except Exception:
   if attempt==2:raise
   time.sleep(2)
with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(get,wanted))
(ROOT/'download-provenance.json').write_text(json.dumps({'repository':BASE+'/models/'+MODEL,'files':wanted},indent=2))
print('Model downloaded and verified.',flush=True)
