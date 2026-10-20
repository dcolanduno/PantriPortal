"""Permission-scoped administration and private, tamper-evident operational records."""
import csv,hashlib,hmac,io,json,os,re,secrets,shutil,sqlite3,tarfile,threading,time,types
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PERMISSIONS={
 'health.read':'Run application diagnostics','database.read':'Read database statistics',
 'database.backup':'Create private recovery backups','users.read':'View all accounts',
 'users.manage':'Edit accounts and revoke sessions','roles.manage':'Manage roles and permissions',
 'audit.read':'Search activity and errors','audit.export':'Export audit records',
 'integrations.read':'Review recipe connections','integrations.manage':'Configure recipe connections',
 'content.read':'Review inventory and recipes','content.manage':'Edit inventory and recipes',
 'images.manage':'Manage product and recipe images','maintenance.manage':'Maintain caches and logging'}
DEFAULTS={'admin':set(PERMISSIONS),'author':set(),'user':set()}
FAMILIES={
 400:('PP-VALIDATION','Check the submitted information','A field or request format was rejected.','Review required fields, allowed lengths and supported file formats. Retry with corrected information.'),
 401:('PP-SIGNIN','Sign in again','The request has no valid signed-in session.','Sign in again. Check that the browser accepts cookies and the account is active.'),
 403:('PP-ACCESS','Access was not accepted','The account lacks permission, or the request security checks failed.','Check the assigned role and permissions. Refresh the page. Confirm the correct HTTPS domain and request origin.'),
 404:('PP-NOTFOUND','Record or route not found','The requested resource is missing or is outside the account scope.','Refresh the list, verify the record still exists, and check the deployment asset routes. Do not bypass ownership checks.'),
 405:('PP-METHOD','Request method not supported','This operation does not support that request method.','Refresh to the current application build and check the route and HTTP method.'),
 413:('PP-SIZE','This upload is too large','A file, archive entry or expanded import exceeded its size limit.','Use a smaller supported export or divide it into batches. Do not disable archive expansion limits.'),
 422:('PP-IMPORT','The recipe cannot be imported','The public page or export does not contain supported structured recipe information.','Use a supported export file, paste the recipe details, or choose a public page with structured Recipe data. Private account collections cannot be imported by URL.'),
 409:('PP-CONFLICT','The change conflicts with current data','A duplicate, concurrent change, active job, or last-administrator protection prevented this change.','Refresh current data. Resolve duplicates or wait for the active job. Keep at least one enabled administrator with full permissions.'),
 429:('PP-LIMIT','Please wait before retrying','A request, provider, or generation capacity limit was reached.','Wait for the limit to reset or queued work to finish. Check provider quotas. Avoid repeated automatic retries.'),
 500:('PP-INTERNAL','The service could not finish','An unexpected internal failure occurred.','Use the request reference to find the audit event. Run diagnostics and inspect private service logs. Verify disk space, permissions and recent release changes.'),
 502:('PP-PROVIDER','An external service is unavailable','A catalog or recipe service did not return a usable response.','Check provider availability, quotas and supported import methods. Retry later or use manual entry.'),
 503:('PP-UNAVAILABLE','A required component is unavailable','A required model, database or runtime component is unavailable.','Run diagnostics. Check the installed dependencies, verified model files, data permissions and available memory.'),
}
SPECIAL={
 'PP-IMAGE':{'status':503,'message':'The local image generator is unavailable.','meaning':'The image job failed; existing saved images remain unchanged.','checks':'Check model readiness, available RAM and swap, dependency versions and the private service log. Retry the job after fixing the cause.'},
 'PP-CLIENT':{'status':0,'message':'A browser operation failed.','meaning':'The signed-in browser reported a script or unhandled-promise error.','checks':'Refresh the current build. Check asset availability, browser compatibility and connectivity. Use the request reference; no form contents are recorded.'},
 'PP-HEALTH':{'status':503,'message':'An application diagnostic check failed.','meaning':'One or more application components did not pass diagnostics.','checks':'Open Diagnostics for component results. Check database integrity, free disk space, assets, image-model readiness and audit-log integrity.'},
 'PP-AUDIT':{'status':500,'message':'Audit integrity verification failed.','meaning':'A signed audit record or its sequence does not match the stored chain.','checks':'Preserve the database and private audit key. Restrict administrative changes and investigate private backups and host access. Do not edit the audit rows to conceal a mismatch.'},
}
_api=None;_key=None;_audit_failed=False
_catalog=None
_anonymous_windows={};_suppressed=0;_sample_lock=threading.Lock()
_checkpoint_lock=threading.Lock()
HOME_SECTIONS=[
 ('personal-care','Personal care','Soap, shampoo, lotion, fragrance and bathroom supplies','🧴'),
 ('cleaning-supplies','Household supplies','Cleaners, laundry products, paper goods and daily supplies','🧹'),
 ('clothing-closet','Clothing and closets','Clothing, shoes, accessories and stored seasonal items','👕'),
 ('tools-hardware','Tools and hardware','Tools, screws, nails, fasteners, glue and tape','🛠'),
 ('medicines-first-aid','Medicines and first aid','Medication inventory and first aid supplies','🩹'),
 ('other-home','Other home items','Furniture, electronics, valuables and other possessions','🏠')]

def catalog():
 global _catalog
 if _catalog is None:
  _catalog={v[0]:{'code':v[0],'status':k,'message':v[1],'meaning':v[2],'checks':v[3]} for k,v in FAMILIES.items()}
  _catalog.update({k:dict(v,code=k) for k,v in SPECIAL.items()})
  path=ROOT/'error_catalog.json'
  if path.exists():_catalog.update({x['code']:x for x in json.loads(path.read_text(encoding='utf-8'))})
 return _catalog

