# enforce-and-profile 核对

## 1 命令与结果

```
cmd bash scripts/verify.sh
exit 0
```

verify.log 里 56 条 `PASS` 之后打印 `OK`。完整输出在 `specs/enforce-and-profile/verify.log`。

## 2 验收条件逐条对照

| # | decision.md 里写的验收 | 结果 | 证据 |
|---|---|---|---|
| 1 | `approve` 需要一次已答复的拍板 | 达到 | `PASS approve refuses without an answered question`（无 `last_reply` → `NEED_ANSWER`，不写文件） |
| 2 | `gate_strict` 下手写的行不作数 | 达到 | `PASS hand-written pass line is ignored under gate_strict` |
| 3 | `approve` 写完后真能放行 | 达到 | `PASS approve after a real reply unlocks the write` |
| 4 | `gate_check` 跑命令、非 0 停 | 达到 | `PASS gate_check blocks a clean working tree`、`PASS gate_check passes when the tree changed` |
| 5 | `change` 编码阶段检查「有没有改动」 | 达到 | `workflows/change.json` stage 2 的 `gate_check`；上面两条用例走的就是它 |
| 6 | `profiles/go-kratos/profile.md` 存在 + 四个文件有守卫 | 达到 | 新增 profile；守卫加在 `requirement-analysis/SKILL.md`、`impact-assessment/SKILL.md`、`change-review/SKILL.md`、`templates/plan-template.md`（`interface-test` 原来就有） |
| 7 | description ≤ 300 字 | 达到 | 1328 → **179 字** |

## 3 diff 有没有超出 decision.md

| 决定条目 | 落点 |
|---|---|
| D1 放行行只由 approve 写 | `workflow_next.py`（`cmd_approve`、`answer` 保留 `last_reply`、`usage`、子命令分发）；`gate_edit.py`（`read_passes` 带 `approved` 标记、`strict` 下过滤、拒绝理由改成指路 `approve`）；`edit-gate.md`、`commands.md`、`change.md`、`tech-design/SKILL.md`、`config.example.yaml` |
| D2 `gate_check` | `workflow_next.py`（`run_gate_check`、`tail_lines`、`show`/`cmd_done` 两处调用）；`change.json` stage 2 |
| C profile | 新增 `profiles/go-kratos/profile.md`；四个文件加守卫；`SKILL.md` 正文加一句指过去 |
| C description | `SKILL.md` frontmatter：1328 → 179 字 |

**超出范围的：无。** 没有新增工作流/阶段，没有改 `design`/`waiver` 的覆盖语义，没有把 `gate_strict` 默认打开，没动 `evals.json`。

## 4 行为变化与迁移

1. **手写的 `design`/`waiver` 行在 `gate_strict` 下不再作数。** 迁移：跑一次 `wait` → `answer` → `approve`。默认（audit）模式仍兼容旧行，不会突然拦死。
2. **`change` 的编码阶段要求工作树真的有改动。** 已知盲区两个：① 改动只落在被 gitignore 的文件里（例如只改了 `specs/` 里的东西）会被误判；② 不是 git 仓时这道检查直接跳过（无法判定）。两条都写进了 `change.json` 的 `gate` 文字。
3. **description 从 1328 字压到 179 字**，触发词一个没删；删掉的是原先塞在 description 里的规则（运行记录、verify、scope、受保护路径）。这些规则在正文与 `references/` 里都有唯一副本。

## 5 仍然欠着的

| 欠着 | 为什么这次不做 |
|---|---|
| `gate_check` 只接了 `change` 一处 | Go 实例的门需要按仓库给的命令，等九项负债正文搬进 profile 时一起接 |
| `stack` 只提示、不阻塞 | 硬阻塞会破坏既有用例与其他仓库的既有运行 |
| 九项负债正文仍在通用阶段文件里（只有守卫句） | 搬迁会改链接与语义，要等有真实 Go 仓库可回归 |
| 语义门 | 脚本判断不了"未知写得对不对" |
| `shell_destinations()` 盲区、`contract_diff.sh` 的 `python3`、`check_runner.module()` | 与这两轮无关 |
| 真实业务仓库的端到端演练 | 需要用户的知识源与一个真实域 |
