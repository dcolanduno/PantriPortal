"""Build an immutable application ZIP directly from a pushed Git commit."""
import argparse,datetime,hashlib,io,json,subprocess,zipfile
from pathlib import Path,PurePosixPath

ROOT=Path(__file__).resolve().parents[1]
REPOSITORY='https://github.com/dcolanduno/PantriPortal.git'
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])

def build(ref,output):
 if git('status','--porcelain','--untracked-files=normal').strip():raise SystemExit('Commit and push the working tree before packaging a release.')
 sha=git('rev-parse','--verify',ref+'^{commit}').decode().strip()
 origin=git('remote','get-url','origin').decode().strip()
 if origin.rstrip('/') not in (REPOSITORY,REPOSITORY.removesuffix('.git'),'git@github.com:dcolanduno/PantriPortal.git'):raise SystemExit('Origin is not the designated PantriPortal repository.')
 git('fetch','--quiet','origin')
 if subprocess.run(['git','-C',str(ROOT),'merge-base','--is-ancestor',sha,'origin/main'],check=False).returncode:raise SystemExit('The release commit must already be pushed to origin/main.')
 archive=git('archive','--format=zip',sha,'app/');files={}
 with zipfile.ZipFile(io.BytesIO(archive)) as source:
  for entry in source.infolist():
   if entry.is_dir():continue
   path=PurePosixPath(entry.filename)
   if path.parts[0]!='app' or '..' in path.parts:raise SystemExit('Unexpected archive path.')
   name=PurePosixPath(*path.parts[1:]).as_posix()
   if path.parts[1] in ('models','media','runtime','__pycache__') or path.suffix in ('.sqlite3','.pem','.key'):raise SystemExit('Runtime files must not be included in an application release.')
   files[name]=source.read(entry)
 if 'server.py' not in files:raise SystemExit('The commit has no application server.')
 hashes={name:hashlib.sha256(data).hexdigest() for name,data in sorted(files.items())}
 metadata={'repository':REPOSITORY,'commit':sha,'built_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':hashes,
  'excluded':'Private runtime data, credentials, uploads, backups and separately installed model weights.'}
 files['release-source.json']=(json.dumps(metadata,indent=2)+'\n').encode()
 files['RELEASE-SHA256SUMS']=''.join(hashlib.sha256(data).hexdigest()+'  '+name+'\n' for name,data in sorted(files.items())).encode()
 output=output.resolve();output.parent.mkdir(parents=True,exist_ok=True)
 if output.exists():raise SystemExit('Output already exists; choose a new artifact path.')
 with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED) as dest:
  for name,data in sorted(files.items()):dest.writestr(name,data)
 print(json.dumps({'artifact':str(output),'commit':sha,'application_files':len(hashes),'sha256':hashlib.sha256(output.read_bytes()).hexdigest()}))

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--ref',default='HEAD');p.add_argument('--output',type=Path,required=True);args=p.parse_args();build(args.ref,args.output)
