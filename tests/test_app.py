import os, sys, tempfile, threading, unittest, json, urllib.request, urllib.error, http.cookiejar, secrets, time, base64, io
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

TEST_WORK=Path(__file__).resolve().parents[1]/'work';TEST_WORK.mkdir(exist_ok=True)
TEMP=tempfile.TemporaryDirectory(prefix='pantry-tests-',dir=TEST_WORK)
os.environ.update(PANTRY_DATA=TEMP.name,PANTRY_DEV='1',PANTRY_PORT='8879')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
import server
from PIL import Image

def client():return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

class AppTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  server.init();cls.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
  cls.base='http://127.0.0.1:'+str(cls.http.server_port);server.ORIGINS.add(cls.base)
  threading.Thread(target=cls.http.serve_forever,daemon=True).start()
 @classmethod
 def tearDownClass(cls):cls.http.shutdown();cls.http.server_close()
 def setUp(self):
  server.RATE.clear();self.a=client();self.b=client()
  self.ua=self.register(self.a);self.ub=self.register(self.b)
 def test_health_reports_the_running_version_and_build(self):
  self.assertEqual(self.call(self.a,'/api/health'),{'status':'ok','version':'0.15.4','build':server.release_build()})
 def call(self,c,path,method='GET',data=None,csrf='',status=200,origin=None):
  req=urllib.request.Request(self.base+path,method=method,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json','Origin':origin or self.base,'X-CSRF-Token':csrf})
  try:r=c.open(req,timeout=20)
  except urllib.error.HTTPError as e:r=e
  self.assertEqual(r.status,status,path)
  return json.loads(r.read())
 def register(self,c,setup=None):
  data={'name':'test_'+secrets.token_hex(6),'password':secrets.token_urlsafe(24)}
  if setup:data['setup']=setup
  return self.call(c,'/api/register','POST',data)
 def add(self,**kw):
  d={'name':'Canned beans','barcode':'0123456789012','location':'Pantry','unit':'cans','qty':2}
  d.update(kw);return self.call(self.a,'/api/items','POST',d,self.ua['csrf'],201)
 def test_atomic_merge_and_units(self):
  first=self.add();second=self.add(qty=3)
  self.assertTrue(second['merged']);self.assertEqual(second['item']['id'],first['item']['id']);self.assertEqual(second['item']['qty'],5)
  self.assertFalse(self.add(unit='cases')['merged']);self.assertFalse(self.add(location='Freezer')['merged'])
  def add_one(_):return self.add(qty=1)
  with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(add_one,range(8)))
  rows=self.call(self.a,'/api/items')['items'];self.assertEqual(next(r['qty'] for r in rows if r['id']==first['item']['id']),13)
  self.assertFalse(self.add(barcode='',weight='200 g')['merged']);self.assertFalse(self.add(barcode='',weight='400 g')['merged'])
 def test_isolation_and_csrf(self):
  item=self.add()['item'];iid=item['id'];self.assertEqual(self.call(self.b,'/api/items')['items'],[])
  self.call(self.b,'/api/items/'+iid,'DELETE',{},self.ub['csrf'],404)
  self.call(self.a,'/api/items/'+iid+'/adjust','POST',{'delta':1},'wrong',403)
  self.call(self.a,'/api/items','POST',{'name':'x'},self.ua['csrf'],403,origin='https://bad.example')
  self.call(self.a,'/api/admin/users',status=403)
  self.call(self.a,'/api/items','POST',{'name':'x','qty':-1},self.ua['csrf'],400)
  self.call(self.a,'/api/items','POST',{'name':'x','qty':float('nan')},self.ua['csrf'],400)
 def test_import_merges_once(self):
  first=self.add()['item'];batch={'items':[dict(first,qty=3),dict(first,qty=4)]}
  result=self.call(self.a,'/api/import','POST',batch,self.ua['csrf']);self.assertEqual(result['merged'],2);self.assertEqual(result['items'][0]['qty'],9)
  result=self.call(self.a,'/api/import','POST',batch,self.ua['csrf']);self.assertEqual(result['merged'],0);self.assertEqual(result['items'][0]['qty'],9)
  self.call(self.a,'/api/import','POST',{'items':['invalid']},self.ua['csrf'],400)
 def test_private_photos(self):
  im=Image.new('RGB',(8,8),'green');data=io.BytesIO();im.save(data,format='PNG')
  photo=self.call(self.a,'/api/upload','POST',{'image':'data:image/png;base64,'+base64.b64encode(data.getvalue()).decode()},self.ua['csrf'],201)
  url=photo['image'];self.assertEqual(self.a.open(self.base+url).headers['Content-Type'],'image/jpeg')
  self.call(self.b,url,status=404)
  self.call(self.b,'/api/items','POST',{'name':'stolen','image':url},self.ub['csrf'],403)
  with patch.object(server,'lookup',return_value={'products':[],'warnings':[]}):
   self.add(image=url)
  self.call(self.a,'/api/logout','POST',{},self.ua['csrf']);self.call(self.a,'/api/items',status=401)
 def test_edit_collision(self):
  a=self.add()['item'];b=self.add(name='Rice',barcode='')['item']
  self.call(self.a,'/api/items/'+b['id'],'PUT',a,self.ua['csrf'],409)
 def test_real_photo_survives_generated_merge(self):
  first=self.add(image='https://images.openfoodfacts.org/images/products/example.jpg',image_source='Catalog')['item']
  with patch('local_images.generate',return_value=Image.new('RGB',(24,24),'yellow')):
   job=self.call(self.a,'/api/images/generate','POST',{'name':'Canned beans'},self.ua['csrf'],202)['job'];gen=self.wait_image(job)['result']
  merged=self.add(image=gen['image'],image_source=gen['image_source'])['item']
  self.assertEqual(merged['image'],first['image']);self.assertFalse(merged['image_generated']);self.assertEqual(merged['qty'],4)
 def test_audit_does_not_generate_on_provider_failure(self):
  item=self.add()['item'];jid=secrets.token_hex(12);server.JOBS[jid]={'state':'queued','checked':0,'total':0,'repaired':0,'generated':0,'unresolved':0,'results':[]}
  with server.db() as c:c.execute('DELETE FROM items WHERE id<>?',(item['id'],))
  with patch.object(server,'lookup',return_value={'products':[],'warnings':['Provider unavailable']}),patch.object(server,'generated_image') as gen:
   server.audit_worker(jid,True);gen.assert_not_called()
  self.assertEqual(server.JOBS[jid]['unresolved'],1)
 def test_generation_and_failure(self):
  item=self.add()['item']
  with patch('local_images.generate',return_value=Image.new('RGB',(24,24),'orange')):
   job=self.call(self.a,'/api/images/generate','POST',{'id':item['id']},self.ua['csrf'],202)['job']
   self.call(self.b,'/api/images/job?job='+job,status=404)
   result=self.wait_image(job)
   self.assertEqual(result['state'],'complete')
   saved=self.call(self.a,'/api/items')['items'][0]
   self.assertTrue(saved['image_generated']);self.assertIn('not a product photo',saved['image_source'])
   self.call(self.b,saved['image'],status=404)
   forged=self.add(image=saved['image'],image_source='Real product photo',qty=1)['item']
   self.assertTrue(forged['image_generated']);self.assertIn('AI-generated',forged['image_source'])
  with patch('local_images.generate',side_effect=RuntimeError('private-path-do-not-expose')):
   job=self.call(self.a,'/api/images/generate','POST',{'name':'Other product'},self.ua['csrf'],202)['job']
   result=self.wait_image(job);self.assertEqual(result['state'],'failed');self.assertNotIn('private-path',result['error'])
 def wait_image(self,job):
  for _ in range(100):
   result=self.call(self.a,'/api/images/job?job='+job)
   if result['state'] in ('complete','failed'):return result
   time.sleep(.02)
  self.fail('Image job did not settle')
 def test_three_choices_regeneration_and_draft_selection(self):
  seeds=[]
  def render(item):
   seeds.append(item['_seed']);return Image.new('RGB',(24,24),(item['_seed'],item['_view']*70,30))
  with patch('local_images.generate',side_effect=render),patch.object(server.secrets,'randbits',side_effect=range(10,16)):
   first=self.call(self.a,'/api/images/generate','POST',{'name':'Apple','options':True},self.ua['csrf'],202)['job']
   result=self.wait_image(first)['result'];self.assertEqual(len(result['options']),3)
   self.assertEqual(len({i['image'] for i in result['options']}),3)
   self.assertEqual(self.call(self.a,'/api/items')['items'],[])
   self.call(self.b,'/api/images/select','POST',{'job':first,'image':result['options'][0]['image']},self.ub['csrf'],404)
   self.call(self.a,'/api/images/select','POST',{'job':first,'image':'/media/not-in-this-set.jpg'},self.ua['csrf'],400)
   second=self.call(self.a,'/api/images/generate','POST',{'name':'Apple','options':True},self.ua['csrf'],202)['job']
   newer=self.wait_image(second)['result']['options'];self.assertFalse(set(i['image'] for i in newer)&set(i['image'] for i in result['options']))
   chosen=self.call(self.a,'/api/images/select','POST',{'job':second,'image':newer[1]['image']},self.ua['csrf'])
   self.assertEqual(chosen['image'],newer[1]['image']);self.assertEqual(self.call(self.a,'/api/items')['items'],[])
   saved=self.add(name='Apple',barcode='',image=chosen['image'])['item'];self.assertTrue(saved['image_generated'])
   self.assertEqual(saved['image'],newer[1]['image']);self.call(self.b,saved['image'],status=404)
  self.assertEqual(seeds,list(range(10,16)))
 def test_image_choices_do_not_replace_until_selected_and_detect_changes(self):
  original=self.add()['item']
  def render(item):return Image.new('RGB',(24,24),(item['_view']*70,50,80))
  with patch('local_images.generate',side_effect=render):
   job=self.call(self.a,'/api/images/generate','POST',{'id':original['id'],'options':True},self.ua['csrf'],202)['job']
   choices=self.wait_image(job)['result']['options']
   self.assertEqual(self.call(self.a,'/api/items')['items'][0]['image'],original['image'])
   selected=self.call(self.a,'/api/images/select','POST',{'job':job,'image':choices[2]['image']},self.ua['csrf'])
   self.assertEqual(self.call(self.a,'/api/items')['items'][0]['image'],selected['image'])
   stale=self.call(self.a,'/api/images/generate','POST',{'id':original['id'],'options':True},self.ua['csrf'],202)['job']
   options=self.wait_image(stale)['result']['options']
   self.call(self.a,'/api/items/'+original['id'],'PUT',dict(original,image='https://images.openfoodfacts.org/replacement.jpg'),self.ua['csrf'])
   self.call(self.a,'/api/images/select','POST',{'job':stale,'image':options[0]['image']},self.ua['csrf'],409)
   self.assertEqual(self.call(self.a,'/api/items')['items'][0]['image'],'https://images.openfoodfacts.org/replacement.jpg')
 def test_admin_bootstrap_roles_and_audit(self):
  # Generate a fresh setup hash inside this isolated test database.
  token=secrets.token_urlsafe(32)
  with server.db() as c:c.execute('INSERT OR REPLACE INTO config VALUES(?,?)',('admin_setup',server.hashlib.sha256(token.encode()).hexdigest()))
  admin=client();ua=self.register(admin,token)
  self.assertEqual(ua['role'],'admin');self.call(client(),'/api/register','POST',{'name':'extra_'+secrets.token_hex(4),'password':secrets.token_urlsafe(24),'setup':token},status=403)
  users=self.call(admin,'/api/admin/users')['users'];me=next(u for u in users if u['name']==ua['name'])
  # Remove any earlier test admins so this case checks the last-admin guard.
  with server.db() as c:c.execute("UPDATE users SET role='user' WHERE id<>?",(me['id'],))
  self.call(admin,'/api/admin/role','POST',{'id':me['id'],'role':'user'},ua['csrf'],409)
  regular=next(u for u in users if u['name']==self.ua['name'])
  self.call(admin,'/api/admin/role','POST',{'id':regular['id'],'role':'admin'},ua['csrf'])
  self.assertEqual(self.call(self.a,'/api/me')['role'],'admin')
  self.call(admin,'/api/admin/role','POST',{'id':regular['id'],'role':'user'},ua['csrf'])
  self.add()
  with server.db() as c:c.execute('DELETE FROM items WHERE user_id NOT IN (SELECT id FROM users WHERE name=?)',(self.ua['name'],))
  with patch.object(server,'lookup',return_value={'products':[],'warnings':[]}),patch('local_images.generate',return_value=Image.new('RGB',(24,24),'blue')):
   job=self.call(admin,'/api/admin/audit','POST',{'generate':True},ua['csrf'],202)['job']
   for _ in range(100):
    state=self.call(admin,'/api/admin/audit?job='+job)
    if state['state']=='complete':break
    time.sleep(.02)
   self.assertEqual(state['generated'],1);self.assertEqual(state['unresolved'],0)
   item=self.call(self.a,'/api/items')['items'][0];self.assertTrue(item['image_generated']);self.assertEqual(self.a.open(self.base+item['image']).status,200)
 def test_static_allowlist(self):
  self.assertEqual(client().open(self.base+'/').status,200)
  self.call(client(),'/server.py',status=401)
  self.call(client(),'/../work/runtime/admin-setup-token',status=401)

if __name__=='__main__':unittest.main(verbosity=2)
