# 一次改动

这条只用于没有 data-service 阶段表的仓库，或者这次改动用不上那九项负债。改动落在 `api/`、proto、pb.go、`internal/biz/status.go`，或涉及状态机、租户权限、回滚时，不用这条，用 `feature` 或 `hotfix`。

`decision.md` 第一句写用户这次真正要的结果。已有 `文件:符号` 能做到就复用。做不到的最小改动才写进「改什么」。

定架构时，同一份 `decision.md` 写四句：现有边界各管什么、这次不新增什么、下一刀落在哪个边界、还没有出处的词。词的含义走知识层，空则待确认。不套 feature 的九步。另一个仓库把 `protected_paths` 和 `waiver_globs` 写成自己的路径；两个键都写成空，才不用 data-service 的默认 Go 路径。只定架构、还没有该仓库的测试入口时，`done` 会停在 `RED`，不要写成通过。

1. 写 `specs/<feature>/decision.md`：改什么，不改什么。还剩一个选择时，文件里写上「待拍板」，然后运行 `workflow_next.py wait`。`reply` 是对方能原样粘贴回来的一句。写完停止，不要接着改代码。
2. 对方回了那一句，运行 `answer`。然后只按 decision.md 改文件。改完运行 `done`。`done` 跑这个仓库自己的测试入口（`verify`，或 package.json / Makefile / pytest / cargo 里已经写明的那条）。退出码不是 0 就停，输出在 `specs/<feature>/verify.log`。
3. 写 `specs/<feature>/check.md`：只写 verify.log 的 exit 那一行。没有配置 verify 时，`done` 停在 RED，不要自己写成通过。

保护哪些路径看该项目 `config.yaml` 的 `protected_paths` 和 `waiver_globs`。这两个键都没写时，仍按 `references/edit-gate.md` 的默认路径拦截。
