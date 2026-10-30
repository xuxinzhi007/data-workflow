# pluggable-skill-pack 核对（如实修订版）

> 初版把验收第 3 条改写成「标注为 Go 栈」，掩盖了「技能源不再有 data-service 默认硬编码」这一验收未达成；diff 范围「16 文件 / 109 行」不含暂存的 4 份 `specs/` 记录；遗留不全（漏了 docs/、scope.md、接口测试 Go 命令）。复核指出后，本文件按下述真实状态重写。修复运行见 `specs/pluggable-skill-pack-fix/check.md`。

## verify.log

`exit 0`（`check_runner.py` 全部 PASS，末尾 OK）。

## 验收逐条（真实状态）

1. **装进任意非 Go 项目可用 → 已达成**：临时 JS 项目实测 `install.sh` 成功；默认门禁不拦 `api/foo.proto`、`internal/x.go`、`src/app.ts`；声明 `protected_paths: "*.proto"` 后 `api/foo.proto` 被拦；change 工作流可用。
2. **data-service 降为普通配置实例 → 部分达成**：`gate-edit` 默认无受保护路径、`routing.md` 通用段、`project-index.md` 通用骨架已改。未达成：`stack` 只出现在注释与文字标注，未接到执行（未声明 Go 的仓库走进 feature 仍按 Go 门做）；`feature.json` 存在无效路径 `go-style.md（Go 栈）`；`scope.md` L3 与 `SKILL.md` 选型矛盾；config 无 `domains` 键。→ 已由 `pluggable-skill-pack-fix` 修复。
3. **技能源不再有 data-service 默认硬编码 → 未达成**：`docs/external-skill-packs.md`、`scope.md`、`interface-test` 的 Go 命令仍绑定。scope 与接口测试已由 fix 运行修正；docs/ 未改，写进遗留。
4. **叙述层去 data-service 化 → 已达成**：`SKILL.md`、`README.md`、`config.example.yaml`、`evals/evals.json`、`workflows.md`、`dw-start.md`、`change.md`、`change.json` 已改为「任意仓库用 change，data-service 作示例实例」。
5. **check_runner.py 全 PASS → 通过**：verify.log 末尾 OK。

## diff 范围（如实）

第一轮正文改动 16 个文件（暂存 M），另有 4 份 `specs/pluggable-skill-pack/` 记录（暂存 A）。git status 合计 16 M + 4 A = 20 项。初版「16 文件 / 109 行」只计正文、漏计 specs 记录，属规模漏计。修复轮（`pluggable-skill-pack-fix`）另改了 9 个技能源文件 + 新增运行记录 + data-service 副本 `config.yaml`，见修复运行 check。

## 遗留（初版漏记，此处补全）

- `docs/` 下 `external-skill-packs.md` 等仍以 data-service 为主要叙述对象，仅定位为实例说明，未逐句通用化。
- feature 九步链保留为 Go 栈（data-service）模板，未做多技术栈模板化——本次「解耦 + data-service 降为实例」的范围；为其他技术栈提供完整九步模板属后续扩展。
