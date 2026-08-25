#!/usr/bin/env node
// Copyright 2026 Jarryd Adaens
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

/**
 * Supervise one pi RPC session: spawn cli.js through node directly, send one
 * prompt, stream JSONL events, exit on stream idle, and report
 * "ended naturally" versus "hard cap hit" as distinct outcomes.
 *
 * Do not use `pi -p`. Print mode buffers until exit, cannot host the review
 * bot, and forces liveness to be inferred from CPU. Do not spawn `pi.cmd`:
 * the .cmd shim is fragile to path escaping. Do not use Node `readline` to
 * parse stdout: it splits on U+2028/U+2029, which are valid inside JSON.
 *
 * Exit codes:
 *   0 ended naturally
 *   1 hung (killed after silence + reachable rig + no descendants)
 *   2 hard cap hit
 *   3 existing pi session found; refused to spawn a second
 *   4 rig down (silence + unreachable endpoint)
 *   5 spawn / resolution / usage failure
 */

import { spawn, execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync, appendFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { StringDecoder } from "node:string_decoder";
import { fileURLToPath } from "node:url";

const EXIT = {
  endedNaturally: 0,
  hung: 1,
  hardCap: 2,
  refusedExisting: 3,
  rigDown: 4,
  spawnFailed: 5,
};

const DEFAULT_IDLE_MS = 180_000; // 3 min: how long without events before a liveness check
const DEFAULT_THINK_GRACE_MS = 900_000; // 15 min: silence that looks like thinking before HUNG
const DEFAULT_HARD_CAP_MS = 0; // none; the skill forbids a wall-clock budget as the kill signal
const CPU_WORKING_S_PER_MIN = 0.2; // measured working burn was ~0.4+ s/min; hung was ~0.01
const CPU_SAMPLE_MS = 15_000;

function usage() {
  return `Usage:
  node pi-rpc-client.mjs --prompt <text> | --prompt-file <path>
       [--cwd <dir>] [--idle-ms ${DEFAULT_IDLE_MS}] [--think-grace-ms ${DEFAULT_THINK_GRACE_MS}]
       [--hard-cap-ms ${DEFAULT_HARD_CAP_MS}] [--model <model-slug>] [--events-file <path>] [--session-dir <path>]
       [--name <session-name>] [--transport rpc|json] [--allow-existing] [--probe-url <url>]
  node pi-rpc-client.mjs --list-sessions
  node pi-rpc-client.mjs --self-check
`;
}

function parseArgs(argv) {
  const out = {
    prompt: null,
    promptFile: null,
    cwd: process.cwd(),
    idleMs: DEFAULT_IDLE_MS,
    thinkGraceMs: DEFAULT_THINK_GRACE_MS,
    hardCapMs: DEFAULT_HARD_CAP_MS,
    model: null,
    eventsFile: null,
    sessionDir: null,
    name: null,
    transport: "rpc",
    allowExisting: false,
    probeUrl: null,
    listSessions: false,
    selfCheck: false,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    const next = () => {
      i += 1;
      if (i >= argv.length) {
        throw new Error(`Missing value for ${arg}`);
      }
      return argv[i];
    };
    switch (arg) {
      case "--prompt":
        out.prompt = next();
        break;
      case "--prompt-file":
        out.promptFile = next();
        break;
      case "--cwd":
        out.cwd = resolve(next());
        break;
      case "--idle-ms":
        out.idleMs = Number(next());
        break;
      case "--think-grace-ms":
        out.thinkGraceMs = Number(next());
        break;
      case "--hard-cap-ms":
        out.hardCapMs = Number(next());
        break;
      case "--model":
        out.model = next();
        break;
      case "--events-file":
        out.eventsFile = resolve(next());
        break;
      case "--session-dir":
        out.sessionDir = resolve(next());
        break;
      case "--name":
        out.name = next();
        break;
      case "--transport": {
        const value = next();
        if (value !== "rpc" && value !== "json") {
          throw new Error(`--transport must be rpc or json, got ${value}`);
        }
        out.transport = value;
        break;
      }
      case "--allow-existing":
        out.allowExisting = true;
        break;
      case "--probe-url":
        out.probeUrl = next();
        break;
      case "--list-sessions":
        out.listSessions = true;
        break;
      case "--self-check":
        out.selfCheck = true;
        break;
      case "--help":
      case "-h":
        process.stdout.write(usage());
        process.exit(0);
        break;
      default:
        throw new Error(`Unknown argument: ${arg}\n${usage()}`);
    }
  }
  return out;
}

function isFile(path) {
  try {
    return existsSync(path);
  } catch {
    return false;
  }
}

function envPath(name) {
  return process.env[name] || process.env[name.toUpperCase()] || process.env[name.toLowerCase()];
}

function resolvePiLaunch() {
  const envNode = envPath("PI_NODE_EXE");
  const envCli = envPath("PI_CLI_JS");
  if (envNode && envCli && isFile(envNode) && isFile(envCli)) {
    return { nodeExe: envNode, cliJs: envCli, note: "PI_NODE_EXE + PI_CLI_JS" };
  }

  const envRoot = envPath("PI_NODE_ROOT");
  const candidates = [];
  if (envRoot) {
    candidates.push(envRoot);
  }
  const local = envPath("LOCALAPPDATA");
  if (local) {
    candidates.push(join(local, "pi-node", "current"));
  }
  candidates.push(join(homedir(), "AppData", "Local", "pi-node", "current"));
  candidates.push(join(homedir(), ".pi-node", "current"));

  for (const root of candidates) {
    const nodeExe = join(root, "node.exe");
    const nodeBin = join(root, "bin", "node");
    const nodeUnix = join(root, "node");
    const cliJs = join(root, "node_modules", "@earendil-works", "pi-coding-agent", "dist", "cli.js");
    const node = [nodeExe, nodeBin, nodeUnix].find((p) => isFile(p));
    if (node && isFile(cliJs)) {
      return { nodeExe: node, cliJs, note: `pi-node at ${root}` };
    }
  }

  return null;
}

function readJsonIfPresent(path) {
  if (!isFile(path)) {
    return null;
  }
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch {
    return null;
  }
}

function defaultProbeUrl() {
  const agentDir = join(homedir(), ".pi", "agent");
  const settings = readJsonIfPresent(join(agentDir, "settings.json")) || {};
  const models = readJsonIfPresent(join(agentDir, "models.json")) || {};
  const providerName = settings.defaultProvider;
  const provider = providerName && models.providers ? models.providers[providerName] : null;
  if (provider && typeof provider.baseUrl === "string" && provider.baseUrl.length > 0) {
    const base = provider.baseUrl.replace(/\/+$/u, "");
    return `${base}/models`;
  }
  return null;
}

function probeEndpoint(url, timeoutMs = 3000) {
  if (!url) {
    return { ok: false, reason: "no probe URL (pass --probe-url or configure ~/.pi/agent/models.json)" };
  }
  const started = Date.now();
  try {
    const script = `
const url = ${JSON.stringify(url)};
const ac = new AbortController();
const t = setTimeout(() => ac.abort(), ${timeoutMs});
fetch(url, { signal: ac.signal })
  .then((r) => {
    clearTimeout(t);
    process.stdout.write(JSON.stringify({ ok: r.ok || r.status < 500, status: r.status, ms: Date.now() - ${started} }));
  })
  .catch((e) => {
    clearTimeout(t);
    process.stdout.write(JSON.stringify({ ok: false, error: e.name === "AbortError" ? "timeout" : String(e), ms: Date.now() - ${started} }));
  });
`;
    const out = execFileSync(process.execPath, ["-e", script], {
      encoding: "utf8",
      timeout: timeoutMs + 2000,
      windowsHide: true,
    });
    return JSON.parse(out.trim() || '{"ok":false}');
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : String(err) };
  }
}

