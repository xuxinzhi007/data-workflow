
import os, glob, json, subprocess, hashlib

DS = '/Users/xuxinzhi/Documents/gowork/data-service'

def sh(cmd, cwd=None):
    r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return (r.stdout or '') + (r.stderr or '')

print("== data-service staged .gitignore diff ==")
print(sh("git diff --cached -- .gitignore", cwd=DS))

print("== data-service staged job_export.go diff (first 80) ==")
print("\n".join(sh("git diff --cached -- internal/biz/job_export.go", cwd=DS).splitlines()[:80]))

print("== data-service specs dirs contents ==")
for d in sorted(glob.glob(DS + '/specs/*')):
    print(os.path.basename(d), '->', sorted(os.listdir(d)))

print()
print("== data-service installed skill hooks ==")
for p in sorted(glob.glob(DS + '/.cursor/skills/data-workflow/hooks/*')):
    print(os.path.basename(p), os.path.getsize(p))
print('scripts:', sorted(os.path.basename(p) for p in glob.glob(DS + '/.cursor/skills/data-workflow/scripts/*')))

print()
print("== data-service next ==")
r = subprocess.run(['python3', DS + '/.cursor/skills/data-workflow/scripts/workflow_next.py', 'next', '--repo', DS], capture_output=True, text=True)
print('exit', r.returncode)
print(r.stdout)
print(r.stderr)

print()
print("== source next in data-service context ==")
r = subprocess.run(['python3', 'skills/data-workflow/scripts/workflow_next.py', 'next', '--repo', DS], capture_output=True, text=True)
print('exit', r.returncode)
print(r.stdout)
print(r.stderr)

print()
print("== check.md first line vs documented 'first screen is exit' ==")
for f in sorted(glob.glob('specs/*/check.md')):
    first = open(f, encoding='utf-8').read().splitlines()[0] if open(f, encoding='utf-8').read().splitlines() else ''
    print(os.path.basename(os.path.dirname(f)).ljust(28), '|', first[:50])

print()
print("== check.md contains 'exit' anywhere, position ==")
for f in sorted(glob.glob('specs/*/check.md')):
    txt = open(f, encoding='utf-8').read().splitlines()
    pos = next((i for i,l in enumerate(txt) if 'exit' in l), None)
    print(os.path.basename(os.path.dirname(f)).ljust(28), 'line', pos)

print()
print("== data-service .cursor hooks mtime and install.sh policy mtime ==")
print(sh("stat -f '%Sm %N' -t '%Y-%m-%d %H:%M' " + DS + "/.cursor/hooks.json"))
print(sh("git log -1 --format='%ad %h %s' --date=short -- scripts/install.sh"))

print()
print("== does data-service harness have fail-open-capable gate-edit? ==")
p = DS + '/.cursor/skills/data-workflow/hooks/gate-edit'
print('gate-edit exists:', os.path.exists(p))
if os.path.exists(p):
    print(open(p, encoding='utf-8').read()[:1200])

print()
print("== claim register C3/C6/C8 ==")
for line in open('docs/claim-register.md', encoding='utf-8'):
    if line.startswith(('| C3','| C6','| C8')):
        print(line.strip()[:220])
