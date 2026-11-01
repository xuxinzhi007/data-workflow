# evidence-gates 核对

## 1 命令与结果

```
cmd bash scripts/verify.sh
exit 0
```

verify.log 里 49 条 `PASS` 之后打印 `OK`。完整输出在 `specs/evidence-gates/verify.log`。

## 2 验收条件逐条对照

| # | decision.md 里写的验收 | 结果 | 证据 |
|---|---|---|---|
| 1 | `start` 存原话，`next` 打印 `RAW` | 达到 | `PASS start stores the raw request verbatim`、`PASS complete intake advances and echoes the raw request` |
| 2 | `decision.md` 缺 `原话`/`本质`/`未知` 任一行 → `next` 与 `done` 打 `GATE` 并停 | 达到 | `PASS missing 未知 stops at the gate`；`done` 走同一函数，停在返回码 1 |
| 3 | `check.md` 缺 exit 行 → 同上 | 达到 | `change.json` stage 3 的 `requires: ["exit","verify.log"]`；本轮 `next` 在写本文件前就打了 `NEED .../check.md` |
| 4 | `paths.sh` 输出 `DOMAINS='a,b'` | 达到 | `PASS paths.sh exposes the configured domains` |
| 5 | `routing.md` step 0 空 `$CARDS` 明确跳过 | 达到（文档改动，无自动用例） | `stages/oncall/references/routing.md` step 0 的 `if [ -z "${CARDS:-}" ]` 分支 |

第 5 条没有自动用例，原因写在 §5：那段是给 agent 读的 shell 片段，不是仓库里的脚本。

## 3 diff 有没有超出 decision.md

| 决定条目 | 落点 |
|---|---|
| 1 `requires` 内容门 | `workflow_next.py` 的 `unmet_requires()`（`show` 与 `cmd_done` 两处调用）、`workflows/change.json`（stage 1 + 3）、`workflows/feature.json`（stage 1） |
| 2 `raw_request` | `cmd_start()` 第 4 参、`print_context()` 的 `RAW` 行、`usage()` |
| 3 模板 5 行受理单 | `templates/decision-template.md`、`templates/spec-template.md`、`workflows/change.md` 第 1/3 步 |
| 4 `routing.md` 空 `$CARDS` | `stages/oncall/references/routing.md` step 0 |
| 5 `domains` 接线 | `scripts/paths.sh` 的 `emit DOMAINS domains`、`routing.md` step 1、`config.example.yaml` 注释 |

同一批改动带上的（属"让改动可验证"，不新增语义）：

- `check_runner.py`：新增 `case_intake` / `case_domains`；`reach_code()` 与异仓用例的 `decision.md` 补成 5 行（否则新门会拦测试自身）。
- `docs/competitive.md` + `README.md` 一条指针：这是用户这次要的"价值对照"，属交付物，不是实现。

**超出范围的：无。** 没有新增工作流、没有动 hook 的放行语义、没有碰 `stages/` 下的分析正文（只改 `routing.md` 的两处写法与 `change.md` 的步骤说明）。

## 4 行为变化与迁移

- 新 `start` 会写 `raw_request`；旧运行记录缺这个字段时**不会**被拦（`print_context` 只是不打印 `RAW`）。
- **旧 `decision.md` 会在升级后立刻打 `GATE`**：缺 `原话`/`本质`/`未知` 就停。补法：把用户原话粘进去，写上本质与未知（没有就写"无"）。这是本意，不是回归。
- `feature` 链的 `spec.md` 现在要求出现 `本质` 和 `怎样算满足`；`templates/spec-template.md` 已带这两行。

## 5 仍然欠着的

| 欠着 | 为什么这次不做 |
|---|---|
| 门是**字面量门**：只查"产物里有没有这几个字"，不查写得对不对 | 语义门要模型判断，脚本做不了；强门要靠 review 阶段与人拍板 |
| `gate_check`（每 stage 一条 shell 命令做门） | 通用技能里没有通用命令；等 P2 的 profiles 按仓库给 |
| `passes.log` 仍由模型手写（自授权） | 审计模式（D1）下把放行绑到拍板回话只增摩擦、不增约束；等真要 enforce 时一起做 |
| `routing.md` 的空 `$CARDS` 守卫只有文档、无回归 | 那段是给 agent 读的片段，没有脚本可测。要测就得抽成一个 `scripts/cards.sh`，属 P2 |
| `check_runner.module()` 仍用 `python3 -c` 探测 pytest | 本机 `python3` 是占位程序，导致该用例走"选择失败即 RED"的分支；结论仍正确但标签名不实，属 P1.5 |
| `stack` 只打警告，不阻塞 | 会破坏异仓 `start feature` 的既有用例与本轮无关 |
| 业务分析骨架、知识落点进仓库、`description` 瘦身 | P2，见 `docs/competitive.md` §3「真不如人的地方」 |
