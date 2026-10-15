// Native credentials stay in memory and on the CLI's authenticated bootstrap pipe.
const net = require("node:net");
const crypto = require("node:crypto");
const { spawn } = require("node:child_process");
const path = require("node:path");
const cliEntry = process.argv[2];
process.argv.splice(1, 1);
const timeoutMs = Number(process.env.PEVAL_WORKBUDDY_BOOTSTRAP_TIMEOUT_MS);
const python = process.env.PEVAL_WORKBUDDY_BOOTSTRAP_PYTHON;
delete process.env.PEVAL_WORKBUDDY_BOOTSTRAP_TIMEOUT_MS;
delete process.env.PEVAL_WORKBUDDY_BOOTSTRAP_PYTHON;
if (!python || !Number.isFinite(timeoutMs) || timeoutMs <= 0) {
  process.stderr.write("NATIVE_BOOTSTRAP_UNAVAILABLE\n");
  process.exit(125);
}

let payload;
try {
  payload = JSON.parse(
    process._linkedBinding("electron_browser_workbuddy_storage").loggerGet(),
  );
  if (payload.version !== 1 || typeof payload.atRestSecretKey !== "string" ||
      !payload.atRestSecretKey) {
    throw new Error("Unsupported native bootstrap");
  }
} catch {
  process.stderr.write("NATIVE_BOOTSTRAP_UNAVAILABLE\n");
  process.exit(125);
}
const key = crypto.createHash("sha256").update(payload.atRestSecretKey, "utf8").digest();
delete payload.atRestSecretKey;
const sessionId = crypto.randomUUID();
const token = crypto.randomBytes(32).toString("base64url");
const base = "\\\\.\\pipe\\peval-wb-" + crypto.randomUUID();
const readyPipe = base + "-ready";
const bootPipe = base + "-boot";
Object.assign(process.env, {
  CODEBUDDY_SIDECAR_READY_SOCKET: readyPipe,
  CODEBUDDY_SIDECAR_CREDENTIAL_BOOTSTRAP_SOCKET: bootPipe,
  CODEBUDDY_SIDECAR_READY_TOKEN: token,
  CODEBUDDY_SIDECAR_READY_SESSION_ID: sessionId,
  WORKBUDDY_AT_REST_ENCRYPTION: "fields",
});
const bootstrap = {
  version: 1,
  policy: "fields",
  symmetricKey: {
    keyId: crypto.createHash("sha256").update(key).digest("hex").slice(0, 16),
    keyBase64: key.toString("base64"),
  },
  asymmetricUnavailable: "missing-key",
};
key.fill(0);

const readyServer = net.createServer((socket) => {
  let buffer = "";
  socket.setEncoding("utf8");
  socket.on("data", (chunk) => {
    buffer += chunk.toString("utf8");
    if (buffer.length > 65536) { socket.destroy(); return; }
    const end = buffer.indexOf("\n");
    if (end < 0) return;
    try {
      const request = JSON.parse(buffer.slice(0, end));
      if (request.method !== "session.ready" || request.params?.protocolVersion !== 1 ||
          request.params?.token !== token || request.params?.sessionId !== sessionId ||
          request.params?.pid !== process.pid) {
        throw new Error("Ready identity mismatch");
      }
      socket.end(JSON.stringify({
        jsonrpc: "2.0", id: request.id, result: { ok: true },
      }) + "\n");
      for (const key of ["CODEBUDDY_SIDECAR_READY_SOCKET", "CODEBUDDY_SIDECAR_CREDENTIAL_BOOTSTRAP_SOCKET", "CODEBUDDY_SIDECAR_READY_TOKEN", "CODEBUDDY_SIDECAR_READY_SESSION_ID"]) delete process.env[key];
      readyServer.close();
    } catch { socket.destroy(); }
  });
});
readyServer.listen(readyPipe);
readyServer.unref();

const deadline = Date.now() + timeoutMs;
function checkDeadline() {
  const remaining = deadline - Date.now();
  if (remaining > 0) {
    watchdog = setTimeout(checkDeadline, Math.min(remaining, 2147483647));
    return;
  }
  process.stderr.write("NATIVE_BOOTSTRAP_FAILED\n");
  process.exit(125);
}
let watchdog = setTimeout(checkDeadline, Math.min(timeoutMs, 2147483647));

function deliver() {
  const env = { ...process.env };
  for (const key of Object.keys(env)) if (key.startsWith("CODEBUDDY_SIDECAR_")) delete env[key];
  const helper = spawn(python, [path.join(__dirname, "workbuddy_bootstrap.py"), bootPipe, String(process.pid), String(timeoutMs / 1000)], {
    env, stdio: ["pipe", "pipe", "pipe"], windowsHide: true,
  });
  const message = Buffer.from(JSON.stringify({ version: 1, sessionId, token, pid: process.pid, bootstrap }) + "\n", "utf8");
  helper.stdin.on("error", () => {});
  helper.stdin.end(message, () => message.fill(0));
  delete bootstrap.symmetricKey;
  let result = "";
  helper.stdout.on("data", chunk => {
    if (result.length < 128) result += chunk.toString("utf8");
  });
  helper.stderr.on("data", () => {});
  helper.on("error", () => {
    process.stderr.write("NATIVE_BOOTSTRAP_UNAVAILABLE\n");
    process.exit(125);
  });
  helper.on("close", code => {
    if (code !== 0 || result !== "NATIVE_BOOTSTRAP_ACK_OK\n") {
      process.stderr.write("NATIVE_BOOTSTRAP_FAILED\n");
      process.exit(125);
      return;
    }
    clearTimeout(watchdog);
    process.stderr.write("NATIVE_BOOTSTRAP_ACK_OK\n");
  });
}

deliver();
require(cliEntry);

