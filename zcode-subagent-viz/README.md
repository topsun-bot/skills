# ZCode Subagent Visualizer for Google Antigravity (`zcode-subagent-viz`)

将 [`zai-org/ZCode`](https://github.com/zai-org/ZCode) 中的核心子 Agent 可视化体系（`WorkflowTimeline` 水平多轨时间线、`WorkflowAgentFace` 9 色微表情瓦片脸、`WorkflowAgentPill` 子代理胶囊、`WorkflowRunSpine` 垂直脊线、`SubagentDirectorySidePane` 实时目录与会话只读下钻）抽离并移植为 **Google Antigravity** 的通用 **Skill + UI Plugin (Sidecar)**。

---

## 核心特性

1. **三视图无缝切换**：
   - **轨道图 (`Timeline`)**：复刻 ZCode `timeline-geometry.ts` 黄金几何常量（站宽 `168px`、站距 `24px`、5 站 `936px`），支持主轨、并行分叉虚线轨、站台 1.6s 呼吸灯（`.wf-lamp-running`）与轨道上方空气层的 SVG 控制流圆弧（`WorkflowTimelineArcs`）。
   - **垂直脊线 (`Spine`)**：按波次纵向展开每个阶段站台及其下属子代理胶囊。
   - **子代理名册 (`Directory`)**：按 `Running`（运行中）与 `Ended`（已结束）分组展示子代理状态、步数与 Token 消耗。
2. **9 色动态表情瓦片脸 (`WorkflowAgentFace`)**：
   - 完整移植 `#54B9A6` ~ `#EA4045` 九色环圆角方块 SVG 头像与 7 种眼部表情（`pill` / `happy` / `sleepy` / `focused` / `sad` / `confused` / `dots`），内置随机眨眼（`blink`）、左右扫视（`glance`）、完成跳跃（`hop`）与失败摇头（`shake`）状态机。
3. **子代理胶囊与叠牌扇开门 (`WorkflowAgentPill` & `.wf-more-deck`)**：
   - 悬停时底色抬升、头像放大、右侧状态图标与 `↗` 箭头同格切换；单站超过阈值时自动折叠为三张叠牌扇开门「还有 N 个子代理」。
4. **零侵入解析 Antigravity 原生日志**：
   - 直接读取 `~/.gemini/antigravity/brain/<conversation-id>/.system_generated/logs/transcript.jsonl`，自动关联 `invoke_subagent` 派生树、`send_message` 跨阶段通信与子会话只读步骤详情；无本地会话时自动回退至内置脱敏演示数据（`--demo`）。

---

## 目录结构

```text
zcode-subagent-viz/
├── README.md
├── SKILL.md                                         # Antigravity / Claude / Codex 技能入口说明
├── scripts/
│   └── zcode_subagent_viz_builder.mjs               # Transcript 解析器 + 自包含 HTML 渲染引擎
└── plugin-template/                                 # Antigravity 全局 UI Plugin (Sidecar) 模板
    ├── plugin.json
    └── sidecars/
        └── subagent_visualizer/
            ├── sidecar.json                         # SIDECAR_UI_ENTRYPOINT_AUX_PANE 副屏配置
            └── server.cjs                           # 零依赖 Node HTTP Sidecar 实时服务
```

---

## 快速使用

### 1. 生成 Generative UI 内嵌卡片与全屏工作台

```bash
node scripts/zcode_subagent_viz_builder.mjs \
  --brain-dir "$HOME/.gemini/antigravity/brain" \
  --out-inline "./zcode_subagent_inline.html" \
  --out-full "./zcode_subagent_workbench.html"
```

### 2. 安装为 Antigravity 全局 Sidecar 插件

```bash
mkdir -p ~/.gemini/config/plugins/zcode-subagent-viz/skills/ai-agent-zcode-subagent-viz
cp -R plugin-template/* ~/.gemini/config/plugins/zcode-subagent-viz/
cp -R SKILL.md scripts ~/.gemini/config/plugins/zcode-subagent-viz/skills/ai-agent-zcode-subagent-viz/
```

重启 Antigravity 后，可在对话中通过 `[Subagent Visualizer](sidecar://zcode-subagent-viz/subagent_visualizer/ui.html)` 一键打开右侧副屏实时监控面板。
