# -*- coding: utf-8 -*-
r"""걸리버 보이 — 받은 번역 검사 (병합 전) (2026-09-28)
  python tools/trcheck.py <번역 폴더>
  ① 정규화: 번역 도구마다 다른 꼴을 한 가지로 — 칸 안 실제 줄바꿈(따옴표로 감쌈/안 감쌈 둘 다) → \n,
     감싼 큰따옴표·"" 풀기, BOM 제거, ID 로 시작하지 않는 줄 = 앞 번역의 이어지는 줄.
     → work/trcheck/norm/gulliver_XXX.tsv (원본 파일 이름의 번호 부분만, my files 는 안 건드림)
     ID 목록·원문이 my files/tsv 원본과 같은지 대조.
  ② 토큰·형식: 빌더(build.py)의 검사를 그대로(코드 순서·인수 자리수·줄 수·줄 폭·쪽 바이트·KS X 1001·글꼴 밖 글자)
     → work/trcheck/토큰검사.tsv (ID·파일·오류·원문·번역)
  ③ 용어: 원문 가타카나 낱말(3번 이상)마다 번역 쪽 한글 표기를 모아 «주 표기»와 다른 표기를 찾는다
     → work/trcheck/용어검사.tsv
"""
import collections, csv, difflib, glob, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
OUT = os.path.join(ROOT, 'work', 'trcheck')
IDRE = re.compile(r'^(E?\d{5})\t')


def read_raw(p):
    """번역 파일 → [(ID, 위치, 구분, 공유, 원문, 번역)]"""
    txt = open(p, encoding='utf-8-sig', newline='').read().replace('\r\n', '\n').replace('\r', '\n')
    lines = txt.split('\n')
    recs = []
    for ln in lines[1:]:
        if IDRE.match(ln):
            recs.append(ln)
        elif recs and ln != '':
            recs[-1] += '\n' + ln                   # 칸 안 실제 줄바꿈
        elif recs and ln == '' and recs[-1].count('"') % 2 == 1:
            recs[-1] += '\n'
    out = []
    for r in recs:
        c = r.split('\t')
        if len(c) > 6:                              # 번역 안에 탭이 들어간 경우 뒤로 합침
            c = c[:5] + ['\t'.join(c[5:])]
        while len(c) < 6:
            c.append('')
        t = c[5]
        if len(t) >= 2 and t[0] == '"' and t[-1] == '"' and ('\n' in t or '""' in t):
            t = t[1:-1].replace('""', '"')
        t = t.rstrip('\n').replace('\n', '\\n')
        o = c[4]
        if len(o) >= 2 and o[0] == '"' and o[-1] == '"' and '\n' in o:
            o = o[1:-1].replace('""', '"')
        o = o.replace('\n', '\\n')
        # 이중 이스케이프(번역 도구가 역슬래시를 한 번 더 씀): 글자 그대로 «\\n» → «\n»
        while '\\\\n' in t:
            t = t.replace('\\\\n', '\\n')
        while '\\\\n' in o:
            o = o.replace('\\\\n', '\\n')
        out.append((c[0], c[1], c[2], c[3], o, t))
    return out


def normalize(src):
    os.makedirs(os.path.join(OUT, 'norm'), exist_ok=True)
    for f in glob.glob(os.path.join(OUT, 'norm', '*.tsv')):
        os.remove(f)
    probs = []; allrec = {}
    for p in sorted(glob.glob(os.path.join(src, '*.tsv'))):
        m = re.match(r'(gulliver_(?:etc_)?\d{3})', os.path.basename(p))
        if not m:
            probs.append('파일 이름 모름: %s' % os.path.basename(p)); continue
        stem = m.group(1)
        orig = list(csv.reader(open(os.path.join(ROOT, 'my files', 'tsv', stem + '.tsv'), encoding='utf-8'),
                               delimiter='\t', quoting=csv.QUOTE_NONE))[1:]
        recs = read_raw(p)
        oid = [r[0] for r in orig]; tid = [r[0] for r in recs]
        if oid != tid:
            probs.append('%s: ID 목록 다름(원본 %d / 번역 %d, 빠짐 %s, 더함 %s)' % (
                os.path.basename(p), len(oid), len(tid), sorted(set(oid) - set(tid))[:5], sorted(set(tid) - set(oid))[:5]))
        om = {r[0]: r for r in orig}
        for r in recs:
            if r[0] in om and om[r[0]][4] != r[4]:
                probs.append('%s %s: 원문 칸이 원본과 다름' % (os.path.basename(p), r[0]))
            if not r[5].strip():
                probs.append('%s %s: 번역 빔' % (os.path.basename(p), r[0]))
            allrec[r[0]] = r + (os.path.basename(p),)
        with open(os.path.join(OUT, 'norm', stem + '.tsv'), 'w', encoding='utf-8', newline='\n') as f:
            f.write('ID\t위치\t구분\t공유\t원문\t번역\n')
            for r in recs:
                f.write('\t'.join(r) + '\n')
    return allrec, probs


