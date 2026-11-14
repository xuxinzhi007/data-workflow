# profile: go-kratos

> 一个 **profile** 是"某个技术栈的实例取值"。它只描述**这个栈**：分层目录、契约事实源、生成物、构建命令、专属门。
> 通用流程（`references/`、`workflows/`、`references/business-model.md`）不写实例取值——那些一次重命名就会变成假话。

## 什么时候生效

项目 `config.yaml` 写 `stack: "go"` 时。目前这个键只影响两处：

- `workflow_next.py start feature|bugfix|hotfix` 会提示（未声明时提示改走 `change`）。
- 本文件以及下表列出的实例文件是"给 Go 项目看的"，非 Go 项目等价于跳过。

**尚未生效**（欠账，写在文末）：阶段文件不会因为 `stack` 不是 go 就自动切分支，所以非 Go 项目读到本表的路径时要按「非 Go 替代」换掉。

## 这个 profile 拥有什么

| 类别 | 取值 | 落在哪 |
|---|---|---|
| 分层目录 | `internal/service`（校验/协议适配）、`internal/biz`（规则/编排）、`internal/data`（持久化） | `stages/requirement-analysis/SKILL.md`、`stages/change-review/references/standards-spec.md`、`templates/plan-template.md` |
| 契约事实源 | `api/**/*.proto`；生成物 `*.pb.go` / `*_http.pb.go` / `*_errors.pb.go` | `stages/impact-assessment/SKILL.md`、`references/edit-gate.md` |
| 契约门 | `go test ./api/...`（进程内 httptest）、`scripts/contract_diff.sh <base>` | `stages/interface-test/SKILL.md`、`stages/interface-test/references/contract-gates.md` |
| 状态族 | 状态常量集中在 `internal/biz/status.go`，按族隔离 | `stages/oncall/references/state-protocol.md` |
| 九项负债评估 | 维护性 / 可运营性 / 可信性 | `stages/requirement-analysis/SKILL.md`、`stages/requirement-analysis/references/debt-gate.md` |
| 复用门禁与风格 | 跨层依赖 = 0、重复逻辑必须复用、Go 细则 | `stages/implementation/references/{go-style,reuse-gate}.md` |
| 生成命令 | `make api` / `make api-one PROTO=...` | 本文件「质量门禁命令」；`stages/quality-gate/SKILL.md`、`stages/git-commit/SKILL.md` 只引用本表 |
| 影响面检索配方 | 按 Go 目录分层的 grep | `stages/impact-assessment/references/blast-radius.md` |
| 质量门禁命令 | 见下表 | `stages/quality-gate/SKILL.md`（G1–G5 执行本表，不硬编码） |
| 分支与 MR 节奏 | 见下「分支与版本节奏」 | `stages/git-commit/SKILL.md`（通用提交规则在 stage；本表是 data-service 实例） |

## 质量门禁命令（G1–G5 唯一命令源）

`stack: go` 时，`stages/quality-gate/SKILL.md` 的 G1–G5 按本表执行。改命令只改这里。

| 门 | 命令 | 范围与注意 |
|---|---|---|
| G1 编译 | `go build ./...` | 允许全量：编译有缓存，能捕捉跨包错误 |
| G1 wire | 按 Makefile 重新生成依赖注入 | 仅当 wire 相关文件在 G0 清单内 |
| G1 格式 | `gofmt -l`、`goimports -l` | 只对 G0 清单里的 `.go` 文件；输出必须为空 |
| G2 单测 | `./scripts/test-unit.sh -p <pkg>` | 只跑 G0 涉及包 + G4 直接受影响包；禁止不带 `-p` 的全量 |
| G3 覆盖率 | `make test-coverage-func PKG=<pkg> FUNC=<name>` | 新增导出函数覆盖率 > 0，或用例名直接对应 |
| G4 回归 | 同上 `test-unit.sh -p <pkg>` | 只对直接调用方所在包；二级传导只列风险 |
| G5 生成 | `make api` / `make api-one PROTO=<路径>` | `*.pb.go` / `openapi.yaml` 只能来自生成；手改 pb 打回 |
| G2 兜底 vet（审核用） | `go vet ./<改动涉及的包>` | 改动审核 A2；只 vet 改动包 |

### 嵌入配置（算 Go 逻辑改动）

