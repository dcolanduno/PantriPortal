"""Public reference lookups. Never send cabinet records or cache search terms to disk."""
import http.client,json,os,re,urllib.request,urllib.parse,urllib.error

class CatalogUnavailable(Exception):pass
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):raise CatalogUnavailable()

def fetch(url,data=None,headers=None):
 try:
  req=urllib.request.Request(url,data=json.dumps(data).encode() if data is not None else None,headers={'User-Agent':'PantriPortal/0.12 (+https://www.pantriportal.com)','Accept':'application/json',**({'Content-Type':'application/json'} if data is not None else {}),**(headers or {})})
  with urllib.request.build_opener(NoRedirect()).open(req,timeout=8) as r:
   raw=r.read(8_000_001)
  if len(raw)>8_000_000:raise CatalogUnavailable()
  return json.loads(raw)
 except urllib.error.HTTPError as e:
  if e.code==404:return {}
  raise CatalogUnavailable() from None
 except (OSError,ValueError,http.client.HTTPException):raise CatalogUnavailable() from None

def ctss(table,term,**params):
 return fetch('https://clinicaltables.nlm.nih.gov/api/'+table+'/v3/search?'+urllib.parse.urlencode({'terms':term,'maxList':8,**params}))
def doctors(term,near=''):
 term=re.sub(r'^\s*(?:dr\.?|doctor)(?:\s+|$)','',term,flags=re.I)
 term=re.sub(r',\s*(?:m\.?d\.?|d\.?o\.?)\s*$','',term,flags=re.I).strip()
 results=[];warnings=[]
 if len(term)<2:return {'results':[],'warnings':['Enter the provider name after the title.'],'google_enabled':bool(os.environ.get('PANTRY_GOOGLE_PLACES_KEY',''))}
 try:
  d=ctss('npi_idv',(term+' '+near).strip(),df='name.full,provider_type,addr_practice.full,addr_practice.phone',ef='NPI')
  for n,row in zip(d[1],d[3]):
   if re.fullmatch(r'\d{10}',str(n)):
    results.append(dict(name=row[0],specialty=row[1],address=row[2],phone=row[3],practice='',source='CMS NPI via NIH',source_url='https://npiregistry.cms.hhs.gov/provider-view/'+str(n)))
 except (CatalogUnavailable,IndexError,KeyError,TypeError):warnings.append('The provider registry is unavailable. Try again or enter details manually.')
 key=os.environ.get('PANTRY_GOOGLE_PLACES_KEY','')
 if key:
  try:
   d=fetch('https://places.googleapis.com/v1/places:searchText',{'textQuery':term+' doctor '+near,'pageSize':8},{'X-Goog-Api-Key':key,'X-Goog-FieldMask':'places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.googleMapsUri,places.attributions'})
   for p in d.get('places',[]):
    results.append(dict(name=p.get('displayName',{}).get('text',''),specialty='',practice='',address=p.get('formattedAddress',''),phone=p.get('nationalPhoneNumber',''),source='Google Maps',source_url=p.get('googleMapsUri','https://maps.google.com/'),attributions=[a.get('provider','') for a in p.get('attributions',[])]))
  except (CatalogUnavailable,KeyError,TypeError):warnings.append('Google Maps search is unavailable. Registry results remain available.')
 words=re.findall(r'\w+',term.casefold())
 # The directory searches addresses too: put actual name matches ahead of street-name matches.
 results.sort(key=lambda r:-sum(any(token.startswith(w) for token in re.findall(r'\w+',r['name'].casefold())) for w in words))
 return {'results':results,'warnings':warnings,'google_enabled':bool(key)}

def drugs(term):
 d=ctss('rxterms',term,ef='STRENGTHS_AND_FORMS,RXCUIS')
 if not isinstance(d,list) or len(d)<4:raise CatalogUnavailable()
 extra=d[2] or {};out=[]
 for i,name in enumerate(d[1]):
  strengths=extra.get('STRENGTHS_AND_FORMS',[]);ids=extra.get('RXCUIS',[])
  forms=strengths[i] if i<len(strengths) else [];codes=ids[i] if i<len(ids) else []
  out.append({'name':name,'source':'NIH RxTerms / RxNorm','forms':[{'strength':s.strip(),'rxcui':str(codes[j]) if j<len(codes) else ''} for j,s in enumerate(forms or [])]})
 return {'results':out,'warnings':[]}

