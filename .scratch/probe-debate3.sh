echo "== claim register line numbers =="
grep -n -E "^\| C[1-8] |^\| V[0-9]+ |^\| 断言" docs/claim-register.md
echo "== competitive key lines =="
grep -n -E "hook 坏了|多 agent|知识落点|门是字面量|生态规模|三个真的差异点|真不如人|45\+" docs/competitive.md
echo "== data-service .cursor =="
ls -la /Users/xuxinzhi/Documents/gowork/data-service/.cursor/ 2>/dev/null
cat /Users/xuxinzhi/Documents/gowork/data-service/.cursor/hooks.json 2>/dev/null || echo NO_HOOKS_JSON
echo "== data-service specs files =="
find /Users/xuxinzhi/Documents/gowork/data-service/specs -maxdepth 3 -type f -print 2>/dev/null
echo "== verify.log head =="
head -8 /Users/xuxinzhi/Documents/gowork/data-service/specs/dispatch-remove-office-option/verify.log 2>/dev/null
echo "== passes.log =="
cat /Users/xuxinzhi/Documents/gowork/data-service/specs/passes.log 2>/dev/null
echo "== data-service status =="
git -C /Users/xuxinzhi/Documents/gowork/data-service status --short 2>/dev/null
git -C /Users/xuxinzhi/Documents/gowork/data-service diff --stat 2>/dev/null
echo "== job_export diff head =="
git -C /Users/xuxinzhi/Documents/gowork/data-service diff -- internal/biz/job_export.go 2>/dev/null | head -60
echo "== edit-gate =="
sed -n "1,180p" skills/data-workflow/references/edit-gate.md
echo "== README key lines =="
grep -n -E "写入门禁|完成证据|60 条|三种模式|默认" README.md | head -30
echo "== research doc scale claims =="
grep -n -E "74 个 md|4322|43 个|24 个|过度|门比活多" docs/research/debate-adjust-or-overengineered.md
echo "== actual scale =="
find . -name "*.md" -not -path "./.git/*" | wc -l
find . -name "*.md" -not -path "./.git/*" -exec cat {} + | wc -l
find . \( -name "*.py" -o -name "*.sh" -o -name "*.js" \) -not -path "./.git/*" -exec cat {} + | wc -l