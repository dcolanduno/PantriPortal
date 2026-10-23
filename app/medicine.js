(function(){
'use strict';
const bridge=window.PantryAdminBridge;
let state=null,epoch=0,tab='prescription',editing=null,loading=false;
let officeObserver=null;
const officeCache=new Map();
const labels={prescription:'Prescriptions',doctor:'Doctors',appointment:'Appointments',pharmacy:'Household pharmacy'};
const fields={
 doctor:[['name','Doctor name','text',true],['specialty','Specialty'],['practice','Practice / clinic'],['phone','Phone','tel'],['email','Email','email'],['address','Address','textarea'],['notes','Notes','textarea']],
 prescription:[['name','Medicine name','text',true],['strength','Strength (as printed on the label)'],['directions','Directions from your prescription label','textarea'],['quantity','Quantity on hand','number'],['unit','Quantity unit (tablets, mL, etc.)'],['refills_remaining','Refills remaining','integer'],['last_filled','Last filled','date'],['next_refill','Next refill date','date'],['expires','Prescription expiration','date'],['bottle_expires','Bottle / medication discard date','date'],['ndc','NDC product code'],['label_prescriber','Prescriber printed on label'],['pharmacy','Pharmacy name'],['pharmacy_phone','Pharmacy phone','tel'],['pharmacy_address','Pharmacy address','textarea'],['rx_number','Prescription number'],['notes','Personal notes','textarea']],
 appointment:[['name','Visit / appointment title','text',true],['starts','Date and time','datetime-local',true],['timezone','Time zone (for example America/New_York)','text',true],['location','Clinic / address / video visit details','textarea',true],['phone','Appointment contact phone','tel'],['notes','Notes / things to bring','textarea']]
};
const style=document.createElement('style');style.textContent=`
.medicine-lookup [role=listbox]{max-height:300px;overflow:auto;border:1px solid #c7c4ce;border-radius:9px;background:white}.medicine-lookup [role=option]{padding:12px;border-bottom:1px solid #ddd;cursor:pointer}.medicine-lookup [role=option]:hover,.medicine-lookup [aria-selected=true]{background:#efe8f7}.medicine-lookup [role=option] span,.medicine-lookup [role=option] small{display:block;font-weight:400;margin-top:4px}#medicine-info select{width:100%;padding:10px;font:inherit;margin:10px 0}.medicine-label-text{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.6}#medicine-info details{padding:12px 0;border-bottom:1px solid #ddd}#medicine-info summary{cursor:pointer;font-weight:600}.medicine-area .mode-banner{display:none}.medicine-banner{border:1px solid #ccc0e4;border-radius:20px;padding:22px;background:linear-gradient(115deg,#f0e8fb,#e6f4f5);margin-bottom:20px}.medicine-banner h2{margin:0;color:#583374}.medicine-banner p{margin:8px 0}.medicine-tabs{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0}.medicine-tabs button[aria-pressed=true]{background:#583374;color:white}.medicine-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,310px),1fr));gap:16px}.medicine-card{border:1px solid var(--line);border-radius:16px;padding:18px;background:var(--white,#fff);overflow-wrap:anywhere}.medicine-card h3{margin:0 0 12px;font-size:22px}.medicine-card dl{display:grid;grid-template-columns:minmax(95px,1fr) minmax(0,2fr);gap:7px;margin:14px 0}.medicine-card dt{font-weight:600}.medicine-card dd{margin:0;white-space:pre-wrap}.medicine-tools{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:14px 0}.medicine-tools input[type=search]{flex:1;min-width:150px}.medicine-dialog{width:min(700px,calc(100vw - 24px));max-height:90vh;border:1px solid var(--line);border-radius:20px;padding:22px;overflow:auto}.medicine-dialog::backdrop{background:#15253680}.medicine-form{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.medicine-form label{display:flex;flex-direction:column;gap:6px;font-weight:600}.medicine-form input,.medicine-form select,.medicine-form textarea{width:100%;min-width:0;padding:11px;border:1px solid #c7c4ce;border-radius:9px;font:inherit}.medicine-form textarea{min-height:88px}.medicine-wide{grid-column:1/-1}.medicine-note{font-size:14px;color:#625e71}.medicine-error{color:#9a273e}.medicine-card .medicine-archived{font-weight:600;color:#625e71}@media(max-width:600px){.medicine-form{grid-template-columns:1fr}.medicine-card dl{grid-template-columns:1fr}.medicine-card dd{margin-bottom:5px}.medicine-dialog{padding:16px}}
`;document.head.append(style);
style.textContent+=`.medicine-office-map{margin:16px 0}.medicine-map-preview{display:block;position:relative;max-width:460px;min-height:185px;border:1px solid var(--line);border-radius:12px;overflow:hidden;background:#edf2ed;color:var(--green);text-decoration:none}.medicine-map-preview:focus-visible{outline:3px solid var(--green);outline-offset:3px}.medicine-map-preview iframe{display:block;width:100%;height:185px;border:0;pointer-events:none}.medicine-map-placeholder{display:flex;min-height:185px;align-items:center;justify-content:center;padding:18px;text-align:center}.medicine-map-caption{display:block;font-size:14px;margin-top:8px}.medicine-map-credit{font-size:12px;margin:7px 0}.medicine-map-actions{display:flex;gap:12px;flex-wrap:wrap;font-size:14px}`;
$('.nav').insertAdjacentHTML('beforeend','<button id="medicine-nav" data-page="medicine">✚ Medicine</button>');
$('.main').insertAdjacentHTML('beforeend',`<section class="section" id="medicine"><div class="medicine-banner"><h2>✚ Medicine & pharmacy</h2><p>Your private medicine cabinet and your household’s everyday pharmacy supplies.</p><p class="medicine-note">Personal prescriptions, doctors and appointments are visible and editable only through your own account. Shared supplies stay in Home inventory.</p></div><div class="panel"><div id="medicine-heading"></div><nav class="medicine-tabs" aria-label="Medicine sections">${Object.entries(labels).map(([key,label])=>`<button type="button" class="secondary" data-medicine-tab="${key}">${label}</button>`).join('')}</nav><div class="medicine-tools"><input type="search" id="medicine-search" aria-label="Search medicine area" placeholder="Search this section"><label><input type="checkbox" id="medicine-archives"> Show archived</label><button class="secondary" id="medicine-reload">Refresh</button><button class="primary" id="medicine-add">Add prescription</button></div><p id="medicine-status" role="status"></p><div id="medicine-list" class="medicine-grid"></div></div></section>`);
document.body.insertAdjacentHTML('beforeend',`<dialog id="medicine-editor" class="medicine-dialog" aria-labelledby="medicine-editor-title"><h2 id="medicine-editor-title"></h2><form id="medicine-form"><div id="medicine-fields" class="medicine-form"></div><p id="medicine-form-error" class="medicine-error" role="alert"></p><div class="medicine-tools"><button type="button" class="secondary" id="medicine-cancel">Cancel</button><button class="primary" type="submit" id="medicine-save">Save</button></div></form></dialog>`);
const oldGoto=goto;goto=function(page){oldGoto(page);document.body.classList.toggle('medicine-area',page==='medicine');if(page==='medicine'){$('#page-title').textContent='Medicine & pharmacy';$('#page-sub').textContent='Personal care records and shared household supplies.'}};
async function api(path='',method='GET',data){const e=epoch,r=await bridge.api('medicine/'+path,method,data);if(e!==epoch)throw new Error('Your account changed. Reopen Medicine.');return r}
function message(s){$('#medicine-status').textContent=s}
function doctor(id){return state?.records.find(r=>r.kind==='doctor'&&r.id===id)}
function detail(label,value){return value===null||value===undefined||value===''?'':`<dt>${esc(label)}</dt><dd>${esc(String(value))}</dd>`}
function officeMapCard(r){
 if(r.kind!=='doctor')return '';
 const address=(r.address||'').trim();
 if(!address)return '<p class="medicine-note">Add an office address to show its map.</p>';
 const query=encodeURIComponent(address),map='https://www.google.com/maps/search/?api=1&query='+query;
 return `<section class="medicine-office-map" data-office-id="${r.id}" aria-label="Office location"><a class="medicine-map-preview" href="${esc(map)}" target="_blank" rel="noopener noreferrer" aria-label="Open office map for ${esc(address)} in a new tab"><span class="medicine-map-placeholder">Loading office map…</span></a><span class="medicine-map-caption">Office location · click the map to open Google Maps</span><div class="medicine-map-actions"><a href="${esc(map)}" target="_blank" rel="noopener noreferrer">Open full map ↗</a><a href="https://www.google.com/maps/dir/?api=1&destination=${query}" target="_blank" rel="noopener noreferrer">Get directions ↗</a></div><p class="medicine-map-credit">Map: © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap contributors</a> · Office address located by U.S. Census. Preview pins are approximate.</p></section>`;
}
function loadOfficeMaps(){
 officeObserver?.disconnect();
 const e=epoch;
 async function loadMap(node){
  officeObserver?.unobserve(node);
  const record=state?.records.find(r=>r.kind==='doctor'&&r.id===node.dataset.officeId);if(!record)return;
  const address=record.address.trim();
  try{
   let map=officeCache.get(address);
   if(!map){map=await api('office-map','POST',{id:record.id});if(e!==epoch)return;officeCache.set(address,map)}
   if(e!==epoch||!node.isConnected)return;
   const preview=node.querySelector('.medicine-map-preview');
   if(!map.available){preview.innerHTML='<span class="medicine-map-placeholder">📍 Open office location<br>Preview unavailable — use the full map or directions.</span>';return}
   const lat=Number(map.latitude),lon=Number(map.longitude);
   if(!Number.isFinite(lat)||!Number.isFinite(lon)||Math.abs(lat)>85||Math.abs(lon)>180)throw new Error('Map unavailable');
   const params=new URLSearchParams({bbox:[Math.max(-180,lon-.009),lat-.006,Math.min(180,lon+.009),lat+.006].join(','),layer:'mapnik',marker:lat+','+lon});
   const frame=document.createElement('iframe');frame.title='Office location map';frame.src='https://www.openstreetmap.org/export/embed.html?'+params;frame.loading='lazy';frame.referrerPolicy='no-referrer';frame.tabIndex=-1;frame.setAttribute('aria-hidden','true');frame.setAttribute('sandbox','allow-scripts allow-same-origin');preview.replaceChildren(frame);
   if(map.matched_address){const note=document.createElement('p');note.className='medicine-note';note.textContent='Mapped address: '+map.matched_address;node.append(note)}
  }catch{if(e===epoch&&node.isConnected)node.querySelector('.medicine-map-preview').innerHTML='<span class="medicine-map-placeholder">📍 Open office location<br>Preview unavailable — use the full map or directions.</span>'}
 }
 if('IntersectionObserver' in window){officeObserver=new IntersectionObserver(entries=>{for(const entry of entries)if(entry.isIntersecting)loadMap(entry.target)},{rootMargin:'0px'});for(const node of $$('#medicine .medicine-office-map'))officeObserver.observe(node)}
 else for(const node of $$('#medicine .medicine-office-map'))loadMap(node);
}
function refillContact(r){
 if(r.kind!=='prescription')return '';
 const phone=window.PantryPrescriptionLabel.telephone(r.pharmacy_phone);
 return `<section><h4>Request a refill</h4>${phone?`<a class="secondary" href="${esc(phone)}">Call pharmacy for refill</a>`:'<p class="medicine-note">Add the pharmacy phone from your bottle to call for refills.</p>'}<p class="medicine-note">Have your prescription number ready. Refills are confirmed by your pharmacy; no request is submitted automatically.</p></section>`;
}
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
  return `<article class="medicine-card"><h3>${esc(r.name)}</h3>${r.archived?'<p class="medicine-archived">Archived</p>':''}<dl>${details}</dl>${officeMapCard(r)}${refillContact(r)}${r.kind==='prescription'?`<div class="medicine-drug-reference"><h4>Drug information</h4><p class="medicine-note">Uses, side effects, warnings, interactions and full product labeling.</p><button type="button" class="secondary" data-medicine-info="${r.id}">Read drug information</button></div>`:''}<div class="medicine-tools"><button type="button" class="secondary" data-medicine-edit="${r.id}">Edit ${r.kind}</button><button type="button" class="secondary" data-medicine-archive="${r.id}">${r.archived?'Restore':'Archive'}</button></div></article>`;
 }).join('')||`<p>No ${esc(labels[tab].toLowerCase())} ${term?'match your search':'yet'}.</p>`;
 if(tab==='pharmacy'){$('#medicine-list').insertAdjacentHTML('beforeend','<div class="medicine-wide"><button type="button" class="secondary" id="medicine-manage-stock">Manage shared stock in Home inventory</button></div>');message('OTC medicines and supplies in the Medicines and first aid Home section appear here. Stock is counted once. Keep personal prescriptions in your private cabinet.')}else message('');
 loadOfficeMaps();
}
async function load(){
 if(!bridge.current()){$('#medicine-heading').innerHTML='<p>Sign in to open your private cabinet.</p>';$('#medicine-list').replaceChildren();message('');return}
 if(loading)return;loading=true;const e=epoch;message('Loading your cabinet…');
 try{const next=await api('state');if(e!==epoch)return;state=next;draw()}catch(err){if(e===epoch)message(err.message)}finally{if(e===epoch)loading=false}
}
async function open(){if(!bridge.current()){bridge.openAccount();return}goto('medicine');await load()}
function editor(kind,r=null){
 stopLookup();editing=r?{...r}:{kind};$('#medicine-form-error').textContent='';$('#medicine-editor-title').textContent=kind==='cabinet'?'Name your medicine cabinet':(r?'Edit ':'Add ')+kind;
 const list=kind==='cabinet'?[['name','Cabinet name','text',true]]:fields[kind];const data=r||{};
 $('#medicine-fields').innerHTML=(['prescription','appointment'].includes(kind)?`<label class="medicine-wide">${kind==='prescription'?'Prescribing doctor':'Doctor'}<select name="doctor_id"><option value="">Not selected</option>${state.records.filter(d=>d.kind==='doctor'&&(!d.archived||d.id===data.doctor_id)).map(d=>`<option value="${d.id}" ${d.id===data.doctor_id?'selected':''}>${esc(d.name)}${d.archived?' (archived)':''}</option>`).join('')}</select><small>Add a doctor in the Doctors section to link their contact details.</small></label>`:'')+list.map(([key,label,type='text',required=false])=>{
  let value=data[key]??'';if(key==='timezone'&&!value)value=Intl.DateTimeFormat().resolvedOptions().timeZone||'UTC';
  const maximum=kind==='cabinet'?100:kind==='doctor'?({name:160,specialty:160,practice:200,phone:80,email:200,address:500,notes:1500}[key]):({name:160,strength:120,directions:1500,unit:60,pharmacy:200,pharmacy_phone:80,pharmacy_address:500,rx_number:120,ndc:20,label_prescriber:160,notes:1500,location:500,phone:80,timezone:100}[key]||100);
  return `<label class="${type==='textarea'?'medicine-wide':''}">${esc(label)}${required?' *':''}${type==='textarea'?`<textarea name="${key}" maxlength="${maximum}" ${required?'required':''}>${esc(value)}</textarea>`:`<input name="${key}" type="${type==='integer'?'number':type}" value="${esc(value)}" maxlength="${maximum}" ${['number','integer'].includes(type)?`min="0" max="1000000" step="${type==='integer'?'1':'any'}"`:''} ${required?'required':''}>`}</label>`;
 }).join('');installSearch(kind,data);$('#medicine-save').disabled=false;$('#medicine-editor').showModal();
}
window.PantryOpenScannedPrescription=async draft=>{
 if(!bridge.current()){bridge.openAccount();return}
 const e=epoch;await open();if(e!==epoch||!state||!bridge.current())return;editor('prescription');
 for(const [key] of fields.prescription){const el=$('#medicine-form').elements.namedItem(key);if(el&&draft[key]!==undefined)el.value=String(draft[key])}
 $('#medicine-editor-title').textContent='Review scanned prescription';
};
$('#medicine-form').onsubmit=async e=>{e.preventDefault();const button=$('#medicine-save');button.disabled=true;const saved=editing;
 try{const d=Object.fromEntries(new FormData(e.target));d.kind=saved.kind;d.archived=saved.archived||false;d.revision=saved.revision||'';
  await api(saved.kind==='cabinet'?'cabinet':saved.id?'records/'+saved.id:'records',saved.kind==='cabinet'||saved.id?'PUT':'POST',d);$('#medicine-editor').close();editing=null;await load();toast('Medicine cabinet saved.');
 }catch(err){$('#medicine-form-error').textContent=err.message}finally{button.disabled=false}};
