# AGENTS.md

拦住写错和假完成。一个词在业务里指什么，从知识层读，不写进技能。流程在 `skills/data-workflow/SKILL.md`，点名再读。

- 知识源走 `skills/data-workflow/scripts/resolve.sh`。空值就问，不猜路径。
- 梳理一个词、字段或状态：读 `skills/data-workflow/stages/oncall/references/routing.md`。不改代码，不编口径。
- 用户真正要的那一句能用现有 `文件:符号` 做到，就走 `change`。技术债读 `skills/data-workflow/stages/requirement-analysis/references/debt-gate.md`。
- 定架构走 `workflows/change.json`。形状写在 `decision.md`，不套 feature 九步。
- 未做完的运行在 `specs/<feature>/run.json`。`workflow_next.py next` 打出 NEED、WAIT、DO、OPEN 时只做那一件。

## Agent skills

### Issue tracker

Issues 和 spec 记在仓库里的 `.scratch/<feature>/`。见 `docs/agents/issue-tracker.md`。

### Triage labels

五个默认角色，标签名与角色名相同。见 `docs/agents/triage-labels.md`。

### Domain docs

单仓库：根目录 `GLOSSARY.md`，决策在 `docs/adr/`。见 `docs/agents/domain.md`。
