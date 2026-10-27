---
name: data-workflow
description: data-service 开发工作台，需求到提交的唯一入口。用户说 @data-workflow、data-skill、开始开发、dev、开发工作台、今天干什么活，或要做需求分析、技术方案、编码实现、改动审核、质量检查、排查确认、提交时读取本文件并按菜单执行。不用于：只判断改动风险（直接 data-workflow:change-review）、追查线上症状与状态含义（直接 data-workflow:oncall）、纯 git 操作、画图（直接 data-workflow:excalidraw-diagram）、与 data-service 无关的任务。
---

# data-service 开发工作台

本文件只负责**选型、顺序、门禁**。具体步骤在被点名的技能里；业务事实一律运行时从知识层读，本文件不保存任何取值、状态名、字段名。

项目索引（去哪读什么）在 `references/project-index.md`，进入具体工作后再读。

`$PLUGIN_ROOT` = 本 SKILL.md 往上两级的目录（`scripts/` 与 `skills/` 同级；软链安装时先用 `readlink -f` 解析）。

外部路径不写死在技能里，会话开头解析一次（步骤 0 之前）：

```bash
eval "$(bash "$PLUGIN_ROOT/scripts/paths.sh")"
# → $KNOW 知识根 / $CARDS 排查卡片目录 / $TEMPLATES 公司模板根
#   $REPO 被测代码仓库 / $TECH_DESIGN_TEMPLATE / $MR_TEMPLATE / $PERSONAL_AGENTS_MD
```

路径可能含空格，命令里必须引号包裹。解析出空值的键**不许猜绝对路径**：要么问用户，要么显式声明降级后继续。

## 启动

### 步骤 0 环境探测（整个会话只做一次）

```bash
"$PLUGIN_ROOT/scripts/repo_snapshot.sh"
"$PLUGIN_ROOT/scripts/knowledge_drift.sh"
```

记下 branch、commit、是否有未提交改动，以及每份知识文档的 FRESH / STALE / SKIP。结果**向下游所有步骤传递，任何步骤技能不再重复探测**。

新鲜度规则：`FRESH` 可当证据引用；`STALE`（含缺 frontmatter 的）只当线索——用它选搜索目标，取值回代码重新推导，并在产出里说明哪份文档已过期。门禁**只标注、不阻塞**，不要因为 STALE 就停下不干活。

### 步骤 1 查重（进入任何一步之前）

- 是否已有覆盖此事的工件？`grep -rl "<主题词>" "$REPO/specs/" "$CARDS/"`
- 是否与已钉住的决策冲突？看 `specs/` 里最近那份的决定表，以及该 IDE 的临时目录（`.cursor/plans/`、`.qoder/plans/` 等等价物）。
- 用户这句话是否已点明选型表中的某一行？

命中已有产出就接着它做，不要重开一份。

### 步骤 2 选型

用户这句话已点明下表某一行：直接读该行技能并执行，跳过菜单。
用户只说开始干活：立刻用 AskUserQuestion 弹菜单，等选择后再往下。一次一题，`multiSelect: true`，题目写「这次做哪几件？可多选，按下面顺序串行。」选项：需求分析 / 影响面评估 / 技术方案 / 编码实现 / 改动审核 / 质量与接口 / 排查确认 / 提交。

### 步骤 3 选工作流

选完要做的事，再选**按哪条流程串**。工作流是确定性状态机（`$PLUGIN_ROOT/workflows/*.json`），阶段顺序、每阶段的技能、门禁、能不能派子 agent 都写在里面：

| 场景 | 工作流 |
|---|---|
| 新能力 / 扩展 / 新字段 / 新端点 | `workflows/feature.json` |
| 已知错误行为要修 | `workflows/bugfix.json` |
| 线上正在出事，最短路径止血 | `workflows/hotfix.json` |
| 只审不改（评 MR、上线前把关） | `workflows/review-only.json` |

**新业务场景 = 写新工作流模板（重排现有技能），不是加新技能。** 技能池是复用的，模板才是扩展点。工作流里没有的阶段就不做，做了也要在 change-note 记账。

## 选型表

`$KNOW/**` 按业务域拆分，**一次只加载一个域文件**；`$TEMPLATES/**` 放公司模板。清单与信任级别见 `data-workflow:oncall` 的 `references/knowledge-sources.md`。

| 选择 | 执行 |
|------|------|
| 需求分析 | `data-workflow:requirement-analysis`。拍板用全局技能 `grilling`（要它读文档时把文档路径一起给它）。访谈前先从 `$KNOW/<相关域>/` 取一个域文件建立口径，不要凭记忆问用户已写过的东西。九项负债与风险评估必须在选方案之前答完。产出 `specs/<feature>/spec.md` |
| 影响面评估 | `data-workflow:impact-assessment`。四轴（调用方 / 状态机 / 租户权限 / 回滚）+ 维护性三查，每项带证据或 `UNVERIFIED`。产出 `specs/<feature>/impact.md` |
| 技术方案 | `data-workflow:tech-design`（模板 `$TECH_DESIGN_TEMPLATE`，为空则问用户）。需要架构图时用 `data-workflow:excalidraw-diagram`。一页方案未确认时回到 `grilling`。产出 `plan.md` + `rollback.md` |
| 编码实现 | `data-workflow:implementation`。写 Go 前读它的 `references/go-style.md`，改完 Go 后读 `references/reuse-gate.md` |
| 改动审核 | `data-workflow:change-review`。三轴并行子 agent（spec 合规 / 代码质量 / 接口影响）共读同一份 `specs/<feature>/diff.patch`，主 agent 合并裁决 |
| 质量检查 | `data-workflow:quality-gate`，以命令输出为准 |
| 接口测试 | `data-workflow:interface-test`。三级门：`go test ./api/...` → `scripts/contract_diff.sh` → 场景回放（跑不了如实 WAIVED）。四态裁决 PASS/CONCERNS/FAIL/WAIVED |
| 排查确认 | `data-workflow:oncall`，保持只读。业务知识走它的 `references/routing.md` 域路由，**不要读仓库 `docs/support/`——那是降级区**。根因是偶发故障或性能回退时再读全局技能 `diagnosing-bugs`；不存在就停在 oncall 结论 |
| 提交 | `data-workflow:git-commit`（MR 模板 `$MR_TEMPLATE`）。**提交前过文档审计门**，产出 `specs/<feature>/change-note.md` |

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

每步的产出都落盘，落点与命名见 `references/artifact-tree.md`，模板在 `$PLUGIN_ROOT/templates/`。

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
6. **知识新鲜度**：产出里引用了 `STALE` 文档的取值、却没回代码重新推导，算未过。

编码实现一旦入选，改动审核 → 质量 → 接口 → 文档审计按上面顺序跟着做完；提交留到最后。

## 三条硬规则

1. **答案与产出里不复述知识层内容，只引用你读过的文件。**复述是「看起来完整却漏链路」的来源。
2. **一次只加载一个业务域文件。**跨域问题分小节各自给信源，不做合并大表。
3. **技能之间用命名空间名互相调用（`data-workflow:xxx` 或全局技能名），不写绝对路径。**新增引用时同样遵守。
