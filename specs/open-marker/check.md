# open-marker 核对

## 命令与结果

```
$ python3 skills/data-workflow/scripts/check_runner.py
...
PASS file_is_open('正文提到就不算:\n- 现有能力：`open_decision') should be False
PASS file_is_open('待拍板') should be True
PASS file_is_open('- 待拍板') should be True
PASS file_is_open('- 待拍板：用全量还是三态？') should be True
PASS file_is_open('> 待拍板') should be True
PASS file_is_open('# 决定\n\n- 原话：改一处\n- 待拍板\n') should be True
PASS file_is_open('- 待拍板\n已拍板：用全量\n') should be False
PASS file_is_open('没有这个标记\n') should be False
PASS closed markers do not reopen the file
OK
```

exit 0。断言 90 → 99，case 33 → 34。

`specs/open-marker/verify.log` 第一行是 `exit 0`。

## 验收条件逐条核对

| 决定里的条件 | 是否达到 | 证据 |
|---|---|---|
| 正文提到不触发 OPEN | 是 | 第 1 条样本 `should be False`；本文件自己的 decision.md 就是活证据——它引用了标记词，`next` 仍打 DO |
| 行首标记仍触发 | 是 | `- 待拍板` / `> 待拍板` / 无前缀 均 True |
| `已拍板：` 行首能关闭 | 是 | `closed markers do not reopen the file` |
| 断言变红才算修好 | 是 | 见下 |

## 反向验证

修改后先跑一遍，`case_answer` 和 `case_decided` 两个旧夹具挂了：

```
FAIL reply is recorded
FAIL next echoes the last decision
```

两者都写 `范围待拍板`（标记不在行首）——**这正是被修掉的那类误报**。改夹具为 `- 待拍板：…` 后转绿。这个顺序证明新逻辑真的改变了判定面，不是改了个措辞。

## 修到的两处夹具

| 夹具 | 原写法 | 现写法 |
|---|---|---|
| `case_answer` | `范围待拍板` | `- 待拍板：用全量还是三态？` |
| `case_decided` | `范围待拍板` | `- 待拍板：范围多大？`（并补齐第一屏 5 行） |

## 超出范围的：无

`unmet_requires` 的字面量检查未动——它按设计就该在全文找「原话」「本质」这些，和标记词不是一类。

## 遗留

`bugfix` / `hotfix` 是否需要理解确认，仍未评估。上一轮 check.md 已说明不建议照搬（一个重找证据、一个时间敏感）。
