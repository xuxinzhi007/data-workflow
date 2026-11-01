# business-model 决定

> 规则在 `references/scope.md`。级别 L1：新增一个 references 文件、一个模板、两个脚本参数，并把知识落点改成「仓库内优先」。不碰业务契约。

- 级别：L1
- 原话（一字不改）：先进行一次本地提交吧 ，然后继续b 的路程
- 本质：把业务分析从「只有检索协议」补成「有分析骨架」，并让业务事实能落进仓库、随代码提交——否则每次分析都从零开始。
- 怎样算满足：`references/business-model.md` 里的维度能被 `oncall` 与 `scope.md` 直接引用；`paths.sh` 输出 `DOMAIN_DOCS`；`knowledge_drift.sh` 默认扫描包含 `$REPO/docs/domain/*.md`；`bash scripts/verify.sh` exit 0 且有对应用例。
- 未知：无
- 这次不做：不问用户要真实业务仓库来做一次端到端演练（会需要新的知识源，且这轮是 L1 的结构改动）；不动 `$KNOW` 的既有内容；不写任何具体取值（状态数字、字段名）。

## 真正要解决的问题

`docs/competitive.md` §3 里承认的第一条短板：**业务分析不可累积**。

拆开是两件事，都不是模型能力问题：

1. **有检索协议，没有分析骨架。** `routing.md` 教的是"先查卡片、再读一个域文件、再回代码"——是**去哪找**。全程没有回答"看什么维度"：对象与身份、状态族、写入口与守卫、读侧可见性、角色与数据范围、外部通道、幂等、审计、契约。缺这一层时，agent 面对一个陌生业务只能写通用散文。
2. **事实不落仓库。** 业务事实在 `$KNOW`（个人 vault，仓外，且 `knowledge-sources.md` 自述整个知识层没有 baseline commit），分析产物在 `specs/`（被 install 写进 `.gitignore`）。于是"这次证明对了"成立，"下次更快"不成立。

## 现状（带证据）

| # | 事实 | 证据 |
|---|---|---|
| 1 | 分析维度里只有「状态族」有专门文件，其余八项零散在各处或缺失 | `stages/oncall/references/state-protocol.md`；"实体/角色/不变量"在 45 个 md 里几乎零命中（上一轮 grep 结果） |
| 2 | 业务事实的落点只有仓外两个：`$KNOW` 与 `$CARDS` | `oncall/references/knowledge-sources.md`、`capture.md` 的落点表 |
| 3 | 知识层没有 baseline，`knowledge_drift.sh` 只对卡片生效 | `knowledge-sources.md`「已知缺口」；`knowledge_drift.sh` 默认只扫 `$VAULT_KNOWLEDGE` + `CONTEXT.md` |
| 4 | `docs/agents/domain.md` 已经写了仓库内落点（`GLOSSARY.md` + `docs/adr/`），技能却不读它 | 该文件存在；技能侧 `project-index.md` 只说 `$KNOW` |

## 现有能力（复用）

- `knowledge_drift.sh` 已经支持传任意 md：只要带 `verified_commit` + `watches` 就判 FRESH/STALE。**不用新写脚本**，只要把它默认扫的目录加上仓库内域文档。
- `capture.md` 的卡片格式（`object`/`applies_to`/`invalidates_when`）可直接复用到域文档 frontmatter。
- `paths.sh` 的 `emit` 与 CARDS 的推导方式：加一个 `DOMAIN_DOCS` 即可。

## 最小充分方案

1. 新增 `references/business-model.md`：九个维度，每个写「问什么 / 去哪读 / 证据形式 / 典型错答」，**不含任何取值**。
2. 新增 `templates/domain-doc-template.md`：仓库内域文档的骨架 + frontmatter（复用卡片的字段名，让同一套 drift 规则生效）。
3. `paths.sh` 增 `DOMAIN_DOCS`；`knowledge_drift.sh` 默认扫描 `$REPO/docs/domain/*.md`。
4. 把「仓库内优先」写进四处：`routing.md` step 1、`oncall/SKILL.md`、`scope.md`「先看口径」、`knowledge-sources.md` 的信任级别表。
5. `check_runner` 加一条用例：仓库里有 `docs/domain/*.md` 时 `paths.sh` 输出它、drift 能判级。

## 为什么更小的做法不够

只写 `business-model.md` 不动落点：分析维度有了，结论还是落在仓外，下次照旧从零开始。
只改落点不写维度：仓库里多一个空模板，agent 仍然不知道往里面填什么。

## 相关的债

- A 现在偿还：`docs/competitive.md` §3「真不如人的地方」第 1、2 条的一半（知识落仓库、分析维度）。
- B 局部偿还：`$KNOW` 保持原样，只是把优先级降到「补充源」，并要求引用时标「未核对」。
- C 暂缓：把已有 `$KNOW` 内容批量迁进仓库（要人判断哪条还成立，属独立工作）。

## 这次不做

- 不搬 `$KNOW` 的既有内容，不建空的 `docs/domain/` 目录（技能不猜别的仓库结构）。
- 不动 `feature` 九步链（它是 Go 实例模板）。
- 不写任何业务取值示例（状态数字、字段名、表名）——那正是会腐烂的东西。

## 风险

不碰契约、持久化、权限、状态、回滚。行为变化一处：`oncall` 的加载顺序从「先 `$KNOW` 域文件」变成「先仓库内 `docs/domain`（有的话）」；两者都空时仍走降级区并声明。