def token_check(allrec):
    os.environ['GB_TSV'] = os.path.join(OUT, 'norm')
    import build
    build.TSV = os.environ['GB_TSV']
    tr = build.load_translations()
    dia, etc = build.load_ids()
    _, e1 = build.build_dialogue(tr, dia, print)
    _, _, e2 = build.build_etc(tr, etc, print)
    rows = []
    for e in e1 + e2:
        i = e.split(' ', 1)[0]
        r = allrec.get(i)
        rows.append((i, r[6] if r else '', e.split(' ', 1)[1], r[4] if r else '', r[5] if r else ''))
    with open(os.path.join(OUT, '토큰검사.tsv'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('ID\t파일\t오류\t원문\t번역\n')
        for r in rows:
            f.write('\t'.join(r) + '\n')
    return rows


STOP = set('オレ ヤツ ボク アタシ キミ ホント ダメ バカ モン イヤ ワケ トコ クセ ザンネン セーブ バトル ダメージ アル アンタ オマエ オイラ ワタシ アイツ コイツ ソイツ ヤバ スゴ ヘン ハズ モノ ボクら オレたち'.split())
JOSA = sorted('으로서 에게서 한테서 으로는 에서는 에게는 으로 에서 에게 한테 까지 부터 처럼 보다 이나 이랑 하고 께서 이야 이여 이다 이란 이라 이네 이지 이군 이잖아 님이 님은 님을 님의 님께 이 가 을 를 은 는 의 에 도 와 과 로 야 여 만 랑'.split(), key=len, reverse=True)


def strip_josa(w):
    for j in JOSA:
        if len(w) > len(j) + 1 and w.endswith(j):
            return w[:-len(j)]
    return w


KATA = re.compile(r'[ァ-ヺー・]{2,}')
HAN = re.compile(r'[가-힣]+')


def terms(allrec):
    occ = collections.defaultdict(set)
    for i, r in allrec.items():
        for w in set(KATA.findall(r[4])):
            w = w.strip('・ー')
            if len(w) >= 2:
                occ[w].add(i)
    report = []
    for w, ids in occ.items():
        if len(ids) < 3:
            continue
        subs = {}
        for i in ids:
            s = set()
            for run in HAN.findall(allrec[i][5]):
                run = strip_josa(run)                 # «이스탄불에» → «이스탄불»
                for a in range(len(run)):
                    for b in range(a + 1, min(len(run), a + 7) + 1):
                        s.add(run[a:b])
            subs[i] = s
        cnt = collections.Counter(x for s in subs.values() for x in s)
        L = len(w.replace('ー', '').replace('ッ', '').replace('ャ', '').replace('ュ', '').replace('ョ', '').replace('ァ', '').replace('ィ', '').replace('ゥ', '').replace('ェ', '').replace('ォ', ''))
        cand = [(c, x) for x, c in cnt.items() if max(1, L - 2) <= len(x) <= L + 2]
        if not cand:
            continue
        mx = max(c for c, _ in cand)
        top_c, top = max(((c, x) for c, x in cand if c >= mx * 0.5), key=lambda t: (len(t[1]), t[0]))   # 흔한 것 중 가장 긴 표기(«리버» 말고 «걸리버»)
        if top_c < max(2, len(ids) * 0.4) or len(top) < 2 or w in STOP:
            continue
        miss = [i for i in ids if top not in subs[i]]
        if not miss:
            continue
        var = collections.Counter()
        for i in miss:
            for x in subs[i]:
                if abs(len(x) - len(top)) <= 1 and x != top and difflib.SequenceMatcher(None, x, top).ratio() >= 0.5:
                    var[x] += 1
        vs = [x for x, _ in var.most_common(3)]
        report.append((len(miss), w, top, top_c, len(ids), vs, sorted(miss)))
    report.sort(key=lambda t: (-t[0], t[1]))
    with open(os.path.join(OUT, '용어검사.tsv'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('원문 낱말\t주 표기\t쓰인 줄\t주 표기 없는 줄 수\t다른 표기 후보\t주 표기 없는 ID(앞 20)\n')
        for n, w, top, c, tot, vs, miss in report:
            f.write('%s\t%s\t%d/%d\t%d\t%s\t%s\n' % (w, top, c, tot, n, ' · '.join(vs), ' '.join(miss[:20])))
    return report


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    src = sys.argv[1]
    os.makedirs(OUT, exist_ok=True)
    allrec, probs = normalize(src)
    print('① 정규화: %d 줄 (문제 %d)' % (len(allrec), len(probs)))
    for p in probs[:20]:
        print('   ', p)
    open(os.path.join(OUT, '형식문제.txt'), 'w', encoding='utf-8').write('\n'.join(probs))
    rows = token_check(allrec)
    kinds = collections.Counter(re.sub(r'[0-9]+|\[.*|\(.*|:.*', '', r[2]).strip() for r in rows)
    print('② 토큰·형식 오류 %d건:' % len(rows), dict(kinds.most_common()))
    rep = terms(allrec)
    print('③ 용어 흔들림 후보 %d 낱말' % len(rep))
    for n, w, top, c, tot, vs, miss in rep[:25]:
        print('   %s → %s (%d/%d)  다른 표기 %d줄: %s' % (w, top, c, tot, n, ' · '.join(vs)))


if __name__ == '__main__':
    main()
