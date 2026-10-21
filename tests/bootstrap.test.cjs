const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const source=fs.readFileSync(require('node:path').join(__dirname,'../app/bootstrap.js'),'utf8');
async function load(flag,fail){
 const requests=[],messages=[];
 const document={
  createElement(tag){return {tag,setAttribute(){}}},
  head:{append(script){requests.push(script.src);Promise.resolve().then(()=>script.src===fail?script.onerror(new Error('offline')):script.onload())}},
  getElementById(){return {addEventListener(){},hidden:false}},
  body:{prepend(message){messages.push(message.textContent)}}
 };
 await vm.runInNewContext(source,{window:{PP_RUN_APP:flag,addEventListener(){}},document,navigator:{},matchMedia:()=>({matches:false}),alert(){}});
 return {requests,messages};
}
test('an unfinished inventory transfer prevents application initialization',async()=>{
 const result=await load(false);assert.deepEqual(result.requests,[]);assert.deepEqual(result.messages,[]);
});
test('canonical and local pages load dependencies in order',async()=>{
 for(const flag of [true,undefined])assert.deepEqual((await load(flag)).requests,['/mode-data.js','/app.js','/features.js','/modes.js','/admin.js','/home-sections.js','/kitchen.js','/medicine.js','/navigation.js']);
});
test('a failed application asset stops initialization with a recovery message',async()=>{
 const result=await load(true,'/features.js');assert.deepEqual(result.requests,['/mode-data.js','/app.js','/features.js']);
 assert.equal(result.messages.length,1);assert.match(result.messages[0],/saved inventory is preserved/);
});
