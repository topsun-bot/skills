# 自研 Skills

这个仓库集中存放 Topsun 团队自己开发的 Codex Skills。每个 Skill 使用一个独立的顶层目录，入口文件为 `SKILL.md`。

## Skill 列表

| Skill | 作用 | 触发方式 |
| --- | --- | --- |
| [`multi-agent-delivery`](multi-agent-delivery/) | 让多个 Agent 按“需求取证 → 计划 → 独立审计划 → 开发 → 专项验证 → 原开发者修复 → 最终验收”的流程协作，并通过稳定问题指纹和轮次预算防止无限复盘。 | 明确说“用多 Agent 协同完成”“启用多智能体交付模式”，或直接使用 `$multi-agent-delivery`。 |
| [`topsun-delegate-to-chatgpt-pro`](topsun-delegate-to-chatgpt-pro/) | 把复杂工程问题安全地委托给 ChatGPT Pro，再由 Codex 在本地独立应用和验证结果。 | 直接使用 `$topsun-delegate-to-chatgpt-pro`。 |
| [`unitree-g1-go2w-preflight`](unitree-g1-go2w-preflight/) | 在任何真机运动前，用只读优先证据门核验 G1、Go2、Go2W 的网络、状态新鲜度、固件/模式/控制权、Nav2 与机械臂集成。 | 询问宇树机器人联调、上机前检查、SDK/ROS 2 排障或直接使用 `$unitree-g1-go2w-preflight`。 |
| [`inspection-robot-api-acceptance`](inspection-robot-api-acceptance/) | 把巡检机器人 HTTP/ROS 2 接口、数据语义、故障恢复、培训、维保和试运行要求写成可追溯验收证据。 | 询问巡检机器人系统对接、API 合同、交付验收、维保排障或直接使用 `$inspection-robot-api-acceptance`。 |

## 目录约定

- `SKILL.md`：Skill 的入口、触发条件和主流程。
- `agents/`：Codex 展示信息和默认提示词。
- `references/`：各角色约束、工作流协议和验收规则。
- `assets/`：运行时模板。
- `scripts/`：初始化、校验等辅助脚本。
