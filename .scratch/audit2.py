
import json, os, glob, subprocess, datetime

print("== run.json fields ==")
for f in sorted(glob.glob('specs/*/run.json')):
    d = json.load(open(f))
    n = os.path.basename(os.path.dirname(f))
    print(n, '|', {k: d.get(k) for k in ('workflow','stage','status','raw_request','created_at','updated_at','started_at')})

print()
print("== feature stage 6 ==")
w = json.load(open('skills/data-workflow/workflows/feature.json'))
print(json.dumps(w['stages'][5], ensure_ascii=False, indent=1))

print()
print("== knowledge_drift referenced in workflow json? ==")
for f in sorted(glob.glob('skills/data-workflow/workflows/*.json')):
    t = open(f, encoding='utf-8').read()
    print(os.path.basename(f), 'knowledge_drift' in t, 'knowledge_feedback' in t)

print()
print("== claim register C8 ==")
for line in open('docs/claim-register.md', encoding='utf-8'):
    if line.startswith('| C8'):
        print(line.strip())

print()
print("== data-service ===")
ds = '/Users/xuxinzhi/Documents/gowork/data-service'
for root, dirs, files in os.walk(ds + '/specs'):
    print(root.replace(ds,''), 'dirs=', dirs, 'files=', files)
    break
print('passes.log:')
print(open(ds + '/specs/passes.log', encoding='utf-8').read())

print()
print("== data-service recent activity ==")
for cmd in [['git','-C',ds,'log','-8','--format=%ad %h %s','--date=iso'],
            ['git','-C',ds,'status','--short'],
            ['git','-C',ds,'diff','--cached','--stat']]:
    r = subprocess.run(cmd, capture_output=True, text=True)
    print('$', ' '.join(cmd))
    print(r.stdout.strip() or '(empty)')
    print()

print("== docs/domain across repos ==")
print('skill repo docs/domain:', os.path.isdir('docs/domain'))
print('skill repo GLOSSARY:', os.path.exists('GLOSSARY.md'))
print('ds docs/domain:', os.path.isdir(ds+'/docs/domain'))
print('ds GLOSSARY:', os.path.exists(ds+'/GLOSSARY.md'))

print()
print("== md line totals by top dir ==")
import glob as g
for top in ['skills','docs','specs']:
    fs = g.glob(top+'/**/*.md', recursive=True)
    lines = sum(len(open(f,encoding='utf-8',errors='ignore').read().splitlines()) for f in fs)
    print(top, len(fs), 'files', lines, 'lines')

print()
print("== skills dir breakdown ==")
for top in ['skills/data-workflow/stages','skills/data-workflow/references','skills/data-workflow/workflows','skills/data-workflow/templates']:
    fs = g.glob(top+'/**/*.md', recursive=True)
    lines = sum(len(open(f,encoding='utf-8',errors='ignore').read().splitlines()) for f in fs)
    print(top, len(fs), 'files', lines, 'lines')
