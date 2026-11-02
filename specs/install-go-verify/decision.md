# install-go-verify 决定

- 级别：L1
- 原话（一字不改）：进行修复吧 ，
- 我理解你要的是：修在 `system_tags_editor` 实战里暴露的两个技能自身问题——① 新仓库没有工具目录时 `--project` 直接拒绝；② `RED / verify 未配置` 不给补救办法，且 Go 项目要手配
- 可能理解错的地方：「进行修复吧」可能指修复实战报告里提到的全部问题（含 231 行拆行边界差）。我按那两个「技能自身」的问题做——拆行边界差是被测项目的缺陷，不是技能的，且改动会改变所有用户的保存输出，需要单独决定。
- 本质：安装入口把「目标工具已初始化」当前提，而新项目往往没有；测试入口探测漏了 Go，且失败提示只报错不给路。
- 怎样算满足：
  1. 仓库没有任何工具目录时，`--project` / `--with-hooks` 自动建一个 Cursor 的，不拒绝
  2. `go.mod` 存在时自动用 `go test ./...`，不需要手配 verify
  3. 真的没有测试入口时，RED 提示写明「在 config.yaml 写 verify」和它会自动探测哪些文件
  4. 新增断言覆盖三条，且破坏实现时断言变红
- 未知：无
- 这次不做：不修 `system_tags_editor` 的拆行边界差（那是被测项目的事）。不改 `--global` 的既有行为。
- 现有能力：
  - `install.sh` 的 `dirs` 为空时，只有 `--global` 且无 target 才自建目录，其余一律 `NOTHING` 退出 —— 已证实（实战踩到）
  - `declared_verify` 支持 package.json / Makefile(test:) / pytest / Cargo.toml，**没有 Go** —— 已证实（实战中只能手配 `go build ./... && go test ./...`）
  - `run_verify` 未配置时只打印 `RED` + `verify 未配置` —— 已证实
- 旧决定：无。
- 最小充分方案：
  1. `install.sh`：把自建 `.cursor/skills` 的条件从「仅 `--global` 无 target」扩到「`--project` / `--with-hooks` 也算」，并打印 `CREATE` 说明
  2. `workflow_next.py:declared_verify` 加 `go.mod` → `go test ./...`
  3. `run_verify` 的 RED 分支改成四行：现象、去哪配、会自动探测哪些文件、示例命令
  4. `check_runner.py`：重写 `case_gomod`（原断言「go.mod stays RED」已过时），新增 `case_install_makes_tool_dir`，扩展 `case_none` 覆盖提示内容
- 为什么更小的做法不够：
  - 只改 install 不改 verify → Go 项目仍要手配，实战里就是这一步卡了两次
  - 只加 go.mod 探测不改提示 → 非 Go 且无测试入口的项目仍只看到「verify 未配置」
  - 不改 `case_gomod` 的旧断言 → 它会变红，但不是因为实现错，是因为断言过时——必须先更新断言再改实现，否则分不清哪边错了
- 相关的债：A 现在偿还。这两条都是实战直接撞到的，不修下次换项目还会撞。
- 风险：不碰契约、持久化语义、权限、状态、回滚。`go.mod` 探测只在没有显式 `verify` 且没有 package.json/Makefile/pytest/Cargo 时才生效，不覆盖已有配置。
