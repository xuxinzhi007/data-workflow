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

## 2026-12-01

### 自评和被评的东西挤在同一份产物里，诚实就有代价（change）

**证据**：`requires` 是字面量门（V2，`workflow_next.py:353` 全文子串匹配）。AI 写 `decision.md` 时，"显得完整"和"承认没想清"在同一份文字里竞争。而且诚实写"这里没把握"会触发 `wait` 停住流程——诚实有成本。

**依据**：OpenAI《自白技术如何让语言模型保持诚实》（2025-12-03）。它的机制不是教模型诚实，是给诚实单独开一条不参与主奖励竞争的通道。其实验里主回复真实准确率下降、自白准确率上升到接近 100%。

**改动**：加 `confess` 通道。`done` 推进后打印 `CONFESS`，写 `specs/<feature>/confess/<stage-id>.md`。三个问题只问事实，不问评价。**不入门、不影响推进、不退回。**

**教训**：转发提示（`print_stage_hints`）是必要条件，不是充分条件。就算 AI 看到了 `self_check`，让它在同一次输出里自评，这个自评本身不可信。真修法是把自评变成独立的一次调用。

### 改 runner 时，收尾提醒会漏在早退分支里（change）

**证据**：`print_unconfessed` 加在 `show()` 循环结束后的 DONE 处，但 `advance` 把 status 置 done 后，`guard` 循环下一圈命中 `status == "done"` 早退（第 758 行），跳过了末尾那行。实测：`next` 打完 DONE 没有 UNCONFESSED。

**修复**：done 早退分支也调用 `print_unconfessed`。

**教训**：`show()` 有一个 while 循环，DONE 有两条出口（早退分支、循环末尾）。加输出时两条都要看一眼——这与"两个消费方"是同一类错误：**一个结论有多条路径到达时，只在其中一条上做修改。**

### 先翻历史，再决定要不要做实验（change）

**证据**：C3/C9 的 2×2 对照实验要跑 40 次模型调用。但在跑之前，`specs/` 里躺着 20 次真实 `change` 运行——免费数据。`bash scripts/self-eval-stats.sh` 跑出来的分布：

- 「未知」栏：有这栏 17 份，写「无」15 份（88%）
- 「可能理解错」栏：有这栏 11 份，写内容 10 份（91%）

**观察**：两个栏都是自评、都过同一个字面量门、写在同一份文件里。凭什么一个 88% 走过场、另一个 91% 在写内容？

**解释（推断，未证实）**：「可能理解错」要复述用户需求，有外部文本（原话）可对账；「未知」要报「自己不知道什么」，没有外部锚点，写「无」永远安全。

**教训**：做实验前先把已有产物的分布数出来。这次省掉了 40 次模型调用——而且拿到的结论比对照实验更具体：自评失效不在「所有自评」，具体在「没有外部锚点的自评」这一维。

### 自动判分器的边界要写在它自己的输出里

**证据**：`honesty_stats.py judge` 第一版直接把 `decision.md` 里所有反引号路径拿去对磁盘，判 20/21 缺失。实际大部分是相对技能目录的路径，或「这次要新建」的路径，不是编造。

**修复**：多基准根路径逐试，并把局限打在使用者眼前：「M1 只能回答这些路径在磁盘上找不到，不能回答是不是编造」。

**教训**：判分器一旦输出数字，就会被当成事实。所以它的局限必须印在自己的 stdout 里，不能只写在设计文档中——设计文档没人读，stdout 每次都读。

### 命令文件写死路径，只在开发环境跑得通（install）

**证据**：在 data-service（真实使用环境）实测，`python3 .cursor/skills/data-workflow/scripts/workflow_next.py next` 报 `ENOENT`。四个 `commands/*.md` 都写「装进别的仓库后在 `.cursor/skills/data-workflow/scripts/workflow_next.py`」，但默认安装（$HOME）根本不往项目里放技能副本。在技能源仓库里这个路径是存在的，所以从来没暴露。

**修复**：`install.sh` 不再 `cp` 原样复制，改为按实际落点把 `{{RUNNER}}` / `{{SKILL}}` 替换成绝对路径。

**教训**：和 C2「19 项探针是凭经验枚举的」是同一类错误——**测的环境不是用的环境**。任何「路径」「位置」类的字符串，只要能在开发目录里成立，就一定会漏掉安装后的真实布局。判据必须是「装一遍，然后验证那个路径真的存在」。

### 命令文件是第二个路由入口，约束必须写在入口上（install）

