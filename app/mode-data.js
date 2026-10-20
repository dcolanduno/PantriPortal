(function(root){
 'use strict';
 const definitions={
  kitchen:{label:'Kitchen',locations:['Pantry','Refrigerator','Freezer','Other']},
  home:{label:'Home inventory',locations:['Bathroom','Closet','Medicine cabinet','Utility closet','Laundry room','Garage','Workshop','Other']}
 };
 function isFood(item){
  if(typeof item.is_food==='boolean')return item.is_food;
  const category=String(item.category||'').toLowerCase();
  if(item.home_section)return false;
  if(/cleaning|personal care|bathroom|fragrance|laundry|household|tools|electronics|furniture|valuables|clothing|closet|hardware|medicines|first aid|shoes/.test(category))return false;
  if(/produce|dairy|eggs|grains|pasta|canned|snacks|baking|beverages|frozen|meat|seafood/.test(category))return true;
  return !/\b(soap|shampoo|lotion|perfume|toilet cleaner|detergent|toothpaste|deodorant)\b/i.test(item.name||'');
 }
 function filter(items,mode){return items.filter(item=>isFood(item)===(mode!=='home'))}
 function locations(items,mode){const key=mode==='home'?'home':'kitchen',custom=(root.PantryCustomLocations||[]).filter(x=>x.mode===key).map(x=>x.name);return [...new Set([...definitions[key].locations,...custom,...filter(items,mode).map(i=>i.location).filter(Boolean)])]}
 function homeSection(item){
  if(item.home_section)return item.home_section;
  const text=String(item.category||'')+' '+String(item.name||'');
  if(/clothing|closet|shirt|trouser|pants|shoes|jacket|sweater|dress|coat|socks/i.test(text))return 'clothing-closet';
  if(/tools|hardware|screws|nails|fastener|glue|tape|hammer|wrench|drill/i.test(text))return 'tools-hardware';
  if(/medicine|medication|first aid|bandage|aspirin|ibuprofen/i.test(text))return 'medicines-first-aid';
  if(/cleaning|laundry|detergent|toilet cleaner|paper towel|household supplies/i.test(text))return 'cleaning-supplies';
  if(/personal|bathroom|fragrance|soap|shampoo|lotion|perfume|toothpaste/i.test(text))return 'personal-care';
  return 'other-home';
 }
 const api={definitions,isFood,filter,locations,homeSection};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;
 else root.PantryModes=api;
})(typeof globalThis!=='undefined'?globalThis:this);
