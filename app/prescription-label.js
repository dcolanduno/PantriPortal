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
 // Do not discard a useful label line simply because Tesseract is uncertain.
 // The user sees and verifies the text before any prescription can be saved.
 const good=lines.filter(l=>l.confidence>=20&&l.text&&/[a-z0-9]/i.test(l.text)&&((l.text.match(/[a-z0-9\s.,:;#()/%+\-]/gi)||[]).length/l.text.length)>=.65);
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
function newLines(existing,readings){
 const normalize=line=>line.trim().toLowerCase().replace(/\s+/g,' '),known=new Set(String(existing||'').split('\n').map(normalize).filter(Boolean)),fresh=[];
 for(const line of readings.flatMap(r=>String(r.text||'').split('\n')).map(line=>line.trim()).filter(Boolean)){const key=normalize(line);if(key&&!known.has(key)){known.add(key);fresh.push(line)}}
 return fresh;
}
function consensus(readings,minimumVotes=2,highConfidence=84){
 const normalize=line=>line.trim().toLowerCase().replace(/[^a-z0-9]+/g,' ').trim(),lines=new Map();
 for(const reading of readings){const seen=new Set();for(const text of String(reading.text||'').split('\n').map(line=>line.trim()).filter(Boolean)){const key=normalize(text);if(!key||seen.has(key))continue;seen.add(key);const item=lines.get(key)||{text,votes:0,confidence:0};item.votes++;if((Number(reading.confidence)||0)>item.confidence){item.text=text;item.confidence=Number(reading.confidence)||0}lines.set(key,item)}}
 const good=[...lines.values()].filter(item=>item.votes>=minimumVotes||item.confidence>=highConfidence);
 if(good.length)return {text:good.map(item=>item.text).join('\n'),confidence:good.reduce((sum,item)=>sum+item.confidence,0)/good.length,confirmed:good.every(item=>item.votes>=2)};
 // Preserve the strongest readable one-pass candidate for human correction.
 // A strict consensus gate made all imperfect but useful OCR appear blank.
 const best=[...readings].filter(r=>r.text&&Number(r.confidence)>=70).sort((a,b)=>Number(b.confidence)-Number(a.confidence))[0];
 return best?{text:best.text,confidence:Number(best.confidence)||0,confirmed:false}:{text:'',confidence:0,confirmed:false};
}
function validGtin(value){if(!/^\d{8,14}$/.test(value))return false;let sum=0,weight=3;for(let i=value.length-2;i>=0;i--){sum+=Number(value[i])*weight;weight=weight===3?1:3}return (10-sum%10)%10===Number(value[value.length-1])}
function healthcareNdc(gtin){const upc=gtin.slice(-12);return upc.startsWith('3')&&validGtin(upc)?upc.slice(1,11):''}
function gs1Date(value){if(!/^\d{6}$/.test(value))return '';const yy=Number(value.slice(0,2)),year=yy<=49?2000+yy:1900+yy,month=Number(value.slice(2,4)),day=Number(value.slice(4,6));if(month<1||month>12||day>31)return '';const finalDay=day===0?new Date(Date.UTC(year,month,0)).getUTCDate():day;return date(`${year}-${String(month).padStart(2,'0')}-${String(finalDay).padStart(2,'0')}`)}
function parseBarcode(raw,format=''){
 const original=String(raw||'').slice(0,512),result={raw:original,format:String(format||''),gtin:'',ndc:'',lot:'',serial:'',expires:'',fields:[],standard:false};if(!original)return result;
 let data=original.trim().replace(/^\](?:d2|C1|Q3)/,'');
 const set=(ai,value)=>{if(ai==='01'&&/^\d{14}$/.test(value)&&validGtin(value)){result.gtin=value;result.ndc=healthcareNdc(value);result.standard=true}
  else if(ai==='715'&&/^\d{12}$/.test(value)){result.ndc=value;result.standard=true}
  else if(ai==='17'){result.expires=gs1Date(value)}
  else if(ai==='10'&&value){result.lot=value.slice(0,20)}
  else if(ai==='21'&&value){result.serial=value.slice(0,20)}
  if(result.standard||['01','715','17','10','21'].includes(ai))result.fields.push({ai,value});};
 if(/^https?:\/\/(?:id\.)?gs1\.org\//i.test(data)){
  try{const u=new URL(data);const path=u.pathname.split('/').filter(Boolean);for(let i=0;i+1<path.length;i+=2){const ai=path[i],v=decodeURIComponent(path[i+1]);if(['01','10','17','21','715'].includes(ai))set(ai,v)}for(const [ai,v] of u.searchParams)if(['10','17','21'].includes(ai))set(ai,v)}catch{}return result;
 }
 if(/\(\d{2,4}\)/.test(data)){
  const re=/\((\d{2,4})\)([^()]*)/g;let m;while((m=re.exec(data))){const ai=m[1],value=m[2];if(['01','715'].includes(ai)&&value.length===(ai==='01'?14:12)||['17'].includes(ai)&&value.length===6||['10','21'].includes(ai)&&value.length<=20)set(ai,value)}return result;
 }
 data=data.replace(/[\x1d\x00]/g,'\x1d');let i=0;
 while(i<data.length){if(data[i]==='\x1d'){i++;continue}let ai='';if(data.startsWith('715',i)&&/^\d{12}/.test(data.slice(i+3)))ai='715';else if(['01','17','10','21'].some(x=>data.startsWith(x,i)))ai=['01','17','10','21'].find(x=>data.startsWith(x,i));if(!ai)break;i+=ai.length;const length=ai==='01'?14:ai==='17'?6:null;if(length){const v=data.slice(i,i+length);if(v.length!==length||!/^\d+$/.test(v))break;set(ai,v);i+=length;continue}const end=data.indexOf('\x1d',i),v=data.slice(i,end<0?data.length:end);set(ai,v);i=end<0?data.length:end;
 }
 if(!result.standard&&['UPC_A','EAN_13','EAN_8','UPC_E','UPC-A','EAN-13'].includes(String(format).toUpperCase())){const digits=data.replace(/\D/g,'');if(validGtin(digits)){result.gtin=digits.padStart(14,'0');result.ndc=healthcareNdc(result.gtin);result.standard=true;result.fields.push({ai:'01',value:result.gtin})}}
 return result;
}
return {parse,date,telephone,reading,combine,newLines,consensus,parseBarcode,validGtin};
});
