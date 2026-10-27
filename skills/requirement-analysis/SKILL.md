---
name: requirement-analysis
description: data-service 需求分析。把模糊需求问成可实现的口径：读知识库建立现状、grilling 逼用户拍板、输出一页方案与 spec。用户说需求分析、这个需求怎么做、帮我拆一下需求、写个 spec 时使用。不用于：已经拍板只等写代码（用 data-workflow:implementation）、纯技术选型文档（用 data-workflow:tech-design）、排查线上问题（用 data-workflow:oncall）。
---

# Requirement Analysis

用于编码前分析需求。目标不是写长方案，而是把“到底要改什么、复用什么、不做什么”讲清楚。

## 先看口径

分析前先按需查这些来源，不要只凭需求文字猜：

- `api/**/*.proto`：接口和字段事实来源。
- `docs/API`：HTTP 入参、出参、前端使用口径。
- `docs/architecture`：跨模块流程和架构约束。
- `internal/service`：参数校验、协议适配、错误转换。
- `internal/biz`：业务规则、编排、Repo 接口。
- `internal/data`：DB 查询、外部依赖适配。
- `configs/tag/system_tags.json`：系统标签、枚举类业务配置。

如果需求涉及 Go 实现，后续编码前再读 `data-workflow:implementation` 的 `references/go-style.md` 与 `data-workflow:implementation`；完成 Go 改动前读 `data-workflow:implementation` 的 `references/reuse-gate.md`。拍板用 全局技能 `grilling`。一页方案确认后再读 `data-workflow:tech-design` 填公司模板。

## 分析步骤

1. 判定需求归属  
   先说明这是新能力、已有能力扩展、筛选条件、状态流转、数据修正、权限控制，还是展示字段补齐。

2. 找现有能力  
   搜 proto、docs、service/biz/data 中是否已有字段、RPC、状态、标签、Repo 方法、查询条件。能复用就明确写“复用现有”；不能复用再说明缺口。

3. 收窄本质  
   用一句话写清楚本质，避免被需求名词带偏。  
   示例：本质不是新增审批系统，而是在现有任务列表上增加一个按审批状态过滤的入口。

4. 判断是否需要新增  
   逐项判断是否需要新增字段、RPC、表字段、配置、索引、状态、错误码、文档。  
   新增表或字段前必须解释为什么现有能力解决不了。

5. 拆接口变更  
   只写核心字段和兼容性影响。接口变更先落到 `api/<module>/v1/*.proto`，不要从 service 或 data 层倒推。

6. 拆后端流程  
   按 `service → biz → data` 写 3-6 步。  
   service 只做校验和协议适配；biz 写规则和编排；data 只做持久化、筛选、排序、分页、聚合。

7. 查影响面  
   覆盖调用方、默认行为、历史数据、分页排序、权限、错误码、文档、生成文件、测试。  
   高频 SQL 或大表路径要说明索引与查询收窄方式。

8. 标出待拍板点  
   只列真正会影响行为、成本或兼容性的决策；不要把实现细节伪装成待确认问题。

9. 拷问拍板点（全局技能 `grilling`，需要时把知识库文档路径一起给它）  
   标出待拍板点后读 全局技能 `grilling` 并执行：
   - 一次只问一个问题，按依赖顺序走决策树，每问附推荐答案。
   - 能从代码、文档查到的先核对再问。用户说法与代码不一致时，先指出差异。
   - 术语在决定时写入仓库 `CONTEXT.md`。
   - 待拍板清零后，写一页方案：结论在前，只含已确认的决定。这是评审正文。

## 输出格式

按 `.cursor/rules/data-service.mdc` 的「方案写法」输出，保持一屏内。需求很小时压缩为：核心结论、本质、改动范围、待确认。

## 判断规则

- 能加筛选就不要新增流程。
- 能复用状态就不要新增枚举。
- 能复用主表字段就不要新增关联表。
- 能在 biz 组合就不要把业务规则塞进 SQL。
- 能批量查询就不要 N+1。
- 不为了未来扩展加灰度、开关、中间层或配置。
- 不把另一个历史方案默认纳入当前需求；范围不清时先问。

## 质量检查

输出前自查：

- 是否引用了项目事实来源，而不是凭空设计。
- 是否说明“新增”和“不新增”。
- 是否遵守 `service → biz → data` 分层。
- 是否指出 API 文档和 proto 是否需要同步。
- 是否把 SQL、索引、分页、权限、历史数据影响说清楚。
- 是否只保留真正需要用户拍板的问题。