**证据**：`SKILL.md:22` 写「只梳理、不改代码时不 start」，但 `dw-start.md` 无条件执行 start。`SKILL.md:45` 写「不 start，直接读 routing.md」，但 `dw-wait.md` 只写「运行 wait，然后停止」。四个命令里只有 `dw-next` 写了兜底（「没有未完成运行时回答当前的问题」）——只有它不出问题。

**修复**：四个命令文件都补上前置条件（什么时候该用、什么时候不该用），路径改为安装时注入。

**教训**：`commands/*.md` 是独立入口，用户敲 `/` 直接命中，**不经过 SKILL.md**。副本内容少于原件就是制造冲突。这和「共享 stage 文件」是同一类，但更严重：不只是共享，是跨文件重复且不同步。

### 目录不存在时静默 return，然后报一个不存在的路径（install）

**证据**：`install_commands` 开头是 `[ -d "$root/.cursor" ] || return 0`。新项目没有 `.cursor` 时，4 个命令被静默丢弃；紧接着 DONE 分支打印「Cursor 命令在 <base>/.cursor/commands/」——那个目录不存在。两处错误叠加：**丢东西 + 谎报**。

**修复**：改成 `mkdir -p`；DONE 那句的 `$base`（HOME）改成 `$project_root`。

**教训**：`return 0` 是「成功」的退出码。用它在「跳过」的路径上，调用方无法区分「做了」和「没做」。要么返回非 0 并打印原因，要么就别让这条路径存在。

### 命令只写 .cursor，不写 .agents（install）

**核实**：`.agents` 在项目和 HOME 都有，但只有 `skills/`，没有 `commands/` 的约定。斜杠命令是 Cursor 特有机制。

**决定**：只写 `.cursor/commands/`。非 Cursor 环境不需要命令文件——`SKILL.md` 的 description 会让 AI 自动触发，那才是真入口。往 `.agents` 塞 `commands/` 会让「技能」和「命令」两个概念混在一起，且放进去也不会生效。

### 抄格式不抄架构：tempest 的两条规则（stages）

**参照**：`mtthsnc/tempest`（参考对比用，不入本仓）。它 9 个 skill 全是 `Overview → Procedure → Common mistakes → Guardrails`，`description` 一律以 "Use when" 开头，`validate.sh` 强制检查。

**只抄两条**：

1. `description` 是触发器，不写步骤。原来 SKILL.md 的 description 写了「先跑 next 再读文件」——照它的话，agent 会照摘要办事而不读正文。
2. 每个 stage 加「常见错法」段。历史证据：`specs/` 20 次运行「未知」栏 88% 写「无」——文件只讲做什么，没讲最容易错成什么样。

**不抄**：它的状态机（它根本没有，`plan→build→review` 只是文档建议路径）、符号链接安装、只做格式验证。本仓的 `run.json`/字面量门/`evidence.log` 是它没有的东西。

**体积纪律**：融合只给 stage 加失败模式段，运行时 2005 → 2077 行（+72，每个 stage 均 +7），最长 stage 180 行。锁在 `case_stages_have_failure_modes` 的 200 行上限里——超了就说明该拆 reference，不是加长。

## 2026-11-12

### 状态机缺一个「不需要做了」的终态，比缺一个阶段更贵（bugfix-close-exit）

**证据**：真实运行复现。临时仓库 `start bugfix bug-x` 后，在 `specs/bug-x/spec.md` 写「已修复 commit abc123，验证通过，不需要再排查」，`next` 仍输出 `STAGE 2 修复影响面 / NEED impact.md`。同名再 `start` 打到 `ALREADY` 后直接 `show(existing)`，人被拽回旧链条，连开新运行的口都没有。

**根因**：`run.json` 只表达「进度」（`stage` 索引）和「结束」（`status=done`）。「这个 bug 已经不存在了」不是某个阶段的产物，也无法用「再写一份文件」表达——它是**终止判定**。状态机里没有这条边，AI 就只能沿着唯一的路继续要文件。

**修复**：加终态 `closed`（+ `outcome` 说明为什么关），由显式子命令 `close` 触发，不在 `next` 里自动评。

**教训**：判断「缺的是阶段还是终态」看一件事——这个变化是**多写一份产物**，还是**不用再写了**。前者加阶段，后者加终态。用阶段去表达「不用做了」，就会永远停在那个阶段要文件。

### 判定「已经好了」必须有外部锚点，字面量不够（bugfix-close-exit）

