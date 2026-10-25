#!/usr/bin/env node
/**
 * Antigravity Sidecar Server for ZCode Subagent Visualizer
 * Serves /ui.html and /api/sessions by dynamically scanning ~/.gemini/antigravity/brain/
 */
const http = require("node:http");
const path = require("node:path");
const { pathToFileURL } = require("node:url");

const os = require("node:os");
const fs = require("node:fs");
const PORT = Number(process.env.PORT || process.env.SIDECAR_PORT || 0);
const BRAIN_DIR = process.env.ANTIGRAVITY_BRAIN_DIR || path.join(os.homedir(), ".gemini/antigravity/brain");

function resolveBuilderPath() {
  const candidates = [
    path.resolve(__dirname, "../../scripts/zcode_subagent_viz_builder.mjs"),
    path.resolve(__dirname, "../../../scripts/zcode_subagent_viz_builder.mjs"),
    path.resolve(__dirname, "../../skills/ai-agent-zcode-subagent-viz/scripts/zcode_subagent_viz_builder.mjs"),
  ];
  for (const c of candidates) {
    if (fs.existsSync(c)) return c;
  }
  return candidates[0];
}
const BUILDER_PATH = resolveBuilderPath();

let builderModPromise = null;
function getBuilder() {
  if (!builderModPromise) {
    builderModPromise = import(pathToFileURL(BUILDER_PATH).href);
  }
  return builderModPromise;
}

const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url || "/", "http://127.0.0.1");
    if (url.pathname === "/healthz") {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ status: "ok" }));
      return;
    }
    const mod = await getBuilder();
    const conv = url.searchParams.get("conv") || "";
    let sessions = mod.scanBrainSessions(BRAIN_DIR, conv);
    if (!sessions || sessions.length === 0) {
      sessions = mod.getDemoSessions();
    }

    if (url.pathname === "/api/sessions") {
      res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
      res.end(JSON.stringify({ sessions }));
      return;
    }

    // Default: serve interactive ZCode Subagent Visualizer HTML
    const html = mod.buildHTML(sessions, "full");
    res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
    res.end(html);
  } catch (err) {
    res.writeHead(500, { "Content-Type": "text/plain; charset=utf-8" });
    res.end("Sidecar Error: " + (err && err.stack ? err.stack : String(err)));
  }
});

server.listen(PORT, "127.0.0.1", () => {
  const addr = server.address();
  const actualPort = typeof addr === "object" && addr ? addr.port : PORT;
  console.log(JSON.stringify({ type: "sidecar_ready", port: actualPort }));
});