def ndc_candidates(code):
 """Only explicit NDC inputs; never infer a product from an arbitrary Rx barcode."""
 if not isinstance(code,str):return []
 code=code.strip();out=[]
 if re.fullmatch(r'(?:\d{4}-\d{4}-\d{2}|\d{5}-\d{3}-\d{2}|\d{5}-\d{4}-\d|\d{6}-\d{4}-\d{2})',code):return [code]
 digits=code.replace('-','')
 if re.fullmatch(r'\d{5}-\d{4}-\d{2}',code) or re.fullmatch(r'\d{11}',code):
  a,b,c=digits[:5],digits[5:9],digits[9:]
  if a.startswith('0'):out.append(a[1:]+'-'+b+'-'+c)
  if b.startswith('0'):out.append(a+'-'+b[1:]+'-'+c)
  if c.startswith('0'):out.append(a+'-'+b+'-'+c[1:])
 elif re.fullmatch(r'\d{10}',code):out=[code[:4]+'-'+code[4:8]+'-'+code[8:],code[:5]+'-'+code[5:8]+'-'+code[8:],code[:5]+'-'+code[5:9]+'-'+code[9:]]
 elif re.fullmatch(r'\d{12}',code):out=[code[:6]+'-'+code[6:10]+'-'+code[10:]]
 return list(dict.fromkeys(out))

def ndc_lookup(code):
 candidates=ndc_candidates(code)
 if not candidates:return {'results':[]}
 search=' OR '.join('packaging.package_ndc:'+literal(n) for n in candidates)
 data=fetch('https://api.fda.gov/drug/ndc.json?'+urllib.parse.urlencode({'search':search,'limit':10}))
 out=[];seen=set()
 for row in data.get('results',[]):
  for package in row.get('packaging',[]):
   ndc=package.get('package_ndc','')
   if ndc not in candidates or ndc in seen:continue
   seen.add(ndc)
   out.append({'ndc':ndc,'name':row.get('brand_name') or row.get('generic_name',''),'strength':'; '.join(i.get('strength','') for i in row.get('active_ingredients',[]) if i.get('strength')),'manufacturer':row.get('labeler_name','')})
 return {'results':out}

def valid_gtin(code):
 if not isinstance(code,str) or len(code) not in (8,12,13,14) or not code.isascii() or not code.isdigit():return False
 total=sum(int(d)* (3 if (len(code)-2-i)%2==0 else 1) for i,d in enumerate(code[:-1]))
 return (10-total%10)%10==int(code[-1])

def gtin_lookup(code):
 """Match only an exact FDA-harmonized UPC; never infer an NDC from GTIN digits."""
 if not valid_gtin(code):return {'results':[]}
 variants=[code]
 for length in (13,12):
  candidate=code[-length:]
  if len(candidate)==length and code.startswith('0'*(14-length)) and valid_gtin(candidate):variants.append(candidate)
 variants=list(dict.fromkeys(variants))
 search=' OR '.join('openfda.upc:'+literal(v) for v in variants)
 data=fetch('https://api.fda.gov/drug/ndc.json?'+urllib.parse.urlencode({'search':search,'limit':10}))
 out=[];seen=set()
 for row in data.get('results',[]):
  f=row.get('openfda',{});upcs=f.get('upc',[])
  if not any(v in variants for v in upcs):continue
  ndcs={p.get('package_ndc','') for p in row.get('packaging',[]) if p.get('package_ndc')}
  ndc=next(iter(ndcs),'')
  key=(ndc,row.get('brand_name'),row.get('generic_name'))
  if not ndc or key in seen:continue
  seen.add(key);out.append({'ndc':ndc,'name':row.get('brand_name') or row.get('generic_name',''),'strength':'; '.join(i.get('strength','') for i in row.get('active_ingredients',[]) if i.get('strength')),'manufacturer':row.get('labeler_name',''),'gtin':code})
 return {'results':out}

