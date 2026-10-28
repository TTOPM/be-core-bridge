import { test } from 'node:test';
import assert from 'node:assert/strict';
import { BelelAcousticNetwork } from '../../src/lib/belel-acoustic-network/network.ts';
import { BelelAcousticBus } from '../../src/lib/belel-acoustic-network/bus.ts';
import { BelelWakeIntelligence } from '../../src/lib/belel-acoustic-network/wake.ts';
import { BelelPronunciationCortex } from '../../src/lib/belel-acoustic-network/pronunciation.ts';
import { BelelDuplexConductor } from '../../src/lib/belel-acoustic-network/duplex.ts';
import { BelelModelRegistry } from '../../src/lib/belel-acoustic-network/modelRegistry.ts';

test('defaults to passive observe; no audio or model access', () => {
  const net = new BelelAcousticNetwork();
  assert.equal(net.settings.mode,'observe');
  assert.equal(net.canUseModel(),false);
  assert.equal(net.canSendAudio(),false);
  net.shutdown();
});
test('observes but does not control legacy Belel events', () => {
  const target = new EventTarget(); const net=new BelelAcousticNetwork();
  const detach=net.attachToExistingEvents(target);
  target.dispatchEvent(new Event('belel:tts:start'));
  assert.equal(net.bus.recent()[0].type,'tts.started');
  detach(); target.dispatchEvent(new Event('belel:tts:end'));
  assert.equal(net.bus.recent().length,1);
});
test('rejects raw audio from its telemetry fabric',()=>{
  const bus=new BelelAcousticBus();
  assert.throws(()=>bus.publish('network.health','bain.test',{pcm:new Float32Array(2)}));
  assert.throws(()=>bus.publish('network.health','bain.test',{audio:new Uint8Array(2)}));
});
test('isolates observer faults and bounded memory',()=>{
  const bus=new BelelAcousticBus(2);
  bus.subscribe('network.health',()=>{throw Error('observer')});
  for(let i=0;i<3;i++)bus.publish('network.health','bain.test',{count:i});
  assert.equal(bus.recent().length,2);
});
test('Belel pronunciation is lexical, Unicode-safe and leaves canonical text untouched',()=>{
  const p=new BelelPronunciationCortex();
  p.add({term:'Déjà vu',spoken:'day zhah voo',locale:'en-GB',version:1,source:'owner-approved'});
  p.add({term:'Belel',spoken:'Bel El',ipa:'bɛlˈɛl',locale:'en-GB',version:1,source:'owner-approved'});
  const original='Belel describes déjà vu. Belelian stays unchanged.';
  const rendered=p.prepare(original,'belel-kokoro');
  assert.equal(rendered.original,original);
  assert.equal(rendered.speakable,'Bel El describes day zhah voo. Belelian stays unchanged.');
  assert.equal(rendered.pronunciationNotes.length,2);
});
test('wake requires independently verified confidence and prevents spurious re-entry',async()=>{
  const bus=new BelelAcousticBus(); let now=10000;
  const frame={pcm:new Float32Array(1280),sampleRate:16000,at:1,source:'test-fixture' as const};
  const wake=new BelelWakeIntelligence({id:'test-model',score:async()=>.94},{verify:async()=>.9},bus,{primary:.84,verification:.72,cooldownMs:2000,now:()=>now});
  assert.equal((await wake.assess(frame)).accepted,true);
  assert.equal((await wake.assess(frame)).reason,'cooldown');
  now+=2100;
  assert.equal((await wake.assess(frame)).accepted,true);
});
test('acoustic near-miss never activates Belel',async()=>{
  const wake=new BelelWakeIntelligence({id:'test-model',score:async()=>.69},{verify:async()=>1},new BelelAcousticBus(),{primary:.8,verification:.7,cooldownMs:2000});
  assert.equal((await wake.assess({pcm:new Float32Array(1280),sampleRate:16000,at:0,source:'test-fixture'})).reason,'near_miss');
});
test('interruption yields without terminating voice session',()=>{
  const bus=new BelelAcousticBus();let yieldCount=0;let resumed=0;
  const duplex=new BelelDuplexConductor(bus,{onYield:()=>yieldCount++,onResume:()=>resumed++},()=>10000);
  duplex.assistantStart();duplex.userStart();duplex.userStart();
  assert.equal(yieldCount,1);
  assert.equal(duplex.state,'yielded');
  duplex.userEnd();duplex.resume();
  assert.equal(resumed,1);
  assert.equal(bus.recent().filter(e=>e.type==='duplex.yield').length,1);
});
test('model activation needs owner, licence and self-hosting review',()=>{
  const registry=new BelelModelRegistry();
  const model={id:'moshi-local',supportsDuplex:true as const,start:async()=>{},send:async()=>{},stop:async()=>{}};
  registry.register(model);
  assert.throws(()=>registry.use(model.id));
  assert.throws(()=>registry.approve(model.id,{ownerApproved:true,licenseReviewed:false,selfHosted:true}));
  registry.approve(model.id,{ownerApproved:true,licenseReviewed:true,selfHosted:true});
  assert.equal(registry.use(model.id),model);
  registry.revoke(model.id);
  assert.throws(()=>registry.use(model.id));
});

test('benchmark evaluation measures recall and transcript errors without raw audio',async()=>{
  const { evaluateWakeLabels, wordErrorRate } = await import('../../src/lib/belel-acoustic-network/evaluation.ts');
  const x=evaluateWakeLabels([
    {expectedWake:true,detectedWake:true,noise:'quiet'},
    {expectedWake:true,detectedWake:false,noise:'moderate'},
    {expectedWake:false,detectedWake:false,noise:'high'},
  ]);
  assert.equal(x.truePositiveRate,.5);
  assert.equal(x.falsePositiveRate,0);
  assert.equal(wordErrorRate('Hey Belel open the window','Hey Belel open window'),.2);
});
