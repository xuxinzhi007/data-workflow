# data-workflow

data-service 的完整开发工作流，作为一个独立可 git 管理的 Qoder 插件。

## 设计原则

**技能只装流程，业务事实运行时读取。**

判断一句话该放哪，用易变性测试：*明天一个代码 commit 能否让这句话变成假的，而不需要任何人编辑它所在的文件？*

- 能 → **事实**，放知识层，带 `verified_commit` + `watches`
- 不能 → **流程**，放技能

推论：指针是流程，取值是事实。绝不存「假了也没声音」的事实。

| 层 | 位置 | 内容 |
|---|---|---|
| L0 编排器 | `skills/data-workflow/` | 选型、顺序、门禁。零事实 |
| L1 步骤技能 | `skills/<stage>/` | 每个阶段的流程，SKILL.md ≤ 200 行，细节进 `references/` |
| L2 知识层 | Obsidian `xxz_obsidian/knowledge/**`、`开发规范化/**` | 业务事实、公司模板 |
| L3 权威 | 代码、生成物、聚焦测试 | 永不上抄 |

仓库内 `docs/`、`docs/support/` 是**降级区**：已被证实在 MQTT 推送链路与 Episode 终态上说谎，只可当搜索线索。

## 技能

| 技能 | 作用 |
|---|---|
| `data-workflow:data-workflow` | 入口。环境探测 → 查重 → 选型 → 串联 → 门禁 |
| `data-workflow:requirement-analysis` | 需求分析，拍板走全局技能 `grilling` |
| `data-workflow:tech-design` | 技术方案，套 Obsidian 公司模板 |
| `data-workflow:implementation` | 编码实现 + Go 规范 + 复用门禁 |
| `data-workflow:change-review` | 改动风险审核 + 规范与需求符合性 |
| `data-workflow:quality-gate` | 用命令输出证明可提交 |
| `data-workflow:git-commit` | 分支名、commit、MR |
| `data-workflow:oncall` | 线上排查，只读，状态族隔离 |
| `data-workflow:excalidraw-diagram` | 架构图，产 `.excalidraw` + `.svg` + `.png` |

技能之间只用命名空间名互相调用，不写绝对路径。

## 安装

```bash
qoder plugins install ~/skills/data-workflow --scope user
```

## 脚本

| 脚本 | 作用 |
|---|---|
| `scripts/repo_snapshot.sh` | 记录被测仓库的 branch / commit / dirty 状态 |
| `scripts/knowledge_drift.sh` | 知识新鲜度门禁。读 frontmatter 的 `verified_commit` 与 `watches`，比对 data-service HEAD，输出 FRESH / STALE / SKIP |

门禁**只标注、不阻塞**：恒 exit 0，exit 2 仅表示文档无法解析。缺 frontmatter 按 STALE 处理，让未纳管的文档自我暴露。

被测仓库优先级：`$DS_REPO` > 当前目录所在仓库 > `~/Documents/gowork/data-service`。

## 知识落点

| 落点 | 归属 |
|---|---|
| Obsidian `knowledge/<域>/` | 已稳定的领域知识 |
| Obsidian `knowledge/排查卡片/` | oncall 调查结论，按症状词检索 |
| Obsidian `开发规范化/` | 公司模板（技术方案、MR） |
| 仓库 `.cursor/plans/` | 决策前的工作记忆，临时 |
