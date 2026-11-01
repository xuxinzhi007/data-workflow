# business-model 核对

## 1 命令与结果

```
cmd bash scripts/verify.sh
exit 0
```

verify.log 里 51 条 `PASS` 之后打印 `OK`。完整输出在 `specs/business-model/verify.log`。

## 2 验收条件逐条对照

| # | decision.md 里写的验收 | 结果 | 证据 |
|---|---|---|---|
| 1 | 维度文件能被 `oncall` 与 `scope.md` 直接引用 | 达到 | `references/business-model.md`（九维度）；`oncall/SKILL.md` 的「按九个维度逐维度取证」；`scope.md` 的域文件优先级段；`routing.md` 通用表首行 |
| 2 | `paths.sh` 输出 `DOMAIN_DOCS` | 达到 | `PASS paths.sh exposes the repo domain docs` |
| 3 | `knowledge_drift.sh` 默认扫描含 `$REPO/docs/domain/*.md` 且能判级 | 达到 | `PASS drift grades the repo domain doc`（临时仓里 `FRESH`） |
| 4 | `verify.sh` exit 0 且有对应用例 | 达到 | 本节 §1 + 新增 `case_domain_docs` |

## 3 diff 有没有超出 decision.md

| 决定条目 | 落点 |
|---|---|
| 1 九个维度 | 新增 `skills/data-workflow/references/business-model.md` |
| 2 仓库内域文档模板 | 新增 `skills/data-workflow/templates/domain-doc-template.md`（frontmatter 复用卡片字段名，让同一个 drift 规则生效） |
| 3 落点接线 | `scripts/paths.sh`（`DOMAIN_DOCS`）、`scripts/knowledge_drift.sh`（默认目标加 `docs/domain`、`GLOSSARY.md`，去重） |
| 4 仓库内优先写进文档 | `stages/oncall/SKILL.md`、`stages/oncall/references/routing.md`、`scope.md`、`capture.md` 落点表、`knowledge-sources.md` 信任表、`project-index.md`、`SKILL.md` 选型表、`README.md` 知识层段 |
| 5 回归用例 | `check_runner.py`：`git_commit_all()` + `case_domain_docs` |

**超出范围的：无。** 没有新建空目录、没有迁 `$KNOW` 内容、没有写任何业务取值、没有动 `feature` 九步链。

## 4 行为变化

- `oncall` 与 `scope.md` 的域文件加载顺序变成：`$DOMAIN_DOCS/<域>.md`（仓库内）→ `$KNOW`（补充源，标「未核对」）→ 仓库 `docs/`（降级区）。
- `knowledge_drift.sh` 默认扫描多了三类目标：`$REPO/docs/domain/*.md`、`$REPO/GLOSSARY.md`、`$REPO/CONTEXT.md`（最后一项原来就有），并去重。**没有 `docs/domain` 的仓库行为不变。**
- `capture.md` 的落点表从「本技能唯一写入位置是 `$CARDS/`」改成「团队共识写 `docs/domain/`（用户确认后），个人线索写 `$CARDS/`」。

## 5 这个改动**没有**解决什么（重要）

`business-model.md` 是**骨架**：它告诉 agent 看哪九个维度、去哪读、证据长什么样。它**不会**让分析自动变准——准不准取决于：

1. 有没有人真的把 `docs/domain/<域>.md` 写出来（本仓自己没有，也不该替别的仓库造）。
2. 结论有没有回代码核对（这条靠 `scope.md` 的四态 + `UNVERIFIED`，不靠这个文件）。

所以这一轮把「不可能」变成「可能」，但没有把「可能」变成「已经」。真正的验证要在有真实业务仓库时做一次端到端演练——那是下一轮的事，不是这一轮的成果。

## 6 仍然欠着的

| 欠着 | 为什么这次不做 |
|---|---|
| 没有真实业务仓库的端到端演练 | 需要用户的知识源与一个真实域；本仓没有业务代码 |
| `$KNOW` 既有内容迁进仓库 | 要人逐条判断哪条还成立，属独立工作 |
| 语义门（门只识字面量） | 脚本判断不了"未知写得对不对" |
| `passes.log` 自授权、`gate_check` shell 门、`stack` 不阻塞、`check_runner.module()` 的 `python3` | 见前两轮 `check.md` §5，未变 |
| data-service 特化下沉到 profiles、`SKILL.md` description 瘦身（1328 字） | 属 P2 剩余部分，与「业务分析」这条主线可以分开做 |
