"""Download the public quantized CLIP model for private browser inference."""
import urllib.request,json,hashlib,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
BASE='https://modelscope.cn';MODEL='Xenova/clip-vit-base-patch32'
ROOT=Path(__file__).resolve().parents[1]/'app/models'/MODEL
with urllib.request.urlopen(BASE+'/api/v1/models/'+MODEL+'/repo/files?Revision=master&Recursive=true',timeout=30) as r:meta=json.load(r)
files=[f for f in meta['Data']['Files'] if f.get('Type')!='tree' and (f['Path'].endswith(('.json','.txt','.md')) or f['Path']=='onnx/model_quantized.onnx')]
def get(f):
 dest=ROOT/f['Path'];dest.parent.mkdir(parents=True,exist_ok=True)
 expected=f['Sha256']
 if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest()==expected:return
 tmp=dest.with_suffix(dest.suffix+'.partial')
 for attempt in range(3):
  try:
   with urllib.request.urlopen(BASE+'/models/'+MODEL+'/resolve/master/'+f['Path'],timeout=90) as r,tmp.open('wb') as out:
    while chunk:=r.read(1024*1024):out.write(chunk)
   if hashlib.sha256(tmp.read_bytes()).hexdigest()!=expected:raise ValueError('Checksum mismatch')
   tmp.replace(dest);print('Verified',f['Path'],dest.stat().st_size,flush=True);return
  except Exception:
   if attempt==2:raise
   time.sleep(2)
with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(get,files))
(ROOT/'download-provenance.json').write_text(json.dumps({'repository':BASE+'/models/'+MODEL,'files':files},indent=2))
print('Recognition model ready.',flush=True)
