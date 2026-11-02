# evidence-first 核对

## 命令与结果

```
$ python3 skills/data-workflow/scripts/check_runner.py
PASS scope.md keeps the evidence-first section
PASS scope.md names the boundary marker '本机文件'
PASS scope.md names the boundary marker '业务口径'
PASS scope.md names the boundary marker '卡在哪'
PASS scope.md names the boundary marker '谁去补'
PASS scope.md carries a failing example
PASS AGENTS.md points at the evidence-first rule
OK
```

exit 0。断言 112 → 119，case 35 → 36。

`specs/evidence-first/verify.log` 第一行是 `exit 0`。

## 验收条件逐条核对

| 决定里的条件 | 是否达到 | 证据 |
|---|---|---|
| 硬规则：能自己查的先查完 | 是 | `scope.md`「查证义务」首句加粗 |
| 可判定边界 | 是 | 四行表格：本机文件/公开文档 → 你查；业务口径/别人机器 → 问人 |
| 查不到时输出形状 | 是 | 三行模板「卡在哪 / 缺什么 / 谁去补」 |
| 反例 | 是 | 「不通过的样子」用了本次真实发生的 4 轮往返 |
| AGENTS.md 指路 | 是 | 断言 `先查完再给方案` |

## 这条规则实际能不能拦住本次那种情况

拿本次对话代入新规则：

```
用户问：这套东西在 DSH 上能不能用？

按新规则第 1 轮就该做：
  事实在哪？→ 本机已装软件 + 应用包
  → ls /Applications | grep -i deepseek
  → strings app.asar | grep "ctx\."
  → 拿到 ctx.tools.guard()
  → 结论：能，且比原方案强

不需要问用户任何问题。
```

本次实际花了几轮？第 1 轮给方案（B 标「我这里没找到」），第 3 轮看目录仍没查包，第 5 轮才查。**4 轮往返全部来自少跑三条命令。**

## 为什么这条不做成机器门

「该不该查」无法机器判定。`unmet_requires` 能查字面量，查不出「这个结论是不是该查却没查」。所以这条靠 agent 遵守，靠断言钉住文档本身不被删。

诚实说明：**这是一条行为约束，不是强制执行。** 它降低概率，不保证。

## 反向验证

删掉「查证义务」整节：

```
FAIL scope.md names the boundary marker '本机文件'
```

恢复后 OK。

## 超出范围的：无

没有新加工作流阶段，没有改 `workflow_next` 行为，没有做自动查证工具。

## 遗留

同一条精神在别处也有缺口，本轮只补了 `scope.md` 这一处：

1. `SKILL.md` 的选工作流部分没提查证义务——但它在 `references/scope.md` 指过去了
2. `bugfix` / `hotfix` 第一步是否也要查证前置，未评估（这两个本来就是「去查证据」的流程，大概率已覆盖）
