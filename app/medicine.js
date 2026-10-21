(function(){
'use strict';
const bridge=window.PantryAdminBridge;
let state=null,epoch=0,tab='prescription',editing=null,loading=false;
const labels={prescription:'Prescriptions',doctor:'Doctors',appointment:'Appointments',pharmacy:'Household pharmacy'};
const fields={
 doctor:[['name','Doctor name','text',true],['specialty','Specialty'],['practice','Practice / clinic'],['phone','Phone','tel'],['email','Email','email'],['address','Address','textarea'],['notes','Notes','textarea']],
 prescription:[['name','Medicine name','text',true],['strength','Strength (as printed on the label)'],['directions','Directions from your prescription label','textarea'],['quantity','Quantity on hand','number'],['unit','Quantity unit (tablets, mL, etc.)'],['refills_remaining','Refills remaining','integer'],['last_filled','Last filled','date'],['next_refill','Next refill date','date'],['expires','Prescription expiration','date'],['pharmacy','Pharmacy name'],['pharmacy_phone','Pharmacy phone','tel'],['pharmacy_address','Pharmacy address','textarea'],['rx_number','Prescription number'],['notes','Personal notes','textarea']],
 appointment:[['name','Visit / appointment title','text',true],['starts','Date and time','datetime-local',true],['timezone','Time zone (for example America/New_York)','text',true],['location','Clinic / address / video visit details','textarea',true],['phone','Appointment contact phone','tel'],['notes','Notes / things to bring','textarea']]
};
const style=document.createElement('style');style.textContent=`
.medicine-area .mode-banner{display:none}.medicine-banner{border:1px solid #ccc0e4;border-radius:20px;padding:22px;background:linear-gradient(115deg,#f0e8fb,#e6f4f5);margin-bottom:20px}.medicine-banner h2{margin:0;color:#583374}.medicine-banner p{margin:8px 0}.medicine-tabs{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0}.medicine-tabs button[aria-pressed=true]{background:#583374;color:white}.medicine-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,310px),1fr));gap:16px}.medicine-card{border:1px solid var(--line);border-radius:16px;padding:18px;background:var(--white,#fff);overflow-wrap:anywhere}.medicine-card h3{margin:0 0 12px;font-size:22px}.medicine-card dl{display:grid;grid-template-columns:minmax(95px,1fr) minmax(0,2fr);gap:7px;margin:14px 0}.medicine-card dt{font-weight:600}.medicine-card dd{margin:0;white-space:pre-wrap}.medicine-tools{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:14px 0}.medicine-tools input[type=search]{flex:1;min-width:150px}.medicine-dialog{width:min(700px,calc(100vw - 24px));max-height:90vh;border:1px solid var(--line);border-radius:20px;padding:22px;overflow:auto}.medicine-dialog::backdrop{background:#15253680}.medicine-form{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.medicine-form label{display:flex;flex-direction:column;gap:6px;font-weight:600}.medicine-form input,.medicine-form select,.medicine-form textarea{width:100%;min-width:0;padding:11px;border:1px solid #c7c4ce;border-radius:9px;font:inherit}.medicine-form textarea{min-height:88px}.medicine-wide{grid-column:1/-1}.medicine-note{font-size:14px;color:#625e71}.medicine-error{color:#9a273e}.medicine-card .medicine-archived{font-weight:600;color:#625e71}@media(max-width:600px){.medicine-form{grid-template-columns:1fr}.medicine-card dl{grid-template-columns:1fr}.medicine-card dd{margin-bottom:5px}.medicine-dialog{padding:16px}}
`;document.head.append(style);
$('.nav').insertAdjacentHTML('beforeend','<button id="medicine-nav" data-page="medicine">✚ Medicine</button>');
$('.main').insertAdjacentHTML('beforeend',`<section class="section" id="medicine"><div class="medicine-banner"><h2>✚ Medicine & pharmacy</h2><p>Your private medicine cabinet and your household’s everyday pharmacy supplies.</p><p class="medicine-note">Personal prescriptions, doctors and appointments are visible and editable only through your own account. Shared supplies stay in Home inventory.</p></div><div class="panel"><div id="medicine-heading"></div><nav class="medicine-tabs" aria-label="Medicine sections">${Object.entries(labels).map(([key,label])=>`<button type="button" class="secondary" data-medicine-tab="${key}">${label}</button>`).join('')}</nav><div class="medicine-tools"><input type="search" id="medicine-search" aria-label="Search medicine area" placeholder="Search this section"><label><input type="checkbox" id="medicine-archives"> Show archived</label><button class="secondary" id="medicine-reload">Refresh</button><button class="primary" id="medicine-add">Add prescription</button></div><p id="medicine-status" role="status"></p><div id="medicine-list" class="medicine-grid"></div></div></section>`);
document.body.insertAdjacentHTML('beforeend',`<dialog id="medicine-editor" class="medicine-dialog" aria-labelledby="medicine-editor-title"><h2 id="medicine-editor-title"></h2><form id="medicine-form"><div id="medicine-fields" class="medicine-form"></div><p id="medicine-form-error" class="medicine-error" role="alert"></p><div class="medicine-tools"><button type="button" class="secondary" id="medicine-cancel">Cancel</button><button class="primary" type="submit" id="medicine-save">Save</button></div></form></dialog>`);
const oldGoto=goto;goto=function(page){oldGoto(page);document.body.classList.toggle('medicine-area',page==='medicine');if(page==='medicine'){$('#page-title').textContent='Medicine & pharmacy';$('#page-sub').textContent='Personal care records and shared household supplies.'}};
async function api(path='',method='GET',data){const e=epoch,r=await bridge.api('medicine/'+path,method,data);if(e!==epoch)throw new Error('Your account changed. Reopen Medicine.');return r}
function message(s){$('#medicine-status').textContent=s}
function doctor(id){return state?.records.find(r=>r.kind==='doctor'&&r.id===id)}
function detail(label,value){return value===null||value===undefined||value===''?'':`<dt>${esc(label)}</dt><dd>${esc(String(value))}</dd>`}
function draw(){
 if(!state)return;
 const next=state.records.filter(r=>r.kind==='appointment'&&!r.archived&&new Date(r.starts_utc)>=new Date()).sort((a,b)=>a.starts_utc.localeCompare(b.starts_utc))[0];
 $('#medicine-heading').innerHTML=`<h2>${esc(state.cabinet.name)}</h2><p>Private to ${esc(bridge.current()?.name||'you')}. ${state.records.filter(r=>r.kind==='prescription'&&!r.archived).length} active prescriptions.</p>${next?`<p><strong>Next visit:</strong> ${esc(next.name)} · ${esc(next.starts.replace('T',' '))} (${esc(next.timezone)}) · ${esc(next.location)}</p>`:'<p>No upcoming appointments saved.</p>'}<button type="button" class="secondary" id="medicine-rename">Name my cabinet</button>`;
 for(const b of $$('#medicine [data-medicine-tab]'))b.setAttribute('aria-pressed',String(b.dataset.medicineTab===tab));
 $('#medicine-add').textContent=tab==='pharmacy'?'Add shared supply':tab==='doctor'?'Add doctor':tab==='appointment'?'Add appointment':'Add prescription';
 $('#medicine-archives').closest('label').hidden=tab==='pharmacy';
 const term=$('#medicine-search').value.trim().toLocaleLowerCase();
 let rows=(tab==='pharmacy'?state.pharmacy:state.records.filter(r=>r.kind===tab)).filter(r=>(!r.archived||$('#medicine-archives').checked)&&(!term||JSON.stringify(r).toLocaleLowerCase().includes(term)));
 if(tab==='appointment')rows.sort((a,b)=>Number(new Date(a.starts_utc)<new Date())-Number(new Date(b.starts_utc)<new Date())||a.starts_utc.localeCompare(b.starts_utc));
 if(tab==='prescription')rows.sort((a,b)=>(a.next_refill||'9999').localeCompare(b.next_refill||'9999'));
 $('#medicine-list').innerHTML=rows.map(r=>{
  if(tab==='pharmacy')return `<article class="medicine-card"><h3>${esc(r.name)}</h3><dl>${detail('Stock',`${r.qty} ${r.unit||'units'}`)}${detail('Location',r.location)}${detail('Inventory owner',r.owner)}${detail('Best by',r.bestBy)}</dl><p class="medicine-note">Shared from Home inventory · Medicines and first aid. Stock is counted once.</p></article>`;
  const names=Object.fromEntries(fields[r.kind].map(f=>[f[0],f[1]]));let details='';
  if(r.doctor_id){const d=doctor(r.doctor_id);details+=detail('Doctor',d?d.name+(d.archived?' (archived)':''):'Doctor unavailable');if(d){details+=detail('Doctor phone',d.phone);details+=detail('Doctor address',d.address)}}
  for(const [key,label] of Object.entries(names))if(key!=='name')details+=detail(label,r[key]);
  return `<article class="medicine-card"><h3>${esc(r.name)}</h3>${r.archived?'<p class="medicine-archived">Archived</p>':''}<dl>${details}</dl><div class="medicine-tools"><button type="button" class="secondary" data-medicine-edit="${r.id}">Edit ${r.kind}</button><button type="button" class="secondary" data-medicine-archive="${r.id}">${r.archived?'Restore':'Archive'}</button></div></article>`;
 }).join('')||`<p>No ${esc(labels[tab].toLowerCase())} ${term?'match your search':'yet'}.</p>`;
 if(tab==='pharmacy'){$('#medicine-list').insertAdjacentHTML('beforeend','<div class="medicine-wide"><button type="button" class="secondary" id="medicine-manage-stock">Manage shared stock in Home inventory</button></div>');message('OTC medicines and supplies in the Medicines and first aid Home section appear here. Stock is counted once. Keep personal prescriptions in your private cabinet.')}else message('');
}
async function load(){
 if(!bridge.current()){$('#medicine-heading').innerHTML='<p>Sign in to open your private cabinet.</p>';$('#medicine-list').replaceChildren();message('');return}
 if(loading)return;loading=true;const e=epoch;message('Loading your cabinet…');
 try{const next=await api('state');if(e!==epoch)return;state=next;draw()}catch(err){if(e===epoch)message(err.message)}finally{if(e===epoch)loading=false}
}
async function open(){if(!bridge.current()){bridge.openAccount();return}goto('medicine');await load()}
function editor(kind,r=null){
 editing=r?{...r}:{kind};$('#medicine-form-error').textContent='';$('#medicine-editor-title').textContent=kind==='cabinet'?'Name your medicine cabinet':(r?'Edit ':'Add ')+kind;
 const list=kind==='cabinet'?[['name','Cabinet name','text',true]]:fields[kind];const data=r||{};
 $('#medicine-fields').innerHTML=(['prescription','appointment'].includes(kind)?`<label class="medicine-wide">${kind==='prescription'?'Prescribing doctor':'Doctor'}<select name="doctor_id"><option value="">Not selected</option>${state.records.filter(d=>d.kind==='doctor'&&(!d.archived||d.id===data.doctor_id)).map(d=>`<option value="${d.id}" ${d.id===data.doctor_id?'selected':''}>${esc(d.name)}${d.archived?' (archived)':''}</option>`).join('')}</select><small>Add a doctor in the Doctors section to link their contact details.</small></label>`:'')+list.map(([key,label,type='text',required=false])=>{
  let value=data[key]??'';if(key==='timezone'&&!value)value=Intl.DateTimeFormat().resolvedOptions().timeZone||'UTC';
  const maximum=kind==='cabinet'?100:kind==='doctor'?({name:160,specialty:160,practice:200,phone:80,email:200,address:500,notes:1500}[key]):({name:160,strength:120,directions:1500,unit:60,pharmacy:200,pharmacy_phone:80,pharmacy_address:500,rx_number:120,notes:1500,location:500,phone:80,timezone:100}[key]||100);
  return `<label class="${type==='textarea'?'medicine-wide':''}">${esc(label)}${required?' *':''}${type==='textarea'?`<textarea name="${key}" maxlength="${maximum}" ${required?'required':''}>${esc(value)}</textarea>`:`<input name="${key}" type="${type==='integer'?'number':type}" value="${esc(value)}" maxlength="${maximum}" ${['number','integer'].includes(type)?`min="0" max="1000000" step="${type==='integer'?'1':'any'}"`:''} ${required?'required':''}>`}</label>`;
 }).join('');$('#medicine-save').disabled=false;$('#medicine-editor').showModal();
}
$('#medicine-form').onsubmit=async e=>{e.preventDefault();const button=$('#medicine-save');button.disabled=true;const saved=editing;
 try{const d=Object.fromEntries(new FormData(e.target));d.kind=saved.kind;d.archived=saved.archived||false;d.revision=saved.revision||'';
  await api(saved.kind==='cabinet'?'cabinet':saved.id?'records/'+saved.id:'records',saved.kind==='cabinet'||saved.id?'PUT':'POST',d);$('#medicine-editor').close();editing=null;await load();toast('Medicine cabinet saved.');
 }catch(err){$('#medicine-form-error').textContent=err.message}finally{button.disabled=false}};
$('#medicine-cancel').onclick=()=>$('#medicine-editor').close();
$('#medicine-editor').addEventListener('close',()=>{$('#medicine-form').reset();$('#medicine-fields').replaceChildren();editing=null});
$('#medicine-nav').onclick=open;$('#medicine-reload').onclick=load;
$('#medicine-search').oninput=draw;$('#medicine-archives').onchange=draw;
function sharedStock(add=false){document.querySelector('[data-mode="home"]').click();window.PantryActiveHomeSection='medicines-first-aid';activeFilter='All';$('#search').value='';goto('inventory');render();if(add){const location=$('#item-form').elements.location;if(![...location.options].some(o=>o.value==='Medicine cabinet'))location.add(new Option('Medicine cabinet','Medicine cabinet'));openAdd()}}
$('#medicine-add').onclick=()=>{if(!state){bridge.openAccount();return}if(tab==='pharmacy'){sharedStock(true);return}editor(tab)};
$('#medicine').addEventListener('click',async e=>{const b=e.target.closest('button');if(!b)return;
 if(b.dataset.medicineTab){tab=b.dataset.medicineTab;$('#medicine-search').value='';draw();return}
 if(b.id==='medicine-manage-stock'){sharedStock();return}
 if(b.id==='medicine-rename'){editor('cabinet',{kind:'cabinet',name:state.cabinet.name,revision:state.cabinet_revision});return}
 const id=b.dataset.medicineEdit||b.dataset.medicineArchive;if(!id)return;const r=state.records.find(r=>r.id===id);if(!r)return;
 if(b.dataset.medicineEdit){editor(r.kind,r);return}
 b.disabled=true;try{await api('records/'+r.id,'PUT',{...r,archived:!r.archived});await load()}catch(err){message(err.message)}finally{b.disabled=false}
});
window.addEventListener('pantry-account-updated',()=>{epoch++;state=null;loading=false;$('#medicine-editor').close();$('#medicine-heading').replaceChildren();$('#medicine-list').replaceChildren();$('#medicine-search').value='';message('');if($('.section.active')?.id==='medicine')load()});
})();
