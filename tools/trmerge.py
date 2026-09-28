# -*- coding: utf-8 -*-
r"""걸리버 보이 — 검사 끝난 받은 번역 병합 (2026-09-28)
  work/trcheck/fixed/gulliver_*.tsv 의 «번역» 열 → my files/tsv/같은 이름(ID·위치·구분·공유·원문 열이 같아야 함)
  병합 전 원본은 work/trcheck/tsv_before_merge/ 에 복사 · 합본 gulliver_전체.tsv 는 대사 44 + etc 2 를 다시 이어 붙임
  python tools/trmerge.py
"""
import csv, glob, os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
FIX = os.path.join(ROOT, 'work', 'trcheck', 'fixed')
TSV = os.path.join(ROOT, 'my files', 'tsv')
BAK = os.path.join(ROOT, 'work', 'trcheck', 'tsv_before_merge')


def rows(p):
    return list(csv.reader(open(p, encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE))


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    os.makedirs(BAK, exist_ok=True)
    names = sorted(os.path.basename(p) for p in glob.glob(os.path.join(FIX, 'gulliver_*.tsv')))
    new = {}
    for n in names:                      # 먼저 전부 대조 — 하나라도 어긋나면 아무것도 안 쓴다
        a, b = rows(os.path.join(TSV, n)), rows(os.path.join(FIX, n))
        key = lambda r: [r[0]] + r[2:5]          # 위치 열은 빌더가 안 쓴다(ID 로 대응) — 다르면 경고, 우리 추출본 값 유지
        if len(a) != len(b) or any(key(x) != key(y) for x, y in zip(a, b)):
            sys.exit('⛔%s: 번역 말고 다른 열이 다르다 — 병합 중단' % n)
        for x, y in zip(a, b):
            if x[1] != y[1]:
                print('⚠%s %s 위치 열 다름(받은 번역 %s) — 추출본 값 유지' % (n, x[0], y[1]))
        new[n] = [x[:5] + [y[5]] for x, y in zip(a, b)]
    for n in names + ['gulliver_전체.tsv']:
        src = os.path.join(TSV, n)
        if os.path.exists(src) and not os.path.exists(os.path.join(BAK, n)):
            shutil.copy2(src, os.path.join(BAK, n))
    k = 0
    for n in names:
        with open(os.path.join(TSV, n), 'w', encoding='utf-8', newline='\n') as f:
            f.write(''.join('\t'.join(r) + '\n' for r in new[n]))
        k += sum(1 for r in new[n][1:] if r[5])
    order = [n for n in names if '_etc_' not in n] + [n for n in names if '_etc_' in n]
    with open(os.path.join(TSV, 'gulliver_전체.tsv'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\t'.join(new[order[0]][0]) + '\n')
        for n in order:
            f.write(''.join('\t'.join(r) + '\n' for r in new[n][1:]))
    print('병합 %d개 파일 · 번역 %d줄 · 합본 다시 만듦 · 원본 백업 %s' % (len(names), k, BAK))


if __name__ == '__main__':
    main()
