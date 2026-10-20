(function(){
 'use strict';
 const f=$('#item-form');
 const oldRender=render,oldGoto=goto,oldOpen=openAdd;
 const homeCategories=['Bathroom supplies','Fragrance','Laundry','Household supplies','Tools & electronics','Furniture & valuables'];
 for(const value of homeCategories)if(![...f.elements.category.options].some(o=>o.value===value))f.elements.category.add(new Option(value,value));
 f.elements.is_food.closest('label').firstChild.textContent='Item belongs to';
 f.elements.is_food.options[0].textContent='Kitchen — food & drink';
 f.elements.is_food.options[1].textContent='Home inventory — household items';
 $('.main').insertAdjacentHTML('afterbegin',`<section class="mode-banner" aria-label="Current inventory mode"><div class="mode-banner-copy"><span id="mode-art" class="mode-art" aria-hidden="true">🍽</span><div><strong id="mode-label">Kitchen mode</strong><p id="mode-description">Food, drinks & recipe ideas</p></div></div><div class="mode-switch" role="group" aria-label="Choose mode"><button type="button" data-mode="kitchen" aria-label="Kitchen mode" aria-pressed="true">Kitchen <span id="kitchen-count"></span></button><button type="button" data-mode="home" aria-label="Home inventory mode" aria-pressed="false">Home inventory <span id="home-count"></span></button></div></section>`);
 const recipePanel=$('#recipe-preview').closest('.panel');
 function page(){return $('.section.active')?.id||'dashboard'}
 function pageText(p){
  if(p==='admin')return;
  const kitchen=activeMode==='kitchen';
  const text={dashboard:kitchen?['Good afternoon!','A clear view of what’s stocked and what you can make.']:['Good afternoon!','A clear view of what’s stocked around your home.'],inventory:kitchen?['Kitchen inventory','Your food and drinks, ready to count, find, and cook with.']:['Home inventory','Cleaning, personal care, and the everyday supplies you keep at home.'],locations:kitchen?['Kitchen storage','Find food in your pantry, refrigerator, and freezer.']:['Household storage','Find supplies in the bathroom, laundry room, garage, and other spaces.'],recipes:['Recipe ideas','Make something delicious from the food you already have.']}[p];
  if(text){$('#page-title').textContent=text[0];$('#page-sub').textContent=text[1]}
 }
 function syncMode(){
  const kitchen=activeMode==='kitchen';document.body.dataset.mode=activeMode;
  $('#mode-label').textContent=kitchen?'Kitchen mode':'Home inventory mode';
  $('#mode-description').textContent=kitchen?'Food, drinks & recipe ideas':'Supplies, clothing, tools & more';
  $('#mode-art').textContent=kitchen?'🍽':'🧴';
  $('#kitchen-count').textContent='('+PantryModes.filter(items,'kitchen').length+')';
  $('#home-count').textContent='('+PantryModes.filter(items,'home').length+')';
  $$('.mode-switch [data-mode]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.mode===activeMode)));
  $('.topline .eyebrow').textContent=kitchen?'FROM YOUR PANTRY TO YOUR PLATE':'EVERYDAY ESSENTIALS, IN THEIR PLACE';
  $('.hero .eyebrow').textContent=kitchen?'YOUR KITCHEN AT A GLANCE':'YOUR HOME AT A GLANCE';
  $('.hero h2').textContent=kitchen?'Good food starts with what you have.':'A well-stocked home, without the guesswork.';
  $('.hero p').textContent=kitchen?'Know what’s in your pantry, fridge and freezer. Find something good to make.':'Keep supplies, clothes, tools, hardware, medicines, and other belongings organized.';
  $('.side-note').textContent=kitchen?'Less waste. More meals. Keep food visible and make dinner easier.':'Find it before you buy it. Keep everyday supplies organized throughout your home.';
  $('[data-page="recipes"]').hidden=!kitchen;recipePanel.hidden=!kitchen;
  const stats=$$('.stats .stat');stats[0].querySelector('.stat-foot').textContent=kitchen?'Food & drink only':'Household items only';
  stats[2].querySelector('.stat-foot').textContent=kitchen?'Pantry to freezer':'Every room, closet and workbench';
  stats[3].querySelector('.stat-label').textContent=kitchen?'Recipes to try':'Running low';
  stats[3].querySelector('.stat-foot').textContent=kitchen?'Based on your food stock':'One unit or less';
  $('#inventory .panel-head h3').textContent=kitchen?'Kitchen inventory':'Household inventory';
  $('#search').placeholder=kitchen?'Search food, drinks, or brands…':'Search clothing, tools, supplies…';
  $('#filters').innerHTML=['All',...PantryModes.locations(items,activeMode)].map(l=>`<button class="chip ${l===activeFilter?'active':''}" data-filter="${esc(l)}">${esc(l==='All'?'All items':l==='Refrigerator'?'Fridge':l)}</button>`).join('');
  for(const option of [...f.elements.location.options])if(option.dataset.customLocation)option.remove();
  for(const location of (window.PantryCustomLocations||[]).filter(l=>l.mode===(kitchen?'kitchen':'home')))if(![...f.elements.location.options].some(o=>o.value.toLowerCase()===location.name.toLowerCase())){const option=new Option(location.name,location.name);option.dataset.customLocation='true';f.elements.location.add(option)}
  if(!modeItems().length){$('#inventory-list').innerHTML=`<div class="empty">${kitchen?'No food or drinks yet. Add cereal, ingredients, or your favorite snacks.':'No household items yet. Add soap, shampoo, cleaning products, or other supplies.'}</div>`}
  pageText(page());
 }
 render=function(){oldRender();syncMode()};
 goto=function(p){if(activeMode==='home'&&p==='recipes')p='dashboard';oldGoto(p);pageText(p)};
 function switchMode(mode){
  if(!['kitchen','home'].includes(mode))return;
  const current=page();activeMode=mode;activeFilter='All';$('#search').value='';
  try{localStorage.setItem('pp-mode',mode)}catch{}
  $('#lookup-source').value=mode==='home'?'all':'food';
  render();goto(current==='recipes'||current==='admin'||current==='admin-center'?'dashboard':current);
 }
 openAdd=function(){oldOpen();const home=activeMode==='home';f.elements.is_food.value=home?'false':'true';f.elements.category.value=home?'Personal care':'Grains & pasta';f.elements.location.value=home?'Bathroom':'Pantry';f.elements.name.placeholder=home?'e.g. Shampoo or toilet cleaner':'e.g. Cereal or rolled oats'};
 $$('.mode-switch [data-mode]').forEach(b=>b.onclick=()=>switchMode(b.dataset.mode));
 window.PantryModeView={showItem(item){activeFilter='All';$('#search').value='';switchMode(PantryModes.isFood(item)?'kitchen':'home')}};
 $('#lookup-source').value=activeMode==='home'?'all':'food';
 render();
})();
