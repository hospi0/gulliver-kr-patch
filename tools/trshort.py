# -*- coding: utf-8 -*-
r"""걸리버 보이 — 줄인 번역 검사·적용 (2026-09-28)
  work/trcheck/short/*.tsv (ID \t 새 번역, 줄바꿈 = 글자 \n) → 빌더 규칙으로 하나씩 검사 → 통과분만 work/trcheck/fixed 에 반영
  python tools/trshort.py [파일…]   (없으면 short/ 전부)
"""
import csv, glob, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
FIX = os.path.join(ROOT, 'work', 'trcheck', 'fixed')


def check(build, dia, etc, i, t):
    """→ 오류 문자열 또는 None"""
    if i in dia:
        _, errs = build.build_dialogue({i: t}, {i: dia[i]}, print)
    else:
        _, _, errs = build.build_etc({i: t}, {i: etc[i]}, print)
    return errs[0] if errs else None


def widths(build, dia, i, t):
    if i not in dia:
        return ''
    toks, err = build.parse(t, halfspace=b' ' in dia[i])
    return [build.width(l) for l in build.lines_of(toks)] if not err else err


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    os.environ['GB_TSV'] = FIX
    import build
    dia, etc = build.load_ids()
    files = sys.argv[1:] or sorted(glob.glob(os.path.join(ROOT, 'work', 'trcheck', 'short', '*.tsv')))
    new = {}; bad = 0
    for p in files:
        for ln in open(p, encoding='utf-8'):
            ln = ln.rstrip('\n')
            if not ln or '\t' not in ln:
                continue
            i, t = ln.split('\t', 1)
            e = check(build, dia, etc, i, t)
            if e:
                bad += 1
                print('✗ %s %s  폭%s  | %s' % (i, e.split(' ', 1)[1][:80], widths(build, dia, i, t), t))
            else:
                new[i] = t
    n = 0
    for p in sorted(glob.glob(os.path.join(FIX, '*.tsv'))):
        rows = list(csv.reader(open(p, encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE))
        ch = False
        for r in rows[1:]:
            if r[0] in new and r[5] != new[r[0]]:
                r[5] = new[r[0]]; ch = True; n += 1
        if ch:
            with open(p, 'w', encoding='utf-8', newline='\n') as f:
                f.write(''.join('\t'.join(r) + '\n' for r in rows))
    print('통과 %d · 실패 %d · fixed 에 반영 %d' % (len(new), bad, n))


if __name__ == '__main__':
    main()
