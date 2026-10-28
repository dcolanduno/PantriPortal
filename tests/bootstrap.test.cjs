const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const source=fs.readFileSync(require('node:path').join(__dirname,'../app/bootstrap.js'),'utf8');
async function load(flag,fail){
 const requests=[],messages=[],version={textContent:'Checking version…'},healthRequests=[];
 const document={
  createElement(tag){return {tag,setAttribute(){}}},
  head:{append(script){requests.push(script.src);Promise.resolve().then(()=>script.src===fail?script.onerror(new Error('offline')):script.onload())}},
  getElementById(id){return id==='app-version'?version:{addEventListener(){},hidden:false}},
  body:{prepend(message){messages.push(message.textContent)}}
 };
 await vm.runInNewContext(source,{window:{PP_RUN_APP:flag,addEventListener(){}},document,navigator:{},matchMedia:()=>({matches:false}),fetch:(...args)=>{healthRequests.push(args);return Promise.resolve({ok:true,json:()=>Promise.resolve({version:'0.15.8',build:'abcdef123456'})})},alert(){}});
 await Promise.resolve();await Promise.resolve();
 return {requests,messages,version,healthRequests};
}
test('an unfinished inventory transfer prevents application initialization',async()=>{
 const result=await load(false);assert.deepEqual(result.requests,[]);assert.deepEqual(result.messages,[]);
});
test('canonical and local pages load dependencies in order',async()=>{
 for(const flag of [true,undefined])assert.deepEqual((await load(flag)).requests,['/mode-data.js','/app.js','/features.js','/modes.js','/admin.js','/home-sections.js','/kitchen.js','/prescription-label.js','/medicine.js','/prescription-scan.js','/medicine-benefits.js','/navigation.js']);
});
test('a failed application asset stops initialization with a recovery message',async()=>{
 const result=await load(true,'/features.js');assert.deepEqual(result.requests,['/mode-data.js','/app.js','/features.js']);
 assert.equal(result.messages.length,1);assert.match(result.messages[0],/saved inventory is preserved/);
});
test('the shared footer displays the server version and deployed build without caching',async()=>{
 const result=await load(false);assert.equal(result.version.textContent,'Version 0.15.8 · Build abcdef123456');
 assert.equal(result.healthRequests.length,1);assert.equal(result.healthRequests[0][0],'/api/health');assert.equal(result.healthRequests[0][1].cache,'no-store');
});
