import unittest,json,secrets,base64,io,threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from PIL import Image
from test_app import AppTests,server,client

class KitchenTests(unittest.TestCase):
 setUpClass=classmethod(AppTests.setUpClass.__func__)
 tearDownClass=classmethod(AppTests.tearDownClass.__func__)
 call=AppTests.call;register=AppTests.register
 def setUp(self):
  server.RATE.clear();self.a=client();self.b=client();self.ua=self.register(self.a);self.ub=self.register(self.b)
  self.egg=self.call(self.a,'/api/items','POST',{'name':'Eggs','qty':2,'unit':'each','is_food':True},self.ua['csrf'],201)['item']
 def api(self,path,method='GET',data=None,status=200):return self.call(self.a,'/api/kitchen/'+path,method,data,self.ua['csrf'],status)
 def recipe(self,amount=4,**extra):
  data={'name':'My egg dish','servings':2,'description':'A test recipe','prep_minutes':0,'cook_minutes':5,'visibility':'personal',
   'ingredient_lines':[{'ref':'pantry:'+self.egg['id'],'amount':amount,'unit':'each','preparation':'beaten'}],
   'steps':[{'text':'Beat the eggs.','image':''},{'text':'Cook until set.','image':''}]}
  data.update(extra);return self.api('recipes','POST',data,201)
 def plan(self,rid,servings=2):return self.api('plans','POST',{'recipe_id':rid,'date':'2026-10-25','slot':'Dinner','servings':servings},201)['id']
 def shopping(self):return self.api('lists','POST',{'name':'Weekly groceries'},201)['id']
 def test_guided_validation_pantry_links_and_scope(self):
  found=self.api('ingredients?q=Eggs');self.assertEqual(found['ingredients'][0]['ref'],'pantry:'+self.egg['id'])
  d=self.recipe();r=d['recipe'];self.assertTrue(r['guided']);self.assertEqual(r['ingredient_lines'][0]['product']['name'],'Eggs');self.assertEqual(r['instructions'][1],'Cook until set.')
  self.assertEqual(self.call(self.b,'/api/recipes')['recipes'],[])
  self.call(self.b,'/api/kitchen/recipes/'+r['id'],status=404)
  payload={'name':'Invalid','servings':2,'ingredient_lines':[{'ref':'pantry:'+self.egg['id'],'amount':2,'unit':'each'}],'steps':[{'text':'Cook.'}]}
  self.call(self.b,'/api/kitchen/recipes','POST',payload,self.ub['csrf'],400)
  for changes in [{'ingredient_lines':[]},{'steps':[]},{'steps':[{'text':''}]},{'ingredient_lines':[{'ref':'off:forged','amount':1,'unit':'each'}]},{'servings':0}]:
   self.api('recipes','POST',dict(payload,**changes),400)
 def test_public_database_results_are_persisted_not_client_asserted(self):
  response={'meals':[{'idIngredient':'700','strIngredient':'Eggs','strDescription':'Eggs description'}]}
  with patch.object(server.kitchen._api,'json_fetch',return_value=response),patch.object(server.kitchen._api,'lookup',return_value={'products':[],'warnings':[]}):
   d=self.api('ingredients?q=Eggs&public=1');self.assertTrue(any(i['ref']=='mealdb:700' for i in d['ingredients']))
  d=self.recipe(ingredient_lines=[{'ref':'mealdb:700','amount':'1 1/2','unit':'each'}]);self.assertEqual(d['recipe']['ingredient_lines'][0]['amount'],1.5)
  self.assertEqual(d['recipe']['ingredient_lines'][0]['product']['description'],'Eggs description')
 def test_optional_step_photos_are_owned_and_retained_on_edit(self):
  out=io.BytesIO();Image.new('RGB',(40,40),'yellow').save(out,format='JPEG')
  image=self.call(self.a,'/api/upload','POST',{'image':'data:image/jpeg;base64,'+base64.b64encode(out.getvalue()).decode()},self.ua['csrf'],201)['image']
  saved=self.recipe(steps=[{'text':'Cook the eggs.','image':image}]);r=saved['recipe']
  edit=self.api('recipes/'+r['id']);payload=dict(r,revision=edit['revision'],prep_minutes=0,cook_minutes=1,ingredient_lines=[{'ref':'pantry:'+self.egg['id'],'amount':4,'unit':'each'}])
  self.api('recipes/'+r['id'],'PUT',payload);self.api('recipes/'+r['id'],'PUT',payload,409)
  self.assertEqual(self.api('recipes/'+r['id'])['recipe']['steps'][0]['image'],image)
  self.call(self.b,'/media/'+image.rsplit('/',1)[1],status=404)
  self.call(self.a,'/api/recipes/'+r['id'],'PUT',r,self.ua['csrf'],409)
 def test_plan_scaling_aggregates_stock_once_across_days(self):
  r=self.recipe()['recipe'];p1=self.plan(r['id']);p2=self.plan(r['id'],4)
  d=self.api('requirements','POST',{'plan_ids':[p1,p2]});line=d['ingredients'][0]
  self.assertEqual(line['required'],12);self.assertEqual(line['available'],2);self.assertEqual(line['needed'],10)
  self.assertEqual(self.call(self.a,'/api/items')['items'][0]['qty'],2)
  self.call(self.b,'/api/kitchen/requirements','POST',{'plan_ids':[p1]},self.ub['csrf'],404)
 def test_mass_conversion_and_ambiguous_packages_are_not_assumed(self):
  item=self.call(self.a,'/api/items','POST',{'name':'Flour','qty':0.25,'unit':'kg'},self.ua['csrf'],201)['item']
  r=self.recipe(ingredient_lines=[{'ref':'pantry:'+item['id'],'amount':500,'unit':'g'}])['recipe'];p=self.plan(r['id'])
  line=self.api('requirements','POST',{'plan_ids':[p]})['ingredients'][0];self.assertEqual(line['needed'],250);self.assertFalse(line['review'])
  item=self.call(self.a,'/api/items','POST',{'name':'Oil','qty':2,'unit':'bottle','weight':'500 ml'},self.ua['csrf'],201)['item']
  r=self.recipe(ingredient_lines=[{'ref':'pantry:'+item['id'],'amount':100,'unit':'ml'}])['recipe'];p=self.plan(r['id'])
  line=self.api('requirements','POST',{'plan_ids':[p]})['ingredients'][0];self.assertTrue(line['review']);self.assertEqual(line['available'],0)
 def test_existing_suggestions_and_imports_can_be_planned_with_review(self):
  p=self.plan('builtin-cheesy-spinach-omelet');d=self.api('requirements','POST',{'plan_ids':[p]});self.assertTrue(all(i['review'] and i['needed'] is None for i in d['ingredients']))
  imported=self.call(self.a,'/api/recipes/import','POST',{'recipes':[{'name':'Old recipe','ingredients':['1 cup flour'],'instructions':['Mix.'],'yield':'2 servings'}]},self.ua['csrf'],201)['recipes'][0]
  p=self.plan(imported['id']);self.assertTrue(self.api('requirements','POST',{'plan_ids':[p]})['ingredients'][0]['review'])
 def test_grocery_generation_is_repeat_safe_and_lists_are_private(self):
  r=self.recipe()['recipe'];p=self.plan(r['id']);lid=self.shopping()
  self.assertEqual(self.api('lists/'+lid+'/from-plans','POST',{'plan_ids':[p]})['added'],1)
  self.assertEqual(self.api('lists/'+lid+'/from-plans','POST',{'plan_ids':[p]})['added'],0)
  self.assertEqual(len(self.api('lists/'+lid)['lines']),1)
  self.call(self.b,'/api/kitchen/lists/'+lid,status=404)
 def test_scanning_and_basket_only_add_stock_after_confirmed_checkout(self):
  lid=self.shopping();self.api('lists/'+lid+'/lines','POST',{'ref':'pantry:'+self.egg['id'],'quantity':3,'unit':'each'},201)
  line=self.api('lists/'+lid)['lines'][0]
  self.api('lists/'+lid+'/checkout','POST',{'line_ids':[line['id']],'confirmed':True},409)
  self.api('lines/'+line['id'],'PATCH',{'revision':line['revision'],'state':'basket','purchase_qty':3,'purchase_unit':'each','location':'Pantry'})
  self.assertEqual(self.call(self.a,'/api/items')['items'][0]['qty'],2)
  self.api('lists/'+lid+'/checkout','POST',{'line_ids':[line['id']],'confirmed':False},400)
  for _ in range(2):self.api('lists/'+lid+'/checkout','POST',{'line_ids':[line['id']],'confirmed':True})
  self.assertEqual(self.call(self.a,'/api/items')['items'][0]['qty'],5)
  self.assertEqual(self.api('lists/'+lid)['lines'][0]['state'],'purchased')
 def test_separate_batches_recompute_all_meals_without_reusing_stock(self):
  r=self.recipe()['recipe'];a=self.plan(r['id']);b=self.plan(r['id']);lid=self.shopping()
  self.api('lists/'+lid+'/from-plans','POST',{'plan_ids':[a]})
  self.assertEqual(self.api('lists/'+lid)['lines'][0]['quantity'],2)
  self.api('lists/'+lid+'/from-plans','POST',{'plan_ids':[b]})
  rows=self.api('lists/'+lid)['lines'];self.assertEqual(len(rows),1);self.assertEqual(rows[0]['quantity'],6)
  self.api('lists/'+lid+'/from-plans','POST',{'plan_ids':[a]})
  self.assertEqual(self.api('lists/'+lid)['lines'][0]['quantity'],6)
 def test_scanned_product_keeps_generic_ingredient_link_after_purchase(self):
  server.kitchen.remember([{'ref':'mealdb:test-milk','name':'Milk','barcode':'','image':'','source':'TheMealDB','description':''},
   {'ref':'off:1234567890123','name':'Brand whole milk','barcode':'1234567890123','image':'','source':'Open Food Facts','description':''}])
  r=self.recipe(ingredient_lines=[{'ref':'mealdb:test-milk','amount':250,'unit':'ml'}])['recipe'];p=self.plan(r['id']);lid=self.shopping()
  self.api('lists/'+lid+'/from-plans','POST',{'plan_ids':[p]});line=self.api('lists/'+lid)['lines'][0]
  self.api('lines/'+line['id'],'PATCH',{'revision':line['revision'],'state':'basket','purchase_ref':'off:1234567890123','purchase_qty':500,'purchase_unit':'ml','location':'Fridge'})
  self.api('lists/'+lid+'/checkout','POST',{'line_ids':[line['id']],'confirmed':True})
  need=self.api('requirements','POST',{'plan_ids':[p]})['ingredients'][0];self.assertEqual(need['needed'],0)
  stock=next(i for i in self.call(self.a,'/api/items')['items'] if i['name']=='Brand whole milk')
  self.call(self.a,'/api/items/'+stock['id'],'PUT',dict(stock,notes='Keep chilled'),self.ua['csrf'])
  self.assertEqual(self.api('requirements','POST',{'plan_ids':[p]})['ingredients'][0]['needed'],0)
 def test_checkout_is_atomic_and_concurrent_retries_do_not_duplicate(self):
  lid=self.shopping();self.api('lists/'+lid+'/lines','POST',{'ref':'pantry:'+self.egg['id']},201);line=self.api('lists/'+lid)['lines'][0]
  self.api('lines/'+line['id'],'PATCH',{'revision':line['revision'],'state':'basket','purchase_qty':1,'purchase_unit':'each'})
  self.api('lists/'+lid+'/checkout','POST',{'line_ids':[line['id'],'f'*24],'confirmed':True},404)
  self.assertEqual(self.call(self.a,'/api/items')['items'][0]['qty'],2)
  with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(lambda _:self.api('lists/'+lid+'/checkout','POST',{'line_ids':[line['id']],'confirmed':True}),range(2)))
  self.assertEqual(self.call(self.a,'/api/items')['items'][0]['qty'],3)
 def test_basket_state_and_purchase_products_are_validated_and_scoped(self):
  lid=self.shopping();self.api('lists/'+lid+'/lines','POST',{'ref':'pantry:'+self.egg['id']},201);line=self.api('lists/'+lid)['lines'][0]
  for changes in [{'state':'purchased'},{'state':'basket','purchase_qty':0,'purchase_unit':'each'},{'purchase_ref':'off:fake'}]:self.api('lines/'+line['id'],'PATCH',dict(changes,revision=line['revision']),400)
  self.call(self.b,'/api/kitchen/lines/'+line['id'],'PATCH',{'state':'needed','revision':line['revision']},self.ub['csrf'],404)
  self.api('lines/'+line['id'],'PATCH',{'state':'needed','revision':'stale'},409)

del AppTests
