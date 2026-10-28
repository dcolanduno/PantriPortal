import os,json,sqlite3,secrets,hashlib,hmac,time,re,threading,urllib.request,urllib.parse,urllib.error,base64,io,math,mimetypes,importlib.util,socket,ipaddress,html,zipfile,gzip
from pathlib import Path
from html.parser import HTMLParser
from collections import defaultdict,deque
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from http.cookies import SimpleCookie
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from PIL import Image,ImageOps

ROOT=Path(__file__).resolve().parent
APP_VERSION='0.15.9'
DATA=Path(os.environ.get('PANTRY_DATA',str(ROOT.parent/'work/runtime')));DATA.mkdir(parents=True,exist_ok=True)
MEDIA=DATA/'media';MEDIA.mkdir(exist_ok=True);DB=DATA/'inventory.sqlite3'
ORIGINS={'https://www.pantriportal.com','https://pantriportal.com','https://68.168.30.142'}
PORT=int(os.environ.get('PANTRY_PORT','8767'))
def release_build():
 try:
  commit=json.loads((ROOT/'release-source.json').read_text(encoding='utf-8')).get('commit','')
  return commit[:12] if isinstance(commit,str) and re.fullmatch(r'[0-9a-f]{40}',commit) else 'local'
 except (OSError,ValueError,TypeError):return 'local'
DEV=os.environ.get('PANTRY_DEV')=='1'
if DEV:ORIGINS.update({'http://127.0.0.1:'+str(PORT),'http://localhost:'+str(PORT)})
COOKIE_SECURE='' if DEV else '; Secure'
LOCK=threading.Lock();RATE=defaultdict(deque);JOBS={};POOL=ThreadPoolExecutor(max_workers=4)
IMAGE_JOBS={};IMAGE_POOL=ThreadPoolExecutor(max_workers=1)
Image.MAX_IMAGE_PIXELS=20_000_000
FACTS={'food':('world.openfoodfacts.org','Open Food Facts'),'beauty':('world.openbeautyfacts.org','Open Beauty Facts')}
IMAGE_HOSTS={'www.themealdb.com','images.openfoodfacts.org','images.openbeautyfacts.org','images.openproductsfacts.org','images.openpetfoodfacts.org','static.openfoodfacts.org','i5.walmartimages.com','m.media-amazon.com','images-na.ssl-images-amazon.com','target.scene7.com','i.ebayimg.com','images.heb.com','images.kroger.com','www.kroger.com'}
class Problem(Exception):
 def __init__(self,status,message,code=None):self.status=status;self.message=message;self.code=code or ops.error_code(status,message)
class Connection(sqlite3.Connection):
 def __exit__(self,*args):
  try:return super().__exit__(*args)
  finally:self.close()
def db():
 c=sqlite3.connect(DB,timeout=30,factory=Connection);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');return c
def init():
 with db() as c:
  c.executescript('''PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,name TEXT UNIQUE,salt TEXT,password TEXT,role TEXT,created REAL);
CREATE TABLE IF NOT EXISTS homes(id TEXT PRIMARY KEY,name TEXT,join_code TEXT UNIQUE,created REAL);
CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id TEXT REFERENCES users(id),csrf TEXT,expires REAL);
CREATE TABLE IF NOT EXISTS items(id TEXT PRIMARY KEY,user_id TEXT REFERENCES users(id),body TEXT,updated REAL);
CREATE INDEX IF NOT EXISTS items_user ON items(user_id);
CREATE TABLE IF NOT EXISTS imports(user_id TEXT,digest TEXT,PRIMARY KEY(user_id,digest));
CREATE TABLE IF NOT EXISTS media(id TEXT PRIMARY KEY,user_id TEXT REFERENCES users(id),created REAL);
CREATE TABLE IF NOT EXISTS cache(url TEXT PRIMARY KEY,body TEXT,expires REAL);
CREATE TABLE IF NOT EXISTS config(key TEXT PRIMARY KEY,value TEXT);
CREATE TABLE IF NOT EXISTS activity(id INTEGER PRIMARY KEY AUTOINCREMENT,home_id TEXT,actor_id TEXT,item_id TEXT,action TEXT,detail TEXT,created REAL);
CREATE INDEX IF NOT EXISTS activity_home ON activity(home_id,created DESC);
CREATE TABLE IF NOT EXISTS recipes(id TEXT PRIMARY KEY,home_id TEXT,owner_id TEXT,body TEXT,created REAL);
CREATE TABLE IF NOT EXISTS personal_recipes(id TEXT PRIMARY KEY,home_id TEXT,owner_id TEXT,body TEXT,created REAL);
CREATE TABLE IF NOT EXISTS recipe_sources(user_id TEXT,provider TEXT,status TEXT NOT NULL DEFAULT 'import_only',last_import REAL,recipe_count INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(user_id,provider));
CREATE TABLE IF NOT EXISTS user_settings(user_id TEXT PRIMARY KEY,body TEXT NOT NULL,updated REAL);
CREATE TABLE IF NOT EXISTS home_locations(home_id TEXT,mode TEXT,name TEXT COLLATE NOCASE,created REAL,PRIMARY KEY(home_id,mode,name));
''')
  cols={r['name'] for r in c.execute('PRAGMA table_info(users)')}
  if 'home_id' not in cols:c.execute('ALTER TABLE users ADD COLUMN home_id TEXT')
  if 'home_role' not in cols:c.execute("ALTER TABLE users ADD COLUMN home_role TEXT NOT NULL DEFAULT 'member'")
  if 'approved' not in cols:c.execute('ALTER TABLE users ADD COLUMN approved INTEGER NOT NULL DEFAULT 1')
  # Preserve existing account inventories by placing each pre-existing account
  # in its own household. The account owner can then invite household members.
  for u in c.execute('SELECT id,name,role,home_id FROM users WHERE home_id IS NULL').fetchall():
   hid=secrets.token_hex(12);code=secrets.token_urlsafe(9)[:12].upper()
   c.execute('INSERT INTO homes VALUES(?,?,?,?)',(hid,u['name']+"'s Home",code,time.time()))
   c.execute('UPDATE users SET home_id=?,home_role=?,approved=1 WHERE id=?',(hid,'admin',u['id']))
  c.execute('CREATE INDEX IF NOT EXISTS users_home ON users(home_id,approved)')
  if not c.execute("SELECT 1 FROM config WHERE key='admin_setup'").fetchone():
   token=secrets.token_urlsafe(32);f=DATA/'admin-setup-token';f.write_text(token);f.chmod(0o600);c.execute('INSERT INTO config VALUES(?,?)',('admin_setup',hashlib.sha256(token.encode()).hexdigest()))
 DB.chmod(0o600)
 ops.initialize(globals())
 kitchen.initialize(globals())
 medicine.initialize(globals())
def limit(key,n,seconds):
 with LOCK:
  t=time.time();q=RATE[key]
  while q and q[0]<t-seconds:q.popleft()
  if len(q)>=n:raise Problem(429,'Please wait before trying again. The free lookup service has usage limits.')
  q.append(t)
  if len(RATE)>5000:
   for k in list(RATE):
    if not RATE[k] or RATE[k][-1]<t-86400:RATE.pop(k,None)
def pw(p,s):return hashlib.scrypt(p.encode(),salt=bytes.fromhex(s),n=16384,r=8,p=1).hex()
def norm(s):return re.sub(r'\W+',' ',s.lower()).strip()
def identity(d):
 # Never combine different units or package sizes without an explicit conversion.
 return ('barcode:'+d['barcode'].lstrip('0') if d.get('barcode') else 'name:'+norm(d['name'])+'|'+norm(d.get('brand',''))+'|'+norm(d.get('weight','')))+'|'+norm(d.get('location','Pantry'))+'|'+norm(d.get('unit') or 'each')+('|section:'+ops.section_for(d) if d.get('is_food') is False else '')
def safe_image(s):
 if not isinstance(s,str):return ''
 if re.fullmatch(r'/media/[a-f0-9]{64}\.jpg',s):return s
 try:
  u=urllib.parse.urlsplit(s)
  if u.scheme=='https' and u.hostname in IMAGE_HOSTS and u.port in (None,443) and not u.username and len(s)<1500:return s
 except ValueError:pass
 return ''
def clean(d):
 if not isinstance(d,dict):raise Problem(400,'Each item must be an object.')
 result={}
 fields={'home_section':80,'name':160,'brand':160,'category':120,'location':80,'unit':40,'store':120,'storage':80,'bestBy':10,'barcode':14,'weight':80,'food_type':120,'notes':1500,'image':1500,'image_source':120,'source_url':400,'ingredients':3000,'allergens':1000}
 for k,maxlen in fields.items():
  v=d.get(k,'')
  if not isinstance(v,str) or len(v)>maxlen:raise Problem(400,'Invalid '+k.replace('_',' ')+'.')
  result[k]=v.strip()
 if result.get('home_section'):
  with db() as c:
   if not c.execute('SELECT 1 FROM home_sections WHERE id=?',(result['home_section'],)).fetchone():raise Problem(400,'Choose an existing Home inventory section.')
 if not result['name']:raise Problem(400,'Enter an item name.')
 for k,default in [('qty',1),('cost',0)]:
  try:v=float(d.get(k,default))
  except (TypeError,ValueError):raise Problem(400,'Enter a valid '+k+'.')
  if not math.isfinite(v) or not 0<=v<=100000:raise Problem(400,'Use a number between 0 and 100,000.')
  result[k]=round(v,3)
 if result['bestBy']:
  try:date.fromisoformat(result['bestBy'])
  except ValueError:raise Problem(400,'Enter a valid best-by date.')
 if result['barcode'] and not re.fullmatch(r'\d{8,14}',result['barcode']):raise Problem(400,'Use an 8–14 digit barcode.')
 result['image']=safe_image(result['image']);result['is_food']=d.get('is_food',True) is True;result['location']=result['location'] or 'Pantry';result['unit']=result['unit'] or 'each'
 result['image_generated']=False
 if result['image']:
  with db() as c:r=c.execute('SELECT value FROM config WHERE key=?',('generated:'+result['image'],)).fetchone()
  result['image_generated']=bool(r)
  if r:result['image_source']='AI-generated illustration · not a product photo'
 return result
def json_fetch(url,kind):
 with db() as c:hit=c.execute('SELECT body FROM cache WHERE url=? AND expires>?',(url,time.time())).fetchone()
 if hit:return json.loads(hit['body'])
 if kind=='upc':limit('provider:upc',90,86400)
 else:limit('provider:'+kind,8 if kind.endswith('search') else 12,60)
 try:
  r=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'PantryPortal/0.2 (https://www.pantriportal.com)','Accept':'application/json'}),timeout=12)
  with r:d=json.loads(r.read(2_000_000))
 except urllib.error.HTTPError as e:
  if e.code==404:return {}
  raise Problem(502,'A free product service is temporarily unavailable or has reached its quota.')
 except Exception:raise Problem(502,'A product service did not respond. Try another source or enter the item manually.')
 with db() as c:
  c.execute('DELETE FROM cache WHERE expires<?',(time.time(),));c.execute('INSERT OR REPLACE INTO cache VALUES(?,?,?)',(url,json.dumps(d),time.time()+86400))
 return d
