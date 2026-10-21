import json,secrets,unittest
import test_app as base
from test_app import server,client

class MedicineTests(unittest.TestCase):
 setUpClass=classmethod(base.AppTests.setUpClass.__func__)
 tearDownClass=classmethod(base.AppTests.tearDownClass.__func__)
 call=base.AppTests.call;register=base.AppTests.register;setUp=base.AppTests.setUp
 def api(self,path='state',method='GET',data=None,status=200):return self.call(self.a,'/api/medicine/'+path,method,data,self.ua['csrf'],status)
 def create(self,kind='prescription',**extra):return self.api('records','POST',dict(kind=kind,name='Synthetic private record',**extra),201)
 def saved(self,rid):return next(r for r in self.api()['records'] if r['id']==rid)
 def update(self,rid,**extra):return self.api('records/'+rid,'PUT',dict(self.saved(rid),**extra))
 def test_owner_only_even_same_household_admin(self):
  rid=self.create()['id'];doc=self.create('doctor')['id']
  with server.db() as c:
   a=c.execute('SELECT * FROM users WHERE name=?',(self.ua['name'],)).fetchone()
   c.execute("UPDATE users SET home_id=?,home_role='admin',role='admin' WHERE name=?",(a['home_id'],self.ub['name']))
  self.assertEqual(self.call(self.b,'/api/medicine/state')['records'],[])
  self.call(self.b,'/api/medicine/records/'+rid,'PUT',self.saved(rid),self.ub['csrf'],404)
  self.call(self.b,'/api/medicine/records','POST',dict(kind='prescription',name='Foreign doctor',doctor_id=doc),self.ub['csrf'],400)
  self.call(self.b,'/api/admin/ops/content?kind=medicine_records',status=400)
  self.call(self.b,'/api/admin/ops/content/detail?kind=medicine_records&id='+rid,status=400)
 def test_prescriber_refills_archive_restore_and_conflicts(self):
  doc=self.create('doctor',phone='555-0100',practice='Synthetic clinic',address='Test address')['id']
  rid=self.create(doctor_id=doc,strength='Label strength',quantity=30,unit='tablets',refills_remaining=2,last_filled='2026-10-20',next_refill='2026-11-20',pharmacy='Test pharmacy')['id']
  old=self.saved(rid);self.assertEqual(old['refills_remaining'],2)
  self.update(rid,quantity=28,refills_remaining=1,archived=True)
  self.api('records/'+rid,'PUT',old,409)
  self.update(rid,archived=False);self.assertFalse(self.saved(rid)['archived'])
  self.update(doc,archived=True);self.assertEqual(self.saved(rid)['doctor_id'],doc)
  self.assertEqual(self.call(self.a,'/api/items')['items'],[])
 def test_cabinet_names_are_private_and_concurrent_safe(self):
  self.api('cabinet','PUT',{'name':'My private cabinet','revision':''})
  self.assertEqual(self.api()['cabinet']['name'],'My private cabinet')
  self.assertEqual(self.call(self.b,'/api/medicine/state')['cabinet']['name'],'My medicine cabinet')
  self.api('cabinet','PUT',{'name':'Old edit','revision':''},409)
  self.api('cabinet','PUT',{'name':'Updated cabinet','revision':self.api()['cabinet_revision']})
 def test_appointments_require_time_zone_and_preserve_location(self):
  doc=self.create('doctor')['id']
  rid=self.create('appointment',doctor_id=doc,starts='2026-11-03T09:30',timezone='America/New_York',location='Synthetic clinic, room 2')['id']
  row=self.saved(rid);self.assertEqual(row['starts_utc'],'2026-11-03T14:30:00+00:00');self.assertEqual(row['location'],'Synthetic clinic, room 2')
  for changes in [{'starts':'2026-02-30T10:00'},{'timezone':'Invalid/Zone'},{'starts':'2026-03-08T02:30'}]:
   self.api('records','POST',dict({'kind':'appointment','name':'Visit','location':'Test clinic','starts':'2026-11-03T09:30','timezone':'America/New_York'},**changes),400)
 def test_shared_pharmacy_is_same_stock_not_private_records(self):
  with server.db() as c:
   a=c.execute('SELECT home_id FROM users WHERE name=?',(self.ua['name'],)).fetchone()
   c.execute('UPDATE users SET home_id=? WHERE name=?',(a['home_id'],self.ub['name']))
  item=self.call(self.b,'/api/items','POST',{'name':'Q-Tips','qty':2,'unit':'boxes','is_food':False,'home_section':'medicines-first-aid'},self.ub['csrf'],201)['item']
  self.call(self.a,'/api/items','POST',{'name':'Cereal','qty':1,'is_food':True},self.ua['csrf'],201)
  self.create()
  rows=self.api()['pharmacy'];self.assertEqual([r['id'] for r in rows],[item['id']]);self.assertEqual(rows[0]['qty'],2)
  self.assertEqual(len(self.call(self.b,'/api/medicine/state')['pharmacy']),1)
  self.call(self.b,'/api/items/'+item['id']+'/adjust','POST',{'delta':1},self.ub['csrf'])
  self.assertEqual(self.api()['pharmacy'][0]['qty'],3)
  with server.db() as c:c.execute('UPDATE users SET disabled=1 WHERE name=?',(self.ub['name'],))
  self.assertEqual(self.api()['pharmacy'],[])
 def test_validation_csrf_and_no_medical_values_in_logs(self):
  marker='private_'+secrets.token_hex(12)
  self.api('records','POST',{'kind':'prescription','name':marker,'directions':marker,'notes':marker},201)
  for extra in [{'quantity':-1},{'refills_remaining':1.5},{'last_filled':'bad-date'},{'archived':'true'},{'doctor_id':[]},{'name':'x'*161}]:
   self.api('records','POST',dict({'kind':'prescription','name':'Test'},**extra),400)
  self.call(self.a,'/api/medicine/records','POST',{'kind':'prescription','name':marker},'wrong',403)
  self.call(client(),'/api/medicine/state',status=401)
  with server.db() as c:
   logs=[dict(r) for r in c.execute("SELECT * FROM audit_events WHERE route LIKE '/api/medicine%'")]
  self.assertTrue(logs);self.assertNotIn(marker,json.dumps(logs));self.assertTrue(all(r['route']=='/api/medicine' and r['target']=='' for r in logs))

if __name__=='__main__':unittest.main()
