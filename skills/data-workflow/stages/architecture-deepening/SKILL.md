# 架构深挖（architecture-deepening）

只看只报，不提出接口、不改代码。产出**一份可视化报告**：当前架构里哪些 module 是浅的、该往哪加深。

和 `change-review` 的分工：那个看「这批改动会不会搞坏东西」，这个看「现有结构本身哪里在摩擦」。两者都能在没改代码时跑。

## 词汇

全程用深 module 的固定词表，不替换成 component / service / API / boundary：

| 词 | 含义 |
|---|---|
| **module** | 有 interface 和 implementation 的东西。函数、类、package、跨层切片都算。 |
| **interface** | 调用方要正确用它必须知道的一切：类型签名、不变量、顺序约束、错误模式、必需配置、性能特征。 |
| **implementation** | module 内部的代码本体。 |
| **depth** | 每单位 interface 能压住多少行为。行为多 interface 小 = **deep**；两者差不多 = **shallow**。 |
| **seam** | 能在不改动此处的前提下改变行为的位置。interface 所在之处。 |
| **adapter** | 在 seam 上满足 interface 的具体实现。说的是**角色**不是内容。 |
| **leverage** | 调用方从 depth 得到的：学一次 interface，到处可用。 |
| **locality** | 维护者从 depth 得到的：改动、bug、验证集中在一处。 |

## A0 圈定范围（先做，不然会漫无目的扫）

**YAGNI 前置。** 加深一个 module 的回报是「以后改它更容易」，所以权重压在**最近真的在改的**地方。

1. 用户点名了方向（某个 module、子系统、痛点）→ 就用它，跳过下面第 2 步。
2. 没点名 → `git log --oneline -40`，再 `git log --pretty=format: --name-only | sort | uniq -c | sort -rn | head -25` 找热点。改动集中在少数文件就顺着它们走；散得没热点就放宽范围。
3. 先读 `GLOSSARY.md` 和 `docs/adr/` 里涉及这块的内容。没有这两个文件就跳过，不要现编。
4. 范围写进报告头。**明确不扫的东西也写上** —— 防止下一轮重复提议已经被否掉的。

## A1 走查（子 agent 并行，只读）

至少派两个子 agent，各自一个角度，都只读、都写各自的 finding 文件：

| 轴 | 问题 |
|---|---|
| 结构 | 理解一个概念要不要在好几个小 module 之间跳？哪里的 interface 快赶上 implementation 大了？ |
| 调用 | 为了可测而抽出来的纯函数，真实 bug 是不是藏在「怎么被调用」上（缺 locality）？哪两个紧耦合的 module 从一个 seam 的两侧漏到对方？ |

两边都做 **deletion test**：把这个 module 删掉，复杂度是消失（说明它是 pass-through），还是在 N 个调用方重新长出来（说明它在挣饭钱）？

**「是的，会集中」就是你要的信号。**

## A2 出报告

**落点在本工作流的 `artifacts_root`，不写进被审仓库以外的位置。**

报告格式、图表模式、配色见 `$PLUGIN_ROOT/stages/architecture-deepening/references/report.md`。要点：

- HTML 自包含单文件，Tailwind + Mermaid 走 CDN。**落在仓库里，不要写 OS 临时目录** —— 临时目录会被清理，`git status` 也看不见。
- Mermaid 画图状关系（调用图、依赖、时序）；手搓 div / SVG 画更编辑性的东西（体量对比、剖面、折叠）。
- 每个候选一张卡片：**Files / Problem / Solution / Wins / before-after 图 / 推荐强度徽章**。
- 推荐强度三档：`Strong`（emerald）/ `Worth exploring`（amber）/ `Speculative`（slate）。
- Wins 用 depth 的词写：*"locality: bug 集中在一处"*、*"leverage: 一个 interface 服务 N 个调用方"*。**不要写「更易维护」「更干净」** —— 不在词表里，也没挣到位置。
- 结尾一个 Top recommendation：先做哪个、为什么。

**同时落一份 `README.md` 摘要**（纯文本）。HTML 依赖 CDN，命令行和离线不好读；摘要里放候选清单、注入路径/调用路径矩阵、建议顺序、待拍板项。开发时读摘要就够，不用开浏览器。

**这一步不提接口。** 报告只指方向。

## A3 停下来问

报告写完就停。打一句：**「这几个你想先展开哪个？」**

不要自己往下选。用户点了之后才进 grilling —— 那时才谈 interface、seam 位置、什么留在 seam 后面、哪些测试能活下来。

## 常见错法

- **直接扫整个仓库。** 先跑 `git log` 找热点，或让用户指方向。没圈范围就开扫，出来的是通用架构建议，不是这个仓库的。
- **把「浅」当成「小」。** 小但 deep 的 module 是好东西。判据是 interface 压不压得住 implementation，不是行数。
- **跳过 deletion test。** 不做就去提「这个抽象该收拢」，很可能它本来就在挣饭钱，删了复杂度会散到 N 个调用方。
- **顺手提接口。** A2 只出方向。一旦写起 `Select(agent) []Note` 这种签名，就已经在做 A3 的事了，而且用户没点头。
- **报告落在 `/tmp`。** 临时目录会被清理，`git status` 也看不见。落 `artifacts_root`。
- **只出 HTML。** 依赖 CDN，命令行和离线读不了。总配一份 `README.md` 纯文本摘要。
- **词表漂移。** 写成 component / service / API / boundary，读者就失去了「谁 shallow、seam 在哪」的共同语言，报告退化成印象派。
- **把 ADR 禁的项全列一遍。** 只在摩擦真够大时 reopen，并写清为什么够大。

## 硬规则

- **不改业务代码。** 只读源码、`git log`、`git diff`。用户明确要求改时才切到 `change` / `feature`。
- **不提接口。** A2 只出候选和方向。interface 设计是 A3 之后的事。
- **不重复提已被否掉的。** 被拒的候选，如果理由是「以后还会有人再提一遍」那种，提议记一条 ADR，别每轮重新吵。
- **词表不漂。** 说 module / interface / depth / seam / adapter / leverage / locality，不说 component / service / API / boundary。
- **ADR 冲突只在摩擦真够大时才报。** 不要列全所有被 ADR 禁掉的理论重构。真够大时卡片上标一个 amber callout：*"与 ADR-0007 冲突，但值得重开，因为…"*。
- **候选要能指到 `文件:符号`。** 指不到的就是猜，写「待确认」或删掉。
