# enforce-and-profile 决定

> 规则在 `references/scope.md`。级别 L1：改技能自己的脚本、工作流声明、profile 与文档。不碰业务契约。

- 级别：L1
- 原话（一字不改）：执行 本地提交操作 ，然后 把当前的 c + d  进行优化一下  总结一下上下文信息 ，在进行一次分析一下 查看当前的 流程需要的 架构和 流程
- 本质：把上一轮列的两条债还掉——门禁的放行记录不再由写代码的那只手自己开（D1），门除了查字面量还能查命令（D2）；另外把 data-service 的实例取值从通用阶段文件里挪走，并把常驻的 description 从 1328 字压下来（C）。
- 怎样算满足：`approve` 需要一次已答复的拍板才写放行行，`gate_strict` 下手写的行不作数；`stage.gate_check` 能跑命令并在非 0 时停；`change` 的编码阶段真的检查「有没有改动」；`profiles/go-kratos/profile.md` 存在且四个 Go 实例文件顶部有指向它的守卫；`SKILL.md` 的 description ≤ 300 字；`bash scripts/verify.sh` exit 0。
- 未知：无
- 这次不做：不把 `stages/requirement-analysis` 的九项负债整篇搬进 profile（会改链接与语义，属独立工作，见「为什么更小的做法不够」）；不动 `$KNOW`；不引入新的 hook 事件。

## 真正要解决的问题

三处结构问题，前两处是上一轮 `check.md` §5 自己列出来的：

1. **放行记录是自授权的**（D1）。`specs/passes.log` 由写代码的模型自己追加 `design`/`waiver` 行，`gate-edit` 只认这一行字。所以那道"门"实际是"写一行字"，不是"有人同意"。审计模式下这可以接受，但既然要往 enforce 走，第一步必须是：**放行行的写权限从"能改代码的手"移到"已经问过人、且人回过话"的流程里**。
2. **门只识字面量**（D2）。`requires` 能查"产物里有没有『未知』"，查不了"这一步的实际事实成不成立"。最少要有一种"跑一条命令、看退出码"的门，否则 `gate` 字段永远只是中文。
3. **实例取值躺在通用技能里**（C）。`requirement-analysis`、`impact-assessment`、`change-review`、`plan-template` 把 `internal/{service,biz,data}`、`api/**`、`make api-one` 当成默认事实。非 Go 仓库照抄就等于写错。另外 description 1328 字，是这套东西**最贵**的一格常驻上下文（每轮对话都在），而它里面装的全是规则——正是 `docs/agent-pain.md` 引用的那条反模式。

## 现状（带证据）

| # | 事实 | 证据 |
|---|---|---|
| 1 | `passes.log` 由模型手写，`gate-edit` 只读 | `stages/tech-design/SKILL.md:44`、`workflows/change.md` 第 1 步；`gate-edit` 的 `read_passes()` |
| 2 | `answer` 会清掉 `reply`，没有留下"谁在什么时候同意了什么" | `workflow_next.py` 的 `cmd_answer`（把 reply 置空） |
| 3 | stage 的 `gate` 是中文，runner 不消费 | `workflow_next.py` 只读 `artifacts` / `code` / `requires` |
| 4 | 编码阶段可能一个文件都没改就往下走 | 现在唯一的检查是 `run_verify()`，测试通过不代表改了什么 |
| 5 | Go 实例取值直接写在通用阶段文件正文里 | `requirement-analysis/SKILL.md:23-28`、`plan-template.md:29-31`、`change-review/SKILL.md:63-64`、`impact-assessment/references/blast-radius.md` |
| 6 | description 1328 字 | `SKILL.md` frontmatter |

## 现有能力（复用）

- `read_passes()` 已经能解析 `design`/`waiver` 两种行，加一个"是否带 approved 标记"即可，不必改格式。
- `run_verify()` 的 subprocess 写法可直接复用给 `gate_check`（含超时与输出截断）。
- `layout`/`config_value` 已有 `gate_strict` 读取（在 `gate_edit.py`），D1 的严格分支只需读同一个键。

## 最小充分方案

1. **D1**：`answer` 保留 `last_reply`；新增 `approve <feature> <design|waiver> <前缀> [原因]`，必须有 `last_reply` 才追加，行尾带 `approved` 标记；`gate_edit` 在 `gate_strict` 下忽略没有该标记的行。
2. **D2**：`stage.gate_check`（一条 shell 命令，`<feature>` 会被替换）；runner 在 `requires` 之后、`verify` 之前跑它；非 0 打印 `GATE` 并停。`change` 的编码阶段写 `test -n "$(git status --porcelain)"`。
3. **C**：新增 `profiles/go-kratos/profile.md`（Go 实例拥有什么、非 Go 用什么替代）；四个 Go 实例文件顶部加一行守卫；`SKILL.md` description 压到 ≤300 字。

## 为什么更小的做法不够

- 只加 `approve` 不改 `gate_edit`：手写行照样放行，等于没改。
- 只加 `gate_check` 不接线：又是一段没人用的机制（这类债这两轮已经清了两条）。
- 只把 description 压短不改阶段守卫：常驻上下文省下来的钱，会在读到 `internal/biz/status.go` 时连本带利还回去。
- 把九项负债整篇搬进 profile 属于**搬迁**，会改 `specs/*/check.md` 里已有的链接与语义；这一轮先立"边界声明 + 守卫"，搬迁留到有真实 Go 仓库可回归时做。

## 相关的债

- A 现在偿还：D1、D2、C 三处（都在上一轮 `check.md` §5 里点名过）。
- C 暂缓：九项负债正文搬迁、`stack` 硬阻塞。
- 无关不动：`shell_destinations()` 的正则盲区、`contract_diff.sh` 的 `python3`、`check_runner.module()`。

## 这次不做

- 不新增工作流/阶段；不改 `design`/`waiver` 的**语义**（覆盖规则、plan pass 条件不变）。
- 不把 `gate_strict` 默认打开（默认仍是 audit）。
- 不动 `evals.json`。

## 风险

不碰契约、持久化、权限、状态、回滚。行为变化三处，都写进 `check.md`：**手写的放行行在 `gate_strict` 下不再作数**（迁移要跑一次 `approve`）；**编码阶段必须真的有 diff**（纯 gitignore 文件的改动会被误判，写进已知限制）；**description 变短**，触发词必须一个不少，否则技能不被唤起。
