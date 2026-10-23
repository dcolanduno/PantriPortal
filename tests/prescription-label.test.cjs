const test=require('node:test'),assert=require('node:assert/strict');
const {parse,date,telephone}=require('../app/prescription-label.js');
test('reads explicit prescription details without turning discard dates into Rx expiration',()=>{
 const r=parse(`EXAMPLE PHARMACY
123 Example Street
Example, NY 10001
Phone: (212)555-0100
RX# 001234-56
PATIENT: SAMPLE PERSON
MEDICINE: LISINOPRIL 10 MG
TAKE 1 TABLET BY MOUTH DAILY
QTY: 30 TABLETS
REFILLS: 2
FILLED: 10/20/2026
REFILL AFTER: 11/20/2026
DISCARD AFTER: 10/20/2027
Prescriber: Dr Example
NDC: 0002-8215-01`);
 assert.equal(r.name,'LISINOPRIL');assert.equal(r.strength,'10 MG');assert.equal(r.rx_number,'001234-56');assert.equal(r.directions,'TAKE 1 TABLET BY MOUTH DAILY');assert.equal(r.quantity,'30');assert.equal(r.refills_remaining,'2');assert.equal(r.pharmacy_phone,'(212)555-0100');assert.equal(r.last_filled,'2026-10-20');assert.equal(r.next_refill,'2026-11-20');assert.equal(r.bottle_expires,'2027-10-20');assert.equal(r.expires,undefined);assert.equal(r.label_prescriber,'Dr Example');assert.equal(r.ndc,'0002-8215-01');
});
test('does not invent identity or contact data from patient names and unknown barcodes',()=>{
 const r=parse('Patient: SAMPLE PERSON\nDoctor: Example 20 MG\nDoctor Phone: 212-555-0101\nhttps://example.invalid/1234567890\n1234567890');
 assert.equal(r.name,undefined);assert.equal(r.pharmacy_phone,undefined);assert.equal(r.ndc,undefined);assert.equal(r.rx_number,undefined);
});
test('preserves no-refill and separately labelled dates; rejects ambiguous year and impossible dates',()=>{
 assert.equal(parse('NO REFILLS').refills_remaining,'0');assert.equal(parse('RX EXPIRES: 01/02/2027').expires,'2027-01-02');
 assert.equal(date('2/29/2026'),'');assert.equal(date('2/29/2028'),'2028-02-29');assert.equal(date('10/20/26'),'');assert.equal(parse('Filled: 10/20/26').last_filled,undefined);
});
test('contact links only accept telephone values and preserve extensions',()=>{
 assert.equal(telephone('(212) 555-0100 ext 2'),'tel:2125550100;ext=2');assert.equal(telephone('+1 212 555 0100'),'tel:+12125550100');assert.equal(telephone('javascript:alert(1)'), '');assert.equal(telephone('https://example.invalid/2125550100'),'');assert.equal(telephone('123'),'');
});
test('keeps multiline directions as printed without calculating dosing or quantities',()=>{
 const r=parse('ALBUTEROL 90 MCG\nInhale 2 puffs\nevery 6 hours as needed\nRefills: 0\nRx# 000999');assert.equal(r.directions,'Inhale 2 puffs every 6 hours as needed');assert.equal(r.refills_remaining,'0');assert.equal(r.quantity,undefined);
});

test('refill-call contact is distinct from doctor contact and use-by is not a direction',()=>{
 const r=parse('Phone: 212-555-0101\nEXAMPLE PHARMACY\nFor refills call: 212-555-0102\nUSE BY: 10/20/2027');
 assert.equal(r.pharmacy_phone,'212-555-0102');assert.equal(r.directions,undefined);assert.equal(r.bottle_expires,'2027-10-20');
});
