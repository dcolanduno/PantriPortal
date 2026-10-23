import json,unittest,urllib.parse
from unittest.mock import patch
import test_medicine as base
from test_app import server,client
import medicine_maps as maps

class OfficeMapTests(unittest.TestCase):
 setUpClass=classmethod(base.MedicineTests.setUpClass.__func__)
 tearDownClass=classmethod(base.MedicineTests.tearDownClass.__func__)
 call=base.MedicineTests.call;register=base.MedicineTests.register
 api=base.MedicineTests.api;create=base.MedicineTests.create;saved=base.MedicineTests.saved;update=base.MedicineTests.update
 def setUp(self):base.MedicineTests.setUp(self);maps._cache.clear()
 def test_owner_scope_minimal_provider_request_and_cache(self):
  address='1600 Pennsylvania Ave NW, Washington DC 20500';rid=self.create('doctor',address=address,notes='PRIVATE_NOTES')['id']
  response={'result':{'addressMatches':[{'matchedAddress':'MATCHED PUBLIC OFFICE','coordinates':{'x':-77.03,'y':38.89}}]}}
  with patch.object(maps.catalog,'fetch',return_value=response) as fetch:
   result=self.api('office-map','POST',{'id':rid,'address':'IGNORED','notes':'PRIVATE_NOTES'})
   self.assertTrue(result['available']);self.assertEqual(result['latitude'],38.89)
   self.api('office-map','POST',{'id':rid});fetch.assert_called_once()
   url=fetch.call_args.args[0];self.assertEqual(urllib.parse.urlsplit(url).hostname,'geocoding.geo.census.gov')
   self.assertEqual(urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)['address'],[address])
   self.assertNotIn('PRIVATE_NOTES',url);self.assertNotIn(rid,url)
   with server.db() as c:
    owner=c.execute('SELECT home_id FROM users WHERE name=?',(self.ua['name'],)).fetchone()
    c.execute("UPDATE users SET role='admin',home_id=? WHERE name=?",(owner['home_id'],self.ub['name']))
   self.call(self.b,'/api/medicine/office-map','POST',{'id':rid},self.ub['csrf'],404)
   self.call(client(),'/api/medicine/office-map','POST',{'id':rid},status=401)
   self.call(self.a,'/api/medicine/office-map','POST',{'id':rid},'wrong',403)
  with server.db() as c:
   logs=json.dumps([dict(r) for r in c.execute("SELECT * FROM audit_events WHERE route='/api/medicine'")])
  self.assertNotIn(address,logs);self.assertNotIn('PRIVATE_NOTES',logs);self.assertNotIn(rid,logs)
 def test_missing_invalid_or_ambiguous_location_does_not_invent_pin(self):
  rid=self.create('doctor')['id']
  with patch.object(maps.catalog,'fetch') as fetch:
   self.assertFalse(self.api('office-map','POST',{'id':rid})['available']);fetch.assert_not_called()
  for fixture in [{'result':{'addressMatches':[]}}, {'result':{'addressMatches':[{},{}]}}, {'result':{'addressMatches':[{'coordinates':{'x':float('nan'),'y':40}}]}}, {'result':{'addressMatches':[{'coordinates':{'x':-77,'y':100}}]}}]:
   maps._cache.clear()
   with patch.object(maps.catalog,'fetch',return_value=fixture):self.assertFalse(maps.office_map('Public office')['available'])
 def test_service_failure_and_address_edits(self):
  rid=self.create('doctor',address='Old public office')['id']
  with patch.object(maps.catalog,'fetch',side_effect=maps.catalog.CatalogUnavailable):self.assertFalse(self.api('office-map','POST',{'id':rid})['available'])
  self.update(rid,address='New public office')
  fixture={'result':{'addressMatches':[{'coordinates':{'x':-77,'y':39}}]}}
  with patch.object(maps.catalog,'fetch',return_value=fixture) as fetch:
   self.assertTrue(self.api('office-map','POST',{'id':rid})['available']);self.assertIn('New+public+office',fetch.call_args.args[0])
  self.assertEqual(self.saved(rid)['address'],'New public office')

if __name__=='__main__':unittest.main()
