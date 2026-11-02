# docs-drift 决定

- 级别：L1
- 原话（一字不改）：现在回到现在的这个项目吧 进行整理和分析吧
- 我理解你要的是：把 data-workflow 仓库整体过一遍，找出文档与实现不一致、死文件、失效引用这类积累问题，修掉并用断言钉住
- 可能理解错的地方：「整理」也可能指把 15 个 specs/ 运行记录归档或清理，或者精简冗长的阶段正文。我按「文档与实现一致性」做——那是能客观判定的，其余需要你定方向。
- 本质：文档会随实现漂移。上一轮实战里新人照 README 写 decision.md 被门拦住，就是漂移的直接后果。
- 怎样算满足：
  1. README 的流程示例与 `change.json` 的 `requires` 一致
  2. `docs/scripts.md` 列出每个实际存在的脚本
  3. 文档里不硬编码会随测试增加而过期的数字
  4. 新增断言覆盖这三条，破坏时变红
- 未知：无
- 这次不做：不归档 `specs/`（15 个运行记录，332K，都 done，删了会丢决策追溯）。不精简阶段正文（那是另一个判断）。不动 `bugfix`/`hotfix`/`review-only` 的空 requires。
- 现有能力（整理时的实测结论）：
  - README「写 decision.md：原话 / 本质 / 验收 / 未知 / 这次不做」与实际 requires 5 项不符，缺「我理解你要的是」「可能理解错」—— 已证实
  - `docs/competitive.md` 写「47 条回归」，实际 123 条 —— 已证实
  - `docs/scripts.md` 漏列 `find_python.sh`、`layout.py`、`check_runner.py` —— 已证实
  - 全部 md 的相对链接 0 失效 —— 已证实
  - 无零引用的死文件 —— 已证实（逐个统计引用次数）
  - evals 5 条与 check_runner case 映射全部成立 —— 已证实
  - 15 个运行全部 done，无未完成 —— 已证实
- 旧决定：`specs/install-go-verify` 等。实现是否仍符合：符合。
- 最小充分方案：
  1. README 的 decision.md 第一屏改成实际 7 项，并说明含糊时先 wait
  2. `docs/competitive.md` 去掉硬编码数字
  3. `docs/scripts.md` 补齐三个脚本
  4. `check_runner.py` 加两条断言：README 第一屏 ⊇ requires；scripts.md ⊇ 实际脚本清单
  5. 加一条断言：competitive.md 不得出现 `verify.sh # <数字>条` 这种写法
- 为什么更小的做法不够：
  - 只改 README 不加断言 → 下次改 requires 又会漂，而且是同一个坑
  - 让断言去跑一遍 verify 来自检断言数 → 会递归、内外层互相干扰（试过，超时）
  - 把断言数写进文档 → 每加一条测试就过期，本质上是记录一个必然变化的数字
- 相关的债：A 现在偿还。这是上一轮实战暴露的直接后果。
- 风险：不碰契约、持久化语义、权限、状态、回滚。
