# AI 使用 data-workflow 的经验提炼

> 每段标日期 + 工作流 + feature（如果是 run 里的）+ 证据。没有就跳过，不硬写。

---

## 2026-11-10

### workflow JSON 里的 self_check / reads / note / on_gate_fail / calls / subagents AI 永远看不到（bugfix, change）

**证据**：实际跑了 bugfix workflow。runner 打印 `READ stages/oncall/SKILL.md`，AI 跟着 READ 走读 stage SKILL.md，不会主动读 workflow JSON。stage SKILL.md 里 self_check 的内容覆盖率 0%。

**修复**：workflow_next.py 加了 `print_stage_hints(stage)`，在 STAGE/READ 之后打印 JSON 里的提示字段。

**教训**：判断"字段/文件有没有用"时，runner 不读 ≠ AI 看不到——两个消费方独立。先跑一遍看真实数据流（谁消费 → 怎么消费 → 能不能到），不能用间接推断跳过。

### runner 和 AI 是两个独立消费方

runner 读机器可判字段：stages 数组、id/name/file/artifacts/requires/gate_check/code/kind。
AI 读提示字段：self_check、reads、note、on_gate_fail、template、calls、subagents。

两者不重叠。所有字段都写进同一个 JSON 是合理的设计——但需要 runner 把 AI 提示转发出来。

### 共享 stage 文件里不要塞 workflow 专属提示

oncall/SKILL.md 同时被 bugfix 和 hotfix 用，但 bugfix 的 self_check 是"根因要有代码证据"，hotfix 是"根因未明也能止血先止血"——直接塞进同一个 md 会出现互相矛盾的指令。runner 转发方案（B 方案）天生解决这个问题。
