# -*- coding: utf-8 -*-
r"""걸리버 보이 — 실행 파일(1ST_READ.PRG)에서 추출이 놓친 일본어 문자열 찾기 (2026-09-28)
  NUL 로 끝나는 SJIS+ASCII 연속 중 가나·한자가 든 것 → work/trans/ids_etc.tsv 의 1ST_READ 위치 구간과 안 겹치면 출력
  python tools/findmissed.py [최소 가나·한자 수=2] > work/trans/missed_1st.txt
"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN = int(sys.argv[1]) if len(sys.argv) > 1 else 2

d = open(os.path.join(ROOT, 'work', 'disc1', '1ST_READ.PRG'), 'rb').read()
cov = []
for ln in list(open(os.path.join(ROOT, 'work', 'trans', 'ids_etc.tsv'), encoding='utf-8'))[1:]:
    for x in ln.rstrip('\n').split('\t')[2:]:
        loc, L = x.rsplit(':', 1)
        if loc.startswith('1ST_READ-raw-'):
            a = int(loc.rsplit('-', 1)[1], 16); cov.append((a, a + int(L)))

sys.stdout.reconfigure(encoding='utf-8')
n = 0
for m in re.finditer(rb'(?:[\x81-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc]|[\x20-\x7e])+\x00', d):
    s = m.group()[:-1]; a = m.start()
    try:
        t = s.decode('cp932')
    except UnicodeDecodeError:
        continue
    if len(re.findall('[぀-ヿ一-鿿]', t)) < MIN:
        continue
    # 가나·한자 글자 하나라도 추출 범위 밖이면 보고(추출기가 코드 뒤 조각만 잡은 문자열 잡기, 2026-09-28)
    q = 0; out = []
    while q < len(s):
        if s[q] >= 0x81:
            ch = s[q:q + 2].decode('cp932', 'replace')
            if re.match('[぀-ヿ一-鿿]', ch) and not any(x <= a + q < y for x, y in cov):
                out.append(a + q)
            q += 2
        else:
            q += 1
    if not out:
        continue
    n += 1
    print('%X\t%d\t%s' % (a, len(s), t))
print('합계 %d' % n, file=sys.stderr)
