# 内部待确认断言清单

**这个文件存在的理由**：项目里有一批断言的证据强度和「外部查不到出处的数字」完全一样，但它们以陈述句进了架构论证。承认过一次不算数——进这张表才算。

规则：

- 一条断言一行，**写清错了会怎样**（代价）。按代价排序，不按发现顺序。
- 有证据的移到「已证实」，写清证据形式（命令 / 测试名 / commit）。
- 状态只有四种：`已证实` / `推断` / `待确认` / `存在冲突`，与 `references/scope.md` 同一套。
- **外部数字（论文、行业报告）一律进这张表**，除非能给出可复核的出处。

---

## 待确认（按代价降序）

| # | 断言 | 代价 | 状态 | 怎么才能证实 |
|---|---|---|---|---|
| C1 | `protected_paths` 里 `api/`、`*.proto`、`*.pb.go`、`internal/biz/status.go` 是「该保护」的路径 | **高**：这是全线唯一不依赖 LLM 的增量。配错了，这个增量价值为零；漏配了，真该保护的东西不设防 | 待确认 | 需要业务方给出「为什么这个路径动之前必须有人拍板」。**当前全仓无此依据**，`config.yaml` 默认 `""` |
| C2 | 「70% 写操作覆盖率」（19 项探针中拦 14） | **高**：这是对唯一增量的可靠性描述，会被人当事实引用 | 待确认（**有偏样本**） | 19 项是凭经验枚举的，不是从 Agent 实际 shell 日志抽的。仓库内**无 shell 命令日志**。需先采集真实命令频次，再加权统计 |
| C3 | `gate` 字段（自评提示）对产出质量有正贡献 | **高**：若为负（降低审查强度），它比没有更危险 | 待确认（**实验已设计，机制层已锁**） | 2×2 对照见 `c3-c9-experiment.md`。第一层（机制性质）已进 `verify.sh`：`case_no_hints_switch` 证明开关只摘 SELF_CHECK。第二层（AI 表现，N=10×4 组）未跑 |
| C4 | `fail-open`（未知工具、MCP 写入放行）是有意设计 | **中高**：若无事后补偿机制，「放行」等于没有兜底 | 待确认 | 需要一条「MCP 写了受保护文件，事后怎么发现」的补偿路径。**当前没有** |
| C5 | 「一次只读一个文件」优于一次性加载 | **中**：影响上下文供给策略；`business-model.md` 称合并会互相污染，但未测 | 待确认 | A/B 实验，需先固定 stage 划分（C6） |
| C6 | 24 个 stage 的边界划得对 | **中**：前置于 C5；格子划错，测什么都不干净 | 待确认 | 边界重叠/合并分析，未做 |
| C7 | `change` 三步对 L1 改动不过重 | **中低**：体验问题，不伤正确性 | 推断 | 无数据；仅「用户反馈偏重」 |
| C8 | `quality-gate` G7 知识反哺跑得对 | **已降级**：判据已存在且会拦（见「已证实」V10），但只判 `verified_commit` 是否 == HEAD，**不判内容对不对**；「口径冲突只标不改」仍只是文字，无用例 | 存在冲突 | 仍需：拿真实域文件跑一次，看 §4 符号是否真刷新 |
| C9 | `confess` 通道（独立自白文件，不入门、不影响推进）能提升自评的诚实度 | **中高**：效仿 OpenAI 自白（2025-12-03），目标分离是该机制成立的前提。若无效，它只是又多一层仪式，且会让人误以为有了诚实保障 | 推断（**外部结论，非本仓实测**）；机制性质已锁，效果未测 | 2×2 对照见 `c3-c9-experiment.md`。第一层已进 `verify.sh`：`case_confess_never_gates` 锁住「写什么都不影响推进」。第二层未跑。**绕开 C6**（只跑 change 三步，不碰 24 个 stage） |

---

## 已证实（附证据形式）

