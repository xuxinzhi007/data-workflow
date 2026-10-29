# 安装

在目标仓库根执行。data-service 和其他仓库是同一条命令。

```bash
bash ~/skills/data-workflow/scripts/install.sh
bash ~/skills/data-workflow/scripts/install.sh --global
bash ~/skills/data-workflow/scripts/install.sh --unlink
```

`--global` 复制到 `$HOME` 里已经有的工具目录。它不写 Cursor hook，也不写 `/` 命令。

`--unlink` 卸掉副本，留下 `config.yaml`。

脚本只改已经存在的 `.qoder`、`.claude`、`.cursor`、`.codex`、`.agents`。不创建没有的工具目录。复制进 `skills/data-workflow/`，不软链回技能仓库。再跑一次更新正文，不覆盖已有的 `config.yaml`。

在本技能仓库里执行时，不另拷一份技能。`.cursor/hooks.json` 指向 `skills/data-workflow/hooks/`。

装进带 `.cursor` 的项目后，hook 在写入前查 `specs/passes.log`。路径表在技能的 `references/edit-gate.md`。Qoder、Claude、Codex 的副本没有这道拦截。

有未完成运行时，`sessionStart` 注入一条 NOTICE：运行名、状态、一行摘要。它不代替当前需求。用户要继续那条时再跑 `next`。这取决于当前 Cursor 会不会加载 `.cursor/hooks.json`。新会话没有看到 NOTICE 时，先看这份文件是否被加载。

Agent 输入框输入 `/`，可选 `dw-next`、`dw-done`、`dw-wait`、`dw-start`。这四个文件写在目标仓库的 `.cursor/commands/`。

Qoder 也可以走插件通道。插件通道会复制进缓存：

```bash
qoder plugins install ~/skills/data-workflow --scope user
```