def fda_query(search,limit=12):
 d=fetch('https://api.fda.gov/drug/label.json?'+urllib.parse.urlencode({'search':search,'limit':limit,'sort':'effective_time:desc'}))
 return d.get('results',[])
def literal(s):return '"'+s.replace('\\','\\\\').replace('"','\\"')+'"'
def label_options(name,rxcui):
 if rxcui:rows=fda_query('openfda.rxcui:'+literal(rxcui))
 else:
  # RxTerms display names include a parenthesized route, not part of the brand name.
  term=re.sub(r'\s*\([^)]*\)\s*$','',name).strip()
  rows=fda_query('(openfda.brand_name:'+literal(term)+' OR openfda.generic_name:'+literal(term)+')')
 options=[]
 for row in rows:
  f=row.get('openfda',{});rid=row.get('id','')
  if not re.fullmatch(r'[a-fA-F0-9-]{36}',rid):continue
  options.append({'id':rid,'brand':f.get('brand_name',[]),'generic':f.get('generic_name',[]),'manufacturer':f.get('manufacturer_name',[]),'route':f.get('route',[]),'product_ndc':f.get('product_ndc',[]),'effective_time':row.get('effective_time','')})
 return {'results':options,'warnings':[]}

SECTIONS=[('boxed_warning','Boxed warning'),('indications_and_usage','Uses / indications'),('purpose','Purpose'),('usage','Uses'),('adverse_reactions','Side effects / adverse reactions'),('warnings','Warnings'),('warnings_and_cautions','Warnings and precautions'),('contraindications','Who should not use this medicine'),('drug_interactions','Drug interactions'),('dosage_and_administration','Label dosage and administration'),('pregnancy','Pregnancy'),('nursing_mothers','Breastfeeding'),('pregnancy_or_breast_feeding','Pregnancy / breastfeeding'),('pediatric_use','Use in children'),('geriatric_use','Use in older adults'),('overdosage','Overdose'),('description','Description'),('clinical_pharmacology','How the medicine works'),('storage_and_handling','Storage and handling'),('how_supplied','How supplied'),('information_for_patients','Information for patients'),('patient_medication_information','Patient medication information'),('spl_medguide','Medication guide')]
def label_detail(label_id):
 rows=fda_query('id:'+literal(label_id),1)
 if not rows:return {'label':None}
 row=rows[0];setid=row.get('set_id','');sections=[]
 for key,title in SECTIONS:
  value=row.get(key,[])
  if value:sections.append({'key':key,'title':title,'text':'\n\n'.join(value) if isinstance(value,list) else str(value)})
 # Keep remaining prescribing sections available, rather than implying the summary is exhaustive.
 known={k for k,_ in SECTIONS}|{'id','set_id','version','effective_time','openfda'}
 for key,value in row.items():
  if key not in known and isinstance(value,list) and all(isinstance(v,str) for v in value):sections.append({'key':key,'title':key.replace('_',' ').capitalize(),'text':'\n\n'.join(value)})
 return {'label':{'id':row['id'],'identity':row.get('openfda',{}),'effective_time':row.get('effective_time',''),'sections':sections,'source':'FDA product labeling via openFDA','source_url':'https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid='+setid if re.fullmatch(r'[a-fA-F0-9-]{36}',setid) else 'https://dailymed.nlm.nih.gov/dailymed/'}}


def pharmacies(zip):
 d=ctss('npi_org',zip,maxList=100,df='name.full,addr_practice.full,addr_practice.phone,provider_type',sf='addr_practice.zip',q='licenses.taxonomy.classification:"Pharmacy"')
 if not isinstance(d,list) or len(d)<4:raise CatalogUnavailable()
 rows=[]
 for n,r in zip_rows(d):
  if re.fullmatch(r'\d{10}',str(n)) and len(r)>=4:rows.append({'key':str(n),'name':r[0],'address':r[1],'phone':r[2],'source':'CMS NPI via NIH','source_url':'https://npiregistry.cms.hhs.gov/provider-view/'+str(n)})
 return {'results':rows,'source':'CMS NPI via NIH','note':'Up to 100 registered pharmacies matching this ZIP; not an exhaustive list or confirmation of stock, network participation, dispensing services or price.'}
def zip_rows(d):return zip(d[1],d[3])
