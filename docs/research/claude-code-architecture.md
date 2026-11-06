# 调研：Claude Code 的架构，和同类差在哪

> 调研时间 2026-11。来源全部是 Anthropic 官方文档（`code.claude.com/docs/en/*.md` 的 markdown 原文档，不是渲染页），一条外部转述都没用。
> 本文的结论只讲**结构**。凡是写具体数字（token 上限、层数、字符数）的，都能在引用的页面里搜到原句。

## 结论先说

**它不是"更强的提示词"，也不是"更多技能"。它的架构里有一条别人没有的、可执行的东西：把 agent 的每一步切成命名的生命周期事件，让你在事件上挂代码，代码的退出码能直接否决 agent 的动作。**

别人（Superpowers / Matt / Addy / Spec Kit / BMAD）交付的是**文档**，靠模型读了照做。Claude Code 交付的是**钩子点**，靠进程退出码生效。这是量级差别，不是风格差别。

第二个不那么显眼、但影响最大的差异：**它把上下文按"何时加载"分了四层，并且每一层在压缩后的命运是写死的。** 大多同类把技能全量塞进上下文，Claude Code 只让 description 常驻，正文用到才进，压缩后按 5000/25000 token 预算重新挂回。

三条差异按"别人有没有同类机制"排序：

| # | 差异 | 别人的做法 | 为什么难抄 |
|---|---|---|---|
| ① | **hooks 是 41 个可挂载的生命周期事件，退出码 2 = 否决** | 无对应层 | 需要先有运行时；技能包没有运行时，只有 markdown |
| ② | **上下文四层分级 + 压缩后重挂预算** | 全量常驻或按提示词自觉 | 需要能改 harness 本身 |
| ③ | **subagent 是一个"上下文隔离 + 权限隔离 + 工具隔离"的一等公民** | 子代理靠约定；并行靠 worktree 隔离 | 需要运行时支持独立 window 与独立 permission |

后面每条都给原话和页面，并在 §5 逐条对照本仓 `docs/competitive.md` 的矩阵，说明哪些格子该改。

---

## 1 架构骨架：harness 包着 model

**已证实**（`how-claude-code-works.md`）：

> Claude Code is the layer around the model that provides the tools and manages the context the model sees. This surrounding layer is what the term **agentic harness** refers to.

循环本身是三段，且官方明说三段是**混杂的、不是线性步骤**：

> it works through three phases: **gather context**, **take action**, and **verify results**. These phases blend together.

**这是第一个容易看错的地方**：很多人把 `gather → act → verify` 当作一个流水线去建模（本仓 `workflows/feature.json` 就近似这个形状）。官方口径是"blend together"，即模型每一 turn 自己决定进哪段，没有阶段机。**不要把它读成状态机。**

内置工具五类：文件操作、搜索、执行、Web、代码智能。官方强调工具是 agentic 的来源：

> Without tools, Claude can only respond with text. With tools, Claude can act.

运行时环境三选一（Local / Cloud / Remote Control），但 **loop 完全相同**：

> The interface determines how you see and interact with Claude, but the underlying agentic loop is identical.

**这解释了一件事**：为什么 CLI、IDE、桌面、网页、Slack、CI 的行为能一致。不是"各自实现了一遍"，是同一 loop 换了外壳。技能包做不到这点——它们寄生在某一个宿主里。

---

## 2 差异①：hooks 是被低估的那一层

### 2.1 规模

**已证实**（`hooks.md`）：41 个事件，分三种节奏：

- 每 session：`SessionStart`、`SessionEnd`
- 每 turn：`UserPromptSubmit`、`Stop`、`StopFailure`
- **每一次工具调用**：`PreToolUse`、`PostToolUse`

还有几个在别的架构里根本不存在的事件：

| 事件 | 官方描述的点 | 为什么值得注意 |
|---|---|---|
| `PreToolUse` | 工具调用前，**Can block it** | 唯一能在动作发生前否决的点 |
| `PostToolBatch` | 一批并行工具调用全部结束后、下一次模型调用前 | 并行工具是 Claude Code 的常态，这是唯一能"批量收口"的位置 |
| `PreCompact` / `PostCompact` | 上下文压缩前后 | **压缩是可干预的**，不只是自动发生的 |
| `PreModelSwitch` | 模型切换前，**Can block the switch** | 换模型能被拦。这直接影响 prompt cache |
| `Elicitation` / `ElicitationResult` | MCP server 在工具调用中要求用户输入时 | MCP 的人机交互被做成了可挂点 |
| `WorktreeCreate` / `WorktreeRemove` | 创建 worktree 时，**Replaces default git behavior** | 连 git 行为都能替换 |
| `InstructionsLoaded` | CLAUDE.md 或 `.claude/rules/*.md` 被加载时 | 能观测到"规则什么时候真的进了上下文" |
| `TaskCreated` / `TaskCompleted` | 任务被创建 / 被标记完成时 | **"完成"这个动作本身有钩子** |
| `TeammateIdle` | agent team 成员即将空闲时 | 多 agent 调度的接缝 |

