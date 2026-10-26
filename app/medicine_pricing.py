"""Official GoodRx V2 adapter. Disabled until the operator configures approved access."""
import os,re,base64,hmac,hashlib,urllib.parse,datetime,decimal
import medicine_catalog as catalog

def configured():return os.environ.get('PANTRY_GOODRX_ENABLED')=='1' and bool(os.environ.get('PANTRY_GOODRX_API_KEY')) and bool(os.environ.get('PANTRY_GOODRX_SECRET'))
def status():return {'provider':'GoodRx','configured':configured(),'application_url':'https://www.goodrx.com/developer/apply'}
def ndc11(code):
 if re.fullmatch(r'\d{11}',code):return code
 parts=code.split('-')
 if len(parts)==3 and all(p.isdigit() for p in parts) and tuple(map(len,parts)) in [(4,4,2),(5,3,2),(5,4,1),(5,4,2)]:return '-'.join([parts[0].zfill(5),parts[1].zfill(4),parts[2].zfill(2)]).replace('-','')
 return ''
def normal(s):return re.sub(r'\s+','',str(s)).casefold()
def form(s):return {'tablets':'tablet','capsules':'capsule'}.get(normal(s),normal(s))
def safe_link(value):
 try:
  u=urllib.parse.urlsplit(value)
  return value if u.scheme=='https' and u.hostname in ['www.goodrx.com','goodrx.com'] and not u.username and not u.password else ''
 except (ValueError,TypeError):return ''
def money(value):
 try:
  if isinstance(value,bool):return None
  n=decimal.Decimal(str(value))
  return str(n.quantize(decimal.Decimal('.01'))) if n.is_finite() and 0<=n<=9999999 else None
 except decimal.DecimalException:return None

def compare(rx,fill):
 if not configured():return {'configured':False,'results':[],'reason':'Automatic GoodRx price checks are not available yet. Use the provider links or record pharmacy quotes.'}
 # Never include patient identity, insurance identifiers, directions, Rx number or contact data.
 params={'metric_quantity':fill['quantity'],'location':fill['zip'],'manufacturer_type':'match'}
 code=ndc11(rx.get('ndc',''))
 if rx.get('ndc') and not code:return {'configured':True,'results':[],'reason':'Confirm a formatted ten-digit or eleven-digit NDC for this provider.'}
 if code:params['ndc']=code
 else:params.update(name=rx['name'],form=fill['form'],dosage=rx['strength'])
 params['api_key']=os.environ['PANTRY_GOODRX_API_KEY'];query=urllib.parse.urlencode(params)
 signature=base64.b64encode(hmac.new(os.environ['PANTRY_GOODRX_SECRET'].encode(),query.encode(),hashlib.sha256).digest(),b'__').decode()
 result=catalog.fetch('https://api.goodrx.com/v2/price/compare?'+query+'&sig='+urllib.parse.quote(signature,safe=''))
 d=result.get('data',{})
 try:matched=(normal(d.get('dosage',''))==normal(rx['strength']) and form(d.get('form',''))==form(fill['form']) and decimal.Decimal(str(d.get('metric_quantity',d.get('quantity'))))==decimal.Decimal(fill['quantity']) and str(d.get('days_supply',''))==str(fill['days_supply']))
 except (decimal.DecimalException,TypeError,ValueError):matched=False
 if not matched:return {'configured':True,'results':[],'reason':'Provider returned different or incomplete strength, form, quantity or days supply. No prices were used. Verify the exact fill on GoodRx.'}
 rows=[]
 for p in d.get('prices',[])[:80]:
  amount=money(p.get('price'))
  if amount is None or p.get('type') not in ['cash','coupon','membership']:continue
  rows.append({'pharmacy':str(p.get('pharmacy',''))[:200],'type':p['type'],'price':amount,'membership_fee':money(p.get('program_cost')),'ncpdp':str(p.get('ncpdp') or '')[:7],'url':safe_link(p.get('coupon_url') or d.get('url',''))})
 return {'configured':True,'results':rows,'drug':str(d.get('display',''))[:200],'strength':str(d.get('dosage',''))[:120],'form':str(d.get('form',''))[:120],'quantity':str(d.get('metric_quantity',d.get('quantity',''))),'days_supply':str(d.get('days_supply','')),'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':'GoodRx V2','reason':'Estimates for this fill; verify product, pharmacy location and eligibility. Membership fees are separate. These are not insurance, Gold-member or other plan-specific benefit adjudications.'}


