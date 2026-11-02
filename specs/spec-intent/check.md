# spec-intent 核对

## 命令与结果

```
$ python3 skills/data-workflow/scripts/check_runner.py
...
PASS change.json stage 1 requires 我理解你要的是
PASS change.json stage 1 requires 可能理解错
PASS decision-template.md contains 我理解你要的是
PASS feature.json stage 1 requires 我理解你要的是
PASS feature.json stage 1 requires 可能理解错
PASS spec-template.md contains 我理解你要的是
PASS spec-template.md contains 可能理解错
OK
```

exit 0。断言 79 → 90，case 32 → 33。

`specs/spec-intent/verify.log` 第一行是 `exit 0`。

## 验收条件逐条核对

| 决定里的条件 | 是否达到 | 证据 |
|---|---|---|
| `spec-template.md` 头部含两行 | 是 | `contains spec-template.md` 两条断言 |
| `feature.json` 第 1 步 `requires` 加两行 | 是 | `feature.json stage 1 requires` 两条断言；实测缺行时打印「缺：我理解你要的是、可能理解错、怎样算满足」 |
| 「无歧义」是合法答案 | 是 | 门仍是字面量子串检查，不检查内容；`change` 侧 `case_intake` 已覆盖 |
| 照抄给 NOTE 不阻塞 | 是 | `restated_raw` 与工作流无关，`case_restated_raw` 已覆盖；feature 复用同一函数 |

## 端到端实测（临时仓库）

```
start feature add-cancel "给订单加取消状态"
  → STACK 提示（未声明 stack=go，符合既有设计）
  → STAGE 1 需求与负债评估 / NEED spec.md

spec.md 只写「原话 + 本质」
  → GATE 缺：我理解你要的是、可能理解错、怎样算满足

spec.md 补全两行 + 怎样算满足
  → 推进到 STAGE 2 影响面评估 / NEED impact.md
```

## 反向验证（故意破坏）

把 `spec-template.md` 里的「我理解你要的是」改成「我理解的需求是」，制造模板与 `requires` 措辞不一致：

```
FAIL spec-template.md contains 我理解你要的是
```

恢复后 OK。这条断言正好钉住「措辞不一致 → 字面量门永远匹配不上」这个坑。

## 一处措辞统一

`change` 和 `feature` 两边用同一组字面量（`我理解你要的是` / `可能理解错`），没有另发明一套。`restated_raw` 也因此在两个工作流里都生效，不必写两套。

## 超出范围的：无

没有改 `open_decision` 的误判逻辑（遗留 2）。没有动 `bugfix` / `hotfix` / `review-only`。

## 遗留

1. **`open_decision` 无法区分「正文引用关键字」和「用关键字下指令」。** 上一轮写 decision.md 时踩到：正文里提到那个标记词，`next` 就误打 OPEN。修法有两类——只看列表行首，或文档约定不裸引。两种都改变门行为，需单起一次。
2. `bugfix` / `hotfix` 的第 1 步是否也需要理解确认，未评估。这两个工作流的第一阶段分别是「根因定位」和「止血决策」，性质不同，不该照搬。
