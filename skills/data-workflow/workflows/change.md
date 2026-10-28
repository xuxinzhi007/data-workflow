# 一次改动

这条只用于没有 data-service 阶段表的仓库，或者这次改动用不上那九项负债。

1. 写 `specs/<feature>/decision.md`：改什么，不改什么。还剩一个选择时，文件里写上「待拍板」，然后运行 `workflow_next.py wait`。`reply` 是对方能原样粘贴回来的一句。写完停止，不要接着改代码。
2. 对方回了那一句，运行 `answer`。然后只按 decision.md 改文件。改完运行 `done`。
3. 写 `specs/<feature>/check.md`：命令和最后看到的结果。没有命令可跑就写没有。

保护哪些路径看该项目 `config.yaml` 的 `protected_paths` 和 `waiver_globs`。这两个键都没写时，仍按 `references/edit-gate.md` 的默认路径拦截。