FIELDS='code,product_name,product_name_en,brands,categories,quantity,image_front_url,image_front_small_url,image_url,ingredients_text,allergens,product_type'
def fact_product(p,kind):
 host,label=FACTS[kind];name=p.get('product_name') or p.get('product_name_en') or ''
 brand=p.get('brands','');brand=', '.join(brand) if isinstance(brand,list) else str(brand)
 return {'name':name[:160],'brand':brand[:160],'barcode':str(p.get('code',''))[:14],'category':str(p.get('categories','')).split(',')[0][:120],'weight':str(p.get('quantity',''))[:80],'image':safe_image(p.get('image_front_url') or p.get('image_url') or p.get('image_front_small_url') or ''),'image_source':label,'source_url':'https://'+host+'/product/'+str(p.get('code','')),'ingredients':str(p.get('ingredients_text',''))[:3000],'allergens':str(p.get('allergens',''))[:1000],'is_food':kind=='food'}
def lookup(code='',query='',source='food'):
 def facts(kind):
  host,_=FACTS[kind]
  if code:
   d=json_fetch('https://'+host+'/api/v2/product/'+code+'.json?fields='+FIELDS,kind+'lookup');p=d.get('product',{});return [fact_product(p,kind)] if d.get('status')==1 and (p.get('product_name') or p.get('product_name_en')) else []
  if kind=='food':
   hits=json_fetch('https://search.openfoodfacts.org/search?'+urllib.parse.urlencode({'q':query,'page_size':3}),'foodsearch').get('hits',[])
   out=[]
   for hit in hits:
    try:
     detail=json_fetch('https://'+host+'/api/v2/product/'+str(hit['code'])+'.json?fields='+FIELDS,'foodlookup').get('product') or hit
    except Problem:detail=hit
    out.append(fact_product(detail,kind))
   return out
  url='https://'+host+'/cgi/search.pl?'+urllib.parse.urlencode({'search_terms':query,'search_simple':1,'action':'process','json':1,'page_size':8,'fields':FIELDS})
  return [fact_product(p,kind) for p in json_fetch(url,kind+'search').get('products',[]) if p.get('product_name') or p.get('product_name_en')]
 def upc():
  suffix='lookup?upc='+code if code else 'search?s='+urllib.parse.quote(query)
  d=json_fetch('https://api.upcitemdb.com/prod/trial/'+suffix,'upc');out=[]
  for p in d.get('items',[])[:8]:
   images=[safe_image(x) for x in p.get('images',[])];out.append({'name':str(p.get('title',''))[:160],'brand':str(p.get('brand',''))[:160],'barcode':str(p.get('ean') or p.get('upc') or code)[:14],'category':str(p.get('category',''))[:120],'weight':str(p.get('weight',''))[:80],'image':next((x for x in images if x),''),'image_source':'UPCitemdb','source_url':'https://www.upcitemdb.com/upc/'+str(p.get('upc') or code),'is_food':False})
  return out
 funcs=[lambda:facts('food'),lambda:facts('beauty'),upc] if code or source=='all' else [upc] if source=='general' else [lambda:facts(source if source in FACTS else 'food')]
 results=[];warnings=[]
 futures=[POOL.submit(f) for f in funcs]
 for f in futures:
  try:results.extend(f.result(timeout=16))
  except Exception as e:warnings.append(e.message if isinstance(e,Problem) else 'One source did not respond.')
 seen=set();unique=[]
 for p in results:
  key=(norm(p['name']),p.get('barcode'),p.get('image'))
  if key not in seen and p['name']:seen.add(key);unique.append(p)
 return {'products':unique,'warnings':list(dict.fromkeys(warnings)),'sources':['Open Food Facts','Open Beauty Facts','UPCitemdb']}
def has_image(url):
 if url.startswith('/media/'):return (MEDIA/Path(url).name).is_file()
 url=safe_image(url)
 if not url:return False
 class Redirect(urllib.request.HTTPRedirectHandler):
  def redirect_request(self,req,fp,code,msg,headers,newurl):
   if not safe_image(newurl):raise ValueError('Image redirect rejected')
   return super().redirect_request(req,fp,code,msg,headers,newurl)
 try:
  with urllib.request.build_opener(Redirect()).open(urllib.request.Request(url,method='HEAD',headers={'User-Agent':'PantryPortal/0.2 (https://www.pantriportal.com)'}),timeout=8) as r:return r.status==200 and r.headers.get('Content-Type','').startswith('image/')
 except Exception:return False

def recipe_from_data(d,url=''):
 if not isinstance(d,dict):return None
 typ=d.get('@type',[]);typ=[typ] if isinstance(typ,str) else typ
 if 'Recipe' not in typ:return None
 ingredients=d.get('recipeIngredient',[])
 if not isinstance(ingredients,list):ingredients=[]
 def instructions(value):
  out=[]
  if isinstance(value,str):out.append(value)
  elif isinstance(value,list):
   for x in value:out.extend(instructions(x))
  elif isinstance(value,dict):
   if value.get('text'):out.append(str(value['text']))
   elif value.get('name'):out.append(str(value['name']))
   else:out.extend(instructions(value.get('itemListElement',[])))
  return out
 name=html.unescape(str(d.get('name','')).strip())[:200]
 if not name:return None
 image=d.get('image','')
 if isinstance(image,list):image=next((x for x in image if x), '')
 if isinstance(image,dict):image=image.get('url') or image.get('contentUrl') or ''
 image=image if isinstance(image,str) and image.startswith('https://') and len(image)<1500 else ''
 def ingredient_text(x):
  if isinstance(x,(str,int,float)):return str(x)
  if isinstance(x,dict):return ' '.join(str(x.get(k,'')) for k in ('value','unitText','name') if x.get(k))
  return ''
 author=d.get('author','')
 if isinstance(author,list):author=author[0] if author else ''
 if isinstance(author,dict):author=author.get('name','')
 categories=d.get('recipeCategory',[]);cuisine=d.get('recipeCuisine',[]);keywords=d.get('keywords',[])
 def joined(value):
  if isinstance(value,list):return ', '.join(str(x) for x in value[:20])[:240]
  return str(value or '')[:240]
 rating=d.get('aggregateRating') or {};rating=rating if isinstance(rating,dict) else {}
 nutrition=d.get('nutrition') or {};nutrition=nutrition if isinstance(nutrition,dict) else {}
 nutrition={k:str(nutrition[k])[:60] for k in ('calories','carbohydrateContent','proteinContent','fatContent','fiberContent','sodiumContent','sugarContent') if nutrition.get(k)}
 return {'name':name,'ingredients':[html.unescape(ingredient_text(x))[:300] for x in ingredients[:150] if ingredient_text(x)],
  'instructions':instructions(d.get('recipeInstructions',[]))[:120], 'description':html.unescape(str(d.get('description','')))[:1500],
  'prepTime':str(d.get('prepTime',''))[:40],'cookTime':str(d.get('cookTime',''))[:40],'totalTime':str(d.get('totalTime',''))[:40],
  'yield':joined(d.get('recipeYield',''))[:100],'category':joined(categories),'cuisine':joined(cuisine),'keywords':joined(keywords),
  'author':str(author or '')[:120],'rating':str(rating.get('ratingValue',''))[:20],'ratingCount':str(rating.get('ratingCount') or rating.get('reviewCount') or '')[:20],
  'nutrition':nutrition,'image':image,'source_url':url or str(d.get('url',''))[:1200],'source':urllib.parse.urlsplit(url or str(d.get('url',''))).hostname or 'Imported recipe'}

def recipe_image_worker(jid,recipe,requester,recipe_id,home_id):
 with LOCK:IMAGE_JOBS[jid]['state']='running'
 try:
  from local_images import generate_recipe
  im=generate_recipe(recipe);out=io.BytesIO();im.save(out,format='JPEG',quality=90);b=out.getvalue()
  iid=hashlib.sha256(requester.encode()+b).hexdigest();url='/media/'+iid+'.jpg'
  (MEDIA/(iid+'.jpg')).write_bytes(b)
  with db() as c:
   c.execute('BEGIN IMMEDIATE')
   c.execute('INSERT OR IGNORE INTO media VALUES(?,?,?)',(iid,requester,time.time()))
   table='personal_recipes';row=c.execute('SELECT body FROM personal_recipes WHERE id=? AND home_id=?',(recipe_id,home_id)).fetchone()
   if not row:table='recipes';row=c.execute('SELECT body FROM recipes WHERE id=? AND home_id=?',(recipe_id,home_id)).fetchone()
   if not row:raise Problem(404,'Recipe is no longer available.')
   current=json.loads(row['body'])
   if not current.get('image'):
    current.update(image=url,image_generated=True,image_source='Dish image generated locally')
    c.execute(f'UPDATE {table} SET body=? WHERE id=? AND home_id=?',(json.dumps(current,ensure_ascii=False),recipe_id,home_id))
   else:url=current['image']
  with LOCK:IMAGE_JOBS[jid].update(state='complete',result={'image':url,'image_generated':True})
 except Exception as error:
  ops.record_exception(error,jid)
  ops.append_event(action='image.failed',code='PP-IMAGE',status=503,reference=jid,message='Local image generation failed.')
  with LOCK:IMAGE_JOBS[jid].update(state='failed',code='PP-IMAGE',reference=jid,error='PantriPortal could not create a dish image right now. The recipe is still saved; try opening it again later.')

class PublicRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  validate_public_recipe_url(newurl);return super().redirect_request(req,fp,code,msg,headers,newurl)
def validate_public_recipe_url(url):
 try:
  p=urllib.parse.urlsplit(url)
  if p.scheme!='https' or not p.hostname or p.username or p.password or p.port not in (None,443):raise ValueError()
  addresses={ipaddress.ip_address(x[4][0]) for x in socket.getaddrinfo(p.hostname,443,type=socket.SOCK_STREAM)}
  if not addresses or any(not a.is_global for a in addresses):raise ValueError()
 except Exception:raise Problem(400,'Enter a public HTTPS recipe page URL.')
 return p
def import_recipe_url(url):
 p=validate_public_recipe_url(url);url=urllib.parse.urlunsplit((p.scheme,p.netloc,p.path,p.query,''))
 try:
  op=urllib.request.build_opener(PublicRedirect());req=urllib.request.Request(url,headers={'User-Agent':'PantriPortal/1.0 (+https://www.pantriportal.com)','Accept':'text/html,application/xhtml+xml'})
  with op.open(req,timeout=12) as res:
   if res.status!=200 or 'text/html' not in res.headers.get('Content-Type','').lower():raise Problem(422,'That link did not return a public recipe page.')
   raw=res.read(2_000_000).decode('utf-8','replace')
  for block in re.findall(r'<script[^>]+type=[\"\']application/ld\+json[\"\'][^>]*>(.*?)</script\s*>',raw,re.I|re.S):
   try:root=json.loads(html.unescape(block))
   except Exception:continue
   stack=root if isinstance(root,list) else [root]
   while stack:
    node=stack.pop(0)
    if isinstance(node,dict):
     parsed=recipe_from_data(node,url)
     if parsed:return parsed
     stack.extend(node.get('@graph',[]) if isinstance(node.get('@graph',[]),list) else [])
    elif isinstance(node,list):stack.extend(node)
  raise Problem(422,'This page does not publish recipe details in a format PantriPortal can import. Try a recipe export file instead.')
 except Problem:raise
 except Exception:raise Problem(502,'The recipe page could not be reached. You can import a recipe export file instead.')

