import json,os,sys,unittest,urllib.parse
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
import medicine_catalog as catalog
import test_medicine as medicine_tests
from test_app import server,client

class CatalogParsingTests(unittest.TestCase):
 def test_drug_strength_ids_stay_paired(self):
  fixture=[2,['TEST (Oral Pill)','TEST XR (Oral Pill)'],{'STRENGTHS_AND_FORMS':[[' 10 mg Tab','20 mg Tab'],['30 mg Tab']],'RXCUIS':[['101','102'],['103']]},[['TEST'],['TEST XR']]]
  with patch.object(catalog,'fetch',return_value=fixture) as fetch:
   rows=catalog.drugs('test')['results']
  self.assertEqual(rows[0]['forms'],[{'strength':'10 mg Tab','rxcui':'101'},{'strength':'20 mg Tab','rxcui':'102'}]);self.assertEqual(rows[1]['forms'][0]['rxcui'],'103')
  self.assertIn('terms=test',fetch.call_args.args[0])
 def test_doctor_registry_phone_and_source(self):
  fixture=[1,['1234567890'],None,[['TEST DOCTOR','Family medicine','TEST OFFICE','555-0100']]]
  with patch.dict(os.environ,{'PANTRY_GOOGLE_PLACES_KEY':''}),patch.object(catalog,'fetch',return_value=fixture) as fetch:
   result=catalog.doctors('test','test city')
  self.assertEqual(result['results'][0]['phone'],'555-0100');self.assertIn('1234567890',result['results'][0]['source_url']);self.assertFalse(result['google_enabled'])
  self.assertEqual(urllib.parse.parse_qs(urllib.parse.urlsplit(fetch.call_args.args[0]).query)['terms'],['test test city'])
 def test_doctor_provider_failure_keeps_manual_entry(self):
  with patch.dict(os.environ,{'PANTRY_GOOGLE_PLACES_KEY':''}),patch.object(catalog,'fetch',side_effect=catalog.CatalogUnavailable):
   result=catalog.doctors('test')
  self.assertEqual(result['results'],[]);self.assertTrue(result['warnings'])
 def test_doctor_titles_and_name_ranking(self):
  fixture=[2,['1234567890','1234567891'],None,[['SMITH, ALICE','Family medicine','10 JOHN STREET','555-0100'],['SMITH, JOHN','Family medicine','20 EXAMPLE STREET','555-0101']]]
  with patch.dict(os.environ,{'PANTRY_GOOGLE_PLACES_KEY':''}),patch.object(catalog,'fetch',return_value=fixture) as fetch:
   result=catalog.doctors('Dr. John Smith, MD','Atlanta')
  self.assertEqual(result['results'][0]['name'],'SMITH, JOHN')
  self.assertEqual(urllib.parse.parse_qs(urllib.parse.urlsplit(fetch.call_args.args[0]).query)['terms'],['John Smith Atlanta'])
  with patch.object(catalog,'fetch') as fetch:
   self.assertEqual(catalog.doctors('Dr.')['results'],[]);fetch.assert_not_called()
 def test_google_key_is_header_only_and_registry_survives_failure(self):
  with patch.dict(os.environ,{'PANTRY_GOOGLE_PLACES_KEY':'synthetic-key'}),patch.object(catalog,'fetch',side_effect=[[0,[],None,[]],{'places':[{'displayName':{'text':'TEST CLINIC'},'formattedAddress':'TEST ADDRESS','nationalPhoneNumber':'555-0101','googleMapsUri':'https://maps.google.com/','attributions':[{'provider':'TEST attribution'}]}]}]) as fetch:
   result=catalog.doctors('test')
  self.assertEqual(result['results'][0]['source'],'Google Maps');self.assertEqual(result['results'][0]['phone'],'555-0101')
  self.assertNotIn('synthetic-key',fetch.call_args.args[0]);self.assertEqual(fetch.call_args.args[2]['X-Goog-Api-Key'],'synthetic-key')
 def test_labels_use_exact_identity_and_preserve_full_sections(self):
  lid='11111111-1111-1111-1111-111111111111';long='Label text '*5000
  fixture={'results':[{'id':lid,'set_id':lid,'effective_time':'20261001','openfda':{'brand_name':['TEST'],'manufacturer_name':['TEST MAKER']},'boxed_warning':['Important warning'],'adverse_reactions':[long],'indications_and_usage':['Test indication'],'clinical_studies':['Other full section']}]}
  with patch.object(catalog,'fetch',return_value=fixture) as fetch:
   options=catalog.label_options('ignore name','123');search=urllib.parse.parse_qs(urllib.parse.urlsplit(fetch.call_args.args[0]).query)['search'][0]
   result=catalog.label_detail(options['results'][0]['id'])['label']
  self.assertEqual(search,'openfda.rxcui:"123"');self.assertEqual(next(s['text'] for s in result['sections'] if s['key']=='adverse_reactions'),long);self.assertTrue(any(s['key']=='clinical_studies' for s in result['sections']));self.assertIn(lid,result['source_url'])
 def test_name_search_quotes_provider_query_syntax(self):
  with patch.object(catalog,'fetch',return_value={}) as fetch:catalog.label_options('TEST " OR * (Oral Pill)','')
  query=urllib.parse.parse_qs(urllib.parse.urlsplit(fetch.call_args.args[0]).query)['search'][0]
  self.assertIn('\\"',query);self.assertNotIn('Oral Pill',query)

