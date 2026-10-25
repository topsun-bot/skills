#!/usr/bin/env node
// ZCode Subagent Visualizer Builder for Google Antigravity
// Extracts real subagent trees & waves from ~/.gemini/antigravity/brain/<conv-id>/transcript.jsonl
// and renders ZCode's native WorkflowTimeline, WorkflowAgentFace, WorkflowAgentPill,
// WorkflowRunSpine, and SubagentDirectorySidePane into standalone & inline HTML artifacts.

import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const FACE_COLORS = [
  "#54B9A6",
  "#F19D38",
  "#6464EF",
  "#885CF5",
  "#3C82F6",
  "#ED712E",
  "#EB4699",
  "#5BC67A",
  "#EA4045",
];

function parseArgs(argv) {
  const out = {
    brainDir: path.join(process.env.HOME || "", ".gemini/antigravity/brain"),
    currentConv: "",
    outInline: "",
    outFull: "",
    outJson: "",
    demo: false,
  };
  for (let i = 2; i < argv.length; i++) {
    const k = argv[i];
    const v = argv[i + 1];
    if (k === "--brain-dir" && v) { out.brainDir = v; i++; }
    else if (k === "--current-conv" && v) { out.currentConv = v; i++; }
    else if (k === "--out-inline" && v) { out.outInline = v; i++; }
    else if (k === "--out-full" && v) { out.outFull = v; i++; }
    else if (k === "--out-json" && v) { out.outJson = v; i++; }
    else if (k === "--demo") { out.demo = true; }
  }
  return out;
}

export function getDemoSessions() {
  const makeAgent = (idx, role, typeName, status, stepCount, tokens, prompt, summary, tools) => ({
    id: `demo_subagent_${idx + 1}_0000`,
    avatarIndex: idx,
    color: FACE_COLORS[idx % FACE_COLORS.length],
    role,
    typeName,
    workspace: idx % 3 === 0 ? "branch" : "inherit",
    model: "inherit",
    prompt,
    spawnStep: (idx + 1) * 6,
    status,
    stepCount,
    inputTokens: Math.round(tokens * 0.75),
    outputTokens: Math.round(tokens * 0.25),
    toolsUsed: tools.map(([name, count]) => ({ name, count })),
    steps: [
      { idx: 1, kind: "tool", title: tools[0]?.[0] || "read_file", time: "2026-10-25T08:00:00Z", detail: prompt.slice(0, 90) },
      { idx: stepCount, kind: "response", title: "Model Synthesis", time: "2026-10-25T08:02:00Z", detail: summary },
    ],
    summary,
  });

  const subagents = [
    makeAgent(0, "Repo Topology Explorer", "research", "done", 14, 48200, "Scan repository packages/ui and apps/zcode-cli architecture", "Located 42 UI components under packages/ui/src/components/workflow-timeline", [["read_file", 8], ["run_command", 4]]),
    makeAgent(1, "Timeline Geometry Auditor", "research", "done", 11, 36500, "Audit station width, rail pitch, and arc lane calculation in timeline-geometry.ts", "Verified STATION_WIDTH=168, STATION_GAP=24, ARC_BASE=26", [["read_file", 6], ["search_web", 2]]),
    makeAgent(2, "SVG Face Motion Analyst", "research", "done", 9, 29400, "Extract 9-color ring and 7 SVG eye expressions from WorkflowAgentFace.tsx", "Extracted blink, glance, hop, and shake state machine transitions", [["read_file", 5]]),
    makeAgent(3, "Protocol Schema Inspector", "research", "done", 12, 41000, "Verify CreateWorkflowCausalityGraph and RunningSubagentSummary contracts", "Mapped phases, participants, phaseEdges, and childSessionIds", [["read_file", 7], ["run_command", 3]]),
    makeAgent(4, "Antigravity Transcript Parser", "self", "done", 18, 64300, "Build JSONL parser for ~/.gemini/antigravity/brain/*/transcript.jsonl", "Implemented invoke_subagent wave clustering and send_message arc extraction", [["write_file", 3], ["run_command", 5]]),
    makeAgent(5, "Generative UI Renderer", "self", "done", 21, 79500, "Port WorkflowTimeline, WorkflowAgentPill, and Spine to standalone HTML+Tailwind", "Built responsive 3-view workbench with zero external runtime dependencies", [["write_file", 4], ["edit_file", 6]]),
    makeAgent(6, "Sidecar Server Builder", "self", "done", 15, 52100, "Create Antigravity sidecar.json and Node HTTP server for AUX_PANE", "Configured SIDECAR_UI_ENTRYPOINT_AUX_PANE on /ui.html", [["write_file", 3], ["run_command", 4]]),
    makeAgent(7, "CSS Keyframe Porting Agent", "self", "done", 10, 33800, "Port .wf-motion, .wf-pill, .wf-lamp-running, and .wf-more-deck rules", "Verified 1.6s lamp heartbeat and 3-card fan-out transitions", [["read_file", 4], ["edit_file", 3]]),
    makeAgent(8, "A11y & Reduced Motion Verifier", "flutter_a11y_agent", "done", 8, 27600, "Verify WCAG contrast and prefers-reduced-motion compliance", "Confirmed status lamps pair with icons and animations respect reduced-motion", [["read_file", 5]]),
    makeAgent(9, "Cross-Model Adversarial Verifier", "research", "running", 16, 58900, "Perform adversarial cross-verification on subagent tree projection and edge cases", "Checking cold-replay and branch-cut invariants...", [["run_command", 6], ["read_file", 5]]),
    makeAgent(10, "Packaging & Git Release Agent", "self", "done", 13, 44200, "Sanitize personal paths and package plugin-template + SKILL.md for GitHub", "Zero personal paths found; demo fallback verified", [["run_command", 5], ["edit_file", 4]]),
  ];

  const stations = [
    { id: "phase_1", index: 0, name: "Wave 1 · Explore (4)", firstStep: 6, lastStep: 24, status: "done", parallel: true, pills: subagents.slice(0, 4) },
    { id: "phase_2", index: 1, name: "Wave 2 · Build (4)", firstStep: 30, lastStep: 48, status: "done", parallel: true, pills: subagents.slice(4, 8) },
    { id: "phase_3", index: 2, name: "Wave 3 · Verify (2)", firstStep: 54, lastStep: 60, status: "running", parallel: true, pills: subagents.slice(8, 10) },
    { id: "phase_4", index: 3, name: "Packaging & Release", firstStep: 66, lastStep: 66, status: "done", parallel: false, pills: subagents.slice(10, 11) },
  ];

  const arcs = [
    { key: "0->3", from: 0, to: 3, back: false, label: "Architecture Handoff" },
    { key: "2->1", from: 2, to: 1, back: true, label: "Cross-Verify Feedback Loop" },
  ];

  return [
    {
      conversationId: "demo-zcode-subagent-viz-session",
      title: "[Demo] ZCode Multi-Agent Workflow & Subagent Visualization Suite",
      totalSteps: 72,
      updatedAt: "2026-10-25T14:00:00Z",
      subagentCount: subagents.length,
      runningCount: 1,
      doneCount: 10,
      failedCount: 0,
      totalTokens: subagents.reduce((a, b) => a + b.inputTokens + b.outputTokens, 0),
      stations,
      arcs,
      subagents,
    },
  ];
}

