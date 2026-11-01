# evidence-anchor 核对

## 1 命令与结果

```
cmd bash scripts/verify.sh
exit 0
```

verify.log 里 60 条 `PASS` 之后打印 `OK`。本运行自己的证据行：

```
stage=1 requires=ok gate_check=none verify=none head=8040733 at=2026-11-01T19:02:05+08:00 by=runner
stage=2 requires=ok gate_check=ok   verify=exit0 head=8040733 at=2026-11-01T19:07:39+08:00 by=runner
```

## 2 验收条件逐条对照

| # | decision.md 里写的验收 | 结果 | 证据 |
|---|---|---|---|
| 1 | `done`/推进后 `evidence.log` 多一行，含 `stage/门/退出码/head/by=runner` | 达到 | 上面两行；`PASS advancing appends an evidence line` |
| 2 | HEAD 变化后 `next` 打 `NOTE`，不阻塞 | 达到 | `PASS head drift shows up as a note`（新提交后 `NOTE 工作树已变`，`next` 返回码仍是 0） |
| 3 | 有拍板时 `next` 打 `DECIDED` | 达到 | `PASS next echoes the last decision` |
| 4 | `SKILL.md` 里不再有阶段→文件映射，只留四个非工作流入口 | 达到 | `PASS SKILL.md keeps only the four non-workflow entries` |
| 5 | `verify.sh` exit 0 | 达到 | §1 |

## 3 diff 有没有超出 decision.md

| 决定条目 | 落点 |
|---|---|
| 批 1 证据行 | `workflow_next.py`：`run_verify` 改为返回退出码、`record_evidence()`、`advance` 的两处调用点、`git_head()`、`last_evidence_head()`、`head_note()` |
| 批 1 派生输出 | `print_context()` 加 `DECIDED` / `NOTE`；`last_decision()` 从产物读 `已拍板：` |
| 批 2 删表 | `SKILL.md` 删 10 行阶段表 → 4 个非工作流入口；两处提到"选型表"的句子改写 |
| 文档 | `README.md` 两处、`references/{commands,artifact-tree}.md`、`evals/evals.json` 加一条路由用例 |

**超出范围的：无。** 没动 `gate_edit`、没给 hook 加新依赖、没改 `run.json` 字段（`head` 落在证据行里，不进 `run.json`）、没碰域文档同步门与 NOTICE 静音（上轮评估里已定为"缓/不做"）。

## 4 行为变化

- `next` / `DONE` 的输出多两行（有拍板才有 `DECIDED`，HEAD 漂了才有 `NOTE`）；两者都不改变返回码。
- `done` 多写一个文件 `specs/<feature>/evidence.log`（只追加）。
- `SKILL.md` 少 10 行；「用户点名一个阶段」现在走"先 `start`，再按 `READ`"，不再查表。
- `run_verify()` 的返回值从 bool 改成退出码（内部函数，CLI 行为不变）。

## 5 已知限制与仍然欠着的

| 项 | 说明 |
|---|---|
| `evidence.log` 只靠约定"只由 runner 写" | 行尾 `by=runner` 是标记，不是强制。要强制得像 `approve` 那样加校验，属下一轮 |
| `NOTE` 只比 HEAD，不比工作树 | 未提交的改动不会触发；`git status` 每次调用成本更高，故意不做 |
| `DECIDED` 取的是"文件名排序下最后一条 `已拍板：`" | 一条运行里多次拍板时，选的是最后写入的那个文件里的最后一条；够用，但不是严格时序 |
| 域文档同步门 | 上轮评估定为缓：没有真实 `docs/domain` 时它永远是"不需要" |
| NOTICE 按天数静音 | 上轮评估定为不做：忘了收尾的运行会永远静音 |
| `hook` 读 `evidence.log` | 上轮评估定为不做：会让稳定组件依赖新状态 |
| 语义门、`stack` 硬阻塞、九项负债搬迁、真实业务仓库演练 | 与前几轮一样，仍然欠着 |
