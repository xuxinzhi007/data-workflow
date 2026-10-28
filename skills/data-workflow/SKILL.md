---
name: data-workflow
description: data-service 开发工作台，也带一条任意仓库都能跑的 change 工作流。Cursor 项目安装后会话开始即绑定；有未完成的 specs/*/run.json 时先跑 scripts/workflow_next.py next，只做它打印的下一步。写入受保护路径或 Go 文件时，没有 specs/passes.log 放行记录会被 hook 拒绝。用户说 @data-workflow、开始开发、需求分析、影响面、技术方案、编码实现、改动审核、审一下、质量检查、接口测试、排查、状态含义、提交、提 MR、画架构图时读取本文件，再只读点名的那一个阶段文件。不用于：纯 git 操作、解决合并冲突。与 data-service 无关的改动走 workflows/change.json，不套九项负债。
---

# data-service 开发工作台

本文件只负责**选型、顺序、门禁**。具体步骤在 `stages/` 里被点名的那一个文件；业务事实一律运行时从知识层读，本文件不保存任何取值、状态名、字段名。阶段文件不是独立技能，安装后工具目录里只有这一个 `data-workflow`。

项目索引（去哪读什么）在 `references/project-index.md`，进入具体工作后再读。

`$PLUGIN_ROOT` = 本 SKILL.md 所在目录。这里有 `scripts/`、`workflows/`、`templates/`、`stages/`，以及项目自己的 `config.yaml`。装进别的仓库后这是一份独立副本，不回到技能仓库找文件。反引号里的 `stages/...` 与 `references/...` 都相对这个目录。

外部路径不写死在技能里，会话开头解析一次（步骤 0 之前）：

```bash
eval "$(bash "$PLUGIN_ROOT/scripts/paths.sh")"
# → $KNOW 知识根 / $CARDS 排查卡片目录 / $TEMPLATES 公司模板根
#   $REPO 被测代码仓库 / $TECH_DESIGN_TEMPLATE / $MR_TEMPLATE / $PERSONAL_AGENTS_MD
```

路径可能含空格，命令里必须引号包裹。解析出空值的键**不许猜绝对路径**：要么问用户，要么显式声明降级后继续。

## 绑定

Cursor 项目安装后，会话开始的 hook 注入本文件和 `references/edit-gate.md`。写代码不依赖「开始开发」这几个词。没有 `specs/passes.log` 里覆盖该路径的记录，hook 拒绝写入。哪些路径要 `design`、哪些要 `waiver`，只维护在 `references/edit-gate.md`。项目可以在 `config.yaml` 里用 `protected_paths` 和 `waiver_globs` 换掉默认路径；两个键都没写时，默认仍是 `api/`、proto、pb.go、`internal/biz/status.go` 和其它 `*.go`。

## 继续一次运行

未完成的运行在当前 git 根的 `specs/<feature>/run.json`。换一个会话也在这个文件里，不在上一场聊天里，也不在 `config.yaml` 的 `repo`。全部做完时，`next` 仍打印最近一次，标记是 `LAST`。Cursor 项目安装后，会话开始的 hook 会先把这段原文注入进来。只做那一件。没有注入就自己跑：

```bash
python3 "$PLUGIN_ROOT/scripts/workflow_next.py" next
```

- `READ` / `NEED`：只读打印出来的那一个阶段文件，把缺的文件写出来。
- `OPEN` 或还要问一句才能往下：`wait <feature> "<问题>" "<对方能原样粘贴的一句>"`，然后停止。不要用「根据项目规则进行调整」收尾。
- `WAIT`：把 `REPLY` 那一句交给对方。对方原样回了，再 `answer`。`answer` 会在仍写着「待拍板」的产物末尾追加一行「已拍板：」。
- `DO`：做完这一阶段再 `done <feature>`。
- `DONE`：这次运行结束。

`start feature|bugfix|hotfix|review-only|change <feature>` 新开一次。`config.yaml` 写了 `default_workflow` 时，`next` 在没有运行记录时会打印该用哪条。没有 data-service 的九项负债时用 `change`，不套 feature 的阶段表。

## 启动

### 步骤 0 环境探测（整个会话只做一次）

```bash
"$PLUGIN_ROOT/scripts/repo_snapshot.sh"
"$PLUGIN_ROOT/scripts/knowledge_drift.sh"
```

记下 branch、commit、是否有未提交改动，以及每份知识文档的 FRESH / STALE / SKIP。结果**向下游所有步骤传递，任何步骤技能不再重复探测**。

新鲜度分三层，同时成立：

1. **脚本只标注**。`knowledge_drift.sh` 恒 exit 0（exit 2 仅表示文档无法解析），把每份文档标成 FRESH / STALE / SKIP。缺 frontmatter 算 STALE。
2. **STALE 不停工**。过期文档用来选搜索目标，取值回代码重新推导，产出里写明哪份文档已过期。`FRESH` 可当证据引用。
3. **过门要回代码**。产出里引用了 STALE 文档的取值、却没回代码重新推导 = 知识新鲜度门未过，停。

### 步骤 1 查重（进入任何一步之前）

- 是否已有覆盖此事的工件？`grep -rl "<主题词>" "$REPO/specs/" "$CARDS/"`
- 是否与已钉住的决策冲突？看 `specs/` 里最近那份的决定表，以及该 IDE 的临时目录（`.cursor/plans/`、`.qoder/plans/` 等等价物）。
- 用户这句话是否已点明选型表中的某一行？

命中已有产出就接着它做，不要重开一份。`specs/<feature>/run.json` 的 status 不是 done 时，先跑 `scripts/workflow_next.py next`，只做它打印的那一步。

### 步骤 2 选型

用户这句话已点明下表某一行：直接读该行的阶段文件并执行，跳过菜单。一次只读表里点名的那一个文件。
用户只说开始干活：立刻用 AskUserQuestion 弹菜单，等选择后再往下。一次一题，`multiSelect: true`，题目写「这次做哪几件？可多选，按下面顺序串行。」选项：需求分析 / 影响面评估 / 技术方案 / 编码实现 / 改动审核 / 质量与接口 / 排查确认 / 提交。

### 步骤 3 选工作流

选完要做的事，再选**按哪条流程串**。工作流是确定性状态机（`$PLUGIN_ROOT/workflows/*.json`），阶段顺序、每阶段的 `file`（相对本技能根的阶段文件）、门禁、能不能派子 agent 都写在里面。读那个文件，不把它当成另一个已安装技能：

| 场景 | 工作流 |
|---|---|
| 新能力 / 扩展 / 新字段 / 新端点 | `workflows/feature.json` |
| 已知错误行为要修 | `workflows/bugfix.json` |
| 线上正在出事，最短路径止血 | `workflows/hotfix.json` |
| 只审不改（评 MR、上线前把关） | `workflows/review-only.json` |
| 没有 data-service 门禁的一次改动 | `workflows/change.json` |

**新业务场景 = 写新工作流模板（重排 `stages/` 里已有的阶段文件），不是再装一个技能。** 工作流里没有的阶段就不做，做了也要在 change-note 记账。

## 选型表

`$KNOW/**` 按业务域拆分，**一次只加载一个域文件**；`$TEMPLATES/**` 放公司模板。清单与信任级别见 `stages/oncall/references/knowledge-sources.md`。

| 选择 | 执行 |
|------|------|
| 需求分析 | `stages/requirement-analysis/SKILL.md`。拍板用全局技能 `grilling`（要它读文档时把文档路径一起给它）。访谈前先从 `$KNOW/<相关域>/` 取一个域文件建立口径，不要凭记忆问用户已写过的东西。九项负债与风险评估必须在选方案之前答完。产出 `specs/<feature>/spec.md` |
| 影响面评估 | `stages/impact-assessment/SKILL.md`。四轴（调用方 / 状态机 / 租户权限 / 回滚）+ 维护性三查，每项带证据或 `UNVERIFIED`。产出 `specs/<feature>/impact.md` |
| 技术方案 | `stages/tech-design/SKILL.md`（模板 `$TECH_DESIGN_TEMPLATE`，为空则问用户）。需要架构图时用 `stages/excalidraw-diagram/SKILL.md`。一页方案未确认时回到 `grilling`。产出 `plan.md` + `rollback.md` |
| 编码实现 | `stages/implementation/SKILL.md`。写 Go 前读 `stages/implementation/references/go-style.md`，改完 Go 后读 `stages/implementation/references/reuse-gate.md` |
| 改动审核 | `stages/change-review/SKILL.md`。三轴并行子 agent（spec 合规 / 代码质量 / 接口影响）共读同一份 `specs/<feature>/diff.patch`，主 agent 合并裁决 |
| 质量检查 | `stages/quality-gate/SKILL.md`，以命令输出为准 |
| 接口测试 | `stages/interface-test/SKILL.md`。三级门：`go test ./api/...` → `scripts/contract_diff.sh` → 场景回放（跑不了如实 WAIVED）。四态裁决 PASS/CONCERNS/FAIL/WAIVED |
| 排查确认 | `stages/oncall/SKILL.md`，保持只读。业务知识走 `stages/oncall/references/routing.md` 域路由，**不要读仓库 `docs/support/`——那是降级区**。根因是偶发故障或性能回退时再读全局技能 `diagnosing-bugs`；不存在就停在 oncall 结论 |
| 提交 | `stages/git-commit/SKILL.md`（MR 模板 `$MR_TEMPLATE`）。**提交前过文档审计门**，产出 `specs/<feature>/change-note.md` |

点名才读，不进菜单：`ponytail-review`（删过度设计）、`security-best-practices`、`security-threat-model`、`gh-fix-ci`、`gh-address-comments`、`domain-modeling`（改 `CONTEXT.md` 或术语时）。这些是全局技能，按名字调用。

归档已完成的需求见 `references/feature-archive.md`。

## 串联（主链九步）

`feature` 工作流的完整链，前一步的产出就是后一步的输入。其它工作流是它的裁剪版，见 `workflows/*.json`：

```
① 环境探测 + 查重      → branch/commit/dirty、知识新鲜度、已有产出
② 需求分析（含九项负债） → specs/<feature>/spec.md
③ 影响面评估            → specs/<feature>/impact.md
④ 技术方案 + 回滚预案    → specs/<feature>/plan.md · rollback.md
⑤ 编码实现              → 代码 + 必要的契约测试
⑥ 改动审核（三轴并行）   → specs/<feature>/review/*.md
⑦ 质量门（构建+单测）    → specs/<feature>/quality.md
⑧ 接口门（三级）         → specs/<feature>/interface-test.md
⑨ 文档审计 + 提交        → specs/<feature>/change-note.md · commit · MR
```

一页方案是评审阅读的正文；公司模板只承接已确认的内容，空章节写「无」。用户没要求发工单时不发布 issue。

排查确认（`oncall`）单独走，不插入这条链；但在 `bugfix` / `hotfix` 工作流里它是第 ① 步。

每步结束用一句话汇报产出（工件路径 + 门的结论），并问是否进入下一步；用户说「一路到底」则连续做完，**门禁命中时仍然停**。

## 工件

每步的产出都落盘，落点与命名见 `references/artifact-tree.md`，模板在 `$PLUGIN_ROOT/templates/`。写 spec、impact、plan、rollback、review、change-note 之前读 `references/doc-shape.md`：一篇一个主活，第一屏答完「这是干什么的、读者现在该做什么」。

**工件是流程的记忆**：对话会被上下文压缩吃掉，落盘的文件不会。三条纪律——一步一产物、产物只引用不复述、每条事实可复现（带 `文件:符号` 或命令输出，做不到就写 `UNVERIFIED`）。

## 多 agent 什么时候用

判据与完整协议见 `references/subagent-protocol.md`。一句话版：

- **派**：2 个以上彼此独立、无共享写状态、互不需要对方上下文的问题（典型：审核三轴、影响面四轴取证、多域调研）。
- **不派**：实现类任务（共享工作树会互相覆盖）、探索性 debug（需要连续假设）、相关联的失败（同一根因）、事故期、以及**任何裁决**（判 breaking、判风险等级）。
- **取证可并行，裁决不可并行。** 合并结论永远是主 agent 的活。
- 协议靠文件承载：`agents/brief-*.md`（派活书，四要素）、`agents/report-*.md`（证据 + UNVERIFIED）、`agents/ledger.md`（台账，压缩后唯一可信状态源）。
- brief 里**不塞业务事实**，让子 agent 自己去 `$KNOW` 与代码查 —— 塞下去等于把主 agent 的偏见传成锚点。
- fix loop 上限 2 轮，第 3 轮不收敛就 `parked with ruling`：停下、原样交给用户、附裁决建议。

## 门禁

六道门，任一未过就停下等用户，不自行绕过：

1. **负债门**（需求阶段）：九项评估里第 2/4/6/7/8/9 项阻塞且无缓解 = 不进技术方案；方案只有一个或没有「最小改动」= 视为未做分析。
2. **影响面门**：四轴任一项空白（既无证据也没标 UNVERIFIED）= 评估未做；数据不可逆 + 无备份 + 无重放 = 阻塞。
3. **改动审核门**：有 high 或 medium 时停，不进入质量门；review 指纹（base/head sha + 文件数 + 行数）与工作树不一致时结论 STALE，必须重跑。
4. **接口门**：`go test ./api/...` 失败 = FAIL；`contract_diff.sh` 报 BREAKING 而没逐行裁决 = FAIL；场景回放跑不了只能记 WAIVED 并写补跑条件，**不许谎报 PASS**。
5. **文档审计门**（提交前）：对照 `git diff --name-only` 核 `specs/<feature>/`、README、CONTEXT、知识层是否同步；不同步就必须在 change-note 里显式记「接受的文档风险」，二选一，不许沉默提交。
6. **知识新鲜度**：按步骤 0 的三层执行。完成标准：产出引用了 STALE 取值却未回代码 = 未过；文档本身 STALE 不停工。

编码实现一旦入选，改动审核 → 质量 → 接口 → 文档审计按上面顺序跟着做完；提交留到最后。

## 三条硬规则

1. **答案与产出里不复述知识层内容，只引用你读过的文件。**复述是「看起来完整却漏链路」的来源。
2. **一次只加载一个业务域文件。**跨域问题分小节各自给信源，不做合并大表。
3. **阶段是本技能内的文件，读 `stages/<name>/SKILL.md`，不把它们装成别的技能，也不用技能名去调用。** 全局技能（`grilling`、`diagnosing-bugs` 等）仍按名字调用。新增引用时同样遵守。
