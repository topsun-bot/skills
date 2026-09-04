# 上海桦之坚科技有限公司｜机器人产品与现场工程

本仓库维护可复用的机器人工程 Skills，并作为上海桦之坚科技有限公司的公开技术入口。当前聚焦宇树 G1 / Go2W 二次开发、安防自主导航、机械臂集成、ROS 2 / SDK 联调和现场试点验收。

## G1 / Go2W 现场工程服务

- **Go2W 安防自主导航**：团队陈述已有安防场景自主导航演示，可继续拆分地图、定位、避障、停止、断网恢复、告警和工单接口；演示不等于第三方客户验收、连续无人值守或安全认证。
- **G1 机械臂与移动操作**：可围绕机械臂集成、抓取、按钮、开关门和受约束维修任务做接口与验证；具体能力仍需按本体自由度、末端工具、负载、控制模式和现场条件确认。
- **ROS 2 / SDK 二次开发**：覆盖网络、DDS、固件、模式、控制权、状态新鲜度、导航接口和证据化验收；默认先做离线、仿真和只读检查，任何真机运动或生产写入必须单独授权。

完整服务页：[宇树 G1 与 Go2W 二次开发｜自主导航、机械臂集成与试点验收](https://jixun-robot-lab.guo1988yan.chatgpt.site/unitree-g1-go2w-secondary-development?src=github-skills-readme-unitree-service)

一元书面初筛：[提交一个具体的 G1 或 Go2W 二次开发问题](https://jixun-robot-lab.guo1988yan.chatgpt.site/one-yuan-unitree-precheck?src=github-skills-readme-one-yuan)，获取“已知事实、证据缺口、下一步只读检查”三项结果；付款以收款人微信到账记录为准，浏览和表单提交不代表已付款。

免费工程资料：[安防巡检试点范围生成器](https://jixun-robot-lab.guo1988yan.chatgpt.site/security-pilot-scope-generator?src=github-skills-readme-security)，用于梳理现场路线、任务边界、证据等级与验收条件；填写内容仅在浏览器内处理，不触发真机。

公开答疑：[宇树 G1、Go2W 二次开发、安防导航与机械臂集成](https://github.com/topsun-bot/skills/issues/15)，可提交已脱敏的型号、版本、现象、目标和验收要求。

> 边界说明：本仓库包含独立集成、预检和验收方法，不属于宇树官方支持或官方认证，不把团队演示、离线检查、仿真或文档证据表述为量产、客户案例或真机验收。

## Skill 列表

| Skill | 作用 | 触发方式 |
| --- | --- | --- |
| [`multi-agent-delivery`](multi-agent-delivery/) | 让多个 Agent 按“需求取证 → 计划 → 独立审计划 → 开发 → 专项验证 → 原开发者修复 → 最终验收”的流程协作；普通修复到上限后先做独立根因裁决，仅对范围和权限不变的问题自动追加一次修复，避免无限复盘和无意义暂停。 | 仅在当前请求中直接使用 `$multi-agent-delivery`，或在界面中明确选择/附加该 Skill；不支持隐式触发。 |
| [`build-interactive-web-deck`](build-interactive-web-deck/) | 把 PPT、文档、报告或研究材料编辑成手绘感互动网页演讲册，提供演讲与探索双模式、热点、分支、讲稿、证据和浏览器验收。 | 询问网页演讲册、可点击知识图册、Flipbook 风格演示，或直接使用 `$build-interactive-web-deck`。 |
| [`topsun-delegate-to-chatgpt-pro`](topsun-delegate-to-chatgpt-pro/) | 把复杂工程问题安全地委托给 ChatGPT Pro，再由 Codex 在本地独立应用和验证结果。 | 直接使用 `$topsun-delegate-to-chatgpt-pro`。 |
| [`unitree-g1-go2w-preflight`](unitree-g1-go2w-preflight/) | 在任何真机运动前，用只读优先证据门核验 G1、Go2、Go2W 的网络、状态新鲜度、固件/模式/控制权、Nav2 与机械臂集成。 | 询问宇树机器人联调、上机前检查、SDK/ROS 2 排障或直接使用 `$unitree-g1-go2w-preflight`。 |
| [`g1-controller-temperature-evidence`](g1-controller-temperature-evidence/) | 离线比较 GEAR-SONIC G1 两组 CSV 日志的温升斜率、估算力矩 RMS、关节速度 RMS 与策略动作波动，输出证据门而非根因结论。 | 询问 G1 控制器高温、GEAR-SONIC 日志 A/B、调参前后证据，或直接使用 `$g1-controller-temperature-evidence`。 |
| [`inspection-robot-api-acceptance`](inspection-robot-api-acceptance/) | 把巡检机器人 HTTP/ROS 2 接口、数据语义、故障恢复、培训、维保和试运行要求写成可追溯验收证据。 | 询问巡检机器人系统对接、API 合同、交付验收、维保排障或直接使用 `$inspection-robot-api-acceptance`。 |

## 目录约定

- `SKILL.md`：Skill 的入口、触发条件和主流程。
- `agents/`：Codex 展示信息和默认提示词。
- `references/`：各角色约束、工作流协议和验收规则。
- `assets/`：运行时模板。
- `scripts/`：初始化、校验等辅助脚本。
