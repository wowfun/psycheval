import {appendFileSync} from 'node:fs';

// Observe bytes as the consumer pulls them. Bounded parsing never delays output
// until completion, and cancellation reaches the original reader immediately.
export function observeResponse(response, observe, failed = () => {}) {
  if (!response.body) return response;
  const reader = response.body.getReader();
  return new Response(new ReadableStream({
    async pull(controller) {
      try {
        const item = await reader.read();
        if (item.done) { controller.close(); return; }
        try { observe(item.value); } catch { try { failed(); } catch { /* Optional diagnostics cannot break the stream. */ } }
        controller.enqueue(item.value);
      } catch (error) { controller.error(error); }
    },
    cancel(reason) { return reader.cancel(reason); },
  }, {highWaterMark:0}), {status:response.status,statusText:response.statusText,headers:response.headers});
}

export function sseObserver(onOutput, onUsage, onInvalid = () => {}) {
  const decoder = new TextDecoder();
  let pending = '', enabled = true, first = false;
  return bytes => {
    if (!enabled) return;
    pending += decoder.decode(bytes, {stream:true});
    if (pending.length > 1024 * 1024) { enabled = false; pending = ''; onInvalid(); return; }
    let end;
    while ((end = pending.indexOf('\n')) >= 0) {
      const line = pending.slice(0,end).replace(/\r$/, ''); pending = pending.slice(end+1);
      if (!line.startsWith('data:')) continue;
      const text = line.slice(5).trim();
      if (!text || text === '[DONE]') continue;
      let data;
      try { data = JSON.parse(text); } catch { enabled=false; pending=''; onInvalid(); return; }
      for (const choice of data.choices ?? []) {
        const d = choice.delta ?? {};
        const nonempty = x => typeof x === 'string' && x.length > 0;
        if (!first && (nonempty(d.content) || nonempty(d.reasoning_content) || nonempty(d.reasoning) ||
            (d.tool_calls ?? []).some(t => nonempty(t.function?.name) || nonempty(t.function?.arguments)))) {
          first = true; onOutput();
        }
      }
      if (data.usage) {
        const u=data.usage;
        onUsage({input_tokens:u.prompt_tokens,output_tokens:u.completion_tokens,
                 cached_tokens:u.prompt_tokens_details?.cached_tokens});
      }
    }
  };
}

export default {id:'peval-measurements', async setup(ctx) {
  let bytes=0,count=0,sequence=0,truncated=false;
  const active=new Map(), requests=new WeakMap();
  const write=record=>{
    try {
      if(truncated) return;
      const line=JSON.stringify(record)+'\n',size=Buffer.byteLength(line);
      if(bytes+size>8*1024*1024-128 || count>=99999) {
        truncated=true;appendFileSync(process.env.PEVAL_OPENCODE_MEASUREMENTS,'{"kind":"truncated"}\n');return;
      }
      appendFileSync(process.env.PEVAL_OPENCODE_MEASUREMENTS,line);bytes+=size;count++;
    } catch { /* Evidence failure cannot change a request. */ }
  };
  write({kind:'loaded'});
  await ctx.session.hook('http.request',e=>{
    if(e.kind!=='primary') return;
    const id=String(++sequence),session=e.sessionID;
    const attempt={id,session};requests.set(e.request,attempt);active.set(session,attempt);
    write({kind:'request',id,session,time:Date.now()});
  });
  await ctx.session.hook('http.response',e=>{
    if(e.kind!=='primary') return;
    const attempt=requests.get(e.request);
    if(!attempt) { write({kind:'unlinked_response',session:e.sessionID});return; }
    const {id,session}=attempt;
    if(!e.response.ok) return;
    if(!e.response.headers.get('content-type')?.includes('text/event-stream')) {
      write({kind:'unsupported_protocol',id,session});return;
    }
    const observer=sseObserver(
      ()=>write({kind:'output',id,session,time:Date.now()}),
      usage=>write({kind:'usage',id,session,...usage}),
      ()=>write({kind:'invalid_stream',id,session}));
    e.response=observeResponse(e.response,observer,()=>write({kind:'observer_error',id,session}));
  });
  await ctx.session.hook('retry',e=>write({kind:'retry',session:e.sessionID,attempt:e.attempt,time:Date.now()}));
  (async()=>{for await(const e of ctx.event.subscribe()) {
    if(!['session.step.started','session.step.streamed','session.step.ended'].includes(e.type)) continue;
    const d=e.data,session=d.sessionID,attempt=active.get(session);
    write({kind:e.type,session,message:d.assistantMessageID,request:attempt?.id,
           time:e.created,start:d.started});
  }})().catch(()=>write({kind:'event_subscription_failed'}));
}};