function runPowerShell(script) {
  const wrapped = `$ProgressPreference = 'SilentlyContinue'\n${script}`;
  const encoded = Buffer.from(wrapped, "utf16le").toString("base64");
  return execFileSync("powershell.exe", ["-NoProfile", "-NonInteractive", "-EncodedCommand", encoded], {
    encoding: "utf8",
    timeout: 20000,
    windowsHide: true,
  }).trim();
}

function parseJsonPayload(text) {
  const start = text.search(/[\[{]/u);
  const payload = start > 0 ? text.slice(start) : text;
  const parsed = JSON.parse(payload);
  return Array.isArray(parsed) ? parsed : [parsed];
}

function powershellJson(script) {
  const out = runPowerShell(script);
  if (!out) {
    return [];
  }
  return parseJsonPayload(out);
}

function listPiSessions() {
  if (process.platform === "win32") {
    const script = `
$procs = @(Get-CimInstance Win32_Process | Where-Object {
  $_.CommandLine -and ($_.CommandLine -match 'pi-coding-agent' -or $_.CommandLine -match 'dist[\\\\/]cli\\.js')
})
if ($procs.Count -eq 0) { '[]' } else {
  $procs | ForEach-Object {
    [PSCustomObject]@{ pid = $_.ProcessId; ppid = $_.ParentProcessId; name = $_.Name; commandLine = $_.CommandLine }
  } | ConvertTo-Json -Compress
}
`;
    try {
      return powershellJson(script);
    } catch (err) {
      return [{ error: err instanceof Error ? err.message : String(err) }];
    }
  }
  try {
    const out = execFileSync("ps", ["-eo", "pid=,ppid=,args="], { encoding: "utf8", timeout: 10000 });
    return out
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const match = /^(\d+)\s+(\d+)\s+(.*)$/u.exec(line);
        if (!match) {
          return null;
        }
        const commandLine = match[3];
        if (!/pi-coding-agent|\/dist\/cli\.js|\\dist\\cli\.js/u.test(commandLine)) {
          return null;
        }
        return { pid: Number(match[1]), ppid: Number(match[2]), name: "node", commandLine };
      })
      .filter(Boolean);
  } catch (err) {
    return [{ error: err instanceof Error ? err.message : String(err) }];
  }
}

