"""Guided recipes, verified ingredient references, personal plans and purchase confirmation."""
import datetime,hashlib,json,math,re,secrets,time,types
from fractions import Fraction
from pathlib import Path
from urllib.parse import quote

_api=None
UNITS={'g':('mass',1),'kg':('mass',1000),'oz':('mass',28.349523125),'lb':('mass',453.59237),
 'ml':('volume',1),'l':('volume',1000),'tsp':('volume',4.92892159375),'tbsp':('volume',14.78676478125),'cup':('volume',236.5882365),
 'each':('each',1),'can':('can',1),'box':('box',1),'bag':('bag',1),'bottle':('bottle',1),'package':('package',1),'clove':('clove',1),'slice':('slice',1)}
ALIASES={'grams':'g','gram':'g','kilograms':'kg','kilogram':'kg','ounces':'oz','ounce':'oz','pounds':'lb','pound':'lb','lbs':'lb','cups':'cup','tablespoons':'tbsp','tablespoon':'tbsp','teaspoons':'tsp','teaspoon':'tsp','milliliters':'ml','liters':'l','units':'each','unit':'each','pieces':'each','piece':'each','cans':'can','boxes':'box','bags':'bag','bottles':'bottle','packages':'package','cloves':'clove','slices':'slice'}

def initialize(namespace):
 global _api
 _api=types.SimpleNamespace(**namespace)
 with _api.db() as c:c.executescript('''
CREATE TABLE IF NOT EXISTS ingredient_catalog(ref TEXT PRIMARY KEY,body TEXT NOT NULL,updated REAL NOT NULL);
CREATE TABLE IF NOT EXISTS meal_plans(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),body TEXT NOT NULL,updated REAL NOT NULL);
CREATE INDEX IF NOT EXISTS plans_user ON meal_plans(user_id,updated);
CREATE TABLE IF NOT EXISTS grocery_lists(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),name TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS grocery_lines(id TEXT PRIMARY KEY,list_id TEXT NOT NULL REFERENCES grocery_lists(id),body TEXT NOT NULL,updated REAL NOT NULL);
CREATE INDEX IF NOT EXISTS grocery_list_lines ON grocery_lines(list_id);
CREATE TABLE IF NOT EXISTS grocery_generations(list_id TEXT NOT NULL REFERENCES grocery_lists(id),digest TEXT NOT NULL,PRIMARY KEY(list_id,digest));
CREATE TABLE IF NOT EXISTS grocery_plan_sources(list_id TEXT NOT NULL REFERENCES grocery_lists(id),plan_id TEXT NOT NULL,body TEXT NOT NULL,PRIMARY KEY(list_id,plan_id));
''')

def fail(message,status=400):raise _api.Problem(status,message)
def text(value,label,maximum=200,required=True):
 if not isinstance(value,str) or len(value)>maximum or (required and not value.strip()):fail('Enter a valid '+label+'.')
 return value.strip()
def number(value,label,maximum=1000000):
 try:
  if isinstance(value,bool):raise ValueError()
  if isinstance(value,str) and ' ' in value.strip():result=sum(float(Fraction(x)) for x in value.split())
  else:result=float(Fraction(value)) if isinstance(value,str) else float(value)
  if not math.isfinite(result) or not 0<result<=maximum:raise ValueError()
  return result
 except (ValueError,TypeError,ZeroDivisionError,OverflowError):fail('Enter a positive '+label+' within the allowed range.')
def unit(value):
 value=ALIASES.get(str(value).strip().lower(),str(value).strip().lower())
 if value not in UNITS:fail('Choose a supported ingredient or purchase unit.')
 return value
def minutes(value):
 try:
  result=int(value)
  if isinstance(value,bool) or str(value).strip()!=str(result) or not 0<=result<=10000:raise ValueError()
  return result
 except (ValueError,TypeError,OverflowError):fail('Enter whole minutes between 0 and 10,000.')
