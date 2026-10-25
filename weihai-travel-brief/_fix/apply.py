import base64
import json
import os

FIX = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(FIX)

rp = os.path.join(ROOT, 'weihai_travel_runner.py')
if os.path.exists(rp):
    b = open(rp, 'rb').read()
    b2 = b.replace(bytes([92, 92]), bytes([92]))
    if b2 != b:
        open(rp, 'wb').write(b2)
    print('RUNNER', len(b2))

sp = os.path.join(ROOT, 'weihai_travel_skill_SKILL_V6.md')
bp = os.path.join(FIX, 'skill.spec.b64')
if os.path.exists(sp) and os.path.exists(bp):
    spec = json.loads(base64.b64decode(open(bp, 'rb').read().strip()).decode('utf-8'))
    ol = open(sp, 'rb').read().decode('utf-8').splitlines(keepends=True)
    res = []
    cur = 0
    for tag, i1, i2, rep in spec['ops']:
        res.extend(ol[cur:i1])
        if tag in ('replace', 'insert'):
            res.extend(rep)
        cur = i2
    res.extend(ol[cur:])
    data = ''.join(res).encode('utf-8')
    if len(data) == 19278:
        open(sp, 'wb').write(data)
        print('SKILL OK')
    else:
        print('SKILL SKIP', len(data))
