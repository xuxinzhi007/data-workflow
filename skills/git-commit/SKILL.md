---
name: git-commit
description: data-service 提交与 MR。创建分支、写 commit message、提 MR 之前执行：分支名规范、Conventional Commits、中文 title、MR 描述套公司模板。用户说提交、commit、建分支、提 MR 时使用。不用于：审核改动内容（用 data-workflow:change-review）、跑测试（用 data-workflow:quality-gate）、解决合并冲突。
---

# Git 分支、提交与 MR 规范

## 新建分支

从最新的目标分支（默认 `main` 或对应 `release/x.y.z.0`）切出，分支名格式：

```text
<前缀>/<版本号>/<功能>
release/<版本号>

# 示例（以当前版本 26.10.1.0 为例）
feature/26.10.1.0/episode-qc-visibility
fix/26.10.1.0/task-dispatch-retry
hotfix/26.9.4.0/batch-approve-gap-lock
release/26.10.1.0
```

- 版本号为四位：`主版本.次版本.修订号.迭代号`，如 `26.10.1.0`，不带 `v` 前缀
- 版本号必须与当前开发中的 release 分支对应，新功能跟随下一个版本号
- hotfix 使用线上正在运行的版本号
- 功能描述用小写英文单词，中划线分隔，不超过 4 个词

## 分支前缀

| 前缀 | 用途 |
| --- | --- |
| `feature` | 新功能开发 |
| `fix` | 缺陷修复（跟随版本节奏） |
| `hotfix` | 线上紧急修复（对应 hotfix 版本号） |
| `release` | 版本发布分支（仅版本号，不带功能） |

```bash
git fetch origin
git checkout -b feature/26.10.1.0/episode-qc-visibility origin/main
```

## Commit 信息格式

遵循 Conventional Commits 规范：

```text
<type>(<scope>): <描述>

[可选 body]

[可选 footer]
```

## Types

| Type | 用途 |
| --- | --- |
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 仅文档变更 |
| `style` | 代码格式（不影响逻辑） |
| `refactor` | 既非修复也非新功能的代码重构 |
| `perf` | 性能优化 |
| `test` | 新增或修正测试 |
| `build` | 构建系统或外部依赖 |
| `ci` | CI 配置变更 |
| `chore` | 其他维护性工作 |
| `revert` | 回滚之前的提交 |

## 规则

1. 描述使用祈使语气（写「新增 xx 功能」而非「新增了 xx 功能」）
2. 描述结尾不加句号
3. 描述控制在 72 字符以内
4. subject 与 body 之间空一行
5. body 用来说明改动的动机、背景、注意事项，不要复述 diff
6. 提交信息正文使用中文

## Scope

可选。用于标明改动范围，优先使用仓库模块名，如 `api`、`service`、`biz`、`data`、`conf`、`wire`。

## 破坏性变更

在 type/scope 后加 `!`，或在 footer 中加入 `BREAKING CHANGE:`：

```text
feat(api)!: 移除废弃的 /v1/users 接口

BREAKING CHANGE: /v1/users 接口已被删除。
```

## 署名

提交信息中禁止出现任何 AI 署名、co-author 标签或 generated-by footer。

## 提交 MR（glab CLI）

使用 `glab` 创建或编辑 MR，描述必须使用以下模板：

```bash
glab mr create --title "<type>(<scope>): <描述>" --description-file <描述文件>
glab mr update <mr-id> --description-file <描述文件>
```

生成 MR 说明时，先读 `$MR_TEMPLATE`（由 `paths.sh` 解析，见 `data-workflow:data-workflow`），按该文件的章节和字段名填写。`$MR_TEMPLATE` 为空或文件读不到时用下面这份兜底，字段名保持不变，并在 MR 说明里注明「未使用公司模板」。

```markdown
## 变更背景

## 改动内容

- 

## 关联需求/Issue

- 需求文档：
- Jira：

## 关联设计方案

- 

## 测试情况

- 自测文档：
- 自测结论：

## SQL 性能评估

- 预检截图：
- 只读节点试跑耗时：
- 查询数据量：
```

### MR 要求

1. 同一次回复先给 commit 信息，再给填好的 MR 正文。MR 标题与 commit subject 一致。
2. 输出去掉模板里的注释和代码围栏，只留填好的章节。
3. 「变更背景」「改动内容」写这次改动的原因和要点。
4. 没有文档、Jira、设计方案或自测文档时，该字段写「无」。有链接时写成 `[名称](URL)`。不编造链接。
5. 「自测结论」写「通过」或「不通过」，并在该节用一句话说明测了什么。
6. 无 SQL 变更时，「SQL 性能评估」下三项都写「无」。有 SQL 变更时填预检截图、只读节点试跑耗时、查询数据量。
7. 用户只要文案、尚未确认时，不执行 `git commit`、`glab mr create`。确认后再提交。
8. MR 描述更新后用 `glab mr update` 同步。
