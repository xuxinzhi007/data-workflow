# pluggable-skill-pack-fix 核对

对照 `decision.md` 的 6 条验收逐条核对，均给证据。全部改动先经 `check_runner.py` 全 PASS（verify.log exit 0），再做针对性实测。

## verify.log

`exit 0`（`python3 skills/data-workflow/scripts/check_runner.py` 全部 PASS，末尾 OK）。修改过的 5 份 workflow JSON 均通过 `json.load` 校验。

## 验收逐条

1. **`stack` 接到执行 → 已达成**。`scripts/workflow_next.py` 的 `cmd_start` 在读 config 的 `stack` 键：`start feature|bugfix|hotfix` 且非 go 栈时打印 `STACK 项目未声明 stack=go……建议 start change`。实测临时 JS 项目 `start feature demo` 输出该 STACK 行并继续 `NEED specs/demo/spec.md`。Go 门标注（仅当 stack=go）：`feature.json` 编码 gate、`interface-test/SKILL.md` 顶部、`hotfix.json` gate、`plan-template.md` §6、`feature.json` 的 `api/**/*_contract_test.go` artifact。
2. **无效路径修复 → 已达成**。`feature.json` 的 `go-style.md（Go 栈）` 改为纯路径 `go-style.md`，条件说明移到 gate（仅当 stack=go）。grep 确认技能源不再有 `go-style.md（Go 栈）` 这类括号留路径。
3. **`scope.md` 与 `SKILL.md` 选型一致 → 已达成**。`scope.md` L3 表改为「data-service（Go 栈）实例走 feature/hotfix；未声明 Go 栈的项目 L3 / 定架构走 change（decision.md 定形状）」。grep 确认 scope.md 其余无 feature/hotfix 默认绑定。与 SKILL.md「任意仓库用 change」一致。
4. **域清单配置项 → 已达成**。`config.example.yaml` 新增注释掉的 `domains` 键（示例 = data-service 12 域）；`routing.md` 通用表「具体业务域」行改为「从 config.yaml 的 domains 键，或 $KNOW 下的域目录 / 索引发现」。配置键与读取点都落位，与「这次不做自动发现」并存（留空时回落 $KNOW 目录）。
5. **`check.md` 如实 → 已达成**。旧 `specs/pluggable-skill-pack/check.md` 初版虚报已重写为如实版本（验收第 3 条改回「未达成」并补 docs/、scope.md、接口测试 Go 命令进遗留，规模改为 16 M + 4 A = 20 项）。本文件（fix 运行）亦逐条给证据。
6. **data-service 门禁恢复 → 已达成**。data-service 副本 `config.yaml`（`.cursor/`，`.agents`/`.qoder` 软链到它）补写 `stack: "go"`、`protected_paths: "api/**,*.proto,*.pb.go,internal/biz/status.go,*/biz/status.go"`、`waiver_globs: "*.go"`。实测副本 `gate-edit` 对 `api/foo.proto` 返回 `deny`。

## diff 范围（如实，含暂存区全部）

技能源仓库 `git status --short`：4 A（`specs/pluggable-skill-pack/`）+ 19 M + 3 MM + 1 未跟踪目录（`specs/pluggable-skill-pack-fix/`，含 decision/run.json/verify.log/check.md）。修复轮本次改动：`workflow_next.py`、`feature.json`、`interface-test/SKILL.md`、`hotfix.json`、`bugfix.json`、`plan-template.md`、`scope.md`、`routing.md`、`config.example.yaml` + `specs/pluggable-skill-pack-fix/` 记录 + 修订旧 `pluggable-skill-pack/check.md`。另 data-service 副本 `config.yaml` 属另一仓库，计 1 项。

## 验证方式与结果

- `check_runner.py` 全 PASS（含「defaults to no write gate until protected_paths declared」「activates on declared protected_paths」）。
- 实测：非 Go 项目 `start feature` 输出 STACK 提示；data-service 副本对 `api/foo.proto` deny。
- 5 份 workflow JSON 合法。

## 遗留

- `docs/` 下 `external-skill-packs.md` 仍以 data-service 为主要叙述对象，仅定位为实例说明，未逐句通用化（范围内，属叙述层后续收尾）。
- feature 九步链仍为 Go 栈（data-service）模板，未做多技术栈模板化——本次范围外。
- 技能源全部改动与 data-service 副本 config.yaml 均未 `git commit`（改动在工作区/暂存区；data-service 副本 config 未进 data-service 的 git）。
