(function(){
 'use strict';
 const api=window.PantryAdminBridge.api,f=$('#item-form');
 let sections=[
  {id:'personal-care',name:'Personal care',icon:'🧴',description:'Soap, shampoo, lotion and bathroom supplies'},
  {id:'cleaning-supplies',name:'Household supplies',icon:'🧹',description:'Cleaning, laundry and daily supplies'},
  {id:'clothing-closet',name:'Clothing and closets',icon:'👕',description:'Clothes, shoes and accessories'},
  {id:'tools-hardware',name:'Tools and hardware',icon:'🛠',description:'Tools, screws, nails, fasteners, glue and tape'},
  {id:'medicines-first-aid',name:'Medicines and first aid',icon:'🩹',description:'Medication inventory and first aid supplies'},
  {id:'other-home',name:'Other home items',icon:'🏠',description:'Furniture, electronics and other possessions'}];
 try{const saved=JSON.parse(localStorage.getItem('pp-home-sections'));if(Array.isArray(saved)&&saved.length)sections=saved}catch{}
 window.PantryActiveHomeSection='';
 const grid=document.createElement('div');grid.className='panel';grid.id='home-sections-panel';grid.innerHTML='<h3>Your Home inventory sections</h3><p>Keep clothes, tools, supplies, medicines, and other belongings in their own sections.</p><div id="home-section-grid" class="home-section-grid"></div>';
 $('#dashboard .hero').after(grid);
 const bar=document.createElement('div');bar.className='home-section-bar';bar.innerHTML='<label>Home inventory section<select id="home-section-filter" aria-label="Filter Home inventory section"></select></label>';$('#inventory .panel').prepend(bar);
 const label=document.createElement('label');label.className='form-field';label.id='entry-home-section-row';label.innerHTML='Home inventory section<select name="home_section" id="entry-home-section"></select>';$('#item-form .form-grid').append(label);
 for(const category of ['Clothing and closets','Tools and hardware','Medicines and first aid'])if(![...f.elements.category.options].some(o=>o.value===category))f.elements.category.add(new Option(category,category));
 const oldRender=render,oldOpen=openAdd;
 function sync(){
  const home=activeMode==='home';grid.hidden=!home;bar.hidden=!home;
  const all=PantryModes.filter(items,'home'),visible=sections.filter(s=>!s.archived||all.some(i=>PantryModes.homeSection(i)===s.id));
  for(const item of all){const id=PantryModes.homeSection(item);if(!visible.some(s=>s.id===id))visible.push({id,name:'Saved section',icon:'📦',description:'Existing items retained'})}
  const current=window.PantryActiveHomeSection;
  $('#home-section-grid').innerHTML=`<button type="button" data-home-section="" aria-pressed="${!current}"><strong>All Home items</strong><small>${all.length} items</small></button>`+visible.map(s=>`<button type="button" data-home-section="${esc(s.id)}" aria-pressed="${current===s.id}"><strong>${esc(s.icon)} ${esc(s.name)}${s.archived?' · archived':''}</strong><small>${all.filter(i=>PantryModes.homeSection(i)===s.id).length} items · ${esc(s.description||'')}</small></button>`).join('');
  const select=$('#home-section-filter');select.innerHTML='<option value="">All Home items</option>'+visible.map(s=>`<option value="${esc(s.id)}">${esc(s.name)}${s.archived?' (archived)':''}</option>`).join('');select.value=current;
  const previous=f.elements.home_section.value;f.elements.home_section.innerHTML='<option value="">Choose a Home section</option>'+sections.filter(s=>!s.archived||s.id===previous).map(s=>`<option value="${esc(s.id)}">${esc(s.icon)} ${esc(s.name)}${s.archived?' (archived)':''}</option>`).join('');f.elements.home_section.value=previous;
  formMode();
 }
 function formMode(){const household=f.elements.is_food.value==='false';label.hidden=!household;f.elements.home_section.disabled=!household}
 function choose(id){window.PantryActiveHomeSection=id;activeFilter='All';$('#search').value='';goto('inventory');render()}
 render=function(){oldRender();sync()};
 openAdd=function(){oldOpen();f.elements.home_section.value=activeMode==='home'?(window.PantryActiveHomeSection||'personal-care'):'';if(activeMode==='home'){const id=f.elements.home_section.value;f.elements.location.value=({'tools-hardware':'Garage','clothing-closet':'Closet','medicines-first-aid':'Medicine cabinet','personal-care':'Bathroom','cleaning-supplies':'Utility closet'})[id]||'Other';const category=({'tools-hardware':'Tools and hardware','clothing-closet':'Clothing and closets','medicines-first-aid':'Medicines and first aid'})[id];if(category)f.elements.category.value=category}formMode()};
 window.addEventListener('pantry-entry-ready',e=>{const item=e.detail;if(item){f.elements.home_section.disabled=false;f.elements.home_section.value=PantryModes.isFood(item)?'':PantryModes.homeSection(item)}formMode()});
 f.elements.is_food.addEventListener('change',()=>{if(f.elements.is_food.value==='false'&&!f.elements.home_section.value)f.elements.home_section.value=window.PantryActiveHomeSection||'personal-care';formMode()});
 $('#home-section-filter').onchange=e=>choose(e.target.value);
 document.addEventListener('click',e=>{const b=e.target.closest('[data-home-section]');if(b)choose(b.dataset.homeSection)});
 async function load(){if(!window.PantryAdminBridge.current())return;try{sections=(await api('home-sections')).sections;try{localStorage.setItem('pp-home-sections',JSON.stringify(sections))}catch{}render()}catch{}}
 window.addEventListener('pantry-sections-updated',load);window.addEventListener('pantry-account-updated',load);load();render();
})();
