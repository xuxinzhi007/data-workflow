# pluggable-skill-pack-fix 决定

> 落 `specs/pluggable-skill-pack-fix/decision.md`。这是 `pluggable-skill-pack` 改造的修复运行：上次 change 虽 `DONE`，但验收有 6 处未达成，由复核指出。规则在 `references/scope.md`。

- 级别：L3（碰写入门禁、feature 链、契约门）。作用对象是技能源仓库自身 + data-service 实例的 `config.yaml`，不改任何业务代码，风险可控，仍走 `change`。
- 真正要解决的问题：`pluggable-skill-pack` 的「可拔插做完」验收未达成，复核指出 6 处：① `stack` 没接到执行上，Go 门不跟随 `config.yaml` 的 `stack` 生效；② `feature.json` 里 `go-style.md（Go 栈）` 是无效路径；③ `scope.md` 与 `SKILL.md` 选型入口互相矛盾（非 Go 仓库 L3 变更两份文件给的流程不一致）；④ 决定里的「config 域清单」没有配置键；⑤ `check.md` 把未完成的项写成了完成，规模数据不含暂存的 4 份 `specs/` 记录；⑥ 装上这版后 data-service 仓库的门禁（api/proto/status.go）将失效——该仓库无 `config.yaml`。
- 怎样算满足：
  1. `stack: go` 真正接到执行：`workflow_next.py` 在 `start feature|bugfix|hotfix` 时读 `stack` 键，非 go 栈明确提示「Go 门不适用，建议 change」；`feature.json`、`interface-test/SKILL.md`、`hotfix.json`、`plan-template.md` 里的 Go 门标注「仅当 stack=go」。
  2. 技能源里不再有 `go-style.md（Go 栈）` 这类无效路径。
  3. `scope.md` L3 表与 `SKILL.md` 选型一致：data-service（Go 栈）实例的 L3 走 `feature`/`hotfix`；未声明 Go 栈的项目 L3 / 定架构走 `change`。
  4. `config.yaml` 新增 `domains` 键，`routing.md` 读它；data-service 域作为默认示例。
  5. `check.md` 如实核对：验收逐条给证据，未达成项写进遗留，规模含暂存区全部（含 `specs/pluggable-skill-pack*`）。
  6. data-service 仓库补写 `config.yaml`（`protected_paths` / `waiver_globs`），恢复其门禁；若用户不愿改该仓库，此项记为阻塞并 `wait`。
- 现有能力（已证实）：上次改造已建立——`hooks/gate-edit` 默认无受保护路径、`protected_paths` 声明后拦截；`routing.md` 通用段 + data-service 示例；`project-index.md` 通用骨架；`SKILL.md` 选型表标注 feature 为 Go 栈；`change` 三步通用工作流。
- 旧决定：`pluggable-skill-pack` 的 `decision.md` / `check.md`。实现是否仍符合：6 处不符合验收（见上），需修复。
- 最小充分方案：上列 6 条逐项修。
- 为什么更小的做法不够：任一条不修，「可拔插」就不成立（stack 空转、选型矛盾、门禁失效），或验收记录造假（check 虚报）。
- 相关的债：B 局部偿还。无关的历史债写在不做里。
- 这次不做：不新建多技术栈的完整九步模板（`feature` 仍是 Go 栈模板）；不改 data-service 的任何业务代码（只补写它的 `config.yaml`）；不重做 Matt / Addy / Superpowers 集成。
- 风险：作用于技能源仓库自身 + data-service 实例新增一个 `config.yaml`（低风险，可回滚）。通过 `check_runner.py` + 实测 data-service 门禁恢复验证。
