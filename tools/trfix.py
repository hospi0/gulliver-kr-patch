# -*- coding: utf-8 -*-
r"""걸리버 보이 — 받은 번역 일괄 수정 (2026-09-28, 사용자 결정 반영)
  입력 work/trcheck/norm/*.tsv(tools/trcheck.py 정규화본) → 출력 work/trcheck/fixed/*.tsv + 수정내역.tsv
  ① 용어 통일(원문에 그 말이 있는 줄만, 받침이 바뀌면 바로 뒤 조사도 고침)
     사용자: «이름은 겟코같이»(한자 이름 = 일본어 읽기) · «주도는 쥬도»
  ② 글꼴 밖 글자 바꾸기(사용자 «바꿔도 됨»): ㅡ — → ー · · → ・ · 낱자모·KS X 1001 밖 음절은 줄마다 정한 대로
  ③ 음성 대사의 {z..}{w..}{r} 지움(빌더가 원문 타이밍으로 넣음)
  ④ 줄 폭 초과 중 «낱말 단위 줄바꿈 이동만으로 들어가는 것»만 다시 줄바꿈(글자는 그대로, 줄 수 한도 안) — 사용자 «1138건부터»
  python tools/trfix.py
"""
import csv, glob, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
SRC = os.path.join(ROOT, 'work', 'trcheck', 'norm')
DST = os.path.join(ROOT, 'work', 'trcheck', 'fixed')

# (원문에 있어야 할 말, [(바꿀 것, 바꿀 말)], 제외 ID)
TERMS = [
    ('ガリバー', [('갈리버', '걸리버')], ()),
    ('ジュドー', [('주도', '쥬도'), ('쥐도', '쥬도')], ()),
    ('アルバーン', [('알바른', '알반')], ()),
    ('ポンピ', [('폰피', '폼피'), ('퐁피', '폼피')], ()),
    ('マーロン', [('마론', '말론')], ()),
    ('ハレルヤ', [('하레루야', '할렐루야')], ()),
    ('日輪', [('일륜', '니치린'), ('이, 일륜', '니, 니치린')], ()),
    ('月光', [('월광', '겟코')], ()),
    ('満月', [('만월', '만게츠'), ('보름달', '만게츠'), ('궁전', '팰리스')], ('05910',)),   # 05910 = 시 구절의 보름달
    ('シーライオン', [('시라이온', '시라이언'), ('씨라이언', '시라이언')], ()),
    ('コロッセオ', [('콜로세움', '콜로세오')], ()),
    ('カバヤキ', [('가바야키', '카바야키')], ()),
    ('バカリャオ', [('바카랴우', '바칼랴우'), ('바칼라우', '바칼랴우')], ()),
    ('ブリウアト', [('브리와트', '브리우아트')], ()),
    ('ルルブ', [('루르브', '루루브'), ('룰루브', '루루브')], ()),
    ('サン・マルコ', [('산 마르코', '산마르코')], ()),
    ('リニアトレイン', [('리니어트레인', '리니어 트레인')], ()),
    ('アルバーン', [('알바안', '알반')], ()),
]
CHARS = [('ㅡ', 'ー'), ('—', 'ー'), ('·', '・'), ('모ーㄴ', '모온'), ('오ーㄴ', '오온'), ('~ㅇ?', '~응?'),
         ('잌', '익'), ('귱', '궁'), ('춍', '총'), ('슌', '순')]
# 조사: (받침 있을 때, 받침 없을 때) — 긴 것부터
JOSA = [('이라는', '라는'), ('이라고', '라고'), ('이라니', '라니'), ('이라던가', '라던가'), ('이랑', '랑'), ('이야', '야'),
        ('이여', '여'), ('이란', '란'), ('이지', '지'), ('이다', '다'), ('으로', '로'), ('은', '는'), ('이', '가'),
        ('을', '를'), ('과', '와')]


def batchim(ch):
    return '가' <= ch <= '힣' and (ord(ch) - 0xAC00) % 28 != 0


