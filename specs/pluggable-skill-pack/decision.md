# pluggable-skill-pack 决定

> 落 `specs/pluggable-skill-pack/decision.md`。规则在 `references/scope.md`。
> 这是技能源仓库自身的一次架构级改造，按 SKILL.md「任意仓库定架构走 change」执行，不套 data-service 九步。

- 级别：L3（碰写入门禁=权限机制、feature 链、契约门）。但作用对象是**技能源仓库自身**，不是 data-service 线上代码，风险边界可控，仍走 `change`。
- 真正要解决的问题：data-workflow 当前默认深度绑定 data-service（写入门禁默认只拦 Go/proto、业务梳理域路由表写死 data-service 业务域、项目索引是 data-service 专属、feature 链是 Go/proto 专用、叙述层只讲 data-service）。装进其他项目即失效，达不到「可拔插技能包、管理业务、提升任意被引用项目质量」的目标。
- 怎样算满足：
  1. 装进任意非 Go/data-service 项目后：`install.sh` 可用；写入门禁不默认误拦 Go/proto；业务梳理能从该项目知识层读域；质量门用该项目声明的测试入口。
  2. data-service 的全部专有内容（门禁路径、域表、项目索引、Go 栈门、分支规范、评测）降为通过 `config.yaml` 注入的普通实例。
  3. `check_runner.py` 全部 PASS；`install.sh` 在任意项目复制成功；技能源 grep 无 data-service 默认硬编码。
  4. 叙述层（`SKILL.md` / `README.md` / `docs` / `config.example.yaml`）不再默认讲 data-service，data-service 作为示例实例。
- 现有能力（都是可复用的钩子，已证实）：
  - `config.yaml` 支持 `protected_paths` / `waiver_globs` 覆盖默认门禁（`references/edit-gate.md`）—— 已证实
  - `scripts/resolve.sh` / `paths.sh` 配置化知识源路径 —— 已证实
  - `scripts/layout.py` 产物落点分流（本仓库 vs `runs/<仓库名>/`）—— 已证实
  - `scripts/workflow_next.py` 通用测试入口发现（package.json / Makefile / pytest / cargo）—— 已证实
  - `workflows/change.json` 已是通用工作流 —— 已证实
- 旧决定：无（本仓库此前无此改造决定）。实现是否仍符合：不适用。
- 最小充分方案（核心解耦，一次做完）：
  1. `hooks/gate-edit`：去掉硬编码默认（`api/`、`*.proto`、`*.pb.go`、`internal/biz/status.go`、`*.go`）。默认保护路径为空（通用，不拦）；data-service 的门禁路径由 data-service 实例的 `config.yaml` 注入。
  2. `stages/oncall/references/routing.md`：域路由表从写死的 data-service 域，改为「从 `$KNOW` 读域索引 / config 域清单」+ data-service 域作为示例。
  3. `references/project-index.md`：改为通用索引骨架，data-service 作为示例实例段落。
  4. `workflows/feature.json` 及关联 stage（quality-gate / interface-test / implementation / requirement-analysis / git-commit）：Go/proto 专属门（`go-style.md`、`contract_diff.sh`、`go test ./api/...`、`api/**/*_contract_test.go`、`go build`/`gofmt`/`test-unit.sh`、`feature/26.10.1.0/x` 分支规范）抽成「go 栈」配置（`config.yaml` 增 `stack: go`），data-service 实例用 go 栈；默认通用项目不强制这些。
  5. 叙述层：`SKILL.md`、`README.md`、`config.example.yaml`、`docs/` 去 data-service 默认化，data-service 作示例实例。
  6. `evals/evals.json`：同步评测，去掉「默认拦 Go/proto」这类绑定题，补「通用项目接入」题。
- 为什么更小的做法不够：只改 hook 默认或只改域表，其余绑定（feature 链 Go 门、project-index、叙述层、评测）仍会让别的项目读不懂、被误拦，达不到「可拔插」。
- 相关的债：B 局部偿还——保留 data-service 实例配置与示例，不重写其业务逻辑；历史债写在不做里。
- 这次不做：
  - 不新增独立的多项目质量盯盘框架（用户定位为「技能包」，解耦 + 通用即满足）。
  - 不重做 Matt / Addy / Superpowers 集成。
  - 不改 data-service 仓库本身的任何业务代码。
  - 不把 oncall 域路由做成完全无配置的自动发现（保留 data-service 示例 + config 域清单兜底）。
- 风险：碰写入门禁、feature 链、契约门（L3 触发条件），但作用于技能源仓库自身，不改线上业务；通过 `check_runner.py` + `install.sh` + 一个非 Go 仓库实测验证。
