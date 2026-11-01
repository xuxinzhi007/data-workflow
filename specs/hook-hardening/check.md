# hook-hardening 核对

> 规则在 `workflows/change.md` 第 3 步。先写 verify.log 的 exit 那一行，再写验收条件与 diff 范围。

## 1 命令与结果

```
cmd bash scripts/verify.sh
exit 0
OK
```

完整输出在 `specs/hook-hardening/verify.log`（45 条 PASS 之后打印 `OK`）。
入口是本仓库 `config.yaml` 的 `verify: "bash scripts/verify.sh"`；`verify.sh` 自己探测可用 python（本机 `python3` 是 Microsoft Store 占位程序，`py` 指向已删除的解释器，最终选中 `/d/Dev/tools/Python310/python.exe`）。

## 2 验收条件逐条对照

| # | 决定里写的验收 | 结果 | 证据 |
|---|---|---|---|
| 1 | `check_runner` 在本机打印 `OK` | 达到 | `verify.log` 末行 `OK`；用例数从 14 个函数增到 19 个 |
| 2 | 读 `api/foo.proto` → allow；写同一文件 → deny | 达到 | `PASS reading protected paths is allowed`、`PASS writing protected paths is denied`；另外手跑了真实 payload（见下） |
| 3 | 无 python 时 hook 输出合法 JSON 且 allow；`session-start` 仍合法 | 达到 | `PASS missing interpreter allows instead of blocking`；`bash hooks/session-start` 实跑输出正常 NOTICE |
| 4 | `next` 中文可读；`triage.md` / `review/verdict.md` 取代幻影文件 | 达到 | `PASS runner prints readable utf-8`、`PASS hotfix asks for triage.md, not a phantom stage file`、`PASS review-only asks for review/verdict.md` |
| 5 | `gate_strict: "true"` 拒绝坏输入；不开时放行 | 达到 | `PASS bad input fails open unless gate_strict is on` |

### 真实 payload 手跑（临时 git 仓，`protected_paths: "api/**"`、`waiver_globs: "*.go"`）

```
read_file  api/a.proto            → {"permission": "allow"}
edit_file  api/a.proto            → deny  「先完成 specs/<feature>/plan.md …」
apply_patch(*** Update File:)     → deny  （旧版看不见补丁正文里的路径）
edit_file  main.go (waiver_globs) → deny  「往 specs/passes.log 追加 waiver …」
'{not json'                       → allow + 「按 fail-open 放行（gate_strict 未开）」
mystery_tool api/a.proto          → {"permission": "allow"}
```

中文不再是乱码，拒绝理由可以直接照做。

## 3 diff 有没有超出 decision.md

决定里写的是 P0 六条。逐条对上：

| 决定条目 | 落点 |
|---|---|
| 1 解释器探测 | 新增 `scripts/find_python.sh`、`hooks/gate-edit` 改为壳、新增 `hooks/gate-edit.cmd`、`hooks/session-start`、`scripts/install.sh`、`scripts/verify.sh` |
| 2 读写区分 | 新增 `hooks/gate_edit.py`（`WRITE_TOOLS` / `SHELL_TOOLS` / `apply_patch` 抠路径） |
| 3 UTF-8 | `gate_edit.py` 的 `utf8_stdout()`、`workflow_next.py` 顶部 reconfigure |
| 4 fail-open + `gate_strict` | `gate_edit.py` 的 `strict()` 与 `main()`；`install.sh` 不再写 `failClosed: true` |
| 5 幻影工件 | `workflow_next.py` 的 `stage_paths()` / `show()`；`workflows/hotfix.json`、`workflows/review-only.json` |
| 6 回归可跑 | `check_runner.py`（`sys.executable`、`encoding="utf-8"`、payload 带 `tool_name`）、5 条新用例 |

顺手带上的、和这六条直接相关的三处，不碰语义：

- `install.sh` 去掉 `rsync` 依赖（本机没有 rsync，安装会失败）——属第 1 条"让工具链能跑"。
- `.gitignore` 加 `__pycache__/`——跑 verify 会产生。
- `decision()` 不再调用 `layout.store_root()`（旧版每次 hook 都可能 `mkdir specs/`）——属第 2 条"只读"。

**超出范围的：无。** 没有新增工作流、没有改 `passes.log` 的放行语义（`design` / `waiver` 判定一字未动）、没有动 `evals.json`、没有碰 `stages/` 正文。

## 4 行为变化（要说清的代价）

以前默认是 fail-closed（`hooks.json` 写死 `failClosed: true`），现在默认 fail-open，严格度由 `gate_strict` 决定。

- 好的一面：环境缺 python / hook 崩了，不再把仓库变成只读，也不再把「读」当「写」拦。
- 代价：门禁在坏环境下**静默失效**，而不是响亮地拦死。兜底仍然是提交前看 diff。要恢复严格：项目 `config.yaml` 写 `gate_strict: "true"`。
- 另一个已声明的代价：`hooks.json` 的命令带 `bash` 前缀，团队里没装 bash 的机器上门禁不生效。

## 5 仍然欠着的（不在这次 diff 里）

| 欠着 | 为什么这次不做 |
|---|---|
| `passes.log` 仍由模型手写（自授权） | 属 P1，需要 `workflow_next approve` 与一次拍板回话绑定 |
| `gate` / `on_gate_fail` / `reads` / `template` 仍不被 runner 消费（文件名门） | 属 P1，要给每 stage 加 `gate_check` 可执行命令 |
| `run.json` 仍没有 `base_commit` / `raw_request` | 属 P1 |
| `routing.md:8` 空 `$CARDS` 会 `grep -rl … /` | 属 P1，一行 shell 修复但与本轮 diff 无关 |
| `domains` 键无读取方；`stack` 只打警告 | 属 P1 |
| `shell_destinations()` 的正则盲区 | 文档已声明尽力而为 |
| `contract_diff.sh` 仍用 `command -v python3` | 只服务 Go 栈实例，等 `stack` 真正生效时一起改 |
| 本仓库自己的 `verify` 写在**被忽略的** `config.yaml` 里 | 新克隆运行时 `done` 会停 `RED`（`verify 未配置`），手跑 `bash scripts/verify.sh` 即可。要消除这个断点，需给 `declared_verify()` 加一条「仓库有 `scripts/verify.sh` 就用它」的约定（属 P1） |
| 业务分析骨架（`business-model.md`）、知识落点三分、description 瘦身 | 属 P2 |
