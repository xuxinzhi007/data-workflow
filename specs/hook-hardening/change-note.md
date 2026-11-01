# 门禁与内容门 变更说明（change note）

> 覆盖两次运行：`hook-hardening`（P0）与 `evidence-gates`（P1）。两者改同一批文件，因此同一个提交。
> 形状按 `references/doc-shape.md`：第一屏是一句话 + 文档同步了没有。

- feature：`hook-hardening` + `evidence-gates` ／ 分支：`main` ／ commit 范围：工作树，提交后回填
- 日期：2026-11-01

## 1 一句话

把门禁从「要么全拦、要么全不拦」改成「只拦写、坏了让路、可转严格」，并让「门」从文件名门变成内容门、让用户原话进运行记录。

## 2 为什么

需求出处：连续两轮用户原话——「hook 拦截感觉也存在一些问题」「对业务的分析好像不是很行」，以及授权继续后的「接着走完下一步流程」。

现有能力不够用的三条证据（都在 `specs/hook-hardening/decision.md` §现状、`specs/evidence-gates/decision.md` §现状里带行号）：

1. hook 靠 `#!/usr/bin/python3` 直接执行，Windows 上解析到 Microsoft Store 占位程序（exit 49）→ 无 stdout → `failClosed: true` 把**所有写入**拒掉，连诊断都做不了。
2. `destinations()` 不看 `tool_name`，把 `read_file` 的 `target_file` 当写入目标 → 一旦配 `protected_paths`，agent 连 `api/**`、`status.go` 都读不了，业务分析直接断。
3. `next`/`done` 只查文件存在且非空 → `decision.md` 写「决定」两个字也能推进；用户原话不落盘，下一轮无法判断「本质」有没有过度解读。

## 3 改了什么

| 层 | 文件 | 变更 |
|---|---|---|
| 门禁入口 | `hooks/gate-edit`（改为 bash 壳）、`hooks/gate-edit.cmd`（新增）、`hooks/gate_edit.py`（新增） | 解释器探测后才执行；找不到就输出合法 JSON 放行 |
| 门禁逻辑 | `hooks/gate_edit.py` | 按 `tool_name` 只拦写；`apply_patch` 从补丁正文抠路径；UTF-8；fail-open + `gate_strict`；不再 `mkdir specs/` |
| 运行器 | `scripts/workflow_next.py` | `requires` 内容门；`raw_request`；`RAW` 输出；去掉 `stage-N.md` 幻影兜底；UTF-8 |
| 解释器 | `scripts/find_python.sh`（新增）、`hooks/session-start`、`scripts/install.sh` | 统一走实跑探测（`py -3` → `python3` → `python` → PATH 里的 `python.exe`） |
| 分发 | `scripts/install.sh` | 去 `rsync` 依赖（无则 tar 管道）；`hooks.json` 写 `bash <cmd>` 且不再 `failClosed: true` |
| 工作流 | `workflows/change.json`、`feature.json`、`hotfix.json`、`review-only.json`、`change.md` | `requires`；`triage.md` / `review/verdict.md` 取代幻影文件 |
| 知识源 | `scripts/paths.sh`、`stages/oncall/references/routing.md` | `$DOMAINS` 接线；`$CARDS` 空值守卫 |
| 测试 | `scripts/check_runner.py`、`scripts/verify.sh`（新增） | `sys.executable` + UTF-8 + `tool_name`；新增 7 条用例；本仓声明 verify 入口 |
| 文档 | `references/edit-gate.md`、`commands.md`、`artifact-tree.md`、`templates/{decision,spec}-template.md`、`config.example.yaml`、`README.md`、`docs/{install,executable-workflows,agent-pain}.md`、`docs/competitive.md`（新增） | 与新行为对齐；补竞品对照 |

## 4 契约影响

不适用：本仓没有 proto / 对外 API。`scripts/*.sh` 的 CLI 向后兼容（`start` 第 4 参可选；`next`/`done`/`answer` 签名不变）。

## 5 验证记录

| 门 | 命令 | 结果 |
|---|---|---|
| 回归 | `bash scripts/verify.sh` | PASS ×49，结束后打印 `OK` |
| P0 验收 | `specs/hook-hardening/verify.log` | `exit 0`，45 条 PASS |
| P1 验收 | `specs/evidence-gates/verify.log` | `exit 0`，49 条 PASS |
| 门禁真实 payload | 临时 git 仓手跑（见 `specs/hook-hardening/check.md` §2） | 读 allow / 写 deny / 坏 JSON 放行 / 未知工具放行 |
| 内容门 | 临时仓 `start change demo "<原话>"` | `RAW` 打印；缺 `未知` 打 `GATE`；补齐后进 `DO` |

## 6 文档审计（提交前门）

| 文档 | 是否需要同步 | 状态 | 备注 |
|---|---|---|---|
| `specs/hook-hardening/{decision,check}.md` | 是 | 已同步 | 含行为变化与仍欠项 |
| `specs/evidence-gates/{decision,check}.md` | 是 | 已同步 | 同上 |
| `README.md` | 是 | 已同步 | 新增 `docs/competitive.md` 指针 |
| `config.example.yaml` | 是 | 已同步 | `gate_strict`、`DATA_WORKFLOW_PYTHON`、`domains` 说明 |
| `docs/install.md`、`docs/executable-workflows.md`、`docs/agent-pain.md` | 是 | 已同步 | 旧的 failClosed / python3 / 幻影工件描述已改 |
| `CONTEXT.md`（术语） | 不需要 | 不适用 | 本仓没有该文件；术语表在 P2 处理 |
| `api/**` 生成物 | 不需要 | 不适用 | 无 proto |
| `spec.md` / `impact.md` / `plan.md` / `rollback.md` / `interface-test.md` | 不需要 | 不适用 | 两次都是 L1（`change` 三步），按 `references/scope.md` 不进九步链 |

接受的文档风险：无。

## 7 仍然欠着的

`passes.log` 自授权、`gate_check` shell 门、语义门、`check_runner.module()` 的 `python3`、`stack` 不阻塞、业务分析骨架与知识落仓库（P2）。逐条理由见两个 `check.md` 的 §5 与 `docs/competitive.md` §3。
