# spec-intent 决定

- 级别：L2
- 原话（一字不改）：接着进行实现吧
- 我理解你要的是：把上一轮在 `change` 里做好的「理解确认」回路，补到 `feature` 工作流第 1 步的 `spec.md` 上——L3 变更比 L1 更需要先确认理解对不对
- 可能理解错的地方：「接着」可能指遗留 1（feature 补回路），也可能指遗留 2（正文引用门关键字会误判）。我按遗留 1 做——上一轮 check.md 把两条都列为遗留，没指定顺序；遗留 1 直接影响用户看到的行为，遗留 2 是内部误判，优先做前者。
- 本质：让 L3 变更在写 spec 之前，也强制过一次「我理解的和你要的是不是一回事」，并且同样把判断权留给用户。
- 怎样算满足：
  1. `spec-template.md` 头部含「我理解你要的是」和「可能理解错的地方」两行
  2. `feature.json` 第 1 步 `requires` 加上这两个字面量，缺了 `next` 打 GATE
  3. 写「无歧义」是合法答案，门不因缺歧义而卡
  4. 照抄原话时给 NOTE，不阻塞（与 `change` 行为一致）
- 未知：无
- 这次不做：不改 `open_decision` 的误判逻辑（遗留 2，另起一次）。不动 `bugfix` / `hotfix` / `review-only`。
- 现有能力：
  - `templates/decision-template.md` 已有这两行及「怎么用」一节 —— 已证实（`specs/intent-confirm`）
  - `workflow_next.py:restated_raw` 已实现照抄检测，与工作流无关 —— 已证实（`case_restated_raw`）
  - `unmet_requires` 是通用字面量门，对 feature 同样生效 —— 已证实（`feature.json` 现用 `requires: [本质,怎样算满足]`）
- 旧决定：`specs/intent-confirm/decision.md` 的不做项。实现是否仍符合：符合。
- 最小充分方案：
  1. `templates/spec-template.md` 头部加两行，与 decision 模板措辞保持一致
  2. `feature.json` 第 1 步 `requires` 从 `[本质, 怎样算满足]` 扩成 4 项，gate 文案同步
  3. `stages/requirement-analysis/SKILL.md` 的「收窄本质」步骤前补一句：先确认理解再收窄
  4. `check_runner.py` 加一条断言：feature 第 1 步的 requires 含这两行，且 spec 模板有对应行
- 为什么更小的做法不够：
  - 只改模板不加 requires → 模型可以整行不写，门不响
  - 只加 requires 不改模板 → 模型不知道要写哪两行，只能猜措辞，门会误伤
  - 两处措辞不一致（模板写「我理解你要的是」、requires 写别的）→ 字面量门永远匹配不上
- 相关的债：B 局部偿还——把 `change` 已验证的写法原样搬过来，不发明第二套措辞。`bugfix`/`hotfix` 是否需要同类改动，本轮不评估。
- 风险：不碰契约、持久化、权限、状态、回滚。