### 2.2 退出码语义

**已证实**（`hooks.md` → Exit code output）：

- **exit 0**：成功，应用打印的 JSON 字段，动作继续
- **exit 2**：**阻断**。在可阻断事件上，Claude Code 停下这个动作
- **其他任何退出码 / 跑不起来 / 输出非法 JSON**：非阻断错误，**动作照常进行**

最后一条是关键：**默认是 fail-open 的**。而且官方明确"exit 2 时即使打印了 JSON，也照样阻断；连 `permissionDecision: "allow"` 都放不过去"。

但 fail-open 不是无条件的。`onFailure: "block"` 可以把"hook 自己崩了"改成阻断：

> The action goes ahead, except for hooks whose failure blocks the action, for example a hook with `onFailure` set to `"block"`.

**这条直接对上本仓的一个已证实断言**：`docs/claim-register.md` V1 写「`gate_strict` 默认关闭，异常一律 fail-open」，`docs/competitive.md` 把"hook 坏了自己的降级策略"列为差异点 ②。对照官方：**这是同一套设计的两个实现**——默认 fail-open、显式开关才转严格。所以那格不是"别人没有"，是"Claude Code 官方有，技能包里没有"。**矩阵需要改。**

### 2.3 两种容易漏的 hook 形态

**已证实**：

- **prompt-based hooks** 与 **agent-based hooks**：hook 不一定是 shell，也可以是"让模型判断"
- **async hooks**：不阻塞主循环，事后通过 `additionalContext` 报告

第二条很关键。它给了唯一一种"既要检查又不拖慢"的形态：

> Only run tests for source files … Send a notification via additionalContext

**推断**：这正好是本仓 `verify` 那类耗时检查的合适位置。当前本仓把 verify 放在 `done` 这一步阻塞执行，官方提供的替代形状是"异步跑、结果回注上下文"。代价是本仓 `verify.log` 的 `exit N` 首行证据链会变成异步的，跨会话可核对性下降。**这是个 trade-off，不是免费升级**，不进这次改动建议，只记在这里。

---

## 3 差异②：上下文按"何时加载"分四层

### 3.1 四层

**已证实**（`features-overview.md`、`context-window.md`、`skills.md`）：

| 层 | 载入时机 | 压缩后 |
|---|---|---|
| CLAUDE.md / 项目根 rules | 每次 session 自动 | 从磁盘**重新注入** |
| Agent / skill 的 `description` | 每次 session 自动（只加载描述） | 按当前技能集**重建并重新注入**（v2.1.304+） |
| Skill 正文 | 被调用时 | 重挂，**每技能 5000 tokens 上限，总计 25000**，超了从最老的开始丢 |
| 文件内容 / 工具输出 | 读到才进 | 重新读最多 5 个，最近修改优先 |

技能正文那句原话：

> a skill's body loads only when it's used, so long reference material costs almost nothing until you need it.

**这是"渐进披露"（progressive disclosure）的具体实现。** 对比本仓：`SKILL.md` 只选择阶段，阶段文件点名才读——形状一样。但 Claude Code 多了一条本仓没有的：**压缩后的重挂策略是写死的预算，不是靠模型自觉**。

「老技能会被整条丢掉」原文：

> Claude Code fills this budget starting from the most recently invoked skill, so older skills can be dropped entirely after compaction if you have invoked many in one session.

**这解释了一个常见现象**：会话长了以后模型"不遵守技能了"。不是模型忘性大，是技能正文被预算挤掉了。官方给的解法是**把最重要的指令放 `SKILL.md` 最前面**（截断保留开头）：

> Truncation keeps the start of the file, so put the most important instructions near the top of `SKILL.md`.

**这条是可执行的检查项**：本仓 45 个 md 里，`SKILL.md` 开头的写法是否满足"最重要的在最前"？这是一个可以真去核的格子。

### 3.2 description 有硬上限

**已证实**（`skills.md`）：

> the combined `description` and `when_to_use` text is truncated at **1,536 characters** in the skill listing

**这直接对应本仓的一条已知风险**。`docs/external-skill-packs.md` 末尾写：

> 三套不要同时常驻。description 会一起进上下文，路由会抢同一句话。

现在有了量化口径：**每个常驻技能都在吃这 1536 字符的预算**。多套装一起常驻，不是"占点上下文"这种模糊说法，是**在同一个硬上限里互相挤**。本仓那句话可以升级成有数字的断言。