function listDescendants(rootPid) {
  if (!rootPid) {
    return [];
  }
  if (process.platform === "win32") {
    const script = `
$all = Get-CimInstance Win32_Process
$root = ${Number(rootPid)}
$ids = New-Object 'System.Collections.Generic.HashSet[int]'
[void]$ids.Add($root)
$changed = $true
while ($changed) {
  $changed = $false
  foreach ($p in $all) {
    if ($ids.Contains([int]$p.ParentProcessId) -and -not $ids.Contains([int]$p.ProcessId)) {
      [void]$ids.Add([int]$p.ProcessId)
      $changed = $true
    }
  }
}
[void]$ids.Remove($root)
$kids = @($all | Where-Object { $ids.Contains([int]$_.ProcessId) })
if ($kids.Count -eq 0) { '[]' } else {
  $kids | ForEach-Object {
    [PSCustomObject]@{ pid = $_.ProcessId; ppid = $_.ParentProcessId; name = $_.Name; commandLine = $_.CommandLine }
  } | ConvertTo-Json -Compress
}
`;
    try {
      return powershellJson(script);
    } catch {
      return [];
    }
  }
  try {
    const out = execFileSync("ps", ["-eo", "pid=,ppid=,args="], { encoding: "utf8", timeout: 10000 });
    const rows = out
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const match = /^(\d+)\s+(\d+)\s+(.*)$/u.exec(line);
        return match
          ? { pid: Number(match[1]), ppid: Number(match[2]), name: "proc", commandLine: match[3] }
          : null;
      })
      .filter(Boolean);
    const kids = [];
    const pending = [Number(rootPid)];
    const seen = new Set(pending);
    while (pending.length > 0) {
      const current = pending.pop();
      for (const row of rows) {
        if (row.ppid === current && !seen.has(row.pid)) {
          seen.add(row.pid);
          pending.push(row.pid);
          kids.push(row);
        }
      }
    }
    return kids;
  } catch {
    return [];
  }
}