def error_code(status,message):
 for code,entry in catalog().items():
  if entry.get('template') and entry['status']==status:
   parts=re.split(r'(\{detail\})',entry['template'])
   pattern=''.join('.+?' if p=='{detail}' else re.escape(p) for p in parts)
   if re.fullmatch(pattern,message):return code
 return FAMILIES.get(status,FAMILIES[500])[0]

def initialize(namespace):
 global _api,_key
 _api=types.SimpleNamespace(**namespace)
 with _api.db() as c:
  if 'disabled' not in {x['name'] for x in c.execute('PRAGMA table_info(users)')}:c.execute('ALTER TABLE users ADD COLUMN disabled INTEGER NOT NULL DEFAULT 0')
  c.executescript('''
CREATE TABLE IF NOT EXISTS admin_permissions(user_id TEXT PRIMARY KEY REFERENCES users(id),allow_json TEXT NOT NULL,deny_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit_events(id INTEGER PRIMARY KEY AUTOINCREMENT,created REAL NOT NULL,actor_id TEXT,actor TEXT,method TEXT,route TEXT,action TEXT,target TEXT,status INTEGER,error_code TEXT,request_id TEXT,duration_ms INTEGER,message TEXT,previous_hash TEXT,digest TEXT);
CREATE INDEX IF NOT EXISTS audit_created ON audit_events(created DESC,id DESC);
CREATE INDEX IF NOT EXISTS audit_actor ON audit_events(actor_id,created DESC);
CREATE INDEX IF NOT EXISTS audit_error ON audit_events(error_code,created DESC);
CREATE TABLE IF NOT EXISTS integration_settings(provider TEXT PRIMARY KEY,body TEXT NOT NULL,updated REAL NOT NULL);
CREATE TABLE IF NOT EXISTS error_occurrences(reference TEXT PRIMARY KEY,error_class TEXT NOT NULL,frames TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS home_sections(id TEXT PRIMARY KEY,name TEXT NOT NULL COLLATE NOCASE UNIQUE,description TEXT NOT NULL,icon TEXT NOT NULL,position INTEGER NOT NULL,archived INTEGER NOT NULL DEFAULT 0);
''')
  for position,(sid,name,description,icon) in enumerate(HOME_SECTIONS):c.execute('INSERT OR IGNORE INTO home_sections VALUES(?,?,?,?,?,0)',(sid,name,description,icon,position))
  # Pin the existing owner by immutable account ID, never by a supplied login name.
  primary=c.execute("SELECT value FROM config WHERE key='primary_admin_id'").fetchone()
  if not primary:
   owners=c.execute("SELECT id FROM users WHERE name='dcolanduno' COLLATE NOCASE").fetchall()
   if len(owners)>1:raise RuntimeError('Ambiguous primary administrator identity')
   if owners:
    owner=owners[0]['id']
    c.execute("UPDATE users SET role='admin',disabled=0,approved=1,home_role='admin' WHERE id=?",(owner,))
    c.execute('DELETE FROM admin_permissions WHERE user_id=?',(owner,))
    c.execute("INSERT INTO config(key,value) VALUES('primary_admin_id',?)",(owner,))
  c.executescript('''
CREATE TRIGGER IF NOT EXISTS primary_admin_no_delete BEFORE DELETE ON users
WHEN OLD.id=(SELECT value FROM config WHERE key='primary_admin_id')
BEGIN SELECT RAISE(ABORT,'The main administrator cannot be deleted'); END;
CREATE TRIGGER IF NOT EXISTS primary_admin_no_restrict BEFORE UPDATE ON users
WHEN OLD.id=(SELECT value FROM config WHERE key='primary_admin_id')
AND (NEW.id IS NOT OLD.id OR NEW.name IS NOT OLD.name OR NEW.role IS NOT 'admin' OR NEW.disabled IS NOT 0 OR NEW.approved IS NOT 1 OR NEW.home_role IS NOT 'admin')
BEGIN SELECT RAISE(ABORT,'The main administrator must retain full access'); END;
CREATE TRIGGER IF NOT EXISTS primary_admin_pin_no_delete BEFORE DELETE ON config
WHEN OLD.key='primary_admin_id'
BEGIN SELECT RAISE(ABORT,'The main administrator identity is protected'); END;
CREATE TRIGGER IF NOT EXISTS primary_admin_pin_no_change BEFORE UPDATE ON config
WHEN OLD.key='primary_admin_id' AND (NEW.key IS NOT OLD.key OR NEW.value IS NOT OLD.value)
BEGIN SELECT RAISE(ABORT,'The main administrator identity is protected'); END;
''')
 keyfile=_api.DATA/'audit-signing-key'
 try:
  with keyfile.open('xb') as f:f.write(secrets.token_bytes(32))
 except FileExistsError:pass
 keyfile.chmod(0o600);_key=keyfile.read_bytes()
 if len(_key)!=32:raise RuntimeError('Audit signing key must contain 32 bytes.')

def permissions(user,c=None):
 if not user:return set()
 own=c is None
 if own:c=_api.db()
 try:
  if primary_admin(user,c):return set(PERMISSIONS)
  row=c.execute('SELECT allow_json,deny_json FROM admin_permissions WHERE user_id=?',(user['user_id'] if 'user_id' in user.keys() else user['id'],)).fetchone()
  result=set(DEFAULTS.get(user['role'],set()))
  if row:result.update(json.loads(row['allow_json']));result.difference_update(json.loads(row['deny_json']))
  return result&set(PERMISSIONS)
 finally:
  if own:c.close()

