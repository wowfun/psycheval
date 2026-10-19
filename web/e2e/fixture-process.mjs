import { execFile, spawn } from "node:child_process";
import { promisify } from "node:util";

async function startFixture(environment = {}) {
  const fixture = spawn("uv", ["run", "--no-sync", "python", "web/e2e/fixture_server.py"], {
    stdio: ["ignore", "pipe", "pipe"],
    env: { ...process.env, ...environment },
    windowsHide: true,
  });
  const output = [];
  let stdout = "";
  fixture.stdout.on("data", chunk => {
    const text = String(chunk);
    stdout += text;
    output.push(text);
  });
  fixture.stderr.on("data", chunk => output.push(String(chunk)));
  const deadline = Date.now() + 15_000;
  while (Date.now() < deadline) {
    if (fixture.exitCode !== null) {
      throw new Error(`ACP fixture exited early:\n${output.join("")}`);
    }
    const origin = stdout.match(
      /^PEVAL_E2E_ORIGIN=(http:\/\/127\.0\.0\.1:\d+)\r?$/m,
    )?.[1];
    if (!origin) {
      await new Promise(resolve => setTimeout(resolve, 50));
      continue;
    }
    try {
      const response = await fetch(new URL("/api/session", origin), {
        signal: AbortSignal.timeout(250),
      });
      if (response.ok) {
        fixture.origin = origin;
        return fixture;
      }
    } catch {
      // The fixture has not bound its listener yet.
    }
    await new Promise(resolve => setTimeout(resolve, 50));
  }
  throw new Error(`ACP fixture did not become ready:\n${output.join("")}`);
}

async function stopFixture(fixture) {
  if (!fixture || fixture.exitCode !== null) return;
  if (process.platform === "win32") {
    // Killing uv alone leaves its Python server holding the pipes and listener open.
    try {
      await promisify(execFile)("taskkill", ["/PID", String(fixture.pid), "/T", "/F"], { windowsHide: true });
    } catch (error) {
      if (!await waitForExit(fixture)) throw error;
    }
    if (!await waitForExit(fixture)) throw new Error("Windows fixture did not exit after tree termination");
    return;
  }
  fixture.kill("SIGINT");
  await Promise.race([
    new Promise(resolve => fixture.once("exit", resolve)),
    new Promise(resolve => setTimeout(resolve, 3000)),
  ]);
  if (fixture.exitCode === null) fixture.kill("SIGKILL");
}

async function waitForExit(fixture) {
  if (fixture.exitCode !== null || fixture.signalCode !== null) return true;
  return new Promise(resolve => {
    const onExit = () => finish(true);
    const timer = setTimeout(() => finish(false), 3000);
    function finish(exited) {
      clearTimeout(timer);
      fixture.removeListener("exit", onExit);
      resolve(exited);
    }
    fixture.once("exit", onExit);
  });
}

export { startFixture, stopFixture };
