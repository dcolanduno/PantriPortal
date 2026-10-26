(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.PantryPrescriptionLabel=api})(typeof window!=='undefined'?window:this,function(){
'use strict';
function date(value){
 const s=String(value||'').trim();let y,m,d;let match=s.match(/^(\d{4})-(\d{2})-(\d{2})$/);
 if(match)[,y,m,d]=match;else{match=s.match(/^(\d{1,2})[\/-](\d{1,2})[\/-](\d{4})$/);if(!match)return '';[,m,d,y]=match}
 const dt=new Date(Date.UTC(+y,+m-1,+d));return dt.getUTCFullYear()===+y&&dt.getUTCMonth()===+m-1&&dt.getUTCDate()===+d?[y,String(m).padStart(2,'0'),String(d).padStart(2,'0')].join('-'):'';
}
function parse(value){
 const lines=String(value||'').slice(0,16000).split(/\r?\n/).map(s=>s.replace(/[\t ]+/g,' ').trim()).filter(Boolean),fields={};
 const find=pattern=>{for(const line of lines){const m=line.match(pattern);if(m)return m}return null};
 let m=find(/\bNDC\s*(?:#|NO\.?|NUMBER)?\s*[:#-]?\s*((?:\d{4,6}-\d{3,4}-\d{1,2})|\d{10,12})\b/i);if(m)fields.ndc=m[1];
 m=find(/^\s*(?:RX|PRESCRIPTION)\s*(?:#|NO\.?|NUMBER|:)\s*[:#]?\s*([A-Z0-9-]{3,120})\b/i);if(m)fields.rx_number=m[1];
 m=find(/^\s*(?:DRUG|MEDICATION|MEDICINE)\s*:\s*(.{2,160})$/i);
 let drug=m?m[1]:lines.find(s=>!/^(?:WARNING|CAUTION|PATIENT|PRESCRIBER|DOCTOR|DR\.?\s|PHARMACY|RX\b|TAKE\b|USE\b|APPLY\b|INJECT\b|INHALE\b|INSTILL\b|DISSOLVE\b|CHEW\b)/i.test(s)&&/^[A-Z][A-Z /()-]{2,100}\s+\d+(?:\.\d+)?\s*(?:MCG|MG|G|ML|UNITS?|%)/i.test(s));
 if(drug){const strength=drug.match(/\b\d+(?:\.\d+)?\s*(?:MCG|MG|G|ML|UNITS?|%)(?:\s*\/\s*(?:\d+(?:\.\d+)?\s*)?(?:MCG|MG|G|ML|UNITS?|%))?/i);if(strength){fields.strength=strength[0];fields.name=drug.slice(0,strength.index).trim()||drug}else fields.name=drug}
 m=find(/\b(?:QTY|QUANTITY|DISPENSED)\s*[:#]?\s*(\d+(?:\.\d+)?)(?:\s+(TABLETS?|CAPSULES?|ML|GRAMS?|G|PATCHES?|BOTTLES?))?\b/i);if(m){fields.quantity=m[1];if(m[2])fields.unit=m[2].toLowerCase()}
 m=find(/\b(?:REFILLS?\s*(?:REMAINING|LEFT)?\s*[:#]?\s*(\d{1,3})\b|(\d{1,3})\s+REFILLS?\s+(?:REMAINING|LEFT)\b)/i);if(m)fields.refills_remaining=m[1]||m[2];else if(find(/\b(?:NO REFILLS?|REFILLS?\s*[:#]\s*NONE)\b/i))fields.refills_remaining='0';
 for(const [key,pattern] of [['last_filled',/^(?:DATE\s+FILLED|FILLED|FILL DATE)\s*[:#]?\s*(\d{4}-\d{2}-\d{2}|\d{1,2}[\/-]\d{1,2}[\/-]\d{4})\b/i],['next_refill',/^(?:NEXT REFILL(?: DATE)?|REFILL (?:AFTER|ON))\s*[:#]?\s*(\d{4}-\d{2}-\d{2}|\d{1,2}[\/-]\d{1,2}[\/-]\d{4})\b/i],['bottle_expires',/^(?:DISCARD AFTER|USE BY|BOTTLE EXPIRES)\s*[:#]?\s*(\d{4}-\d{2}-\d{2}|\d{1,2}[\/-]\d{1,2}[\/-]\d{4})\b/i],['expires',/^(?:RX EXPIRES|PRESCRIPTION EXPIRES)\s*[:#]?\s*(\d{4}-\d{2}-\d{2}|\d{1,2}[\/-]\d{1,2}[\/-]\d{4})\b/i]]){m=find(pattern);if(m&&date(m[1]))fields[key]=date(m[1])}
 m=find(/^(?:PRESCRIBER|DOCTOR|PHYSICIAN|DR\.?)(?!\s*[:#]?\s*(?:PHONE|TEL|FAX)\b)\s*[:#]?\s+(.{2,160})$/i);if(m)fields.label_prescriber=m[1];
 let pharmacyIndex=lines.findIndex(s=>/^PHARMACY\s*:/i.test(s)||(/\bPHARMACY\b/i.test(s)&&!/(?:CALL|ASK|CONTACT|REFILL|PHONE|TEL\b|FAX)/i.test(s)));
 if(pharmacyIndex>=0){fields.pharmacy=lines[pharmacyIndex].replace(/^PHARMACY\s*:\s*/i,'').slice(0,200);const following=lines.slice(pharmacyIndex+1,pharmacyIndex+4);if(/^\d+\s+[A-Z]/i.test(following[0]||''))fields.pharmacy_address=following.slice(0,/\b[A-Z]{2}\s+\d{5}/.test(following[1]||'')?2:1).join(', ').slice(0,500)}
 for(let i=0;i<lines.length;i++){
  const line=lines[i];if(/FAX|PRESCRIBER|DOCTOR|PHYSICIAN/i.test(line))continue;
  if(/\b(?:PHARMACY|REFILLS?)\b.*\b(?:CALL|PHONE|TEL)\b|\bCALL\b.*\b(?:PHARMACY|REFILLS?)\b/i.test(line)||/(?:PHARMACY|REFILL)\s*(?:PHONE|TEL)?\s*[:#]/i.test(line)||((pharmacyIndex>=0&&i>=pharmacyIndex&&i<=pharmacyIndex+5)&&/\b(?:PHONE|TEL|PH)\s*[:.]/i.test(line))){const phone=line.match(/(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]?\d{3}[ .-]?\d{4}(?:\s*(?:ext\.?|x)\s*\d{1,6})?/i);if(phone){fields.pharmacy_phone=phone[0];break}}
 }
 let start=lines.findIndex(s=>/^DIRECTIONS\s*:/i.test(s)||(!/^USE BY\b/i.test(s)&&/^(?:TAKE|APPLY|INHALE|INSTILL|INJECT|USE|PLACE|DISSOLVE|CHEW)\s/i.test(s)));
 if(start>=0){let text=lines[start].replace(/^DIRECTIONS\s*:\s*/i,'');for(let i=start+1;i<Math.min(lines.length,start+3);i++){if(/^(?:QTY|QUANTITY|REFILL|FILLED|DISCARD|RX|NDC|PATIENT|PRESCRIBER|DOCTOR|PHARMACY|WARNING|CAUTION|STORE|KEEP)\b/i.test(lines[i]))break;if(/^[a-z]/.test(lines[i])||/^(?:WITH|BY|FOR|AS|DAILY|EVERY|AT|BEFORE|AFTER|TIMES|MOUTH|NEEDED)\b/i.test(lines[i]))text+=' '+lines[i];else break}if(text)fields.directions=text.slice(0,1500)}
 return fields;
}
function telephone(value){const m=String(value||'').match(/^\s*(\+?[\d() .-]{7,30})(?:\s*(?:ext\.?|x|#)\s*(\d{1,6}))?\s*$/i);if(!m)return '';const digits=m[1].replace(/\D/g,'');if(digits.length<7||digits.length>15)return '';return 'tel:'+(m[1].trim().startsWith('+')?'+':'')+digits+(m[2]?';ext='+m[2]:'')}
// Keep useful lines even when bottle edges lower the whole-image confidence.
function reading(data){
 const groups=new Map();
 for(const row of String(data.tsv||'').split(/\r?\n/).slice(1)){
  const c=row.split('\t');if(c[0]!=='5'||c.length<12)continue;
  const confidence=Number(c[10]),text=c.slice(11).join(' ').trim();if(!text||!Number.isFinite(confidence)||confidence<0)continue;
  const k=c.slice(1,5).join(':');if(!groups.has(k))groups.set(k,[]);groups.get(k).push({text,confidence});
 }
 const lines=[...groups.values()].map(words=>({text:words.map(w=>w.text).join(' '),confidence:words.reduce((s,w)=>s+w.confidence,0)/words.length}));
 if(!lines.length)for(const line of data.lines||[])lines.push({text:line.text,confidence:Number(line.confidence)});
 if(!lines.length)lines.push(...String(data.text||'').split(/\r?\n/).map(text=>({text,confidence:Number(data.confidence)||0})));
 const good=lines.filter(l=>l.confidence>=55&&l.text&&/[a-z0-9]/i.test(l.text)&&((l.text.match(/[a-z0-9\s.,:;#()/%+\-]/gi)||[]).length/l.text.length)>=.85);
 return {text:good.map(l=>l.text.trim()).join('\n'),confidence:good.length?good.reduce((s,l)=>s+l.confidence,0)/good.length:0};
}
function combine(readings){
 const ranked=readings.map(r=>({...r,fields:parse(r.text)})).sort((a,b)=>b.confidence-a.confidence),fields={},conflicts=new Set(),seen=new Set(),lines=[];
 for(const r of ranked){
  for(const [key,value] of Object.entries(r.fields)){if(fields[key]===undefined)fields[key]=value;else if(String(fields[key]).toLowerCase().replace(/\s+/g,'')!==String(value).toLowerCase().replace(/\s+/g,''))conflicts.add(key)}
  for(const line of r.text.split('\n')){const k=line.trim().toLowerCase().replace(/\s+/g,' ');if(k&&!seen.has(k)){seen.add(k);lines.push(line)}}
 }
 return {fields,conflicts:[...conflicts],text:lines.join('\n').slice(0,16000)};
}
return {parse,date,telephone,reading,combine};
});