def revision(body):return hashlib.sha256(body.encode()).hexdigest()
def food(item):return item.get('is_food') is not False and not re.search('cleaning|personal care|hardware|clothing|medicine',item.get('category',''),re.I)
def pantry(u,c):
 rows=c.execute('SELECT i.id,i.body FROM items i JOIN users u ON u.id=i.user_id WHERE u.home_id=? AND u.approved=1',(u['home_id'],)).fetchall()
 return [dict(json.loads(r['body']),id=r['id']) for r in rows if food(json.loads(r['body']))]
def product(item,ref,source):
 return {'ref':ref,'name':str(item.get('name',''))[:160],'barcode':str(item.get('barcode',''))[:14],
  'brand':str(item.get('brand',''))[:160],'image':str(item.get('image',''))[:1500],
  'description':str(item.get('description') or item.get('ingredients') or '')[:1500],
  'weight':str(item.get('weight',''))[:80],'source':source,'source_url':str(item.get('source_url',''))[:500]}
def remember(records):
 with _api.db() as c:
  for item in records:c.execute('INSERT INTO ingredient_catalog VALUES(?,?,?) ON CONFLICT(ref) DO UPDATE SET body=excluded.body,updated=excluded.updated',(item['ref'],json.dumps(item),time.time()))

def search(u,query,code='',public=False):
 if code and not re.fullmatch(r'\d{8,14}',code):fail('Use an 8–14 digit barcode.')
 query=text(query,'ingredient search',100,not bool(code))
 with _api.db() as c:stock=pantry(u,c)
 found=[product(i,'pantry:'+i['id'],'Your household pantry') for i in stock if (code and i.get('barcode','').lstrip('0')==code.lstrip('0')) or (not code and query.casefold() in (i['name']+' '+i.get('brand','')).casefold())][:25]
 warnings=[]
 if public:
  _api.limit('ingredient-search:'+u['user_id'],25,60)
  public_records=[]
  if not code:
   try:
    data=_api.json_fetch('https://www.themealdb.com/api/json/v1/1/list.php?i=list','ingredientlist')
    for row in data.get('meals') or []:
     name=row.get('strIngredient') or '';identifier=str(row.get('idIngredient') or '')
     if query.casefold() in name.casefold() and identifier.isdigit():
      public_records.append(product({'name':name,'image':'https://www.themealdb.com/images/ingredients/'+quote(name.replace(' ','_'))+'.png','description':row.get('strDescription') or '', 'source_url':'https://www.themealdb.com/api.php'},'mealdb:'+identifier,'TheMealDB'))
    public_records=sorted(public_records,key=lambda x:(x['name'].casefold()!=query.casefold(),len(x['name'])))[:15]
   except _api.Problem:warnings.append('The generic ingredient database is unavailable. Pantry and product matches can still be used.')
  if code or len(public_records)<5:
   result=_api.lookup(code=code,query=query,source='food');warnings.extend(result.get('warnings',[]))
   for item in result['products']:
    if item.get('is_food') is True and re.fullmatch(r'\d{8,14}',item.get('barcode','')):public_records.append(product(item,'off:'+item['barcode'],'Open Food Facts'))
  remember(public_records);found+=public_records
 return {'ingredients':found,'warnings':warnings,'units':list(UNITS)}

def resolve(ref,u,c,prior=None):
 if not isinstance(ref,str):fail('Choose a verified ingredient match.')
 if ref.startswith('pantry:'):
  match=next((i for i in pantry(u,c) if 'pantry:'+i['id']==ref),None)
  if match:return product(match,ref,'Your household pantry')
 else:
  row=c.execute('SELECT body FROM ingredient_catalog WHERE ref=?',(ref,)).fetchone()
  if row:return json.loads(row['body'])
 if prior and ref in prior:return prior[ref]
 fail('Choose an ingredient from your pantry or a public database result before saving.')

def image(value,h,u):
 if not value:return ''
 if not isinstance(value,str) or not re.fullmatch(r'/media/[a-f0-9]{64}\.jpg',value):fail('Upload a step or recipe photo before using it.')
 h.check_image_owner(value,u);return value

