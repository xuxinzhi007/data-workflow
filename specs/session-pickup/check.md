命令：`bash scripts/install.sh /Users/xuxinzhi/skills/data-workflow`

结果：`SOURCE .../skills/data-workflow`，`HOOKS add .../.cursor/hooks.json`。没有生成 `.cursor/skills/data-workflow` 副本。

`.cursor/hooks.json` 的 sessionStart 命令是 `skills/data-workflow/hooks/session-start`。

命令：在仓库根执行这个 hook。

结果里先是：

```
RUN session-pickup change working
RECORD specs/session-pickup/run.json
DO
STAGE 2 按决定改
```

后面才是 next / start / wait / answer / done 的用法。没有要求从 SKILL.md 步骤 0 重开。

命令：对 `skills/data-workflow/scripts/workflow_next.py` 走编辑门禁。

结果：`{"permission": "allow"}`。本仓库 config 把 `protected_paths` 和 `waiver_globs` 写成空，所以改这个技能不会套 data-service 的 Go 门禁。

命令：`workflow_next.py done session-pickup`

结果：进入阶段 3，`NEED specs/session-pickup/check.md`。

命令：写完本文件后再跑 `workflow_next.py next`（不带 feature）。

结果：

```
LAST
RUN session-pickup change done
RECORD specs/session-pickup/run.json
DONE session-pickup
DEFAULT change
```

会话 hook 打出来的第一段也是这个，不是「先读完整份 SKILL.md」。
