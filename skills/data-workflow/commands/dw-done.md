---
description: 结束当前步骤，编码步骤先跑该仓库的测试入口
---

**先确认有一条未完成的运行。** 没有运行就没有可结束的步骤——别硬造一个 feature 名。

feature 取当前未完成的 `specs/<feature>/run.json`；只有一个未完成运行时省略也行，多个时 `next` 会打 `MANY` 列出来，挑一个写上。

然后运行：`{{RUNNER}} done <feature>`
退出码不是 0 就停在这一步，不要跳到下一步。
