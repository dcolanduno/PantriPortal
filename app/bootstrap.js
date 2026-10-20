// Keep the old-address transfer page in control until inventory reaches the canonical site.
(async function(){
 'use strict';
 if(window.PP_RUN_APP===false)return;
 for(const name of ['mode-data.js','app.js','features.js','modes.js','admin.js','home-sections.js','kitchen.js','navigation.js']){
  await new Promise((resolve,reject)=>{
   const script=document.createElement('script');
   script.src='/'+name;script.onload=resolve;script.onerror=reject;
   document.head.append(script);
  });
 }
 if('serviceWorker' in navigator)navigator.serviceWorker.register('/sw.js',{scope:'/'}).catch(()=>{});
 const installButton=document.getElementById('install-app');
 let installPrompt=null;
 const standalone=()=>matchMedia('(display-mode: standalone)').matches||navigator.standalone===true;
 const appleMobile=/iPhone|iPad|iPod/.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
 if(standalone())installButton.hidden=true;
 window.addEventListener('beforeinstallprompt',event=>{event.preventDefault();installPrompt=event});
 window.addEventListener('appinstalled',()=>{installPrompt=null;installButton.hidden=true});
 installButton.addEventListener('click',async()=>{
  if(installPrompt){installPrompt.prompt();await installPrompt.userChoice;installPrompt=null;return}
  alert(appleMobile?'To install PantriPortal on your iPhone or iPad, open this page in Safari, tap Share, then choose “Add to Home Screen”.':'To install PantriPortal, use your browser menu and choose “Install app” or “Add to Home screen”.');
 });
})().catch(()=>{
 const message=document.createElement('p');
 message.setAttribute('role','alert');
 message.textContent='The page could not finish loading. Please refresh to try again. Your saved inventory is preserved.';
 document.body.prepend(message);
});
