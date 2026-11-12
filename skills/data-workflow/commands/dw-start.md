---
description: 新开一次运行。任意仓库的一次改动或定架构用 change
---

**先判断该不该 start**（见 `{{SKILL}}/SKILL.md` 的「怎么选工作流」）：
只梳理、只排查、只读代码、不改代码——**不 start**，直接读 `{{SKILL}}/stages/oncall/references/routing.md`。
要改代码、或者要定架构，才往下走。

问清 feature 名。任意仓库的一次改动或定架构，运行 `{{RUNNER}} start change <feature> "<用户原话>"`。
data-service（Go 栈）实例的 L3 变更用用户选的 workflow：`feature`、`bugfix`、`hotfix`、`review-only`。
开完只做 `next` 打印的那一件。

**`ALREADY` 不是失败。** 它说明同名已有一条没结束的运行。它会把旧运行的 `RAW`（用户原话）和 `DECIDED`（最近一次拍板）一起打出来——
对照一下：
- 同一件事 → 跑 `next <feature>` 接着做，不要重开。
- 另一件事 → 跑 `start <workflow> <feature> --new`，它会开成 `<feature>-2`，旧记录原样留着。
- 本来就不是要做的事（例如那个 bug 已经修好了）→ 不要硬推旧链条，让用户决定 `close` 还是 `abandon`。
