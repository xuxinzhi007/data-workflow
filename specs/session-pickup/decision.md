改什么：新开的会话不靠上一场聊天。这个仓库每次会话先跑 `skills/data-workflow/scripts/workflow_next.py next`，上次停在哪看 `specs/<feature>/run.json` 和它打印的那一件事。用法跟在同一段输出里。本仓库的 Cursor hook 指向 `skills/data-workflow/hooks/`，不另拷一份，改完的脚本就是会话里跑的那份。

不改什么：不把进度摘要写进 AGENTS.md。不改 data-service 那份配置里的个人路径，也不放宽那边的默认门禁。不把 Matt、pstack、Osmani 包进来。

运行记录在当前 git 根的 `specs/`，不是 `config.yaml` 里的 `repo`。