### 3.3 技能正文进上下文后不重读

**已证实**（`skills.md` → Skill content lifecycle）：

> When you or Claude invoke a skill, the rendered `SKILL.md` content enters the conversation as a single message and **stays there across later turns**. … Claude Code **does not re-read the skill file on later turns**

**这条推翻了本仓 `docs/claim-register.md` 的一条待确认断言。** 那条写：

> 「同时只有 1 个 stage 在上下文」→ 读入不自动消失，要么靠有损摘要，要么根本不成立。且曾用它驳回 Skill++，属循环论证

官方口径确认了前半句"读入不自动消失"，并且给出了机制（作为一条 message 常驻）。**所以那条断言可以从不成立的质疑，升级为"已证实：常驻是对的，但有压缩预算"**。同时后半句"曾用它驳回 Skill++ 属循环论证"依然成立——常驻不等于全量常驻，Claude Code 自己就用 description-only 规避了这个问题。这两件事不矛盾。

**这是本次调研里唯一一处能直接把本仓的待确认项转成已证实的地方**，且不涉及改代码，只改 `claim-register.md` 一行和 `competitive.md` 一格。

---

## 4 差异③：subagent 是三重隔离的一等公民

### 4.1 隔离的是三样东西

**已证实**（`sub-agents.md`）：

> Each subagent runs in its own context window with a custom system prompt, specific tool access, and independent permissions.

即：**上下文窗口独立、系统提示独立、工具集独立、权限独立**。而且：

> Each subagent starts with a fresh, isolated context window. It doesn't see your conversation history, the skills you've already invoked, or the files Claude has already read.

### 4.2 三种形态，别混

**已证实**：

| 形态 | 继承什么 | 用在 |
|---|---|---|
| 普通 subagent | 什么也不继承，只拿到一段委派说明 | 高频输出隔离（跑测试、读日志） |
| **fork** | 继承整个对话（system prompt、tools、model、消息历史全同） | 需要大量背景才有用的侧任务 |
| `isolation: worktree` | 独立的仓库副本 | 并行改代码不撞车 |

**fork 对输入的隔离被明确取消了**：

> This drops the input isolation that subagents otherwise provide

**这解释了本仓的一条纪律。** `docs/competitive.md` 写本仓"实现类禁止并行，因为同一批文件、共享工作区会互相覆盖"。对照官方：**并行实现是可行的，前提是 `isolation: worktree` 或直接跑独立 session**。Claude Code 自己没把"禁止并行"当铁律，它把并行做成可选项，用隔离换来的。

**这是本仓一个真实的能力缺口**，不是风格差异。但补它需要运行时支持 worktree 隔离；本仓是纯 markdown + 脚本，只能靠约定"别并行"。**所以这不是一次改动能补的，属于架构层的缺口，应记进 `competitive.md` 而不是排进 backlog。**

### 4.3 层数和成本

- **最多向下三层**（supervisor → sub → sub-sub），到限后除了 fork 都不再给 `Agent` 工具
- subagent 的请求**算进同一个用量额度**（`costs.md`）
- subagent 有**自己的自动压缩**，窗口大小由它自己的模型决定（可能比父的小）
- `skills:` 字段可以**预载全文**到 subagent，上限**前 32 个不同名字**

最后一条值得单独说：**"预载全文"和主对话的"只加载 description"是两套策略。** 主对话省钱，subagent 里预先灌满。**推断**：这是官方对"隔离窗口里 1536 字符预算问题不存在"的利用——反正只活一次。

---

## 5 差异④（衍生）：把计划搬进代码

`workflows.md` 给了一张四方案对照，**这张表的分类轴本身值得抄**：

| | Subagents | Skills | Agent teams | **Workflows** |
|---|---|---|---|---|
| 谁决定下一个做什么 | Claude，逐 turn | Claude，按提示词 | lead agent，逐 turn | **脚本** |
| 中间结果放哪 | 上下文窗口 | 上下文窗口 | 共享任务列表 | **脚本变量** |
| 什么可复用 | worker 定义 | 指令 | team 定义 | **编排本身** |
| 规模 | 每 turn 几个委派 | 同 subagents | 几个长跑 peer | **每次几十到几百个 agent** |
| 中断 | 重启这一 turn | 重启这一 turn | peer 继续跑 | **同一 session 内可恢复** |

原话：

> A workflow moves the plan into code. … A workflow script holds the loop, the branching, and the intermediate results itself, so **Claude's context holds only the final answer**.

还有一条官方点名的用途，和本仓"质量门"目标一致：

> it can have independent agents **adversarially review each other's findings** before they're reported

