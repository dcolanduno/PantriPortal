"""Owner-only benefit cards and attributed prescription quotes; no eligibility inference."""
import medicine_pricing as pricing
import medicine_catalog as catalog
import json,re,secrets,time,hashlib,types,datetime
_api=None
PROGRAM={'name':160,'category':30,'plan':200,'member_id':120,'group_number':120,'rxbin':6,'rxpcn':80,'phone':80,'website':500,'notes':1500}
def initialize(namespace):
 global _api
 _api=types.SimpleNamespace(**namespace)
 with _api.db() as c:c.executescript('''CREATE TABLE IF NOT EXISTS medicine_benefit_entries(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),kind TEXT NOT NULL,body TEXT NOT NULL,updated REAL NOT NULL);
CREATE INDEX IF NOT EXISTS medicine_benefit_owner ON medicine_benefit_entries(user_id,kind);
CREATE TABLE IF NOT EXISTS medicine_benefit_profiles(user_id TEXT PRIMARY KEY REFERENCES users(id),body TEXT NOT NULL);''')
def fail(message,status=400):raise _api.Problem(status,message)
def text(d,key,size,required=False):
 v=d.get(key,'')
 if not isinstance(v,str) or len(v)>size or (required and not v.strip()):fail('Check '+key.replace('_',' ')+'.')
 return v.strip()
