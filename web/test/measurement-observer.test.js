import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync, readFileSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {apply as observeDsh} from '../../src/psycheval/harbor/agents/dsh_measurements.mjs';
import {observeResponse,sseObserver} from '../../src/psycheval/harbor/agents/opencode_measurements.mjs';

test('DSH truncation retains a prefix and stops subsequent writes', () => {
  const directory=mkdtempSync(join(tmpdir(),'peval-observer-'));
  const previous=process.env.PEVAL_DSH_MEASUREMENTS;
  process.env.PEVAL_DSH_MEASUREMENTS=join(directory,'events.ndjson');
  let callback;
  try {
    observeDsh({on(_event, fn){callback=fn;}});
    const result={value:{exitCode:7},isError:false};
    for(const id of ['before','x'.repeat(8*1024*1024),'after']) callback({callId:id,agent:{session:{id:'root'}}},result);
    const records=readFileSync(process.env.PEVAL_DSH_MEASUREMENTS,'utf8').trim().split('\n').map(JSON.parse);
    assert.equal(records.length,2);
    assert.equal(records[0].id,'before');
    assert.equal(records[0].exit_code,7);
    assert.deepEqual(records[1],{diagnostic:'truncated'});
  } finally {
    if(previous===undefined) delete process.env.PEVAL_DSH_MEASUREMENTS; else process.env.PEVAL_DSH_MEASUREMENTS=previous;
    rmSync(directory,{recursive:true,force:true});
  }
});

test('response observation preserves bytes, order, demand and cancellation', async () => {
  let pulls=0, cancelled, seen=[];
  const chunks=[new Uint8Array([0,255,1]),new Uint8Array([2,3])];
  const original=new Response(new ReadableStream({pull(c){c.enqueue(chunks[pulls++]);},cancel(reason){cancelled=reason;}},{highWaterMark:0}),{headers:{'content-type':'text/event-stream'}});
  const response=observeResponse(original,b=>seen.push([...b]));
  await new Promise(resolve=>setTimeout(resolve,10));
  assert.equal(pulls,0);
  const reader=response.body.getReader();
  assert.deepEqual([...((await reader.read()).value)], [0,255,1]);
  assert.equal(pulls,1);
  assert.deepEqual([...((await reader.read()).value)], [2,3]);
  await reader.cancel('caller-cancel');
  assert.equal(cancelled,'caller-cancel');
  assert.deepEqual(seen,[[0,255,1],[2,3]]);
});

test('observer exception cannot replace response bytes',async()=>{
  let failed=0;
  const response=observeResponse(new Response('identical'),()=>{throw Error('telemetry');},()=>failed++);
  assert.equal(await response.text(),'identical');assert.equal(failed,1);
});

test('SSE counts first nonempty reasoning or tool generation and one final usage',()=>{
  for(const delta of [{reasoning_content:'思考'},{tool_calls:[{function:{arguments:'{"'}}]}]) {
    let first=0,usage=[];
    const observe=sseObserver(()=>first++,u=>usage.push(u));
    const bytes=new TextEncoder().encode([
      {choices:[{delta:{role:'assistant',content:''}}]},
      {choices:[],usage:{prompt_tokens:1,completion_tokens:0}},
      {choices:[{delta}]},{choices:[{delta:{content:'OK'}}]},
      {usage:{prompt_tokens:100,completion_tokens:5,prompt_tokens_details:{cached_tokens:60}},choices:[]},
    ].map(x=>'data: '+JSON.stringify(x)+'\r\n\r\n').join('')+'data: [DONE]\n\n');
    for(const byte of bytes)observe(new Uint8Array([byte]));
    assert.equal(first,1);assert.deepEqual(usage.at(-1),{input_tokens:100,output_tokens:5,cached_tokens:60});
  }
});

test('oversized parsing disables measurement while pass-through remains available',()=>{
  let invalid=0,first=0;
  const observe=sseObserver(()=>first++,()=>{},()=>invalid++);
  observe(new TextEncoder().encode('x'.repeat(1024*1024+1)));
  observe(new TextEncoder().encode('data: {"choices":[{"delta":{"content":"ignored"}}]}\n'));
  assert.equal(invalid,1);assert.equal(first,0);
});
