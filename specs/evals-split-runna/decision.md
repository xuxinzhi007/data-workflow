# evals-split-runnable 决定

- 级别：L1
- 原话（一字不改）：`evals 里 14 条用例从来没被执行过，拆成机器可判和人工评审两处`
- 本质：README 把 `evals/evals.json` 称作「每条钉住一个已经踩过的缺陷」，但仓库里没有任何代码读它；14 条用例自写下至今零执行记录。这是一处假完成，和 `AGENTS.md` 第一条「拦住写错和假完成」直接冲突。
- 怎样算满足：
  1. `evals/evals.json` 里每一条都能被 `bash scripts/verify.sh` 判定，且带 `machine_case` 指向真实存在的 `case_`
  2. 判不了 9 条移到 `docs/review-cases.md`，并显式标注「未执行」
  3. README 不再声称 evals 是被执行过的质量证明
  4. 有人把判不了的用例塞回 `evals.json` 时，`verify.sh` 失败
- 未知：无
- 这次不做：不实现「自动跑 agent 并评分」的执行器。那需要引入 agent 调用层，是另一类决定。
- 现有能力：
  - `skills/data-workflow/scripts/check_runner.py` 已有 28 个 case、58 条断言，覆盖安装/门禁/runner —— 已证实
  - `scripts/verify.sh` 是本仓库声明的测试入口，`config.yaml` 的 `verify` 指向它 —— 已证实
  - `evals/evals.json` 无任何消费者（`grep -rn evals.json --include=*.py --include=*.sh` 结果为空）—— 已证实
- 旧决定：`specs/pluggable-skill-pack/decision.md` 第 6 条要求「同步评测」。实现是否仍符合：不符合——文件同步了，但从未被执行，`evals/evals.json` 与 `check_runner.py` 无任何连接。
- 最小充分方案：
  1. 按判据性质拆分：pass 条件要求「读 agent 自然语言回答」的归人工，其余归机器
  2. 机器那 5 条（#5 #6 #12 #13 #14）补齐到 `check_runner.py`：#5 → `case_card_writeback`，#6 → `case_lazy_load`，#12/#13/#14 已有 case
  3. `evals.json` 每条加 `machine_case` 字段指名覆盖它的 case
  4. 新增 `case_evals_are_runnable` 断言：缺 `machine_case`、或指名的 case 不存在 → FAIL
  5. 9 条人工用例写进 `docs/review-cases.md`，带「上次执行 = 未执行」的状态表
- 为什么更小的做法不够：
  - 只改 README 措辞 → `evals.json` 仍是死文件，下一个人仍会以为它在跑
  - 只删 evals.json → 那 9 条人工用例描述的期望行为会丢失，且没有替代位置
  - 只补 case 不拆分 → 判不了的仍混在里面，`verify.sh` 无法执行它们
- 相关的债：A 现在偿还——顺带修掉 `#5`/`#6` 的零覆盖（前者只有 drift 判级、后者完全没有）。
- 风险：不碰契约、持久化、权限、状态、回滚。
