# data-service 项目索引

本文件只有指针。**任何会被一个 commit 变成假话的内容（状态取值、枚举清单、文件职责、构建命令）都不写在这里**，写了对它就会腐烂，而且腐烂时没人会听见。

业务口径以 Obsidian `knowledge/**` + 当前代码为准。仓库内 `docs/` 与 `docs/support/` 是**降级区**：已被证实在 MQTT 推送链路与 Episode 终态上说谎，只可当搜索线索，不可当结论（清单见 `data-workflow:oncall` 的 `references/knowledge-sources.md`）。

## 去哪读

知识层根路径 `/Users/xuxinzhi/Documents/Obsidian Vault/xxz_obsidian/`（含空格，命令必须引号包裹）。

| 要查什么 | 去哪 |
|---|---|
| 技术栈、项目全貌、常用命令 | Obsidian `knowledge/data-service项目速查.md` |
| 状态定义、语义、聚合口径 | Obsidian `knowledge/状态机.md` → 再回 `internal/biz/status.go` 核对取值 |
| 线上症状、排查入口 | Obsidian `knowledge/线上排查.md` |
| 构建与本地运行 | Obsidian `knowledge/运行与构建.md` → 命令以 `Makefile` 目标为准 |
| 单个业务域（采集任务/审批流程/任务分发/采集批次/数据条目/设备管理/质检管理/标签管理/小组管理/多样性模板/任务配置/飞书配置） | Obsidian `knowledge/<域>/README.md`，一次只读一个域 |
| 公司模板（技术方案、MR、提测、代码规范、研发流程） | Obsidian `开发规范化/` |
| 工程约束、分层规则、生成物清单、构建命令 | `.cursor/rules/data-service.mdc`（**唯一副本**） |
| Go 细则 R01–R18 | `.cursor/rules/data-service-go.mdc` |
| 复用门禁 | `.cursor/rules/reuse-gate.mdc`，自检清单 `data-workflow:implementation` 的 `references/reuse-gate.md` |
| 术语 | `CONTEXT.md` |
| 个人调查卡片（症状索引） | `$VAULT/knowledge/排查卡片/`，检索方式见该目录 `README.md` |
| 接口字段 | `api/**/*.proto`（生成物 `*.pb.go` 同源） |
| 任何域的当前真实行为 | `internal/{service,biz,data}` 里对应文件，以当前代码为准 |

## 找代码入口的方法

不维护「域 → 文件」对照表——那种表每次重命名就腐烂，而且腐烂时是**安静地骗人**。改用不会失效的定位规则：

已知 URL → 搜 `api/**/*.proto` 的 HTTP path；已知 RPC → 从 `internal/service` 同名方法进入；已知表/字段 → 从 `internal/data` 模型与 `Where/Joins` 进入再反查 biz 调用者；已知状态数字 → 先定族再 grep `internal/biz/status.go` 的对应 const 块。

完整规则见 `data-workflow:oncall` 的 `references/routing.md` step 2。
