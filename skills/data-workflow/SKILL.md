---
name: data-workflow
description: 装进任意仓库后，未完成的运行在该仓库 specs/<feature>/run.json。有未完成步骤时先跑 scripts/workflow_next.py next，只做它打印的那一件。编码步骤的 done 跑该仓库自己的测试入口，退出码不是 0 就停。没有 data-service 门禁时用 start change <feature>。做架构也走 change：形状写在 decision.md，不套九步。梳理一个词、字段或状态的含义时，先查排查卡片再读一个域文件，取值回代码，不编口径。用户这次真正要的范围小于方案时，停在能复用的现有符号或最小改动上。技术债读负债门，不另开结构。data-service 上还绑定写入门禁和原有阶段链。用户说 @data-workflow、开始开发、架构设计、梳理业务、这个词什么意思、需求分析、影响面、技术方案、编码实现、改动审核、审一下、质量检查、接口测试、排查、状态含义、提交、提 MR、画架构图时读取本文件，再只读点名的那一个阶段文件。不用于：纯 git 操作、解决合并冲突。
---

# data-service 开发工作台

本文件只做选型。具体步骤在点名的那一个 `stages/` 文件里。业务事实运行时从知识层读。安装后工具目录里只有这一个 `data-workflow`。装进别的仓库后，那个仓库里的代理读这份副本。

`$PLUGIN_ROOT` 是本文件所在目录。命令表在 `references/commands.md`。Agent 输入框输入 `/`，选 `dw-next`、`dw-done`、`dw-wait`、`dw-start`。

会话开头解析一次路径。空值就问，或显式声明降级后继续。不猜绝对路径。

```bash
eval "$(bash "$PLUGIN_ROOT/scripts/paths.sh")"
```

## 绑定

Cursor 项目安装后，没有 `specs/passes.log` 里覆盖该路径的记录，hook 拒绝写入。路径表只维护在 `references/edit-gate.md`。`protected_paths` 和 `waiver_globs` 都没写时，默认仍是 `api/`、proto、pb.go、`internal/biz/status.go` 和其它 `*.go`。有未完成运行时，会话钩子只注入 `next` 的那一段。这次注入依赖 Cursor 加载了 `.cursor/hooks.json` 里的 `sessionStart`。新会话没有看到下一步时，先确认这份钩子文件被加载。

## 继续一次运行

未完成的运行在当前 git 根的 `specs/<feature>/run.json`。没有注入，或输出是 `LAST` / `NO_RUN` 时，回答当前的问题。

| 看到 | 做 |
|---|---|
| `READ` / `NEED` | 只读打印出来的那一个阶段文件，把缺的文件写上 |
| `OPEN` | `wait <feature> "<问题>" "<对方能原样粘贴的一句>"`，然后停止 |
| `WAIT` | 把 `REPLY` 交给对方。对方原样回了再 `answer`。对不上就停 |
| `DO` | 做完再 `done <feature>`。这一步跑该仓库自己的测试入口，退出码不是 0 就停 |
| `DONE` | 这次运行结束。证实或推翻了一条口径时，按 capture.md 写一张卡 |
| `LAST` | 这次没有未完成步骤。回答当前的问题 |

`start feature|bugfix|hotfix|review-only|change <feature>` 新开一次。没有 data-service 的九项负债时用 `change`。改动落在 `api/`、proto、pb.go、`internal/biz/status.go`，或涉及状态机、租户权限、回滚时，不用 `change`，用 `feature` 或 `hotfix`。

这轮不做了就 `abandon <feature>`。状态变成 `abandoned` 之后，钩子不再注入。不按天数、也不按 HEAD 变化自动放弃。停在 `working` 的运行下次仍会注入，直到 `abandon`。编码步骤的退出码是完成信号的下界。状态和 proto 的语义是否正确，看 `plan pass`、契约 diff 和审核。

## 选工作流

用户这句话已经点明选型表某一行：直接读该行的阶段文件。用户只说开始干活：用 AskUserQuestion 弹菜单，一次一题，可多选，按表的顺序串行。

进入选型表里 data-service 的一行之前，先读 `references/workflows.md`，再读那一个阶段文件。

| 场景 | 工作流 |
|---|---|
| 新能力 / 扩展 / 新字段 / 新端点 | `workflows/feature.json` |
| 已知错误行为要修 | `workflows/bugfix.json` |
| 线上正在出事 | `workflows/hotfix.json` |
| 只审不改 | `workflows/review-only.json` |
| 没有 data-service 门禁的一次改动，或给任意仓库定架构 | `workflows/change.json` |

新业务场景是新的工作流模板，不是再装一个技能。

只梳理、不改代码时，不 `start`。读 `stages/oncall/references/routing.md`：先 grep `$CARDS/`，再只读一个域文件，取值回代码。`status: superseded` 的卡跳过。没有出处的词写成待确认，然后 `wait`。用户要留下这条时，再读 `stages/oncall/references/capture.md` 写一张卡。不先写一篇领域百科。

先写用户这次真正要的那一句。仓库里已有的 `文件:符号` 能做到，就复用，不加表、不加字段、不加开关、不加中间层。最小改动做得到，走 `change`。碰 `api/`、proto、状态、租户权限、回滚时才走 `feature` 或 `hotfix`，方案里仍要有一个最小改动。问现有业务欠了什么债，读 `stages/requirement-analysis/references/debt-gate.md`：还债或欠债都落到 `文件:符号`；欠债写落点、怎么还、何时还。

## 选型表

一次只读表里点名的一个文件。`$KNOW` 一次只加载一个域文件。

| 选择 | 读 | 产出 |
|---|---|---|
| 需求分析 | `stages/requirement-analysis/SKILL.md` | `specs/<feature>/spec.md` |
| 影响面评估 | `stages/impact-assessment/SKILL.md` | `specs/<feature>/impact.md` |
| 技术方案 | `stages/tech-design/SKILL.md` | `plan.md`、`rollback.md` |
| 编码实现 | `stages/implementation/SKILL.md` | 代码 |
| 改动审核 | `stages/change-review/SKILL.md` | `specs/<feature>/review/*.md` |
| 质量检查 | `stages/quality-gate/SKILL.md` | `specs/<feature>/quality.md` |
| 接口测试 | `stages/interface-test/SKILL.md` | `specs/<feature>/interface-test.md` |
| 业务梳理 | `stages/oncall/references/routing.md` | 待确认，或一张卡 |
| 排查确认 | `stages/oncall/SKILL.md` | 只读结论 |
| 提交 | `stages/git-commit/SKILL.md` | `specs/<feature>/change-note.md` |

点名才读的全局技能：`grilling`、`diagnosing-bugs`、`ponytail-review`、`security-best-practices`、`security-threat-model`、`gh-fix-ci`、`gh-address-comments`、`domain-modeling`。阶段文件按路径读，不用技能名去调用。

写 spec、impact、plan、rollback、review、change-note 之前读 `references/doc-shape.md`。归档见 `references/feature-archive.md`。

## 三条硬规则

1. 答案与产出里引用读过的文件，不复述知识层。
2. 一次只加载一个业务域文件。
3. 阶段是本技能内的文件。全局技能仍按名字调用。
