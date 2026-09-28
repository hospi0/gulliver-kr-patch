# -*- coding: utf-8 -*-
r"""걸리버 보이 — 선택지 줄 구조 복원 (2026-09-28)
  받은 번역의 «줄바꿈 이동»(trfix)이 선택지 {o} 를 질문 줄 뒤로 끌어올린 줄을 원문 구조로 되돌린다.
  · 선택지 부분: 원문 선택지 줄마다 {o} 개수만큼 번역 선택지 조각을 넣고, 조각 사이 간격은 원문 그대로(예: «はい　　　»의 　×3)
  · 앞 질문 글: 원문 질문 줄 수 안에 폭 max(19, 원문 최장) 칸으로 다시 나눔(낱말 단위)
  python tools/choicefix.py → work/trcheck/short/c02_choice.tsv (ID \t 새 번역) + 안 들어간 줄 목록
"""
import csv, glob, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import build

NL = chr(92) + 'n'
CODE = re.compile(r'\{[a-z{v][0-9]*\}')


def opos(t):
    """선택지 모양: 첫 선택지 줄부터의 (상대 줄, 줄 맨 앞인가) — 질문 줄 수는 달라도 된다(창 3줄 안)"""
    out = []
    ls = t.split(NL)
    k0 = next((i for i, l in enumerate(ls) if '{o}' in l), 0)
    for li, line in enumerate(ls):
        li -= k0
        for m in re.finditer(r'\{o\}', line):
            out.append((li, re.fullmatch(r'(\{[a-z][0-9]*\})*', line[:m.start()]) is not None))
    return out


def w(s):
    toks, err = build.parse(s, halfspace=False)
    return build.width(toks) if not err else 99


def wrap(text, n, W):
    words = re.split(r'(?<=[ 　])', text.replace(NL, ' '))
    words = [x for x in words if x]
    lines = ['']
    for x in words:
        if w((lines[-1] + x).rstrip(' 　')) <= W:
            lines[-1] += x
        else:
            lines.append(x)
    lines = [l.rstrip(' 　') for l in lines]
    return lines if len(lines) <= n and all(w(l) <= W for l in lines) else None


def fix(o, t):
    ol = o.split(NL)
    k = next(i for i, l in enumerate(ol) if '{o}' in l)
    lead = re.match(r'((?:\{[a-z][0-9]*\})*?)\{o\}', ol[k]).group(1)      # 선택지 줄 앞 코드(예: {z00})
    i0 = t.find(lead + '{o}') if lead else t.find('{o}')
    pre, post = t[:i0].rstrip(' 　' + NL), t[i0 + len(lead):]
    if pre.endswith(NL):
        pre = pre[:-2]
    segs = [s for s in post.split('{o}')][1:]                          # 번역 선택지 조각
    segs = [s.replace(NL, ' ').strip(' 　') for s in segs]
    W = max(19, max(w(re.sub(r'\{o\}', '', l)) for l in ol))
    out = []
    si = 0
    for li in range(k, len(ol)):
        parts = ol[li].split('{o}')
        head = parts[0] if li == k else parts[0]
        line = lead if li == k else head
        for pj, op in enumerate(parts[1:]):
            gap = re.search(r'([ 　]*)(\{i\})?$', op)
            sep = re.search(r'[ 　]+$', re.sub(r'\{i\}$', '', op))
            seg = segs[si]; si += 1
            if pj < len(parts) - 2 and sep:
                seg = re.sub(r'\{i\}$', '', seg).rstrip(' 　') + sep.group() if not seg.endswith('{i}') else seg
            line += '{o}' + seg
        out.append(line)
    if si != len(segs):
        return None, '선택지 수 다름'
    kq = max(k, build.LINES - (len(ol) - k)) if k else 0      # 질문 줄: 창 3줄에서 선택지 줄을 뺀 만큼까지
    prel = wrap(pre, kq, W) if k else ([] if not pre else None)
    if prel is None:
        return None, '질문 글이 %d줄×%d칸에 안 들어감: %s' % (kq, W, pre)
    return NL.join(prel + out), None


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    good, bad = [], []
    for p in sorted(glob.glob(os.path.join(ROOT, 'my files', 'tsv', 'gulliver_0*.tsv'))):
        for r in list(csv.reader(open(p, encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE))[1:]:
            if '{o}' not in r[4] or not r[5] or opos(r[4]) == opos(r[5]):
                continue
            nt, e = fix(r[4], r[5])
            if nt and opos(nt) == opos(r[4]):
                good.append((r[0], nt))
            else:
                bad.append((r[0], e or '구조 불일치 %s' % nt, r[4], r[5]))
    out = os.path.join(ROOT, 'work', 'trcheck', 'short', 'c02_choice.tsv')
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        f.write(''.join('%s\t%s\n' % g for g in good))
    print('자동 %d · 손으로 %d → %s' % (len(good), len(bad), out))
    for i, e, o, t in bad:
        print('✗', i, e, '\n   JP:', o, '\n   KR:', t)


if __name__ == '__main__':
    main()
