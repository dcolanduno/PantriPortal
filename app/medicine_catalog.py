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
