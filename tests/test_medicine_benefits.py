import json,unittest,datetime,os,urllib.parse,base64,hmac,hashlib
from unittest.mock import patch
import test_medicine as base
from test_app import server,client
import medicine_catalog as catalog
import medicine_pricing as pricing
class BenefitsTests(unittest.TestCase):
 setUpClass=classmethod(base.MedicineTests.setUpClass.__func__);tearDownClass=classmethod(base.MedicineTests.tearDownClass.__func__)
 call=base.MedicineTests.call;register=base.MedicineTests.register;setUp=base.MedicineTests.setUp;api=base.MedicineTests.api;create=base.MedicineTests.create;saved=base.MedicineTests.saved;update=base.MedicineTests.update
 def program(self):return self.api('benefits/programs','POST',dict(name='GoodRx',category='discount',member_id='PRIVATE_MEMBER_1234',group_number='PRIVATE_GROUP',rxbin='123456',rxpcn='PRIVATE_PCN',website='https://www.goodrx.com/'),201)['id']
 def quote(self,rx,**changes):return dict(prescription_id=rx['id'],prescription_revision=rx['revision'],pharmacy='Example Pharmacy',address='123 Example St',phone='212-555-0100',program_id='cash',amount='12.34',form='tablet',quantity='30',unit='tablets',days_supply='30',quoted_on=datetime.date.today().isoformat(),source='Synthetic pharmacist quote',confirmed=True,**changes)
 def test_cards_profiles_private_and_conflict_safe(self):
  pid=self.program()
  with server.db() as c:
   a=c.execute('SELECT home_id FROM users WHERE name=?',(self.ua['name'],)).fetchone();c.execute("UPDATE users SET home_id=?,home_role='admin',role='admin' WHERE name=?",(a['home_id'],self.ub['name']))
  self.call(self.b,'/api/admin/ops/content?kind=medicine_benefit_entries',status=400)
  state=self.api('benefits/state');p=state['programs'][0];self.assertEqual(p['id'],pid)
  self.assertEqual(self.call(self.b,'/api/medicine/benefits/state')['programs'],[])
  self.call(self.b,'/api/medicine/benefits/programs/'+pid,'PUT',p,self.ub['csrf'],404)
  self.api('benefits/programs/'+pid,'PUT',dict(p,plan='Example plan'))
  self.api('benefits/programs/'+pid,'PUT',p,409)
  self.api('benefits/profile','PUT',{'zip':'10001','revision':''});self.api('benefits/profile','PUT',{'zip':'10002','revision':''},409)
  self.assertEqual(self.call(self.b,'/api/medicine/benefits/state')['profile']['zip'],'')
  with server.db() as c:logs=json.dumps([dict(r) for r in c.execute("SELECT * FROM audit_events WHERE route='/api/medicine'")])
  for v in ['PRIVATE_MEMBER','PRIVATE_GROUP','PRIVATE_PCN','10001']:self.assertNotIn(v,logs)
 def test_quote_identity_price_zero_history_and_foreign_records(self):
  pid=self.program();rid=self.create(strength='10 mg',ndc='0002-8215-01')['id'];rx=self.saved(rid);q=self.quote(rx);self.api('benefits/quotes','POST',q,201)
  q2=dict(q,amount='0',program_id=pid);self.api('benefits/quotes','POST',q2,201)
  rows=self.api('benefits/state')['quotes'];self.assertEqual(len(rows),2);self.assertEqual(rows[0]['amount'],'0');self.assertEqual(rows[0]['strength'],'10 mg')
  self.call(self.b,'/api/medicine/benefits/quotes','POST',q,self.ub['csrf'],404)
  self.call(self.b,'/api/medicine/benefits/state',status=200)
  for change in [{'amount':'-1'},{'amount':'NaN'},{'amount':'1.234'},{'confirmed':False},{'quantity':'0'},{'days_supply':'0'},{'quoted_on':'2999-01-01'},{'program_id':'foreign'}]:self.api('benefits/quotes','POST',dict(q,**change),400)
  self.update(rid,strength='20 mg');self.api('benefits/quotes','POST',q,409)
 def test_auth_csrf_and_validation(self):
  self.call(client(),'/api/medicine/benefits/state',status=401)
  self.call(self.a,'/api/medicine/benefits/programs','POST',{'name':'Test','category':'discount'},'wrong',403)
  for change in [{'website':'javascript:alert(1)'},{'website':urllib.parse.urlunsplit(('https','fixture-user:fixture-password@example.invalid','','',''))},{'website':'https://[invalid'},{'rxbin':'123'},{'category':'unknown'},{'member_id':['invalid']}]:self.api('benefits/programs','POST',dict({'name':'Example','category':'discount'},**change),400)
  self.api('search/pharmacies','POST',{'zip':'12345 OR *'},400)
  with patch.object(catalog,'pharmacies',return_value={'results':[]}) as p:self.api('search/pharmacies','POST',{'zip':'10001','member_id':'PRIVATE'});p.assert_called_once_with('10001')
 def test_provider_disabled_and_minimal_consent_payload(self):
  rx=self.saved(self.create(strength='10 mg')['id']);body=dict(self.quote(rx),zip='10001',consent=True)
  with patch.dict(os.environ,{'PANTRY_GOODRX_ENABLED':'0'}),patch.object(catalog,'fetch') as fetch:
   r=self.api('benefits/provider-prices','POST',body);self.assertFalse(r['configured']);fetch.assert_not_called()
  self.api('benefits/provider-prices','POST',dict(body,consent=False),400)
  self.call(self.b,'/api/medicine/benefits/provider-prices','POST',body,self.ub['csrf'],404)
 def test_browse_needs_only_name_optional_zip_and_consent(self):
  with patch.object(pricing,'browse',return_value={'variants':[]}) as browse:
   self.api('benefits/provider-browse','POST',{'name':'Example','consent':True,'member_id':'PRIVATE_IGNORE','directions':'PRIVATE_IGNORE'})
   browse.assert_called_once_with('Example','')
  self.api('benefits/provider-browse','POST',{'name':'Example','consent':False},400)
  self.call(client(),'/api/medicine/benefits/provider-browse','POST',{'name':'Example','consent':True},status=401)
  with patch.object(catalog,'drugs',return_value={'results':[{'name':'Example (Oral Pill)','forms':[{'strength':'10 mg Tab','rxcui':'101'},{'strength':'20 mg Tab','rxcui':'102'}]},{'name':'Different drug','forms':[{'strength':'999 mg','rxcui':'999'}]},{'name':'Example (Extended Release)','forms':[{'strength':'888 mg','rxcui':'888'}]}]}):
   self.assertEqual([o['strength'] for o in self.api('benefits/dose-options','POST',{'name':'Example'})['options']],['10 mg Tab','20 mg Tab'])

 def test_public_prices_owner_authenticated_and_name_only(self):
  with patch.object(pricing,'public_prices',return_value={'results':[]}) as lookup:
   self.api('benefits/public-prices','POST',{'name':'Example','member_id':'PRIVATE','directions':'PRIVATE'})
   lookup.assert_called_once_with('Example')
  self.call(client(),'/api/medicine/benefits/public-prices','POST',{'name':'Example'},status=401)
  self.call(self.a,'/api/medicine/benefits/public-prices','POST',{'name':'Example'},'wrong',403)
  with patch.object(pricing,'public_prices',side_effect=catalog.CatalogUnavailable):self.api('benefits/public-prices','POST',{'name':'Example'},502)

