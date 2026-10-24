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