def recipe_from_export_text(raw,filename):
 text=raw.decode('utf-8-sig','replace').replace('\r','');lines=[x.strip() for x in text.split('\n')]
 name=Path(filename).stem.replace('_',' ').strip();ingredients=[];instructions=[];section='title';preamble=[]
 for line in lines:
  if not line:continue
  label=re.sub(r'[^a-z]','',line.lower().rstrip(':'))
  if label in ('ingredients','ingredient'):section='ingredients';continue
  if label in ('directions','direction','instructions','instruction','method','preparation','preparations'):section='instructions';continue
  if label in ('notes','note','description'):section='notes';continue
  if section=='title' and (line.lower().startswith('name:') or line.lower().startswith('title:')):
   name=line.split(':',1)[1].strip() or name;continue
  if section=='title' and len(preamble)<3:preamble.append(line)
  elif section=='ingredients':ingredients.append(line)
  elif section=='instructions':instructions.append(line)
 if preamble and (not name or name==Path(filename).stem):name=preamble[0][:200]
 if not ingredients and not instructions:return None
 return {'name':name[:200],'ingredients':ingredients[:150],'instructions':instructions[:120],'source':'Recipe export'} if name else None

def parse_export_file(raw,filename):
 if len(raw)>16_000_000:raise Problem(413,'Choose an export file smaller than 16 MB.')
 out=[];total=0;files=0
 def is_recipe_node(node):
  typ=node.get('@type',[]) if isinstance(node,dict) else []
  return typ=='Recipe' if isinstance(typ,str) else isinstance(typ,list) and 'Recipe' in typ
 def parse_member(content,name):
  nonlocal total,files
  files+=1;total+=len(content)
  if total>50_000_000 or files>1500:raise Problem(413,'This export contains too much data to import at once.')
  if content.startswith(b'\x1f\x8b'):
   try:
    with gzip.GzipFile(fileobj=io.BytesIO(content)) as zipped:content=zipped.read(8_000_001)
   except Exception:return
   if len(content)>8_000_000:raise Problem(413,'An exported recipe is larger than 8 MB.')
   total+=len(content)
   if total>50_000_000:raise Problem(413,'This export contains too much data to import at once.')
  ext=Path(name).suffix.lower()
  if ext in ('.jpg','.jpeg','.png','.gif','.webp','.pdf'):return
  if ext in ('.html','.htm') or b'<html' in content[:2048].lower():
   json_before=len(out)
   rawhtml=content.decode('utf-8','replace')
   for block in re.findall(r'<script[^>]+type=[\"\']application/ld\+json[\"\'][^>]*>(.*?)</script\s*>',rawhtml,re.I|re.S):
    try:node=json.loads(html.unescape(block))
    except Exception:continue
    nodes=node if isinstance(node,list) else [node]
    stack=list(nodes)
    while stack:
     item=stack.pop(0)
     if isinstance(item,dict):
      if is_recipe_node(item):out.append(item)
      stack.extend(item.get('@graph',[]) if isinstance(item.get('@graph'),list) else [])
     elif isinstance(item,list):stack.extend(item)
   if len(out)==json_before:
    class Microformat(HTMLParser):
     def __init__(self):super().__init__();self.active=[];self.data={'name':[],'ingredients':[],'instructions':[],'description':[],'image':[]}
     def handle_starttag(self,tag,attrs):
      attrs=dict(attrs);classes=set((attrs.get('class') or '').split());field=next((k for k,names in {'name':('fn','p-name'),'ingredients':('ingredient','p-ingredient'),'instructions':('instructions','e-instructions'),'description':('summary','p-summary'),'image':('photo','u-photo')}.items() if classes.intersection(names)),None)
      if field:self.active.append({'tag':tag,'field':field,'text':[],'depth':0,'value':attrs.get('src','') if field=='image' else ''})
      for frame in self.active:frame['depth']+=1
     def handle_data(self,data):
      for frame in self.active:frame['text'].append(data)
     def handle_endtag(self,tag):
      for frame in self.active:frame['depth']-=1
      done=[x for x in self.active if x['tag']==tag and x['depth']<=0]
      for frame in done:
       value=frame['value'] or re.sub(r'\s+',' ',' '.join(frame['text'])).strip()
       if value:self.data[frame['field']].append(value)
       self.active.remove(frame)
    parser=Microformat()
    try:parser.feed(rawhtml)
    except Exception:pass
    fields=parser.data;name=next(iter(fields['name']),Path(name).stem)
    if name and fields['ingredients']:
     out.append({'name':name,'ingredients':fields['ingredients'],'instructions':fields['instructions'],'description':next(iter(fields['description']),''),'image':next(iter(fields['image']),''),'source':Path(filename).stem})
   return
  try:
   value=json.loads(content.decode('utf-8-sig'))
   values=value if isinstance(value,list) else value.get('recipes',value.get('items',[value])) if isinstance(value,dict) else []
   if isinstance(values,list):out.extend(x for x in values if isinstance(x,dict))
   return
  except Exception:pass
  parsed=recipe_from_export_text(content,name)
  if parsed:out.append(parsed)
 try:
  if zipfile.is_zipfile(io.BytesIO(raw)):
   with zipfile.ZipFile(io.BytesIO(raw)) as z:
    members=[m for m in z.infolist() if not m.is_dir()]
    if len(members)>1500:raise Problem(413,'This export contains too many files.')
    for m in members:
     if m.file_size>8_000_000:raise Problem(413,'An exported recipe is larger than 8 MB.')
     if m.file_size+total>50_000_000:raise Problem(413,'This export contains too much data to import at once.')
     # Never extract archive members to disk; member paths are treated only as labels.
     parse_member(z.read(m),m.filename)
  else:parse_member(raw,filename)
 except Problem:raise
 except (zipfile.BadZipFile,RuntimeError,ValueError):raise Problem(400,'That recipe export archive could not be read.')
 if not out:raise Problem(422,'No readable recipes were found. Use a provider recipe export, JSON/CSV file, public recipe link, or paste the recipe details.')
 if len(out)>500:raise Problem(413,'Import at most 500 recipes at a time; split this export and try again.')
 return out

def record_activity(c,u,item_id,action,detail=''):
 c.execute('INSERT INTO activity(home_id,actor_id,item_id,action,detail,created) VALUES(?,?,?,?,?,?)',(u['home_id'],u['user_id'],item_id,action,detail[:240],time.time()))

def generated_image(item,user_id,variant=None):
 from local_images import generate
 key='illustration:'+user_id+':'+hashlib.sha256(identity(item).encode()).hexdigest()
 with db() as c:cached=c.execute('SELECT value FROM config WHERE key=?',(key,)).fetchone()
 if variant is None and cached and has_image(cached['value']):return {'image':cached['value'],'image_generated':True,'image_source':'AI-generated illustration · not a product photo'}
 request=dict(item,_seed=secrets.randbits(32),_view=variant) if variant is not None else item
 im=generate(request);out=io.BytesIO();im.save(out,format='JPEG',quality=88);b=out.getvalue()
 iid=hashlib.sha256(user_id.encode()+b).hexdigest();url='/media/'+iid+'.jpg'
 (MEDIA/(iid+'.jpg')).write_bytes(b)
 with db() as c:
  c.execute('INSERT OR IGNORE INTO media VALUES(?,?,?)',(iid,user_id,time.time()))
  c.execute('INSERT OR REPLACE INTO config VALUES(?,?)',('generated:'+url,'local-ai'))
  if variant is None:c.execute('INSERT OR REPLACE INTO config VALUES(?,?)',(key,url))
 return {'image':url,'image_generated':True,'image_source':'AI-generated illustration · not a product photo'}

def image_worker(jid,item,owner,target_id,options=False):
 with LOCK:IMAGE_JOBS[jid]['state']='running'
 try:
  if options:
   choices=[]
   for n in range(3):
    choices.append(generated_image(item,owner,n))
    with LOCK:IMAGE_JOBS[jid]['completed']=n+1
   result={'options':choices}
  else:result=generated_image(item,owner)
  if target_id and not options:
   with db() as c:
    c.execute('BEGIN IMMEDIATE')
    row=c.execute('SELECT body FROM items WHERE id=? AND user_id=?',(target_id,owner)).fetchone()
    if not row:raise Problem(404,'Item no longer exists.')
    current=json.loads(row['body'])
    # Do not overwrite a photo uploaded while generation was running.
    if current.get('image')!=item.get('image',''):raise Problem(409,'The image changed while generating. Refresh to see the newer photo.')
    current.update(result);c.execute('UPDATE items SET body=?,updated=? WHERE id=?',(json.dumps(current),time.time(),target_id))
  with LOCK:IMAGE_JOBS[jid].update(state='complete',result=result)
 except Exception as error:
  ops.record_exception(error,jid)
  ops.append_event(action='image.failed',code='PP-IMAGE',status=503,reference=jid,message='Local image generation failed.')
  with LOCK:IMAGE_JOBS[jid].update(state='failed',code='PP-IMAGE',reference=jid,error='The local image generator is unavailable. Your item is preserved. An administrator can check the model installation and retry.')
def audit_worker(jobid,allow_generate=False):
 with db() as c:rows=c.execute('SELECT id,user_id,body FROM items').fetchall()
 j=JOBS[jobid];j.update(total=len(rows),state='running')
 for row in rows:
  d=json.loads(row['body']);entry={'id':row['id'],'name':d['name'],'status':'ok'}
  try:
   if d.get('image_generated') or not has_image(d.get('image','')):
    if d.get('barcode'):
     found=lookup(code=d['barcode']);candidates=[p for p in found['products'] if p.get('image') and p.get('barcode','').lstrip('0')==d['barcode'].lstrip('0')]
     if candidates and len({p['image'] for p in candidates})==1:
      chosen=candidates[0]
      if has_image(chosen['image']):
       with db() as c:
        c.execute('BEGIN IMMEDIATE')
        latest=c.execute('SELECT body FROM items WHERE id=?',(row['id'],)).fetchone()
        if latest:
         now=json.loads(latest['body'])
         if now.get('image')==d.get('image'):
          now.update(image=chosen['image'],image_source=chosen['image_source'],source_url=chosen['source_url'],image_generated=False);c.execute('UPDATE items SET body=?,updated=? WHERE id=?',(json.dumps(now),time.time(),row['id']));entry['status']='repaired';j['repaired']+=1
         else:entry['status']='changed'
        else:entry['status']='removed'
      else:entry['status']='needs-photo'
     else:entry.update(status='needs-review',candidates=candidates)
    else:
     found=lookup(query=(d.get('brand','')+' '+d['name']).strip()[:100],source='food' if d.get('is_food',True) else 'all')
     entry.update(status='needs-review',candidates=[p for p in found['products'] if p.get('image')])
    if entry['status'] not in ('ok','repaired') and not entry.get('candidates') and not found.get('warnings'):
     if d.get('image_generated') and has_image(d.get('image','')):entry['status']='illustration'
     elif allow_generate:
      result=generated_image(d,row['user_id'])
      with db() as c:
       c.execute('BEGIN IMMEDIATE');latest=c.execute('SELECT body FROM items WHERE id=?',(row['id'],)).fetchone()
       if latest:
        now=json.loads(latest['body'])
        if now.get('image')==d.get('image'):
         now.update(result);c.execute('UPDATE items SET body=?,updated=? WHERE id=?',(json.dumps(now),time.time(),row['id']));entry['status']='generated';j['generated']+=1
        else:entry['status']='changed'
    if entry['status'] not in ('ok','repaired','generated','illustration'):j['unresolved']+=1
  except Exception as e:entry.update(status='retry',message=e.message if isinstance(e,Problem) else 'Image could not be checked.');j['unresolved']+=1
  with LOCK:j['checked']+=1;j['results'].append(entry)
  if entry['status'] not in ('ok','repaired','generated','illustration') and len(rows)>1:time.sleep(1)
 j['state']='complete'