`go:embed` 引用的配置（如 `configs/tag/system_tags.json`）算 **Go 逻辑相关改动**，G2/G3 不得跳过。圈定规则见 `references/diff-scope.md`；本段是实例取值。

### 文档审计补充（提交前）

改了 proto 时：`make api` / `make api-one PROTO=...` 已重跑，生成物与 proto **同一次提交**。检查项落在 `stages/git-commit/SKILL.md` 的通用审计表；本条是 Go 实例的 `api/**` 生成物口径。

## 分支与版本节奏（data-service 实例）

未声明 `stack: go` / 无本 profile 时，**不要**套用下面的四位版本号；跟目标仓库自己的分支与 MR 约定。

从最新的目标分支（默认 `main` 或对应 `release/x.y.z.0`）切出：

```text
<前缀>/<版本号>/<功能>
release/<版本号>

# 示例（以当前版本 26.10.1.0 为例）
feature/26.10.1.0/episode-qc-visibility
fix/26.10.1.0/task-dispatch-retry
hotfix/26.9.4.0/batch-approve-gap-lock
release/26.10.1.0
```

- 版本号为四位：`主版本.次版本.修订号.迭代号`，如 `26.10.1.0`，不带 `v` 前缀
- 版本号必须与当前开发中的 release 分支对应，新功能跟随下一个版本号
- hotfix 使用线上正在运行的版本号
- 功能描述用小写英文单词，中划线分隔，不超过 4 个词

| 前缀 | 用途 |
| --- | --- |
| `feature` | 新功能开发 |
| `fix` | 缺陷修复（跟随版本节奏） |
| `hotfix` | 线上紧急修复（对应 hotfix 版本号） |
| `release` | 版本发布分支（仅版本号，不带功能） |

```bash
git fetch origin
git checkout -b feature/26.10.1.0/episode-qc-visibility origin/main
```

Scope 优先用仓库模块名：`api`、`service`、`biz`、`data`、`conf`、`wire`。

## 非 Go 项目怎么换

| Go 实例取值 | 换成 |
|---|---|
| `internal/{service,biz,data}` | 该项目成文的工程约束（`.cursor/rules/` → `.qoder/rules/` → `AGENTS.md` → `CLAUDE.md`；都没有就明说"本仓无成文工程约束"）。定位方法见 `references/project-index.md` |
| `api/**/*.proto` | 该项目的契约事实源（openapi / 类型定义 / schema），以代码为准 |
| `go test ./api/...` + `contract_diff.sh` | 该仓库自己的接口测试入口与 `verify`；没有就写 `UNVERIFIED`，不许假装跑过 |
| `internal/biz/status.go` 状态族 | `business-model.md` 维度 2：先定族，再找该族的权威 const/枚举位置 |
| 九项负债 | **不套用**。用 `references/scope.md` 的分级与 `references/business-model.md` 的九维度；L3 仍走 `change`（形状写进 `decision.md`） |
| Go 风格与复用门禁 | 该项目成文的工程约束；没有就不加自造规则 |
| `make api` / `make api-one` | 该项目构建入口（Makefile / package.json / 任务运行器）里真实存在的那条命令 |
| 上表 G1–G5 命令 | 该仓库的 `verify` / test / build 入口；没有就 `UNVERIFIED` |
| `feature/26.10.1.0/...` 四位版本分支 | 该仓库自己的分支与 MR 约定；不发明 data-service 版本方案 |

## 迁移欠账

这三条不影响使用，但让"profile 生效"仍然靠文字而不是机制：

1. **九项负债正文还没搬进 profile**：`stages/requirement-analysis/SKILL.md` 与 `references/debt-gate.md` 仍是通用路径，只在顶部加了守卫。搬会改链接与语义，等有真实 Go 仓库能回归时做。
2. **`stack` 只提示、不阻塞**：`start feature|bugfix|hotfix` 未声明 `stack: go` 时只打印一行提示。硬阻塞会破坏既有用例与其他仓库的既有运行。
3. **`reuse-gate` / `go-style` 的路径没有从阶段文件里摘掉**：它们只在 `stack=go` 时有意义，现在靠守卫句提醒。
4. **阶段正文里仍有 Go 路径举例**（如 `internal/service`）：phase 3 再收口；本 profile 已是 G1–G5 与分支节奏的唯一命令/取值源。
