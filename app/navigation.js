(function(){
 'use strict';
 const nav=document.querySelector('.nav'),bridge=window.PantryAdminBridge;
 const home=nav.querySelector('[data-page="dashboard"]');home.textContent='⌂ Home';
 function dropdown(id,label){const d=document.createElement('details');d.className='nav-dropdown';d.id=id;d.innerHTML=`<summary aria-controls="${id}-panel" aria-expanded="false">${label}<span aria-hidden="true">⌄</span></summary><div class="nav-panel" id="${id}-panel"></div>`;return d}
 const organize=dropdown('organize-menu','Organize'),account=dropdown('account-menu','Account');
 for(const page of ['inventory','recipes','locations','medicine'])organize.lastElementChild.append(nav.querySelector('[data-page="'+page+'"]'));
 account.classList.add('nav-account');
 for(const id of ['my-dashboard-nav','household-nav','admin-nav'])account.lastElementChild.append(document.getElementById(id));
 const signIn=document.createElement('button');signIn.type='button';signIn.id='nav-sign-in';signIn.textContent='Sign in / create household';signIn.onclick=()=>bridge.openAccount();account.lastElementChild.append(signIn);
 nav.append(organize,document.getElementById('kitchen-nav'),account);
 function close(except){for(const menu of [organize,account])if(menu!==except)menu.open=false}
 function sync(){
  const u=bridge.current(),admin=document.getElementById('admin-nav');
  const allowed=!!u&&Array.isArray(u.permissions)&&u.permissions.length>0;
  if(admin.hidden===allowed)admin.hidden=!allowed;
  if(signIn.hidden!==!!u)signIn.hidden=!!u;
  for(const menu of [organize,account]){
   const selected=[...menu.querySelectorAll('button')].some(b=>!b.hidden&&b.classList.contains('active'));
   menu.firstElementChild.classList.toggle('active',selected);
   menu.firstElementChild.setAttribute('aria-expanded',String(menu.open));
  }
  const current=document.querySelector('.section.active')?.id;
  for(const b of nav.querySelectorAll('button')){
   const selected=!b.hidden&&(b.dataset.page===current||(b.id==='admin-nav'&&['admin','admin-center'].includes(current)));
   if(selected)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');
  }
 }
 for(const menu of [organize,account])menu.addEventListener('toggle',()=>{if(menu.open)close(menu);sync()});
 nav.addEventListener('click',e=>{if(e.target.closest('button')){close();queueMicrotask(sync)}});
 document.addEventListener('click',e=>{if(!nav.contains(e.target))close()});
 document.addEventListener('keydown',e=>{if(e.key==='Escape'){const open=[organize,account].find(m=>m.open);if(open){close();open.firstElementChild.focus();e.preventDefault()}}});
 window.addEventListener('pantry-account-updated',()=>{close();sync()});
 new MutationObserver(sync).observe(document.querySelector('.main'),{subtree:true,attributes:true,attributeFilter:['class']});
 new MutationObserver(sync).observe(nav,{subtree:true,attributes:true,attributeFilter:['hidden']});
 sync();
})();
