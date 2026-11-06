set +e
echo "== verify run =="
bash scripts/verify.sh > /tmp/dw-verify.out 2>&1; echo "VERIFY_EXIT=$?"
tail -6 /tmp/dw-verify.out
echo
echo "== sizes =="
wc -l skills/data-workflow/scripts/check_runner.py skills/data-workflow/scripts/workflow_next.py skills/data-workflow/hooks/gate_edit.py
echo
echo "== workflow requires =="
python3 -c "import json,glob,os;
for f in sorted(glob.glob('skills/data-workflow/workflows/*.json')):
    w=json.load(open(f));
    print(os.path.basename(f), 'stages=', len(w['stages']), 'requires=', sum(len(s.get('requires',[])) for s in w['stages']))"
echo
echo "== data-service usage =="
DS="/Users/xuxinzhi/Documents/gowork/data-service"
ls -d "$DS/specs"/*/ 2>/dev/null | wc -l
find "$DS/specs" -name run.json 2>/dev/null | wc -l
find "$DS/specs" -name passes.log 2>/dev/null | wc -l
find "$DS/specs" -name evidence.log 2>/dev/null | wc -l
grep -h status "$DS"/specs/*/run.json 2>/dev/null | sort | uniq -c
echo "-- protected_paths --"
grep -A2 protected_paths "$DS/.cursor/skills/data-workflow/config.yaml" 2>/dev/null
echo
echo "== claim register =="
grep -c "| 待确认" docs/claim-register.md
grep -c "| 已证实" docs/claim-register.md
echo
echo "== evals machine cases vs case_ functions =="
grep -c "def case_" skills/data-workflow/scripts/check_runner.py
grep -o "case_[a-z_0-9]*" evals/evals.json | sort -u | wc -l
echo
echo "== review cases =="
grep -c "^## #" docs/review-cases.md
echo
echo "== stage files reachable =="
python3 -c "import json,glob;
fs=set()
for f in glob.glob('skills/data-workflow/workflows/*.json'):
    w=json.load(open(f));
    for s in w['stages']:
        if s.get('file'): fs.add(s['file'])
print(len(fs));
print(chr(10).join(sorted(fs)))"
echo
echo "== stage files on disk =="
find skills/data-workflow/stages -name "SKILL.md" | wc -l
echo
echo "== git status =="
git status --short