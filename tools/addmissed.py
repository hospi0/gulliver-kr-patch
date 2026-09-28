# -*- coding: utf-8 -*-
r"""걸리버 보이 — 추출이 놓친 실행 파일 문자열을 대사 밖 ID 로 추가 (2026-09-28, tools/findmissed.py 결과)
  work/trans/missed_add.tsv (16진 오프셋 \t 번역) → work/trans/ids_etc.tsv 에 E00745‥ 추가 +
  my files/tsv/gulliver_etc_002.tsv · gulliver_전체.tsv 끝에 줄 추가(원문 = 코드 {} 표기). 이미 있는 위치는 건너뜀.
  python tools/addmissed.py
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import build

sys.stdout.reconfigure(encoding='utf-8')
d = open(os.path.join(ROOT, 'work', 'disc1', '1ST_READ.PRG'), 'rb').read()
IDS = os.path.join(ROOT, 'work', 'trans', 'ids_etc.tsv')
lines = open(IDS, encoding='utf-8').read().rstrip('\n').split('\n')
have = {x.rsplit(':', 1)[0] for ln in lines[1:] for x in ln.split('\t')[2:]}
last = max(int(ln.split('\t')[0][1:]) for ln in lines[1:])
rows_ids, rows_tsv = [], []
for ln in open(os.path.join(ROOT, 'work', 'trans', 'missed_add.tsv'), encoding='utf-8'):
    ln = ln.rstrip('\n')
    if not ln:
        continue
    off, tr = ln.split('\t', 1); a = int(off, 16)
    loc = '1ST_READ-raw-%X' % a
    if loc in have:
        print('있음', loc); continue
    raw = d[a:d.index(b'\0', a)]
    src = ''
    for t in build.raw_tokens_etc(raw):
        src += t[1].decode('cp932') if t[0] == 'c' else '\\n' if t[0] == 'n' else '{%s%s}' % (t[1], t[2])
    last += 1; i = 'E%05d' % last
    rows_ids.append('%s\t%s\t%s:%d' % (i, raw.hex(), loc, len(raw)))
    rows_tsv.append('\t'.join([i, loc, '실행파일 최대%dB' % len(raw), '1', src, tr]))
    print(i, loc, src, '→', tr)
with open(IDS, 'a', encoding='utf-8', newline='\n') as f:
    f.write(''.join(r + '\n' for r in rows_ids))
for n in ('gulliver_etc_002.tsv', 'gulliver_전체.tsv'):
    with open(os.path.join(ROOT, 'my files', 'tsv', n), 'a', encoding='utf-8', newline='\n') as f:
        f.write(''.join(r + '\n' for r in rows_tsv))
print('추가 %d줄' % len(rows_ids))
