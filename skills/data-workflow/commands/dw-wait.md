---
description: 停下来等一句可以原样粘贴的回复
---

**先确认前提：只有已经有一条 `working` 状态的运行、且当步打了 `OPEN` 或 `NEED` 需要人拍板时，才用这条。**
没有运行、或者只是梳理 / 排查 / 只读，不要用这条——那种情况按 `{{SKILL}}/SKILL.md` 的「只读、不改代码的入口」读 `stages/oncall/references/routing.md`。

确认有,再运行：`{{RUNNER}} wait <feature> "<问题>" "<对方能原样粘贴的一句>"`，然后停止。
不要自己把决定写完。
