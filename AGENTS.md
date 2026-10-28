# AGENTS.md

本仓库是一个 **IDE 无关的 agent 技能项目**（agentskills 标准：SKILL.md + references/ + scripts/）。

- 安装后工具目录里只有一个技能 `skills/data-workflow/`。选型、顺序、六道门禁在它的 `SKILL.md`；阶段文件在它的 `stages/`，不单独安装。阶段序列是 `workflows/*.json` 状态机（新业务场景写新模板，不加新技能），工件模板在 `templates/`，已修缺陷钉在 `evals/evals.json`。
- 技能只装流程；业务事实运行时从知识源读取，**知识源路径不硬编码**。配置在引用仓库的 `.<工具>/skills/data-workflow/config.yaml`，和技能放在同一个目录（`install.sh` 从 `config.example.yaml` 复制，已存在不覆盖），不写回技能仓库。解析入口 `scripts/resolve.sh <key>`，技能里一次 `eval "$(bash scripts/paths.sh)"` 拿到 `$KNOW $CARDS $TEMPLATES $REPO` 等；解析为空就问用户，不猜绝对路径。
- 装进目标工具：`bash scripts/install.sh` 把 `skills/data-workflow/` 复制进已存在的 `.claude/.cursor/.qoder/.codex/.agents`（`--global` 装个人级，`--unlink` 卸载副本并留下 config.yaml）。副本不依赖本仓库。
- 本文件只做指路牌，**不承载技能正文与业务事实**——那些内容进 AGENTS.md 会撑爆上下文且必然腐化。
