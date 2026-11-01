# 业务分析骨架与知识落点 变更说明（change note）

- feature：`business-model` ／ 分支：`main` ／ commit 范围：工作树，提交后回填
- 日期：2026-11-01

## 1 一句话

补上业务分析的九个维度，并把业务事实的落点从「仓外 vault + 个人卡片」改成「仓库内 `docs/domain` 优先」。

## 2 为什么

`docs/competitive.md` §3 承认的第一条短板：**业务分析不可累积**。拆开是「只有检索协议（去哪找），没有分析骨架（看什么）」+「事实不落仓库」。证据在 `specs/business-model/decision.md` §现状。

## 3 改了什么

| 层 | 文件 | 变更 |
|---|---|---|
| 分析骨架 | `skills/data-workflow/references/business-model.md`（新增） | 九维度：对象与身份 / 状态族 / 迁移与守卫 / 读侧可见性 / 角色与数据范围 / 外部通道 / 幂等与重试 / 审计与通知 / 契约。每维四栏：问什么 / 去哪读 / 证据形式 / 典型错答。零取值 |
| 知识落点 | `templates/domain-doc-template.md`（新增） | 仓库内域文档骨架，frontmatter 复用卡片字段名，让同一个 drift 规则生效 |
| 知识源 | `scripts/paths.sh`、`scripts/knowledge_drift.sh` | `$DOMAIN_DOCS`；默认扫描加 `docs/domain/*.md` 与 `GLOSSARY.md`，并去重 |
| 接线 | `stages/oncall/SKILL.md`、`oncall/references/{routing,capture,knowledge-sources}.md`、`references/{scope,project-index}.md`、`SKILL.md`、`README.md` | 统一加载顺序：仓库内 `docs/domain` → `$KNOW`（标「未核对」）→ 仓库 `docs/`（降级区）；团队共识写 `docs/domain`，个人线索写 `$CARDS` |
| 测试 | `scripts/check_runner.py` | `git_commit_all()` + `case_domain_docs`（`paths.sh` 能取到、drift 判 `FRESH`） |

## 4 契约影响

不适用：本仓无对外 API。`paths.sh` 只新增变量 `DOMAIN_DOCS`，既有变量不变；`knowledge_drift.sh` 的 CLI 不变。

## 5 验证记录

| 门 | 命令 | 结果 |
|---|---|---|
| 回归 | `bash scripts/verify.sh` | PASS ×51，`OK` |
| 运行记录 | `specs/business-model/verify.log` | `exit 0` |
| 域文档判级 | 临时仓 `docs/domain/order.md` | `FRESH`（`case_domain_docs`） |

## 6 文档审计（提交前门）

| 文档 | 是否需要同步 | 状态 | 备注 |
|---|---|---|---|
| `specs/business-model/{decision,check}.md` | 是 | 已同步 | `check.md` §5 写明「本轮没解决什么」 |
| `README.md` 知识层段 | 是 | 已同步 | 维度 / 去哪找 / 落在哪 三段 |
| `config.example.yaml` | 不需要 | 不适用 | `domains` 说明已在上一提交补齐 |
| `CONTEXT.md` / `GLOSSARY.md` | 不需要 | 不适用 | 本仓没有；模板已就位，等真有域文档时再用 |
| 九步链产物（spec/impact/plan/rollback/interface-test） | 不需要 | 不适用 | L1（`change` 三步） |

接受的文档风险：无。

## 7 仍然欠着的

没有真实业务仓库的端到端演练；`$KNOW` 存量未迁；语义门、`passes.log` 自授权、`gate_check` shell 门（后两项下一轮做）。
