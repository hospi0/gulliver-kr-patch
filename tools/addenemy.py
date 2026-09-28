# -*- coding: utf-8 -*-
r"""걸리버 보이 — 전투 설정 레코드의 적 이름·전투 문구 추가 추출 (2026-09-28)
  extract_other.py 는 «대사처럼 읽히는 레코드»를 건너뛰어, 필드 파일(C*·CS*·D*·V*…)의 전투 설정 레코드에 든
  적 이름을 놓쳤다(실기: «ムース이(가) 나타났다!»). 이 레코드는 «ガリバー\0ミスティ\0エジソン\0» 다음에
  적 이름·전투 문구가 NUL 로 이어지고, 게임은 오프셋으로 가리킨다. 일반 적 이름은 «이름!» 꼴(«!» 까지가 이름 — 화면엔 안 나옴).
  → work/trans/ids_etc.tsv 에 E01001‥ 덧붙임(이미 있는 위치는 건너뜀) · my files/tsv/gulliver_etc_003.tsv (번역 빈칸)
  되넣기: build.py build_etc 가 원문 끝 «!» 를 떼고 비교, 새 바이트 뒤에 «!» 를 다시 붙이고 남는 자리는 NUL.
  python tools/addenemy.py
"""
import collections, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import msg
from extract_other import plausible, fmt

HEAD = b'\x00'.join(s.encode('cp932') for s in ('ガリバー', 'ミスティ', 'エジソン')) + b'\x00'
IDS = os.path.join(ROOT, 'work', 'trans', 'ids_etc.tsv')
OUT = os.path.join(ROOT, 'my files', 'tsv', 'gulliver_etc_003.tsv')


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    lines = open(IDS, encoding='utf-8').read().splitlines()
    have = set()
    for ln in lines[1:]:
        for x in ln.split('\t')[2:]:
            have.add(x.rsplit(':', 1)[0])
    found = collections.OrderedDict()
    for fn in sorted(os.listdir(msg.DISC)):
        if fn.endswith('.CPK'):
            continue
        d = open(os.path.join(msg.DISC, fn), 'rb').read()
        for k, (i, L, o, r) in enumerate(msg.records(d) or []):
            b = o if o is not None else r
            p = b.find(HEAD)
            while p >= 0:
                q = p + len(HEAD)
                while q < len(b) and b[q] != 0:
                    e = b.index(b'\0', q); s = b[q:e]
                    core = s[:-1] if s.endswith(b'!') else s
                    loc = '%s-%d%s-%X' % (fn.rsplit('.', 1)[0], k, 'z' if o is not None else '', q)
                    try:
                        ok = plausible(core)
                    except Exception:
                        ok = False
                    if ok and loc not in have:
                        found.setdefault(s, []).append((loc, len(s)))
                    q = e + 1
                p = b.find(HEAD, p + 1)
    n0 = 1001 + sum(1 for ln in lines[1:] if ln.startswith('E01'))
    rows = []; add = []
    for j, (s, locs) in enumerate(found.items()):
        i = 'E%05d' % (n0 + j)
        add.append('%s\t%s\t%s' % (i, s.hex(), '\t'.join('%s:%d' % x for x in locs)))
        kind = '적이름' if s.endswith(b'!') else '전투문구' if b'a0' in s else '이름표'
        rows.append('\t'.join([i, locs[0][0], '%s 최대%dB' % (kind, len(s)), str(len(locs)), fmt(s[:-1] if s.endswith(b'!') else s) + ('!' if s.endswith(b'!') else ''), '']))
    with open(IDS, 'a', encoding='utf-8', newline='\n') as f:
        f.write(''.join(x + '\n' for x in add))
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write('ID\t위치\t구분\t공유\t원문\t번역\n' + ''.join(x + '\n' for x in rows))
    print('추가 %d줄 → %s' % (len(rows), OUT))
    for x in rows:
        print(x.split('\t')[0], x.split('\t')[2], x.split('\t')[4])


if __name__ == '__main__':
    main()
