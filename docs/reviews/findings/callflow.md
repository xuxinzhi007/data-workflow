# 调用轴走查

只看「为了可测而抽出来的纯函数，真实 bug 是不是藏在怎么被调用上」和「哪两个紧耦合的 module 从一个 seam 的两侧漏到对方」。结构上的副本（配置文件列表、终态集合）已在 structure.md 写过，这里只写调用路径上仍然成立的行为。

每条都做了 deletion test。只有「是的，会集中」才留下当候选。

核对方式：读源码，并在临时仓库实跑（2026-11-12，Asia/Shanghai）。

---

## C1 `next` / `show` 会推进并写记录，却被钩子当成只读查询

**怎么被调用：**

- `hooks/session-start` 在每个新会话里调用 `workflow_next.py next --repo …`，用输出拼一条 NOTICE。注释写：发现未完成运行，不要把它变成当前这句话的任务；NEED / WAIT / DO / OPEN 只在用户继续那条运行时再看。
- `check_runner.py` 文件头与 `case_hook_quiet` 的约定是：钩子注入 NOTICE，**不改 `run.json`**。
- `workflow_next.py:cmd_close` 的注释写：`next` 必须是只读的（钩子、C3 实验、`case_no_hints_switch` 都依赖它不改 `run.json`）。

**实际调用：** `cmd_next` 走到 `show()`。`show()` 在产物已齐、`stage_gates_block` 未拦住、且该阶段不是 `code`、也不是「无产物」时，会 `advance`、`record_evidence`、`save_run`（`workflow_next.py:show` 中自动推进的那段）。它是一个 `while` 循环，能连续跨过多个已齐的文档阶段。

实跑：

- `start change demo` 后把六行字面量写进 `decision.md`，再跑 `next`：`run.json` 的 stage 从 1 变成 2，并追加了 `evidence.log`（`stage=1 … by=runner`）。
- `start architecture-review` 后只写 `scope.md` 再跑 `next`：stage 从 1 变成 2（该阶段没有 `requires`，文件非空即过）。

`case_hook_quiet` 只在「产物还缺、`next` 打 NEED」时断言 hook 不改记录——那条路径本来就不会推进。产物写齐后再开会话的路径没有用例。

**缺 locality：** 「现在停在哪」和「把阶段向前推一格」走同一条调用路径。为了让 `next` 可测、可给钩子复用，查询被接在了会写盘的 `show()` 上。真实问题不在「有没有 `show` 这个函数」，而在钩子怎么调用它。

**Deletion test：** 删掉 `show()` 里这段自动推进，查询与推进的复杂度不会消失，而会回到「写完决策之后人们还要记得另调一次推进」——它在挣饭钱。但若把「只读查询」和「推进」收成同一个 module 里两条互不泄漏的路径，钩子、C3、裸 `next` 共用只读那条，复杂度集中，也不再静默写盘。**是的，会集中。** 候选。

---

## C2 G7 只挂在 `done` 上，`next` 的自动推进会绕过去

`workflow_next.py:knowledge_feedback` 是抽出来可单测的纯判定。`case_g7_gate_runs` 也只**直接 import 这个函数**来测：命中域文档且 `verified_commit` 没跟上会拦。函数本身成立。

**怎么被调用：**

- `cmd_done` 在 `stage_gates_block` 之后、`run_verify` 之前，若 `stage.get("knowledge_feedback")` 为真，才跑 G7（`workflow_next.py:cmd_done`）。
- `show()` / `next` **没有**这条调用。feature 第 6 步「质量与接口门」在 `feature.json` 里标记了 `knowledge_feedback: true`，它不是 `code` 阶段，产物是非空的 `quality.md`，也没有 `requires` / `gate_check`。
- 上一阶段缺产物时，runner 打印的是「写完后运行 `next`」，不是 `done`。于是按它自己的提示写完 `quality.md` 再 `next`，会走自动推进。

实跑：把一条 feature 运行的 `run.json` 置于 stage=6，写入 `quality.md`，跑 `next`：stage 变成 7（要 `change-note.md`），G7 一行都没有出现。