def primary_admin(user,c=None):
 if not user:return False
 own=c is None
 if own:c=_api.db()
 try:
  row=c.execute("SELECT value FROM config WHERE key='primary_admin_id'").fetchone()
  return bool(row and row['value']==user['user_id' if 'user_id' in user.keys() else 'id'])
 finally:
  if own:c.close()

def require(user,permission):
 if permission not in permissions(user):raise _api.Problem(403,'This account does not have the required administrator permission.')

def full_admin(user,c=None):return user['role']=='admin' and permissions(user,c)==set(PERMISSIONS)

def image_owner_allowed(user,owner):
 with _api.db() as c:row=c.execute('SELECT home_id FROM users WHERE id=?',(owner,)).fetchone()
 return bool(row and (row['home_id']==user['home_id'] or 'images.manage' in permissions(user)))

def safe_text(value):
 text=str(value or '')[:1200]
 text=re.sub(r'https?://\S+','[URL omitted]',text)
 text=re.sub(r'(?i)(password|token|secret|cookie|authorization|csrf|join_code)\s*[:=]\s*[^\s,;]+',r'\1=[redacted]',text)
 return ''.join(ch for ch in text if ch=='\n' or ord(ch)>=32)[:600]

def route_name(path):
 path=path.split('?',1)[0]
 return re.sub(r'(?<=/)[a-f0-9]{24,64}(?=/|\.|$)',':id',path)[:160]

def should_log(actor,path,status,source):
 global _suppressed
 if actor:return True
 if status<400 and path in ('/api/health','/api/features','/api/me'):return False
 # Bound unauthenticated error floods without putting network addresses in the log.
 key=hmac.new(_key,str(source).encode(),hashlib.sha256).hexdigest()[:16]+':'+route_name(path)+':'+str(status)
 with _sample_lock:
  minute=int(time.time()/60)
  if len(_anonymous_windows)>5000:_anonymous_windows.clear()
  old,count=_anonymous_windows.get(key,(minute,0));count=count+1 if old==minute else 1;_anonymous_windows[key]=(minute,count)
  if count>30:_suppressed+=1;return False
 return True

