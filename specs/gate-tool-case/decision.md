# gate-tool-case 决定

- 级别：L2
- 原话（一字不改）：帮我判断一下 现在的这个项目 在 对于 cursor codex claude deepeek hammer 这些 集成上 是否有帮助 ？ 对于提升的影响 我觉得需要进行测试一下 给出数据的评估
- 我理解你要的是：先测出这套东西在几个 AI 编码平台上到底能不能起作用、能起多少作用，用数据说话；测的过程中发现的集成问题要修掉
- 可能理解错的地方：「deepeek」「hammer」不确定具体指哪两个产品——DeepSeek 有 CLI 但没有 skill 目录约定，Hammer 我没能确认是哪个。我按「用平台目录约定 + 通用 skill 规范」的方式测可测的部分，并把这两个标为不确定。「是否有帮助」也可能是问要不要继续投入，不只是技术可行性。
- 本质：跨平台集成点（skill 目录、门禁 hook、slash 命令）只有一个能验真——门禁。实测发现它在所有平台上都是失效的。
- 怎样算满足：
  1. 五个平台的 skill 副本都能跑 `workflow_next.py`（已实测通过）
  2. 门禁在受保护路径上真的 deny，在普通路径上真的 allow
  3. 各宿主真实工具名（Write/write/Edit/MultiEdit…）都能被门禁识别
  4. 新增断言覆盖大小写差异，断言变红才算真修好
- 未知：`deepeek` / `hammer` 的确切产品形态。不影响本轮修复——修的是 gate 自身的健壮性，与宿主无关。
- 这次不做：不改任何平台的 hook 注册方式（Cursor 之外的平台本来就没有 sessionStart hook）。不做 token 消耗的跨平台对比实验（需要真跑四次 agent 会话，成本高且样本不可控）。
- 现有能力：
  - `install.sh` 支持 `.claude .cursor .qoder .codex .agents` 五个目录 —— 已证实（五平台实测安装成功）
  - `workflow_next.py` 与宿主无关，纯文件 + git 操作 —— 已证实（五平台实测都能 start）
  - `gate_edit.py:targets()` 用原始大小写查小写集合 —— 已证实（这就是缺陷）
- 旧决定：`specs/open-marker/decision.md`。实现是否仍符合：符合，无冲突。
- 最小充分方案：
  1. `targets()` 读到的工具名先 `.lower()` 再查集合
  2. 集合里 `multiEdit` 改成 `multiedit`，补 `strreplaceeditor`
  3. 新增 `case_gate_tool_case`：7 种写法都必须 deny 受保护路径，读工具必须 allow
- 为什么更小的做法不够：
  - 只在文档里写「本技能只在 Cursor 生效」→ 其余四个平台会带着一个坏门到处跑，比没有门更糟：它给人「有保护」的错觉
  - 只改 `targets` 不补测试 → 现有测试全用小写工具名，永远抓不到
- 相关的债：A 现在偿还——这个缺陷让「门禁」这个核心卖点在四个平台上一直是空的，属于最该先修的。
- 风险：不碰契约、持久化、权限、状态、回滚。