| # | 断言 | 证据 |
|---|---|---|
| V1 | `gate_strict` 默认关闭，异常一律 fail-open | `check_runner: case_gate_strict / bad input fails open`；`gate_edit.py:481` |
| V2 | 内容门是全文子串匹配，不解析 Markdown 结构 | `workflow_next.py:353` `item not in text` |
| V3 | `contract_diff` 归一化为排序去重集合，注释与顺序变动不误报 | `proto_contract.py:33` `strip_comments` |
| V4 | `knowledge_drift.sh` 恒 exit 0，不停工 | `knowledge_drift.sh:15,196` |
| V5 | `workflow_next.py` 零 LLM 调用，下一步由脚本按 `run.json` 算 | grep 无 openai/anthropic/llm 调用 |
| V6 | hook 拦得住 `>` `>>` `tee` `sed -i` `cp` `mv` `rm` heredoc 及 Write/Edit/multiEdit | 探针实测 14 项（见 `references/edit-gate.md` 覆盖表） |
| V7 | hook 漏 `python -c open().write`、`git apply`、`patch`、`dd of=`、`truncate`、`install`、MCP 工具、未知工具 | 同上，实测 5+2 项 |
| V8 | 状态机无回退边（`abandon`/`bypass` 是终止边，非回退边） | 遍历 workflow JSON，无指向前序阶段的字段 |
| V9 | `SKILL.md` 102 行，`stages/` 24 个文件，`references/` 10 个 | `wc -l` |
| V10 | G7 知识反哺有可执行的判据，且三种状态都会拦/放行 | `check_runner: case_g7_gate_runs`（命中→拦、刷新→放行、无关→不命中）；实现 `workflow_next.knowledge_feedback()` |
| V11 | confess 通道不参与任何判定：写不写、写什么都不改变 next 输出与 run.json 的 stage；`needs_confess` 对写决定阶段为假 | `check_runner: case_confess_never_gates`（四条子断言）；`workflow_next.py: needs_confess/confess_missing` |
| V12 | `DATA_WORKFLOW_NO_HINTS=1` 只摘掉 SELF_CHECK 行，其余输出逐字不变 | `check_runner: case_no_hints_switch`（逐字比对 on/off 全文） |
| V13 | 「未知」栏在真实运行里 88% 写「无」（15/17），而「可能理解错」栏 91% 在写内容（10/11） | `bash scripts/self-eval-stats.sh`（读 `specs/*/decision.md` 的真实分布，20 次运行）；`check_runner: case_honesty_stats_runs` 锁住判定逻辑 |

---

## 已撤回的断言（留档，防复活）

| 断言 | 撤回理由 |
|---|---|
| 「9 个技能名踩 7±2 记忆上限」 | 理由错。真实问题是缺触发条件，不是记忆超载 |
| 「应给 stages 加 `disable-model-invocation`」 | 前提错。stages 不是独立 skill，该字段无效；且三入口均被 workflow 引用 |
| 「外部材料与本项目独立印证」 | 语境不同（大团队/通用域 vs 单开发者/特定域），形状相似不等于约束相同 |
| 「同时只有 1 个 stage 在上下文」 | 读入不自动消失，要么靠有损摘要，要么根本不成立。且曾用它驳回 Skill++，属循环论证 |
| 「模型绕不过 hook」 | 只对常规写工具成立；`python -c` 与 MCP 可绕。混了宿主动作与模型行为 |
| 「`abandon`/`bypass` 可回应异常路径缺失」 | 偷换。终止边 ≠ 回退边 |

---

## 外部数字（未核实，不得当依据）

以下来自行业研究综述，**无法复核出处**，与本文件上半部分同等对待：

- Context Folding / FoldGRPO（ICML 2026）：小 10 倍活跃上下文
- GraSP：奖励最多 +19 分，步数 −41%
- Skill++：技能选择率 36.4% → 76.3%（731 个技能）
- AgentSkillOS：最高 20 万技能
- 1,026 个编排框架 bug、API 误用约 33%
- Anthropic 平台软件工程调用占比 49.7%

用法：可以作为**假设来源**，不可以作为**架构依据**。
