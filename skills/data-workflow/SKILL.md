---
name: data-workflow
description: 当用户说「开始开发」「加字段」「改个功能」「排查一下」「这个词什么意思」「审一下这批改动」「提交」「提 MR」，或要继续一条没做完的运行时使用。纯 git 操作、合并冲突、只读代码不改东西时不调用。
---

# 开发工作台（data-workflow）

**先跑 `next`。它打印一件事，做那一件，做完再跑一次。**

## 怎么选工作流

没开运行时，按用户这句话选。已有运行直接 `next`。

| 场景 | 工作流 |
|---|---|
| data-service（Go 栈）新能力 / 加字段 / 加端点 | `workflows/feature.json` |
| data-service 已知错误要修 | `workflows/bugfix.json` |
| data-service 线上正在出事 | `workflows/hotfix.json` |
| 只审不改 | `workflows/review-only.json` |
| 任意仓库的一次改动，或给任意仓库定架构 | `workflows/change.json` |

选型前读 `references/scope.md`，按 L1/L2/L3 定级。L1 走 `change`；碰到契约、持久化、权限、状态或回滚，即使用户把它叫成小改动，也走 `feature` 或 `hotfix`。只梳理、不改代码时不 `start`，直接读 `stages/oncall/references/routing.md`。

## next 的输出对应什么

| 看到 | 做 |
|---|---|
| `NEED` | 读 `READ` 指明的阶段文件，把缺的工件写上 |
| `GATE` | 工件里缺少 `requires` 里的字面量——补上再 `done` |
| `OPEN` | 文件里还有「待拍板」——`wait`，写一句对方能原样粘贴的回复，停 |
| `WAIT` | 把 `REPLY` 交给对方，原样回了再 `answer` |
| `DO` | 按 `READ` 指明的阶段文件改代码，再 `done`——自动跑仓库声明的测试 |
| `CONFESS` | `done` 推进之后追加的一次独立追问。写 `specs/<feature>/confess/<stage-id>.md`，只写事实。**它不进门、不影响推进**——写不写都不改变这次运行的结果 |
| `DONE` | 这次运行结束。会话收尾前，如果执行中踩了意料之外的坑、发现了新的数据流问题、或对本技能有改进建议，把它追加到 `docs/dev/learnings.md`（标日期、工作流、feature，以及"谁消费/怎么消费/AI能不能到"的证据）。没有就跳过，不硬写 |
| `LAST` / `NO_RUN` | 没未完成运行了，直接回答当前问题 |

开一次运行：`start <workflow> <feature> "<用户原话>"`。停在 `working` 的运行下次仍会被会话钩子注入 NOTICE，直到 `abandon`。

## 绑定

强制写入门禁只在 Cursor + `--project --with-hooks` 生效：改 `protected_paths` 覆盖的文件前，需要 `specs/passes.log` 里有 approve 签发的放行记录（手写行在 `gate_strict` 下不作数）。没配 `protected_paths` 时默认没有受保护路径。其他环境（Qoder/Claude/Codex）没有硬拦截，AI 自觉跑流程。

## 只读、不改代码的入口

不 `start`，直接读：

| 入口 | 文件 |
|---|---|
| 业务梳理 | `stages/oncall/references/routing.md` |
| 排查 | `stages/oncall/SKILL.md` |
| 提交 | `stages/git-commit/SKILL.md` |
| 画图 | `stages/excalidraw-diagram/SKILL.md` |

需要调全局技能时读 `references/global-skills.md`。写 spec / impact / plan / rollback / review / change-note 之前读 `references/doc-shape.md`。

## 四条硬规则

1. 答案与产出里引用读过的文件，不复述知识层。
2. 一次只加载一个业务域文件（`$KNOW` 同理）。
3. stage 文件按路径读，不用技能名调用；全局技能仍按名字调用。
4. **改 workflow JSON 或 runner 前必须跑一遍看真实数据流**：谁消费、怎么消费、AI 能不能到。不能用"runner 不读所以没用"跳过——runner 和 AI 是两个独立消费方。runner 打印的 `READ` 指向 stage SKILL.md，AI 跟着 READ 走，永远不会主动读 JSON 里的 self_check / reads / note / on_gate_fail 等字段。
