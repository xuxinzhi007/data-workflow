# 架构评审

| 报告 | 主题 | 状态 |
|---|---|---|
| [`data-workflow-architecture-review.html`](data-workflow-architecture-review.html) | data-workflow 现有结构里的浅 module 与泄漏的 seam | 提案，待决策 |

前置产物：[`scope.md`](scope.md)、[`findings/structure.md`](findings/structure.md)、[`findings/callflow.md`](findings/callflow.md)。停在哪、先问什么：[`verdict.md`](verdict.md)。

日期：2026-11-12（Asia/Shanghai）。HEAD fe2b141。范围见 scope.md（用户点名整仓库，权重压在 runner / 门禁 / 工作流定义；GLOSSARY.md 与 docs/adr/ 无）。

## 直接读纯文本

### 候选清单

1. **查询与推进挤在同一条路径**（Strong）
   - Problem：会话钩子把 next 当只读探针，show 在产物齐时却会推进并写记录；同一条路径还不调用只挂在 done 上的 G7。
   - 证据：`workflow_next.py:show`、`workflow_next.py:cmd_done`、`workflow_next.py:knowledge_feedback`、`hooks/session-start`。临时仓库实跑：写齐 decision.md 再 next，stage 推进并写 evidence.log；feature 第 6 步只写 quality.md 再 next，跳过 G7 进入第 7 步。
   - 方向：加深运行状态，查询与推进不相漏，G7 跟其它门走推进这一侧。

2. **配置读取裂成四处浅 module**（Strong）
   - Problem：同一配置键要在四份浅副本之间跳，strict 的候选路径和优先级已经与 policy 不一致。
   - 证据：`layout.py:read_yaml_key`、`layout.py:configured_store`、`workflow_next.py:config_value`、`gate_edit.py:policy`、`gate_edit.py:strict`。实跑：仅在 `.qoder/.../config.yaml` 写 `gate_strict: "true"` 时 policy 能读到同文件的 protected_paths，strict 仍为假；仓库根与 `.cursor` 同时存在时，两个键的文件优先级相反。
   - 方向：加深一个配置读取 module，所有键走同一套查找。

3. **产物落点的 interface 是空的**（Strong）
   - Problem：JSON 声明了 artifacts_root，runner 不读这个字段，把 `<artifacts_root>` 写死成 `specs/<feature>`，`<topic>` 也不替换；layout 里的同名键是另一件事。
   - 证据：`workflows/architecture-review.json`、`workflow_next.py:artifact_paths`、`layout.py:configured_store`。实跑：`artifact_paths("<artifacts_root>/<topic>-architecture-review.html", "rev1")` 得到 `specs/rev1/<topic>-architecture-review.html`。
   - 方向：加深产物落点，按声明的根解析占位符。

4. **写入放行泄漏了 feature 的方案门**（Worth exploring）
   - Problem：approve 已签发放行行，写入门禁仍要一份 change 从不产出的 plan.md 与 gate，才能放行受保护路径。
   - 证据：`workflow_next.py:cmd_approve`、`gate_edit.py:design_ok`、`gate_edit.py:decision`、`workflows/change.json`。实跑：change 走完 wait / answer / approve 后，无 plan.md 时受保护路径仍 deny；补上这两份 feature 产物后变为 allow。
   - 方向：加深放行判定，按这次运行的工作流看该有的产物。

未单独成卡片、可并入上面方向的：`is_finished` 在 `cmd_next`、session-start、`gate_edit.active_runs` 仍有终态谓词副本；`print_stage_hints` 仍靠手工枚举（`template` 未转发，change 的阶段正文自己点名了模板）。已修不当现行问题的见 scope.md。

### 注入 / 调用路径矩阵

| 注入或调用路径 | 走到的 module | 产物齐时写不写 run.json | 跑不跑 G7 | 配置查找 |
|---|---|---|---|---|
| `hooks/session-start`（新会话） | `workflow_next.py` 的 `next` → `show` | 会写（文档阶段已齐时自动推进） | 不跑 | 走 runner 的 `config_value` |
| `/dw-next` 或裸 `next` | 同上 `show` | 会写 | 不跑 | 同上 |
| `/dw-done` 或裸 `done` | `cmd_done` | 会写（过门后推进） | 跑（仅当该阶段标记了 knowledge_feedback） | 同上 |
| 裸 `close`（无斜杠命令） | `cmd_close` | 会写（关单） | 不跑 | 同上 |
| Cursor 写入钩子 `gate-edit` | `gate_edit.py:decision` | 不写运行记录 | 不适用 | `policy` 与 `strict` 不是同一套路径 |

文档与用例把第一行写成「不改 run.json」。现行 `show` 不满足这条。

### 建议顺序

1. 查询与推进挤在同一条路径（含把 G7 收进推进侧的门）。
2. 配置读取裂成四处浅 module。
3. 产物落点的 interface 是空的。本轮 architecture-review 的机器门已经受到它影响。
4. 写入放行泄漏了 feature 的方案门。只在配置了 protected_paths 且走 change 时发作。

### 待拍板项

- next 在文档阶段产物齐时自动推进，是预期的使用方式，还是只读查询上的泄漏？若是预期，钩子就不能再走同一条路径。
- architecture-review 的产物根，以 JSON 声明的 `$REPO/docs/reviews/` 为准，还是与其它工作流一样落 `specs/<feature>/`？
- change 要放行受保护路径时，是否继续借用 feature 的 plan.md / gate，还是按 change 自己的产物来判？
- `gate_strict` 与 `protected_paths` 的文件查找顺序以谁为准（仓库根优先，还是工具目录优先；要不要包含 `.qoder` / `.agents` / `.claude` / `.codex` 和 `~/.config`）？
- 第四个运行终态如果以后要加，判定是否必须收进与 hook 共用的一处？

本文件状态是「提案，待决策」。候选一旦落地，结论移进 `docs/design.md`，这里只做历史存档。

## 重新生成

按 `skills/data-workflow/workflows/architecture-review.json` 再跑一轮 architecture-review。圈范围、走查、出报告、停下问，产物仍落 `$REPO/docs/reviews/`。