def append_event(actor=None,method='',route='',action='',target='',status=200,code='',reference='',duration=0,message='',c=None):
 global _audit_failed
 if not _api:return
 data=[round(time.time(),3),actor['user_id'] if actor and 'user_id' in actor.keys() else '',actor['name'] if actor else 'Anonymous',method,route_name(route),action[:80],str(target)[:80],int(status),code,reference[:32],int(duration),safe_text(message)]
 own=c is None
 try:
  if own:c=_api.db();c.execute('BEGIN IMMEDIATE')
  previous=c.execute('SELECT digest FROM audit_events ORDER BY id DESC LIMIT 1').fetchone()
  previous=previous['digest'] if previous else ''
  digest=hmac.new(_key,(previous+json.dumps(data,separators=(',',':'),ensure_ascii=True)).encode(),hashlib.sha256).hexdigest()
  c.execute('INSERT INTO audit_events(created,actor_id,actor,method,route,action,target,status,error_code,request_id,duration_ms,message,previous_hash,digest) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(*data,previous,digest))
  if own:
   c.commit();checkpoint()
 except Exception:
  _audit_failed=True
  if own and c:c.rollback()
  if not own:raise
 finally:
  if own and c:c.close()

def checkpoint():
 # A private host checkpoint also detects removal of a completed request's tail records.
 with _checkpoint_lock:
  with _api.db() as c:row=c.execute('SELECT id,digest FROM audit_events ORDER BY id DESC LIMIT 1').fetchone()
  if not row:return
  payload={'id':row['id'],'digest':row['digest']}
  payload['signature']=hmac.new(_key,json.dumps(payload,sort_keys=True).encode(),hashlib.sha256).hexdigest()
  dest=_api.DATA/'audit-head';temp=_api.DATA/'audit-head.pending'
  temp.write_text(json.dumps(payload),encoding='utf-8');temp.chmod(0o600);temp.replace(dest)

def verify_audit():
 previous='';checked=0
 with _api.db() as c:
  c.execute('BEGIN IMMEDIATE')
  for r in c.execute('SELECT * FROM audit_events ORDER BY id'):
   values=[r[k] for k in ['created','actor_id','actor','method','route','action','target','status','error_code','request_id','duration_ms','message']]
   digest=hmac.new(_key,(previous+json.dumps(values,separators=(',',':'),ensure_ascii=True)).encode(),hashlib.sha256).hexdigest()
   if r['previous_hash']!=previous or not hmac.compare_digest(r['digest'],digest):return {'ok':False,'checked':checked,'first_bad_id':r['id']}
   previous=r['digest'];checked+=1
  path=_api.DATA/'audit-head'
  if path.exists():
   try:
    payload=json.loads(path.read_text(encoding='utf-8'));signature=payload.pop('signature');expected=hmac.new(_key,json.dumps(payload,sort_keys=True).encode(),hashlib.sha256).hexdigest()
    row=c.execute('SELECT digest FROM audit_events WHERE id=?',(payload['id'],)).fetchone()
    if not hmac.compare_digest(signature,expected) or not row or row['digest']!=payload['digest']:return {'ok':False,'checked':checked,'checkpoint_mismatch':True}
   except Exception:return {'ok':False,'checked':checked,'checkpoint_mismatch':True}
  elif checked:return {'ok':False,'checked':checked,'checkpoint_missing':True}
 return {'ok':True,'checked':checked,'last_hash':previous,'write_failure':_audit_failed}

def record_exception(error,reference):
 import traceback,sys
 frames=[{'file':Path(f.filename).name,'line':f.lineno,'function':f.name} for f in traceback.extract_tb(error.__traceback__)[-15:]]
 try:
  with _api.db() as c:c.execute('INSERT OR IGNORE INTO error_occurrences VALUES(?,?,?,?)',(reference,type(error).__name__,json.dumps(frames),time.time()))
 except Exception:pass
 sys.stderr.write('PantriPortal incident '+reference+' '+type(error).__name__+' '+json.dumps(frames)+'\n')

def legacy_permission(path,method):
 if path.startswith('/api/admin/recipes'):return 'content.read' if method=='GET' else 'content.manage'
 if path=='/api/admin/users':return 'users.read'
 if path=='/api/admin/role':return 'roles.manage'
 return 'images.manage'

def diagnostic():
 checks=[]
 def check(name,fn):
  try:
   result=fn();checks.append({'name':name,'ok':bool(result),'detail':'Passed' if result else 'Needs attention'})
  except Exception as e:checks.append({'name':name,'ok':False,'detail':type(e).__name__})
 def integrity():
  with _api.db() as c:return c.execute('PRAGMA quick_check').fetchone()[0]=='ok'
 check('Database integrity',integrity)
 check('Available data disk space',lambda:shutil.disk_usage(_api.DATA).free>100*1024*1024)
 check('Application assets',lambda:all((ROOT/p).is_file() for p in ['bootstrap.js','features.js','modes.js','admin.js','error_catalog.json']))
 check('Private data permissions',lambda:os.name=='nt' or (_api.DB.stat().st_mode&0o077)==0)
 from local_images import ready
 check('Image model and dependencies',ready)
 integrity_result=verify_audit();checks.append({'name':'Audit signature chain','ok':integrity_result['ok'] and not _audit_failed,'detail':f"{integrity_result['checked']} records checked"})
 return {'ok':all(x['ok'] for x in checks),'checks':checks,'jobs':{'images':sum(j['state'] in ('queued','running') for j in _api.IMAGE_JOBS.values()),'audits':sum(j['state'] in ('queued','running') for j in _api.JOBS.values())},'at':time.time()}

def allowed_integration(provider):
 with _api.db() as c:r=c.execute('SELECT body FROM integration_settings WHERE provider=?',(provider,)).fetchone()
 return not r or json.loads(r['body']).get('enabled',True)

def section_for(item):
 if item.get('home_section'):return item['home_section']
 text=str(item.get('category',''))+' '+str(item.get('name',''))
 for pattern,section in [('clothing|closet|shirt|trouser|pants|shoes|jacket|sweater|dress|coat|socks','clothing-closet'),('tools|hardware|screws|nails|fastener|glue|tape|hammer|wrench|drill','tools-hardware'),('medicine|medication|first aid|bandage|aspirin|ibuprofen','medicines-first-aid'),('cleaning|laundry|detergent|toilet cleaner|paper towel|household supplies','cleaning-supplies'),('personal|bathroom|fragrance|soap|shampoo|lotion|perfume|toothpaste','personal-care')]:
  if re.search(pattern,text,re.I):return section
 return 'other-home'

def check_integration(provider,url=''):
 from urllib.parse import urlsplit
 host=urlsplit(url).hostname if url else ''
 for entry in _api.recipe_providers():
  domain=urlsplit(entry.get('url','')).hostname
  if (entry['id']==provider or (domain and host and (host==domain or host.endswith('.'+domain)))) and not allowed_integration(entry['id']):raise _api.Problem(403,'This recipe connection is disabled by an administrator. Existing recipes remain available.')

def handle(h,path,q,user,method_override=None):
 """Return True when a request has been handled."""
 method=method_override or h.command
 if path=='/api/home-sections' and method=='GET':
  with _api.db() as c:rows=[dict(r) for r in c.execute('SELECT * FROM home_sections ORDER BY position,name')]
  h.send(200,{'sections':rows});return True
 if path=='/api/telemetry' and method=='POST':
  _api.limit('telemetry:'+user['user_id'],10,60);d=h.body(3000)
  kind=d.get('kind');
  if kind not in ('script','promise'):raise _api.Problem(400,'Choose a valid browser error kind.')
  error_class=d.get('error_class','Error');asset=d.get('asset','unknown');line=d.get('line',0)
  if error_class not in ('Error','TypeError','ReferenceError','SyntaxError','RangeError','UnhandledRejection'):error_class='Error'
  if asset not in ('app.js','features.js','modes.js','admin.js','home-sections.js','bootstrap.js'):asset='unknown'
  if not isinstance(line,int) or not 0<=line<=100000:line=0
  append_event(user,method,'/browser','browser.'+kind,status=0,code='PP-CLIENT',reference=h.request_id,message=error_class+' in '+asset+' at line '+str(line)+'. Browser details must be inspected privately.')
  h.send(200,{'ok':True});return True
 if not path.startswith('/api/admin/ops/'):return False
 tail=path.removeprefix('/api/admin/ops/')
 if tail=='sections' and method=='GET':
  require(user,'content.read')
  with _api.db() as c:rows=[dict(r) for r in c.execute('SELECT * FROM home_sections ORDER BY position,name')]
  h.send(200,{'sections':rows});return True
 if tail=='sections' and method in ('POST','PUT'):
  require(user,'content.manage');d=h.body();name=d.get('name','');description=d.get('description','');icon=d.get('icon','🏠');position=d.get('position',0);archived=d.get('archived',False)
  if not isinstance(name,str) or not 1<=len(name.strip())<=80 or not isinstance(description,str) or len(description)>500 or not isinstance(icon,str) or len(icon)>8 or not isinstance(position,int) or not 0<=position<=1000 or not isinstance(archived,bool):raise _api.Problem(400,'Enter a section name, short description, icon and valid display order.')
  with _api.db() as c:
   c.execute('BEGIN IMMEDIATE')
   if method=='PUT':
    if not c.execute('SELECT 1 FROM home_sections WHERE id=?',(d.get('id'),)).fetchone():raise _api.Problem(404,'Home inventory section not found.')
    sid=d['id']
   else:
    if c.execute('SELECT count(*) FROM home_sections').fetchone()[0]>=100:raise _api.Problem(409,'The system supports up to 100 Home inventory sections.')
    sid=secrets.token_hex(12)
   if c.execute('SELECT 1 FROM home_sections WHERE name=? AND id<>?',(name.strip(),sid)).fetchone():raise _api.Problem(409,'A Home inventory section already has that name.')
   c.execute('INSERT INTO home_sections VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,description=excluded.description,icon=excluded.icon,position=excluded.position,archived=excluded.archived',(sid,name.strip(),description,icon,position,int(archived)))
   append_event(user,method,path,'home_section.updated',target=sid,reference=h.request_id,message='Home section definition updated; saved items retained.',c=c)
  h.send(200,{'ok':True,'id':sid});return True
 if tail=='overview' and method=='GET':
  grants=permissions(user)
  if not grants:raise _api.Problem(403,'Administrator access is required.')
  result={'permissions':sorted(grants),'permission_labels':PERMISSIONS,'full_admin':full_admin(user),'version':'0.10.1','content_types':['inventory','recipes','product images','recipe images'],'logging':{'started':True,'retroactive':False,'suppressed_anonymous_events':_suppressed,'policy':'Server actions and signed-in browser error types; no passwords, tokens, bodies or query strings. Repeated anonymous errors are sampled to resist log floods. Logs are append-only and require private host maintenance to archive.'}}
  if 'audit.read' in grants:
   with _api.db() as c:
    result['events']=c.execute('SELECT count(*) FROM audit_events').fetchone()[0];result['errors_24h']=c.execute("SELECT count(*) FROM audit_events WHERE error_code<>'' AND created>?",(time.time()-86400,)).fetchone()[0]
  h.send(200,result);return True
 if tail=='database' and method=='GET':
  require(user,'database.read')
  with _api.db() as c:
   tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
   counts={name:c.execute('SELECT count(*) FROM "'+name.replace('"','""')+'"').fetchone()[0] for name in tables}
   mode=c.execute('PRAGMA journal_mode').fetchone()[0]
  h.send(200,{'tables':counts,'database_bytes':_api.DB.stat().st_size,'media_files':len(list(_api.MEDIA.glob('*.jpg'))),'free_bytes':shutil.disk_usage(_api.DATA).free,'sqlite_version':sqlite3.sqlite_version,'journal_mode':mode});return True
 if tail=='diagnostics' and method=='POST':
  require(user,'health.read');_api.limit('diagnostics:'+user['user_id'],5,60)
  result=diagnostic()
  if not result['ok']:append_event(user,method,path,'diagnostics.failed',status=503,code='PP-HEALTH',reference=h.request_id,message='One or more diagnostic checks failed.')
  h.send(200,result);return True
 if tail=='backup' and method=='POST':
  require(user,'database.backup')
  if not full_admin(user):raise _api.Problem(403,'A full administrator is required for recovery backups.')
  _api.limit('backup',2,3600);folder=_api.DATA/'backups';folder.mkdir(mode=0o700,exist_ok=True)
  stamp=time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-'+secrets.token_hex(3)
  snapshot=folder/(stamp+'.sqlite3');archive=folder/(stamp+'.tar.gz')
  with _api.db() as source,sqlite3.connect(snapshot) as target:source.backup(target)
  snapshot.chmod(0o600)
  with sqlite3.connect(snapshot) as target:
   if target.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise _api.Problem(500,'The recovery snapshot did not pass its integrity check.')
   tail=target.execute('SELECT id,digest FROM audit_events ORDER BY id DESC LIMIT 1').fetchone()
  snapshot_head=folder/(stamp+'.audit-head')
  if tail:
   head={'id':tail[0],'digest':tail[1]};head['signature']=hmac.new(_key,json.dumps(head,sort_keys=True).encode(),hashlib.sha256).hexdigest();snapshot_head.write_text(json.dumps(head),encoding='utf-8');snapshot_head.chmod(0o600)
  if not hmac.compare_digest((_api.DATA/'audit-signing-key').read_bytes(),_key):raise RuntimeError('Audit signing key changed outside the application')
  with tarfile.open(archive,'w:gz') as tar:
   tar.add(snapshot,arcname='inventory.sqlite3');tar.add(_api.MEDIA,arcname='media');tar.add(_api.DATA/'audit-signing-key',arcname='audit-signing-key')
   if tail:tar.add(snapshot_head,arcname='audit-head')
  archive.chmod(0o600)
  with archive.open('rb') as source:digest=hashlib.file_digest(source,'sha256').hexdigest()
  h.send(200,{'name':archive.name,'bytes':archive.stat().st_size,'sha256':digest,'message':'Verified recovery backup stored privately on the server. No database or credential material is sent to this browser.'});return True
 if tail=='users' and method=='GET':
  require(user,'users.read')
  with _api.db() as c:
   rows=c.execute('SELECT u.id,u.name,u.role,u.approved,u.disabled,u.home_role,u.created,h.name AS home,(SELECT count(*) FROM sessions s WHERE s.user_id=u.id AND s.expires>?) AS sessions FROM users u LEFT JOIN homes h ON h.id=u.home_id ORDER BY u.name',(time.time(),)).fetchall()
   users=[]
   for row in rows:
    item=dict(row);item['primary_admin']=primary_admin(row,c);item['permissions']=sorted(permissions(row,c));override=c.execute('SELECT * FROM admin_permissions WHERE user_id=?',(row['id'],)).fetchone();item['allow']=json.loads(override['allow_json']) if override else [];item['deny']=json.loads(override['deny_json']) if override else [];users.append(item)
  h.send(200,{'users':users,'roles':['user','author','admin']});return True
 if tail=='users' and method=='PATCH':
  require(user,'users.manage');d=h.body();target=d.get('id')
  if not isinstance(target,str) or not 1<=len(target)<=80:raise _api.Problem(400,'Choose a valid account identifier.')
  with _api.db() as c:
   c.execute('BEGIN IMMEDIATE');old=c.execute('SELECT * FROM users WHERE id=?',(target,)).fetchone()
   if not old:raise _api.Problem(404,'Account not found.')
   sensitive=any(k in d for k in ['role','allow','deny'])
   if sensitive and not full_admin(user,c):raise _api.Problem(403,'Only a full administrator can change roles or fine-grained permissions.')
   role=d.get('role',old['role']);disabled=d.get('disabled',bool(old['disabled']))
   if not isinstance(role,str) or role not in DEFAULTS or not isinstance(disabled,bool):raise _api.Problem(400,'Choose a valid account role and access state.')
   override=c.execute('SELECT * FROM admin_permissions WHERE user_id=?',(target,)).fetchone()
   allow=d.get('allow',json.loads(override['allow_json']) if override else []);deny=d.get('deny',json.loads(override['deny_json']) if override else [])
   if not isinstance(allow,list) or not isinstance(deny,list) or any(not isinstance(p,str) or p not in PERMISSIONS for p in allow+deny) or set(allow)&set(deny):raise _api.Problem(400,'Choose valid, non-conflicting administrator permissions.')
   if primary_admin(old,c) and (role!='admin' or disabled or deny):raise _api.Problem(409,'The main administrator cannot be disabled, demoted or have permissions denied.')
   # Anyone who can suspend accounts must not be able to disable a more privileged administrator.
   if not full_admin(user,c) and (old['role']=='admin' or permissions(old,c)-permissions(user,c)):raise _api.Problem(403,'Only a full administrator can change a more privileged account.')
   c.execute('UPDATE users SET role=?,disabled=? WHERE id=?',(role,int(disabled),target))
   c.execute('INSERT OR REPLACE INTO admin_permissions VALUES(?,?,?)',(target,json.dumps(sorted(set(allow))),json.dumps(sorted(set(deny)))))
   administrators=c.execute("SELECT * FROM users WHERE role='admin' AND disabled=0 AND approved=1").fetchall()
   if not any(full_admin(r,c) for r in administrators):raise _api.Problem(409,'Keep at least one enabled administrator with full permissions.')
   if disabled or d.get('revoke_sessions') is True:c.execute('DELETE FROM sessions WHERE user_id=?',(target,))
   append_event(user,method,path,'account.updated',target=target,reference=h.request_id,message='Role '+old['role']+' to '+role+'; disabled='+str(disabled)+'; allowed='+','.join(sorted(allow))+'; denied='+','.join(sorted(deny)),c=c)
  h.send(200,{'ok':True});return True
 if tail=='logs' and method=='GET':
  require(user,'audit.read');export=q.get('export',[''])[0]=='csv'
  if export:require(user,'audit.export')
  clauses=[];args=[]
  for key,column in [('actor','actor'),('action','action'),('code','error_code'),('reference','request_id')]:
   value=q.get(key,[''])[0][:120]
   if value:clauses.append(column+' LIKE ?');args.append('%'+value+'%')
  query=q.get('q',[''])[0][:120]
  if query:clauses.append('(message LIKE ? OR route LIKE ? OR target LIKE ?)');args.extend(['%'+query+'%']*3)
  for key,op in [('from','>='),('to','<=')]:
   value=q.get(key,[''])[0]
   if value:
    try:number=float(value)
    except ValueError:raise _api.Problem(400,'Choose valid audit date filters.')
    clauses.append('created'+op+'?');args.append(number)
  if q.get('errors',[''])[0]=='1':clauses.append("error_code<>''")
  try:offset=max(0,min(1000000,int(q.get('offset',['0'])[0])))
  except ValueError:raise _api.Problem(400,'Choose a valid audit page.')
  where=' WHERE '+' AND '.join(clauses) if clauses else ''
  with _api.db() as c:
   total=c.execute('SELECT count(*) FROM audit_events'+where,args).fetchone()[0]
   rows=[dict(r) for r in c.execute('SELECT * FROM audit_events'+where+' ORDER BY id DESC LIMIT ? OFFSET ?',(*args,5000 if export else 50,offset))]
  for row in rows:row.pop('digest');row.pop('previous_hash')
  if export:
   out=io.StringIO();fields=['id','created','actor','method','route','action','target','status','error_code','request_id','duration_ms','message'];writer=csv.DictWriter(out,fields,extrasaction='ignore');writer.writeheader()
   for row in rows:writer.writerow({k:("'"+str(v) if str(v).lstrip().startswith(('=','+','-','@')) else v) for k,v in row.items()})
   send_file(h,out.getvalue().encode('utf-8-sig'),'text/csv; charset=utf-8','pantriportal-audit.csv')
  else:h.send(200,{'events':rows,'total':total,'offset':offset,'page_size':50})
  return True
 if tail=='integrity' and method=='POST':
  require(user,'audit.read');_api.limit('audit-integrity:'+user['user_id'],3,60);result=verify_audit()
  if not result['ok']:append_event(user,method,path,'audit.integrity_failed',status=500,code='PP-AUDIT',reference=h.request_id,message='Audit signature chain mismatch.')
  h.send(200,result);return True
 if tail=='incident' and method=='GET':
  require(user,'audit.read');reference=q.get('reference',[''])[0][:32]
  with _api.db() as c:
   event=c.execute("SELECT created,actor,route,status,error_code,request_id,message FROM audit_events WHERE request_id=? AND error_code<>'' ORDER BY id DESC LIMIT 1",(reference,)).fetchone()
   context=c.execute('SELECT error_class,frames FROM error_occurrences WHERE reference=?',(reference,)).fetchone()
  if not event:raise _api.Problem(404,'Error occurrence not found.')
  h.send(200,{'event':dict(event),'context':{'error_class':context['error_class'],'frames':json.loads(context['frames'])} if context else None});return True
 if tail in ('errors','guide.docx') and method=='GET':
  require(user,'audit.read')
  if tail=='guide.docx':
   path=ROOT/'admin-error-guide.docx'
   if not path.is_file():raise _api.Problem(503,'The administrator error guide is not installed.')
   send_file(h,path.read_bytes(),'application/vnd.openxmlformats-officedocument.wordprocessingml.document','PantriPortal-Administrator-Error-Guide.docx')
  else:
   code=q.get('code',[''])[0];query=q.get('q',[''])[0].lower()[:160]
   entries=[x for x in catalog().values() if (not code or x['code']==code) and (not query or query in json.dumps(x).lower())]
   h.send(200,{'errors':sorted(entries,key=lambda x:x['code'])})
  return True
 if tail=='integrations' and method=='GET':
  require(user,'integrations.read')
  with _api.db() as c:settings={r['provider']:json.loads(r['body']) for r in c.execute('SELECT * FROM integration_settings')};links=[dict(r) for r in c.execute('SELECT provider,count(*) AS accounts,sum(recipe_count) AS imported_recipes,max(last_import) AS last_import FROM recipe_sources GROUP BY provider')]
  providers=_api.recipe_providers()
  h.send(200,{'providers':[dict(p,settings=settings.get(p['id'],{'enabled':True,'notes':''})) for p in providers],'connections':links});return True
 if tail=='integrations' and method=='PUT':
  require(user,'integrations.manage');d=h.body();known={p['id'] for p in _api.recipe_providers()}
  if not isinstance(d.get('provider'),str) or d.get('provider') not in known or not isinstance(d.get('enabled'),bool) or not isinstance(d.get('notes',''),str) or len(d.get('notes',''))>500:raise _api.Problem(400,'Choose a supported recipe provider and valid connection settings.')
  # Keep public endpoints vetted. Arbitrary callback URLs and third-party passwords are never accepted.
  body={'enabled':d['enabled'],'notes':safe_text(d.get('notes',''))}
  with _api.db() as c:c.execute('INSERT OR REPLACE INTO integration_settings VALUES(?,?,?)',(d['provider'],json.dumps(body),time.time()))
  h.send(200,{'ok':True});return True
 if tail=='integrations/test' and method=='POST':
  require(user,'integrations.read');_api.limit('connection-test:'+user['user_id'],5,60);d=h.body()
  entry=next((p for p in _api.recipe_providers() if p['id']==d.get('provider')),None)
  if not entry or not entry.get('url'):raise _api.Problem(400,'Choose a recipe provider with a public website.')
  import urllib.request,urllib.error
  _api.validate_public_recipe_url(entry['url']);started=time.monotonic();status=0
  try:
   opener=urllib.request.build_opener(_api.PublicRedirect())
   with opener.open(urllib.request.Request(entry['url'],method='HEAD',headers={'User-Agent':'PantriPortal health check (+https://www.pantriportal.com)'}),timeout=8) as response:status=response.status
  except urllib.error.HTTPError as error:status=error.code
  except Exception:pass
  available=200<=status<400
  if not available:append_event(user,method,path,'provider.check_failed',target=entry['id'],status=502,code='PP-PROVIDER',reference=h.request_id,message='Public recipe provider probe returned status '+str(status)+'.')
  h.send(200,{'available':available,'provider':entry['id'],'http_status':status,'duration_ms':round((time.monotonic()-started)*1000),'message':'Public website availability only. Account sync and recipe parsing were not tested. Some providers block automated probes.'});return True
 if tail=='content' and method=='GET':
  require(user,'content.read');kind=q.get('kind',['inventory'])[0]
  with _api.db() as c:
   if kind=='inventory':rows=c.execute('SELECT i.id,i.body,u.name AS owner FROM items i JOIN users u ON u.id=i.user_id ORDER BY i.updated DESC LIMIT 500').fetchall();records=[dict(json.loads(r['body']),id=r['id'],kind=kind,owner=r['owner']) for r in rows]
   elif kind=='recipes':
    records=[]
    for table in ['recipes','personal_recipes']:
     for r in c.execute(f'SELECT r.id,r.body,u.name AS owner FROM {table} r LEFT JOIN users u ON u.id=r.owner_id LIMIT 500'):records.append(dict(json.loads(r['body']),id=r['id'],kind=table,owner=r['owner']))
   else:raise _api.Problem(400,'Choose inventory or recipes.')
  h.send(200,{'records':records});return True
 if tail=='content' and method=='PATCH':
  require(user,'content.manage');d=h.body();kind=d.get('kind');table={'inventory':'items','recipes':'recipes','personal_recipes':'personal_recipes'}.get(kind) if isinstance(kind,str) else None
  if not table:raise _api.Problem(400,'Choose a valid content type.')
  with _api.db() as c:
   c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT body FROM '+table+' WHERE id=?',(d.get('id'),)).fetchone()
   if not row:raise _api.Problem(404,'Content record not found.')
   old=json.loads(row['body']);before=hashlib.sha256(row['body'].encode()).hexdigest()
   if d.get('revision')!=before:raise _api.Problem(409,'This record changed. Reload it before saving your edit.')
   fields={'name','brand','category','location','unit','qty','notes','home_section','is_food'} if kind=='inventory' else {'name','description','instructions','notes','time'}
   changes=d.get('changes',{})
   if not isinstance(changes,dict) or set(changes)-fields:raise _api.Problem(400,'Choose supported content fields.')
   if 'is_food' in changes and not isinstance(changes['is_food'],bool):raise _api.Problem(400,'Choose Kitchen or Home inventory for this item.')
   updated=dict(old,**changes)
   if kind=='inventory':updated=dict(old,**_api.clean(updated))
   else:
    for key,value in changes.items():
     if key=='instructions':
      if not isinstance(value,list) or len(value)>120 or any(not isinstance(line,str) or len(line)>1500 for line in value):raise _api.Problem(400,'Check the recipe instruction lengths.')
     elif not isinstance(value,str) or len(value)>15000:raise _api.Problem(400,'Check the recipe text lengths.')
    if not str(updated.get('name','')).strip():raise _api.Problem(400,'A recipe title is required before saving.')
    if old.get('guided') and 'instructions' in changes:
     if not changes['instructions'] or any(not s.strip() for s in changes['instructions']):raise _api.Problem(400,'Guided recipes require complete cooking instructions.')
     updated['steps']=[{'text':s,'image':old.get('steps',[])[n].get('image','') if n<len(old.get('steps',[])) else ''} for n,s in enumerate(changes['instructions'])]
   if kind=='inventory':
    owner=c.execute('SELECT user_id FROM items WHERE id=?',(d['id'],)).fetchone()[0]
    if any(_api.identity(json.loads(r['body']))==_api.identity(updated) for r in c.execute('SELECT body FROM items WHERE id<>? AND user_id IN (SELECT id FROM users WHERE home_id=(SELECT home_id FROM users WHERE id=?))',(d['id'],owner))):raise _api.Problem(409,'Another entry already has this product, location and unit. Add units to that entry instead.')
    c.execute('UPDATE items SET body=?,updated=? WHERE id=?',(json.dumps(updated),time.time(),d['id']))
   else:c.execute('UPDATE '+table+' SET body=? WHERE id=?',(json.dumps(updated),d['id']))
   append_event(user,method,path,'content.edited',target=d['id'],reference=h.request_id,message='Edited '+kind+' fields: '+','.join(sorted(changes)),c=c)
  h.send(200,{'ok':True});return True
 if tail=='content/detail' and method=='GET':
  require(user,'content.read');table={'inventory':'items','recipes':'recipes','personal_recipes':'personal_recipes'}.get(q.get('kind',[''])[0])
  if not table:raise _api.Problem(400,'Choose a valid content type.')
  with _api.db() as c:row=c.execute('SELECT body FROM '+table+' WHERE id=?',(q.get('id',[''])[0],)).fetchone()
  if not row:raise _api.Problem(404,'Content record not found.')
  h.send(200,{'record':json.loads(row['body']),'revision':hashlib.sha256(row['body'].encode()).hexdigest()});return True
 if tail=='content/image' and method=='POST':
  require(user,'images.manage');d=h.body();kind=d.get('kind');table={'inventory':'items','recipes':'recipes','personal_recipes':'personal_recipes'}.get(kind) if isinstance(kind,str) else None
  if not table:raise _api.Problem(400,'Choose a valid content type.')
  image=_api.safe_image(d.get('image',''))
  if not image.startswith('/media/'):raise _api.Problem(400,'Choose a working product image.')
  with _api.db() as c:
   c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT * FROM '+table+' WHERE id=?',(d.get('id'),)).fetchone()
   if not row:raise _api.Problem(404,'Content record not found.')
   if hashlib.sha256(row['body'].encode()).hexdigest()!=d.get('revision'):raise _api.Problem(409,'This record changed. Reload it before saving your edit.')
   uploaded=c.execute('SELECT user_id FROM media WHERE id=?',(Path(image).stem,)).fetchone()
   if not uploaded or uploaded['user_id']!=user['user_id']:raise _api.Problem(403,'Upload your own replacement photo first.')
   owner=row['user_id'] if kind=='inventory' else row['owner_id'];source=_api.MEDIA/Path(image).name
   if not source.is_file():raise _api.Problem(404,'Image not found.')
   data=source.read_bytes();mid=hashlib.sha256(owner.encode()+data).hexdigest();(_api.MEDIA/(mid+'.jpg')).write_bytes(data)
   c.execute('INSERT OR IGNORE INTO media VALUES(?,?,?)',(mid,owner,time.time()))
   body=json.loads(row['body']);body.update(image='/media/'+mid+'.jpg',image_source='Administrator supplied photo',image_generated=False)
   c.execute('UPDATE '+table+' SET body=? WHERE id=?',(json.dumps(body),d['id']))
   append_event(user,method,path,'content.image_replaced',target=d['id'],reference=h.request_id,message='Image replaced for '+kind+'; original image retained.',c=c)
  h.send(200,{'ok':True});return True
 if tail=='maintenance' and method=='POST':
  require(user,'maintenance.manage');d=h.body()
  if d.get('action')!='clear_catalog_cache':raise _api.Problem(400,'Choose a supported maintenance action.')
  with _api.db() as c:c.execute('DELETE FROM cache')
  h.send(200,{'ok':True,'message':'Catalog response cache cleared. Saved inventory, recipes, sessions and audit records were preserved.'});return True
 raise _api.Problem(404,'Administrator tool not found.')

def send_file(h,data,mime,name):
 h._pending_response=(200,data,{'Content-Type':mime,'Content-Length':str(len(data)),'Content-Disposition':'attachment; filename="'+name+'"','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})
 h.response_status=200
