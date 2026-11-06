
import os, glob, json, subprocess, hashlib

def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return (r.stdout or '') + (r.stderr or '')

print("== knowledge_drift states ==")
t = open('skills/data-workflow/scripts/knowledge_drift.sh', encoding='utf-8').read()
for s in ['FRESH','STALE','SUPERSEDED','CONFLICT']:
    print(s, t.count(s))

print()
print("== session-start ==")
print(open('skills/data-workflow/hooks/session-start', encoding='utf-8').read())

print()
print("== run_verify in workflow_next.py ==")
lines = open('skills/data-workflow/scripts/workflow_next.py', encoding='utf-8').read().splitlines()
for i,l in enumerate(lines):
    if 'def run_verify' in l:
        start=i
        break
else:
    start=None
print('start line', start)
if start is not None:
    for l in lines[start:start+70]:
        print(l)

print()
print("== detection order strings ==")
t2 = open('skills/data-workflow/scripts/workflow_next.py', encoding='utf-8').read()
for key in ['package.json','Makefile','pytest','cargo','go test','verify']:
    print(key, t2.count(key))

print()
print("== one run.json full ==")
d = json.load(open('specs/intent-confirm/run.json'))
print(d)

print()
print("== intent-confirm check.md first 12 lines ==")
print('\n'.join(open('specs/intent-confirm/check.md', encoding='utf-8').read().splitlines()[:12]))

print()
print("== installed copy hashes vs source ==")
ds = '/Users/xuxinzhi/Documents/gowork/data-service'
pairs = [
 ('skills/data-workflow/scripts/workflow_next.py', ds+'/.cursor/skills/data-workflow/scripts/workflow_next.py'),
 ('skills/data-workflow/scripts/check_runner.py', ds+'/.cursor/skills/data-workflow/scripts/check_runner.py'),
 ('skills/data-workflow/hooks/gate_edit.py', ds+'/.cursor/skills/data-workflow/hooks/gate_edit.py'),
 ('skills/data-workflow/workflows/feature.json', ds+'/.cursor/skills/data-workflow/workflows/feature.json'),
]
for a,b in pairs:
    ha = hashlib.sha256(open(a,'rb').read()).hexdigest()[:12] if os.path.exists(a) else 'MISSING'
    hb = hashlib.sha256(open(b,'rb').read()).hexdigest()[:12] if os.path.exists(b) else 'MISSING'
    print(os.path.basename(a), 'src', ha, 'installed', hb, 'SAME' if ha==hb else 'DIFF')

print()
print("== installed workflow_next supports knowledge_feedback? ==")
for p in [ds+'/.cursor/skills/data-workflow/scripts/workflow_next.py', 'skills/data-workflow/scripts/workflow_next.py']:
    if os.path.exists(p):
        t = open(p, encoding='utf-8').read()
        print(p, 'knowledge_feedback' in t, 'G7' in t)

print()
print("== installed feature.json stage6 ==")
p = ds+'/.cursor/skills/data-workflow/workflows/feature.json'
if os.path.exists(p):
    w = json.load(open(p))
    print(json.dumps(w['stages'][5], ensure_ascii=False, indent=1))
else:
    print('missing')

print()
print("== data-service .agents/.qoder installed? ==")
for tool in ['.cursor','.qoder','.agents']:
    p = ds+'/'+tool+'/skills/data-workflow'
    print(tool, os.path.isdir(p), len(glob.glob(p+'/**', recursive=True)) if os.path.isdir(p) else 0)

print()
print("== docs/domain / GLOSSARY ==")
for base in ['.', ds]:
    print(base, 'docs/domain', os.path.isdir(base+'/docs/domain'), 'GLOSSARY.md', os.path.exists(base+'/GLOSSARY.md'))

print()
print("== open questions: any run created after install? ==")
for f in sorted(glob.glob('specs/*/run.json')):
    d = json.load(open(f))
    print(os.path.basename(os.path.dirname(f)), d.get('status'), d.get('stage'))
