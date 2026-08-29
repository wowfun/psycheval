import { spawn } from "node:child_process";

async function startFixture(environment = {}) {
  const fixture = spawn("uv", ["run", "python", "web/e2e/fixture_server.py"], {
    stdio: ["ignore", "pipe", "pipe"],
    env: { ...process.env, ...environment },
  });
  const output = [];
  fixture.stdout.on("data", chunk => output.push(String(chunk)));
  fixture.stderr.on("data", chunk => output.push(String(chunk)));
  const deadline = Date.now() + 15_000;
  while (Date.now() < deadline) {
    if (fixture.exitCode !== null) {
      throw new Error(`ACP fixture exited early:\n${output.join("")}`);
    }
    try {
      const response = await fetch("http://127.0.0.1:4178/api/session", {
        signal: AbortSignal.timeout(250),
      });
      if (response.ok) return fixture;
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