def fix_josa(t, pos, had, has):
    """t[pos:] 이 조사로 시작하면 받침(had→has)에 맞게"""
    if had == has:
        return t
    for a, b in JOSA:
        src, dst = (a, b) if had else (b, a)
        if t.startswith(src, pos):
            nxt = t[pos + len(src):pos + len(src) + 1]
            if src in ('이', '가') and nxt and '가' <= nxt <= '힣':   # «이야기» 같은 낱말은 건드리지 않음
                continue
            return t[:pos] + dst + t[pos + len(src):]
    return t


def replace_term(t, old, new):
    res = ''; rest = t
    while True:
        j = rest.find(old)
        if j < 0:
            return res + rest
        res += rest[:j] + new
        rest = fix_josa(rest[j + len(old):], 0, batchim(old[-1]), batchim(new[-1]))


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    os.environ['GB_TSV'] = SRC
    import build
    dia, etc = build.load_ids()
    os.makedirs(DST, exist_ok=True)
    for f in glob.glob(os.path.join(DST, '*.tsv')):
        os.remove(f)
    log = []; n_reflow = 0
    for p in sorted(glob.glob(os.path.join(SRC, '*.tsv'))):
        rows = list(csv.reader(open(p, encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE))
        for r in rows[1:]:
            i, o, t0 = r[0], r[4], r[5]
            t = t0
            for jp, reps, skip in TERMS:
                if jp in o and i not in skip:
                    for a, b in reps:
                        if a in t:
                            t2 = replace_term(t, a, b)
                            if t2 != t:
                                log.append((i, '용어', '%s→%s' % (a, b), t, t2)); t = t2
            for a, b in CHARS:
                if a in t:
                    t2 = t.replace(a, b); log.append((i, '글자', '%s→%s' % (a, b), t, t2)); t = t2
            if i in dia and dia[i][:1] == b'r' and re.search(r'\{[zw][0-9]{2}\}|\{r\}', t):
                t2 = re.sub(r'\{[zw][0-9]{2}\}|\{r\}', '', t); log.append((i, '음성코드', 'z·w·r 삭제', t, t2)); t = t2
            if i in dia and t.strip():
                t2 = reflow(build, dia[i], t)
                if t2 and t2 != t:
                    log.append((i, '줄바꿈', '줄 폭', t, t2)); t = t2; n_reflow += 1
            r[5] = t
        with open(os.path.join(DST, os.path.basename(p)), 'w', encoding='utf-8', newline='\n') as f:
            for r in rows:
                f.write('\t'.join(r) + '\n')
    with open(os.path.join(ROOT, 'work', 'trcheck', '수정내역.tsv'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('ID\t종류\t내용\t전\t후\n')
        for x in log:
            f.write('\t'.join(x) + '\n')
    import collections
    c = collections.Counter(x[1] for x in log)
    print('수정 %d건 %s · 줄바꿈 다시 한 줄 %d' % (len(log), dict(c), n_reflow))


def reflow(build, raw, t):
    """줄 폭이 넘는 쪽만: 낱말(공백) 단위로 다시 줄바꿈 → 들어가면 새 글, 아니면 None(글자는 안 바꿈)"""
    orig = build.raw_tokens(raw)
    toks, err = build.parse(t, halfspace=b' ' in raw)
    if err:
        return None
    ol = build.lines_of(orig); nl = build.lines_of(toks)
    maxw = max(build.LINE_W, max(build.width(l) for l in ol)); maxl = max(build.LINES, len(ol))
    if all(build.width(l) <= maxw for l in nl):
        return None
    # 글을 줄바꿈 없이 낱말로(공백 = 반각·전각, 공백은 앞 낱말 끝에 붙임)
    flat = t.replace('\\n', ' ')
    words = re.findall(r'[^ 　]+[ 　]*', flat)
    lines = ['']
    for w in words:
        cand = lines[-1] + w
        if lines[-1] and wid(build, raw, cand.rstrip(' 　')) > maxw:
            lines.append(w)
        else:
            lines[-1] = cand
    lines = [l.rstrip(' 　') for l in lines]
    if len(lines) > maxl or any(wid(build, raw, l) > maxw for l in lines):
        return None
    return '\\n'.join(lines)


def wid(build, raw, s):
    toks, err = build.parse(s, halfspace=b' ' in raw)
    return 999 if err else build.width([x for x in toks if x[0] != 'n'])


if __name__ == '__main__':
    main()
