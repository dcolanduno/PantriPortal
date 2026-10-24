import unittest,json,secrets,time,urllib.request,urllib.error,tarfile,io,base64,sqlite3
from test_app import AppTests,server,client
from unittest.mock import patch,MagicMock
from PIL import Image

class AdministrationTests(unittest.TestCase):
 setUpClass=classmethod(AppTests.setUpClass.__func__)
 tearDownClass=classmethod(AppTests.tearDownClass.__func__)
 call=AppTests.call;register=AppTests.register
 def setUp(self):
  server.RATE.clear();self.admin=client();self.admin_session=self.register(self.admin);self.user=client();self.user_session=self.register(self.user)
  with server.db() as c:
   self.admin_id=c.execute('SELECT id FROM users WHERE name=?',(self.admin_session['name'],)).fetchone()[0]
   self.user_id=c.execute('SELECT id FROM users WHERE name=?',(self.user_session['name'],)).fetchone()[0]
   c.execute("UPDATE users SET role='admin' WHERE id=?",(self.admin_id,))
  self.csrf=self.admin_session['csrf']
 def ops(self,path,method='GET',data=None,status=200):return self.call(self.admin,'/api/admin/ops/'+path,method,data,self.csrf,status)
 def test_delegated_permissions_are_enforced_on_new_and_legacy_routes(self):
  self.ops('users','PATCH',{'id':self.user_id,'role':'author','allow':['audit.read','users.read'],'deny':[]})
  me=self.call(self.user,'/api/me');self.assertEqual(me['role'],'author');self.assertIn('audit.read',me['permissions'])
  self.call(self.user,'/api/admin/ops/logs')
  self.call(self.user,'/api/admin/ops/database',status=403)
  self.call(self.user,'/api/admin/users')
  self.call(self.user,'/api/admin/role','POST',{'id':self.user_id,'role':'admin'},self.user_session['csrf'],403)
  self.call(self.user,'/api/admin/ops/users','PATCH',{'id':self.user_id,'allow':list(server.ops.PERMISSIONS)},self.user_session['csrf'],403)
  self.call(self.user,'/api/admin/items',status=403)
 def test_primary_administrator_is_pinned_and_cannot_lose_access(self):
  original=self.user_session['name']
  try:
   with server.db() as c:c.execute("UPDATE users SET name='dcolanduno' WHERE id=?",(self.user_id,))
   server.init()
   me=self.call(self.user,'/api/me');self.assertEqual(me['role'],'admin');self.assertTrue(me['full_admin']);self.assertEqual(set(me['permissions']),set(server.ops.PERMISSIONS))
   # Even a stored override cannot take rights away from the pinned owner.
   with server.db() as c:c.execute('INSERT INTO admin_permissions VALUES(?,?,?)',(self.user_id,'[]',json.dumps(list(server.ops.PERMISSIONS))))
   self.assertEqual(set(self.call(self.user,'/api/me')['permissions']),set(server.ops.PERMISSIONS))
   for changes in [{'role':'user'},{'disabled':True},{'deny':['audit.read']}]:self.ops('users','PATCH',dict(changes,id=self.user_id),409)
   for sql in ['DELETE FROM users WHERE id=?',"UPDATE users SET role='user' WHERE id=?","UPDATE users SET disabled=1 WHERE id=?","UPDATE users SET approved=0 WHERE id=?","UPDATE users SET name='replacement' WHERE id=?"]:
    with self.assertRaises(sqlite3.IntegrityError):
     with server.db() as c:c.execute(sql,(self.user_id,))
   self.call(client(),'/api/register','POST',{'name':'DColanduno','password':secrets.token_urlsafe(24)},status=409)
   self.assertTrue(next(u for u in self.ops('users')['users'] if u['id']==self.user_id)['primary_admin'])
   server.init();self.assertTrue(self.call(self.user,'/api/me')['full_admin'])
  finally:
   # Fixture-only teardown; the shared test database is temporary, never production.
   with server.db() as c:
    for trigger in ['primary_admin_no_delete','primary_admin_no_restrict','primary_admin_pin_no_delete','primary_admin_pin_no_change']:c.execute('DROP TRIGGER IF EXISTS '+trigger)
    c.execute("DELETE FROM config WHERE key='primary_admin_id'")
    c.execute('DELETE FROM admin_permissions WHERE user_id=?',(self.user_id,))
    c.execute("UPDATE users SET name=?,role='user' WHERE id=?",(original,self.user_id))
   server.init()
 def test_last_full_administrator_and_disabled_sessions(self):
  with server.db() as c:c.execute("UPDATE users SET role='user' WHERE id<>?",(self.admin_id,))
  for changes in [{'role':'user'},{'disabled':True},{'deny':['audit.read']}]:self.ops('users','PATCH',dict(changes,id=self.admin_id),409)
  self.assertTrue(self.ops('overview')['full_admin'])
  self.ops('users','PATCH',{'id':self.user_id,'disabled':True})
  self.call(self.user,'/api/items',status=401)
  self.call(client(),'/api/login','POST',{'name':self.user_session['name'],'password':secrets.token_urlsafe(24)},status=401)
 def test_errors_have_references_and_logs_do_not_capture_secrets(self):
  marker='password=NEVER_LOG_THIS_TOKEN'
  response=self.call(self.user,'/api/missing?token='+marker,status=404)
  self.assertTrue(response['code'].startswith('PP-'));self.assertEqual(len(response['reference']),16)
  result=self.ops('logs?reference='+response['reference']);self.assertEqual(result['total'],1);event=result['events'][0]
  self.assertEqual(event['actor'],self.user_session['name']);self.assertNotIn(marker,json.dumps(event))
  entry=self.ops('errors?code='+response['code'])['errors'][0];self.assertTrue(entry['checks']);self.assertTrue(entry['meaning'])
  self.call(self.user,'/api/telemetry','POST',{'kind':'script','message':marker,'error_class':'TypeError','asset':'features.js','line':42},self.user_session['csrf'])
  rows=self.ops('logs?code=PP-CLIENT')['events'];self.assertTrue(any('TypeError' in x['message'] for x in rows));self.assertNotIn(marker,json.dumps(rows))
 def test_tamper_detection_and_csv_safety(self):
  server.ops.append_event({'user_id':self.admin_id,'name':'=malicious_formula'},action='test.formula',message='Fixture')
  integrity=self.ops('integrity','POST',{});self.assertTrue(integrity['ok'])
  with server.db() as c:
   row=c.execute("SELECT id,message FROM audit_events WHERE action='test.formula' ORDER BY id DESC LIMIT 1").fetchone();c.execute('UPDATE audit_events SET message=? WHERE id=?',('Changed outside logger',row['id']))
  try:self.assertFalse(self.ops('integrity','POST',{})['ok'])
  finally:
   with server.db() as c:c.execute('UPDATE audit_events SET message=? WHERE id=?',(row['message'],row['id']))
  with self.admin.open(self.base+'/api/admin/ops/logs?export=csv&action=test.formula') as response:text=response.read().decode('utf-8-sig')
  self.assertIn("'=malicious_formula",text)
  server.ops.append_event(action='test.tail',message='Tail checkpoint fixture')
  with server.db() as c:
   tail=c.execute('SELECT * FROM audit_events ORDER BY id DESC LIMIT 1').fetchone();c.execute('DELETE FROM audit_events WHERE id=?',(tail['id'],))
  try:self.assertFalse(server.ops.verify_audit()['ok'])
  finally:
   with server.db() as c:c.execute('INSERT INTO audit_events VALUES('+','.join('?' for _ in tail)+')',tuple(tail))
  self.assertTrue(server.ops.verify_audit()['ok'])
 def test_custom_sections_preserve_records_and_separate_quantity_merges(self):
  section=self.ops('sections','POST',{'name':'Craft cupboard '+secrets.token_hex(3),'description':'Screws, tape and glue','icon':'📦','position':12})['id']
  data={'name':'Gloves','qty':2,'location':'Other','is_food':False,'home_section':section}
  first=self.call(self.user,'/api/items','POST',data,self.user_session['csrf'],201)['item']
  second=self.call(self.user,'/api/items','POST',dict(data,home_section='tools-hardware'),self.user_session['csrf'],201)['item'];self.assertNotEqual(first['id'],second['id'])
  saved=next(s for s in self.ops('sections')['sections'] if s['id']==section)
  self.ops('sections','PUT',dict(saved,name='Archived cupboard '+secrets.token_hex(3),archived=True))
  records=self.call(self.user,'/api/items')['items'];self.assertEqual(next(r for r in records if r['id']==first['id'])['qty'],2)
  self.assertEqual(next(r for r in records if r['id']==first['id'])['home_section'],section)
 def test_cross_account_edit_and_stale_revision(self):
  record=self.call(self.user,'/api/items','POST',{'name':'Test cereal','qty':3},self.user_session['csrf'],201)['item'];path='content/detail?kind=inventory&id='+record['id'];detail=self.ops(path)
  payload={'id':record['id'],'kind':'inventory','revision':detail['revision'],'changes':{'name':'Updated cereal','qty':4}}
  self.ops('content','PATCH',payload)
  self.ops('content','PATCH',dict(payload,changes={'qty':1}),409)
  self.assertEqual(self.call(self.user,'/api/items')['items'][0]['qty'],4)
  self.call(self.user,'/api/admin/ops/content','PATCH',payload,self.user_session['csrf'],403)
 def test_connection_controls_and_private_backup(self):
  providers=self.ops('integrations')['providers'];self.assertTrue(any(p['id']=='paprika' for p in providers))
  self.ops('integrations','PUT',{'provider':'paprika','enabled':False,'notes':'Maintenance'})
  try:self.call(self.user,'/api/recipes/import','POST',{'provider':'paprika','recipes':[{'name':'Soup','ingredients':['water']}]},self.user_session['csrf'],403)
  finally:self.ops('integrations','PUT',{'provider':'paprika','enabled':True,'notes':''})
  self.ops('integrations','PUT',{'provider':'arbitrary_host','enabled':True},400)
  backup=self.ops('backup','POST',{});path=server.DATA/'backups'/backup['name'];self.assertTrue(path.is_file());self.assertNotIn('password',json.dumps(backup))
  with tarfile.open(path) as archive:self.assertIn('audit-signing-key',archive.getnames());self.assertIn('inventory.sqlite3',archive.getnames())
  snapshot=path.with_name(backup['name'].removesuffix('.tar.gz')+'.sqlite3');checked=snapshot.with_suffix('.checked.sqlite3')
  snapshot.rename(checked);checked.rename(snapshot) # Closed backup handles must allow immediate Windows archive maintenance.
 def test_error_guide_is_permission_protected_and_unexpected_errors_are_trapped(self):
  with self.admin.open(self.base+'/api/admin/ops/guide.docx') as response:self.assertTrue(response.read().startswith(b'PK'))
  self.call(self.user,'/api/admin/ops/guide.docx',status=403)
  self.call(self.user,'/admin-error-guide.docx',status=404)
  with patch.object(server.ops,'diagnostic',side_effect=RuntimeError('secret=DO_NOT_LOG')):
   result=self.ops('diagnostics','POST',{},500)
  self.assertEqual(result['code'],'PP-INTERNAL');self.assertNotIn('DO_NOT_LOG',json.dumps(self.ops('logs?reference='+result['reference'])))
  incident=self.ops('incident?reference='+result['reference']);self.assertEqual(incident['context']['error_class'],'RuntimeError');self.assertTrue(incident['context']['frames']);self.assertNotIn('DO_NOT_LOG',json.dumps(incident))
 def test_cross_household_images_follow_permission_revocation(self):
  auxiliary=self.register(client())
  with server.db() as c:c.execute("UPDATE users SET role='admin' WHERE name=?",(auxiliary['name'],))
  record=self.call(self.user,'/api/items','POST',{'name':'A product for photo review','qty':1},self.user_session['csrf'],201)['item']
  with patch('local_images.generate',side_effect=lambda d:Image.new('RGB',(32,32),(50+int(d.get('_view',0))*30,100,120))):
   job=self.call(self.admin,'/api/images/generate','POST',{'id':record['id'],'options':True},self.csrf,202)
   for _ in range(100):
    state=self.call(self.admin,'/api/images/job?job='+job['job'])
    if state['state']=='complete':break
    time.sleep(.02)
   self.assertEqual(state['state'],'complete');image=state['result']['options'][1]['image']
   self.call(self.admin,'/api/images/select','POST',{'job':job['job'],'image':image},self.csrf)
  with self.admin.open(self.base+image) as response:self.assertEqual(response.status,200)
  self.ops('users','PATCH',{'id':self.admin_id,'deny':['images.manage']})
  self.call(self.admin,'/api/images/job?job='+job['job'],status=404)
  self.call(self.admin,image,status=404)
  with self.user.open(self.base+image) as response:self.assertEqual(response.status,200)
 def test_recipe_edit_image_copy_and_connection_probe(self):
  rid=secrets.token_hex(12)
  with server.db() as c:
   home=c.execute('SELECT home_id FROM users WHERE id=?',(self.user_id,)).fetchone()[0]
   c.execute('INSERT INTO personal_recipes VALUES(?,?,?,?,?)',(rid,home,self.user_id,json.dumps({'name':'Soup','ingredients':['water'],'instructions':['Heat water']}),time.time()))
  detail=self.ops('content/detail?kind=personal_recipes&id='+rid)
  self.ops('content','PATCH',{'id':rid,'kind':'personal_recipes','revision':detail['revision'],'changes':{'instructions':['Bring water to a boil','Serve carefully']}})
  detail=self.ops('content/detail?kind=personal_recipes&id='+rid)
  output=io.BytesIO();Image.new('RGB',(32,32),'blue').save(output,format='JPEG')
  uploaded=self.call(self.admin,'/api/upload','POST',{'image':'data:image/jpeg;base64,'+base64.b64encode(output.getvalue()).decode()},self.csrf,201)
  self.ops('content/image','POST',{'id':rid,'kind':'personal_recipes','revision':detail['revision'],'image':uploaded['image']})
  result=self.ops('content/detail?kind=personal_recipes&id='+rid)['record'];self.assertEqual(len(result['instructions']),2);self.assertNotEqual(result['image'],uploaded['image'])
  response=MagicMock();response.status=200;response.__enter__.return_value=response;opener=MagicMock();opener.open.return_value=response
  with patch.object(server.ops._api,'validate_public_recipe_url'),patch('urllib.request.build_opener',return_value=opener):self.assertTrue(self.ops('integrations/test','POST',{'provider':'paprika'})['available'])

del AppTests
if __name__=='__main__':unittest.main()
