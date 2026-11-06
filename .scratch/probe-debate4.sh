set +e
echo "== install.sh hook writing =="
grep -n -E "failClosed|hooks\.json|gate-edit" scripts/install.sh | head -40
echo
echo "== knowledge_drift size =="
wc -l skills/data-workflow/scripts/knowledge_drift.sh
echo
echo "== per-run artifacts =="
for d in specs/*/; do
  n=$(basename "$d")
  rr=$(python3 -c "import json;d=json.load(open('$d/run.json'));print(len((d.get('raw_request') or '').strip()))" 2>/dev/null)
  ev=$(wc -l < "$d/evidence.log" 2>/dev/null || echo 0)
  vl=$(head -1 "$d/verify.log" 2>/dev/null | tr -d "\n" | cut -c1-24)
  ck=$(head -1 "$d/check.md" 2>/dev/null | tr -d "\n" | cut -c1-32)
  printf "%-28s raw=%-4s ev=%-3s verify=[%s] check=[%s]\n" "$n" "${rr:-ERR}" "${ev:-0}" "$vl" "$ck"
done
echo
echo "== artifact presence counts =="
for f in run.json decision.md check.md verify.log evidence.log change-note.md; do
  c=$(find specs -maxdepth 2 -name "$f" | wc -l | tr -d " ")
  echo "$f: $c/19"
done
echo
echo "== md lines by area =="
for d in . docs skills specs; do
  if [ "$d" = "." ]; then
    files=$(find . -maxdepth 1 -name "*.md")
  else
    files=$(find "$d" -name "*.md")
  fi
  lines=$(echo "$files" | xargs cat 2>/dev/null | wc -l | tr -d " ")
  cnt=$(echo "$files" | wc -l | tr -d " ")
  echo "$d: $cnt files, $lines lines"
done
echo
echo "== tracked vs untracked research =="
git ls-files docs/research | wc -l
git status --short docs/research
echo
echo "== commits: meta vs business =="
git log --format="%h %s" | head -35