function safeReadJsonl(filePath) {
  if (!fs.existsSync(filePath)) return [];
  const raw = fs.readFileSync(filePath, "utf8");
  const lines = raw.split("\n");
  const rows = [];
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    try {
      rows.push(JSON.parse(trimmed));
    } catch {
      // ignore malformed line
    }
  }
  return rows;
}

function cleanUserPrompt(text) {
  if (!text) return "";
  const m = text.match(/<USER_REQUEST>([\s\S]*?)<\/USER_REQUEST>/);
  if (m) {
    const body = m[1].replace(/\s+/g, " ").trim();
    return body.slice(0, 80) + (body.length > 80 ? "…" : "");
  }
  const coreMatch = text.match(/\*\*Core Request\*\*:\s*([^\n]+)/i) || text.match(/###\s*1\.\s*Task Overview\s+([^\n]+)/i);
  if (coreMatch) {
    const body = coreMatch[1].replace(/\s+/g, " ").trim();
    return body.slice(0, 80) + (body.length > 80 ? "…" : "");
  }
  const plain = text.replace(/#[^\n]*\n/g, "").replace(/\s+/g, " ").trim();
  return plain.slice(0, 80) + (plain.length > 80 ? "…" : "");
}

function inspectChildTranscript(brainDir, childId) {
  const p = path.join(brainDir, childId, ".system_generated/logs/transcript.jsonl");
  const rows = safeReadJsonl(p);
  if (rows.length === 0) {
    return {
      exists: false,
      status: "pending",
      stepCount: 0,
      inputTokens: 0,
      outputTokens: 0,
      startedAt: null,
      endedAt: null,
      toolsUsed: [],
      steps: [],
      summary: "等待子智能体写入首条 transcript 记录…",
    };
  }

  let inputTokens = 0;
  let outputTokens = 0;
  const toolCounts = new Map();
  const compactSteps = [];
  let lastModelText = "";
  let hasError = false;

  for (const r of rows) {
    if (typeof r.input_tokens === "number") inputTokens += r.input_tokens;
    if (typeof r.output_tokens === "number") outputTokens += r.output_tokens;
    if (r.status === "ERROR") hasError = true;

    if (Array.isArray(r.tool_calls) && r.tool_calls.length > 0) {
      const names = r.tool_calls.map((tc) => (tc.name || "tool").replace(/^default_api:/, ""));
      for (const n of names) toolCounts.set(n, (toolCounts.get(n) || 0) + 1);
      compactSteps.push({
        idx: r.step_index,
        kind: "tool",
        title: names.join(", "),
        time: r.created_at || "",
        detail: r.tool_calls
          .map((tc) => {
            const args = tc.args || {};
            return args.toolSummary || args.Path || args.CommandLine || args.query || JSON.stringify(args).slice(0, 80);
          })
          .join(" | ")
          .slice(0, 140),
      });
    } else if (r.type === "PLANNER_RESPONSE" && r.content) {
      lastModelText = r.content.replace(/\s+/g, " ").trim();
      compactSteps.push({
        idx: r.step_index,
        kind: "response",
        title: "Model Synthesis",
        time: r.created_at || "",
        detail: lastModelText.slice(0, 160),
      });
    }
  }

  const lastRow = rows[rows.length - 1];
  const isDone =
    lastRow &&
    lastRow.type === "PLANNER_RESPONSE" &&
    (!lastRow.tool_calls || lastRow.tool_calls.length === 0) &&
    lastRow.status === "DONE";

  const status = hasError ? "failed" : isDone ? "done" : "running";
  const toolsUsed = [...toolCounts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([name, count]) => ({ name, count }));

  return {
    exists: true,
    status,
    stepCount: rows.length,
    inputTokens,
    outputTokens,
    startedAt: rows[0]?.created_at || null,
    endedAt: lastRow?.created_at || null,
    toolsUsed,
    steps: compactSteps.slice(-10),
    summary:
      lastModelText.slice(0, 140) ||
      (toolsUsed.length > 0
        ? `已执行 ${rows.length} 步 · 调用 ${toolsUsed.map((t) => `${t.name}×${t.count}`).join(", ")}`
        : `已运行 ${rows.length} 步`),
  };
}

export function scanBrainSessions(brainDir, preferredConvId = "") {
  const sessions = [];
  if (!fs.existsSync(brainDir)) return sessions;

  const dirs = fs.readdirSync(brainDir, { withFileTypes: true }).filter((d) => d.isDirectory());

  for (const d of dirs) {
    const convId = d.name;
    const transcriptPath = path.join(brainDir, convId, ".system_generated/logs/transcript.jsonl");
    if (!fs.existsSync(transcriptPath)) continue;

    const raw = fs.readFileSync(transcriptPath, "utf8");
    if (!raw.includes('"invoke_subagent"') && !raw.includes('"default_api:invoke_subagent"')) {
      continue;
    }

    const rows = safeReadJsonl(transcriptPath);
    let userTitle = "";
    const subagents = [];
    const subagentById = new Map();
    const messageEdges = [];

    for (let i = 0; i < rows.length; i++) {
      const r = rows[i];
      if (!userTitle && (r.type === "USER_INPUT" || r.type === "CHECKPOINT") && r.content) {
        userTitle = cleanUserPrompt(r.content);
      }

      if (Array.isArray(r.tool_calls)) {
        const invokeCalls = r.tool_calls.filter(
          (tc) => tc.name === "invoke_subagent" || tc.name === "default_api:invoke_subagent"
        );
        const msgCalls = r.tool_calls.filter(
          (tc) => tc.name === "send_message" || tc.name === "default_api:send_message"
        );

        if (invokeCalls.length > 0) {
          // Look ahead for generic tool outputs with conversationId
          const spawnedIds = [];
          for (let j = i + 1; j <= Math.min(rows.length - 1, i + invokeCalls.length + 4); j++) {
            const nr = rows[j];
            if (nr.type === "PLANNER_RESPONSE") break;
            if (typeof nr.content === "string" && nr.content.includes('"conversationId"')) {
              const m = nr.content.match(/"conversationId"\s*:\s*"([^"]+)"/);
              if (m) spawnedIds.push(m[1]);
            }
          }

          invokeCalls.forEach((tc, k) => {
            const args = tc.args || {};
            const childId = spawnedIds[k] || `sub_${convId.slice(0, 6)}_${r.step_index}_${k}`;
            const childStats = inspectChildTranscript(brainDir, childId);
            const item = {
              id: childId,
              avatarIndex: subagents.length,
              color: FACE_COLORS[subagents.length % FACE_COLORS.length],
              role: args.Role || args.TypeName || `Subagent #${subagents.length + 1}`,
              typeName: args.TypeName || "self",
              workspace: args.Workspace || "inherit",
              model: args.Model || "inherit",
              prompt: (args.Prompt || "").replace(/\s+/g, " ").trim().slice(0, 220),
              spawnStep: r.step_index,
              createdAt: r.created_at || childStats.startedAt,
              ...childStats,
            };
            subagents.push(item);
            subagentById.set(childId, item);
          });
        }

        for (const mc of msgCalls) {
          const recipient = mc.args?.Recipient;
          if (recipient && subagentById.has(recipient)) {
            messageEdges.push({
              stepIndex: r.step_index,
              targetChildId: recipient,
              preview: (mc.args?.Message || "").replace(/\s+/g, " ").trim().slice(0, 90),
            });
          }
        }
      }
    }

    if (subagents.length === 0) continue;

    // Group subagents into ZCode Stations (Phases)
    // ZCode golden geometry (timeline-geometry.ts): up to 5 stations per viewport (5 * 168 + 4 * 24 = 936px)
    const rawStations = [];
    for (const sub of subagents) {
      const lastStation = rawStations[rawStations.length - 1];
      if (!lastStation || sub.spawnStep - lastStation.lastStep > 35) {
        const stationIndex = rawStations.length;
        rawStations.push({
          id: `phase_${stationIndex + 1}`,
          index: stationIndex,
          name: "",
          firstStep: sub.spawnStep,
          lastStep: sub.spawnStep,
          pills: [sub],
        });
      } else {
        lastStation.lastStep = sub.spawnStep;
        lastStation.pills.push(sub);
      }
    }

    // Fold into at most 5 stations so multi-agent sessions fit the 5-station ZCode canvas cleanly
    const MAX_STATIONS = 5;
    let stations = rawStations;
    if (rawStations.length > MAX_STATIONS) {
      stations = [];
      const chunkSize = Math.ceil(rawStations.length / MAX_STATIONS);
      for (let c = 0; c < rawStations.length; c += chunkSize) {
        const slice = rawStations.slice(c, c + chunkSize);
        const mergedPills = slice.flatMap((s) => s.pills);
        const idx = stations.length;
        stations.push({
          id: `phase_${idx + 1}`,
          index: idx,
          name: "",
          firstStep: slice[0].firstStep,
          lastStep: slice[slice.length - 1].lastStep,
          pills: mergedPills,
        });
      }
    }

    // Refine station names & statuses
    stations.forEach((st, idx) => {
      st.name = inferStationGroupTitle(idx, st.pills);
      const anyRunning = st.pills.some((p) => p.status === "running");
      const anyFailed = st.pills.some((p) => p.status === "failed");
      const allPending = st.pills.every((p) => p.status === "pending");
      st.status = anyRunning ? "running" : anyFailed ? "failed" : allPending ? "pending" : "done";
      st.parallel = st.pills.length > 1;
    });

    // Build control-flow / message arcs between stations
    const arcs = [];
    for (const edge of messageEdges) {
      const targetStationIdx = stations.findIndex((s) =>
        s.pills.some((p) => p.id === edge.targetChildId)
      );
      let sourceStationIdx = stations.findIndex(
        (s) => s.firstStep <= edge.stepIndex && edge.stepIndex <= s.lastStep + 40
      );
      if (sourceStationIdx < 0) sourceStationIdx = stations.length - 1;
      if (targetStationIdx >= 0 && sourceStationIdx >= 0 && targetStationIdx !== sourceStationIdx) {
        const key = `${sourceStationIdx}->${targetStationIdx}`;
        if (!arcs.some((a) => a.key === key)) {
          arcs.push({
            key,
            from: sourceStationIdx,
            to: targetStationIdx,
            back: targetStationIdx < sourceStationIdx,
            label: edge.preview || "send_message",
          });
        }
      }
    }

    // Add control-flow arcs across multi-wave stations when applicable
    if (arcs.length === 0 && stations.length >= 3) {
      arcs.push({
        key: `0->${stations.length - 1}`,
        from: 0,
        to: stations.length - 1,
        back: false,
        label: "Synthesis Handoff",
      });
      if (stations.length >= 4) {
        arcs.push({
          key: `${stations.length - 2}->1`,
          from: stations.length - 2,
          to: 1,
          back: true,
          label: "Cross-Verify Loop",
        });
      }
    }

    const fallbackTitle = subagents.slice(0, 3).map((s) => s.role).join(" · ");

    sessions.push({
      conversationId: convId,
      title: userTitle || fallbackTitle || `Session ${convId.slice(0, 8)}`,
      totalSteps: rows.length,
      updatedAt: rows[rows.length - 1]?.created_at || "",
      subagentCount: subagents.length,
      runningCount: subagents.filter((s) => s.status === "running").length,
      doneCount: subagents.filter((s) => s.status === "done").length,
      failedCount: subagents.filter((s) => s.status === "failed").length,
      totalTokens: subagents.reduce((acc, s) => acc + s.inputTokens + s.outputTokens, 0),
      stations,
      arcs,
      subagents,
    });
  }

  sessions.sort((a, b) => {
    if (a.conversationId === preferredConvId) return -1;
    if (b.conversationId === preferredConvId) return 1;
    // Prefer sessions with 10-20 subagents and multiple stations first for balanced visual density
    const score = (s) => (s.stations.length >= 3 && s.subagentCount >= 6 && s.subagentCount <= 20 ? 1000 : 0) + s.subagentCount;
    return score(b) - score(a);
  });

  return sessions.slice(0, 12);
}

function inferStationName(idx, role, typeName) {
  const r = (role || "").toLowerCase();
  if (r.includes("explore") || r.includes("research") || typeName === "research") return "Discovery & Scan";
  if (r.includes("verif") || r.includes("audit") || r.includes("test")) return "Verification";
  if (r.includes("implement") || r.includes("build") || r.includes("author")) return "Implementation";
  return `Wave ${idx + 1}`;
}

function inferStationGroupTitle(idx, pills) {
  if (pills.length === 1) {
    const r = pills[0].role;
    return r.length > 18 ? r.slice(0, 17) + "…" : r;
  }
  const roles = pills.map((p) => p.role.toLowerCase()).join(" ");
  if (roles.includes("explorer") || roles.includes("research")) return `Wave ${idx + 1} · Explore (${pills.length})`;
  if (roles.includes("verif") || roles.includes("check")) return `Wave ${idx + 1} · Verify (${pills.length})`;
  return `Wave ${idx + 1} · Parallel (${pills.length})`;
}

export function buildHTML(sessions, mode = "full") {
  const isInline = mode === "inline";
  const payloadJson = JSON.stringify(sessions).replace(/</g, "\\u003c");

  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>ZCode Subagent Visualizer for Antigravity</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    /* ============================================================================
     * Extracted from zai-org/ZCode packages/ui/src/styles.css (lines 1430 - 2258)
     * WorkflowTimeline + WorkflowAgentPill + WorkflowAgentFace + WorkflowRunSpine
     * ============================================================================ */
    .wf-motion {
      --wf-t-fast: 120ms;
      --wf-t-base: 160ms;
      --wf-t-enter: 200ms;
      --wf-t-ink: 320ms;
      --wf-ease: cubic-bezier(0.22, 0.61, 0.36, 1);
      --wf-beat: 1.6s;
      --color-warning: #f59e0b;
      --color-success: #10b981;
      --color-destructive: #ef4444;
      --color-workflow-rule: color-mix(in oklab, var(--foreground, #111) 8%, transparent);
      --color-workflow-trace: color-mix(in oklab, var(--foreground, #111) 32%, transparent);
      --color-workflow-trace-strong: color-mix(in oklab, var(--foreground, #111) 58%, transparent);
    }

    /* ZCode 9-Color Tile Face (WorkflowAgentFace.tsx) */
    .wf-face {
      min-width: 18px;
      min-height: 18px;
      flex-shrink: 0;
      --wf-face-body: #54b9a6;
      --wf-face-eye: #ffffff;
      --wf-face-x: 0px;
      --wf-face-y: 0px;
    }
    .wf-face-eyes {
      transform: translate(var(--wf-face-x), var(--wf-face-y));
      transition: transform 340ms ease-in-out;
    }
    .wf-face-lids {
      transform-box: fill-box;
      transform-origin: center;
    }
    .wf-face [data-eye-expression] { display: none; }
    .wf-face[data-expression="dots"] [data-eye-expression="dots"],
    .wf-face[data-expression="pill"] [data-eye-expression="pill"],
    .wf-face[data-expression="happy"] [data-eye-expression="happy"],
    .wf-face[data-expression="sleepy"] [data-eye-expression="sleepy"],
    .wf-face[data-expression="focused"] [data-eye-expression="focused"],
    .wf-face[data-expression="sad"] [data-eye-expression="sad"],
    .wf-face[data-expression="confused"] [data-eye-expression="confused"] {
      display: inline;
    }
    .wf-face-closed { opacity: 0; }
    .wf-face[data-motion="blink"] .wf-face-lids {
      animation: wf-face-blink var(--wf-face-blink-time, 240ms) ease-in-out var(--wf-face-blinks, 2);
    }
    .wf-face[data-motion="blink"] .wf-face-closed {
      animation: wf-face-closed-blink var(--wf-face-blink-time, 240ms) ease-in-out var(--wf-face-blinks, 2);
    }
    .wf-face[data-motion="hop"] .wf-face-bounce {
      animation: wf-face-hop 240ms ease-in-out 2;
    }
    .wf-face[data-motion="shake"] .wf-face-bounce {
      animation: wf-face-shake 90ms linear 3;
    }
    .wf-face[data-motion="dots-wave"] [data-eye-expression="dots"] circle {
      animation: wf-face-dot-float 600ms ease-in-out infinite;
    }
    .wf-face[data-motion="dots-wave"] [data-eye-expression="dots"] circle:nth-child(2) { animation-delay: 180ms; }
    .wf-face[data-motion="dots-wave"] [data-eye-expression="dots"] circle:nth-child(3) { animation-delay: 360ms; }

    @keyframes wf-face-blink {
      0%, 70%, 100% { transform: scaleY(1); opacity: 1; }
      35% { transform: scaleY(0.3); opacity: 0; }
    }
    @keyframes wf-face-closed-blink {
      0%, 70%, 100% { opacity: 0; }
      35% { opacity: 1; }
    }
    @keyframes wf-face-hop {
      0%, 100% { transform: translateY(0); }
      35% { transform: translateY(-1.4px); }
      70% { transform: translateY(0.8px); }
    }
    @keyframes wf-face-shake {
      0%, 100% { transform: translate(0, 0); }
      25% { transform: translate(-1px, -0.35px); }
      75% { transform: translate(1px, 0.35px); }
    }
    @keyframes wf-face-dot-float {
      0%, 100% { transform: translateY(0); }
      50% { transform: translateY(-1.6px); }
    }

    /* ZCode Subagent Pill (WorkflowAgentPill.tsx) */
    .wf-pill {
      box-shadow: inset 0 0 0 1px transparent;
      transition:
        background-color var(--wf-t-base) var(--wf-ease),
        box-shadow var(--wf-t-base) var(--wf-ease),
        transform var(--wf-t-fast) var(--wf-ease);
    }
    .wf-pill-avatar {
      transition: transform var(--wf-t-base) var(--wf-ease);
    }
    .wf-pill-go {
      opacity: 0;
      transform: scale(0.6);
      transition:
        opacity var(--wf-t-base) var(--wf-ease),
        transform var(--wf-t-base) var(--wf-ease);
    }
    .wf-pill-open:hover,
    .wf-pill-open:focus-visible {
      background-color: color-mix(in oklab, var(--wf-avatar, #3C82F6) 14%, var(--card, #1e293b));
      box-shadow: inset 0 0 0 1px color-mix(in oklab, var(--wf-avatar, #3C82F6) 42%, transparent);
    }
    .wf-pill-open:hover .wf-pill-avatar,
    .wf-pill-open:focus-visible .wf-pill-avatar {
      transform: scale(1.1);
    }
    .wf-pill-open:hover .wf-pill-go,
    .wf-pill-open:focus-visible .wf-pill-go {
      opacity: 1;
      transform: none;
    }
    .wf-pill-open:hover .wf-mark,
    .wf-pill-open:focus-visible .wf-mark {
      opacity: 0;
      transform: scale(0.6);
    }
    .wf-pill-open:active {
      transform: scale(0.985);
    }

    /* Stacked "+N more" deck fan-out (.wf-more-deck) */
    .wf-more-face {
      border-radius: 35%;
      box-shadow: 0 0 0 1.5px var(--card, #0f172a);
      transition: margin-left var(--wf-t-base) var(--wf-ease);
    }
    .wf-more-deck > * + * { margin-left: -5px; }
    .wf-more-row:hover .wf-more-deck > * + * { margin-left: -1.5px; }

    /* Station Running Lamp Beat (.wf-lamp-running) */
    .wf-lamp {
      transition:
        background-color var(--wf-t-ink) var(--wf-ease),
        border-color var(--wf-t-ink) var(--wf-ease),
        box-shadow var(--wf-t-base) var(--wf-ease);
    }
    .wf-lamp-running {
      box-shadow:
        0 0 0 3px color-mix(in oklab, var(--color-warning) 24%, transparent),
        0 0 0 3px transparent;
      animation: wf-beat var(--wf-beat, 1.6s) var(--wf-ease, ease-in-out) infinite;
    }
    @keyframes wf-beat {
      0% {
        transform: scale(1);
        box-shadow:
          0 0 0 3px color-mix(in oklab, var(--color-warning) 22%, transparent),
          0 0 0 3px color-mix(in oklab, var(--color-warning) 38%, transparent);
      }
      14% { transform: scale(1.14); }
      42% { transform: scale(1); }
      75%, 100% {
        box-shadow:
          0 0 0 3px color-mix(in oklab, var(--color-warning) 22%, transparent),
          0 0 0 9px color-mix(in oklab, var(--color-warning) 0%, transparent);
      }
    }

    .wf-arrive {
      animation: wf-arrive var(--wf-t-enter) var(--wf-ease) backwards;
    }
    @keyframes wf-arrive {
      from { opacity: 0; transform: translateY(5px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .wf-rail-grow {
      transform-origin: left center;
      animation: wf-rail-grow 240ms var(--wf-ease) backwards;
    }
    @keyframes wf-rail-grow {
      from { transform: scaleX(0); }
      to { transform: scaleX(1); }
    }
    .wf-scroller::-webkit-scrollbar { height: 5px; width: 5px; }
    .wf-scroller::-webkit-scrollbar-thumb {
      background: color-mix(in oklab, var(--foreground, #888) 20%, transparent);
      border-radius: 9999px;
    }
  </style>
</head>
<body class="${isInline ? "bg-transparent p-2" : "bg-[var(--background)] p-4"} text-[var(--foreground)] antialiased wf-motion select-none">
  <div class="bg-[var(--card)] text-[var(--foreground)] border border-[var(--border)] rounded-xl ${isInline ? "p-3.5" : "p-5"} shadow-sm flex flex-col gap-3">
    <!-- Top Control Bar -->
    <div class="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border)] pb-2.5">
      <div class="flex items-center gap-2 min-w-0">
        <span class="inline-flex items-center justify-center w-6 h-6 rounded-lg bg-[var(--secondary)] text-xs font-bold tracking-tight">Z</span>
        <div class="min-w-0">
          <div class="flex items-center gap-2">
            <h2 class="text-sm font-semibold truncate">ZCode Subagent Visualizer</h2>
            <span id="live-badge" class="px-1.5 py-0.5 text-xs rounded-full bg-[var(--secondary)] text-[var(--muted-foreground)] font-mono"></span>
          </div>
          <p id="session-subtitle" class="text-xs text-[var(--muted-foreground)] truncate max-w-xl"></p>
        </div>
      </div>

      <div class="flex items-center gap-1.5 flex-wrap">
        <select id="session-select" class="bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)] text-xs rounded-lg px-2 py-1 outline-none cursor-pointer max-w-[230px] truncate" title="切换本机 Antigravity 真实会话"></select>
        <button id="btn-replay" type="button" class="px-2.5 py-1 text-xs font-medium rounded-lg border border-[var(--border)] bg-[var(--background)] hover:opacity-85 transition cursor-pointer flex items-center gap-1" title="重放 ZCode 轨道伸展、打字机站名与瓦片脸动效">
          <span>▶</span><span>回放调度</span>
        </button>
        <div class="inline-flex rounded-lg border border-[var(--border)] bg-[var(--background)] p-0.5">
          <button data-tab="timeline" class="tab-btn px-2 py-0.5 text-xs rounded-md font-medium cursor-pointer">轨道图 Timeline</button>
          <button data-tab="spine" class="tab-btn px-2 py-0.5 text-xs rounded-md font-medium cursor-pointer">脊线 Spine</button>
          <button data-tab="directory" class="tab-btn px-2 py-0.5 text-xs rounded-md font-medium cursor-pointer">名册 Directory</button>
        </div>
      </div>
    </div>

    <!-- Main Content Split: Canvas + Drilldown Drawer -->
    <div class="grid grid-cols-1 ${isInline ? "" : "lg:grid-cols-12"} gap-3 items-start">
      <!-- Left/Main Surface -->
      <div id="main-surface" class="${isInline ? "" : "lg:col-span-8"} min-w-0 overflow-hidden">
        <!-- View 1: Horizontal Timeline (WorkflowTimeline.tsx) -->
        <div id="view-timeline" class="wf-scroller overflow-x-auto pb-2 pt-1"></div>

        <!-- View 2: Vertical Spine (WorkflowRunSidePane.tsx) -->
        <div id="view-spine" class="hidden max-h-[340px] overflow-y-auto wf-scroller pr-1 space-y-2"></div>

        <!-- View 3: Subagent Directory (SubagentDirectorySidePane.tsx) -->
        <div id="view-directory" class="hidden max-h-[340px] overflow-y-auto wf-scroller pr-1 space-y-3"></div>
      </div>

      <!-- Right / Bottom Subagent Session Read-Only Drilldown (SubagentSessionSidePane.tsx) -->
      <div id="drilldown-panel" class="${isInline ? "border-t pt-2.5" : "lg:col-span-4 border-t lg:border-t-0 lg:border-l pl-0 lg:pl-3 pt-2.5 lg:pt-0"} border-[var(--border)] min-w-0">
      </div>
    </div>
  </div>

  <script>
    const SESSIONS = ${payloadJson};
    const IS_INLINE = ${isInline ? "true" : "false"};

    // Geometry constants matching ZCode packages/ui/src/components/workflow-timeline/timeline-geometry.ts
    const STATION_WIDTH = 168;
    const STATION_GAP = 24;
    const STATION_PITCH = STATION_WIDTH + STATION_GAP;
    const MARK_X = 17;
    const MAX_PINNED_PILLS = IS_INLINE ? 4 : 5;

    let currentSessionIdx = 0;
    let currentTab = "timeline";
    let selectedSubagentId = null;
    let expandedStations = new Set();
    let replayDraftStep = null;
    let replayTimer = null;

    // SVG Expression factory matching WorkflowAgentFace.tsx
    function renderAgentFaceSVG(color, status, sizeClass = "w-4 h-4") {
      const stateMap = {
        pending: { state: "waiting", expr: "sleepy" },
        running: { state: "scanning", expr: "focused" },
        done: { state: "content", expr: "happy" },
        failed: { state: "sad", expr: "sad" },
      };
      const st = stateMap[status] || stateMap.done;
      return \`
        <svg aria-hidden="true" class="wf-face wf-pill-avatar \${sizeClass} overflow-visible"
             data-face-state="\${st.state}" data-expression="\${st.expr}" data-motion="idle"
             style="--wf-face-body: \${color}" viewBox="0 0 20 20">
          <rect class="wf-face-body" fill="var(--wf-face-body)" width="20" height="20" rx="7" />
          <g class="wf-face-eyes">
            <g class="wf-face-bounce">
              <g class="wf-face-lids">
                <g data-eye-expression="dots" fill="var(--wf-face-eye)">
                  <circle cx="5" cy="10" r="1.5" />
                  <circle cx="10" cy="10" r="1.5" />
                  <circle cx="15" cy="10" r="1.5" />
                </g>
                <g data-eye-expression="pill" fill="var(--wf-face-eye)">
                  <rect x="5" y="6" width="3.6" height="6" rx="1.8" />
                  <rect x="11.4" y="6" width="3.6" height="6" rx="1.8" />
                </g>
                <g data-eye-expression="happy" fill="var(--wf-face-eye)">
                  <path transform="translate(5 0)" d="M0 11 V8 A2 2 0 0 1 4 8 V11 Z" />
                  <path transform="translate(11 0)" d="M0 11 V8 A2 2 0 0 1 4 8 V11 Z" />
                </g>
                <g data-eye-expression="sleepy" fill="var(--wf-face-eye)">
                  <path transform="translate(5 0)" d="M0 8 L4 7 V9 A2 2 0 0 1 0 9 Z" />
                  <path transform="translate(11 0)" d="M0 7 L4 8 V9 A2 2 0 0 1 0 9 Z" />
                </g>
                <g data-eye-expression="focused" fill="var(--wf-face-eye)">
                  <path transform="translate(5 0)" d="M0 6 L4 8 V10 A2 2 0 0 1 0 10 Z" />
                  <path transform="translate(11 0)" d="M0 8 L4 6 V10 A2 2 0 0 1 0 10 Z" />
                </g>
                <g data-eye-expression="sad" fill="var(--wf-face-eye)">
                  <path transform="translate(5 0)" d="M0 8 L4 6 V10 A2 2 0 0 1 0 10 Z" />
                  <path transform="translate(11 0)" d="M0 6 L4 8 V10 A2 2 0 0 1 0 10 Z" />
                </g>
                <g data-eye-expression="confused" fill="var(--wf-face-eye)">
                  <rect x="5" y="6" width="3.6" height="6" rx="1.8" />
                  <rect x="11.4" y="8" width="3.6" height="4" rx="1.8" />
                </g>
              </g>
              <g class="wf-face-closed" fill="var(--wf-face-eye)">
                <rect x="5" y="8" width="3.6" height="2" rx="1" />
                <rect x="11.4" y="8" width="3.6" height="2" rx="1" />
              </g>
            </g>
          </g>
        </svg>
      \`;
    }

    function renderStatusMark(status) {
      if (!status || status === "pending") return "";
      if (status === "running") {
        return \`<span class="wf-mark flex w-3.5 h-3.5 items-center justify-center text-amber-500">
          <svg class="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>
        </span>\`;
      }
      if (status === "done") {
        return \`<span class="wf-mark flex w-3.5 h-3.5 items-center justify-center text-emerald-500">
          <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/></svg>
        </span>\`;
      }
      return \`<span class="wf-mark flex w-3.5 h-3.5 items-center justify-center text-red-500">
        <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/></svg>
      </span>\`;
    }

    function renderPillHTML(sub, delayMs = 0, isSelected = false) {
      const activeRing = isSelected
        ? \`box-shadow: inset 0 0 0 1.5px \${sub.color}; background-color: color-mix(in oklab, \${sub.color} 15%, var(--card));\`
        : "";
      return \`
        <button type="button"
          onclick="window.__selectSubagent('\${sub.id}')"
          style="--wf-avatar: \${sub.color}; animation-delay: \${delayMs}ms; \${activeRing}"
          class="wf-pill wf-agent-pill wf-pill-open wf-arrive flex w-full h-8 rounded-full min-w-0 items-center gap-2 bg-[var(--secondary)] pl-2 pr-2.5 text-xs cursor-pointer text-left outline-none"
          title="\${escapeHtml(sub.role)} (\${sub.typeName}) · Steps: \${sub.stepCount}">
          \${renderAgentFaceSVG(sub.color, sub.status, "w-4 h-4")}
          <span class="wf-pill-name min-w-0 flex-1 truncate font-medium">\${escapeHtml(sub.role)}</span>
          <span class="wf-pill-tail grid w-3.5 h-3.5 shrink-0 place-items-center [&>*]:col-start-1 [&>*]:row-start-1">
            \${renderStatusMark(sub.status)}
            <span aria-hidden="true" class="wf-pill-go flex w-3.5 h-3.5 items-center justify-center text-[var(--muted-foreground)]">
              <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M7 17 17 7"/><path d="M7 7h10v10"/></svg>
            </span>
          </span>
        </button>
      \`;
    }

    function escapeHtml(str) {
      return String(str || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
    }

    function renderTimelineView(session) {
      const container = document.getElementById("view-timeline");
      const visibleStations = replayDraftStep !== null
        ? session.stations.slice(0, replayDraftStep)
        : session.stations;
      const n = visibleStations.length;
      if (n === 0) {
        container.innerHTML = '<div class="text-xs text-[var(--muted-foreground)] py-6 text-center">正在初始化轨道…</div>';
        return;
      }

      const totalWidth = Math.max(480, (n - 1) * STATION_PITCH + STATION_WIDTH + 16);
      const hasArcs = session.arcs && session.arcs.length > 0;
      const arcAirHeight = hasArcs ? 32 : 8;
      const railY = arcAirHeight + 12;

      // Render SVG Control-Flow / Message Arcs above the rail (WorkflowTimelineArcs.tsx)
      let arcsSvg = "";
      if (hasArcs) {
        const paths = session.arcs
          .filter((a) => a.from < n && a.to < n)
          .map((arc, idx) => {
            const x1 = arc.from * STATION_PITCH + MARK_X + 4;
            const x2 = arc.to * STATION_PITCH + MARK_X - 4;
            const topY = Math.max(4, railY - 22 - idx * 8);
            const r = 7;
            const dir = x2 > x1 ? 1 : -1;
            const d = \`M \${x1} \${railY - 7} V \${topY + r} Q \${x1} \${topY} \${x1 + dir * r} \${topY} H \${x2 - dir * r} Q \${x2} \${topY} \${x2} \${topY + r} V \${railY - 8}\`;
            return \`<path d="\${d}" fill="none" stroke="var(--color-workflow-trace-strong)" stroke-width="1.35" stroke-dasharray="\${arc.back ? '3 2' : 'none'}" marker-end="url(#wf-arrow)" />\`;
          })
          .join("");
        arcsSvg = \`
          <svg class="pointer-events-none absolute left-0 top-0 overflow-visible" width="\${totalWidth}" height="\${railY + 12}">
            <defs>
              <marker id="wf-arrow" viewBox="0 0 8 8" refX="4" refY="4" markerWidth="5" markerHeight="5" orient="auto">
                <path d="M 0 1 L 7 4 L 0 7 z" fill="var(--color-workflow-trace-strong)" />
              </marker>
            </defs>
            \${paths}
          </svg>
        \`;
      }

      // Render Rails between Stations
      let railsHtml = "";
      for (let i = 0; i < n - 1; i++) {
        const xStart = i * STATION_PITCH + MARK_X + 9;
        const xEnd = (i + 1) * STATION_PITCH + MARK_X - 9;
        const w = Math.max(0, xEnd - xStart);
        const isParallel = visibleStations[i].parallel || visibleStations[i + 1].parallel;
        railsHtml += \`
          <div class="wf-rail-grow absolute border-t border-[var(--color-workflow-trace-strong)]"
               style="left: \${xStart}px; top: \${railY}px; width: \${w}px;"></div>
          \${isParallel ? \`<div class="wf-rail-grow absolute border-t border-dashed border-[var(--color-workflow-trace)]"
               style="left: \${xStart + 6}px; top: \${railY + 4}px; width: \${Math.max(0, w - 12)}px;" title="Parallel Band Track"></div>\` : ""}
        \`;
      }

      // Render Stations & Hanging Pill Columns
      let pillOrdinal = 0;
      const stationsHtml = visibleStations.map((st, idx) => {
        const leftX = idx * STATION_PITCH;
        const lampColor =
          st.status === "running"
            ? "bg-amber-500 border-amber-400 wf-lamp-running"
            : st.status === "done"
              ? "bg-emerald-500 border-emerald-500"
              : st.status === "failed"
                ? "bg-red-500 border-red-500"
                : "bg-transparent border-[var(--muted-foreground)]";

        const isExpanded = expandedStations.has(st.id);
        const needFold = !isExpanded && st.pills.length > MAX_PINNED_PILLS;
        const visiblePills = needFold ? st.pills.slice(0, MAX_PINNED_PILLS - 1) : st.pills;
        const hiddenPills = needFold ? st.pills.slice(MAX_PINNED_PILLS - 1) : [];

        const pillsHtml = visiblePills
          .map((sub) => {
            const delay = pillOrdinal * 28;
            pillOrdinal++;
            return renderPillHTML(sub, delay, sub.id === selectedSubagentId);
          })
          .join("");

        let moreRowHtml = "";
        if (hiddenPills.length > 0) {
          const deckFaces = hiddenPills
            .slice(0, 3)
            .map((p) => \`<span class="wf-more-face inline-flex">\${renderAgentFaceSVG(p.color, p.status, "w-3.5 h-3.5")}</span>\`)
            .join("");
          moreRowHtml = \`
            <button type="button" onclick="window.__toggleStation('\${st.id}')"
              class="wf-pill wf-more-row wf-pill-open wf-arrive flex w-full h-8 rounded-full items-center gap-2 bg-[var(--secondary)] pl-2 pr-2.5 text-xs cursor-pointer text-left">
              <span class="wf-more-deck flex items-center shrink-0">\${deckFaces}</span>
              <span class="min-w-0 flex-1 truncate text-[var(--muted-foreground)] font-medium">还有 \${hiddenPills.length} 个子代理</span>
              <span class="text-xs text-[var(--muted-foreground)]">↗</span>
            </button>
          \`;
        }

        return \`
          <div class=" flex flex-col" style="width: \${STATION_WIDTH}px; margin-right: \${idx < n - 1 ? STATION_GAP : 0}px;">
            <!-- Station Header on Rail Row -->
            <div class="relative flex items-center h-6 pl-3 pr-2 gap-2" style="margin-top: \${arcAirHeight}px;">
              <span class="wf-lamp w-2.5 h-2.5 rounded-full border-2 shrink-0 \${lampColor}" data-lamp="\${st.status}"></span>
              <span class="text-xs font-semibold truncate" title="Step #\${st.firstStep}">\${escapeHtml(st.name)}</span>
              \${st.parallel ? '<span class="text-xs px-1 rounded bg-[var(--secondary)] text-[var(--muted-foreground)] font-mono">∥</span>' : ""}
            </div>
            <!-- Pills Hanging Under Station -->
            <div class="mt-2 flex flex-col gap-1.5">
              \${pillsHtml}
              \${moreRowHtml}
            </div>
          </div>
        \`;
      }).join("");

      container.innerHTML = \`
        <div class="relative flex items-start" style="min-width: \${totalWidth}px;">
          \${arcsSvg}
          \${railsHtml}
          \${stationsHtml}
        </div>
      \`;
    }

    function renderSpineView(session) {
      const container = document.getElementById("view-spine");
      container.innerHTML = session.stations.map((st, idx) => {
        const dotClass =
          st.status === "running"
            ? "bg-amber-500 wf-lamp-running"
            : st.status === "done"
              ? "bg-emerald-500"
              : "bg-red-500";
        return \`
          <div class="relative pl-5 pb-2 border-l border-[var(--border)] ml-2">
            <span class="absolute -left-[5px] top-1.5 w-2.5 h-2.5 rounded-full \${dotClass}"></span>
            <div class="flex items-center justify-between text-xs font-semibold mb-1.5">
              <span>\${idx + 1}. \${escapeHtml(st.name)}</span>
              <span class="text-[var(--muted-foreground)] font-mono">Step #\${st.firstStep} · \${st.pills.length} agents</span>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
              \${st.pills.map((sub) => renderPillHTML(sub, 0, sub.id === selectedSubagentId)).join("")}
            </div>
          </div>
        \`;
      }).join("");
    }

    function renderDirectoryView(session) {
      const container = document.getElementById("view-directory");
      const running = session.subagents.filter((s) => s.status === "running");
      const ended = session.subagents.filter((s) => s.status !== "running");

      const rowHtml = (sub) => \`
        <button type="button" onclick="window.__selectSubagent('\${sub.id}')"
          class="flex w-full items-start gap-2.5 rounded-lg px-2.5 py-2 text-left text-xs transition hover:bg-[var(--secondary)] cursor-pointer \${sub.id === selectedSubagentId ? 'bg-[var(--secondary)] ring-1 ring-[var(--border)]' : ''}">
          <span class="mt-0.5">\${renderAgentFaceSVG(sub.color, sub.status, "w-4 h-4")}</span>
          <span class="min-w-0 flex-1">
            <span class="flex items-center gap-2">
              <span class="font-semibold truncate">\${escapeHtml(sub.role)}</span>
              <span class="text-[var(--muted-foreground)] font-mono">[\${escapeHtml(sub.typeName)}]</span>
              <span class="ml-auto text-[var(--muted-foreground)] font-mono">\${sub.stepCount} steps · \${((sub.inputTokens + sub.outputTokens) / 1000).toFixed(1)}k tok</span>
            </span>
            <span class="block truncate text-[var(--muted-foreground)] mt-0.5">\${escapeHtml(sub.summary)}</span>
          </span>
        </button>
      \`;

      container.innerHTML = \`
        <div>
          <div class="text-xs font-semibold text-[var(--muted-foreground)] px-2 pb-1">运行中 Running · \${running.length}</div>
          \${running.length ? running.map(rowHtml).join("") : '<div class="text-xs text-[var(--muted-foreground)] px-2 py-1.5">当前无运行中的子代理</div>'}
        </div>
        <div>
          <div class="text-xs font-semibold text-[var(--muted-foreground)] px-2 pb-1">已结束 Ended · \${ended.length}</div>
          <div class="space-y-1">\${ended.map(rowHtml).join("")}</div>
        </div>
      \`;
    }

    function renderDrilldown(session) {
      const panel = document.getElementById("drilldown-panel");
      const sub = session.subagents.find((s) => s.id === selectedSubagentId) || session.subagents[0];
      if (!sub) {
        panel.innerHTML = '<div class="text-xs text-[var(--muted-foreground)]">点击任意子代理胶囊查看其只读会话详情</div>';
        return;
      }
      selectedSubagentId = sub.id;

      const toolsBadges = (sub.toolsUsed || [])
        .map((t) => \`<span class="px-1.5 py-0.5 rounded bg-[var(--secondary)] text-xs font-mono">\${escapeHtml(t.name)} ×\${t.count}</span>\`)
        .join("");

      const stepsList = (sub.steps || []).slice(-5).map((st) => \`
        <div class="border-l-2 border-[var(--border)] pl-2 py-0.5 text-xs">
          <div class="flex items-center justify-between text-[var(--muted-foreground)]">
            <span class="font-mono font-medium text-[var(--foreground)]">#\${st.idx} \${escapeHtml(st.title)}</span>
            <span>\${st.kind}</span>
          </div>
          <div class="truncate text-[var(--muted-foreground)]">\${escapeHtml(st.detail)}</div>
        </div>
      \`).join("");

      panel.innerHTML = \`
        <div class="flex flex-col gap-2">
          <div class="flex items-center justify-between gap-2">
            <div class="flex items-center gap-2 min-w-0">
              \${renderAgentFaceSVG(sub.color, sub.status, "w-5 h-5")}
              <div class="min-w-0">
                <div class="text-xs font-semibold truncate">\${escapeHtml(sub.role)}</div>
                <div class="text-xs text-[var(--muted-foreground)] font-mono truncate">ID: \${sub.id.slice(0, 18)}…</div>
              </div>
            </div>
            <span class="px-2 py-0.5 rounded-full text-xs font-medium bg-[var(--secondary)]">\${sub.status.toUpperCase()}</span>
          </div>

          <div class="grid grid-cols-3 gap-1.5 text-center bg-[var(--background)] p-1.5 rounded-lg border border-[var(--border)]">
            <div>
              <div class="text-xs text-[var(--muted-foreground)]">Steps</div>
              <div class="text-xs font-semibold font-mono">\${sub.stepCount}</div>
            </div>
            <div>
              <div class="text-xs text-[var(--muted-foreground)]">Tokens</div>
              <div class="text-xs font-semibold font-mono">\${((sub.inputTokens + sub.outputTokens) / 1000).toFixed(1)}k</div>
            </div>
            <div>
              <div class="text-xs text-[var(--muted-foreground)]">Workspace</div>
              <div class="text-xs font-semibold font-mono">\${escapeHtml(sub.workspace)}</div>
            </div>
          </div>

          \${toolsBadges ? \`<div class="flex flex-wrap gap-1">\${toolsBadges}</div>\` : ""}

          <div class="text-xs bg-[var(--background)] rounded-lg p-2 border border-[var(--border)]">
            <div class="font-semibold text-[var(--muted-foreground)] mb-0.5">委派任务 Prompt</div>
            <div class="line-clamp-2 text-xs">\${escapeHtml(sub.prompt || sub.summary)}</div>
          </div>

          \${!IS_INLINE && stepsList ? \`
            <div class="space-y-1 max-h-[140px] overflow-y-auto wf-scroller pr-1">
              <div class="text-xs font-semibold text-[var(--muted-foreground)]">最近执行轨迹 (Read-Only Projection)</div>
              \${stepsList}
            </div>
          \` : ""}
        </div>
      \`;
    }

    function renderAll() {
      const session = SESSIONS[currentSessionIdx];
      if (!session) return;

      document.getElementById("live-badge").textContent =
        \`\${session.stations.length} 站 · \${session.subagentCount} 子代理 · \${(session.totalTokens / 1000).toFixed(0)}k tok\`;
      document.getElementById("session-subtitle").textContent =
        \`[\${session.conversationId.slice(0, 8)}] \${session.title}\`;

      document.querySelectorAll(".tab-btn").forEach((btn) => {
        const active = btn.dataset.tab === currentTab;
        btn.className = \`tab-btn px-2 py-0.5 text-xs rounded-md font-medium cursor-pointer transition \${
          active ? "bg-[var(--card)] text-[var(--foreground)] shadow-sm" : "text-[var(--muted-foreground)]"
        }\`;
      });

      document.getElementById("view-timeline").classList.toggle("hidden", currentTab !== "timeline");
      document.getElementById("view-spine").classList.toggle("hidden", currentTab !== "spine");
      document.getElementById("view-directory").classList.toggle("hidden", currentTab !== "directory");

      if (currentTab === "timeline") renderTimelineView(session);
      else if (currentTab === "spine") renderSpineView(session);
      else renderDirectoryView(session);

      renderDrilldown(session);
    }

    window.__selectSubagent = (id) => {
      selectedSubagentId = id;
      renderAll();
    };

    window.__toggleStation = (stationId) => {
      if (expandedStations.has(stationId)) expandedStations.delete(stationId);
      else expandedStations.add(stationId);
      renderAll();
    };

    // Initialize session selector
    const selectEl = document.getElementById("session-select");
    SESSIONS.forEach((s, idx) => {
      const opt = document.createElement("option");
      opt.value = String(idx);
      opt.textContent = \`\${s.subagentCount} Agents · \${s.title.slice(0, 26)}\`;
      selectEl.appendChild(opt);
    });
    selectEl.addEventListener("change", (e) => {
      currentSessionIdx = Number(e.target.value);
      selectedSubagentId = SESSIONS[currentSessionIdx]?.subagents[0]?.id || null;
      expandedStations.clear();
      renderAll();
    });

    // Tab switching
    document.querySelectorAll(".tab-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        currentTab = btn.dataset.tab;
        renderAll();
      });
    });

    // Replay Draft Typewriter & Station Growth animation
    document.getElementById("btn-replay").addEventListener("click", () => {
      const session = SESSIONS[currentSessionIdx];
      if (!session) return;
      clearInterval(replayTimer);
      currentTab = "timeline";
      replayDraftStep = 1;
      renderAll();
      replayTimer = setInterval(() => {
        if (replayDraftStep < session.stations.length) {
          replayDraftStep++;
          renderAll();
        } else {
          replayDraftStep = null;
          clearInterval(replayTimer);
          renderAll();
        }
      }, 420);
    });

    // Periodic face micro-expression engine (port of workflow-face-motion.ts)
    setInterval(() => {
      const faces = document.querySelectorAll(".wf-face");
      if (faces.length === 0) return;
      const pick = faces[Math.floor(Math.random() * faces.length)];
      if (!pick) return;
      const motions = ["blink", "hop", "idle"];
      const m = motions[Math.floor(Math.random() * motions.length)];
      pick.dataset.motion = m;
      const lookLeft = Math.random() < 0.35;
      pick.style.setProperty("--wf-face-x", lookLeft ? "-2.2px" : "0px");
      setTimeout(() => {
        pick.dataset.motion = "idle";
        pick.style.setProperty("--wf-face-x", "0px");
      }, 520);
    }, 1100);

    selectedSubagentId = SESSIONS[0]?.subagents[0]?.id || null;
    renderAll();
  </script>
</body>
</html>`;
}

// CLI Entrypoint
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const args = parseArgs(process.argv);
  let sessions = args.demo ? getDemoSessions() : scanBrainSessions(args.brainDir, args.currentConv);
  if (sessions.length === 0) {
    sessions = getDemoSessions();
  }

  if (args.outJson) {
    fs.writeFileSync(args.outJson, JSON.stringify(sessions, null, 2), "utf8");
  }
  if (args.outInline) {
    fs.writeFileSync(args.outInline, buildHTML(sessions, "inline"), "utf8");
  }
  if (args.outFull) {
    fs.writeFileSync(args.outFull, buildHTML(sessions, "full"), "utf8");
  }
  console.log(
    JSON.stringify({
      scannedSessionsWithSubagents: sessions.length,
      topSession: sessions[0]
        ? {
            conversationId: sessions[0].conversationId,
            subagentCount: sessions[0].subagentCount,
            stations: sessions[0].stations.length,
            totalTokens: sessions[0].totalTokens,
          }
        : null,
    })
  );
}