def get_recipe(c,u,rid):
 for table,where,args in [('personal_recipes','owner_id=?',(u['user_id'],)),('recipes','home_id=?',(u['home_id'],))]:
  row=c.execute('SELECT * FROM '+table+' WHERE id=? AND '+where,(rid,*args)).fetchone()
  if row:return table,row,json.loads(row['body'])
 builtins=json.loads((Path(__file__).parent/'builtin-recipes.json').read_text(encoding='utf-8'))
 for r in builtins:
  if r['id']==rid:return None,None,r
 fail('Recipe not found.',404)

def save_recipe(h,u,d,rid=None):
 with _api.db() as c:
  c.execute('BEGIN IMMEDIATE');old={};table='personal_recipes'
  if rid:
   table,row,old=get_recipe(c,u,rid)
   if not row or row['owner_id']!=u['user_id']:fail('Only the recipe creator can use this editor.',403)
   if d.get('revision')!=revision(row['body']):fail('This recipe changed. Reload before saving your edits.',409)
  name=text(d.get('name'),'recipe title');servings=number(d.get('servings'),'serving count',1000)
  entries=d.get('ingredient_lines');steps=d.get('steps')
  if not isinstance(entries,list) or not 1<=len(entries)<=100:fail('Add the full ingredient list, between 1 and 100 ingredients.')
  if not isinstance(steps,list) or not 1<=len(steps)<=100:fail('Add between 1 and 100 cooking steps.')
  prior={i['product']['ref']:i['product'] for i in old.get('ingredient_lines',[])}
  lines=[]
  for entry in entries:
   if not isinstance(entry,dict):fail('Check each ingredient row.')
   record=resolve(entry.get('ref'),u,c,prior);amount=number(entry.get('amount'),'ingredient amount');measure=unit(entry.get('unit'))
   lines.append({'product':record,'amount':amount,'unit':measure,'preparation':text(entry.get('preparation',''),'ingredient preparation',200,False)})
  clean_steps=[]
  for step in steps:
   if not isinstance(step,dict):fail('Enter the instructions one step at a time.')
   clean_steps.append({'text':text(step.get('text'),'cooking instruction',2500),'image':image(step.get('image',''),h,u)})
  visibility=d.get('visibility','personal')
  if visibility not in ('personal','household'):fail('Choose private or household recipe visibility.')
  recipe=dict(old,name=name,servings=servings)
  recipe.update({'yield':str(servings)+' servings','description':text(d.get('description',''),'recipe description',1500,False),
   'ingredient_lines':lines,'ingredients':[f"{i['amount']:g} {i['unit']} {i['product']['name']}"+((', '+i['preparation']) if i['preparation'] else '') for i in lines],
   'steps':clean_steps,'instructions':[s['text'] for s in clean_steps],'image':image(d.get('image',''),h,u),
   'source':'Your recipe','author':u['name'],'guided':True,'source_provider':'created','updated':time.time(),
   'prepTime':'PT'+str(minutes(d.get('prep_minutes',0)))+'M',
   'cookTime':'PT'+str(minutes(d.get('cook_minutes',0)))+'M'})
  rid=rid or secrets.token_hex(12);dest='personal_recipes' if visibility=='personal' else 'recipes'
  if old:c.execute('DELETE FROM '+table+' WHERE id=?',(rid,))
  raw=json.dumps(recipe,ensure_ascii=False);c.execute('INSERT INTO '+dest+'(id,home_id,owner_id,body,created) VALUES(?,?,?,?,?)',(rid,u['home_id'],u['user_id'],raw,time.time()))
  _api.record_activity(c,u,None,'recipe_created' if not old else 'recipe_updated',name)
 return {'recipe':dict(recipe,id=rid,visibility=visibility,owner=u['name']),'revision':revision(raw)}