def signed_get(path,params):
 values={**params,'api_key':os.environ['PANTRY_GOODRX_API_KEY']};query=urllib.parse.urlencode(values)
 sig=base64.b64encode(hmac.new(os.environ['PANTRY_GOODRX_SECRET'].encode(),query.encode(),hashlib.sha256).digest(),b'__').decode()
 return catalog.fetch('https://api.goodrx.com/'+path+'?'+query+'&sig='+urllib.parse.quote(sig,safe=''))

def browse(name,zip=''):
 """Read-only examples across common doses; never edits a prescription or uses its private fields."""
 if not configured():return {'configured':False,'variants':[],'reason':'Live GoodRx prices are not connected yet. Saved prices and official price tools are available.'}
 info=signed_get('drug-info',{'name':name}).get('data',{});options=[]
 if not isinstance(info,dict):raise catalog.CatalogUnavailable()
 drugs=info.get('drugs',{})
 if not isinstance(drugs,dict):raise catalog.CatalogUnavailable()
 for f,doses in drugs.items():
  if not isinstance(doses,dict):continue
  for dose in doses:
   if isinstance(f,str) and isinstance(dose,str) and len(f)<=120 and len(dose)<=120:options.append((f,dose))
 options.sort(key=lambda o:(not any(p in o[0].casefold() for p in ['tablet','capsule','caplet']),o[0],o[1]))
 options=options[:6]
 if not options:return {'configured':True,'variants':[],'reason':'No dose options returned. Check the drug name on GoodRx.'}
 def lookup(option):
  f,dose=option;params={'name':name,'form':f,'dosage':dose,'manufacturer_type':'match'}
  if zip:params['location']=zip
  try:
   d=signed_get('v2/price/compare',params).get('data',{})
   if not isinstance(d,dict):return None
   if normal(d.get('dosage',''))!=normal(dose) or form(d.get('form',''))!=form(f):return None
   quantity=decimal.Decimal(str(d.get('metric_quantity',d.get('quantity'))))
   if not quantity.is_finite() or not 0<quantity<=1000000 or not re.fullmatch(r'[1-9]\d{0,2}',str(d.get('days_supply',''))):return None
   rows=[]
   for p in (d.get('prices') or [])[:80]:
    if not isinstance(p,dict):continue
    amount=money(p.get('price'))
    if amount is None or p.get('type') not in ['cash','coupon','membership']:continue
    rows.append({'pharmacy':str(p.get('pharmacy',''))[:200],'type':p['type'],'price':amount,'membership_fee':money(p.get('program_cost')),'url':safe_link(p.get('coupon_url') or d.get('url',''))})
   if not rows:return None
   return {'drug':str(d.get('display') or name)[:200],'strength':dose,'form':f,'quantity':str(quantity),'days_supply':str(d['days_supply']),'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'results':rows}
  except (catalog.CatalogUnavailable,decimal.DecimalException,ValueError,TypeError):return None
 from concurrent.futures import ThreadPoolExecutor
 with ThreadPoolExecutor(max_workers=3) as pool:variants=[v for v in pool.map(lookup,options) if v]
 return {'configured':True,'variants':variants,'reason':'Price examples for up to six common strengths/forms. Each uses the provider’s standard fill size shown beside its price; verify the product and eligibility. Membership fees are separate. These are not personalized insurance or Gold-member copays. Other strengths may be available on GoodRx.'}


# Shared public catalog only. No user IDs, drug searches, ZIPs or profiles enter this cache.
import threading,time,json
_public_lock=threading.Lock()
_public_catalog=None
_public_loaded=0
_public_fetched=''

def public_prices(name):
 global _public_catalog,_public_loaded,_public_fetched
 with _public_lock:
  if _public_catalog is None or time.monotonic()-_public_loaded>=3600:
   data=catalog.fetch('https://api.costplusdrugs.com/pricelist/cpd')
   if not isinstance(data,list):raise catalog.CatalogUnavailable()
   _public_catalog=data;_public_loaded=time.monotonic();_public_fetched=datetime.datetime.now(datetime.timezone.utc).isoformat()
  products=_public_catalog;fetched=_public_fetched
 def key(s):return re.sub(r'\s*\((?:Oral Pill|Oral Liquid|Oral|Topical|Injectable|Inhalant|Ophthalmic|Otic|Nasal|Rectal|Vaginal|Transdermal)\)\s*$','',str(s),flags=re.I).strip().casefold()
 target=key(name);rows=[];seen=set()
 for p in products:
  if not isinstance(p,dict):continue
  exact=key(p.get('medication_name',''))==target;brand=key(p.get('brand_name',''))==target
  if not target or (not exact and not brand):continue
  channel=p.get('cpd_channel') or {}
  if not isinstance(channel,dict) or channel.get('currency','USD')!='USD':continue
  price=money(channel.get('sample_pack_price_total_to_patient_without_shipping'))
  shipping=money(channel.get('cash_shipping_cost'));total=money(channel.get('sample_pack_price_w_shipping_dispensing'))
  if price is None:continue
  url=p.get('url','')
  try:
   u=urllib.parse.urlsplit(url)
   if u.scheme!='https' or u.hostname not in ['costplusdrugs.com','www.costplusdrugs.com'] or u.username or u.password:continue
  except (TypeError,ValueError):continue
  volume=str(p.get('sample_volume',''))[:120]
  if not volume:continue
  k=(p.get('medication_name'),p.get('strength'),p.get('form'),volume,price,p.get('brand_generic'))
  if k in seen:continue
  seen.add(k);rows.append({'name':str(p.get('medication_name',''))[:160],'strength':str(p.get('strength',''))[:120],'form':str(p.get('form',''))[:120],'fill_size':volume,'price':price,'shipping':shipping,'total':total,'dispensing_fee':money(channel.get('cash_dispensing_fee')),'in_stock':channel.get('in_stock') is True,'kind':str(p.get('brand_generic',''))[:40],'generic_alternative':not exact and p.get('brand_generic')=='Generic','url':url})
 rows.sort(key=lambda r:tuple(float(v) if re.fullmatch(r'\d+(?:\.\d+)?',v) else v.casefold() for v in re.split(r'(\d+(?:\.\d+)?)',r['strength'])))
 return {'results':rows[:100],'source':'Cost Plus Drugs public price catalog','fetched_at':fetched,'notice':'Mail-order cash price examples, not nearby pharmacy or insurance quotes. Fill sizes are supplied by the pharmacy; dispensing is included in the cash price, standard shipping is shown separately. No purchase, transfer or prescription change is made. Catalog prices are cached up to one hour; verify on the pharmacy product page.'}

# Public, documented LowerScript MCP interface. No patient identifiers or search cache.
_local_calls=[]
_local_lock=threading.Lock()

def local_prices(name,zip,strength=''):
 name=re.sub(r'\s*\((?:Oral Pill|Oral Liquid|Oral|Topical|Injectable|Inhalant|Ophthalmic|Otic|Nasal|Rectal|Vaginal|Transdermal)\)\s*$','',name,flags=re.I).strip()
 if not name or not re.fullmatch(r'\d{5}',zip):raise ValueError('Drug name and five-digit ZIP required.')
 with _local_lock:
  now=time.monotonic();_local_calls[:]=[t for t in _local_calls if now-t<86400]
  if len(_local_calls)>=200 or sum(now-t<3600 for t in _local_calls)>=20 or sum(now-t<60 for t in _local_calls)>=3:
   return {'results':[],'status':'rate_limited','notice':'Automatic local pricing has reached its provider allowance. Try again later. Mail-order prices remain separate.'}
  _local_calls.append(now)
 args={'drug':name,'zip':zip}
 if strength:args['strength']=strength
 raw=catalog.fetch('https://www.lowerscript.com/.netlify/functions/mcp',{'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'get_prices','arguments':args}})
 try:
  result=raw['result']
  if result.get('isError'):raise catalog.CatalogUnavailable()
  d=json.loads(next(c['text'] for c in result['content'] if c.get('type')=='text'))
  if not isinstance(d,dict):raise catalog.CatalogUnavailable()
 except (KeyError,ValueError,TypeError,AttributeError,StopIteration):raise catalog.CatalogUnavailable() from None
 if not d.get('matched'):
  return {'results':[],'status':'no_prices','notice':'The local pricing service has no prices for this medicine or ZIP. It currently serves FL, TX, AZ, NC, SC, GA, IL and CA. No calls or manual quotes are needed; retry here later.'}
 # Never accept another ZIP or an unidentifiable/default fill without labels.
 drug=str(d.get('drug',''))[:200];dose=str(d.get('priced_strength',''))[:120]
 def compact(v):return re.sub(r'\s+','',v).casefold()
 requested=re.sub(r'[^a-z0-9]+',' ',name.casefold()).strip()
 actual=re.sub(r'[^a-z0-9]+',' ',drug.casefold()).strip()
 if not requested or not (actual==requested or re.match(re.escape(requested)+r' \d',actual)) or d.get('zip')!=zip or not dose or (strength and compact(dose)!=compact(strength)):
  raise catalog.CatalogUnavailable()
 try:
  quantity=decimal.Decimal(str(d.get('quantity','')));days=decimal.Decimal(str(d.get('days','')))
  if not quantity.is_finite() or quantity<=0 or not days.is_finite() or days<=0:raise ValueError()
 except (decimal.DecimalException,ValueError):raise catalog.CatalogUnavailable() from None
 def safe(v):
  try:
   p=urllib.parse.urlsplit(v)
   return v if p.scheme=='https' and p.hostname in ('www.lowerscript.com','lowerscript.com') and not p.username and not p.password else ''
  except (ValueError,TypeError):return ''
 rows=[];outside=0;unknown=0
 for p in (d.get('pharmacies') or [])[:10]:
  if not isinstance(p,dict) or not p.get('name') or p.get('isOnlineOnly') is True:continue
  price=money(p.get('price_usd'))
  if price is None:continue
  try:
   distance=decimal.Decimal(str(p.get('distance','')))
   if not distance.is_finite() or distance<0:raise ValueError()
  except (decimal.DecimalException,ValueError):unknown+=1;continue
  if distance>20:outside+=1;continue
  rows.append({'pharmacy':str(p['name'])[:200],'price':price,'address':', '.join(str(p.get(k,''))[:200] for k in ('address1','city','state','postalCode') if p.get(k)),'distance':str(distance)})
 rows.sort(key=lambda r:decimal.Decimal(r['price']))
 card=d.get('card') or {}
 return {'radius_miles':20,'coverage_complete':False,'provider_result_limit':10,'outside_radius':outside,'unknown_distance':unknown,'results':rows,'status':'ok' if rows else 'no_prices','drug':drug,'strength':dose,'quantity':str(quantity),'days_supply':str(days),'source':'LowerScript','checked_at':str(d.get('as_of',''))[:80],'url':safe(d.get('page_url','')),'card_url':safe(d.get('card_page_url','')),'card':{k:str(card.get(k,''))[:40] for k in ('bin','pcn','group')},'notice':'LowerScript discount-card prices, not insurance or GoodRx prices. Cannot be combined with insurance, Medicare or Medicaid. Show the LowerScript card to use these prices. The provider supplies the labeled fill size; prices can change. No prescription, purchase or transfer is made.'}