function cpuSeconds(pid) {
  if (!pid) {
    return null;
  }
  try {
    if (process.platform === "win32") {
      const out = execFileSync(
        "powershell.exe",
        ["-NoProfile", "-NonInteractive", "-EncodedCommand", Buffer.from(`(Get-Process -Id ${Number(pid)} -ErrorAction Stop).CPU`, "utf16le").toString("base64")],
        { encoding: "utf8", timeout: 8000, windowsHide: true },
      ).trim();
      if (!out) {
        return null;
      }
      const value = Number(out);
      return Number.isFinite(value) ? value : null;
    }
    const stat = readFileSync(`/proc/${pid}/stat`, "utf8");
    const close = stat.indexOf(")");
    const rest = stat.slice(close + 2).split(" ");
    const utime = Number(rest[11]);
    const stime = Number(rest[12]);
    let ticks = 100;
    try {
      ticks = Number(execFileSync("getconf", ["CLK_TCK"], { encoding: "utf8" }).trim()) || 100;
    } catch {
      ticks = 100;
    }
    return (utime + stime) / ticks;
  } catch {
    return null;
  }
}

async function sampleCpuRate(pid, sampleMs = CPU_SAMPLE_MS) {
  const first = cpuSeconds(pid);
  await delay(sampleMs);
  const second = cpuSeconds(pid);
  if (first == null || second == null) {
    return null;
  }
  const delta = Math.max(0, second - first);
  const perMin = delta / (sampleMs / 60_000);
  return { delta, perMin };
}

function delay(ms) {
  return new Promise((resolveDelay) => {
    setTimeout(resolveDelay, ms);
  });
}

function attachJsonlReader(stream, onLine) {
  const decoder = new StringDecoder("utf8");
  let buffer = "";
  stream.on("data", (chunk) => {
    buffer += typeof chunk === "string" ? chunk : decoder.write(chunk);
    while (true) {
      const newlineIndex = buffer.indexOf("\n");
      if (newlineIndex === -1) {
        break;
      }
      let line = buffer.slice(0, newlineIndex);
      buffer = buffer.slice(newlineIndex + 1);
      if (line.endsWith("\r")) {
        line = line.slice(0, -1);
      }
      if (line.length > 0) {
        onLine(line);
      }
    }
  });
  stream.on("end", () => {
    buffer += decoder.end();
    if (buffer.length > 0) {
      onLine(buffer.endsWith("\r") ? buffer.slice(0, -1) : buffer);
    }
  });
}

function emitResult(record, eventsFile) {
  const line = JSON.stringify({ type: "client_result", ...record });
  process.stdout.write(`${line}\n`);
  process.stderr.write(`${line}\n`);
  if (eventsFile) {
    appendFileSync(eventsFile, `${line}\n`);
  }
}

function sendCommand(child, obj) {
  if (!child.stdin || child.stdin.destroyed) {
    return false;
  }
  return child.stdin.write(`${JSON.stringify(obj)}\n`);
}

function killTree(pid) {
  if (!pid) {
    return;
  }
  try {
    if (process.platform === "win32") {
      execFileSync("taskkill", ["/PID", String(pid), "/T", "/F"], {
        encoding: "utf8",
        timeout: 8000,
        windowsHide: true,
        stdio: "ignore",
      });
    } else {
      process.kill(pid, "SIGKILL");
    }
  } catch {
    // Already gone.
  }
}

