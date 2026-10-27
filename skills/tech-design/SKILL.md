---
name: tech-design
description: data-service 技术方案。把已拍板的一页方案填进公司研发技术方案模板，需要架构图时调 data-workflow:excalidraw-diagram。用户说写技术方案、出个方案文档、tech design 时使用。不用于：需求还没拍板（先 data-workflow:requirement-analysis）、直接写代码（用 data-workflow:implementation）。
---

# Tech Design（技术方案）

把已确认的一页方案填进公司《研发技术方案》模板。本技能不重新做需求分析，也不改一页方案里的决定。

评审阅读一页方案。模板是归档格式。

`$PLUGIN_ROOT` = 本 SKILL.md 往上两级的目录（软链安装时先 `readlink -f`）。模板路径运行时解析，不写死：

```bash
eval "$(bash "$PLUGIN_ROOT/scripts/paths.sh")"   # → $KNOW / $TEMPLATES / $TECH_DESIGN_TEMPLATE
```

路径可能含空格，命令必须引号包裹。`$TECH_DESIGN_TEMPLATE` 为空 → 问用户要模板，不许猜绝对路径、也不许自己发明章节结构。

## 输入要求

- 一页方案已由全局技能 `grilling` 拍板确认。
- 拍板未闭环时回到 `grilling`，不要自己替用户做决定。
- 模板章节只承接一页方案里已有的内容。没有的章节写「无」。

## 回填

1. 打开《研发技术方案》模板：`"$TECH_DESIGN_TEMPLATE"`（路径可能含空格，命令必须引号包裹）。为空或文件不存在 → 问用户要模板路径，不要自己发明章节。
2. 用一页方案填对应章节。接口、数据、风险、发布与回滚写进模板。
3. 一页方案没写到的章节填「无」。
4. 模板开头注明评审正文是一页方案。

## 落点

模板成稿与一页方案放在同一知识库目录（`$KNOW/<相关域>/`），文件名 `<主题>-技术方案.md`。
