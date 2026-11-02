# intent-confirm 核对

## 命令与结果

```
$ python3 skills/data-workflow/scripts/check_runner.py
...
PASS gate also demands the understanding lines
PASS understanding lines alone do not slip past the gate
PASS copying the raw line raises a note
PASS the note does not block progress
PASS rephrasing in own words raises no note
OK
```

exit 0。断言 74 → 79，case 31 → 32。

`specs/intent-confirm/verify.log` 第一行是 `exit 0`。

## 验收条件逐条核对

| 决定里的条件 | 是否达到 | 证据 |
|---|---|---|
| 模板含两行 | 是 | `templates/decision-template.md` 有「我理解你要的是」「可能理解错的地方」 |
| `requires` 加这两个字面量，缺了打 GATE | 是 | `change.json` requires 3 项 → 5 项；实测只写原话+本质时打印「缺：我理解你要的是、可能理解错」 |
| 照抄原话给 NOTE 不阻塞 | 是 | `case_restated_raw`：「copying the raw line raises a note」+「the note does not block progress」 |
| 「无歧义」是合法答案 | 是 | `case_intake` 写「无歧义」后 `next` 打 DO |
| 门只判有无不判好坏 | 是 | `unmet_requires` 逻辑未改，仍是字面量子串检查；写「本质：改」也能过 |

## 端到端实测（临时仓库，非本仓库）

```
场景 A · 含糊
  start change v3 "那个东西改一下，不太好用"
  decision.md 写「我理解你要的是：让某个功能更顺手，但没说哪个功能」
             「可能理解错的地方：「那个东西」指哪个功能不明；…」
  next        → OPEN，要求先 wait
  wait v3 "你说的『那个东西』是订单导出吗？" "是订单导出，导出太慢"
              → WAIT + REPLY
  answer v3 "是订单导出，导出太慢"
              → 记录回到 working，decision.md 尾部追加「已拍板：是订单导出，导出太慢」

场景 B · 照抄
  「我理解你要的是」逐字复制原话
              → NOTE（不阻塞），仍继续 DO

场景 C · 说清楚
  「我理解你要的是：导出默认集固定三态，不再交互追问」
  「可能理解错的地方：三态具体是哪三个尚未确认」
              → 无 NOTE，直接 DO
```

三种场景行为都符合决定里写的。

## 反向验证（故意破坏）

| 破坏方式 | 实际结果 |
|---|---|
| 夹具只写原话 + 本质 | `GATE 缺：我理解你要的是、可能理解错`（`understanding lines alone do not slip past the gate` 也覆盖了“只补未知仍被拦”） |
| 把理解行写成原话复制 | `NOTE … 看起来是原话的复制`，但 `DO` 照出 |

## 超出范围的：无

没有新建 skill，没有引入模型判断，没有改 `unmet_requires` 的判定语义。`feature.json` 的 `requires` 未动（决定里已记为遗留）。

## 过程中发现的一个真问题（本轮未修）

本次自己的 `decision.md` 在「现有能力」里引用了门的关键字，导致 `open_decision` 把叙述当成未决标记，`next` 误打 OPEN。改成描述性说法后恢复正常。

这是内容门的通用缺陷：**它无法区分“我在说这个词”和“我用这个词下指令”**。修法要么改判定（只看列表行首），要么文档里约定不要裸引关键字。两种都会改变门的行为，超出本次范围，记为下一步候选。

## 遗留

1. `feature.json` 第 1 步仍是 `requires: [本质, 怎样算满足]`，没有理解确认两行。L3 变更同样需要这条回路。
2. 上面那条「正文引用门关键字会误判」，需要在 `open_decision` 上做一次小改造。