$('#medicine-cancel').onclick=()=>$('#medicine-editor').close();
$('#medicine-editor').addEventListener('close',()=>{stopLookup();$('#medicine-form').reset();$('#medicine-fields').replaceChildren();editing=null});
$('#medicine-nav').onclick=open;$('#medicine-reload').onclick=load;
$('#medicine-search').oninput=draw;$('#medicine-archives').onchange=draw;
function sharedStock(add=false){document.querySelector('[data-mode="home"]').click();window.PantryActiveHomeSection='medicines-first-aid';activeFilter='All';$('#search').value='';goto('inventory');render();if(add){const location=$('#item-form').elements.location;if(![...location.options].some(o=>o.value==='Medicine cabinet'))location.add(new Option('Medicine cabinet','Medicine cabinet'));openAdd()}}
$('#medicine-add').onclick=()=>{if(!state){bridge.openAccount();return}if(tab==='pharmacy'){sharedStock(true);return}editor(tab)};
$('#medicine').addEventListener('click',async e=>{const b=e.target.closest('button');if(!b)return;
 if(b.dataset.medicineTab){tab=b.dataset.medicineTab;$('#medicine-search').value='';draw();return}
 if(b.id==='medicine-manage-stock'){sharedStock();return}
 if(b.id==='medicine-rename'){editor('cabinet',{kind:'cabinet',name:state.cabinet.name,revision:state.cabinet_revision});return}
 if(b.dataset.medicineInfo){const record=state.records.find(r=>r.id===b.dataset.medicineInfo);if(record)showDrugInfo(record);return}
 const id=b.dataset.medicineEdit||b.dataset.medicineArchive;if(!id)return;const r=state.records.find(r=>r.id===id);if(!r)return;
 if(b.dataset.medicineEdit){editor(r.kind,r);return}
 b.disabled=true;try{await api('records/'+r.id,'PUT',{...r,archived:!r.archived});await load()}catch(err){message(err.message)}finally{b.disabled=false}
});
// Public reference data is requested separately from private cabinet saves.
let lookupSerial=0,lookupTimer=null,infoSerial=0,selectedForms=[];
const input=key=>$('#medicine-form').elements.namedItem(key);
const safeLink=value=>{try{const u=new URL(value);return u.protocol==='https:'?u.href:'#'}catch{return '#'}};
function stopLookup(){clearTimeout(lookupTimer);lookupSerial++;selectedForms=[]}
function installSearch(kind,data){
 if(!['doctor','prescription'].includes(kind))return;
 const name=input('name');name.autocomplete='off';name.setAttribute('role','combobox');name.setAttribute('aria-autocomplete','list');name.setAttribute('aria-expanded','false');name.setAttribute('aria-controls','medicine-suggestions');
 const holder=name.closest('label');holder.classList.add('medicine-wide');
 holder.insertAdjacentHTML('afterend',`<div class="medicine-wide medicine-lookup">${kind==='doctor'?'<label>City, state or ZIP (optional)<input id="medicine-near" maxlength="100" placeholder="Narrow down doctors with the same name"></label>':''}<p class="medicine-note">As you type, ${kind==='doctor'?'the doctor name and optional city/ZIP are sent to the public NIH provider directory and Google Maps if configured':'the medicine name is sent to NIH RxTerms'}. Your account, notes and other prescription details are not sent. Choose a result to fill details; manual entry is always available.</p><div id="medicine-suggestions" role="listbox" aria-label="${kind==='doctor'?'Doctor':'Medication'} suggestions" hidden></div><p id="medicine-lookup-status" class="medicine-note" role="status"></p><div id="medicine-reference-links"></div></div>`);
 let options=[],active=-1;
 if(kind==='prescription'){
  $('#medicine-fields').insertAdjacentHTML('beforeend','<input type="hidden" name="catalog_name"><input type="hidden" name="rxcui"><datalist id="medicine-strengths"></datalist><div class="medicine-wide"><button type="button" class="secondary" id="medicine-editor-info">Read drug information</button><p class="medicine-note">Reference information does not change your prescribed directions. Match the product, strength and route to your label.</p></div>');
  input('catalog_name').value=data.catalog_name||'';input('rxcui').value=data.rxcui||'';input('strength').setAttribute('list','medicine-strengths');
  input('strength').addEventListener('input',()=>{input('ndc').value='';input('rxcui').value=selectedForms.find(f=>f.strength===input('strength').value)?.rxcui||''});
  $('#medicine-editor-info').onclick=()=>showDrugInfo({name:name.value,catalog_name:input('catalog_name').value,rxcui:input('rxcui').value});
 }
 function hide(){const box=$('#medicine-suggestions');if(box){box.hidden=true;name.setAttribute('aria-expanded','false');name.removeAttribute('aria-activedescendant')}active=-1}
 function choose(index){
  const r=options[index];if(!r)return;clearTimeout(lookupTimer);lookupSerial++;name.value=r.name;
  if(kind==='doctor'){
   // Fill only explicitly selected public details. Keep unrelated user notes intact.
   for(const key of ['specialty','practice','phone','address','email'])input(key).value=r[key]||'';
   $('#medicine-lookup-status').textContent='Contact details filled from '+r.source+'. Check the office and phone before saving.';
   $('#medicine-reference-links').innerHTML=`<a href="${esc(safeLink(r.source_url))}" target="_blank" rel="noopener noreferrer">View source: ${esc(r.source)}</a>`;
  }else{
   input('ndc').value='';selectedForms=r.forms||[];input('catalog_name').value=r.name;input('rxcui').value='';
   // A catalog option is not a prescription: users choose the strength printed on their label.
   $('#medicine-strengths').innerHTML=selectedForms.map(f=>`<option value="${esc(f.strength)}"></option>`).join('');
   input('rxcui').value=selectedForms.find(f=>f.strength===input('strength').value)?.rxcui||'';
   $('#medicine-lookup-status').textContent='Medicine selected from NIH RxTerms. Choose or enter the strength from your prescription label.';
  }
  hide();(kind==='prescription'?input('strength'):name).focus();
 }
 function schedule(){
  clearTimeout(lookupTimer);const serial=++lookupSerial,e=epoch,term=name.value.trim();hide();options=[];$('#medicine-reference-links').replaceChildren();
  if(kind==='prescription'){input('ndc').value='';input('catalog_name').value='';input('rxcui').value='';selectedForms=[];$('#medicine-strengths').replaceChildren()}
  const status=$('#medicine-lookup-status');status.textContent=term.length<3?'Type at least three characters for suggestions.':'Searching…';
  if(term.length<3)return;
  lookupTimer=setTimeout(async()=>{
   try{
    const r=await api('search/'+(kind==='doctor'?'doctors':'drugs'),'POST',{term,near:kind==='doctor'?$('#medicine-near').value.trim():''});
    if(serial!==lookupSerial||e!==epoch||!$('#medicine-editor').open)return;
    options=r.results||[];active=-1;const box=$('#medicine-suggestions');
    box.innerHTML=options.map((r,i)=>`<div role="option" aria-selected="false" id="medicine-option-${i}" data-option="${i}"><strong>${esc(r.name)}</strong><span>${esc(kind==='doctor'?[r.specialty,r.address,r.phone].filter(Boolean).join(' · '):(r.forms||[]).slice(0,5).map(f=>f.strength).join(' · '))}</span><small>${esc(r.source)} ${esc((r.attributions||[]).join(', '))}</small></div>`).join('');
    box.hidden=!options.length;name.setAttribute('aria-expanded',String(options.length>0));
    status.textContent=(options.length?`${options.length} suggestions. Use arrow keys and Enter, or select a result.`:'No matches. Try another spelling, add a city for a doctor, or enter details manually.')+' '+(r.warnings||[]).join(' ');
    if(kind==='doctor'){
     const query=encodeURIComponent(term+' doctor '+$('#medicine-near').value.trim());
     $('#medicine-reference-links').innerHTML=`<a href="https://www.google.com/maps/search/?api=1&query=${query}" target="_blank" rel="noopener noreferrer">Search Google Maps</a> · <a href="https://www.bing.com/search?q=${query}" target="_blank" rel="noopener noreferrer">Search Bing</a>${r.google_enabled?'':'<p class="medicine-note">Automatic contact results use the provider registry. Google Maps autofill requires the site’s Places API configuration.</p>'}`;
    }
   }catch(err){if(serial===lookupSerial&&e===epoch&&$('#medicine-editor').open)status.textContent=err.message+' You can enter details manually.'}
  },350);
 }
 name.addEventListener('input',schedule);$('#medicine-near')?.addEventListener('input',schedule);
 $('#medicine-suggestions').addEventListener('mousedown',e=>{if(e.target.closest('[data-option]'))e.preventDefault()});
 $('#medicine-suggestions').addEventListener('click',e=>{const r=e.target.closest('[data-option]');if(r)choose(Number(r.dataset.option))});
 name.addEventListener('keydown',e=>{
  if(e.key==='Escape'&&!$('#medicine-suggestions').hidden){e.preventDefault();e.stopPropagation();hide();return}
  if($('#medicine-suggestions').hidden||!options.length)return;
  if(['ArrowDown','ArrowUp'].includes(e.key)){
   e.preventDefault();active=(active+(e.key==='ArrowDown'?1:-1)+options.length)%options.length;
   for(const row of $$('#medicine-suggestions [role=option]'))row.setAttribute('aria-selected',String(Number(row.dataset.option)===active));
   name.setAttribute('aria-activedescendant','medicine-option-'+active);$('#medicine-option-'+active).scrollIntoView({block:'nearest'});
  }else if(e.key==='Enter'&&active>=0){e.preventDefault();choose(active)}else if(e.key==='Tab')hide();
 });
}
document.body.insertAdjacentHTML('beforeend',`<dialog id="medicine-info" class="medicine-dialog" aria-labelledby="medicine-info-title"><h2 id="medicine-info-title">Drug information</h2><p class="medicine-note">Product-label reference only. It may not cover every use or side effect, including off-label uses. Follow your prescription and ask your pharmacist or clinician about your care. No personalized dosing or interaction assessment is provided.</p><div id="medicine-info-body"></div><button type="button" class="secondary" id="medicine-info-close">Close drug information</button></dialog>`);
$('#medicine-info-close').onclick=()=>$('#medicine-info').close();
$('#medicine-info').addEventListener('close',()=>{infoSerial++;$('#medicine-info-body').replaceChildren()});
async function showDrugInfo(record){
 const e=epoch,serial=++infoSerial,body=$('#medicine-info-body');$('#medicine-info-title').textContent='About '+record.name;body.textContent='Finding product labels…';$('#medicine-info').showModal();
 try{
  const result=await api('drug-labels','POST',{name:record.catalog_name||record.name,rxcui:record.rxcui||''});
  if(serial!==infoSerial||e!==epoch)return;
  const options=result.results||[];
  body.innerHTML=`<p>Choose the label that matches your medicine’s manufacturer, route and product code (NDC). Different products can have different labeling. ${record.rxcui?'Search uses your selected RxNorm strength identifier.':'Search uses the name only; verify the formulation and strength in the full label.'}</p>${options.length?`<label>Matching product labels<select id="medicine-label-choice"><option value="">Select a product label…</option>${options.map((r,i)=>`<option value="${i}">${esc([...(r.brand||[]),...(r.generic||[]),...(r.manufacturer||[]),...(r.route||[]),'NDC '+(r.product_ndc||[]).join(', '),'Label '+r.effective_time].join(' · '))}</option>`).join('')}</select></label>`:'<p>No matching product label was returned. This does not mean the medicine has no risks or uses.</p>'}<p><a target="_blank" rel="noopener noreferrer" href="https://dailymed.nlm.nih.gov/dailymed/search.cfm?query=${encodeURIComponent(record.name)}">Search DailyMed for the complete label</a></p><div id="medicine-label-detail" aria-live="polite"></div>`;
  const select=$('#medicine-label-choice');if(!select)return;
  select.onchange=async()=>{
   const detail=$('#medicine-label-detail'),chosen=options[select.value],request=++infoSerial;detail.replaceChildren();if(!chosen)return;detail.textContent='Loading label…';
   try{
    const r=await api('drug-label','POST',{id:chosen.id});if(request!==infoSerial||e!==epoch)return;
    if(!r.label){detail.textContent='This label is unavailable. Use the DailyMed link or try another product.';return}
    const l=r.label;detail.innerHTML=`<p><strong>${esc(l.source)}</strong> · Label effective date: ${esc(l.effective_time||'Not provided')}</p><p><a href="${esc(safeLink(l.source_url))}" target="_blank" rel="noopener noreferrer">Read complete source label on DailyMed</a></p>${l.sections.map(s=>`<details ${s.key==='boxed_warning'?'open':''}><summary>${esc(s.title)}</summary><p class="medicine-label-text">${esc(s.text)}</p></details>`).join('')}<p class="medicine-note">A missing section means it was not returned by this label source; it does not establish that a risk is absent. Reference dosage never replaces your prescription directions.</p>`;
   }catch(err){if(request===infoSerial&&e===epoch)detail.textContent=err.message}
  };
 }catch(err){if(serial===infoSerial&&e===epoch)body.innerHTML=`<p>${esc(err.message)}</p><p><a target="_blank" rel="noopener noreferrer" href="https://dailymed.nlm.nih.gov/dailymed/search.cfm?query=${encodeURIComponent(record.name)}">Search DailyMed for the complete label</a></p>`}
}

window.addEventListener('pantry-account-updated',()=>{epoch++;officeObserver?.disconnect();officeCache.clear();stopLookup();infoSerial++;$('#medicine-info').close();state=null;loading=false;$('#medicine-editor').close();$('#medicine-heading').replaceChildren();$('#medicine-list').replaceChildren();$('#medicine-search').value='';message('');if($('.section.active')?.id==='medicine')load()});
})();
