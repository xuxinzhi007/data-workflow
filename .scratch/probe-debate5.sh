set +e
echo "== session-pickup check.md: exit / verify.log =="
grep -n -E "exit|verify\.log" specs/session-pickup/check.md || echo NO_MATCH
echo "--- first 14 lines ---"
sed -n "1,14p" specs/session-pickup/check.md
echo
echo "== first line of every check.md =="
for f in specs/*/check.md; do printf "%-34s | " "$f"; head -1 "$f" | cut -c1-60; done
echo
echo "== workflow distribution =="
grep -h '"workflow"' specs/*/run.json | sort | uniq -c
echo "== feature runs =="
grep -l '"workflow": "feature"' specs/*/run.json 2>/dev/null | wc -l
echo
echo "== evidence.log samples =="
echo "--- g7-runnable ---"; cat specs/g7-runnable/evidence.log 2>/dev/null
echo "--- docs-drift ---"; cat specs/docs-drift/evidence.log 2>/dev/null
echo "--- evidence.log count and lines ---"
find specs -name evidence.log | wc -l
find specs -name evidence.log -exec cat {} + 2>/dev/null | wc -l
echo
echo "== raw_request empties =="
grep -c '"raw_request": ""' specs/*/run.json | grep -v ":0" || echo NONE
echo
echo "== changed_files key in run.json =="
grep -l "changed_files" specs/*/run.json 2>/dev/null | wc -l
echo
echo "== data-service passes.log approved count =="
grep -c "approved" /Users/xuxinzhi/Documents/gowork/data-service/specs/passes.log || true
echo "== data-service hooks.json =="
grep -n "failClosed\|command" /Users/xuxinzhi/Documents/gowork/data-service/.cursor/hooks.json
echo "== install.sh writes =="
grep -n "failClosed" scripts/install.sh
echo "== install.sh recent commits =="
git log --format="%ad %h %s" --date=short -3 -- scripts/install.sh
echo "== hooks.json mtime =="
stat -f "%Sm" -t "%Y-%m-%d %H:%M" /Users/xuxinzhi/Documents/gowork/data-service/.cursor/hooks.json
echo
echo "== count claims =="
grep -n "60 条回归" README.md
grep -n "45+ 条回归" docs/competitive.md
grep -n "43 个" docs/research/debate-adjust-or-overengineered.md | head -3
echo "== actual PASS/FAIL =="
grep -c "^PASS" /tmp/dw-verify.out; grep -c "^FAIL" /tmp/dw-verify.out
echo
echo "== competitive stale lines =="
sed -n "30,45p" docs/competitive.md
echo
echo "== research tracked? =="
git ls-files docs/research | wc -l
echo "== last commit date =="
git log -1 --format="%ad %h %s" --date=short
echo
echo "== verify command in config =="
grep -n "^verify" config.yaml
echo
echo "== all evidence.log file list =="
find specs -name evidence.log | sort