#!/usr/bin/env node
/** Project-scoped configuration for orchestrate-localmodel-workflow. */

import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { resolve, join } from "node:path";

const RELATIVE_PATH = join("harness", "orchestrate-localmodel-workflow", "cursor-config.json");
const DEFAULTS = {
  model: "qwen3.8",
  idle_timeout_seconds: 180,
  think_grace_timeout_seconds: 900,
  probe_url: null,
};
const MODELS = {
  "1": "qwen3.8",
  "2": "local-model-placeholder",
};

function usage() {
  return `Usage:
  node localmodel-config.mjs init --workspace <project-root> [--force]
  node localmodel-config.mjs model --workspace <project-root> [--model <1|2|slug>]
  node localmodel-config.mjs timeout --workspace <project-root> [--timeout <idle|think> <seconds|default>]
  node localmodel-config.mjs show --workspace <project-root>`;
}

function argsFrom(argv) {
  const [command, ...rest] = argv;
  const values = { command, workspace: process.cwd(), force: false, model: null, timeout: null };
  for (let index = 0; index < rest.length; index += 1) {
    const item = rest[index];
    if (item === "--workspace") values.workspace = resolve(rest[++index] || "");
    else if (item === "--force") values.force = true;
    else if (item === "--model") values.model = rest[++index] || "";
    else if (item === "--timeout") values.timeout = [rest[++index] || "", rest[++index] || ""];
    else throw new Error(`Unknown argument: ${item}`);
  }
  return values;
}

function configPath(workspace) { return join(resolve(workspace), RELATIVE_PATH); }

function stripJsonComments(text) {
  let result = ""; let quoted = false; let escaped = false; let lineComment = false;
  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];
    const next = text[index + 1];
    if (lineComment) { if (character === "\n") { lineComment = false; result += character; } continue; }
    if (!quoted && character === "/" && next === "/") { lineComment = true; index += 1; continue; }
    result += character;
    if (character === "\\" && quoted) escaped = !escaped;
    else if (character === '"' && !escaped) quoted = !quoted;
    else escaped = false;
  }
  return result;
}

function format(config) {
  return `{
  // Pi model slug passed as --model when the worker starts.\n  "model": ${JSON.stringify(config.model)},
  // Seconds without events before the client checks worker liveness.\n  "idle_timeout_seconds": ${config.idle_timeout_seconds},
  // Seconds of reachable, low-CPU silence before the client classifies a worker as hung.\n  "think_grace_timeout_seconds": ${config.think_grace_timeout_seconds},
  // Optional endpoint override for health and liveness probes; null reads Pi's own configuration.\n  "probe_url": ${config.probe_url === null ? "null" : JSON.stringify(config.probe_url)}
}
`;
}

function load(workspace) {
  const path = configPath(workspace);
  if (!existsSync(path)) throw new Error(`Configuration is missing. Run /localmodel-init first.\nPath: ${path}`);
  let parsed;
  try { parsed = JSON.parse(stripJsonComments(readFileSync(path, "utf8"))); }
  catch (error) { throw new Error(`Configuration is not valid JSONC: ${error.message}`); }
  const config = { ...DEFAULTS, ...parsed };
  if (typeof config.model !== "string" || !config.model.trim()) throw new Error("Configuration field 'model' must be a non-empty slug.");
  for (const key of ["idle_timeout_seconds", "think_grace_timeout_seconds"]) {
    if (!Number.isInteger(config[key]) || config[key] <= 0) throw new Error(`Configuration field '${key}' must be a positive integer.`);
  }
  if (config.probe_url !== null && (typeof config.probe_url !== "string" || !config.probe_url)) throw new Error("Configuration field 'probe_url' must be null or a non-empty URL.");
  return { path, config };
}

function save(path, config) { writeFileSync(path, format(config), "utf8"); }

function modelMenu(config) {
  const mark = (slug) => slug === config.model ? " (current)" : "";
  return `Local-model worker selection\nCurrent: ${config.model}\n\n  1. qwen3.8${mark("qwen3.8")}\n  2. local-model-placeholder${mark("local-model-placeholder")}\n\nInvoke /localmodel-model 1, /localmodel-model 2, or /localmodel-model <Pi model slug>.`;
}

function main() {
  const args = argsFrom(process.argv.slice(2));
  if (!args.command || args.command === "--help" || args.command === "help") { process.stdout.write(`${usage()}\n`); return; }
  if (args.command === "init") {
    const path = configPath(args.workspace);
    if (existsSync(path) && !args.force) throw new Error(`Configuration already exists. Re-run with --force to replace it.\nPath: ${path}`);
    mkdirSync(resolve(args.workspace, "harness", "orchestrate-localmodel-workflow"), { recursive: true });
    save(path, DEFAULTS);
    process.stdout.write(`Local-model workflow config initialized\nPath: ${path}\nRelative: ${RELATIVE_PATH.replaceAll("\\", "/")}\nModel: ${DEFAULTS.model}\nIdle timeout: ${DEFAULTS.idle_timeout_seconds} seconds\nThink-grace timeout: ${DEFAULTS.think_grace_timeout_seconds} seconds\n`);
    return;
  }
  const { path, config } = load(args.workspace);
  if (args.command === "show") {
    process.stdout.write(`Local-model workflow config\nPath: ${path}\nModel: ${config.model}\nIdle timeout: ${config.idle_timeout_seconds} seconds\nThink-grace timeout: ${config.think_grace_timeout_seconds} seconds\nProbe URL: ${config.probe_url ?? "Pi default"}\n`);
    return;
  }
  if (args.command === "model") {
    if (!args.model) { process.stdout.write(`${modelMenu(config)}\n`); return; }
    const model = MODELS[args.model.trim()] || args.model.trim();
    if (!/^[A-Za-z0-9._:/-]+$/u.test(model)) throw new Error("Model slug may contain letters, numbers, dots, underscores, colons, slashes, and hyphens only.");
    save(path, { ...config, model });
    process.stdout.write(`Local-model worker model is now: ${model}\nConfig path: ${path}\n`);
    return;
  }
  if (args.command === "timeout") {
    if (!args.timeout) {
      process.stdout.write(`Local-model supervision timeouts\nIdle: ${config.idle_timeout_seconds} seconds\nThink grace: ${config.think_grace_timeout_seconds} seconds\n\nUse /localmodel-timeout idle <seconds|default> or /localmodel-timeout think <seconds|default>.\nDefaults: idle ${DEFAULTS.idle_timeout_seconds}s; think ${DEFAULTS.think_grace_timeout_seconds}s.\nConfig path: ${path}\n`);
      return;
    }
    const [kind, value] = args.timeout;
    const field = kind === "idle" ? "idle_timeout_seconds" : kind === "think" ? "think_grace_timeout_seconds" : null;
    if (!field) throw new Error("Timeout kind must be 'idle' or 'think'.");
    const seconds = value === "default" ? DEFAULTS[field] : Number(value);
    if (!Number.isInteger(seconds) || seconds <= 0) throw new Error("Timeout must be a positive whole number of seconds, or 'default'.");
    save(path, { ...config, [field]: seconds });
    process.stdout.write(`${kind === "idle" ? "Idle" : "Think-grace"} timeout is now: ${seconds} seconds\nConfig path: ${path}\n`);
    return;
  }
  throw new Error(`Unknown command: ${args.command}\n${usage()}`);
}

try { main(); } catch (error) { process.stderr.write(`${error.message}\n`); process.exitCode = 1; }
