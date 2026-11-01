# evidence-gates 决定

> 规则在 `references/scope.md`。级别 L1：改技能自己的 runner、模板与文档，不碰业务契约。

- 级别：L1
- 原话（一字不改）：接着走完下一步流程吧 ，我需要看到现在这个项目的价值 对比现在网上比较好的skill 进行实现 进行竞品的分析对比
- 本质：把 P1 四条落进仓库——让「门」从文件名门变成内容门，让用户原话进运行记录，修掉知识源空值会误扫根目录的写法，并把 `domains` 这个只写在文档里的配置键接上实现。
- 验收：`bash scripts/verify.sh` exit 0，且新增用例证明「缺 `未知` 行时 `next` 打 `GATE` 并停」「`start` 存下原话」「`paths.sh` 输出 `DOMAINS`」。
- 未知：无（P1 四条在上一轮 check.md 里已经列明，用户已授权继续）
- 这次不做：`passes.log` 只脚本可写（属 D1 的策略选择，audit 模式下绑拍板没有收益，见下）、`gate_check` 可执行 shell 门（需要按仓库给的命令，属 P2 profiles）、`stack` 硬阻塞、业务分析骨架与知识落点（P2）。

## 真正要解决的问题

上一轮把门禁修好了，但**门仍然只看文件名**：`decision.md` 只有「决定」两个字也能过，`next` 照样推进。同时用户原话没进运行记录——下一轮会话（或另一个 agent）无法判断「本质」是不是过度解读。加上 `routing.md` 里 `grep -rl "…" $CARDS/` 在知识源为空时会从文件系统根开始扫，`domains` 键只有文档提到、没有读取方。

## 怎样算满足

1. `start change <f> "<原话>"` 把原话写进 `run.json.raw_request`，`next` 打印 `RAW`。
2. `decision.md` 缺 `原话` / `本质` / `未知` 任一行 → `next` 与 `done` 都打印 `GATE` 并停在这一步。
3. `check.md` 缺 `exit` 行 → 同上。
4. `paths.sh` 输出 `DOMAINS='a,b'`；`routing.md` 的 step 1 用它发现域，不再只写「从 config.yaml 的 domains 键」。
5. `routing.md` step 0 在 `$CARDS` 为空时明确跳过，不再出现未加引号的空变量。

## 现状（带证据）

| # | 事实 | 证据 |
|---|---|---|
| 1 | `next`/`done` 只查文件存在且非空 | `workflow_next.py` 的 `satisfied()`；上一轮 `check.md` §5 第一条 |
| 2 | `run.json` 只有 5 个字段，没有原话 | `cmd_start()` 构造的 dict；`specs/*/run.json` |
| 3 | 文档自己要求 check.md 先写 exit 行，但没有校验 | `workflows/change.md` 第 3 步 |
| 4 | `routing.md:8` 空 `$CARDS` → `grep -rl … /` | 该行代码；`paths.sh` 空值只打 stderr |
| 5 | `domains` 无读取方 | 全仓 grep：只在 `config.example.yaml`、`routing.md`、`capture.md` 的文字里出现 |

## 现有能力（复用）

- `concrete_files()` / `read_text()`：已存在，直接用来读产物内容。
- `paths.sh` 的 `emit` 函数：加一行就能输出 `DOMAINS`。
- `check_runner` 的 `expect()` / `run()`：新用例沿用。

## 最小充分方案

1. `workflows/*.json` 的 stage 加 `requires`（字面量清单），runner 在推进前检查产物里是否都出现。
2. `start` 接受第 4 个参数写进 `raw_request`；`print_context` 打印 `RAW`。
3. 模板与 `workflows/change.md` 写清 5 行受理单。
4. `routing.md` 的 step 0 加空值守卫；step 1 用 `$DOMAINS`。
5. `paths.sh` 加 `emit DOMAINS domains`。

## 为什么更小的做法不够

只写进模板不动 runner，等于又一条「文档说了但没人校验」的债——正是上一轮 §5 列的那一类。只加 runner 校验不改模板，会让每次 `start` 立刻卡在 `GATE` 上。

## 相关的债

- A 现在偿还：门是文件名门（上一轮 check.md §5 第 2 条）。只还「内容门」这一半；`gate_check` 的 shell 门留到 P2，因为它的命令必须按仓库给，没有通用值。
- C 暂缓：`passes.log` 自授权。审计模式（D1）下把放行行绑到一次拍板回话只增加摩擦，不增加约束力。等真要 enforce 时一起做。
- 无关不动：`stack` 阻塞、`contract_diff.sh` 的 python3、`shell_destinations()` 盲区。

## 这次不做

- 不新增工作流、不改 stage 顺序、不动 hook 的放行语义。
- 不改 `evals.json`。
- 不动 `SKILL.md` 的 description 长度（P2）。

## 风险

不碰契约、持久化、权限、状态、回滚。行为变化两处：**已有运行记录**如果没有 `raw_request`，`next` 不会因此停（只在新 `start` 时要求）；**旧 `decision.md`** 缺 5 行会在升级后立刻 `GATE`——这是本意，但要在 `check.md` 里写清怎么补。
