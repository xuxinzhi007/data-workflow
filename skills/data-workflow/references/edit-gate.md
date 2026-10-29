# 编辑门禁

Cursor 项目安装会把 hook 写进该仓库的 `.cursor/hooks.json`。会话开始就注入本技能，不等触发词。`preToolUse` 和 `beforeShellExecution` 在写入前查 `specs/passes.log`。没有记录就拒绝。

`--global` 不写这道 hook。Qoder、Claude、Codex 的副本没有这道拦截，那些环境里门禁仍只在技能被读到之后生效。

hook 看得见的是写入工具的目标路径（`path`、`file_path`、`filePath`），以及命令文本里带有路径的写入（重定向、`tee`、`sed -i`、`rm`、`mv`、`cp`）。从补丁文件间接写入时，命令文本里没有目标路径，hook 看不到。

shell 这条是尽力而为。挡不住 `python -c` 里打开文件、变量拼出来的路径、heredoc，以及 `&&` 或管道后面的 `sed -i`。提交前和 CI 里的 diff 才是兜底。

`failClosed: true` 时，钩子崩溃、超时或没有打出 JSON，Cursor 会阻止这次操作。并发调用偶尔会拿到空 stdout，界面只说 hook 没有输出。被拒绝且没有拒绝理由时，重试一次。

## 谁要记录

| 写入 | 放行 |
|---|---|
| `specs/` 下的工件，含 `passes.log` 本身 | 直接写 |
| `api/`、`*.proto`、`*.pb.go`、`internal/biz/status.go` | `design` 行，且该 feature 的方案门已落盘 |
| 其它 `*.go` | `waiver` 行，或覆盖该文件的 `design` 行 |
| 其余文件 | 直接写 |

调用方在别的仓库里，这道 hook 拦不到。本仓库里协议和状态定义用上表拦住。

## 记录格式

`specs/passes.log`，一行一条，`#` 开头是注释。

```text
design <feature> <前缀>
waiver <前缀> <原因>
```

`<feature>` 只含字母、数字、`.`、`_`、`-`，对应目录 `specs/<feature>/`。前缀是相对仓库根的文件或目录，不含空格。`api/order` 覆盖 `api/order/a.proto`，不覆盖 `api/order2`。

`design` 生效还要同时有：

- `specs/<feature>/plan.md` 非空
- `specs/<feature>/gate` 第一条非空行是 `plan pass`

`plan pass` 只在技术方案门过了之后写。hook 只认这个文件，不重新给九项负债打分。

内部小改动用 `waiver`，原因写在同一行前缀后面。先追加这一行，再改 Go。

## 项目自己的路径

`config.yaml` 里可以写两个键，逗号分隔，相对仓库根：

```yaml
protected_paths: "api/**,*.proto,*.pb.go,internal/biz/status.go,*/biz/status.go"
waiver_globs: "*.go"
```

写了就用写的。`protected_paths` 为空表示没有路径要 `design`。`waiver_globs` 为空表示没有路径要 `waiver`。两个键都不出现时，用上面那张表。

## 和一次运行对上

`specs/<feature>/run.json` 的 `status` 是 `working` 或 `waiting` 时：

- 工作流 `kind` 是 `review`：除 `specs/` 以外的写入都拒绝。
- 工作流 `kind` 是 `execute`：`design` 行里的 feature 必须是这次运行的名字。没有这份运行记录时，仍接受任意合法 feature。

下一步读哪个文件、要不要停下来问一句，由 `scripts/workflow_next.py` 打印。本文件只规定写入能不能发生。