def recipe_providers():
 providers=[
  {'id':'pepperplate','name':'Pepperplate','url':'https://www.pepperplate.com/','help':'https://pepperplate.zendesk.com/hc/en-us/articles/360039223771-Exporting-Recipe-Data','method':'Export your full library as a ZIP of recipe text files, then upload the ZIP; public links and paste are also supported','note':"Choose My Account → Export Recipes → Export Recipe Data. PantriPortal imports the provider's text ZIP; live account sync is not available."},
  {'id':'allrecipes','name':'Allrecipes','url':'https://www.allrecipes.com/','method':'Public recipe link or paste recipe details','note':'Use a recipe page that exposes structured recipe data, or copy details into a JSON/CSV import. Private saved collections are not read.'},
  {'id':'epicurious','name':'Epicurious','url':'https://www.epicurious.com/','method':'Public recipe link or paste recipe details','note':'Import supported public recipe pages. Private recipe-box sync is not enabled.'},
  {'id':'thekitchn','name':'The Kitchn','url':'https://www.thekitchn.com/','method':'Public recipe link or paste recipe details','note':'Import a public page when it includes structured recipe data.'},
  {'id':'budgetbytes','name':'Budget Bytes','url':'https://www.budgetbytes.com/','method':'Public recipe link or paste recipe details','note':'Import a public page when it includes structured recipe data.'},
  {'id':'paprika','name':'Paprika Recipe Manager','url':'https://www.paprikaapp.com/','help':'https://dev.paprikaapp.com/help/windows/','method':'Upload a .paprikarecipes archive, Paprika HTML export ZIP, or paste recipe details','note':'Use File → Export. PantriPortal reads Paprika recipe archives and recipe HTML metadata; private cloud-account sync is not available.'},
  {'id':'anylist','name':'AnyList','url':'https://www.anylist.com/','method':'Share/send a recipe copy, paste details, or import a public source link','note':'AnyList supports sharing recipe copies and public source links. PantriPortal does not connect to AnyList accounts.'},
  {'id':'copyme','name':'Copy Me That','url':'https://www.copymethat.com/','method':'Public recipe link or paste recipe details','note':'Use public recipe pages or bring a supported JSON/CSV export if available in your account.'},
  {'id':'nytcooking','name':'NYT Cooking','url':'https://cooking.nytimes.com/','method':'Public recipe link or paste recipe details','note':'Private subscriber collections are not synced. Import supported public recipe pages or paste your recipe details.'},
  {'id':'foodnetwork','name':'Food Network','url':'https://www.foodnetwork.com/','method':'Public recipe link or paste recipe details','note':'Import supported public recipe pages; account favorites are not synced.'},
  {'id':'bbcgoodfood','name':'BBC Good Food','url':'https://www.bbcgoodfood.com/','method':'Public recipe link or paste recipe details','note':'Import supported public recipe pages or paste recipe details.'},
  {'id':'seriouseats','name':'Serious Eats','url':'https://www.seriouseats.com/','method':'Public recipe link or paste recipe details','note':'Import supported public recipe pages or paste recipe details.'},
  {'id':'tasteofhome','name':'Taste of Home','url':'https://www.tasteofhome.com/','method':'Public recipe link or paste recipe details','note':'Import supported public recipe pages or paste recipe details.'},
  {'id':'simplyrecipes','name':'Simply Recipes','url':'https://www.simplyrecipes.com/','method':'Public recipe link or paste recipe details','note':'Import supported public recipe pages or paste recipe details.'},
  {'id':'marthastewart','name':'Martha Stewart','url':'https://www.marthastewart.com/','method':'Public recipe link or paste recipe details','note':'Import supported public recipe pages or paste recipe details.'},
  {'id':'tasty','name':'Tasty','url':'https://tasty.co/','method':'Public recipe link or paste recipe details','note':'Import supported public recipe pages or paste recipe details.'},
  {'id':'recipekeeper','name':'Recipe Keeper','url':'https://recipekeeperonline.com/','method':'Use a public source link, share a recipe, or import JSON/CSV','note':'Export options depend on your Recipe Keeper version. PantriPortal does not sign into the service.'},
  {'id':'cookbook','name':'CookBook','url':'https://cookbookmanager.com/','help':'https://help.cookbookmanager.com/en/article/how-do-i-bulk-export-or-back-up-all-of-my-recipes-1o6k9my/','method':'Upload your CookBook-format ZIP export or paste recipe details','note':'Export from Settings → Backup / Export recipes → CookBook. PantriPortal imports recipe records from the ZIP; account cloud sync is not available.'},
  {'id':'other','name':'Other service or website','url':'','method':'Public recipe link, JSON/CSV file, or paste recipe details','note':'Works with public pages that expose Schema.org recipe data and compatible JSON/CSV exports.'}
 ]
 return providers

