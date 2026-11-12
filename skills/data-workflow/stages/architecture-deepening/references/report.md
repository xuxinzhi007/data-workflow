# 报告格式

单文件 HTML，落 `artifacts_root`（不是 OS 临时目录）。Tailwind 和 Mermaid 走 CDN。
Mermaid 管图状关系；手搓 div / SVG 管更编辑性的视觉。**别全用 Mermaid，会看着很通用。**

## 骨架

```html
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<title>架构评审 · {{主题}}</title>
<script src="https://cdn.tailwindcss.com"></script>
<script type="module">
  import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
  mermaid.initialize({ startOnLoad: true, theme: "neutral", securityLevel: "loose" });
</script>
<style>
  .seam { stroke-dasharray: 5 5; }
  .leak { stroke: #dc2626; stroke-width: 2; }
  .ghost { opacity: .38; }
  .lbl { font-size: 10px; letter-spacing: .14em; text-transform: uppercase; }
  .deepfill { background: linear-gradient(135deg,#0f172a,#1e293b); }
</style>
</head>
<body class="bg-stone-50 text-slate-900">
<main class="max-w-6xl mx-auto px-8 py-14 space-y-14">
  <header>…</header>
  <section id="candidates" class="space-y-12">…</section>
  <section id="top-recommendation">…</section>
</main>
</body>
</html>
```

## 头部

仓库名、日期、一条紧凑图例：实线框 = module，虚线 = seam，红箭头 = leakage，深色粗框 = deep module。
**不写导语段落**，直接进候选。

## 候选卡片

图挑大梁，文字尽量少。每张一个 `<article>`：

- **标题**：短的，点名要加深的是什么
- **徽章行**：推荐强度（`Strong` emerald / `Worth exploring` amber / `Speculative` slate）+ 依赖类别标签
- **Files**：`font-mono text-sm`
- **before / after 图**：中心件，左右两栏
- **Problem**：一句。疼在哪
- **Solution**：一句。改什么
- **Wins**：项目符号，每条 ≤10 字，用 depth 的词
- **ADR callout**（若有）：一行 amber

不要成段解释。**图要靠一段话才看得懂，就重画图。**

## 图模式

按候选挑，混着用，别每张都长一样。

### Mermaid 图（依赖 / 调用流的工作马）

```html
<div class="rounded-lg border border-slate-200 bg-white p-4">
  <pre class="mermaid">
flowchart LR
  A[Handler] --> B[Validator]
  B --> C[Repo]
  C -.leak.-> D[外部 client]
  classDef leak stroke:#dc2626,stroke-width:2px;
  class C,D leak
  </pre>
</div>
```

### 手搓框和箭头（Mermaid 排版不听话时）

module 用带边框的 `<div>`，箭头用绝对定位在 `relative` 容器上的内联 SVG `<line>`/`<path>`。
**after 图要让人看出一整块厚边框的 deep module、里面灰掉的内部件** —— Mermaid 给不了这个分量感。

### 剖面（适合层层浅）

横条堆叠（`h-12 border-l-4`），展示一次调用穿过的层。before：6 层薄带各干一点事。after：1 条厚带。

### 体量图（适合 "interface 和 implementation 一样宽"）

每个 module 两个矩形：一个量 interface 表面积，一个量 implementation。
before：两边几乎一样高（shallow）。after：interface 矮、implementation 高（deep）。

### 调用图折叠

before：调用树画成嵌套框。after：同一棵树折成一个框，内部调用灰掉放里面。

## 配色

编辑感，不是仪表盘。留白慷慨。标题可用 `font-serif` 配 stone / slate。
颜色克制：一个强调色（emerald 或 indigo）+ 红色标泄漏 + amber 标警告。
图高约 320px，左右并排不用滚。图内 module 标签用 `text-xs uppercase tracking-wider`，读起来像示意图不像 UI。
脚本只有 Tailwind CDN 和 Mermaid ESM import，其余静态。

## Top recommendation

一张大卡片：候选名、一句为什么、锚点链接回卡片。就这些。

## 顺带产出的 README.md

同目录一份纯文本摘要，因为 HTML 依赖 CDN，命令行和离线读不了：

```markdown
# 架构评审

| 报告 | 主题 | 状态 |
|---|---|---|
| [`xxx.html`](xxx.html) | … | 提案，待决策 |

## 直接读纯文本
（候选清单、注入/调用路径矩阵、建议顺序、待拍板项）

## 重新生成
```

状态写成「提案，待决策」。**报告里的候选一旦落地，结论移进 `docs/design.md`，这里只做历史存档。**

## 语气

平、简，但名词和动词直接来自词表。**简洁不是跑偏的借口。**

用：module · interface · implementation · depth · deep · shallow · seam · adapter · leverage · locality

不用：component / service / unit（代替 module）· API / signature（代替 interface）· boundary（代替 seam）

合适的句子长这样：

- "Order intake module is shallow: interface nearly matches the implementation."
- "Pricing leaks across the seam."
- "Deepen: one interface, one place to test."
- "两个 adapter 让这条 seam 成立：生产用 HTTP，测试用内存。"

Wins 用词表写：*"locality: bug 集中在一个 module"*、*"leverage: 一个 interface，N 个调用方"*。

不写「更易维护」「更干净」—— 不在词表里，也没挣到位置。

不铺垫、不"值得注意的是"、不"整体还行"。**一句能变成项目符号就变成项目符号。一个项目符号能删就删。**
词表里没有的词，先去找词表里的，别急着新造。
