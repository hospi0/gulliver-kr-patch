# -*- coding: utf-8 -*-
r"""걸리버 보이 — 고친 번역을 my files/tsv 에 반영 (2026-09-28, 병합 뒤 기준 = my files/tsv)
  파일 (ID \t 새 번역, 줄바꿈 = 글자 \n, 빈 번역 = «-») → 빌더 규칙으로 하나씩 검사 → 통과분만
  my files/tsv/gulliver_*.tsv 전부(나눈 파일 + 합본)의 같은 ID 번역 열을 바꾼다
  python tools/trapply.py 파일…
"""
import csv, glob, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import build
from trshort import check

TSV = os.path.join(ROOT, 'my files', 'tsv')


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    dia, etc = build.load_ids()
    new = {}; bad = 0
    for p in sys.argv[1:]:
        for ln in open(p, encoding='utf-8'):
            ln = ln.rstrip('\n')
            if not ln or '\t' not in ln:
                continue
            i, t = ln.split('\t', 1)
            if t == '-':
                new[i] = ''; continue
            e = check(build, dia, etc, i, t)
            if e:
                bad += 1; print('✗ %s %s | %s' % (i, e.split(' ', 1)[1][:90], t))
            else:
                new[i] = t
    n = 0
    for p in sorted(glob.glob(os.path.join(TSV, 'gulliver_*.tsv'))):
        rows = list(csv.reader(open(p, encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE))
        ch = False
        for r in rows[1:]:
            if r[0] in new and r[5] != new[r[0]]:
                r[5] = new[r[0]]; ch = True; n += 1
        if ch:
            with open(p, 'w', encoding='utf-8', newline='\n') as f:
                f.write(''.join('\t'.join(r) + '\n' for r in rows))
    print('통과 %d · 실패 %d · 바꾼 칸 %d(나눈 파일 + 합본)' % (len(new), bad, n))


if __name__ == '__main__':
    main()
