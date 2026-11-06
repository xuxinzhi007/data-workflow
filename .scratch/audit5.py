
import os, glob, subprocess, json

DS = '/Users/xuxinzhi/Documents/gowork/data-service'

def sh(cmd, cwd=None):
    r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return (r.stdout or '') + (r.stderr or '')

print("== installed hooks dir ==")
h = DS + '/.cursor/skills/data-workflow/hooks'
for p in sorted(glob.glob(h + '/*')):
    print(os.path.basename(p), os.path.getsize(p))
print('gate_edit.py anywhere in installed skill:')
print(sh("find " + DS + "/.cursor/skills/data-workflow -name 'gate_edit.py' -o -name 'gate-edit*'"))

print()
print("== installed gate-edit head ==")
p = h + '/gate-edit'
if os.path.exists(p):
    print(open(p, encoding='utf-8').read()[:800])
else:
    print('MISSING')

print()
print("== installed origin / version ==")
for p in [DS + '/.cursor/skills/data-workflow/origin', DS + '/.cursor/skills/data-workflow/.origin']:
    print(p, os.path.exists(p), open(p).read().strip() if os.path.exists(p) else '')

print()
print("== workflow_next references knowledge_drift? ==")
t = open('skills/data-workflow/scripts/workflow_next.py', encoding='utf-8').read()
print('knowledge_drift' in t, 'knowledge_feedback' in t)
print('drift lines:', [l for l in t.splitlines() if 'drift' in l.lower()][:5])

print()
print("== next in data-service (source runner) ==")
r = subprocess.run(['python3', 'skills/data-workflow/scripts/workflow_next.py', 'next', '--repo', DS], capture_output=True, text=True)
print('exit', r.returncode)
print(r.stdout)
print(r.stderr)

print()
print("== next in data-service (installed runner) ==")
r = subprocess.run(['python3', DS + '/.cursor/skills/data-workflow/scripts/workflow_next.py', 'next', '--repo', DS], capture_output=True, text=True)
print('exit', r.returncode)
print(r.stdout)
print(r.stderr)

print()
print("== data-service test entry ==")
print(sh("grep -n '^test:' Makefile", cwd=DS))
print(sh("ls -1 " + DS + "/Makefile " + DS + "/go.mod 2>/dev/null"))

print()
print("== data-service config verify key ==")
cfg = open(DS + '/.cursor/skills/data-workflow/config.yaml', encoding='utf-8').read()
print('verify key:', [l for l in cfg.splitlines() if l.startswith('verify:')])
print('gate_strict:', [l for l in cfg.splitlines() if l.startswith('gate_strict')])

print()
print("== run completeness counts ==")
runs = sorted(glob.glob('specs/*/run.json'))
empty_raw = 0
for f in runs:
    d = json.load(open(f))
    if not (d.get('raw_request') or '').strip():
        empty_raw += 1
print('runs', len(runs), 'empty raw', empty_raw)
print('evidence files', len(glob.glob('specs/*/evidence.log')))
print('change-note', len(glob.glob('specs/*/change-note.md')))
print('verify.log', len(glob.glob('specs/*/verify.log')))

print()
print("== check.md that fail own requires (no 'exit' or no 'verify.log') ==")
for f in sorted(glob.glob('specs/*/check.md')):
    txt = open(f, encoding='utf-8').read()
    miss = []
    if 'exit' not in txt: miss.append('exit')
    if 'verify.log' not in txt: miss.append('verify.log')
    if miss: print(os.path.basename(os.path.dirname(f)), 'MISSING', miss)

print()
print("== first line of check.md that is 'exit' ==")
cnt = 0
for f in sorted(glob.glob('specs/*/check.md')):
    first = open(f, encoding='utf-8').read().splitlines()[0].strip()
    if first.startswith('exit'):
        cnt += 1
        print(os.path.basename(os.path.dirname(f)), '|', first)
print('count', cnt, '/', len(glob.glob('specs/*/check.md')))

print()
print("== staged data-service change vs passes.log ==")
print('staged files:', sh("git diff --cached --name-only", cwd=DS).strip().splitlines())
print('passes lines with approved:', sh("grep -c approved specs/passes.log", cwd=DS).strip())
print('cached job_export diff stat:', sh("git diff --cached --stat -- internal/biz/job_export.go", cwd=DS).strip())

print()
print("== installed vs source key capability ==")
for name in ['workflow_next.py','check_runner.py','gate_edit.py']:
    src = 'skills/data-workflow/scripts/' + name if name != 'gate_edit.py' else 'skills/data-workflow/hooks/' + name
    dst = DS + '/.cursor/skills/data-workflow/' + ('scripts/' if name != 'gate_edit.py' else 'hooks/') + name
    st = os.path.getmtime(src) if os.path.exists(src) else None
    dt = os.path.getmtime(dst) if os.path.exists(dst) else None
    print(name, 'src', bool(st), 'installed', bool(dt), 'src_mtime', st, 'inst_mtime', dt)