class CatalogApiTests(unittest.TestCase):
 setUpClass=classmethod(medicine_tests.MedicineTests.setUpClass.__func__)
 tearDownClass=classmethod(medicine_tests.MedicineTests.tearDownClass.__func__)
 call=medicine_tests.MedicineTests.call;register=medicine_tests.MedicineTests.register;setUp=medicine_tests.MedicineTests.setUp
 api=medicine_tests.MedicineTests.api;create=medicine_tests.MedicineTests.create;saved=medicine_tests.MedicineTests.saved;update=medicine_tests.MedicineTests.update
 def test_lookup_auth_csrf_validation_privacy_and_minimal_payload(self):
  marker='SYNTHETIC_PRIVATE_LOOKUP';notes='DO_NOT_SEND_NOTES'
  with patch.object(catalog,'drugs',return_value={'results':[],'warnings':[]}) as search:
   self.api('search/drugs','POST',{'term':marker,'notes':notes})
   search.assert_called_once_with(marker)
   self.call(client(),'/api/medicine/search/drugs','POST',{'term':marker},status=401)
   self.call(self.a,'/api/medicine/search/drugs','POST',{'term':marker},'wrong',403)
   self.api('search/drugs','POST',{'term':'ab'},400)
  self.api('drug-label','POST',{'id':'https://internal.invalid/'},400)
  self.api('drug-labels','POST',{'name':'Test','rxcui':'abc'},400)
  with server.db() as c:
   logs=[dict(r) for r in c.execute("SELECT * FROM audit_events WHERE route='/api/medicine'")]
   cache=[dict(r) for r in c.execute('SELECT * FROM cache')]
  self.assertNotIn(marker,json.dumps(logs)+json.dumps(cache));self.assertNotIn(notes,json.dumps(logs)+json.dumps(cache))
 def test_reference_failure_does_not_break_saving(self):
  with patch.object(catalog,'drugs',side_effect=catalog.CatalogUnavailable):self.api('search/drugs','POST',{'term':'test'},502)
  rid=self.create(catalog_name='TEST (Oral Pill)',rxcui='123')['id']
  self.assertEqual(self.saved(rid)['rxcui'],'123')
  self.update(rid,catalog_name='',rxcui='');self.assertEqual(self.saved(rid)['rxcui'],'')
  self.api('records','POST',{'kind':'prescription','name':'Test','rxcui':'invalid'},400)

if __name__=='__main__':unittest.main()