def revision(raw):return hashlib.sha256(raw.encode()).hexdigest()
def row(r):return dict(json.loads(r['body']),id=r['id'],revision=revision(r['body']),updated=r['updated'])
def handle(h,u,tail):
 if not tail.startswith('benefits/'):return False
 action=tail.removeprefix('benefits/');method=h.command;uid=u['user_id']
 if action=='provider-status' and method=='GET':h.send(200,pricing.status());return True
 if action=='provider-prices' and method=='POST':
  _api.limit('medicine-prices:'+uid,12,60)
  d=h.body()
  if d.get('consent') is not True:fail('Confirm sharing drug and fill details with GoodRx.')
  rid=text(d,'prescription_id',24,True)
  with _api.db() as c:rx=c.execute("SELECT body FROM medicine_records WHERE id=? AND user_id=? AND kind='prescription'",(rid,uid)).fetchone()
  if not rx:fail('Save your own prescription first.',404)
  if d.get('prescription_revision')!=revision(rx['body']):fail('Prescription changed. Reopen comparison.',409)
  rx=json.loads(rx['body']);fill={k:text(d,k,n,True) for k,n in {'form':120,'quantity':20,'zip':5,'unit':60,'days_supply':4}.items()}
  if not rx.get('strength'):fail('Save the medicine strength first.')
  if not re.fullmatch(r'\d{5}',fill['zip']) or not re.fullmatch(r'\d{1,6}(?:\.\d{1,3})?',fill['quantity']) or float(fill['quantity'])<=0 or not re.fullmatch(r'[1-9]\d{0,2}',fill['days_supply']):fail('Check ZIP, quantity and days supply.')
  if fill['unit'].casefold() not in ['tablet','tablets','capsule','capsules','ml','g','gram','grams']:fail('Use metric fill quantity in tablets, capsules, mL or grams for this provider.')
  try:result=pricing.compare(rx,fill)
  except catalog.CatalogUnavailable:fail('GoodRx pricing is unavailable. Saved quotes and provider links still work.',502)
  h.send(200,result);return True
 if action=='state' and method=='GET':
  with _api.db() as c:
   entries=c.execute('SELECT * FROM medicine_benefit_entries WHERE user_id=? ORDER BY updated DESC',(uid,)).fetchall();profile=c.execute('SELECT body FROM medicine_benefit_profiles WHERE user_id=?',(uid,)).fetchone()
  h.send(200,{'programs':[row(r) for r in entries if r['kind']=='program'],'quotes':[row(r) for r in entries if r['kind']=='quote'],'profile':json.loads(profile['body']) if profile else {'zip':''},'profile_revision':revision(profile['body']) if profile else ''});return True
 if action=='profile' and method=='PUT':
  d=h.body();zip=text(d,'zip',5)
  if zip and not re.fullmatch(r'\d{5}',zip):fail('Enter a five-digit US ZIP code, or leave it blank.')
  with _api.db() as c:
   c.execute('BEGIN IMMEDIATE');old=c.execute('SELECT body FROM medicine_benefit_profiles WHERE user_id=?',(uid,)).fetchone()
   if d.get('revision')!=(revision(old['body']) if old else ''):fail('Your profile changed. Reopen before saving.',409)
   c.execute('INSERT INTO medicine_benefit_profiles VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET body=excluded.body',(uid,json.dumps({'zip':zip})))
  h.send(200,{'ok':True});return True
 match=re.fullmatch(r'programs/([a-f0-9]{24})',action)
 if (action=='programs' and method=='POST') or (match and method=='PUT'):
  d=h.body();out={k:text(d,k,n,k in ('name','category')) for k,n in PROGRAM.items()}
  if out['category'] not in ['insurance','discount','assistance']:fail('Choose a program type.')
  if out['rxbin'] and not re.fullmatch(r'\d{6}',out['rxbin']):fail('RxBIN must contain six digits.')
  if out['website']:
   import urllib.parse
   try:url=urllib.parse.urlsplit(out['website'])
   except ValueError:fail('Check the program website.')
   if url.scheme!='https' or not url.hostname or url.username or url.password:fail('Use an HTTPS program website without credentials.')
  if type(d.get('archived',False)) is not bool:fail('Check archived setting.')
  out['archived']=d.get('archived',False);rid=match.group(1) if match else secrets.token_hex(12)
  with _api.db() as c:
   c.execute('BEGIN IMMEDIATE')
   if match:
    old=c.execute("SELECT body FROM medicine_benefit_entries WHERE id=? AND user_id=? AND kind='program'",(rid,uid)).fetchone()
    if not old:fail('Program not found.',404)
    if d.get('revision')!=revision(old['body']):fail('Program changed. Reopen before saving.',409)
    c.execute('UPDATE medicine_benefit_entries SET body=?,updated=? WHERE id=? AND user_id=?',(json.dumps(out),time.time(),rid,uid))
   else:c.execute('INSERT INTO medicine_benefit_entries VALUES(?,?,?,?,?)',(rid,uid,'program',json.dumps(out),time.time()))
  h.send(200 if match else 201,{'id':rid});return True
 if action=='quotes' and method=='POST':
  d=h.body();out={k:text(d,k,n,True) for k,n in {'prescription_id':24,'pharmacy':200,'address':500,'program_id':24,'amount':12,'quantity':20,'unit':60,'form':120,'days_supply':4,'quoted_on':10,'source':300}.items()}
  out['phone']=text(d,'phone',80);out['pharmacy_key']=text(d,'pharmacy_key',100)
  if not re.fullmatch(r'\d{1,7}(?:\.\d{1,2})?',out['amount']):fail('Enter the total quoted price in USD, with at most two decimal places.')
  if not re.fullmatch(r'\d{1,6}(?:\.\d{1,3})?',out['quantity']) or float(out['quantity'])<=0:fail('Enter a positive fill quantity.')
  if not re.fullmatch(r'\d{1,3}',out['days_supply']) or int(out['days_supply'])<1:fail('Enter days supply from 1 to 999.')
  try:
   dt=datetime.date.fromisoformat(out['quoted_on'])
   if dt>datetime.datetime.now(datetime.timezone.utc).date() or dt.isoformat()!=out['quoted_on']:raise ValueError()
  except (ValueError,TypeError):fail('Enter a valid quote date, not in the future.')
  with _api.db() as c:
   rx=c.execute("SELECT body FROM medicine_records WHERE id=? AND user_id=? AND kind='prescription'",(out['prescription_id'],uid)).fetchone()
   if not rx:fail('Prescription not found. Save it to your cabinet first.',404)
   if out['program_id']!='cash':
    program=c.execute("SELECT body FROM medicine_benefit_entries WHERE id=? AND user_id=? AND kind='program'",(out['program_id'],uid)).fetchone()
    if not program or json.loads(program['body']).get('archived'):fail('Choose your own active program.')
   if d.get('prescription_revision')!=revision(rx['body']):fail('Prescription changed. Reopen the price comparison.',409)
   if d.get('confirmed') is not True:fail('Confirm the exact product and fill details.')
   rx=json.loads(rx['body'])
   if not rx.get('strength'):fail('Enter the prescription strength before recording a price.')
   out.update(prescription_name=rx['name'],strength=rx.get('strength',''),ndc=rx.get('ndc',''))
   rid=secrets.token_hex(12);c.execute('INSERT INTO medicine_benefit_entries VALUES(?,?,?,?,?)',(rid,uid,'quote',json.dumps(out),time.time()))
  h.send(201,{'id':rid});return True
 fail('Benefits route not found.',404)