async function runSession(args, launch, prompt) {
  if (args.sessionDir) {
    mkdirSync(args.sessionDir, { recursive: true });
  }
  if (args.eventsFile) {
    mkdirSync(dirname(args.eventsFile), { recursive: true });
    writeFileSync(args.eventsFile, "");
  }

  const cliArgs = args.transport === "json" ? ["--mode", "json", "-a"] : ["--mode", "rpc", "-a"];
  if (args.model) {
    cliArgs.push("--model", args.model);
  }
  if (args.sessionDir) {
    cliArgs.push("--session-dir", args.sessionDir);
  } else {
    cliArgs.push("--no-session");
  }
  if (args.name) {
    cliArgs.push("--name", args.name);
  }
  // JSON mode takes the prompt as a CLI argument. That is fine for a smoke
  // probe and unusable for a real worker contract on Windows (CreateProcess
  // command-line cap). RPC is the production transport: the prompt goes on
  // JSONL stdin with no argv limit. See pi-session-operations.md.
  if (args.transport === "json") {
    cliArgs.push(prompt);
  }

  const child = spawn(launch.nodeExe, [launch.cliJs, ...cliArgs], {
    cwd: args.cwd,
    env: process.env,
    stdio: args.transport === "json" ? ["ignore", "pipe", "pipe"] : ["pipe", "pipe", "pipe"],
    windowsHide: true,
  });

  let stderr = "";
  child.stderr.on("data", (chunk) => {
    stderr += chunk.toString();
    if (stderr.length > 32_000) {
      stderr = stderr.slice(-16_000);
    }
  });

  const startedAt = Date.now();
  let lastEventAt = startedAt;
  let eventCount = 0;
  let lastEventType = null;
  let sawAgentSettled = false;
  let settledAt = null;
  let outcome = null;
  let closed = false;

  const finish = (nextOutcome, extra = {}) => {
    if (closed) {
      return;
    }
    closed = true;
    outcome = { outcome: nextOutcome, ...extra };
  };

  const handleLine = (line) => {
    lastEventAt = Date.now();
    eventCount += 1;
    if (args.eventsFile) {
      appendFileSync(args.eventsFile, `${line}\n`);
    }
    process.stdout.write(`${line}\n`);
    let parsed;
    try {
      parsed = JSON.parse(line);
    } catch {
      return;
    }
    lastEventType = parsed.type || "unparsed";
    if (parsed.type === "agent_settled" || parsed.type === "agent_end") {
      sawAgentSettled = true;
      settledAt = Date.now();
    }
    if (parsed.type === "extension_ui_request") {
      if (args.transport !== "rpc") {
        return;
      }
      const method = parsed.method;
      const dialog = method === "select" || method === "confirm" || method === "input" || method === "editor";
      if (dialog) {
        sendCommand(child, { type: "extension_ui_response", id: parsed.id, cancelled: true });
      }
    }
  };

  attachJsonlReader(child.stdout, handleLine);

  await delay(400);
  if (child.exitCode !== null && !closed) {
    finish("spawn_failed", { detail: `pi exited immediately with code ${child.exitCode}`, stderr: stderr.slice(-2000) });
    emitResult(
      {
        outcome: "spawn_failed",
        exitCode: EXIT.spawnFailed,
        durationMs: Date.now() - startedAt,
        eventCount,
        lastEventType,
        stderr: stderr.slice(-2000),
        launch,
      },
      args.eventsFile,
    );
    process.exit(EXIT.spawnFailed);
  }

  if (args.transport === "rpc") {
    sendCommand(child, { id: "prompt-1", type: "prompt", message: prompt });
  }

  child.on("exit", (code, signal) => {
    if (!closed) {
      // One-shot json processes exit when done. Do not treat their exit
      // code as a verdict (plan Q6); the Boss reads verdict.json.
      if (sawAgentSettled || (args.transport === "json" && eventCount > 0)) {
        finish("ended_naturally", { childExitCode: code, signal });
      } else {
        finish("hung", { childExitCode: code, signal, detail: "pi exited before any settle event" });
      }
    }
  });

  const watchdog = async () => {
    while (!closed) {
      await delay(5_000);
      if (closed) {
        break;
      }
      const now = Date.now();
      if (args.hardCapMs > 0 && now - startedAt >= args.hardCapMs) {
        sendCommand(child, { type: "abort" });
        await delay(1500);
        killTree(child.pid);
        finish("hard_cap", { detail: `hard cap ${args.hardCapMs}ms hit` });
        break;
      }
      const silentFor = now - lastEventAt;
      if (silentFor < args.idleMs) {
        continue;
      }

      const descendants = listDescendants(child.pid);
      if (descendants.length > 0) {
        lastEventAt = Date.now();
        continue;
      }

      const probe = probeEndpoint(args.probeUrl || defaultProbeUrl());
      if (!probe.ok) {
        sendCommand(child, { type: "abort" });
        await delay(1500);
        killTree(child.pid);
        finish("rig_down", { detail: "event-stream silence and endpoint unreachable", probe });
        break;
      }

      const cpu = await sampleCpuRate(child.pid);
      if (cpu && cpu.perMin >= CPU_WORKING_S_PER_MIN) {
        lastEventAt = Date.now();
        continue;
      }

      if (sawAgentSettled && settledAt && now - settledAt >= args.idleMs) {
        sendCommand(child, { type: "abort" });
        await delay(500);
        killTree(child.pid);
        finish("ended_naturally", { detail: "agent_settled then stream idle; no descendants" });
        break;
      }

      const silenceTotal = now - lastEventAt;
      if (silenceTotal >= args.thinkGraceMs) {
        sendCommand(child, { type: "abort" });
        await delay(1500);
        killTree(child.pid);
        finish("hung", {
          detail: "silence past think-grace with reachable endpoint, live process, no descendants, low CPU",
          probe,
          cpu,
        });
        break;
      }
    }
  };

  await Promise.race([
    watchdog(),
    new Promise((resolveWait) => {
      const timer = setInterval(() => {
        if (closed) {
          clearInterval(timer);
          resolveWait();
        }
      }, 250);
    }),
  ]);

  if (!closed) {
    if (sawAgentSettled) {
      finish("ended_naturally");
    } else {
      finish("hung", { detail: "watchdog ended without a recorded outcome" });
    }
  }

  if (child.exitCode === null && child.pid) {
    sendCommand(child, { type: "abort" });
    await delay(500);
    killTree(child.pid);
  }

  const exitCode =
    outcome.outcome === "ended_naturally"
      ? EXIT.endedNaturally
      : outcome.outcome === "hung"
        ? EXIT.hung
        : outcome.outcome === "hard_cap"
          ? EXIT.hardCap
          : outcome.outcome === "rig_down"
            ? EXIT.rigDown
            : EXIT.spawnFailed;

  emitResult(
    {
      ...outcome,
      exitCode,
      durationMs: Date.now() - startedAt,
      eventCount,
      lastEventType,
      pid: child.pid,
      sawAgentSettled,
      launch,
    },
    args.eventsFile,
  );
  process.exit(exitCode);
}

