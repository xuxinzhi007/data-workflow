# evidence-anchor 决定

> 规则在 `references/scope.md`。级别 L1：改 runner 与 SKILL.md 的一张表，不碰业务契约。

- 级别：L1
- 原话（一字不改）：按这次总结进行实现 批1 和 批2
- 本质：给运行记录补一个 commit 锚点（让"下一步"知道代码变过），让 `next` 顺带带出最近一次拍板；把 SKILL.md 里与 `next` 重复的那张阶段表删掉，只留不经工作流的四个入口。
- 怎样算满足：`done` 成功后 `specs/<f>/evidence.log` 多一行含 `stage/门/退出码/head/by=runner`；HEAD 变化后 `next` 打一行 `NOTE`（不阻塞）；有拍板时 `next` 打 `DECIDED`；`SKILL.md` 里不再有阶段→文件映射；`bash scripts/verify.sh` exit 0。
- 未知：无
- 这次不做：hook 读 `evidence.log`（会让一个稳定组件依赖新状态，收益不抵风险）、把域文档同步写进核对门（没有真实 `docs/domain` 时永远是"不需要"，见上轮评估）、按天数静音 NOTICE。

## 真正要解决的问题

上一轮评估里定下的批 1 + 批 2，两个真坑：

1. **运行记录不知道自己对应哪次代码。** `run.json` 只有 status/stage。工作树变了、`HEAD` 变了，`next` 照样说"继续第 2 步"。而 `subagent-protocol.md` 要求 review 产物写 base/head 指纹——指纹无处落盘，只能人手抄。
2. **同一事实三份描述会漂。** 「阶段 → 读哪个文件」现在有三份：`SKILL.md` 的表、`workflows/*.json` 的 `file`、`next` 打印的 `READ`。`next` 已经是权威，另外两份是纯重复。

## 现状（带证据）

| # | 事实 | 证据 |
|---|---|---|
| 1 | `run.json` 无 commit 字段 | `cmd_start()` 构造的 dict；`specs/*/run.json` |
| 2 | review 指纹无处落盘 | `subagent-protocol.md` §2/§3 要求写指纹；`artifact-tree.md` 无对应工件 |
| 3 | 拍板记录写进了产物（`已拍板：`），但 `next` 不显示 | `close_decisions()` 追加；`print_context()` 无该字段 |
| 4 | SKILL.md 的阶段表与 `next` 的 `READ` 重复 | `SKILL.md` §选型表 10 行；`workflow_next.py` 的 `stage.get("file")` |

## 现有能力（复用）

- `close_decisions()` 已经写 `已拍板：`，只需读回来。
- `print_context()` 是唯一展示层，`next` / `WAIT` / `DONE` 都走它，加两行即可全局生效。
- `advance()` 是唯一的"推进"点（`show` 与 `cmd_done` 共用），证据行挂在那里只有一处。
- `read_text()` / `glob` 已有。

## 最小充分方案

1. `run_verify()` 返回退出码（0 通过、非 0 失败、-1 未配置），让证据行能写真话。
2. `record_evidence()`：`advance()` 成功后追加一行到 `specs/<f>/evidence.log`：
   `stage=<id> requires=ok gate_check=ok|none verify=exit0|none head=<short sha> at=<iso> by=runner`。
3. `print_context()` 加两行派生输出：`DECIDED <最近一条 已拍板>`、`NOTE 工作树已变（记录 X → 现在 Y）`。
4. `SKILL.md`：删 10 行阶段表，保留四个非工作流入口（业务梳理/排查/提交/画图）+ 一句"其余由 `next` 的 `READ` 决定"；同步改上面两处提到"选型表"的句子；`README.md` 两处引用跟着改。

## 为什么更小的做法不够

只加 `head` 不加 `DECIDED`：新会话继续一条运行时，仍不知道上一轮拍了什么（`已拍板` 在产物里，但没人读）。
只删表不改 `next`：`next` 本来就会打 `READ`，删表本身是安全的；但若不同时把"用户点名阶段"的路径写清（先 `start`），删表会让"帮我写技术方案"没有落点。

## 相关的债

- A 现在偿还：上一轮评估的批 1、批 2。
- 不动：域文档同步门（缓）、时间静音（不做）、`evidence.log` 让 hook 读（不做）。
- 新引入的债：`evidence.log` 的写权限只靠约定（行尾 `by=runner` 是标记，不是强制）。写进 `check.md`。

## 这次不做

- 不新增 hook 依赖，不改 `gate_edit`。
- 不改 `run.json` 的字段（`head` 落在证据行里，不进 `run.json`，避免两处真相）。
- 不动 `evals.json` 之外的测试资产。

## 风险

不碰契约、持久化、权限、状态、回滚。行为变化三处：`next`/`DONE` 输出多两行（`DECIDED`/`NOTE`）；`done` 多写一个文件；`SKILL.md` 少一张表。`NOTE` 不阻塞，只是提示。
