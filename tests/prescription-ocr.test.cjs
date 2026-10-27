const test=require('node:test'),assert=require('node:assert/strict');
const {reading,combine}=require('../app/prescription-label.js');
test('keeps readable OCR lines when curved edges lower whole-image confidence',()=>{
 const tsv='level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n5\t1\t1\t1\t1\t1\t0\t0\t10\t10\t96\tLISINOPRIL\n5\t1\t1\t1\t1\t2\t0\t0\t10\t10\t90\t10 MG\n5\t1\t1\t1\t2\t1\t0\t0\t10\t10\t12\t@@@?!!';
 const r=reading({tsv,confidence:20});assert.equal(r.text,'LISINOPRIL 10 MG');assert.equal(combine([r]).fields.name,'LISINOPRIL');assert.ok(!r.text.includes('@'));
});
test('combines different bottle faces and reports conflicting dose readings',()=>{
 const r=combine([{text:'LISINOPRIL 10 MG\nTAKE 1 TABLET DAILY\nQTY 30 TABLETS',confidence:90},{text:'RX# 001234\nREFILLS 2\nPrescriber: Dr Example\nPharmacy: Example Pharmacy\nPharmacy phone: 212-555-0100',confidence:85},{text:'LISINOPRIL 70 MG',confidence:60}]);
 assert.equal(r.fields.strength,'10 MG');assert.equal(r.fields.quantity,'30');assert.equal(r.fields.rx_number,'001234');assert.equal(r.fields.pharmacy_phone,'212-555-0100');assert.equal(r.fields.label_prescriber,'Dr Example');assert.ok(r.conflicts.includes('strength'));
});
test('does not invent missing fields from unreadable text',()=>{const r=reading({text:'@@!?|~\nerr 003',confidence:15});assert.equal(r.text,'');assert.deepEqual(combine([r]).fields,{});});

test('continuous camera frames add only newly visible label lines',()=>{
 const prior='LISINOPRIL 10 MG\nTAKE ONE TABLET DAILY',again=[{text:'lisinopril 10 mg\nTAKE ONE TABLET DAILY'},{text:'QTY 30\nPharmacy Example'}];
 assert.deepEqual(require('../app/prescription-label.js').newLines(prior,again),['QTY 30','Pharmacy Example']);
 assert.deepEqual(require('../app/prescription-label.js').newLines(prior,[{text:'LISINOPRIL 10 MG'}]),[]);
});

test('scanner keeps lines confirmed by OCR passes and drops low-confidence one-off noise',()=>{
 const {consensus}=require('../app/prescription-label.js'),r=consensus([{text:'LISINOPRIL 10 MG\n@@@',confidence:65},{text:'LISINOPRIL 10 MG\nTAKE ONE TABLET DAILY',confidence:72},{text:'LISINOPRIL 10 MG',confidence:68}]);
 assert.equal(r.text,'LISINOPRIL 10 MG');
 assert.equal(consensus([{text:'random glyphs !??',confidence:61}]).text,'');
 assert.equal(consensus([{text:'RX 001234',confidence:90}]).text,'RX 001234');
});

test('keeps low-confidence label words so independent image passes can recover them',()=>{
 const {reading,consensus}=require('../app/prescription-label.js'),tsv='level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n5\t1\t1\t1\t1\t1\t0\t0\t10\t10\t37\tAMOXICILLIN\n5\t1\t1\t1\t1\t2\t0\t0\t10\t10\t42\t500 MG';
 const first=reading({tsv,confidence:20});assert.equal(first.text,'AMOXICILLIN 500 MG');
 const second={text:'AMOXICILLIN 500 MG',confidence:44};assert.equal(consensus([first,second]).text,'AMOXICILLIN 500 MG');
});

test('falls back to the strongest readable OCR pass when strict consensus would hide it',()=>{
 const {consensus}=require('../app/prescription-label.js'),r=consensus([{text:'AMOXICILLIN 500 MG',confidence:73},{text:'AMOXICILIN 500 MG',confidence:56}]);
 assert.equal(r.text,'AMOXICILLIN 500 MG');assert.equal(r.confirmed,false);
});

test('doctor contact labels are not prescriber names',()=>{const {parse}=require('../app/prescription-label.js');assert.equal(parse('Doctor Phone: 212-555-0101').label_prescriber,undefined);assert.equal(parse('Dr Example').label_prescriber,'Example');});
