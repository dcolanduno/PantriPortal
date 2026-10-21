"""Owner-only medicine cabinets. Shared pharmacy items remain ordinary inventory."""
import datetime,hashlib,json,math,re,secrets,time,types
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError

_api=None
FIELDS={
 'doctor':{'name':160,'specialty':160,'practice':200,'phone':80,'email':200,'address':500,'notes':1500},
 'prescription':{'name':160,'strength':120,'directions':1500,'unit':60,'pharmacy':200,'pharmacy_phone':80,'pharmacy_address':500,'rx_number':120,'notes':1500},
 'appointment':{'name':160,'location':500,'phone':80,'notes':1500},
}

def initialize(namespace):
 global _api
 _api=types.SimpleNamespace(**namespace)
 with _api.db() as c:c.executescript('''
CREATE TABLE IF NOT EXISTS medicine_cabinets(user_id TEXT PRIMARY KEY REFERENCES users(id),body TEXT NOT NULL,updated REAL NOT NULL);
CREATE TABLE IF NOT EXISTS medicine_records(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),kind TEXT NOT NULL,body TEXT NOT NULL,updated REAL NOT NULL);
CREATE INDEX IF NOT EXISTS medicine_owner ON medicine_records(user_id,kind);
''')

def fail(message,status=400):raise _api.Problem(status,message)
def text(value,label,maximum=200,required=False):
 if not isinstance(value,str) or len(value)>maximum or (required and not value.strip()):fail('Check '+label+'.')
 return value.strip()
def revision(raw):return hashlib.sha256(raw.encode()).hexdigest()
def record(row):return dict(json.loads(row['body']),id=row['id'],kind=row['kind'],revision=revision(row['body']))
def date(value,label):
 if value=='':return ''
 try:
  if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):raise ValueError()
  datetime.date.fromisoformat(value);return value
 except (ValueError,TypeError):fail('Check '+label+' (YYYY-MM-DD).')
def number(value,label,integer=False):
 if value in ('',None):return None
 try:
  if isinstance(value,bool):raise ValueError()
  n=float(value)
  if not math.isfinite(n) or not 0<=n<=1000000 or (integer and n!=int(n)):raise ValueError()
  return int(n) if integer else n
 except (ValueError,TypeError,OverflowError):fail('Check '+label+'; use a nonnegative number.')
def clean(d,u,c):
 kind=d.get('kind')
 if not isinstance(kind,str) or kind not in FIELDS:fail('Choose a supported medicine record type.')
 out={key:text(d.get(key,''),key.replace('_',' '),maximum,key=='name' or (kind=='appointment' and key=='location')) for key,maximum in FIELDS[kind].items()}
 if type(d.get('archived',False)) is not bool:fail('Check the archived setting.')
 out['archived']=d.get('archived',False)
 if kind in ('prescription','appointment'):
  doctor=text(d.get('doctor_id',''),'prescriber selection',32)
  if doctor and not c.execute("SELECT 1 FROM medicine_records WHERE id=? AND user_id=? AND kind='doctor'",(doctor,u['user_id'])).fetchone():fail('Choose a doctor from your own cabinet.')
  out['doctor_id']=doctor
 if kind=='prescription':
  for key in ['last_filled','next_refill','expires']:out[key]=date(d.get(key,''),key.replace('_',' '))
  for key in ['quantity','refills_remaining']:out[key]=number(d.get(key),key.replace('_',' '),key=='refills_remaining')
 if kind=='appointment':
  value=d.get('starts','');zone=text(d.get('timezone',''),'appointment time zone',100,True)
  try:
   if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}',value):raise ValueError()
   dt=datetime.datetime.fromisoformat(value);tz=ZoneInfo(zone)
   aware=dt.replace(tzinfo=tz)
   if aware.astimezone(datetime.timezone.utc).astimezone(tz).replace(tzinfo=None)!=dt:raise ValueError()
  except (ValueError,TypeError,ZoneInfoNotFoundError):fail('Enter an appointment date, time and valid time zone.')
  out.update(starts=value,timezone=zone,starts_utc=aware.astimezone(datetime.timezone.utc).isoformat())
 return kind,out

def handle(h,u,path,q):
 if not path.startswith('/api/medicine/'):return False
 method=h.command;tail=path.removeprefix('/api/medicine/')
 if tail=='state' and method=='GET':
  with _api.db() as c:
   cabinet=c.execute('SELECT body FROM medicine_cabinets WHERE user_id=?',(u['user_id'],)).fetchone()
   rows=c.execute('SELECT * FROM medicine_records WHERE user_id=? ORDER BY updated DESC',(u['user_id'],)).fetchall()
   stock=c.execute('SELECT i.id,i.body,u.name AS owner FROM items i JOIN users u ON i.user_id=u.id WHERE u.home_id=? AND u.approved=1 AND u.disabled=0',(u['home_id'],)).fetchall()
  pharmacy=[]
  for row in stock:
   item=json.loads(row['body'])
   if item.get('is_food') is False and item.get('home_section')=='medicines-first-aid':
    pharmacy.append(dict(item,id=row['id'],owner=row['owner'],can_edit=False))
  h.send(200,{'cabinet':json.loads(cabinet['body']) if cabinet else {'name':'My medicine cabinet'},'cabinet_revision':revision(cabinet['body']) if cabinet else '',
   'records':[record(r) for r in rows],'pharmacy':pharmacy});return True
 if tail=='cabinet' and method=='PUT':
  d=h.body();name=text(d.get('name'),'cabinet name',100,True);raw=json.dumps({'name':name})
  with _api.db() as c:
   c.execute('BEGIN IMMEDIATE');old=c.execute('SELECT body FROM medicine_cabinets WHERE user_id=?',(u['user_id'],)).fetchone()
   if d.get('revision')!=(revision(old['body']) if old else ''):fail('Your cabinet changed. Reload before saving.',409)
   c.execute('INSERT INTO medicine_cabinets VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET body=excluded.body,updated=excluded.updated',(u['user_id'],raw,time.time()))
  h.send(200,{'ok':True});return True
 match=re.fullmatch(r'records/([a-f0-9]{24})',tail)
 if (tail=='records' and method=='POST') or (match and method=='PUT'):
  d=h.body();rid=match.group(1) if match else secrets.token_hex(12)
  with _api.db() as c:
   c.execute('BEGIN IMMEDIATE')
   if match:
    old=c.execute('SELECT * FROM medicine_records WHERE id=? AND user_id=?',(rid,u['user_id'])).fetchone()
    if not old:fail('Medicine record not found.',404)
    if d.get('revision')!=revision(old['body']):fail('This record changed. Reload before saving.',409)
    if d.get('kind')!=old['kind']:fail('The record type cannot be changed.')
   kind,out=clean(d,u,c);raw=json.dumps(out,allow_nan=False)
   if match:c.execute('UPDATE medicine_records SET body=?,updated=? WHERE id=? AND user_id=?',(raw,time.time(),rid,u['user_id']))
   else:c.execute('INSERT INTO medicine_records VALUES(?,?,?,?,?)',(rid,u['user_id'],kind,raw,time.time()))
  h.send(200 if match else 201,{'id':rid,'revision':revision(raw)});return True
 fail('Medicine route not found.',404)