class ProviderTests(unittest.TestCase):
 def test_signed_request_filters_fill_mismatches_and_preserves_zero(self):
  rx={'name':'Example','strength':'10 mg','ndc':'1234-5678-90','rx_number':'PRIVATE_RX','directions':'PRIVATE_DIR'};fill=dict(quantity='30',zip='10001',form='tablet',unit='tablets',days_supply='30')
  fixture={'data':dict(display='Example',dosage='10mg',form='tablet',metric_quantity=30,days_supply='30',prices=[dict(pharmacy='Example',type='coupon',price=0,program_cost=0,coupon_url='https://www.goodrx.com/coupon'),dict(pharmacy='Unsafe link',type='membership',price=12,program_cost=36,coupon_url='javascript:bad')])}
  with patch.dict(os.environ,{'PANTRY_GOODRX_ENABLED':'1','PANTRY_GOODRX_API_KEY':'synthetic-api-key','PANTRY_GOODRX_SECRET':'synthetic-secret'}),patch.object(catalog,'fetch',return_value=fixture) as fetch:
   r=pricing.compare(rx,fill);self.assertEqual(r['results'][0]['price'],'0.00');self.assertEqual(r['results'][1]['url'],'');self.assertEqual(r['results'][1]['membership_fee'],'36.00')
   url=fetch.call_args.args[0];query=urllib.parse.urlsplit(url).query;payload,sig=query.rsplit('&sig=',1)
   self.assertEqual(urllib.parse.unquote(sig),base64.b64encode(hmac.new(b'synthetic-secret',payload.encode(),hashlib.sha256).digest(),b'__').decode())
   params=urllib.parse.parse_qs(payload);self.assertEqual(params['ndc'],['01234567890']);self.assertNotIn('PRIVATE',url);self.assertNotIn('synthetic-secret',url)
   self.assertEqual(pricing.compare(rx,dict(fill,quantity='90'))['results'],[])
  for code,expected in [('1234-5678-90','01234567890'),('12345-678-90','12345067890'),('12345-6789-0','12345678900'),('1234567890','')]:self.assertEqual(pricing.ndc11(code),expected)

 def test_name_browse_prices_across_doses_without_manual_fill_fields(self):
  def upstream(url):
   q=urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
   self.assertNotIn('metric_quantity',q);self.assertNotIn('ndc',q)
   if '/drug-info?' in url:return {'data':{'drugs':{'tablet':{'10mg':'','20mg':''}}}}
   dose=q['dosage'][0]
   return {'data':{'display':'Example','dosage':dose,'form':'tablet','metric_quantity':30,'days_supply':'30','prices':[{'pharmacy':'Example pharmacy','type':'coupon','price':0 if dose=='10mg' else 12.34}]}}
  with patch.dict(os.environ,{'PANTRY_GOODRX_ENABLED':'1','PANTRY_GOODRX_API_KEY':'synthetic-api-key','PANTRY_GOODRX_SECRET':'synthetic-secret'}),patch.object(catalog,'fetch',side_effect=upstream):
   rows=pricing.browse('Example')['variants'];self.assertEqual([v['strength'] for v in rows],['10mg','20mg']);self.assertEqual(rows[0]['results'][0]['price'],'0.00');self.assertEqual(rows[1]['results'][0]['price'],'12.34');self.assertEqual(rows[0]['quantity'],'30')
  with patch.dict(os.environ,{'PANTRY_GOODRX_ENABLED':'0'}),patch.object(catalog,'fetch') as f:self.assertFalse(pricing.browse('Example')['configured']);f.assert_not_called()

 def test_public_catalog_prices_are_not_inferred_and_cache_has_no_user_query(self):
  base={'medication_name':'Example','brand_name':'Example Brand','strength':'10mg','form':'Tablet','brand_generic':'Generic','sample_volume':'30 count','url':'https://www.costplusdrugs.com/medications/example','cpd_channel':{'sample_pack_price_total_to_patient_without_shipping':'0','sample_pack_price_w_shipping_dispensing':'5.25','cash_shipping_cost':5.25,'cash_dispensing_fee':0,'in_stock':True,'currency':'USD'}}
  other=dict(base,strength='20mg',cpd_channel=dict(base['cpd_channel'],sample_pack_price_total_to_patient_without_shipping='12.34'))
  invalid=dict(base,strength='30mg',url='https://evil.invalid/')
  with patch.object(pricing,'_public_catalog',None),patch.object(catalog,'fetch',return_value=[base,other,invalid]) as f:
   r=pricing.public_prices('Example');self.assertEqual(len(r['results']),2);self.assertEqual(r['results'][0]['price'],'0.00');self.assertEqual(r['results'][0]['fill_size'],'30 count');self.assertEqual(r['results'][1]['price'],'12.34')
   self.assertTrue(pricing.public_prices('Example Brand')['results'][0]['generic_alternative']);self.assertEqual(pricing.public_prices('Unrelated')['results'],[]);self.assertEqual(pricing.public_prices('(Oral Pill)')['results'],[])
   f.assert_called_once_with('https://api.costplusdrugs.com/pricelist/cpd')
 def test_pharmacy_directory_is_zip_only_and_fixed_classification(self):
  with patch.object(catalog,'fetch',return_value=[1,['1234567890'],None,[['Example Pharmacy','Example address','212-555-0100','Pharmacy']]]) as f:r=catalog.pharmacies('10001')
  self.assertEqual(r['results'][0]['key'],'1234567890');q=urllib.parse.parse_qs(urllib.parse.urlsplit(f.call_args.args[0]).query);self.assertEqual(q['terms'],['10001']);self.assertIn('Pharmacy',q['q'][0])
if __name__=='__main__':unittest.main()
