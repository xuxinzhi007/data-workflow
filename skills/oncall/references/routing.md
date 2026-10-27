# 定位与路由

按 step 0 → 1 → 2 顺序执行。**先查记忆，再查知识库，最后才读代码**；反过来会把已经付过代价的调查重做一遍。

## step 0 记忆检索（必做，在碰任何代码之前）

```bash
grep -rl "<症状词>|<状态值>|<RPC名>|<表名>" $VAULT/knowledge/排查卡片/
```

命中就打开卡片，读 `verified_commit` / `watches` / `status`。然后跑新鲜度门禁：

```bash
"$PLUGIN_ROOT/scripts/knowledge_drift.sh" <卡片路径>
```

- `FRESH` → 可作为第 3 层证据直接引用。
- `STALE` → **只当线索**：用它选搜索目标，然后从 `watches` 列出的文件重新推导每个取值，并在答案里说明该卡已过期。
- 无 frontmatter → 按 `STALE` 处理。
- 卡片 `status: superseded` → 跳过，看它指向的替代卡。

索引表在 `$VAULT/knowledge/排查卡片/README.md`（每卡约 1 行，比逐卡打开便宜）。

## step 1 域路由：只加载一个知识库文件

知识库按业务域拆分，**一次只读一个域**，读错域比不读更糟（会把别的域的状态数字带进上下文）。

| 问题类型 | 加载这一个 |
|---|---|
| 状态数字 / 名称 / 迁移 / 终态 / 展示态 | `knowledge/状态机.md` |
| 线上症状、卡住、看不到、进度不对 | `knowledge/线上排查.md` |
| 项目全貌、新人上下文、分层与常用命令 | `knowledge/data-service项目速查.md` |
| 构建、环境、本地启动 | `knowledge/运行与构建.md` |
| Job 建单（APP/平台）、任务生命周期 | `knowledge/采集任务/README.md` |
| 审批流、节点、规则 | `knowledge/审批流程/README.md` |
| 分发、改派、抢单、工作台 | `knowledge/任务分发/README.md` |
| Collection 采集批次 | `knowledge/采集批次/README.md` |
| Episode 数据条目、事件上报 | `knowledge/数据条目/README.md` |
| QC 质检（列表/领取/提交/智能预检） | `knowledge/质检管理/README.md` |
| 标签、Tag code | `knowledge/标签管理/README.md` |
| 小组、数据范围 | `knowledge/小组管理/README.md` |
| 设备、设备型号、在线状态 | `knowledge/设备管理/README.md` |
| 多样性模板 | `knowledge/多样性模板/README.md` |
| 任务配置 | `knowledge/任务配置/README.md` |
| 飞书通知 | `knowledge/飞书配置/README.md` |

根路径：`/Users/xuxinzhi/Documents/Obsidian Vault/xxz_obsidian/knowledge/`（**含空格，命令里必须引号包裹**）。

各域 `README.md` 是入口，需要细节时再顺着它进同目录的具体文件（如 `质检管理/人工质检.md`）。仍然一次一个文件。

信任级别与例外见 [knowledge-sources.md](./knowledge-sources.md)。**知识库文件只给线索和口径，取值一律回 L3 代码核对**——尤其是状态数字、字段名、SQL 条件。

## step 2 快速定位规则（纯流程，不随 commit 失效）

- 已知 URL：先在 `api/**/*.proto` 搜 HTTP path，再找同名 Service 方法。
- 已知 RPC：从 `internal/service` 同名方法进入，向 Biz 和 Data 追踪。
- 已知表/字段：从 `internal/data` 模型与 `Updates/Where/Joins` 进入，再反查 Biz 调用者。
- 已知状态数字：**先定族**（见 [state-protocol.md](./state-protocol.md)），再只 grep `internal/biz/status.go` 里该族的 const 块，然后搜全部写入口与读侧筛选。
- 已知错误码/文案：搜 Proto error enum、`internal/pkg/errors`、Biz guard 和外部错误映射。
- 已知日志：搜稳定 message/key，而不是完整动态日志行。
- “列表里看不到”：同时检查 RBAC、tenant/group scope、candidate scope、状态/软删过滤、关联表、分页前后过滤。
- “卡住/进度不对”：同时检查持久化状态、并行状态字段、聚合计数、CAS 是否命中、队列/调度器和外部回调。
- “没收到通知/没推送”：不要先信文档结论，先 grep `internal/biz/*notification*.go`、`internal/data/mqtt.go`、`internal/server/scheduler/`，确认是否存在主动推送通道（已有一张卡专门记录这里文档说谎）。

## 完成判定

定位阶段结束的条件：已经能说出「这个问题属于哪个族/哪个域」+「下一步该打开哪 1–3 个代码文件」。若还需要打开第 4 个文档才能决定，说明路由做错了，回到 step 1 重选域。
