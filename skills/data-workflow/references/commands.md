# 命令

Agent 输入框里输入 `/`，选 `dw-next`、`dw-done`、`dw-wait`、`dw-start`。`install.sh` 把这四个文件写到**当前项目**的 `.cursor/commands/`，默认安装也一样——技能副本在 `$HOME`，命令在项目里，可提交给团队共享入口。

脚本只有一份，相对技能根：

```bash
python3 "$PLUGIN_ROOT/scripts/workflow_next.py" <子命令>
```

| 子命令 | 何时 | 成功时看到 |
|---|---|---|
| `next` | 用户要继续那条未完成运行 | 只一件：`NEED`、`WAIT`、`DO`、`OPEN` 或 `DONE` |
| `next` | 没有未完成运行 | `NO_RUN`，或 `LAST` 加记录路径 |
| `start <workflow> <feature>` | 新开。workflow 为 feature、bugfix、hotfix、review-only、change | 停在第一阶段缺的文件 |
| `wait <feature> "<问题>" "<一句回复>"` | `OPEN`，或还要问一句 | `run.json` 里有这句 reply |
| `answer <feature> <回复原文>` | 对方回的就是 reply | 仍开着的产物末尾有 `已拍板：` |
| `done <feature>` | `DO` 做完 | 编码步骤先跑该仓库的测试入口。非 0 则 `RED`，停在这一步。退出码 0 只说明这条命令通过 |
| `abandon <feature>` | 这轮不做了 | `status` 成为 `abandoned`。`next` 把它当已结束，钩子不再注入 |
