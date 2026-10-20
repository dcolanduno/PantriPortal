const test=require('node:test'),assert=require('node:assert/strict');
const modes=require('../app/mode-data.js');
test('explicit classification wins; legacy food and household categories remain useful',()=>{
 assert.equal(modes.isFood({is_food:false,name:'Vanilla',category:'Baking'}),false);
 assert.equal(modes.isFood({is_food:true,category:'Other'}),true);
 for(const name of ['Shampoo','Lotion','Perfume','Toilet cleaner'])assert.equal(modes.isFood({name,category:'Other'}),false);
 assert.equal(modes.isFood({name:'Cereal',category:'Grains & pasta'}),true);
 assert.equal(modes.isFood({name:'Dish soap',category:'Cleaning'}),false);
});
test('modes partition records without changing quantities or losing original data',()=>{
 const items=[{id:1,name:'Cereal',is_food:true,qty:3},{id:2,name:'Soap',is_food:false,qty:2},{id:3,name:'Milk',category:'Dairy & eggs',qty:1}];
 const before=JSON.stringify(items),kitchen=modes.filter(items,'kitchen'),home=modes.filter(items,'home');
 assert.deepEqual(kitchen.map(i=>i.id),[1,3]);assert.deepEqual(home.map(i=>i.id),[2]);assert.equal(JSON.stringify(items),before);
});
test('each mode keeps its own defaults and includes existing custom storage locations',()=>{
 const items=[{is_food:false,location:'Hall cupboard'},{is_food:true,location:'Cold pantry'}];
 assert(modes.locations(items,'home').includes('Bathroom'));assert(modes.locations(items,'home').includes('Hall cupboard'));
 assert(!modes.locations(items,'home').includes('Cold pantry'));assert(modes.locations(items,'kitchen').includes('Cold pantry'));
});
