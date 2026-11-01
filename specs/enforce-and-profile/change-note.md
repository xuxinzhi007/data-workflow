# 放行签发 / 命令门 / profile 变更说明（change note）

- feature：`enforce-and-profile` ／ 分支：`main` ／ commit 范围：工作树，提交后回填
- 日期：2026-11-01

## 1 一句话

把「放行」从写一行字改成要一次已答复的拍板，给门加了一条跑命令的能力，并把 Go 实例取值收进 profile、把 description 从 1328 字压到 179 字。

## 2 为什么

上一轮 `check.md` §5 自己列的两条债（放行自授权、门只识字面量）加一条常驻上下文成本。证据在 `specs/enforce-and-profile/decision.md` §现状。

## 3 改了什么

| 层 | 文件 | 变更 |
|---|---|---|
| 放行签发 | `scripts/workflow_next.py`（`approve`、`answer` 保留 `last_reply`）、`hooks/gate_edit.py`（`read_passes` 带 `approved`、`gate_strict` 下过滤） | 放行行只由 `approve` 写；手写的行在严格模式不作数 |
| 命令门 | `workflow_next.py`（`run_gate_check`）、`workflows/change.json` stage 2 | `gate_check` 跑一条命令，非 0 就停；`change` 编码阶段检查工作树真的动过 |
| profile | `profiles/go-kratos/profile.md`（新增）、`stages/{requirement-analysis,impact-assessment,change-review}/SKILL.md`、`templates/plan-template.md` | Go/Kratos 实例取值集中声明 + 四个文件加守卫句 |
| 常驻上下文 | `SKILL.md` frontmatter | description 1328 → 179 字，触发词一个没删 |
| 文档 | `references/{edit-gate,commands}.md`、`workflows/change.md`、`stages/tech-design/SKILL.md`、`config.example.yaml`、`README.md` | 与新行为对齐 |

## 4 契约影响

不适用：本仓无对外 API。CLI 只新增 `approve` 子命令与 `gate_check` 字段；`design`/`waiver` 的覆盖语义未变。

## 5 验证记录

| 门 | 命令 | 结果 |
|---|---|---|
| 回归 | `bash scripts/verify.sh` | PASS ×56，`OK` |
| 运行记录 | `specs/enforce-and-profile/verify.log` | `exit 0` |
| 放行签发 | `case_approve` | 无拍板 → `NEED_ANSWER`；手写行被忽略；`approve` 后放行 |
| 命令门 | `case_gate_check` | 干净工作树 → `GATE`；有改动 → 过门并跑 verify |

## 6 文档审计（提交前门）

| 文档 | 是否需要同步 | 状态 | 备注 |
|---|---|---|---|
| `specs/enforce-and-profile/{decision,check}.md` | 是 | 已同步 | `check.md` 含行为变化与迁移说明 |
| `README.md` | 是 | 已同步 | 结构树加 `profiles/` |
| `config.example.yaml` | 是 | 已同步 | `gate_strict` 说明补「只认 approve 写的行」 |
| `CONTEXT.md` / `GLOSSARY.md` | 不需要 | 不适用 | 本仓没有 |
| 九步链产物 | 不需要 | 不适用 | L1（`change` 三步） |

接受的文档风险：无。

## 7 仍然欠着的

`gate_check` 只接了 `change` 一处；`stack` 只提示不阻塞；九项负债正文未搬进 profile；语义门；真实业务仓库演练。逐条见 `check.md` §5。
