# docs-drift 核对

## 命令与结果

```
$ bash scripts/verify.sh
...
PASS README first-screen matches change.json requires (missing: [])
PASS docs/scripts.md lists every skill script (missing: [])
PASS competitive.md does not hardcode the assertion count
OK
```

exit 0。断言 123 → 127。

`specs/docs-drift/verify.log` 第一行是 `exit 0`。

## 整理过程：查了什么

不是只看代码，逐项核对了七类一致性：

| 检查项 | 方法 | 结果 |
|---|---|---|
| md 相对链接 | 正则提取 `](xxx.md)` 逐个 `os.path.exists` | **0 失效** |
| 死文件 | 对每个 md 统计被其他文件引用次数 | **0 个零引用** |
| evals ↔ case 映射 | 读 `machine_case` 字段，查 `def case_xxx(` | **5/5 成立** |
| 未完成运行 | `workflow_next.py next` | 无，15 个全 done |
| 工作流 requires ↔ 模板 | 逐个 workflow 读 stage1 | change/feature 已配对 |
| README ↔ requires | 人工比对 | **不符，缺 2 项** |
| scripts.md ↔ 实际目录 | `os.listdir` 比对 | **漏 3 个** |

## 修了什么

### 1. README 的流程示例过时（实战撞过）

```diff
- # 写 decision.md：原话 / 本质 / 验收 / 未知 / 这次不做
+ # 写 decision.md 第一屏：原话（一字不改）/ 我理解你要的是 / 可能理解错的地方 /
+ #                        本质 / 怎样算满足 / 未知 / 这次不做
+ #   含糊时把歧义写进「可能理解错的地方」再 wait，不要先猜
```

后果很直接：新人照 README 写会被 GATE 拦住，还分不清是文档错还是自己错。上一轮在 `system_tags_editor` 就是这么卡住的。

### 2. `competitive.md` 硬编码「47 条回归」

实际 123 条。改成「回归集，末行打印 OK」，并把「文档不得写死这个数字」做成断言。

**理由**：这个数每加一条测试就过期，记它等于记一个必然变成假话的东西。

### 3. `docs/scripts.md` 漏 3 个脚本

补上 `find_python.sh`、`layout.py`、`check_runner.py`。

## 新增的两条断言

```python
# README 第一屏必须覆盖 requires 里的每一项
missing = [k for k in req if k not in text]

# scripts.md 必须列出 skills/scripts/ 下每个文件
missing = [n for n in os.listdir(script_dir) if n not in scripts_md]
```

断言只查「有没有」，不查「写得好不好」——判断力留给人和模型。

## 反向验证

| 破坏方式 | 实际结果 |
|---|---|
| README 第一屏改回旧写法 | `FAIL README documents the decision.md first screen` |
| `scripts.md` 删掉 `layout.py` 那行 | `FAIL lists every skill script (missing: ['layout.py'])` |
| `competitive.md` 写死数字 | `FAIL does not hardcode the assertion count` |

三条都先红后绿。

## 一次失败的尝试（记下来防止重犯）

最初想让断言「跑一遍 verify 数 PASS 行」来自检数字。结果：

1. 递归调用自己 → 300 秒超时
2. 加环境变量守卫后，内层只跑到 75 条（部分 case 被跳过）→ 数字仍不对

改成「不硬编码数字」，问题从根上消失。**记录一个必然变化的数字，不如不记。**

## 超出范围的：无

没有归档 `specs/`（15 个运行、332K，都 done，删了丢决策追溯）。没有精简阶段正文。

## 遗留

1. `bugfix` / `hotfix` / `review-only` 的 stage1 `requires` 为空。这是既有设计（第一步是「根因定位」「止血决策」，性质不同），不是缺陷。
2. `specs/` 会随使用持续增长。等有几十个运行时再考虑归档策略。