class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def send(self,status,data,headers=None):
  self.response_status=status
  if isinstance(data,dict):
   identifier=data.get('id')
   if isinstance(identifier,str) and re.fullmatch('[a-f0-9]{24,64}',identifier):self.audit_target=identifier
   record=data.get('item') or data.get('recipe')
   if isinstance(record,dict):self.audit_target=record.get('id','')
  b=json.dumps(data,allow_nan=False).encode()
  self._pending_response=(status,b,{'Content-Type':'application/json','Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Length':str(len(b)),**(headers or {})})
 def flush_response(self):
  if not hasattr(self,'_pending_response'):return
  status,body,headers=self._pending_response;self.send_response(status)
  for key,value in headers.items():self.send_header(key,value)
  self.end_headers();self.wfile.write(body)
 def static(self,p):
  allowed={'/':'index.html','/index.html':'index.html','/app.js':'app.js','/features.js':'features.js','/features.css':'features.css','/pantriportal.css':'pantriportal.css','/web-assets/assets/header-logo-dashboard.png':'web-assets/assets/header-logo-dashboard.png','/web-assets/assets/grim-recipe-transparent.png':'web-assets/assets/grim-recipe-transparent.png','/web-assets/assets/tomato-spinach-pasta.png':'web-assets/assets/tomato-spinach-pasta.png','/web-assets/assets/creamy-chicken-pasta.png':'web-assets/assets/creamy-chicken-pasta.png','/web-assets/assets/cheesy-spinach-omelet.jpg':'web-assets/assets/cheesy-spinach-omelet.jpg','/web-assets/assets/tomato-black-bean-skillet.jpg':'web-assets/assets/tomato-black-bean-skillet.jpg','/web-assets/assets/pea-cheese-pasta.jpg':'web-assets/assets/pea-cheese-pasta.jpg','/web-assets/assets/spinach-egg-bake.jpg':'web-assets/assets/spinach-egg-bake.jpg','/web-assets/assets/recipe-dish-default.svg':'web-assets/assets/recipe-dish-default.svg','/product-placeholder.svg':'product-placeholder.svg','/vendor/zxing-browser.min.js':'vendor/zxing-browser.min.js','/vendor/tesseract.min.js':'vendor/tesseract.min.js'}
  if p.startswith('/web-assets/assets/'):
   name=p.removeprefix('/web-assets/assets/')
   if re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}',name):allowed[p]='web-assets/assets/'+name
  allowed.update({'/medicine-benefits.js':'medicine-benefits.js','/prescription-label.js':'prescription-label.js','/prescription-scan.js':'prescription-scan.js','/medicine.js':'medicine.js','/navigation.js':'navigation.js','/kitchen.js':'kitchen.js','/kitchen.css':'kitchen.css','/admin.js':'admin.js','/home-sections.js':'home-sections.js','/admin.css':'admin.css','/migration.js':'migration.js','/bootstrap.js':'bootstrap.js','/mode-data.js':'mode-data.js','/modes.js':'modes.js','/manifest.webmanifest':'manifest.webmanifest','/sw.js':'sw.js','/favicon.ico':'favicon.ico'})
  for name in ['config.json','preprocessor_config.json','onnx/model_quantized.onnx']:
   rel='models/Xenova/mobilevit-small/'+name;allowed['/'+rel]=rel
  for name in ['config.json','preprocessor_config.json','tokenizer.json','tokenizer_config.json','special_tokens_map.json','merges.txt','vocab.json','onnx/model_quantized.onnx']:
   rel='models/Xenova/clip-vit-base-patch32/'+name;allowed['/'+rel]=rel
  if p not in allowed:return False
  f=ROOT/allowed[p];b=f.read_bytes();self.send_response(200)
  content_type='application/manifest+json' if p=='/manifest.webmanifest' else mimetypes.guess_type(str(f))[0] or 'application/octet-stream'
  self.send_header('Content-Type',content_type);self.send_header('Content-Length',str(len(b)))
  self.send_header('Cache-Control','no-cache');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer');self.end_headers();self.wfile.write(b);return True
 def body(self,maxsize=45000):
  if hasattr(self,'_cached_body'):return self._cached_body
  try:
   n=int(self.headers.get('Content-Length','0'))
   if not 0<n<=maxsize:raise ValueError()
   if 'application/json' not in self.headers.get('Content-Type',''):raise ValueError()
   d=json.loads(self.rfile.read(n))
   if not isinstance(d,dict):raise ValueError()
   self._cached_body=d
   return d
  except (ValueError,UnicodeDecodeError):raise Problem(400,'The request is invalid or too large.')
 def user(self,required=True,admin=False):
  token=''
  try:token=SimpleCookie(self.headers.get('Cookie',''))['pp_account'].value
  except Exception:pass
  with db() as c:u=c.execute('SELECT s.*,u.name,u.role,u.home_id,u.home_role,u.approved,u.disabled,h.name AS home_name,h.join_code FROM sessions s JOIN users u ON u.id=s.user_id LEFT JOIN homes h ON h.id=u.home_id WHERE s.token=? AND expires>?',(hashlib.sha256(token.encode()).hexdigest(),time.time())).fetchone()
  if u and (not u['approved'] or u['disabled']):u=None
  self.actor=u
  if not u and required:raise Problem(401,'Sign in to save items and photos across your devices.')
  if u and self.command!='GET' and not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),u['csrf']):raise Problem(403,'Refresh this page and try again.')
  if admin and (not u or not ops.permissions(u)):raise Problem(403,'Administrator access is required.')
  return u
 def items(self,u):
  with db() as c:rows=c.execute('SELECT id,body,user_id,updated FROM items WHERE user_id IN (SELECT id FROM users WHERE home_id=? AND approved=1) ORDER BY updated DESC',(u['home_id'],)).fetchall()
  return [dict(json.loads(r['body']),id=r['id'],updated=r['updated']) for r in rows]
 def check_image_owner(self,url,u):
  if url.startswith('/media/'):
   with db() as c:row=c.execute('SELECT user_id FROM media WHERE id=?',(Path(url).stem,)).fetchone();owner=c.execute('SELECT home_id FROM users WHERE id=?',(row['user_id'],)).fetchone() if row else None
   if not row or not owner or owner['home_id']!=u['home_id']:raise Problem(403,'Upload a photo to this household before using it.')
 def dispatch(self):
  parsed=urllib.parse.urlsplit(self.path);p=parsed.path;q=urllib.parse.parse_qs(parsed.query);ip=self.headers.get('X-Real-IP',self.client_address[0])
  if self.command!='GET' and self.headers.get('Origin') not in ORIGINS:raise Problem(403,'Request origin was not accepted.')
  if self.command=='GET' and self.static(p):return
  if p=='/api/health' and self.command=='GET':
   with db() as c:c.execute('SELECT 1')
   return self.send(200,{'status':'ok','version':APP_VERSION,'build':release_build()})
  if p=='/api/features' and self.command=='GET':
   from local_images import ready
   return self.send(200,{'local_images':ready()})
  if p=='/api/me' and self.command=='GET':
   u=self.user(False);return self.send(200,{'name':u['name'],'role':u['role'],'permissions':sorted(ops.permissions(u)),'full_admin':ops.full_admin(u),'home_role':u['home_role'],'home_name':u['home_name'],'join_code':u['join_code'] if u['home_role']=='admin' else None,'csrf':u['csrf']} if u else {'name':None})
  if p in ('/api/register','/api/login') and self.command=='POST':
   limit('auth:'+ip,15,900);d=self.body();name=d.get('name','');password=d.get('password','')
   if not isinstance(name,str) or not re.fullmatch('[a-zA-Z0-9_.-]{3,40}',name) or not isinstance(password,str) or not 12<=len(password)<=128:raise Problem(400,'Use a 3–40 character username and a password of at least 12 characters.')
   name=name.lower()
   with db() as c:
    c.execute('BEGIN IMMEDIATE')
    if p.endswith('register'):
     if name.casefold()=='dcolanduno':raise Problem(409,'This account name is reserved for the main administrator.')
     role='user';setup=d.get('setup','')
     if setup:
      row=c.execute("SELECT value FROM config WHERE key='admin_setup'").fetchone()
      if not isinstance(setup,str) or not row or not row['value'] or not hmac.compare_digest(hashlib.sha256(setup.encode()).hexdigest(),row['value']):raise Problem(403,'This administrator setup link is invalid or was already used.')
      role='admin'
     code=d.get('join_code','');home=None;home_role='admin';approved=1
     if code:
      if not isinstance(code,str):raise Problem(400,'Enter a household invite code.')
      home=c.execute('SELECT * FROM homes WHERE join_code=?',(code.strip().upper(),)).fetchone()
      if not home:raise Problem(404,'That household invite code was not recognized.')
      home_id=home['id'];home_role='member';approved=0
     else:home_id=secrets.token_hex(12)
     uid=secrets.token_hex(16);salt=secrets.token_hex(16)
     if not code:c.execute('INSERT INTO homes VALUES(?,?,?,?)',(home_id,name+"'s Home",secrets.token_urlsafe(9)[:12].upper(),time.time()))
     try:c.execute('INSERT INTO users(id,name,salt,password,role,created,home_id,home_role,approved) VALUES(?,?,?,?,?,?,?,?,?)',(uid,name,salt,pw(password,salt),role,time.time(),home_id,home_role,approved))
     except sqlite3.IntegrityError:raise Problem(409,'That username is already taken.')
     if not approved:return self.send(202,{'pending':True,'name':name,'message':'Account created. A household administrator must approve your request before you can sign in.'})
     if role=='admin':c.execute("UPDATE config SET value='' WHERE key='admin_setup'");(DATA/'admin-setup-token').unlink(missing_ok=True)
    else:
     row=c.execute('SELECT * FROM users WHERE name=?',(name,)).fetchone();calculated=pw(password,row['salt'] if row else '00'*16)
     if not row or not hmac.compare_digest(calculated,row['password']):
      self.actor={'user_id':row['id'] if row else '', 'name':'Sign-in attempt: '+name}
      raise Problem(401,'Username or password was not recognized.')
     if row['disabled']:raise Problem(403,'This account has been disabled. Contact an administrator.')
     if not row['approved']:raise Problem(403,'Your request to join this household is waiting for administrator approval.')
     uid=row['id'];role=row['role']
    token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(24);c.execute('DELETE FROM sessions WHERE expires<?',(time.time(),));c.execute('INSERT INTO sessions VALUES(?,?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),uid,csrf,time.time()+30*86400))
   self.actor={'user_id':uid,'name':name,'role':role}
   return self.send(200,{'name':name,'role':role,'permissions':sorted(ops.permissions(self.actor)),'home_role':home_role if p.endswith('register') else row['home_role'],'csrf':csrf},{'Set-Cookie':'pp_account='+token+'; Path=/'+COOKIE_SECURE+'; HttpOnly; SameSite=Strict; Max-Age=2592000'})
  if p=='/api/products' and self.command=='GET':
   limit('lookup:'+ip,30,60);code=q.get('barcode',[''])[0];query=q.get('q',[''])[0].strip();source=q.get('source',['food'])[0]
   if code and not re.fullmatch(r'\d{8,14}',code):raise Problem(400,'Enter an 8–14 digit barcode.')
   if not code and not 3<=len(query)<=100:raise Problem(400,'Search with 3–100 characters.')
   return self.send(200,lookup(code,query,source))
  u=self.user();limit('api:'+ip,180,60)
  if ops.handle(self,p,q,u):return
  if p=='/api/logout' and self.command=='POST':
   with db() as c:c.execute('DELETE FROM sessions WHERE token=?',(u['token'],))
   return self.send(200,{'ok':True},{'Set-Cookie':'pp_account=; Path=/'+COOKIE_SECURE+'; HttpOnly; SameSite=Strict; Max-Age=0'})
  if kitchen.handle(self,u,p,q):return
  if medicine.handle(self,u,p,q):return
  if p=='/api/home' and self.command=='GET':
   with db() as c:
    members=c.execute('SELECT id,name,home_role,approved,created FROM users WHERE home_id=? ORDER BY approved DESC,created',(u['home_id'],)).fetchall()
    events=c.execute('SELECT a.action,a.detail,a.created,u.name AS actor FROM activity a JOIN users u ON u.id=a.actor_id WHERE a.home_id=? ORDER BY a.created DESC LIMIT 20',(u['home_id'],)).fetchall()
   return self.send(200,{'name':u['home_name'],'home_role':u['home_role'],'join_code':u['join_code'] if u['home_role']=='admin' else None,'members':[dict(x) for x in members],'activity':[dict(x) for x in events]})
  if p=='/api/home/approve' and self.command=='POST':
   d=self.body();target=d.get('id');action=d.get('action')
   if action not in ('approve','deny'):raise Problem(400,'Choose approve or deny.')
   if u['home_role']!='admin':raise Problem(403,'Only a household administrator can review join requests.')
   with db() as c:
    c.execute('BEGIN IMMEDIATE');target_row=c.execute('SELECT id,name,approved FROM users WHERE id=? AND home_id=?',(target,u['home_id'])).fetchone()
    if not target_row:raise Problem(404,'Household member was not found.')
    if ops.primary_admin(target_row,c) and action=='deny':raise Problem(409,'The main administrator cannot be deleted.')
    if target_row['approved']:raise Problem(409,'This account is already approved.')
    if action=='approve':c.execute('UPDATE users SET approved=1 WHERE id=?',(target,))
    else:c.execute('DELETE FROM users WHERE id=?',(target,))
   return self.send(200,{'ok':True})
  if p=='/api/locations' and self.command=='GET':
   with db() as c:
    names=c.execute('SELECT mode,name FROM home_locations WHERE home_id=? ORDER BY mode,name COLLATE NOCASE',(u['home_id'],)).fetchall()
    rows=c.execute('SELECT body FROM items WHERE user_id IN (SELECT id FROM users WHERE home_id=? AND approved=1)',(u['home_id'],)).fetchall()
   counts=defaultdict(int)
   for row in rows:
    item=json.loads(row['body']);counts[(('kitchen' if item.get('is_food',True) else 'home'),item.get('location',''))]+=1
   return self.send(200,{'locations':[{'mode':r['mode'],'name':r['name'],'items':counts[(r['mode'],r['name'])]} for r in names]})
  if p=='/api/locations' and self.command=='POST':
   d=self.body();mode=d.get('mode');name=d.get('name','')
   if mode not in ('kitchen','home') or not isinstance(name,str) or not 1<=len(name.strip())<=80:raise Problem(400,'Enter a location name (1–80 characters) and choose a home mode.')
   name=name.strip();defaults={'kitchen':('Pantry','Refrigerator','Freezer','Other'),'home':('Bathroom','Utility closet','Laundry room','Garage','Other')}
   if norm(name) in {norm(x) for values in defaults.values() for x in values}:raise Problem(409,'That location is already included by default.')
   with db() as c:
    old=c.execute('SELECT mode,name FROM home_locations WHERE home_id=? AND name=?',(u['home_id'],name)).fetchone()
    if old:raise Problem(409,'This household already has a location with that name.')
    c.execute('INSERT INTO home_locations VALUES(?,?,?,?)',(u['home_id'],mode,name,time.time()))
    row=c.execute('SELECT name FROM home_locations WHERE home_id=? AND mode=? AND name=?',(u['home_id'],mode,name)).fetchone()
    record_activity(c,u,None,'location_added',f"Added {mode} location {row['name']}")
   return self.send(201,{'location':{'mode':mode,'name':name,'items':0}})
  if p=='/api/locations' and self.command=='DELETE':
   mode=q.get('mode',[''])[0];name=q.get('name',[''])[0]
   if mode not in ('kitchen','home') or not name:raise Problem(400,'Choose a location to remove.')
   with db() as c:
    c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT name FROM home_locations WHERE home_id=? AND mode=? AND name=?',(u['home_id'],mode,name)).fetchone()
    if not row:raise Problem(404,'Custom location not found.')
    rows=c.execute('SELECT body FROM items WHERE user_id IN (SELECT id FROM users WHERE home_id=? AND approved=1)',(u['home_id'],)).fetchall()
    count=sum(1 for item in rows if (('kitchen' if json.loads(item['body']).get('is_food',True) else 'home')==mode and json.loads(item['body']).get('location','')==row['name']))
    if count:raise Problem(409,f"Move the {count} item(s) out of {row['name']} before removing this location.")
    c.execute('DELETE FROM home_locations WHERE home_id=? AND mode=? AND name=?',(u['home_id'],mode,row['name']));record_activity(c,u,None,'location_removed',f"Removed {mode} location {row['name']}")
   return self.send(200,{'ok':True})
  if p=='/api/recipe-sources' and self.command=='GET':
   providers=recipe_providers()
   with db() as c:
    rows=c.execute('SELECT provider,status,last_import,recipe_count FROM recipe_sources WHERE user_id=? ORDER BY provider',(u['user_id'],)).fetchall()
   state={r['provider']:dict(r) for r in rows}
   return self.send(200,{'providers':[dict(x,**state.get(x['id'],{}),connected=x['id'] in state) for x in providers]})
  if p=='/api/recipe-sources' and self.command=='DELETE':
   provider=q.get('provider',[''])[0]
   with db() as c:
    c.execute('DELETE FROM recipe_sources WHERE user_id=? AND provider=?',(u['user_id'],provider))
   return self.send(200,{'ok':True})
  if p=='/api/settings' and self.command=='GET':
   with db() as c:r=c.execute('SELECT body FROM user_settings WHERE user_id=?',(u['user_id'],)).fetchone()
   return self.send(200,{'settings':json.loads(r['body']) if r else {'diet':'','allergens':'','servings':'','max_time':''}})
  if p=='/api/settings' and self.command=='PUT':
   d=self.body().get('settings',{});allowed={'diet':80,'allergens':500,'servings':3,'max_time':3};cleaned={}
   for key,maximum in allowed.items():
    value=d.get(key,'')
    if not isinstance(value,str) or len(value)>maximum:raise Problem(400,'Check the length of your recipe preferences.')
    if key in ('servings','max_time') and value and not value.isdigit():raise Problem(400,'Servings and maximum time must be whole numbers.')
    cleaned[key]=value.strip()
   with db() as c:c.execute('INSERT INTO user_settings VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET body=excluded.body,updated=excluded.updated',(u['user_id'],json.dumps(cleaned),time.time()))
   return self.send(200,{'settings':cleaned})
  if p=='/api/recipes' and self.command=='GET':
   with db() as c:
    shared=c.execute('SELECT r.id,r.body,u.name AS owner FROM recipes r JOIN users u ON u.id=r.owner_id WHERE r.home_id=? ORDER BY r.created DESC',(u['home_id'],)).fetchall()
    personal=c.execute('SELECT r.id,r.body,u.name AS owner FROM personal_recipes r JOIN users u ON u.id=r.owner_id WHERE r.owner_id=? ORDER BY r.created DESC',(u['user_id'],)).fetchall()
   rows=[dict(json.loads(r['body']),id=r['id'],owner=r['owner'],visibility='household') for r in shared]+[dict(json.loads(r['body']),id=r['id'],owner=r['owner'],visibility='personal') for r in personal]
   return self.send(200,{'recipes':rows})
  if p=='/api/recipes/import-url' and self.command=='POST':
   d=self.body();url=d.get('url','');provider=d.get('provider','other');visibility=d.get('visibility','household')
   if not isinstance(url,str) or len(url)>1500:raise Problem(400,'Enter a recipe page URL.')
   if not isinstance(provider,str) or not re.fullmatch(r'[a-z0-9_-]{1,40}',provider) or visibility not in ('household','personal'):raise Problem(400,'Choose valid recipe source options.')
   ops.check_integration(provider,url)
   recipe=import_recipe_url(url);recipe['source_provider']=provider;rid=secrets.token_hex(12)
   with db() as c:
    table='personal_recipes' if visibility=='personal' else 'recipes'
    if table=='personal_recipes':c.execute('INSERT INTO personal_recipes VALUES(?,?,?,?,?)',(rid,u['home_id'],u['user_id'],json.dumps(recipe,ensure_ascii=False),time.time()))
    else:c.execute('INSERT INTO recipes(id,home_id,owner_id,body,created) VALUES(?,?,?,?,?)',(rid,u['home_id'],u['user_id'],json.dumps(recipe,ensure_ascii=False),time.time()))
    record_activity(c,u,None,'recipe_added',recipe['name'])
    c.execute("INSERT INTO recipe_sources(user_id,provider,status,last_import,recipe_count) VALUES(?,?,'import_only',?,1) ON CONFLICT(user_id,provider) DO UPDATE SET status='import_only',last_import=excluded.last_import,recipe_count=recipe_sources.recipe_count+1",(u['user_id'],provider,time.time()))
   return self.send(201,{'recipe':dict(recipe,id=rid,owner=u['name'])})
  if p=='/api/recipes/parse-export' and self.command=='POST':
   limit('recipe-export:'+u['user_id'],10,3600);d=self.body(22_000_000);filename=d.get('filename','');encoded=d.get('file','')
   if not isinstance(filename,str) or len(filename)>240 or not isinstance(encoded,str) or len(encoded)>21_400_000:raise Problem(400,'Choose a valid recipe export file.')
   try:raw=base64.b64decode(encoded,validate=True)
   except Exception:raise Problem(400,'That recipe export file could not be read.')
   return self.send(200,{'recipes':parse_export_file(raw,filename)})
  if p=='/api/recipes/import' and self.command=='POST':
   payload=self.body(6_000_000);incoming=payload.get('recipes',[]);visibility=payload.get('visibility','household');provider=payload.get('provider','other')
   if visibility not in ('household','personal'):raise Problem(400,'Choose personal or household recipe visibility.')
   if not isinstance(provider,str) or not re.fullmatch(r'[a-z0-9_-]{1,40}',provider):raise Problem(400,'Choose a supported recipe source.')
   if not isinstance(incoming,list) or not 1<=len(incoming)<=500:raise Problem(400,'Import between 1 and 500 recipes at a time.')
   ops.check_integration(provider)
   saved=[]
   with db() as c:
    c.execute('BEGIN IMMEDIATE')
    for raw in incoming:
     r=recipe_from_data(raw) if isinstance(raw,dict) and '@type' in raw else None
     if not r and isinstance(raw,dict):
      name=str(raw.get('name') or raw.get('title') or '').strip();ingredients=raw.get('ingredients') or raw.get('recipeIngredient') or []
      if isinstance(ingredients,str):ingredients=re.split(r'\n|\||;',ingredients)
      if not isinstance(ingredients,list):ingredients=[]
      instructions=raw.get('instructions') or raw.get('directions') or raw.get('recipeInstructions') or []
      if isinstance(instructions,str):instructions=[x.strip() for x in re.split(r'\n+|(?<=[.!?])\s+(?=[A-Z0-9])',instructions) if x.strip()]
      if not isinstance(instructions,list):instructions=[]
      image=raw.get('image') or raw.get('image_url') or raw.get('recipeImage') or ''
      if isinstance(image,list):image=next((x for x in image if x),'')
      if isinstance(image,dict):image=image.get('url') or image.get('contentUrl') or ''
      if not isinstance(image,str) or not image.startswith('https://') or len(image)>=1500:image=''
      author=raw.get('author','');author=author.get('name','') if isinstance(author,dict) else author
      nutrition=raw.get('nutrition') if isinstance(raw.get('nutrition'),dict) else {}
      nutrition={k:str(nutrition[k])[:60] for k in ('calories','carbohydrateContent','proteinContent','fatContent','fiberContent','sodiumContent','sugarContent') if nutrition.get(k)}
      r={'name':name[:200],'ingredients':[str(x)[:300] for x in ingredients[:150] if str(x).strip()],'instructions':[str(x.get('text') or x.get('name') or x)[:1000] if isinstance(x,dict) else str(x)[:1000] for x in instructions[:120]],'description':str(raw.get('description') or '')[:1500],'prepTime':str(raw.get('prepTime') or '')[:40],'cookTime':str(raw.get('cookTime') or '')[:40],'totalTime':str(raw.get('totalTime') or '')[:40],'yield':str(raw.get('yield') or raw.get('recipeYield') or raw.get('servings') or '')[:100],'category':str(raw.get('category') or raw.get('recipeCategory') or '')[:240],'cuisine':str(raw.get('cuisine') or raw.get('recipeCuisine') or '')[:240],'keywords':str(raw.get('keywords') or '')[:240],'author':str(author or '')[:120],'rating':str(raw.get('rating') or '')[:20],'ratingCount':str(raw.get('ratingCount') or '')[:20],'nutrition':nutrition,'image':image,'source_url':str(raw.get('url') or raw.get('source_url') or '')[:1200],'source':str(raw.get('source') or 'Recipe file')[:120]}
     if not r or not r['name']:continue
     r['source_provider']=provider
     rid=secrets.token_hex(12);table='personal_recipes' if visibility=='personal' else 'recipes'
     if table=='personal_recipes':c.execute('INSERT INTO personal_recipes VALUES(?,?,?,?,?)',(rid,u['home_id'],u['user_id'],json.dumps(r,ensure_ascii=False),time.time()))
     else:c.execute('INSERT INTO recipes(id,home_id,owner_id,body,created) VALUES(?,?,?,?,?)',(rid,u['home_id'],u['user_id'],json.dumps(r,ensure_ascii=False),time.time()))
     record_activity(c,u,None,'recipe_added',r['name']);saved.append(dict(r,id=rid,owner=u['name'],visibility=visibility))
    if not saved:raise Problem(400,'No recipes with a name and ingredient list were found in that file.')
    c.execute("INSERT INTO recipe_sources(user_id,provider,status,last_import,recipe_count) VALUES(?,?,'import_only',?,?) ON CONFLICT(user_id,provider) DO UPDATE SET status='import_only',last_import=excluded.last_import,recipe_count=recipe_sources.recipe_count+excluded.recipe_count",(u['user_id'],provider,time.time(),len(saved)))
   return self.send(201,{'recipes':saved,'added':len(saved),'visibility':visibility,'provider':provider})
  image_request=re.fullmatch('/api/recipes/([a-f0-9]{24})/image',p)
  if image_request and self.command=='POST':
   rid=image_request.group(1);limit('generation:'+u['user_id'],20,3600)
   with db() as c:
    row=c.execute('SELECT body FROM personal_recipes WHERE id=? AND owner_id=? AND home_id=?',(rid,u['user_id'],u['home_id'])).fetchone()
    if not row:row=c.execute('SELECT body FROM recipes WHERE id=? AND home_id=?',(rid,u['home_id'])).fetchone()
   if not row:raise Problem(404,'Recipe not found.')
   recipe=json.loads(row['body'])
   if recipe.get('image'):return self.send(200,{'image':recipe['image'],'image_generated':bool(recipe.get('image_generated'))})
   with LOCK:
    for jid,job in IMAGE_JOBS.items():
     if job.get('recipe_id')==rid and job.get('home_id')==u['home_id'] and job['state'] in ('queued','running'):
      return self.send(202,{'job':jid})
    if sum(j['state'] in ('queued','running') for j in IMAGE_JOBS.values())>=8:raise Problem(429,'The image generator is busy. Try again shortly.')
    for old in list(IMAGE_JOBS):
     if IMAGE_JOBS[old]['created']<time.time()-3600 and IMAGE_JOBS[old]['state'] not in ('queued','running'):del IMAGE_JOBS[old]
    jid=secrets.token_hex(12);IMAGE_JOBS[jid]={'state':'queued','requester':u['user_id'],'home_id':u['home_id'],'recipe_id':rid,'target':None,'identity':'recipe:'+rid,'created':time.time(),'options':False,'owner':u['user_id'],'original_image':'','completed':0}
   IMAGE_POOL.submit(recipe_image_worker,jid,recipe,u['user_id'],rid,u['home_id'])
   return self.send(202,{'job':jid})
  if p=='/api/recipes/image-job' and self.command=='GET':
   with LOCK:j=dict(IMAGE_JOBS.get(q.get('job',[''])[0],{}))
   if not j or j.get('home_id')!=u['home_id'] or not j.get('recipe_id'):raise Problem(404,'Recipe image job not found.')
   return self.send(200,{k:v for k,v in j.items() if k in ('state','result','error','code','reference')})
  m=re.fullmatch('/api/recipes/([a-f0-9]{24})',p)
  if m and self.command=='PUT':
   d=self.body();node={'@type':'Recipe','name':d.get('name',''),'recipeIngredient':d.get('ingredients',[]),'recipeInstructions':d.get('instructions',[]),'description':d.get('description',''),'prepTime':d.get('prepTime',''),'cookTime':d.get('cookTime',''),'totalTime':d.get('totalTime',''),'recipeYield':d.get('yield',''),'recipeCategory':d.get('category',''),'recipeCuisine':d.get('cuisine',''),'keywords':d.get('keywords',''),'author':d.get('author',''),'image':d.get('image',''),'url':d.get('source_url',''),'nutrition':d.get('nutrition',{})};recipe=recipe_from_data(node,d.get('source_url',''))
   if not recipe:raise Problem(400,'A recipe title is required before saving.')
   recipe['source']=str(d.get('source') or recipe.get('source') or 'Recipe import')[:120]
   with db() as c:
    table='personal_recipes';row=c.execute('SELECT owner_id,body FROM personal_recipes WHERE id=? AND home_id=?',(m.group(1),u['home_id'])).fetchone()
    if not row:table='recipes';row=c.execute('SELECT owner_id,body FROM recipes WHERE id=? AND home_id=?',(m.group(1),u['home_id'])).fetchone()
    if not row:raise Problem(404,'Recipe not found.')
    if row['owner_id']!=u['user_id'] and u['home_role']!='admin':raise Problem(403,'Only the recipe owner or household admin can edit it.')
    if json.loads(row['body']).get('guided'):raise Problem(409,'Use the guided recipe editor to preserve ingredient links and step photos.')
    recipe['source_provider']=json.loads(row['body']).get('source_provider','other')
    c.execute(f'UPDATE {table} SET body=? WHERE id=?',(json.dumps(recipe,ensure_ascii=False),m.group(1)))
   return self.send(200,{'recipe':dict(recipe,id=m.group(1),visibility='personal' if table=='personal_recipes' else 'household')})
  if m and self.command=='DELETE':
   with db() as c:
    table='personal_recipes';row=c.execute('SELECT owner_id,body FROM personal_recipes WHERE id=? AND home_id=?',(m.group(1),u['home_id'])).fetchone()
    if not row:table='recipes';row=c.execute('SELECT owner_id,body FROM recipes WHERE id=? AND home_id=?',(m.group(1),u['home_id'])).fetchone()
    if not row:raise Problem(404,'Recipe not found.')
    if row['owner_id']!=u['user_id'] and u['home_role']!='admin':raise Problem(403,'Only the recipe owner or household admin can remove it.')
    c.execute(f'DELETE FROM {table} WHERE id=?',(m.group(1),));record_activity(c,u,None,'recipe_removed',json.loads(row['body'])['name'])
   return self.send(200,{'ok':True})
  if p=='/api/images/generate' and self.command=='POST':
   limit('generation:'+u['user_id'],20,3600);d=self.body();target_id=d.get('id');owner=u['user_id'];options=d.get('options') is True
   if target_id:
    with db() as c:row=c.execute('SELECT body,user_id FROM items WHERE id=?',(target_id,)).fetchone()
    if row and not ops.image_owner_allowed(u,row['user_id']):row=None
    if not row:raise Problem(404,'Item not found.')
    item=json.loads(row['body']);owner=row['user_id']
   else:item=clean(d)
   with LOCK:
    for jid,j in IMAGE_JOBS.items():
     if j['requester']==u['user_id'] and j['target']==target_id and j['identity']==identity(item) and j.get('options',False)==options and j['state'] in ('queued','running'):
      return self.send(202,{'job':jid})
    if sum(j['state'] in ('queued','running') for j in IMAGE_JOBS.values())>=8:raise Problem(429,'The image generator is busy. Try again shortly.')
    for jid in list(IMAGE_JOBS):
     if IMAGE_JOBS[jid]['created']<time.time()-3600 and IMAGE_JOBS[jid]['state'] not in ('queued','running'):del IMAGE_JOBS[jid]
    jid=secrets.token_hex(12);IMAGE_JOBS[jid]={'state':'queued','requester':u['user_id'],'target':target_id,'identity':identity(item),'created':time.time(),'options':options,'owner':owner,'original_image':item.get('image',''),'completed':0}
   IMAGE_POOL.submit(image_worker,jid,item,owner,target_id,options)
   return self.send(202,{'job':jid})
  if p=='/api/images/job' and self.command=='GET':
   with LOCK:j=dict(IMAGE_JOBS.get(q.get('job',[''])[0],{}))
   if not j or j['requester']!=u['user_id'] or not ops.image_owner_allowed(u,j['owner']):raise Problem(404,'Image job not found.')
   return self.send(200,{k:v for k,v in j.items() if k in ('state','result','error','completed','code','reference')})
  if p=='/api/images/select' and self.command=='POST':
   d=self.body()
   with LOCK:j=dict(IMAGE_JOBS.get(d.get('job',''),{}))
   if not j or j['requester']!=u['user_id'] or not ops.image_owner_allowed(u,j['owner']):raise Problem(404,'Image options not found.')
   if j['state']!='complete' or not j.get('options'):raise Problem(409,'Wait for the three images to finish.')
   chosen=next((im for im in j['result']['options'] if im['image']==d.get('image')),None)
   if not chosen:raise Problem(400,'Choose one of the images in this set.')
   if j['target']:
    with db() as c:
     c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT body,user_id FROM items WHERE id=?',(j['target'],)).fetchone()
     member=c.execute('SELECT home_id FROM users WHERE id=?',(row['user_id'],)).fetchone() if row else None
     if not row or row['user_id']!=j['owner'] or not member or not ops.image_owner_allowed(u,j['owner']):raise Problem(404,'Item not found.')
     current=json.loads(row['body'])
     if current.get('image','')!=j['original_image']:raise Problem(409,'This item’s image changed. Refresh the item before choosing a new image.')
     current.update(chosen);c.execute('UPDATE items SET body=?,updated=? WHERE id=?',(json.dumps(current),time.time(),j['target']))
   return self.send(200,chosen)
  if p=='/api/upload' and self.command=='POST':
   limit('upload:'+u['user_id'],30,3600);d=self.body(1_000_000)
   try:
    s=d.get('image','');data=base64.b64decode(s.split(',',1)[1],validate=True)
    if len(data)>650000:raise ValueError()
    im=Image.open(io.BytesIO(data));im=ImageOps.exif_transpose(im);im.thumbnail((1000,1000));im=im.convert('RGB');out=io.BytesIO();im.save(out,format='JPEG',quality=85);b=out.getvalue()
   except Exception:raise Problem(400,'Choose a valid photo smaller than 650 KB after resizing.')
   iid=hashlib.sha256(u['user_id'].encode()+b).hexdigest();(MEDIA/(iid+'.jpg')).write_bytes(b)
   with db() as c:c.execute('INSERT OR IGNORE INTO media VALUES(?,?,?)',(iid,u['user_id'],time.time()))
   return self.send(201,{'image':'/media/'+iid+'.jpg','image_source':'Your photo'})
  if re.fullmatch(r'/media/[a-f0-9]{64}\.jpg',p) and self.command=='GET':
   iid=Path(p).stem
   with db() as c:row=c.execute('SELECT user_id FROM media WHERE id=?',(iid,)).fetchone();member=c.execute('SELECT home_id FROM users WHERE id=?',(row['user_id'],)).fetchone() if row else None
   if not row or not member or not ops.image_owner_allowed(u,row['user_id']):raise Problem(404,'Image not found.')
   f=MEDIA/(iid+'.jpg')
   if not f.is_file():raise Problem(404,'Image not found.')
   b=f.read_bytes();self.send_response(200);self.send_header('Content-Type','image/jpeg');self.send_header('Content-Length',str(len(b)));self.send_header('Cache-Control','private,no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(b);return
  if p=='/api/import' and self.command=='POST':
   d=self.body(2_000_000);incoming=d.get('items',[])
   if not isinstance(incoming,list) or len(incoming)>5000:raise Problem(400,'Import at most 5,000 items.')
   bodies=[clean(i) for i in incoming]
   for body in bodies:self.check_image_owner(body['image'],u)
   digest=hashlib.sha256(json.dumps(incoming,sort_keys=True).encode()).hexdigest();added=0;merged=0
   with db() as c:
    c.execute('BEGIN IMMEDIATE')
    if not c.execute('SELECT 1 FROM imports WHERE user_id=? AND digest=?',(u['user_id'],digest)).fetchone():
     existing={identity(json.loads(r['body'])):r for r in c.execute('SELECT id,body FROM items WHERE user_id IN (SELECT id FROM users WHERE home_id=? AND approved=1)',(u['home_id'],))}
     for body in bodies:
      key=identity(body)
      if key in existing:
       row=existing[key];old=json.loads(row['body']);old['qty']=round(old['qty']+body['qty'],3)
       if old['qty']>100000:raise Problem(400,'Combined quantity is too large.')
       if not old.get('image') and body.get('image'):old.update({k:body[k] for k in ('image','image_source','image_generated')})
       c.execute('UPDATE items SET body=?,updated=? WHERE id=?',(json.dumps(old),time.time(),row['id']));record_activity(c,u,row['id'],'updated',f"Imported {body['name']} (quantity +{body['qty']})");existing[key]={'id':row['id'],'body':json.dumps(old)};merged+=1;continue
      if len(existing)>=5000:raise Problem(409,'This household has reached the 5,000-item limit.')
      iid=secrets.token_hex(12);c.execute('INSERT INTO items VALUES(?,?,?,?)',(iid,u['user_id'],json.dumps(body),time.time()));record_activity(c,u,iid,'added',f"Imported {body['name']}");existing[key]={'id':iid,'body':json.dumps(body)};added+=1
     c.execute('INSERT INTO imports VALUES(?,?)',(u['user_id'],digest))
   return self.send(200,{'added':added,'merged':merged,'items':self.items(u)})
  if p=='/api/items':
   if self.command=='GET':return self.send(200,{'items':self.items(u)})
   if self.command=='POST':
    d=clean(self.body());self.check_image_owner(d['image'],u);merged=False
    with db() as c:
     c.execute('BEGIN IMMEDIATE');rows=c.execute('SELECT id,body FROM items WHERE user_id IN (SELECT id FROM users WHERE home_id=? AND approved=1)',(u['home_id'],)).fetchall()
     match=next((r for r in rows if identity(json.loads(r['body']))==identity(d)),None)
     if match:
      old=json.loads(match['body']);added_qty=d['qty'];d['qty']=round(old['qty']+added_qty,3)
      if old.get('ingredient_refs'):d['ingredient_refs']=old['ingredient_refs']
      if old.get('image') and not old.get('image_generated') and (not d['image'] or d['image_generated']):
       for k in ('image','image_source','image_generated','source_url'):d[k]=old.get(k,'')
      if not d['cost'] and old.get('cost'):d['cost']=old['cost']
      if d['qty']>100000:raise Problem(400,'This quantity is too large.')
      for key in d:
       if d[key] in ('',None):d[key]=old.get(key,d[key])
      iid=match['id'];c.execute('UPDATE items SET body=?,updated=? WHERE id=?',(json.dumps(d),time.time(),iid));record_activity(c,u,iid,'updated',f"Added {added_qty} {d['unit']} of {d['name']}");merged=True
     else:
      if len(rows)>=5000:raise Problem(409,'This household has reached the 5,000-item limit.')
      iid=secrets.token_hex(12);c.execute('INSERT INTO items VALUES(?,?,?,?)',(iid,u['user_id'],json.dumps(d),time.time()));record_activity(c,u,iid,'added',f"Added {d['name']} (quantity {d['qty']})")
    return self.send(201,{'item':dict(d,id=iid),'merged':merged})
  m=re.fullmatch('/api/items/([a-f0-9]{24})(/adjust)?',p)
  if m:
   iid,adjust=m.groups()
   with db() as c:
    c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT body FROM items WHERE id=? AND user_id IN (SELECT id FROM users WHERE home_id=? AND approved=1)',(iid,u['home_id'])).fetchone()
    if not row:raise Problem(404,'Item not found.')
    if adjust and self.command=='POST':
     delta=self.body().get('delta')
     if delta not in (-1,1):raise Problem(400,'Invalid quantity change.')
     d=json.loads(row['body']);d['qty']=min(100000,max(0,round(d['qty']+delta,3)));record_activity(c,u,iid,'used' if delta<0 else 'quantity_added',f"{d['name']}: {delta:+d}; quantity now {d['qty']} {d['unit']}")
    elif self.command=='PUT':
     d=clean(self.body());self.check_image_owner(d['image'],u)
     old=json.loads(row['body'])
     if old.get('ingredient_refs') and (old.get('barcode') and old.get('barcode')==d.get('barcode') or not old.get('barcode') and norm(old['name'])==norm(d['name'])):d['ingredient_refs']=old['ingredient_refs']
     others=c.execute('SELECT id,body FROM items WHERE user_id IN (SELECT id FROM users WHERE home_id=? AND approved=1) AND id<>?',(u['home_id'],iid)).fetchall()
     if any(identity(json.loads(r['body']))==identity(d) for r in others):raise Problem(409,'Another entry already has this product, location and unit. Add units to that entry instead.')
    elif self.command=='DELETE':d=json.loads(row['body']);record_activity(c,u,iid,'removed',f"Removed {d['name']}");c.execute('DELETE FROM items WHERE id=?',(iid,));return self.send(200,{'ok':True})
    else:raise Problem(405,'Method not allowed.')
    c.execute('UPDATE items SET body=?,updated=? WHERE id=?',(json.dumps(d),time.time(),iid))
    if not adjust:record_activity(c,u,iid,'edited',f"Updated {d['name']}")
   return self.send(200,{'item':dict(d,id=iid)})
  if p.startswith('/api/admin/'):
   self.user(admin=True);ops.require(u,ops.legacy_permission(p,self.command))
   if p=='/api/admin/recipes' and self.command=='GET':
    with db() as c:
     shared=c.execute("SELECT r.id,r.body,u.name AS owner,h.name AS home FROM recipes r JOIN users u ON u.id=r.owner_id JOIN homes h ON h.id=r.home_id").fetchall()
     personal=c.execute("SELECT r.id,r.body,u.name AS owner,h.name AS home FROM personal_recipes r JOIN users u ON u.id=r.owner_id JOIN homes h ON h.id=r.home_id").fetchall()
    rows=[dict(json.loads(r['body']),id=r['id'],visibility='household',owner=r['owner'],home=r['home']) for r in shared]+[dict(json.loads(r['body']),id=r['id'],visibility='personal',owner=r['owner'],home=r['home']) for r in personal]
    return self.send(200,{'recipes':rows})
   recipe_admin=re.fullmatch('/api/admin/recipes/([a-f0-9]{24})',p)
   if recipe_admin and self.command=='DELETE':
    with db() as c:
     table='personal_recipes';row=c.execute('SELECT body FROM personal_recipes WHERE id=?',(recipe_admin.group(1),)).fetchone()
     if not row:table='recipes';row=c.execute('SELECT body FROM recipes WHERE id=?',(recipe_admin.group(1),)).fetchone()
     if not row:raise Problem(404,'Recipe not found.')
     c.execute(f'DELETE FROM {table} WHERE id=?',(recipe_admin.group(1),))
    return self.send(200,{'ok':True})
   if p=='/api/admin/users' and self.command=='GET':
    with db() as c:rows=c.execute('SELECT id,name,role,created FROM users ORDER BY name').fetchall()
    return self.send(200,{'users':[dict(r) for r in rows]})
   if p=='/api/admin/role' and self.command=='POST':
    return ops.handle(self,'/api/admin/ops/users',q,u,method_override='PATCH')
   if p=='/api/admin/audit' and self.command=='POST':
    options=self.body()
    with LOCK:
     if any(j['state'] in ('queued','running') for j in JOBS.values()):raise Problem(409,'An image audit is already running.')
     JOBS.clear();jid=secrets.token_hex(12);JOBS[jid]={'state':'queued','checked':0,'total':0,'repaired':0,'generated':0,'unresolved':0,'results':[]}
    threading.Thread(target=audit_worker,args=(jid,options.get('generate') is True),daemon=True).start();return self.send(202,{'job':jid})
   if p=='/api/admin/audit' and self.command=='GET':
    jid=q.get('job',[''])[0];j=JOBS.get(jid)
    if not j:raise Problem(404,'Audit not found. Start another scan.')
    return self.send(200,dict(j))
   if p=='/api/admin/items' and self.command=='GET':
    with db() as c:rows=c.execute('SELECT i.id,i.body,u.name AS owner FROM items i JOIN users u ON u.id=i.user_id').fetchall()
    return self.send(200,{'items':[dict(json.loads(r['body']),id=r['id'],owner=r['owner']) for r in rows]})
   if p=='/api/admin/image' and self.command=='POST':
    d=self.body();url=safe_image(d.get('image',''))
    if not url or not has_image(url):raise Problem(400,'Choose a working product image.')
    with db() as c:
     row=c.execute('SELECT body,user_id FROM items WHERE id=?',(d.get('id',''),)).fetchone()
     if not row:raise Problem(404,'Item not found.')
     if url.startswith('/media/'):
      original=c.execute('SELECT user_id FROM media WHERE id=?',(Path(url).stem,)).fetchone()
      if not original or original['user_id']!=u['user_id']:raise Problem(403,'Upload your own replacement photo first.')
      b=(MEDIA/Path(url).name).read_bytes();newid=hashlib.sha256(row['user_id'].encode()+b).hexdigest();(MEDIA/(newid+'.jpg')).write_bytes(b);c.execute('INSERT OR IGNORE INTO media VALUES(?,?,?)',(newid,row['user_id'],time.time()));url='/media/'+newid+'.jpg'
     body=json.loads(row['body']);body.update(image=url,image_source=str(d.get('image_source',''))[:120],image_generated=False);c.execute('UPDATE items SET body=?,updated=? WHERE id=?',(json.dumps(body),time.time(),d['id']))
    return self.send(200,{'ok':True})
  raise Problem(404,'Route not found.')
 def handle_request(self):
  self.request_id=secrets.token_hex(8);self.actor=None;self.response_status=200;self.error_code='';self.error_message='';self.audit_target=''
  started=time.monotonic()
  if hasattr(self,'_cached_body'):del self._cached_body
  if hasattr(self,'_pending_response'):del self._pending_response
  try:self.dispatch()
  except Problem as e:
   self.error_code=e.code;self.error_message=e.message
   self.send(e.status,{'error':e.message,'code':e.code,'reference':self.request_id})
  except (BrokenPipeError,ConnectionResetError):self.response_status=499
  except Exception as error:
   ops.record_exception(error,self.request_id)
   self.error_code='PP-INTERNAL';self.error_message='Internal failure: '+type(error).__name__
   self.send(500,{'error':'The service could not finish. Your saved inventory was preserved.','code':self.error_code,'reference':self.request_id})
  finally:
   path=urllib.parse.urlsplit(self.path).path
   if path.startswith('/api/') and ops.should_log(self.actor,path,self.response_status,self.client_address[0]):
    action=('error' if self.error_code else self.command.lower())+'.'+path.removeprefix('/api/').replace('/','.')
    match=re.search(r'/([a-f0-9]{24,64})(?:/|$)',path)
    if hasattr(self,'_cached_body'):
     target=self._cached_body.get('id')
     if isinstance(target,str) and re.fullmatch('[a-f0-9]{24,64}',target):self.audit_target=target
    if path.startswith('/api/medicine/'):
     # Record operational outcomes, never patient fields, record IDs or clinical values.
     path='/api/medicine';action=self.command.lower()+'.medicine';target='';message='Medicine request failed.' if self.error_code else ''
    else:target=self.audit_target or (match.group(1) if match else '');message=self.error_message
    ops.append_event(self.actor,self.command,path,action,target=target,status=self.response_status,code=self.error_code,reference=self.request_id,duration=(time.monotonic()-started)*1000,message=message)
   try:self.flush_response()
   except (BrokenPipeError,ConnectionResetError):pass
 do_GET=do_POST=do_PUT=do_PATCH=do_DELETE=handle_request
import admin_ops as ops
import kitchen_ops as kitchen
import medicine_ops as medicine
if __name__=='__main__':
 init();print('Pantry Portal ready at http://127.0.0.1:'+str(PORT),flush=True);ThreadingHTTPServer(('127.0.0.1',PORT),Handler).serve_forever()