def canonical_unit(value):
 value=ALIASES.get(str(value).lower().strip(),str(value).lower().strip())
 return UNITS.get(value)
def key(p):return 'barcode:'+p['barcode'].lstrip('0') if p.get('barcode') else 'name:'+_api.norm(p['name'])
def stock_for(p,stock):
 exact=[i for i in stock if p.get('ref')=='pantry:'+i['id'] or p.get('ref') in i.get('ingredient_refs',[])]
 if exact:return exact
 if p.get('barcode'):return [i for i in stock if i.get('barcode','').lstrip('0')==p['barcode'].lstrip('0')]
 return [i for i in stock if _api.norm(i['name'])==_api.norm(p['name'])]

def requirements(u,ids,c,snapshots=None):
 if not isinstance(ids,list) or not 1<=len(ids)<=60 or any(not isinstance(x,str) for x in ids):fail('Choose between 1 and 60 planned meals.')
 needed={};plans=[];stock=pantry(u,c)
 for identifier in dict.fromkeys(ids):
  if snapshots is None:
   row=c.execute('SELECT * FROM meal_plans WHERE id=? AND user_id=?',(identifier,u['user_id'])).fetchone()
   if not row:fail('Planned meal not found.',404)
   plan=json.loads(row['body'])
  else:plan=snapshots[identifier]
  plans.append(dict(plan,id=identifier));r=plan['recipe'];scale=plan['servings']/plan['base_servings']
  entries=r.get('ingredient_lines') or [{'product':{'name':x,'ref':'legacy:'+hashlib.sha256(x.encode()).hexdigest()[:20]},'amount':None,'unit':'each'} for x in r.get('ingredients',[])]
  for entry in entries:
   p=entry['product'];measure=entry['unit'];amount=entry['amount'];family,factor=UNITS[measure];group=(key(p),family if amount is not None else 'unknown')
   if group not in needed:needed[group]={'product':p,'unit':{'mass':'g','volume':'ml'}.get(family,measure),'required':0 if amount is not None else None,'recipes':[],'plan_ids':[]}
   result=needed[group]
   if amount is not None:result['required']+=amount*scale*factor
   result['recipes'].append(r['name']);result['plan_ids'].append(identifier)
 consumed={}
 for (identity,family),line in needed.items():
  matches=stock_for(line['product'],stock);available=0;ambiguous=[]
  if line['required'] is not None:
   for item in matches:
    source=canonical_unit(item.get('unit','each'))
    if source and source[0]==family:
     quantity=max(0,float(item.get('qty',0)))*source[1];left=max(0,quantity-consumed.get(item['id'],0));take=min(left,max(0,line['required']-available));available+=take;consumed[item['id']]=consumed.get(item['id'],0)+take
    elif float(item.get('qty',0))>0:ambiguous.append(f"{item['qty']} {item.get('unit','each')} {item.get('weight','')}".strip())
  line.update(available=round(available,5),needed=round(max(0,line['required']-available),5) if line['required'] is not None else None,
   review=bool(ambiguous) or line['required'] is None,stock_note='; '.join(ambiguous),recipes=list(dict.fromkeys(line['recipes'])),plan_ids=list(dict.fromkeys(line['plan_ids'])))
  if line['required'] is not None:line['required']=round(line['required'],5)
 digest=hashlib.sha256(json.dumps(sorted([(p['id'],p) for p in plans],key=lambda x:x[0]),sort_keys=True).encode()).hexdigest()
 return {'ingredients':list(needed.values()),'digest':digest,'plans':plans,'note':'Exact product/name and compatible units only. US cup, tablespoon and teaspoon measures. Package contents and weight-to-volume conversions require review. Planning does not consume inventory.'}

def owned_list(c,u,lid):
 row=c.execute('SELECT * FROM grocery_lists WHERE id=? AND user_id=?',(lid,u['user_id'])).fetchone()
 if not row:fail('Shopping list not found.',404)
 return row
def line_data(row):return dict(json.loads(row['body']),id=row['id'],revision=revision(row['body']))

