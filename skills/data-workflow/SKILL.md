---
name: data-workflow
description: data-service 开发工作台，需求到提交的唯一入口。用户说 @data-workflow、data-skill、开始开发、dev、开发工作台、今天干什么活，或要做需求分析、技术方案、编码实现、改动审核、质量检查、排查确认、提交时读取本文件并按菜单执行。不用于：只判断改动风险（直接 data-workflow:change-review）、追查线上症状与状态含义（直接 data-workflow:oncall）、纯 git 操作、画图（直接 data-workflow:excalidraw-diagram）、与 data-service 无关的任务。
---

# data-service 开发工作台

本文件只负责**选型、顺序、门禁**。具体步骤在被点名的技能里；业务事实一律运行时从 Obsidian 知识库读，本文件不保存任何取值、状态名、字段名。

项目索引（去哪读什么）在 `references/project-index.md`，进入具体工作后再读。

`$PLUGIN_ROOT` = 本 SKILL.md 往上两级的目录（`scripts/` 与 `skills/` 同级）。

## 启动

### 步骤 0 环境探测（整个会话只做一次）

```bash
"$PLUGIN_ROOT/scripts/repo_snapshot.sh"
"$PLUGIN_ROOT/scripts/knowledge_drift.sh"
```

记下 branch、commit、是否有未提交改动，以及每份知识文档的 FRESH / STALE / SKIP。结果**向下游所有步骤传递，任何步骤技能不再重复探测**。

新鲜度规则：`FRESH` 可当证据引用；`STALE`（含缺 frontmatter 的）只当线索——用它选搜索目标，取值回代码重新推导，并在产出里说明哪份文档已过期。门禁**只标注、不阻塞**，不要因为 STALE 就停下不干活。

### 步骤 1 查重（进入任何一步之前）

- 是否已有覆盖此事的产出？`grep -rl "<主题词>" .cursor/plans/ "$VAULT/knowledge/排查卡片/"`
- 是否与已钉住的决策冲突？看 `.cursor/plans/` 里最近那份的决定表。
- 用户这句话是否已点明选型表中的某一行？

命中已有产出就接着它做，不要重开一份。

### 步骤 2 选型

用户这句话已点明下表某一行：直接读该行技能并执行，跳过菜单。
用户只说开始干活：立刻用 AskUserQuestion 弹菜单，等选择后再往下。一次一题，`multiSelect: true`，题目写「这次做哪几件？可多选，按下面顺序串行。」选项：需求分析 / 技术方案 / 编码实现 / 改动审核 / 质量检查 / 排查确认 / 提交。

## 选型表

`VAULT` = `/Users/xuxinzhi/Documents/Obsidian Vault/xxz_obsidian`（含空格，命令必须引号包裹）。`knowledge/**` 按业务域拆分，**一次只加载一个域文件**；`开发规范化/**` 放公司模板。清单与信任级别见 `data-workflow:oncall` 的 `references/knowledge-sources.md`。

| 选择 | 执行 |
|------|------|
| 需求分析 | `data-workflow:requirement-analysis`。拍板用全局技能 `grilling`（要带文档就 `grill-with-docs`）。访谈前先从 `$VAULT/knowledge/<相关域>/` 取一个域文件建立口径，不要凭记忆问用户已写过的东西。决定闭环后写一页方案，再按全局技能 `to-spec` 写 spec，不再访谈 |
| 技术方案 | `data-workflow:tech-design`（模板 `$VAULT/开发规范化/研发技术方案-模板.md`）。需要架构图时用 `data-workflow:excalidraw-diagram`。一页方案未确认时回到 `grilling` |
| 编码实现 | `data-workflow:implementation`。写 Go 前读它的 `references/go-style.md`，改完 Go 后读 `references/reuse-gate.md` |
| 改动审核 | `data-workflow:change-review`；同一份 diff 再按它的 `references/standards-spec.md` 做规范与需求符合性审核，结论合并成一份 |
| 质量检查 | `data-workflow:quality-gate`，以命令输出为准 |
| 排查确认 | `data-workflow:oncall`，保持只读。业务知识走它的 `references/routing.md` 域路由，**不要读仓库 `docs/support/`——那是降级区**。根因是偶发故障或性能回退时再读全局技能 `diagnosing-bugs`；不存在就停在 oncall 结论 |
| 提交 | `data-workflow:git-commit`（MR 模板 `$VAULT/开发规范化/MR模板.md`） |

点名才读，不进菜单：`ponytail-review`（删过度设计）、`security-best-practices`、`security-threat-model`、`gh-fix-ci`、`gh-address-comments`、`domain-modeling`（改 `CONTEXT.md` 或术语时）。这些是全局技能，按名字调用。

归档已完成的需求见 `references/feature-archive.md`。

## 串联

多选时按这个顺序，前一步的产出就是后一步的输入：

需求分析（grilling → 一页方案 → spec）→ 技术方案（一页方案填进公司模板）→ 编码实现 → 改动审核 → 质量检查 → 提交

一页方案是评审阅读的正文；公司模板只承接已确认的内容，空章节写「无」。spec 与一页方案放同一知识库目录，文件名 `<主题>-spec.md`。用户没要求发工单时不发布 issue。

排查确认单独走，不插入这条链。每步结束用一句话汇报产出，并问是否进入已选的下一步；用户说「一路到底」则连续做完。

## 门禁

三道门，任一未过就停下等用户，不自行绕过：

1. **改动审核**：有 high 或 medium 时停，不进入质量检查。
2. **质量检查**：以命令输出为准，未通过时停在失败项。
3. **知识新鲜度**：产出里引用了 `STALE` 文档的取值、却没回代码重新推导，算未过。

编码实现一旦入选，改动审核与质量检查按上面顺序跟着做完；提交留到两者都通过之后。

## 三条硬规则

1. **答案与产出里不复述知识层内容，只引用你读过的文件。**复述是「看起来完整却漏链路」的来源。
2. **一次只加载一个业务域文件。**跨域问题分小节各自给信源，不做合并大表。
3. **技能之间用命名空间名互相调用（`data-workflow:xxx` 或全局技能名），不写绝对路径。**新增引用时同样遵守。
