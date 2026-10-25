---
name: ai-agent-zcode-subagent-viz
description: 【AI工程｜ZCode子Agent可视化】从zai-org/ZCode抽离的子Agent与多智能体工作流可视化套件（含9色动态表情瓦片脸WorkflowAgentFace、胶囊WorkflowAgentPill、水平轨道与控制流圆弧WorkflowTimeline、垂直脊线WorkflowRunSpine及子会话目录SubagentDirectory），支持解析Antigravity的brain/<conversation-id>/transcript.jsonl生成Generative UI内嵌卡片、独立全屏看板或Sidecar实时副屏插件。
---

# ZCode 子 Agent 可视化套件 (Antigravity 移植版)

本技能将 [`zai-org/ZCode`](https://github.com/zai-org/ZCode) 中的核心子 Agent 可视化体系抽离并移植到 **Google Antigravity**，支持两种运行模式：
1. **Skill + Generative UI 模式（零配置即用）**：通过 `scripts/zcode_subagent_viz_builder.mjs` 直接解析 `~/.gemini/antigravity/brain/<conversation-id>/.system_generated/logs/transcript.jsonl`，生成可在对话流内 `<agent-embed>` 展示的紧凑轨道卡片，以及可在右侧 Artifact 面板打开的完整三视图工作台。
2. **UI Plugin / Sidecar 实时副屏模式**：通过 `plugin-template/` 下的脚手架，可一键注册为 Antigravity 插件（`sidecar://zcode-subagent-viz/subagent_visualizer/ui.html`），通过 SSE 实时监听 `brain/` 目录下的子 Agent 派生与工具调用。

---

## 一、`zai-org/ZCode` 原始代码位置速查

在 `zai-org/ZCode` 仓库中，子 Agent 可视化由**两套互补的子系统**组成：

### 1. 动态多智能体工作流轨道图 (`WorkflowTimeline` & `WorkflowRunSidePane`)
- **规范文档**：`docs/dynamic-workflow/presentation.md`
- **纯函数时间线模型**：`packages/ui/src/components/workflow-timeline/timeline-model.ts`（`buildWorkflowTimeline(graph, run)`，计算站台 `stations`、轨道 `rails`、控制流圆弧 `arcs`、并行分叉带 `bands`）
- **几何布局引擎**：`packages/ui/src/components/workflow-timeline/timeline-geometry.ts`（`STATION_WIDTH = 168`, `STATION_GAP = 24`, `RAIL_ROW = 24`, `ARC_BASE = 26`, `PILL_HEIGHT = 32`）
- **水平轨道主视图**：`packages/ui/src/components/workflow-timeline/WorkflowTimeline.tsx`
- **轨道、呼吸灯与流轨 Chevron**：
  - `packages/ui/src/components/workflow-timeline/WorkflowTimelineTracks.tsx`
  - `packages/ui/src/components/workflow-timeline/WorkflowTimelineArcs.tsx`
  - `packages/ui/src/components/workflow-timeline/WorkflowStreamChevrons.tsx`
- **子 Agent 药丸与九色瓦片脸微表情动画**：
  - `packages/ui/src/components/workflow-timeline/WorkflowAgentPill.tsx`（悬停时底色抬升、头像放大、`↗` 替换右侧状态图标、`+N more` 叠牌扇开 `.wf-more-deck`）
  - `packages/ui/src/components/workflow-timeline/WorkflowAgentFace.tsx`（9 色环 `#54B9A6` ~ `#EA4045` 圆角方块 SVG 瓦片脸，支持 `pill`/`happy`/`sleepy`/`focused`/`sad`/`confused`/`dots` 七种眼部表情）
  - `packages/ui/src/components/workflow-timeline/workflow-face-motion.ts`（状态驱动的随机眨眼 `blink`、左右扫视 `glance`、欢呼跳跃 `hop`、困惑摇头 `shake` 状态机）
- **右侧垂直脊线面板 (Spine)**：
  - `packages/ui/src/app-shell/WorkflowRunSidePane.tsx`
  - `packages/ui/src/app-shell/WorkflowRunSpineParts.tsx`
- **核心动画与样式**：`packages/ui/src/styles.css`（第 1430–2258 行：`.wf-motion`, `.wf-pill`, `.wf-lamp-running`, `.wf-face` 等）

### 2. 父会话子 Agent 目录与只读会话下钻 (`SubagentDirectory` & `AgentToolRenderer`)
- **规范文档**：`docs/subagent-session-directory.md`、`docs/subagent-session-side-tabs.md`
- **子 Agent 运行态投影**：`apps/zcode-cli/packages/bootstrap/src/app/subagent-observation.ts`
- **对话内 Agent 工具卡片渲染器**：`packages/ui/src/ToolCallBlocks/renderers/agent.tsx`、`agentHelpers.ts`
- **侧栏子 Agent 实时目录**：`packages/ui/src/app-shell/SubagentDirectorySidePane.tsx`（Running 实时列表 + Ended 分页列表）
- **侧栏子 Agent 会话只读下钻面板**：`packages/ui/src/app-shell/SubagentSessionSidePane.tsx`、`packages/ui/src/v4/SubagentDrilldown.tsx`

---

## 二、在 Antigravity 中使用本 Skill 生成子 Agent 可视化

### 步骤 1：运行构建脚本提取真实会话数据并生成 HTML

执行以下命令扫描当前会话（或最近包含 `invoke_subagent` 的父会话）并输出 HTML 组件：

```bash
node .agents/skills/ai-agent-zcode-subagent-viz/scripts/zcode_subagent_viz_builder.mjs \
  --brain-dir "$HOME/.gemini/antigravity/brain" \
  --current-conv "<当前conversation-id>" \
  --out-inline "$HOME/.gemini/antigravity/brain/<当前conversation-id>/zcode_subagent_inline.html" \
  --out-full "$HOME/.gemini/antigravity/brain/<当前conversation-id>/zcode_subagent_workbench.html"
```

### 步骤 2：注册 Artifact 并内嵌展示

1. 使用 `write_file`（或由脚本生成后通过 `edit_file` / `write_file` 附带 `ArtifactMetadata`）确保文件具有 `UserFacing: true`。
2. 在回复中嵌入紧凑版水平轨道卡片（高度 < 480px，符合 `generative_ui` 规范）：
   ```html
   <agent-embed src="file:///<appDataDir>/brain/<conversation-id>/zcode_subagent_inline.html"></agent-embed>
   ```
3. 同时提供完整版工作台 Artifact 链接，支持切换 **Horizontal Timeline（水平轨道图）**、**Vertical Spine（垂直脊线）** 与 **Subagent Directory + Session Drilldown（子智能体目录与只读步骤下钻）**。

---

## 三、部署为 Antigravity 全局 UI Plugin (Sidecar)

若用户希望将该可视化作为常驻右侧副屏（Aux Pane）的 UI Plugin：
1. **先向用户确认**（因涉及写入全局 `~/.gemini/config/plugins/zcode-subagent-viz`）。
2. 用户确认后，复制 `plugin-template/` 至 `~/.gemini/config/plugins/zcode-subagent-viz/`。
3. 在聊天中输出 `[ZCode Subagent Visualizer](sidecar://zcode-subagent-viz/subagent_visualizer/ui.html)` 胶囊链接即可一键呼出副屏。
