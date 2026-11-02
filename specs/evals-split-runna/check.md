# evals-split-runnable 核对

## 命令与结果

```
$ python3 skills/data-workflow/scripts/check_runner.py
...
PASS every eval names the check_runner case that covers it (missing: [])
PASS every named case actually exists in check_runner.py (missing: [])
PASS human review cases live in docs/review-cases.md
PASS card pins verified_commit to current HEAD
PASS card has non-empty source_paths
PASS card has non-empty invalidates_when
PASS card has non-empty symptoms
PASS card is findable by symptom keyword
PASS drift grades the freshly written card as FRESH
PASS SKILL.md stays under 200 lines (got 86)
PASS SKILL.md does not glob-load references
PASS description stays short (got 179 chars)
OK
```

exit 0。断言数 58 → 74，case 数 28 → 31。

`specs/evals-split-runna/verify.log` 第一行是 `exit 0`。

## 验收条件逐条核对

| 决定里的条件 | 是否达到 | 证据 |
|---|---|---|
| `evals.json` 每条都能被 `verify.sh` 判定 | 是 | 5 条全部有 `machine_case`；`case_evals_are_runnable` 断言 `missing: []` |
| 带 `machine_case` 且指向真实 case | 是 | 断言逐个在 `check_runner.py` 里查 `def case_xxx(` 存在 |
| 判不了 9 条移到 `docs/review-cases.md` 并标未执行 | 是 | 文件 212 行，含「上次执行 / 未执行」状态表 |
| README 不再声称被执行过 | 是 | 改成两处对照表，并写明「后一类至今没有执行记录」 |
| 塞回判不了的用例时 `verify.sh` 失败 | 是 | 注入 `id:99` 无 `machine_case` → `FAIL ... (missing: [99])`，恢复后 OK |

## 反向验证（故意破坏，确认断言会响）

| 破坏方式 | 实际结果 |
|---|---|
| `description` 塞到 419 字符 | `FAIL description stays short (got 419 chars)` |
| `evals.json` 加一条无 `machine_case` 的用例 | `FAIL every eval names the check_runner case that covers it (missing: [99])` |

两条都先 FAIL、恢复后 PASS。断言不是摆设。

## 超出范围的：无

没有实现自动跑 agent 的评分器（决定里明确不做）。没有改任何阶段正文。没有动门禁语义。

## 遗留

1. 9 条人工用例仍是「未执行」。这需要 data-service 环境和人来跑，本轮不覆盖。
   `docs/review-cases.md` 的状态表已如实写「未执行」，没有假装已验证。
2. 顺带修掉两处零覆盖：`#5` 卡片回写（原来只有 drift 判级，没有字段完整性检查）、`#6` 常驻成本（原来完全没有）。
