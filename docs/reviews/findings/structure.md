# 结构轴走查

只看「理解一个概念要不要在好几个小 module 之间跳」和「哪里的 interface 快赶上 implementation 大了」。不把调用顺序上的 bug 当作本轴结论的前提（那些写在 callflow.md）。

每条都做了 deletion test。只有「删掉它，复杂度会在 N 个调用方重新长出来」才留下当候选。

---

## S1 配置读取是四处浅 module，而且已经读出了不同的答案

**概念：** 一个配置键从哪里读、多个文件同时存在时谁优先、缺省返回什么。

**要跳的地方：**

- `layout.py:read_yaml_key` — 文件没有时返回 `""`，并被 `layout.py:configured_store` 用来找 `artifacts_root`（工具目录 + 仓库根 `config.yaml`，**不看** `~/.config/data-workflow/config.yaml`）
- `workflow_next.py:read_yaml_key` — 同名副本，文件没有时返回 `None`；`workflow_next.py:config_value` 的候选是工具目录 + 仓库根 + `~/.config/data-workflow/config.yaml`
- `gate_edit.py:read_yaml_key` — 第三份同名副本，返回 `None`
- `gate_edit.py:policy` — 用自己那份读 `protected_paths` / `waiver_globs`，候选列表与 `config_value` 相同（工具目录优先，然后仓库根，然后 home）
- `gate_edit.py:strict` — 只用自己那份读 `gate_strict`，候选**只有** 仓库根 `config.yaml` 和 `.cursor/skills/data-workflow/config.yaml`，且仓库根优先

`layout.py` 已经有一份 yaml 读取，但 `workflow_next` 与 `gate_edit` 都不调用它（两者只取 `store_root` / `configured_store`）。`gate_edit.py:repo_root` 与 `workflow_next.py:repo_root`、`layout.py:git_root` 又是三份「找 git 根」。

核对（2026-11-12，Asia/Shanghai，对 `gate_edit.strict` / `gate_edit.policy` 实跑）：

- 只把 `gate_strict: "true"` 写在 `.qoder/skills/data-workflow/config.yaml` 时，`policy` 能读到同文件里的 `protected_paths`，`strict()` 仍为 False。
- 仓库根 `config.yaml` 写 `gate_strict: "false"`、`.cursor/.../config.yaml` 写 `gate_strict: "true"` 时，`strict()` 取仓库根（False）；同一对文件上 `policy()` 取工具目录的 `protected_paths`。两个键的文件优先级相反。

这不是「以后可能会漂」，是已经漂了。

**interface 与 implementation：** 每一份 `read_yaml_key` 的 interface（路径、键名、返回空值的约定）几乎等于它那二十来行 implementation，再由调用方各自列出候选路径——四处都是浅的。真正的 depth（「这个键在这个仓库里取值是什么」）没有 module 压住。

**Deletion test：** 删掉其中任何一份，不会让复杂度消失，只会让剩下的调用方继续各写各的候选列表（或更糟：以为删掉就统一了，其实 `strict` 与 `policy` 仍分叉）。把它收成一处之后，路径和优先级的 bug 会集中在一个 module。**是的，会集中。** 候选。

`layout.py:_legacy_store_root`、`gate_edit.py:protected`、`gate_edit.py:needs_waiver` 是已无行为的残留（后两个恒为 False）。它们不是浅 module 的主因，不单独成候选。

---

## S2 产物落点的 interface 是空的：名字在，取值被写死

**概念：** 一次运行的工件写到哪里、机器门去哪里找它们。

要理解这个概念需要跳：

- 各 `workflows/*.json` 的顶层字段 `artifacts_root`（architecture-review 写的是 `$REPO/docs/reviews/`，其余写 `specs/<feature>/`）
- 阶段 `artifacts` 里的占位符 `<artifacts_root>`、`<feature>`、`<topic>`
- `workflow_next.py:artifact_paths`：把 `<artifacts_root>` **写死替换成** `specs/` + feature；不读 workflow 对象上的 `artifacts_root` 字段（全文件除这处字符串替换外，没有消费该字段）
- `layout.py:configured_store` / `layout.py:store_root`：配置键也叫 `artifacts_root`，但含义是「整个 specs 树放在哪」，与 workflow JSON 那个字段不是一回事

实跑 `artifact_paths("<artifacts_root>/<topic>-architecture-review.html", "rev1")` 得到的是 `specs/rev1/<topic>-architecture-review.html`：

- 声明的 `$REPO/docs/reviews/` 被丢掉
- `<topic>` 不会被替换，机器去找一个字面量文件名

本轮 architecture-review 技能要求报告落在仓库的 `docs/reviews/`，runner 的内容门却不会去那里看，也不会认出 `data-workflow-architecture-review.html` 这个文件名。