**证据**：上一轮的候选修法是给 bugfix 阶段 1 加 `requires: ["复现"]`。但 `requires` 是全文子串匹配，「无法复现，已修复」里也有「复现」二字——门立刻退化成第二个「未知=无」。这与 `docs/dev/learnings.md` 上面那条 88% 是同一个失效模式：自评没有外部文本可对账时，写最安全的那个词永远过关。

**修复**：`close_if` 要求三项独立成立——产物文件非空、产物含 `literal` 里的每一条、`fingerprint` 命令 exit 0。前两项人可读，第三项是外部锚点。**字面量单独永远不足以关单**，有专门用例钉住：`PASS all literals present but a failing fingerprint still refuses`。

**教训**：任何「确认某事已经不成立」的判定，都要有一条**不由被判定方提供**的证据。退出码、测试结果、外部 API 响应都行；文档里的一句话不行。

### 同一个阶段被两个入口判，结论必须一致（bugfix-close-exit）

**证据**：`show()` 在 `if stage.get("code")` 处 `return`，而这段代码在 `open_decision` / `unmet_requires` / `run_gate_check` **之前**。于是 `code` 阶段的五道门只有 `done` 会判：`next` 说 `DO`（去做），`done` 说 `GATE`（不许），中间没有任何提示。

**修复**：抽出 `stage_gates_block()`，`show()` 与 `cmd_done()` 共用，并把调用点提到 `code` 分支之前。

**教训**：和上面「DONE 有两条出口」是同一类错误的另一面——**同一个判定有多条进入路径时，只在其中一条上做检查**。加一个阶段属性时，要问「哪些阶段类型会早退，它们会不会跳过这个检查」。

### 模板里的「恒真」默认值等于给门开后门（bugfix-close-exit）

**风险**：第一版把 `bugfix.json` 的 `close_if.fingerprint` 写成了 `true` 做占位。后果：照着不改的人可以凭一句「已修复」直接关单——正好是本改动要防的事。

**修复 1**：占位改成一个**恒 exit 0** 的命令（打印「还是占位，把它改成本 bug 的复现命令」）。因为 `fingerprint` 的极性是「exit 0 = 仍然复现」，恒 exit 0 就恒关不了，必须有一个人真的把指纹改成复现命令。用例：`PASS the shipped placeholder fingerprint cannot close a bug`。

**教训**：给模板填默认值时，任何「恒真」的默认值都等于给门开了一个后门。占位必须**失败**（在这里是「恒报 bug 还在」），不能通过。这与「`return 0` 是成功码，别用它表示跳过」是同一条：一个东西的默认状态应该是「还没做」，不是「已经做好了」。

### 复用 `run_gate_check` 时，极性会被反转（bugfix-close-exit）——差点上线就关掉活 bug

**证据**：`run_gate_check` 返回的 `ok` 语义是「命令**成功**」（exit 0 = 放行）。而 `close_if.fingerprint` 是**复现命令**，exit 0 = bug 还在。我把 `ok` 直接当成了「可以关」，于是：`app.go` 里还留着 `stuck-status`（grep exit 0）、`spec.md` 写了「已修复」，`close` 输出 `CLOSED bug-x fixed` 并退出 0。**等于是「bug 活着的时候把单关掉」，而且不报错、不留痕**。

**怎么发现的**：端到端手动跑了一遍“bug 仍在 → 应拒绝”的方向，预期 `exit 1`，实际 `exit 0`。写单测时我也是拿着错误极性写的（把 `exit 1` 当“不许关”），所以**测试全绿并没有拦住它**——用了同一个错误假设。

**修复**：在 `cmd_close` 里把 `reproduces` 取反后再判；变量名从 `ok` 改成 `reproduces`，让“这条命令成功 = 什么”在调用点就能读出来。两个方向的端到端用例都补上。

**教训**：

1. **复用别人语义的函数，第一件事是确认它的 true 在你的领域里意味着什么。** `run_gate_check` 的 `ok` 在 `gate_check` 语境里是“门开了”，在 `close_if` 语境里变成“门关了”。同一个布尔在两个调用点意义相反，就一定会写错一边。
2. **变量名 `ok` 会掩盖这个问题。** 叫 `reproduces` 时，“reproduces 为真就返回 1”读起来是显然的；叫 `ok` 时，“ok 为真就返回 1”看起来像个手误，反而容易被“改正”成错的。
3. **测试和实现同时写错时，绿灯是假的。** 我的用例 encode 了同一份错误假设，所以 269 条 PASS 一条都没拦住。判据是“这个用例能不能在我写错时红灯”——不能的话，它只是在重述实现。只用手工跑一遍真实场景（真实文件 + 真实 grep + 看真实退出码）才发现。
