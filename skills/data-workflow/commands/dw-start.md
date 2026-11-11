---
description: 新开一次运行。任意仓库的一次改动或定架构用 change
---

**先判断该不该 start**（见 `{{SKILL}}/SKILL.md` 的「怎么选工作流」）：
只梳理、只排查、只读代码、不改代码——**不 start**，直接读 `{{SKILL}}/stages/oncall/references/routing.md`。
要改代码、或者要定架构，才往下走。

问清 feature 名。任意仓库的一次改动或定架构，运行 `{{RUNNER}} start change <feature> "<用户原话>"`。
data-service（Go 栈）实例的 L3 变更用用户选的 workflow：`feature`、`bugfix`、`hotfix`、`review-only`。
开完只做 `next` 打印的那一件。
