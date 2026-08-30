import { spawn } from "node:child_process";

async function startFixture(environment = {}) {
  const fixture = spawn("uv", ["run", "python", "web/e2e/fixture_server.py"], {
    stdio: ["ignore", "pipe", "pipe"],
    env: { ...process.env, ...environment },
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
  fixture.kill("SIGINT");
  await Promise.race([
    new Promise(resolve => fixture.once("exit", resolve)),
    new Promise(resolve => setTimeout(resolve, 3000)),
  ]);
  if (fixture.exitCode === null) fixture.kill("SIGKILL");
}

export { startFixture, stopFixture };
