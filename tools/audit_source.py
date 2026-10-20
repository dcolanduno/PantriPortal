"""Check the staged source tree without displaying suspected secret values."""
import io,re,subprocess,sys,zipfile
from pathlib import PurePosixPath

def git(*args):return subprocess.check_output(['git',*args])
def audit():
 paths=[p.decode('utf-8') for p in git('ls-files','-z').split(b'\0') if p]
 rules={
  'private key':rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----',
  'GitHub token':rb'(?:gh[pousr]_[A-Za-z0-9_]{25,}|github_pat_[A-Za-z0-9_]{25,})',
  'provider key':rb'\bsk-(?:proj-)?[A-Za-z0-9_-]{30,}',
  'AWS access key':rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
  'credential in URL':rb'https?://[^\s/<>:"\x27]+:[^\s/@<>"\x27]+@',
 }
 forbidden={'work','history','archives','conversations','consolidation','outputs','__pycache__','.venv','venv','node_modules','backups','runtime'}
 findings=[];total=0
 for path in paths:
  parts=PurePosixPath(path).parts
  if forbidden.intersection(parts) or path.startswith('app/models/') or re.search(r'\.(sqlite3(?:-wal|-shm)?|db|pem|key|pfx|p12|log)$',path) or PurePosixPath(path).name in {'.env','admin-setup-token','audit-signing-key','audit-head'}:findings.append((path,'private runtime path'))
  data=git('show',':'+path);total+=len(data)
  if path.endswith('.docx'):
   with zipfile.ZipFile(io.BytesIO(data)) as z:data=b'\n'.join(z.read(n) for n in z.namelist() if n.endswith('.xml'))
  for name,pattern in rules.items():
   if re.search(pattern,data):findings.append((path,name))
 print('Reviewed',len(paths),'staged files,',total,'bytes.')
 for path,rule in findings:print(path+': '+rule)
 if findings:return 1
 print('No forbidden runtime files or recognized credential patterns found.')
 return 0
if __name__=='__main__':sys.exit(audit())
