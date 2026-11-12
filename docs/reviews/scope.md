# 架构评审范围

- 仓库：data-workflow
- 日期：2026-11-12（Asia/Shanghai）
- HEAD：fe2b141（feat: 新增架构深挖工作流和报告格式）
- 工作树：评审开始时干净；本轮只新增 `docs/reviews/` 下产物

## 这次扫哪里

用户点名的是「当前这个项目」整仓库，没有指定某个 subsystem。按 YAGNI，权重压在最近真的在改的地方，而不是把所有目录走成一轮通用建议。

`git log --oneline -40` 再按文件计次，热点集中在这一簇（不是「散得没热点」，因此不放宽成全仓均扫）：

| 次数（近 40 提交） | 文件 |
|---|---|
| 23 | `skills/data-workflow/scripts/check_runner.py` |
| 22 | `README.md` |
| 21 | `skills/data-workflow/SKILL.md` |
| 14 | `skills/data-workflow/scripts/workflow_next.py` |
| 14 | `evals/evals.json` |
| 12 | `scripts/install.sh` |
| 11 | `AGENTS.md` |
| 10 / 9 | `workflows/change.json`、`workflows/feature.json`、`references/edit-gate.md` |

实现体量也集中在同一簇：`check_runner.py`（2756 行，回归）、`workflow_next.py`（1368 行，推进器）、`hooks/gate_edit.py`（483 行）、`scripts/install.sh`（461 行）。

因此本轮扫描：

- 运行时推进：`workflow_next.py`、`layout.py`、各 `workflows/*.json`
- 写入门禁与会话注入：`hooks/gate_edit.py`、`hooks/session-start`
- 工作流定义怎么到达 AI：`SKILL.md`、`commands/*.md`、阶段文件与 JSON 提示字段的关系
- 产物落点：JSON 里的 `artifacts_root` 与 runner 实际解析

`docs/dev/` 下的 known issues / learnings / claim-register 等只当痛点索引，每条 finding 都回源码核对；已修的（如 `print_stage_hints` 补上、指纹极性取反、`stage_gates_block` 抽出、命令路径安装时注入）不当前问题。

## 为什么是这里

加深一个 module 的回报是以后改它更容易。近 40 次提交反复改的就是 runner、门、工作流 JSON 和安装入口——摩擦如果还在，也最可能还在这里。

## 明确不扫什么

- `GLOSSARY.md`：无。跳过，不现编。
- `docs/adr/`：无。跳过，不现编。因此本轮没有「与某条 ADR 冲突、是否 reopen」的项。
- `docs/dev/research/`（claude-code、phone-to-phone 等）和竞品对照里的上游技能包：不是本仓运行时。
- `stages/excalidraw-diagram/` 及其生成脚本：近 40 提交不是热点。
- `profiles/go-kratos/`、`proto_contract.py`、`contract_diff.sh`、`knowledge_drift.sh` 的实现细节：它们面向目标业务仓（data-service 实例），不是本仓最近在改的主体。
- `evals/evals.json` 条目清单、`scripts/honesty_stats.py` 的统计口径：属于试验与回归内容，不把「未跑的 C3/C9 效果实验」写成结构摩擦。
- `docs/guide-*`、`assets/` 两张图是否美观：不在本轮加深范围内。
- 已从版本库移除的 `specs/` 历史运行：可作经验索引，不当现行结构。

## 历史痛点里已核对、本轮不当现行问题的

- workflow JSON 的 `self_check` 等提示曾到不了 AI：现已由 `workflow_next.print_stage_hints` 转发，且有 `case_no_hints_switch` 锁开关。
- `close_if.fingerprint` 复用 `run_gate_check` 时极性曾写反：现已在 `cmd_close` 取反，并有两端用例。
- `show` 与 `done` 对 `code` 阶段门不一致：现已抽出 `stage_gates_block`。
- 命令文件写死开发路径、新项目静默丢命令：安装脚本已按落点替换 `{{RUNNER}}` / `{{SKILL}}`，并 `mkdir -p`。
