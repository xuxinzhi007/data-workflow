
import json, os, glob, re, subprocess

print("== per-run audit ==")
rows = []
for f in sorted(glob.glob('specs/*/run.json')):
    d = json.load(open(f))
    n = os.path.basename(os.path.dirname(f))
    md = os.path.join('specs', n, 'check.md')
    ck = open(md, encoding='utf-8').read() if os.path.exists(md) else ''
    evp = os.path.join('specs', n, 'evidence.log')
    ev = open(evp, encoding='utf-8').read().splitlines() if os.path.exists(evp) else []
    s2 = [l for l in ev if l.startswith('stage=2')]
    v2 = [l for l in s2 if 'verify=exit0' in l]
    raw = (d.get('raw_request') or '').strip()
    rows.append(dict(name=n, stage=d.get('stage'), status=d.get('status'),
                     raw=len(raw), ev=len(ev), s2=len(s2), s2ok=len(v2),
                     has_exit='exit' in ck, has_vlog='verify.log' in ck))
    print(f"{n:28} st={d.get('stage')} {d.get('status'):5} raw={len(raw):2} ev={len(ev)} stage2={len(s2)} v2ok={len(v2)} check_exit={'exit' in ck} check_vlog={'verify.log' in ck}")

print()
print("== summary ==")
print("runs:", len(rows))
print("empty raw_request:", sum(1 for r in rows if r['raw']==0))
print("runs with no evidence.log:", sum(1 for r in rows if r['ev']==0))
print("runs with stage2 verify=exit0:", sum(1 for r in rows if r['s2ok']>0))
print("check.md mention exit:", sum(1 for r in rows if r['has_exit']))
print("check.md mention verify.log:", sum(1 for r in rows if r['has_vlog']))
print("check.md mention both:", sum(1 for r in rows if r['has_exit'] and r['has_vlog']))

print()
print("== domain docs ==")
print("docs/domain exists:", os.path.isdir('docs/domain'))
print("data-service docs/domain exists:", os.path.isdir('/Users/xuxinzhi/Documents/gowork/data-service/docs/domain'))

print()
print("== knowledge_drift wiring ==")
for f in glob.glob('skills/data-workflow/workflows/*.json'):
    t = open(f, encoding='utf-8').read()
    print(os.path.basename(f), 'mentions knowledge_drift:', 'knowledge_drift' in t)
print('scripts referencing knowledge_drift:')
out = subprocess.run(['grep','-rl','knowledge_drift','skills/data-workflow/scripts','skills/data-workflow/stages','skills/data-workflow/references'], capture_output=True, text=True).stdout.strip()
print(out or '(none)')

print()
print("== data-service artifacts ==")
ds = '/Users/xuxinzhi/Documents/gowork/data-service'
print("run.json:", len(glob.glob(ds+'/specs/*/run.json')))
print("check.md:", len(glob.glob(ds+'/specs/*/check.md')))
print("decision.md:", len(glob.glob(ds+'/specs/*/decision.md')))
print("verify.log:", len(glob.glob(ds+'/specs/*/verify.log')))
print("evidence.log:", len(glob.glob(ds+'/specs/*/evidence.log')))
print("passes.log lines:", len(open(ds+'/specs/passes.log', encoding='utf-8').read().splitlines()) if os.path.exists(ds+'/specs/passes.log') else 0)
v = open(ds+'/specs/dispatch-remove-office-option/verify.log', encoding='utf-8').read().splitlines()
print("verify.log head:", v[:3])
print("verify.log tail:", v[-3:])

print()
print("== data-service hook tracked / config ==")
for cmd in [['git','-C',ds,'ls-files','.cursor/hooks.json'], ['git','-C',ds,'check-ignore','-v','.cursor/hooks.json'], ['git','-C',ds,'log','-1','--format=%ad %h %s','--date=short','--','.cursor/hooks.json']]:
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(' '.join(cmd[3:]), '=>', (r.stdout.strip() or r.stderr.strip() or '(empty)'))
cfg = open(ds+'/.cursor/skills/data-workflow/config.yaml', encoding='utf-8').read()
print("has verify key:", any(l.startswith('verify:') for l in cfg.splitlines()))
print("gate_strict in cfg:", 'gate_strict' in cfg)

print()
print("== tracked doc claim numbers ==")
t = open('README.md', encoding='utf-8').read()
print("README 60条:", '60 条回归' in t)
c = open('docs/competitive.md', encoding='utf-8').read()
print("competitive 45+:", '45+ 条回归' in c)
print("competitive hook row still diff:", 'hook 坏了自己的降级策略 | ●' in c)
print("competitive multiagent row still diff:", '多 agent 编排纪律 | ●' in c)

print()
print("== evidence.log stage2 verify lines ==")
for l in sorted(glob.glob('specs/*/evidence.log')):
    for line in open(l, encoding='utf-8'):
        if line.startswith('stage=2'):
            print(os.path.basename(os.path.dirname(l)), '|', line.strip())