这正是词表里说的那种摩擦：为了可测把判定抽纯，bug 藏在「谁调用、谁没调用」。`stage_gates_block` 已经把 OPEN / requires / `gate_check` 收拢到 `show` 与 `done` 共用；G7 还留在 `done` 一侧。两个入口对同一阶段再次给出不同结论——和已经修过的「`next` 说 DO、`done` 说 GATE」是同一类调用分叉，只是换了一道门。

**Deletion test：** 删掉 `knowledge_feedback` 这个函数，G7 不会变简单，只会回到无判定。把它收进与 `stage_gates_block` 同一条「阶段能不能离开」的路径，调用方不再各自决定跑不跑。**是的，会集中。** 与 C1 是同一条加深方向上的第二处泄漏，合并为一个候选。

---

## C3 写入放行在 seam 的另一侧硬要了 feature 的 plan / gate

`workflow_next.py:cmd_approve` 只要求：有运行、有过一次 `answer`（`last_reply` 非空），然后往 `specs/passes.log` 追加带 `approved` 的 design / waiver 行。它不看 `plan.md`，也不看 `gate`。

`gate_edit.py:decision` 在受保护路径上，除了这行放行记录，还要 `gate_edit.py:design_ok` 为真：`specs/<feature>/plan.md` 非空，且 `specs/<feature>/gate` 首条非空行是 `plan pass`。这两份产物是 `feature.json` 第 3 步才有的；默认工作流 `change.json` 只产 `decision.md` / 代码 / `check.md`。

两个 module 夹着 `passes.log` 这条 seam：一侧签发「已经拍板、可以写」，另一侧仍按 feature 的方案门形状解释同一条记录。

实跑（change 运行，`protected_paths: "api/**"`，`gate_strict: "true"`，完整 wait → answer → approve）：

- `approve` 打印 `APPROVED`，`passes.log` 已有 `approved` 行
- `design_ok` 仍为 False，`decision("api/x.proto")` 为 deny，理由要求 plan.md 与 gate
- 手工补上这两份 feature 产物之后，同一条放行行变为 allow

`case_approve` 测的也是 change 工作流，但测试自己先写入了 `plan.md` 和 `gate`——把泄漏当成了前置，所以绿灯拦不住。

**Deletion test：** 删掉 `design_ok`，受保护路径的「方案已过门」会散回调用方或直接消失（只认 passes.log）。它在 feature 链上挣饭钱。加深方向是：放行判定按这次运行的工作流来看该有的产物，而不是所有 execute 运行都漏进 feature 的 plan/gate。**是的，会集中。** 候选（强度：Worth exploring——只在配置了 `protected_paths` 且走 change 时发作）。

---

## C4 `run_gate_check` 的极性 seam：已修，不再当现行问题

`cmd_close` 把 `close_if.fingerprint` 包成一个只有 `gate_check` 字段的 stage，再调用 `run_gate_check`。`ok` 在门禁里是「命令成功则放行」，在指纹里是「命令成功则 bug 还在」。源码已在调用点取反，变量改名为 `reproduces`，两端用例都在。

这条 seam 仍然薄（复用时要靠调用方记住取反），但现行行为是对的，本轴不把它写成待加深的现行候选。若再有第三处复用 `run_gate_check` 来表达相反极性，应先回到这条教训，而不是再开一个浅包装。

---

## C5 配置查找在调用点分叉（与结构轴 S1 同一事实的调用面）

`gate_edit.py:policy` 与 `gate_edit.py:strict` 对同一仓库、同一批 config 文件给出不同优先级和不同候选集。结构轴写了副本本身；调用面上的后果是：只把 `gate_strict` 写在 `.qoder`（或其它非 `.cursor` 的工具目录）里时，路径保护会生效、严格模式不会。不另开候选，并入 S1 的加深。

---

## 本轴不作为候选的

- 字面量门 `unmet_requires` 本身很浅，诚实成本在 confess 设计里已经单独开了通道；那是产品取舍，不是「抽纯函数后调用错了」。
- `print_stage_hints` 已覆盖当前主要提示字段；主泄漏已修。
- fingerprint 极性、`stage_gates_block` 抽出：已修，有回归。
