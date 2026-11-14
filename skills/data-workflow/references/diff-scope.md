# 圈定 diff 范围

改动审核（A0）与质量门禁（G0）共用本规则。后续检查只锚定这份清单，不扩大到全项目。

## 步骤

1. `git status --short` + `git diff` 拿未提交改动；用户指定了 commit 范围（如 `HEAD~1..HEAD`）就按指定范围；两者都没有则问用户要范围，不猜。
2. 产出两份清单：
   - **改动文件清单**：按语言 / 契约 / 配置 / SQL / 文档分类。
   - **改动符号清单**：函数、方法、结构体字段、契约字段、查询条件、配置项。
3. **审查与验证范围只到清单为止。** 清单外的既有问题最多顺带记几行，不展开、不阻塞、不要求本次修。
4. 纯文档、纯注释、纯问答、未改代码 → 直接回「无需审核 / 无需门禁」，不硬凑报告。

## 嵌入与加载的配置算逻辑改动

被编译进二进制、或运行时加载进业务逻辑的配置 / 资源文件，算**逻辑相关改动**，不得因为「看起来像配置」就跳过测试或覆盖率。具体哪些路径算嵌入，看当前 profile（Go 实例见 `profiles/go-kratos/profile.md`）。

## 共享 diff 与指纹（审核用）

三轴审核要读同一份落盘 diff，不许各拉各的。落点默认 `$REPO/specs/<feature>/`。`review-only` 审别人的工作树时，改用该工作流的 `artifacts_root`（`$CARDS/reviews/<feature>/`），下面命令里的 `specs/<feature>` 换成那个目录，不写进对方仓库。

```bash
mkdir -p specs/<feature>/review
git diff <范围> > specs/<feature>/diff.patch
printf 'review 指纹: base=%s head=%s files=%s lines=%s\n' \
  "$(git rev-parse --short <base>)" "$(git rev-parse --short HEAD)" \
  "$(git diff --name-only <范围> | wc -l | tr -d ' ')" \
  "$(wc -l < specs/<feature>/diff.patch | tr -d ' ')"
```

指纹写进报告头。**被审 diff 变了，旧报告即 STALE**（新 commit，或新的未提交业务改动）。写入评审工件不算。结论不再成立时必须重跑（至少重跑受影响的那一轴），不许拿旧报告当通过凭证。