def handle(h,u,path,q):
 if not path.startswith('/api/kitchen/'):return False
 tail=path.removeprefix('/api/kitchen/');method=h.command
 if tail=='ingredients' and method=='GET':
  h.send(200,search(u,q.get('q',[''])[0],q.get('barcode',[''])[0],q.get('public',['0'])[0]=='1'));return True
 m=re.fullmatch(r'recipes(?:/([a-f0-9]{24}))?',tail)
 if m:
  rid=m.group(1)
  if method=='GET' and rid:
   with _api.db() as c:
    table,row,r=get_recipe(c,u,rid)
    if not row or row['owner_id']!=u['user_id']:fail('Only the recipe creator can edit this recipe.',403)
   h.send(200,{'recipe':dict(r,id=rid,visibility='personal' if table=='personal_recipes' else 'household'),'revision':revision(row['body'])});return True
  if (method=='POST' and not rid) or (method=='PUT' and rid):h.send(200 if rid else 201,save_recipe(h,u,h.body(400000),rid));return True
 if tail=='plans' and method=='GET':
  with _api.db() as c:rows=c.execute('SELECT * FROM meal_plans WHERE user_id=? ORDER BY json_extract(body,\'$.date\'),updated',(u['user_id'],)).fetchall()
  h.send(200,{'plans':[dict(json.loads(r['body']),id=r['id'],revision=revision(r['body'])) for r in rows]});return True
 if tail=='plans' and method=='POST':
  d=h.body();date=text(d.get('date'),'meal date',10)
  try:datetime.date.fromisoformat(date)
  except ValueError:fail('Choose a valid meal date.')
  slot=d.get('slot','Dinner')
  if slot not in ('Breakfast','Lunch','Dinner','Snack'):fail('Choose a meal slot.')
  with _api.db() as c:
   _,_,r=get_recipe(c,u,text(d.get('recipe_id'),'recipe identifier',100));base=r.get('servings')
   if not base:
    match=re.search(r'\d+(?:\.\d+)?',str(r.get('yield','')));base=float(match[0]) if match else d.get('base_servings')
   base=number(base,'original recipe servings',1000);servings=number(d.get('servings'),'planned servings',1000)
   identifier=secrets.token_hex(12);body={'date':date,'slot':slot,'servings':servings,'base_servings':base,'recipe_id':d['recipe_id'],'recipe':r}
   c.execute('INSERT INTO meal_plans VALUES(?,?,?,?)',(identifier,u['user_id'],json.dumps(body),time.time()))
  h.send(201,{'id':identifier});return True
 m=re.fullmatch(r'plans/([a-f0-9]{24})',tail)
 if m and method=='DELETE':
  with _api.db() as c:
   if not c.execute('DELETE FROM meal_plans WHERE id=? AND user_id=?',(m.group(1),u['user_id'])).rowcount:fail('Planned meal not found.',404)
  h.send(200,{'ok':True});return True
 if tail=='requirements' and method=='POST':
  with _api.db() as c:result=requirements(u,h.body().get('plan_ids'),c)
  h.send(200,result);return True
 if tail=='lists' and method=='GET':
  with _api.db() as c:rows=c.execute('SELECT * FROM grocery_lists WHERE user_id=? ORDER BY created DESC',(u['user_id'],)).fetchall()
  h.send(200,{'lists':[dict(r) for r in rows]});return True
 if tail=='lists' and method=='POST':
  name=text(h.body().get('name'),'shopping list name',100);identifier=secrets.token_hex(12)
  with _api.db() as c:
   if c.execute('SELECT count(*) FROM grocery_lists WHERE user_id=?',(u['user_id'],)).fetchone()[0]>=100:fail('Keep up to 100 shopping lists.',409)
   c.execute('INSERT INTO grocery_lists VALUES(?,?,?,?)',(identifier,u['user_id'],name,time.time()))
  h.send(201,{'id':identifier,'name':name});return True
 m=re.fullmatch(r'lists/([a-f0-9]{24})(?:/(from-plans|lines|checkout))?',tail)
 if m:
  lid,action=m.groups()
  with _api.db() as c:
   if method!='GET':c.execute('BEGIN IMMEDIATE')
   listing=owned_list(c,u,lid)
   if not action and method=='GET':
    rows=c.execute('SELECT * FROM grocery_lines WHERE list_id=? ORDER BY updated,id',(lid,)).fetchall();h.send(200,{'list':dict(listing),'lines':[line_data(r) for r in rows]});return True
   if action=='from-plans' and method=='POST':
    selected=requirements(u,h.body().get('plan_ids'),c)
    snapshots={r['plan_id']:json.loads(r['body']) for r in c.execute('SELECT * FROM grocery_plan_sources WHERE list_id=?',(lid,))}
    snapshots.update({p['id']:{k:v for k,v in p.items() if k!='id'} for p in selected['plans']})
    if len(snapshots)>60:fail('Use up to 60 planned meals per shopping list.')
    result=requirements(u,list(snapshots),c,snapshots)
    if c.execute('SELECT 1 FROM grocery_generations WHERE list_id=? AND digest=?',(lid,result['digest'])).fetchone():h.send(200,{'added':0,'already_added':True});return True
    # Recompute all associated meals together, so separate batches cannot reuse stock.
    for row in c.execute('SELECT * FROM grocery_lines WHERE list_id=?',(lid,)).fetchall():
     prior=json.loads(row['body'])
     if prior.get('plan_ids') and prior.get('state')=='basket':fail('Finish checkout or return planned items to Needed before adding more meals to this list.',409)
     if prior.get('state')=='needed' and prior.get('plan_ids'):c.execute('DELETE FROM grocery_lines WHERE id=?',(row['id'],))
    added=0
    for line in result['ingredients']:
     if line['needed']==0 and not line['review']:continue
     line.update(state='needed',quantity=line['needed'] if line['needed'] else 1,notes='Check amount and package size' if line['review'] else '')
     c.execute('INSERT INTO grocery_lines VALUES(?,?,?,?)',(secrets.token_hex(12),lid,json.dumps(line),time.time()));added+=1
    for pid,body in snapshots.items():c.execute('INSERT INTO grocery_plan_sources VALUES(?,?,?) ON CONFLICT(list_id,plan_id) DO UPDATE SET body=excluded.body',(lid,pid,json.dumps(body)))
    c.execute('INSERT INTO grocery_generations VALUES(?,?)',(lid,result['digest']));h.send(200,{'added':added});return True
   if action=='lines' and method=='POST':
    d=h.body();p=resolve(d.get('ref'),u,c);line={'product':p,'quantity':number(d.get('quantity',1),'shopping quantity'),'unit':unit(d.get('unit','each')),'state':'needed','notes':text(d.get('notes',''),'shopping note',500,False)}
    identifier=secrets.token_hex(12);c.execute('INSERT INTO grocery_lines VALUES(?,?,?,?)',(identifier,lid,json.dumps(line),time.time()));h.send(201,{'id':identifier});return True
   if action=='checkout' and method=='POST':
    d=h.body();ids=d.get('line_ids')
    if d.get('confirmed') is not True:fail('Confirm that checkout is complete before adding purchased items to inventory.')
    if not isinstance(ids,list) or not 1<=len(ids)<=250 or any(not isinstance(i,str) for i in ids):fail('Choose the purchased basket items.')
    saved=[]
    for identifier in dict.fromkeys(ids):
     row=c.execute('SELECT * FROM grocery_lines WHERE id=? AND list_id=?',(identifier,lid)).fetchone()
     if not row:fail('Shopping item not found.',404)
     line=json.loads(row['body'])
     if line['state']=='purchased':saved.append(line['inventory_id']);continue
     if line['state']!='basket':fail('Review each product and mark it In basket before purchase confirmation.',409)
     p=line.get('purchase_product') or line['product'];entry=_api.clean(dict(p,qty=line['purchase_qty'],unit=line['purchase_unit'],location=line.get('location','Pantry'),weight=line.get('purchase_weight',''),is_food=True,image_source=p.get('source','')))
     entry['ingredient_refs']=list(dict.fromkeys([line['product']['ref'],p['ref']]))
     if entry['qty']<=0:fail('Purchase amounts must be at least 0.001 inventory units.')
     identity=_api.identity(entry);existing=None
     for item in c.execute('SELECT i.* FROM items i JOIN users u ON u.id=i.user_id WHERE u.home_id=? AND u.approved=1',(u['home_id'],)).fetchall():
      if _api.identity(json.loads(item['body']))==identity:existing=item;break
     iid=existing['id'] if existing else secrets.token_hex(12)
     if existing:
      current=json.loads(existing['body']);current['qty']=round(float(current['qty'])+entry['qty'],3)
      current['ingredient_refs']=list(dict.fromkeys(current.get('ingredient_refs',[])+entry['ingredient_refs']))
      if current['qty']>100000:fail('Combined purchased quantity is too large.')
      c.execute('UPDATE items SET body=?,updated=? WHERE id=?',(json.dumps(current),time.time(),iid))
     else:
      if c.execute('SELECT count(*) FROM items i JOIN users u ON u.id=i.user_id WHERE u.home_id=?',(u['home_id'],)).fetchone()[0]>=5000:fail('This household has reached the 5,000-item limit.',409)
      c.execute('INSERT INTO items VALUES(?,?,?,?)',(iid,u['user_id'],json.dumps(entry),time.time()))
     line.update(state='purchased',inventory_id=iid,purchased_at=time.time());c.execute('UPDATE grocery_lines SET body=?,updated=? WHERE id=?',(json.dumps(line),time.time(),identifier));saved.append(iid)
     _api.record_activity(c,u,iid,'purchase_confirmed',entry['name'])
    h.send(200,{'inventory_ids':saved,'message':'Confirmed purchases added to home inventory.'});return True
 m=re.fullmatch(r'lines/([a-f0-9]{24})',tail)
 if m and method in ('PATCH','DELETE'):
  with _api.db() as c:
   c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT l.* FROM grocery_lines l JOIN grocery_lists g ON g.id=l.list_id WHERE l.id=? AND g.user_id=?',(m.group(1),u['user_id'])).fetchone()
   if not row:fail('Shopping item not found.',404)
   line=json.loads(row['body'])
   if line['state']=='purchased':fail('This purchase is complete. Edit the item in inventory to correct it.',409)
   if method=='DELETE':
    c.execute('DELETE FROM grocery_lines WHERE id=?',(row['id'],));h.send(200,{'ok':True});return True
   d=h.body()
   if d.get('revision')!=revision(row['body']):fail('This shopping item changed on another device. Reload it.',409)
   state=d.get('state',line['state'])
   if state not in ('needed','basket'):fail('Choose Needed or In basket. Use purchase confirmation after checkout.')
   if d.get('purchase_ref'):line['purchase_product']=resolve(d['purchase_ref'],u,c)
   if 'quantity' in d:line['quantity']=number(d['quantity'],'shopping quantity')
   if 'unit' in d:line['unit']=unit(d['unit'])
   if state=='basket':
    line['purchase_qty']=number(d.get('purchase_qty'),'purchased amount');line['purchase_unit']=unit(d.get('purchase_unit'))
    line['purchase_weight']=text(d.get('purchase_weight',''),'package size',80,False);line['location']=text(d.get('location','Pantry'),'storage location',80)
   line.update(state=state,notes=text(d.get('notes',line.get('notes','')),'shopping note',500,False))
   c.execute('UPDATE grocery_lines SET body=?,updated=? WHERE id=?',(json.dumps(line),time.time(),row['id']))
  h.send(200,{'ok':True});return True
 fail('Kitchen route not found.',404)
