# data-workflow

这个仓库做两件事。一是拦住代理写错文件、以及没跑检查就说做完。二是让它知道一个词、一个字段、一个状态在这个业务里是什么意思。意思不写进技能，运行时从知识层读。

data-service（Go / Kratos）的阶段链是高风险变更上的模板，不是所有改动的默认路径。安装是把 `skills/data-workflow/` 复制进工具目录。副本自包含，不软链回本仓库。

## 你在什么状态，读什么

- 第一次安装 → [`docs/install.md`](docs/install.md)
- 会话里有 NOTICE → 那是另一条未完成运行，不代替当前这句话。要继续它再跑 `next`
- 要选工作流，或看卡在哪一道门 → [`skills/data-workflow/references/workflows.md`](skills/data-workflow/references/workflows.md)
- 要查 `next` / `wait` / `done` → [`skills/data-workflow/references/commands.md`](skills/data-workflow/references/commands.md)。Agent 输入框输入 `/`，选 `dw-next`、`dw-done`、`dw-wait`、`dw-start`
- 要知道一个词在业务里指什么 → 知识层。路径空就问。键在 [`config.example.yaml`](config.example.yaml)。留空时 drift 打印 `DEGRADED`，回退 `<repo>/docs`
- 要改技能或新增阶段 → 下面的项目结构。阶段正文在 `skills/data-workflow/stages/`，选型在 `SKILL.md`
- 要重画两张图 → [`docs/diagrams.md`](docs/diagrams.md)

## 知识层

业务梳理用现在这套，不另建技能。顺序在 `stages/oncall/references/routing.md`：先 grep `$CARDS/`，再读相关的一个域文件，取值回代码。证据指向另一个域时再读那一个。卡片带 `verified_commit`、`watches`、`verified_at`。`knowledge_drift.sh` 标 `FRESH` / `STALE`，不停工。`status: superseded` 的卡跳过，留着查历史。代码证明的是现在的行为，不是「业务要求永远如此」。

没有出处的词进待确认，用 `wait` 停，不编一个看起来合理的含义。命中卡片后对照它的 `watches`：代码仍符合才当现行规则；已经不符合就标冲突，旧卡标 `superseded`。用户要留下这条，按 `stages/oncall/references/capture.md` 写一张卡，带上 `kind`、`object`、`applies_to`。一次运行结束时，只回写这次证实或推翻的那一条。不先写领域百科。

动手前读 `skills/data-workflow/references/scope.md`。先写用户真正要解决的问题和怎样算满足，再决定改多宽。L1 走 `change`。契约、持久化、权限、状态、回滚即使改动很小也升到 `feature` 或 `hotfix`。与这次无关的债不进这次 diff。

任意仓库定架构也走 `change`。形状写在 `specs/<feature>/decision.md`：现有边界、这次不新增什么、下一刀落在哪。data-service 的九步是高风险模板，不是这套架构本身。别的仓库用自己的 `protected_paths`；两个保护键都写成空，才关掉默认的 Go 路径。

## 分层

![data-workflow 分层架构](assets/architecture.png)

加载方向只能向下，一次只读一个文件。

| 层 | 位置 | 内容 | 加载方式 |
|---|---|---|---|
| L0 编排 | `skills/data-workflow/SKILL.md` | 选型。零事实 | 入口触发 |
| L1 阶段 | `skills/data-workflow/stages/` | 每个阶段的步骤 | 选型表点名才读 |
| L2 知识 | `$KNOW/**`、`$TEMPLATES/**` | 业务事实 | 一次一个域文件 |
| L3 权威 | 代码、生成物、聚焦测试 | 取值 | 回这里核对 |

仓库内 `docs/`、`docs/support/` 是降级区：只可当搜索线索。data-service 里 MQTT 推送链路和 Episode 终态以代码为准。

## 主链

![data-workflow 完整流程](assets/flow.png)

`workflows/feature.json` 串行。每步一个产物。六道门的通过条件、以及未过时停在哪里，在 [`references/workflows.md`](skills/data-workflow/references/workflows.md)。

| 步 | 产出 | 门 |
|---|---|---|
| 环境探测 + 查重 | branch、commit、新鲜度 | 新鲜度 |
| 需求分析 | `specs/<feature>/spec.md` | 负债 |
| 影响面 | `specs/<feature>/impact.md` | 影响面 |
| 技术方案 | `plan.md`、`rollback.md` | |
| 编码 | 代码 | 编码步骤的退出码 |
| 改动审核 | `specs/<feature>/review/*.md` | 改动审核 |
| 质量 | `specs/<feature>/quality.md` | |
| 接口 | `specs/<feature>/interface-test.md` | 接口 |
| 提交 | `specs/<feature>/change-note.md` | 文档审计 |

`bugfix` / `hotfix` 的第一步是排查。`oncall` 和画图不插入这条链。没有 data-service 门禁时用 `workflows/change.json`，三步：`decision.md`、改文件、`check.md`。

工件落点在 [`references/artifact-tree.md`](skills/data-workflow/references/artifact-tree.md)。写入放行在 [`references/edit-gate.md`](skills/data-workflow/references/edit-gate.md)。什么时候派子代理在 [`references/subagent-protocol.md`](skills/data-workflow/references/subagent-protocol.md)。

## 设计原则

判断一句话该放哪：明天一次代码提交能否让这句话变成假的，而不必改它所在的文件？

- 能 → 事实，放知识层，带 `verified_commit` 和 `watches`
- 不能 → 流程，放技能

指针是流程，取值是事实。「EpisodeStatus 定义在 `internal/biz/status.go`」仍成立；「终态是 90/91」一次提交就假。过期后要漏得响：代理去代码里找，而不是信一份不再更新的清单。

## 项目结构

```
data-workflow/
├── AGENTS.md                     薄指路牌
├── config.example.yaml           配置键。副本里的 config.yaml 不进本仓库
├── docs/                         安装、脚本、重画图
├── evals/evals.json              每条钉住一个已经踩过的缺陷
├── scripts/install.sh
└── skills/data-workflow/         唯一安装的技能
    ├── SKILL.md                  选型
    ├── commands/                 复制到目标仓库 .cursor/commands/ 的 / 命令
    ├── workflows/                feature · bugfix · hotfix · review-only · change
    ├── references/               命令、门、工件、写入放行。点名再读
    ├── scripts/
    └── stages/                   阶段文件，不单独安装
```

常驻的只有技能的名称和描述。触发后读 `SKILL.md`。选型表点名后，只读那一个 `stages/<name>/SKILL.md`。

## 安装与验证

```bash
cd <目标仓库根>
bash ~/skills/data-workflow/scripts/install.sh
```

三种模式、卸载和 Qoder 插件通道在 [`docs/install.md`](docs/install.md)。脚本清单在 [`docs/scripts.md`](docs/scripts.md)。

评测在 [`evals/evals.json`](evals/evals.json)。每条有 `pass` / `fail`，对应一个已经踩过的缺陷。
