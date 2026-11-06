set +e
DS="/Users/xuxinzhi/Documents/gowork/data-service"
echo "== DS specs tree =="
find "$DS/specs" -maxdepth 3 -type f 2>/dev/null | head -80
echo
echo "== DS specs dirs =="
for d in "$DS"/specs/*/; do
  echo "--- $d"
  ls -la "$d" 2>/dev/null | head -20
done
echo
echo "== DS passes.log =="
find "$DS/specs" -name passes.log -exec sh -c 'echo "FILE: $1"; cat "$1"' _ {} \; 2>/dev/null
echo
echo "== DS run.json / evidence.log anywhere =="
find "$DS" -name run.json -not -path "*/.git/*" 2>/dev/null | head -20
find "$DS" -name evidence.log -not -path "*/.git/*" 2>/dev/null | head -20
echo
echo "== DS git =="
git -C "$DS" log --oneline -8 2>/dev/null
git -C "$DS" status --short 2>/dev/null | head -20
echo
echo "== DS configs =="
for f in "$DS"/.cursor/skills/data-workflow/config.yaml "$DS"/.qoder/skills/data-workflow/config.yaml "$DS"/.agents/skills/data-workflow/config.yaml; do
  echo "--- $f"
  grep -E 'protected_paths|waiver_globs|verify|repo|knowledge_root|artifacts_root' "$f" 2>/dev/null
done
echo
echo "== DS specs ignored? =="
grep -n "specs" "$DS/.gitignore" 2>/dev/null
echo
echo "== PASS count =="
grep -c '^PASS' /tmp/dw-verify.out
grep -c '^FAIL' /tmp/dw-verify.out
echo
echo "== skill repo spec runs summary =="
python3 - <<'PY'
import json,glob,os
for f in sorted(glob.glob('specs/*/run.json')):
    try:
        d=json.load(open(f))
        print(os.path.basename(os.path.dirname(f)), '|', d.get('workflow'), '| stage', d.get('stage'), '|', d.get('status'), '|', (d.get('raw_request') or '')[:70].replace(chr(10),' '))
    except Exception as e:
        print(f, 'ERR', e)
PY
echo
echo "== docs/research =="
git ls-files docs/research | wc -l
ls -la docs/research
echo
echo "== README/competitive/claim numbers =="
grep -n "60 条\|45+\|43 个\|24 个\|116\|74 个\|4322\|5035" README.md docs/competitive.md docs/claim-register.md docs/research/debate-adjust-or-overengineered.md | head -30
echo
echo "== last 12 commits with stats =="
git log --oneline -12 --stat | head -120