**这是四个方案里唯一一个"编排可复用、可重跑、可审阅"的**。本仓 `workflows/feature.json` 是同一思路的极简版：把阶段顺序写进 JSON，由 `workflow_next.py` 算下一步，**零 LLM 调用**（`claim-register.md` V5 已证实）。区别是：本仓的脚本只算"下一步是哪一步"，Claude Code 的脚本能直接**驱动几十个 agent**。

**这个方向的判断**：本仓不要追。理由是规模不匹配——1 个技能追几十个并发 agent 没有意义。但**"编排可复用"这一点本仓已经做到了**，可以写进 `competitive.md` 作为已证实格子。

---

## 6 逐条对照本仓矩阵：哪几格写错了

只列**结论会变**的格子。`docs/competitive.md` 的原文在左，右列是官方口径。

| 矩阵格 | 本仓现写 | 官方事实 | 该怎么改 |
|---|---|---|---|
| hook 降级策略 | ● 本仓有，**同类里没找到对应设计（推断）** | `onFailure: "block"` + 默认 fail-open，官方明文写了 | **性质变了**：不是"别人没想过"，是"官方有标准实现"。本仓那格保留 ●，但"差异点"的表述要降级 |
| 写入拦截 | ● 本仓有 Cursor hook | `PreToolUse` 可 block，41 事件 | 保留，但说明是**在别人的 hook 上做**，不是自建 |
| 未完成任务跨会话续跑 | ● `run.json` + NOTICE，同类都没有 | session 存 `~/.claude/projects/*.jsonl`，可 resume / fork / `/branch`；但**不记"停在第几步"** | **本仓这格是真的**。官方有 session 恢复，但没有阶段语义。差异点①仍成立 |
| 多 agent 编排纪律 | ● 本仓禁止并行实现 | 官方：并行可行，靠 worktree / 独立 session 隔离 | **这格要改**：不是"我们更严谨"，是"我们没隔离手段所以只能禁"。属缺口 |
| 上下文分级 | 矩阵里没这行 | 四层 + 5000/25000 预算 + 1536 字符 | **建议新增一行**，本仓 ◐（有分级，无预算机制） |
| "同时只有 1 个 stage 在上下文" | `claim-register.md` 待确认，且质疑其不成立 | 官方：技能正文常驻不重读 | **升为已证实**，见 §3.3 |

---

## 7 不能从这份调研得到的东西

写清楚，免得被当成结论引用：

1. **没有性能数据。** 官方文档不讲"开了 hooks 会慢多少"。§5 里 async hook 适合跑 verify 的判断是**推断**，需要实测。
2. **没有对比实验。** "上下文分层比全量常驻更好"是官方的设计意图，不是官方给的数据。本仓 `claim-register.md` C5（"一次只读一个文件优于一次性加载"）**不受这份文档证实**，仍然待确认。
3. **版本相关。** 文中数字绑定了页面上的版本标注（如 `v2.1.304`、`v2.1.198`、`v2.1.247`）。上游在动，引用前重新抓一遍。
4. **Agent SDK 只看了定位。** `headless.md` 确认 SDK 给的是 "the same tools, agent loop, and context management that power Claude Code"，但 SDK 的 API 细节没读。要动 SDK 需另开一轮。
5. **和本仓 `docs/agent-pain.md` 第一条有张力。** 那条引的是"长说明进上下文会降低成功率 3%"。本调研 §3 说"分层加载降低了常驻成本"——**两者不冲突但也不互相支持**：前者讲"塞了什么"，后者讲"何时塞"。不要拿这份文档去论证前者。

---

## 8 如果只做一件事

**改 `docs/competitive.md` 里那两格：hook 降级策略、多 agent 编排。**

理由：这两格现在都在往**对自己有利**的方向写，而官方文档直接反驳了其中一部分。`competitive.md` 开头自己写了"过期后就按 `docs/agent-pain.md` 的说法——过期后要漏得响"。这次就是漏了。

其余（上下文分级、claim-register 升格）是增补，不动结论，可以一起做也可以不做。

---

## 附：本文引用的官方页面

全部以 `.md` 原始文档抓取，非渲染页：

- `how-claude-code-works.md` — agentic loop、harness、内置工具、session、压缩
- `features-overview.md` — 扩展层全景与选型
- `skills.md` — 技能正文生命周期、frontmatter、1536 字符上限、5000/25000 预算、32 个预载上限
- `sub-agents.md` — 三重隔离、fork、深度三层、`isolation: worktree`
- `hooks.md` — 41 个事件、退出码语义、`onFailure`、prompt/agent/async hook
- `workflows.md` — 四方案对照、编排进代码
- `context-window.md` — 压缩后各类内容的命运
- `claude-directory.md`、`memory.md`、`prompt-caching.md`、`agent-teams.md`、`worktrees.md`、`agents.md`、`headless.md`
