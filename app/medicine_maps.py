"""Address-only, bounded in-memory geocoding for private doctor cards."""
import hashlib,math,threading,time,urllib.parse
import medicine_catalog as catalog

_cache={}
_lock=threading.Lock()

def office_map(address):
 key=hashlib.sha256(address.strip().casefold().encode()).hexdigest()
 with _lock:
  cached=_cache.get(key)
  if cached and cached[0]>time.monotonic():return dict(cached[1])
 result={'available':False,'reason':'unmatched'}
 try:
  data=catalog.fetch('https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?'+urllib.parse.urlencode({'address':address,'benchmark':'Public_AR_Current','format':'json'}))
  matches=data.get('result',{}).get('addressMatches',[])
  if len(matches)>1:result={'available':False,'reason':'ambiguous'}
  if len(matches)==1:
   point=matches[0]['coordinates'];lat=float(point['y']);lon=float(point['x'])
   if not math.isfinite(lat) or not math.isfinite(lon) or not -85<=lat<=85 or not -180<=lon<=180:raise ValueError()
   result={'available':True,'latitude':lat,'longitude':lon,'matched_address':str(matches[0].get('matchedAddress',''))[:500]}
 except (catalog.CatalogUnavailable,KeyError,TypeError,ValueError,AttributeError,IndexError):result={'available':False,'reason':'unavailable'}
 with _lock:
  now=time.monotonic()
  for old in [k for k,v in _cache.items() if v[0]<=now]:_cache.pop(old,None)
  if len(_cache)>=500:_cache.pop(next(iter(_cache)))
  _cache[key]=(now+(86400 if result['available'] else 60),dict(result))
 return result
