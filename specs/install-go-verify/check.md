# install-go-verify 核对

## 命令与结果

```
$ bash scripts/verify.sh
...
PASS RED names where to configure verify
PASS RED lists the auto-detected entry files
PASS go.mod discovered as the verify entry
PASS --project on a repo without tool dirs does not refuse
PASS --project creates the Cursor skill dir when none exists
OK
```

exit 0。断言 119 → 123。

`specs/install-go-verify/verify.log` 第一行是 `exit 0`。

## 验收条件逐条核对

| 决定里的条件 | 是否达到 | 证据 |
|---|---|---|
| 无工具目录时 `--project` 不拒绝 | 是 | `case_install_makes_tool_dir`；实测打印 `CREATE .../.cursor/skills` |
| `go.mod` 自动用 `go test ./...` | 是 | `case_gomod`；实测 `declared_verify('.')` 返回 `'go test ./...'` |
| RED 提示给补救办法 | 是 | 四行：现象 / 去哪配 / 自动探测的四个文件名 / 示例命令 |
| 断言覆盖且会红 | 是 | 见下 |

## 在真实项目上验证（system_tags_editor）

改动前：

```
$ install.sh --project
NOTHING ... 下没有 .claude/.cursor/.qoder/.codex/.agents 任何一个。   ← 装不上
$ done
RED
verify 未配置                                                        ← 不知怎么办
```

改动后：

```
$ install.sh --project
CREATE .../.cursor/skills （目标仓库还没有工具目录，建了一个 Cursor 的）
COPY   .../.cursor/skills/data-workflow
CONFIG ...

$ declared_verify('.')
'go test ./...'                                                      ← 自动认出 Go
```

## 反向验证

| 破坏方式 | 实际结果 |
|---|---|
| 把 `--project` 的自建条件改回 `[ "$global" = 1 ]` | `FAIL --project on a repo without tool dirs does not refuse` |
| 删掉 `go.mod` 探测 | `FAIL go.mod discovered as the verify entry` |

第二条第一次**没抓到**——原断言写成 `"exit 0" in done.stdout.lower()`，太宽松。收紧为「verify.log 里必须出现 `go test`」后才生效。这是我自己写的断言不够严，已修正。

## 断言先红后绿的顺序

`case_gomod` 原断言是「go.mod only stays RED」——它写死了旧行为。改实现前它通过了，改实现后必然红。

处理顺序：**先重写断言，再改实现**。否则红的时候分不清是实现错了还是断言过时了。

## 超出范围的：无

没有改 `--global` 的既有行为。没有修 `system_tags_editor` 的拆行边界差。

## 遗留

1. `declared_verify` 现在支持 6 种入口（package.json / Makefile / pytest / Cargo / go.mod / 显式 verify）。每加一种都该有对应 case——目前 Go 有了，其余 5 种也已覆盖。
2. `system_tags_editor` 的拆行边界差（第 231 行多拆一次）仍未修。那是被测项目的格式问题，改动影响所有用户的保存输出。