async function main() {
  let args;
  try {
    args = parseArgs(process.argv.slice(2));
  } catch (err) {
    process.stderr.write(`${err instanceof Error ? err.message : String(err)}\n`);
    process.exit(EXIT.spawnFailed);
  }

  const launch = resolvePiLaunch();

  if (args.selfCheck) {
    const sessions = listPiSessions();
    const probeUrl = args.probeUrl || defaultProbeUrl();
    const probe = probeUrl ? probeEndpoint(probeUrl) : { ok: false, reason: "no probe URL" };
    const record = {
      type: "self_check",
      launch,
      probeUrlPresent: Boolean(probeUrl),
      probe,
      sessionCount: sessions.filter((s) => s.pid).length,
      sessions,
      client: fileURLToPath(import.meta.url),
    };
    process.stdout.write(`${JSON.stringify(record, null, 2)}\n`);
    process.exit(launch ? EXIT.endedNaturally : EXIT.spawnFailed);
  }

  if (args.listSessions) {
    const sessions = listPiSessions();
    process.stdout.write(`${JSON.stringify(sessions, null, 2)}\n`);
    process.exit(EXIT.endedNaturally);
  }

  if (!launch) {
    emitResult(
      {
        outcome: "spawn_failed",
        exitCode: EXIT.spawnFailed,
        detail: "Could not resolve pi's node.exe and dist/cli.js. Install pi, or set PI_NODE_EXE and PI_CLI_JS.",
      },
      args.eventsFile,
    );
    process.exit(EXIT.spawnFailed);
  }

  const sessions = listPiSessions().filter((s) => s.pid);
  if (sessions.length > 0 && !args.allowExisting) {
    emitResult(
      {
        outcome: "refused_existing",
        exitCode: EXIT.refusedExisting,
        detail: "Existing pi session(s) found. Will not spawn a second. Ask the user before killing anything.",
        sessions,
      },
      args.eventsFile,
    );
    process.exit(EXIT.refusedExisting);
  }

  let prompt = args.prompt;
  if (args.promptFile) {
    prompt = readFileSync(resolve(args.promptFile), "utf8");
  }
  if (!prompt || !prompt.trim()) {
    process.stderr.write(`A prompt is required.\n${usage()}`);
    process.exit(EXIT.spawnFailed);
  }

  await runSession(args, launch, prompt);
}

main().catch((err) => {
  process.stderr.write(`${err instanceof Error ? err.stack || err.message : String(err)}\n`);
  process.exit(EXIT.spawnFailed);
});
