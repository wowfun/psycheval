// Observe only the frozen final result. No prompt, arguments or output is retained.
import { appendFileSync } from 'node:fs';
export const name = 'peval-measurements';
export function apply(ctx) {
  let bytes = 0, count = 0, truncated = false;
  const write = record => {
    try {
      if (truncated) return;
      const line = JSON.stringify(record) + '\n';
      const size = Buffer.byteLength(line);
      if (bytes + size > 8 * 1024 * 1024 - 128 || count >= 99999) {
        if (!truncated) appendFileSync(process.env.PEVAL_DSH_MEASUREMENTS, '{"diagnostic":"truncated"}\n');
        truncated = true;
        return;
      }
      appendFileSync(process.env.PEVAL_DSH_MEASUREMENTS, line);
      bytes += size; count++;
    } catch { /* Measurement failure cannot affect tool execution. */ }
  };
  ctx.on('tools/result', (exec, result) => {
    const value = result.value;
    const scalar = x => typeof x === 'number' && Number.isFinite(x) ? x : undefined;
    write({type:'tool', id:exec.callId, call_id:exec.callId,
      session_id:exec.agent?.session?.id,
      exit_code:scalar(value?.exitCode),
      is_error:result.isError === true,
      timed_out:value?.timedOut === true,
      cancelled:value?.aborted === true || exec.signal?.aborted === true,
      status:result.isError ? 'failed' : value?.kind === 'background' ? 'unknown' : 'completed',
      source:'dsh.tools/result'});
  });
}