**interface 与 implementation：** JSON 上的 `artifacts_root` 看起来像一个可配置的 interface，implementation 并不使用它。interface 几乎没有压住任何行为——典型的浅。两个同名 `artifacts_root` 还让人在 `layout` 与 workflow JSON 之间跳。

**Deletion test：** 删掉 `artifact_paths` 里那一行写死替换，调用方（`stage_paths`、`close_if`、NEED 打印）会各自发明路径规则，architecture-review 与 change/feature 的落点会分成两套。把它加深成「按声明的根解析占位符」，落点规则集中在一处。**是的，会集中。** 候选。

---

## S3 工作流定义仍要在几个浅层之间跳，但主泄漏已经修过

**概念：** 这一步 AI 该读什么、用哪份模板、怎样算做完。

仍要跳的地方：`SKILL.md`（选型）、`workflows/*.json`（机器字段 + 提示字段）、`stages/*/SKILL.md` 或 `workflows/change.md`（步骤正文；多个工作流共享同一份阶段文件，例如 `stages/oncall/SKILL.md` 同时被 bugfix 与 hotfix 引用，`stages/change-review/SKILL.md` 被 5 个阶段共用）、`commands/*.md`（斜杠命令，不经过 `SKILL.md`）。

双消费方本身是有意的设计（runner 判机器字段，AI 读提示字段），`print_stage_hints` 已经把 JSON 里的 `self_check` / `reads` / `note` / `on_gate_fail` / `calls` / `subagents` / `close_if` 转发出去——learnings 里那条「AI 永远看不到」已不是现况。

残留的浅：

- `print_stage_hints` 是手工枚举。新加一个给 AI 看的 JSON 字段，必须再改这个函数，否则字段只存在于 JSON，AI 仍然看不见。当前 `template` 出现在 8 个阶段里，这里不转发；change 的阶段正文自己点名了 `templates/decision-template.md`，所以这条还没造成 change 写不出决定，但不构成 depth。
- `commands/` 没有 `close` / `approve` / `abandon` 的入口，这三件事只写在 `SKILL.md` 与 runner 用法里。斜杠命令是第二入口，和「共享阶段文件不要塞专属提示」是同一类结构：副本少于原件就会分叉。

**Deletion test：**

- 删掉 `print_stage_hints`：复杂度不会消失，AI 重新看不到提示——它在挣饭钱，但作为 module 仍然浅。加深方向是「提示字段的转发不再靠一份手写清单」，值得记，但优先级低于 S1/S2。作 **Worth exploring / 残留**，不单独作为最强候选。
- 共享阶段文件本身：删掉共享、每条工作流复制一份 SKILL.md，复杂度会散到 N 份正文里，而且会重新引入「bugfix 与 hotfix 指令互相覆盖」。共享是在挣饭钱，**不是**该拆掉的浅 module。不作为候选。

---

## S4 终态判定声称只在一处，结构上仍有副本

`workflow_next.py:is_finished` 的注释写明：终态有三个，判定只在这一处；以前三处各写一遍，加一个终态就要改三处。

现行源码里，同一份终态集合仍出现在：

- `workflow_next.py:is_finished`（`done` / `closed` / `abandoned`）——`cmd_start`、`cmd_close` 走这里
- `workflow_next.py:cmd_next` 仍手写 `item[2] not in ("done", "closed", "abandoned")`，没用 `is_finished`
- `hooks/session-start` 里对 NOTICE 的 `done|closed|abandoned` 分支
- `gate_edit.py:active_runs` 用的是另一套谓词：只把 `working` / `waiting` 当未完成

`show()` / `cmd_done()` 对单一状态的等值判断（`== "waiting"` 等）是输出分支，不算副本。真正的结构问题是「这条运行结束了没有」没有被一个 module 的 interface 压住。

**Deletion test：** 删掉 `is_finished`，副本本来就在，复杂度不消失。把它加深到 hook 与 `cmd_next` 也走同一处，加第四个终态时只改一个 module。**是的，会集中。** 作次要候选，可并入「运行状态」那一块加深，不必单独开一张主卡片。

---

## 本轴不作为候选的

- `workflow_next.py` 有 59 个顶层函数、约 1368 行，CLI interface（start / next / done / …）相对 implementation 并不算大——按词表这是偏 deep 的，不是「因为文件大所以要拆」。要加深的是它漏出去的配置与落点，不是按行数切文件。
- `check_runner.py` 体量大，但是回归，删掉它复杂度不会在产品调用方长出来。不作为产品结构候选。
- `unmet_requires` 的字面量匹配：interface 确实几乎等于 implementation（浅门），这是已知产品取舍（claim-register V2），结构轴只记录，不把「改成语义门」当作本轮候选——那是能力升级，不是把已有行为收拢。
