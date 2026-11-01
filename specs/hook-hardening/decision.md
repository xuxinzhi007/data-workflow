# hook-hardening 决定

> 落 `specs/hook-hardening/decision.md`。规则在 `references/scope.md`。
> 级别 L1：改的是技能自己的脚本与 hook，不碰任何业务契约、状态、权限、回滚。

- 级别：L1
- 原话（一字不改）：按这里的方向进行调整吧
- 本质：把 P0 六条落进仓库——让门禁脚本在本机能跑、只拦写、输出可读、坏了自己让路；顺带修掉两个幻影工件。
- 验收：`bash scripts/verify.sh` 退出码 0，且新增的 5 条回归用例各自能证明「读放行 / 写拦截 / 严格模式 / 无 python 放行 / UTF-8 可读 / 无幻影工件」。
- 未知：无（本轮不需要业务口径；用户已按 D1=audit、D2=仓库内优先、D3=decision.md 头部 拍板）
- 这次不做：P1（`gate_check`、`raw_request`、`passes.log` 只脚本可写、`domains` 接线）、P2（`business-model.md`、知识落点三分、profiles 拆分、description 瘦身）。理由见下。

## 真正要解决的问题

现在这套门禁在这台机器上**要么全拦、要么全不拦**，而且 README/AGENTS.md 把它写成"受保护路径不能绕过"。
实测三条：`hooks/session-start` 直接执行 `#!/usr/bin/python3` 的脚本 → 无输出；`.cursor/hooks.json` 里 `failClosed: true` → 无输出即拒绝；`check_runner.py` 用 `[RUNNER, ...]` 直接执行 `.py` → WinError 193。
所以"门禁是否生效"目前无法被验证，改任何后续东西都没底。

## 怎样算满足

1. `python skills/data-workflow/scripts/check_runner.py` 在本机（Windows + git-bash）跑完打印 `OK`。
2. 读 `api/foo.proto`（受保护路径）→ `allow`；写同一个文件 → `deny`。
3. 找不到可用 python 时，hook 输出合法 JSON 且 `permission=allow`（不拦死），`bash hooks/session-start` 仍输出合法 JSON。
4. `next` 打印的中文在 UTF-8 下可读；`hotfix` 第 1 步要 `triage.md`、`review-only` 第 4 步要 `review/verdict.md`，不再出现 `stage-N.md`。
5. `gate_strict: "true"` 时坏输入拒绝；不写这个键时坏输入放行。

## 现状（每条带证据）

| # | 事实 | 证据 | 置信度 |
|---|---|---|---|
| 1 | hook 靠 shebang 直接执行，Windows 下解析到 Store 占位程序（exit 49） | `hooks/gate-edit:1`、`scripts/workflow_next.py:1`；实测 `echo 1 \| python3 -` → exit 49 | 已证实 |
| 2 | hook 失败时 Cursor 按 `failClosed` 拒绝写入 | `.cursor/hooks.json`、`install.sh` 的 `merge_cursor_hooks`（写死 `failClosed: True`） | 已证实（配置即证据） |
| 3 | 门禁不区分读写：`read_file` 的 `target_file` 被当写入目标 | `gate-edit:289 destinations()` 不看 `tool_name`；临时仓实测 `read_file api/a.proto` → `deny` | 已证实 |
| 4 | 输出未固定编码，中文在 Windows 下乱码 | `gate-edit:26 emit()` 用 `ensure_ascii=False`，未设 stdout 编码；实测 `next` 输出 GBK 字节 | 已证实 |
| 5 | 中文 artifact 兜底成 `specs/<f>/stage-N.md` 幻影文件 | `workflow_next.py:216`；实测 hotfix→`stage-1.md`、review-only→`stage-4.md` | 已证实 |
| 6 | hook 有写副作用：每次调用都可能 `mkdir specs/` | `gate-edit:236` → `layout.store_root()` → `os.makedirs` | 已证实（读码） |
| 7 | 自带回归用例在本机跑不起来 | 实测 `WinError 193`；`check_runner.py:31` 直接执行 `.py` | 已证实 |
| 8 | 现有用例不覆盖读写区分 | `check_runner.py:396 gate_permission()` 的 payload 没有 `tool_name` | 已证实（读码） |

## 现有能力（复用，不新造）

- `layout.configured_store()`：只读解析 `artifacts_root`，不建目录 → 直接复用，去掉 hook 的副作用。
- `check_runner.py` 的 `expect()` / `with_store()` / `clean_env()` / `git_init()` 复用，只换启动方式与 payload。
- 不动 `passes.log` 语义、不动 workflow stage 顺序、不动 hook 判定规则本身（`design` / `waiver` 条件一字不改）。

## 最小充分方案

1. 新增 `scripts/find_python.sh`（`dw_python()`）：按 `py -3` → `python3` → `python` 顺序**实跑探测**（`-c "import sys"` 必须成功），Store 占位程序因此被跳过。
2. 逻辑搬到 `hooks/gate_edit.py`；`hooks/gate-edit` 变成 bash 薄壳（找到解释器再 `exec`），另加 `hooks/gate-edit.cmd` 给原生 Windows。
3. `gate_edit.py`：按 `tool_name` 白名单只处理写工具；`apply_patch` 从补丁文本抠目标路径；其余一律 `allow`。异常/坏 JSON 默认放行，`gate_strict: true` 时拒绝。
4. 两个 python 脚本固定 stdout 为 UTF-8。
5. `stage_paths()` 不再造文件名；`hotfix` 第 1 步与 `review-only` 第 4 步改成真实工件路径。
6. `install.sh`：去掉 `rsync` 依赖（有就用、没有走 `tar` 管道）、`python3` 换成探测结果、生成的 `hooks.json` 用 `failClosed: false` 且命令带 `bash` 前缀。
7. `check_runner.py`：`sys.executable` 启动、`encoding="utf-8"`、payload 带 `tool_name`，并新增 5 条用例。

## 为什么更小的做法不够

只改 shebang（`#!/usr/bin/env python3`）解决不了 Windows 上「Cursor 用 cmd 执行无扩展名文件」这一步；只改 `failClosed: false` 不解决读写误拦；只修读写区分不解决"测试跑不起来"。四条必须同时改，否则任何一条都无法被验证。

## 相关的债

- B 局部偿还：只还"能被验证"这一块。`gate_check` / `passes.log` 自授权 / 知识落点（P1、P2）明确留到下一轮，写进 `check.md` 的"仍然欠着的"。
- 不碰：`shell_destinations()` 的正则盲区（文档已声明尽力而为），属 P1。

## 这次不做

- 不新增工作流、不新增阶段、不改 `passes.log` 的放行语义。
- 不动 `evals/evals.json`（等 runner 能跑之后再对一遍）。
- 不动 `SKILL.md` 的 description 长度、不拆 profiles、不改 `routing.md` 的空 `$CARDS`（P1）。

## 风险

不碰契约、持久化、权限、状态、回滚。唯一的行为变化是：**默认从 fail-closed 变成 fail-open**，即"hook 崩了不拦写入"。这是有意的（理由写进 `references/edit-gate.md`），代价是门禁在坏环境下会静默失效，需要 `gate_strict: "true"` 才能恢复严格。
