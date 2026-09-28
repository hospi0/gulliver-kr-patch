# -*- coding: utf-8 -*-
r"""걸리버 보이 한글 빌더 (2026-09-27)
  번역: my files/tsv/gulliver_*.tsv (나눈 파일·합본 모두 읽음, 같은 ID 에 다른 번역이면 멈춤) · 원문 대응: work/trans/ids.tsv · ids_etc.tsv
  ① 대사(ID 00001‥): 쪽 단위로 바꿔 레코드를 다시 짠다(메시지·쪽 순서 그대로, LZ 재압축)
       · 음성 대사(원문이 r 로 시작): 번역에는 r·z·w 가 없다 → 원문 타이밍을 옮긴다(retime)
         원문 대기(w)의 위치를 «줄 안 글자 비율»로 새 글에 옮기고(가까운 공백·부호 뒤로), 대기 사이 구간마다
         «원문 구간 글자 시간(z 합) / 새 구간 글자 수» 를 z 로 — PoC 실기에서 속도 OK 확인한 방식의 일반화
       · 검사(하나라도 걸리면 빌드 중단): 코드 순서가 원문과 같은지(z·w·r 제외) · 인수 자리수 · 줄 수 ≤ max(3, 원문) ·
         줄 폭 ≤ max(19, 원문 최장 줄) 칸 · 쪽 바이트 ≤ 254 · 한글은 KS X 1001 2,350자만
       · 부호 뒤 공백은 뺀다(전프로젝트 규칙) · 반각 영숫자·부호는 전각으로(반각 ASCII 는 제어 코드로 읽힌다)
  ② 대사 밖(ID E00001‥): 제자리(원문 바이트 이하, 뒤는 00) — 아이템 이름(SYSDATA 레코드 1)만 포인터 표로 다시 채움(≤ 8칸)
  ③ 합치기: FONT.DAT(한글 2,350자) + work/kr/*(그림·동영상 — 대사 밖 글은 그 위에 덮음) → tools/iso.py (넘치는 파일만 끝으로)
  python tools/build.py            → 검사·통계만
  python tools/build.py --write    → work/out/ 트랙 1
"""
import collections, glob, os, re, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, r'C:\claude\project\anearth-kr-patch\tools')
import lz, msg, kenc, disc

TSV = os.environ.get('GB_TSV') or os.path.join(ROOT, 'my files', 'tsv')   # 시험용 번역 폴더는 GB_TSV 로
DISC = os.path.join(ROOT, 'work', 'disc1')
KR = os.path.join(ROOT, 'work', 'kr')
OUT = os.path.join(ROOT, 'work', 'out')
LINE_W, LINES = 19, 3
ARGS = {**{c: 0 for c in 'dehilnoqru'}, **{c: 1 for c in 'abckptv'}, **{c: 2 for c in 'fgjswxyz'}, 'm': 4}
VAR_W = {'a': 5, 'b': 5}                           # 이름 변수 폭(최장 동료 이름 «フィービー» 5칸)
ITEM_W, ITEM_MAX = 8, 8
ASCII2FULL = {**{chr(c): chr(c + 0xFEE0) for c in range(0x21, 0x7F)}, ' ': '　'}
# 전프로젝트 표준 부호 목록(2026-09-28 보강). 반각 { } 는 이 TSV 에서 토큰 문법이라 뺀다(전각 ｝ 는 넣음)
PUNCT = '！？。．、，…‥』」）!?.,~～' + ':;)]\'"' + '：；］｝】〉》”’・·〜♪♥'


# ─────────────────────────── 번역 읽기
def load_translations():
    tr = {}; where = {}; bad = []
    for p in sorted(glob.glob(os.path.join(TSV, 'gulliver_*.tsv'))):
        for n, ln in enumerate(open(p, encoding='utf-8'), 1):
            c = ln.rstrip('\n').split('\t')
            if n == 1 or len(c) < 6 or not c[5].strip():
                continue
            i, t = c[0], c[5]
            if i in tr and tr[i] != t:
                bad.append('%s: %s 와 %s 번역이 다름' % (i, where[i], os.path.basename(p)))
            tr[i] = t; where[i] = os.path.basename(p)
    if bad:
        raise SystemExit('⛔같은 ID 다른 번역\n' + '\n'.join(bad[:30]))
    return tr


def load_ids():
    dia = {}; etc = {}
    for ln in list(open(os.path.join(ROOT, 'work', 'trans', 'ids.tsv'), encoding='utf-8'))[1:]:
        c = ln.rstrip('\n').split('\t'); dia[c[0]] = bytes.fromhex(c[1])
    for ln in list(open(os.path.join(ROOT, 'work', 'trans', 'ids_etc.tsv'), encoding='utf-8'))[1:]:
        c = ln.rstrip('\n').split('\t')
        etc[c[0]] = (bytes.fromhex(c[1]), [(x.rsplit(':', 1)[0], int(x.rsplit(':', 1)[1])) for x in c[2:]])
    return dia, etc


# ─────────────────────────── 원문 토큰
def raw_tokens(b):
    """원문 바이트 → [('c', 2바이트) | ('n',) | ('k', 글자, 숫자열)] (대사 레코드 표기: 줄바꿈 = n 00)"""
    out = []; p = 0
    while p < len(b):
        c = b[p]
        if 0x81 <= c <= 0x9F or 0xE0 <= c <= 0xEF:
            out.append(('c', b[p:p + 2])); p += 2
        elif c == 0x6E and p + 1 < len(b) and b[p + 1] == 0:
            out.append(('n',)); p += 2
        elif c == 0x7B:
            out.append(('k', '{', b[p + 1:p + 4].decode())); p += 4
        elif c == 0x20:
            out.append(('c', b' ')); p += 1
        else:
            ch = chr(c); k = ARGS.get(ch, 0)
            out.append(('k', ch, b[p + 1:p + 1 + k].decode())); p += 1 + k
    return out


# ─────────────────────────── 번역 파싱·인코딩
TOK = re.compile(r'\\n|\{v([0-9]{3})\}|\{([a-z])([0-9]*)\}')


def squeeze(t):
    """부호(+ 특수 글리프 g00 !! · g01 !? · g02 ♪ · g03 ♥) 뒤 공백 «1칸»만 뺀다 — 2칸 이상은 칸 맞춤이라 둔다.
    조사 괄호 «은(는)·을(를)» 의 ) 는 부호가 아니다(뒤 띄어쓰기 유지)."""
    return re.sub(r'((?<!\([가-힣])(?<!\([가-힣]{2})[%s]|\{g0[0-3]\})((?:\{[zw][0-9]{2}\})*)[ 　](?![ 　])' % re.escape(PUNCT),
                  r'\1\2', t)


def quotes(t):
    """반각 ' " → ‘’ “”(여닫기 번갈아). 전각 ＇＂ 는 cp932 에서 0xEEFB·0xEEFC(IBM 확장) — 글꼴 밖이라 게임이 튕긴다(2026-09-28 실기)"""
    for a, (o, c) in (("'", '‘’'), ('"', '“”')):
        n = [0]
        def rep(m):
            n[0] += 1
            return o if n[0] % 2 else c
        t = re.sub(re.escape(a), rep, t)
    return t


def in_font(b):
    """cp932 2바이트 → 글꼴(FONT.DAT) 안인가: JIS X 0208 에 정의된 1‥7행(기호 453칸 = 94+14+62+83+86+48+66) ·
    16‥47행(1수준 한자 = 한글 자리)만. 8행(괘선)·NEC/IBM 확장은 없다. 0x06017816 글자 번호 함수 기준"""
    lead, tr = b[0], b[1]
    if not (0x81 <= lead <= 0x9F):
        return False
    try:
        b.decode('shift_jis')                     # 엄격한 JIS X 0208 — 행 안의 빈 칸 거름
    except UnicodeDecodeError:
        return False
    row = (lead - 0x81) * 2 + (1 if tr < 0x9F else 2)
    return 1 <= row <= 7 or 16 <= row <= 47


def parse(t, halfspace):
    """번역 글 → 토큰, 오류"""
    out = []; err = []; p = 0
    t = quotes(squeeze(t))
    while p < len(t):
        m = TOK.match(t, p)
        if m:
            if m.group() == '\\n':
                out.append(('n',))
            elif m.group(1):
                out.append(('k', '{', m.group(1)))
            else:
                ch, dg = m.group(2), m.group(3)
                if ch not in ARGS or len(dg) != ARGS[ch]:
                    err.append('코드 %s 인수 자리수(%s 는 %d자리)' % (m.group(), ch, ARGS.get(ch, -1)))
                out.append(('k', ch, dg))
            p = m.end(); continue
        ch = t[p]; p += 1
        if ch == ' ' and halfspace:
            out.append(('c', b' ')); continue
        ch = ASCII2FULL.get(ch, ch)
        if ch in kenc.IDX:
            out.append(('c', struct.pack('>H', kenc.sjis(ch))))
        else:
            try:
                b = ch.encode('cp932')
            except UnicodeEncodeError:
                err.append('글꼴에 없는 글자 %r' % ch); continue
            if len(b) != 2:
                err.append('반각 글자 %r' % ch); continue
            if '가' <= ch <= '힣':
                err.append('KS X 1001 밖 한글 %r' % ch); continue
            if not in_font(b):
                err.append('글꼴 밖 글자 %r (%s — 게임이 튕김)' % (ch, b.hex())); continue
            out.append(('c', b))
    return out, err


def encode(tokens, lone_n=False):
    b = bytearray()
    for t in tokens:
        if t[0] == 'c':
            b += t[1]
        elif t[0] == 'n':
            b += b'n' if lone_n else b'n\0'
        elif t[1] == '{':
            b += b'{' + t[2].encode()
        else:
            b += (t[1] + t[2]).encode()
    return bytes(b)


def lines_of(tokens):
    ls = [[]]
    for t in tokens:
        if t[0] == 'n':
            ls.append([])
        else:
            ls[-1].append(t)
    return ls


def choice_shape(lines):
    """첫 선택지 줄부터: 줄마다 [각 {o} 앞이 코드뿐인가] — 받은 번역의 줄바꿈 이동이 선택지를 질문 줄 뒤로 끌어올려
    «저주를 / 풀다» 처럼 깨졌다(2026-09-28 실기). 질문 줄 수는 달라도 된다"""
    out = []; on = False
    for l in lines:
        row = []
        for k, t in enumerate(l):
            if t[0] == 'k' and t[1] == 'o':
                row.append(all(x[0] == 'k' for x in l[:k]))
        on = on or bool(row)
        if on:
            out.append(row)
    return out


def width(line):
    w = 0
    for t in line:
        if t[0] == 'c':
            w += 1
        elif t[1] == 'g':
            w += 1
        elif t[1] in VAR_W:
            w += VAR_W[t[1]]
        elif t[1] == '{':
            w += ITEM_W
    return w


def disp(t):
    return t[0] == 'c' or (t[0] == 'k' and t[1] == 'g')


# ─────────────────────────── 음성 대사 타이밍
def retime(orig, new):
    """orig/new 토큰(new 에는 z·w·r 없음) → r + z/w 를 끼운 new"""
    # 원문: 줄마다 (글자 수, 글자 시간 목록, 대기 [(글자 위치, 값)])
    def scan(tokens):
        L = [{'n': 0, 'z': [], 'w': []}]; z = 0
        for t in tokens:
            if t[0] == 'n':
                L.append({'n': 0, 'z': [], 'w': []})
            elif t[0] == 'k' and t[1] == 'z':
                z = int(t[2])
            elif t[0] == 'k' and t[1] == 'w':
                L[-1]['w'].append((L[-1]['n'], int(t[2])))
            elif disp(t):
                L[-1]['z'].append(z); L[-1]['n'] += 1
        return L
    OL = scan(orig)
    NL = lines_of(new)
    if len(OL) != len(NL):                          # 줄 수가 다르면 한 줄로 보고 옮긴다
        flat = {'n': 0, 'z': [], 'w': []}
        for l in OL:
            for pos, v in l['w']:
                flat['w'].append((flat['n'] + pos, v))
            flat['z'] += l['z']; flat['n'] += l['n']
        OLm = [flat]; groups = [list(range(len(NL)))]
    else:
        OLm = OL; groups = [[i] for i in range(len(NL))]
    out = [('k', 'r', '')]
    first = True
    for ol, g in zip(OLm, groups):
        toks = []
        for gi, li in enumerate(g):
            if gi:
                toks.append(('n',))
            toks += NL[li]
        nd = sum(1 for t in toks if disp(t))
        # 대기 위치 옮기기
        waits = collections.defaultdict(list)
        for pos, v in ol['w']:
            q = round(pos * nd / ol['n']) if ol['n'] else nd
            waits[q].append(v)
        # 대기 사이 구간 속도
        cuts = sorted({0, ol['n']} | {p for p, _ in ol['w']})
        segs = []
        for a, b in zip(cuts, cuts[1:]):
            T = sum(ol['z'][a:b]); qa = round(a * nd / ol['n']) if ol['n'] else 0; qb = round(b * nd / ol['n']) if ol['n'] else nd
            segs.append((qa, qb, T))
        def speed(q):
            for qa, qb, T in segs:
                if qa <= q < qb:
                    return 0 if T == 0 else max(1, min(99, round(T / max(1, qb - qa))))
            return 0
        if first:
            out.append(('k', 'z', '00')); first = False
        cur = 0; zc = None
        for t in toks:
            if t[0] == 'n':
                for v in waits.pop(cur, []):
                    out.append(('k', 'w', '%02d' % min(99, v)))
                out.append(t); continue
            if disp(t):
                for v in waits.pop(cur, []):
                    out.append(('k', 'w', '%02d' % min(99, v)))
                z = speed(cur)
                if z != zc:
                    out.append(('k', 'z', '%02d' % z)); zc = z
                out.append(t); cur += 1
            else:
                out.append(t)
        for q in sorted(waits):
            for v in waits[q]:
                out.append(('k', 'w', '%02d' % min(99, v)))
        if len(OLm) > 1 and ol is not OLm[-1]:
            out.append(('n',))
    return out


# ─────────────────────────── ① 대사
def build_dialogue(tr, dia, log):
    newpage = {}; errs = []
    for i, raw in dia.items():
        if i not in tr:
            continue
        orig = raw_tokens(raw)
        voiced = raw[:1] == b'r'
        toks, err = parse(tr[i], halfspace=b' ' in raw)
        errs += ['%s %s' % (i, e) for e in err]
        if err:
            continue
        ocodes = [t[1:] for t in orig if t[0] == 'k' and not (voiced and t[1] in 'rzw')]
        ncodes = [t[1:] for t in toks if t[0] == 'k']
        if voiced and any(t[0] in 'rzw' for t in ncodes):
            errs.append('%s 음성 대사 번역에 r·z·w 가 있다(빌더가 넣는다)' % i); continue
        if ocodes != ncodes:
            errs.append('%s 코드가 원문과 다름: 원문 %s / 번역 %s' % (i, [''.join(c) for c in ocodes], [''.join(c) for c in ncodes])); continue
        ol = lines_of(orig); nl = lines_of(toks)
        if choice_shape(ol) != choice_shape(nl):
            errs.append('%s 선택지 줄 구조가 원문과 다름(선택지는 원문처럼 줄 맨 앞·같은 묶음 — 질문 줄 수만 바뀔 수 있음)' % i); continue
        maxw = max(LINE_W, max(width(l) for l in ol)); maxl = max(LINES, len(ol))
        if len(nl) > maxl:
            errs.append('%s 줄 수 %d > %d' % (i, len(nl), maxl)); continue
        over = [(k, width(l)) for k, l in enumerate(nl) if width(l) > maxw]
        if over:
            errs.append('%s 줄 폭 초과 %s (최대 %d칸)' % (i, over, maxw)); continue
        if voiced:
            toks = retime(orig, toks)
        b = encode(toks)
        if len(b) + 1 > 255:
            errs.append('%s 쪽 %d바이트 > 254' % (i, len(b))); continue
        newpage[raw] = b
    return newpage, errs


def rebuild_dialog_record(t, newpage):
    out = bytearray(); p = 0
    while t[p:] not in (b'\0\0', b'\0'):
        n = t[p]; out.append(n); p += 1
        for _ in range(n):
            L = t[p]; b = t[p + 1:p + L]
            nb = newpage.get(b, b)
            out += bytes([len(nb) + 1]) + nb + b'\0'
            p += 1 + L
    return bytes(out) + t[p:]


# ─────────────────────────── ② 대사 밖
def build_etc(tr, etc, log):
    """→ {(파일, 레코드 태그): [(오프셋, 원문길이, 새 바이트)]}, 아이템 이름 {원문: 새}, 오류"""
    edits = collections.defaultdict(list); items = {}; errs = []
    for i, (raw, locs) in etc.items():
        if i not in tr:
            continue
        lone = b'n' in raw and b'n\0' not in raw
        toks, err = parse(tr[i], halfspace=False)
        errs += ['%s %s' % (i, e) for e in err]
        if err:
            continue
        # 전투 설정 레코드의 적 이름 «이름!»(tools/addenemy.py): «!» 까지가 이름(화면엔 안 나옴) → 떼고 비교, 새 이름 뒤에 다시 붙임
        bang = raw.endswith(b'!')
        ocodes = [t[1:] for t in raw_tokens_etc(raw[:-1] if bang else raw) if t[0] == 'k']
        ncodes = [t[1:] for t in toks if t[0] == 'k']
        if ocodes != ncodes:
            errs.append('%s 코드가 원문과 다름: 원문 %s / 번역 %s' % (i, [''.join(c) for c in ocodes], [''.join(c) for c in ncodes])); continue
        b = encode(toks, lone_n=True) + (b'!' if bang else b'')
        # 실행 파일 이름 표(0x5CB00‥0x5CC00, 상태창 이름 등): 셀 할당이 «폭÷8 버림» 이라 12px 글자 수가 홀수면
        # 다음 글줄(HP)이 이름 마지막 열 셀을 겹쳐 받아 찌꺼기가 생긴다(2026-09-27 실기) → 전각 공백으로 짝수 칸
        b_even = encode(toks + [('c', '　'.encode('cp932'))], lone_n=True) if width([t for t in toks if t[0] != 'n']) % 2 else b
        b_plain = b
        for loc, L in locs:
            # 짝수 채움은 자리에 들어갈 때만(원문부터 홀수 칸인 «　呪いd» 같은 줄은 원문과 같은 조건이라 그냥 둔다)
            b = b_even if loc.startswith('1ST_READ-raw-') and 0x5CB00 <= int(loc.rsplit('-', 1)[1], 16) < 0x5CC00 and len(b_even) <= L else b_plain
            f, tag, off = loc.rsplit('-', 2)
            if f == 'SYSDATA' and tag == '1':
                if width(toks) > ITEM_MAX:
                    errs.append('%s 아이템 이름 %d칸 > %d' % (i, width(toks), ITEM_MAX))
                items[raw] = b
                continue
            if len(b) > L:
                errs.append('%s %s 자리 %dB < 번역 %dB' % (i, loc, L, len(b))); continue
            edits[(f, tag)].append((int(off, 16), L, b))
    edits[('1ST_READ', 'raw')] += raw_char_edits()
    return edits, items, errs


def raw_tokens_etc(b):
    """대사 밖 원문(단독 n 줄바꿈, 코드 = 글자 + 숫자 0‥3)"""
    out = []; p = 0
    while p < len(b):
        c = b[p]
        if c >= 0x81:
            out.append(('c', b[p:p + 2])); p += 2
        elif c == 0x6E:
            out.append(('n',)); p += 1
        elif c == 0x7B:
            out.append(('k', '{', b[p + 1:p + 4].decode())); p += 4
        else:
            k = ARGS.get(chr(c))                  # 인수 자리수를 아는 코드(m = 4자리 «dm1501» 등)는 그만큼
            if k and b[p + 1:p + 1 + k].isdigit():
                out.append(('k', chr(c), b[p + 1:p + 1 + k].decode())); p += 1 + k; continue
            m = re.match(rb'[a-z][0-9]{0,3}', b[p:])
            out.append(('k', chr(c), m.group()[1:].decode())); p += m.end()
    return out


# 실행 파일 안 글자만 제자리로 바꾸는 곳(반각 기호·숫자가 섞여 TSV 로 못 다루는 문자열, 2026-09-28)
#   (오프셋, 원래 글자, 한글) — 원래 바이트가 다르면 빌드 중단
RAW_CHARS = [
    (0x60960, '攻', '공'), (0x60964, '防', '방'), (0x6096E, '賢', '지'), (0x60972, '早', '속'), (0x6097C, '体', '체'),   # 능력치 머리
    (0x609F4, 'バ', '배'), (0x609F6, 'リ', '리'), (0x609F8, 'ア', '어'),                                              # «バリア 0d»
]


# 추출기가 앞부분을 놓친 실행 파일 문자열(칸 맞춤 반각 공백·코드가 섞여 TSV 로 못 다룸, 2026-09-28 tools/findmissed.py)
#   (문자열 시작, 일본어 구간, 한글) — 구간만 제자리로 바꾸고 남는 바이트는 반각 공백. 한글 쪽 공백은 전각으로 쓸 것
RAW_TEXT = [
    (0x5F546, 'を捨てます。', '　버립니다．'), (0x5F546, 'よろしいですか？', '괜찮습니까？'), (0x5F546, 'はい', '예'),
    (0x5F5A4, 'もう', '더는'),
    (0x5F5C8, '持ち物が', '소지품이'),
    (0x5FA3C, 'セーブします。よろしいですか？', '저장합니다．괜찮습니까？'), (0x5FA3C, 'はい', '예'),
    (0x5FAA0, 'バックアップメモリが足りません。', '백업　메모리가　부족합니다．'),
    (0x5FB18, 'ロードします。よろしいですか？', '불러옵니다．괜찮습니까？'), (0x5FB18, 'はい', '예'),
    (0x5FB5C, 'データがこわれています。', '데이터가　깨졌습니다．'), (0x5FB5C, 'ロードすることはできません。', '불러올　수　없습니다．'),
    (0x5FCA4, '左右で選択', '좌우：선택'), (0x5FCA4, 'で決定', '：결정'), (0x5FCA4, 'でキャンセル', '：취소'),
    (0x5FCFC, '左右で選択', '좌우：선택'), (0x5FCFC, 'で決定', '：결정'), (0x5FCFC, 'でキャンセル', '：취소'),
    (0x60760, 'は', '：'), (0x60778, 'は', '：'),
    (0x5CB28, '毒', '독'), (0x609DC, '毒', '독'),
]


def enc_kr(t):
    b = bytearray()
    for ch in t:
        b += struct.pack('>H', kenc.sjis(ch)) if ch in kenc.IDX else ch.encode('cp932')
    return bytes(b)


def raw_char_edits():
    d = open(os.path.join(DISC, '1ST_READ.PRG'), 'rb').read()
    out = []
    for off, a, h in RAW_CHARS:
        if d[off:off + 2] != a.encode('cp932'):
            sys.exit('⛔RAW_CHARS 0x%X: 원래 글자 %r 아님(%s)' % (off, a, d[off:off + 2].hex()))
        out.append((off, 2, struct.pack('>H', kenc.sjis(h))))
    for s0, a, h in RAW_TEXT:
        end = d.index(b'\0', s0); ja = a.encode('cp932'); off = d.find(ja, s0, end)
        kb = enc_kr(h)
        if off < 0 or len(kb) > len(ja) or not all(in_font(kb[k:k + 2]) for k in range(0, len(kb), 2)):
            sys.exit('⛔RAW_TEXT 0x%X %r: 원문 없음·길이 초과·글꼴 밖 (%d > %d)' % (s0, a, len(kb), len(ja)))
        out.append((off, len(ja), kb + b' ' * (len(ja) - len(kb))))
    return out


def rebuild_items(r, items):
    """SYSDATA 레코드 1: 이름 풀 다시 채우기(포인터 u32 @ 0x10 + 16k, 이름 0x1004‥, 4바이트 정렬 FF 채움)"""
    r = bytearray(r)
    ptrs = []; k = 0
    while 0x10 + 16 * k + 4 <= 0x1000:
        q = struct.unpack_from('>I', r, 0x10 + 16 * k)[0]
        if not 0x1000 <= q < len(r):
            break
        ptrs.append(q); k += 1
    names = {}
    for q in sorted(set(ptrs)):
        e = r.index(b'\0', q); names[q] = bytes(r[q:e])
    pool = bytearray(); newoff = {}; seen = {}
    base = 0x1004 if 0x1000 not in names else 0x1000
    for q in sorted(names):
        s = items.get(names[q], names[q])
        if s in seen:
            newoff[q] = seen[s]; continue
        off = base + len(pool)
        pool += s + b'\0'
        pool += b'\xff' * (-len(pool) % 4)
        newoff[q] = seen[s] = off
    end = len(r)                                     # 레코드는 길이로 걸어 찾는다(0x0601331E) → 풀이 길어져도 된다
    r[base:] = pool + b'\xff' * max(0, end - base - len(pool))
    for k, q in enumerate(ptrs):
        struct.pack_into('>I', r, 0x10 + 16 * k, newoff[q])
    return bytes(r)


# ─────────────────────────── 파일 다시 짜기
def rebuild_file(d, repl):
    """{레코드 번호: 새 내용(LZ 레코드는 풀린 내용)}"""
    R = msg.records(d)
    out = bytearray(); p = 0
    for k, (i, L, o, r) in enumerate(R):
        out += d[p:i]
        if k in repl and repl[k] != (o if o is not None else r):
            if o is not None:
                c = lz.enc(repl[k]); c += bytes(-len(c) % 4)
                out += struct.pack('>II', len(c) + 4, len(repl[k])) + c
            else:
                c = repl[k] + bytes(-len(repl[k]) % 4)
                out += struct.pack('>I', len(c)) + c
        else:
            out += d[i:i + 4 + L]
        p = i + 4 + L
    out += d[p:]
    return bytes(out)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    tr = load_translations()
    dia, etc = load_ids()
    nd = sum(1 for i in dia if i in tr); ne = sum(1 for i in etc if i in tr)
    print('번역: 대사 %d/%d · 대사 밖 %d/%d' % (nd, len(dia), ne, len(etc)))
    newpage, e1 = build_dialogue(tr, dia, print)
    edits, items, e2 = build_etc(tr, etc, print)
    errs = e1 + e2
    if errs:
        print('⛔검사 오류 %d건' % len(errs))
        for e in errs[:60]:
            print('  ' + e)
        raise SystemExit(1)
    # 파일별 적용
    files = {}; grow = []
    touched = collections.defaultdict(dict)
    for fn, k, m in msg.blocks():
        if any(b in newpage for _, pages in m for b in pages):
            touched[fn][k] = 'dialog'
    for (f, tag) in edits:
        fn = next(x for x in os.listdir(DISC) if x.rsplit('.', 1)[0] == f)
        touched[fn][tag] = 'etc'
    if items:
        touched['SYSDATA.BIN']['items'] = 'items'
    for fn in sorted(touched):
        base = os.path.join(KR, fn) if os.path.exists(os.path.join(KR, fn)) else os.path.join(DISC, fn)
        d = open(base, 'rb').read()
        R = msg.records(d)
        if any(tag == 'raw' for tag in touched[fn]):
            nd_ = bytearray(d)
            for off, L, b in edits[(fn.rsplit('.', 1)[0], 'raw')]:
                nd_[off:off + L] = b + bytes(L - len(b))
            files[fn] = bytes(nd_); continue
        repl = {}
        for k, (i, L, o, r) in enumerate(R):
            cur = o if o is not None else r
            if touched[fn].get(k) == 'dialog':
                cur = rebuild_dialog_record(cur, newpage)
            for tag in (str(k), '%dz' % k):
                for off, L2, b in edits.get((fn.rsplit('.', 1)[0], tag), []):
                    cur = cur[:off] + b + bytes(L2 - len(b)) + cur[off + L2:]
            if fn == 'SYSDATA.BIN' and k == 1 and items:
                cur = rebuild_items(cur, items)
            if cur != (o if o is not None else r):
                repl[k] = cur
                if o is not None and len(cur) > len(o):
                    grow.append((len(cur) - len(o), fn, k, len(o), len(cur)))
        files[fn] = rebuild_file(d, repl)
        if fn == 'SYSDATA.BIN':                      # RAM 0x00228000‥0x00248000(다음 = STARTUP 자리) 안
            assert len(files[fn]) <= 0x20000, ('SYSDATA 가 적재 구역을 넘는다', len(files[fn]))
    # 그림·동영상(work/kr) 중 글로 안 건드린 것
    for fn in os.listdir(KR):
        files.setdefault(fn, open(os.path.join(KR, fn), 'rb').read())
    import poc
    files['FONT.DAT'] = poc.font()
    print('바꾼 파일 %d개' % len(files))
    for g in sorted(grow, reverse=True)[:8]:
        print('  ⚠레코드 커짐 +%d B  %s 레코드 %d (%d → %d)' % g)
    if '--write' not in sys.argv:
        print('검사 끝 — 쓰려면 --write'); return
    import iso
    os.makedirs(OUT, exist_ok=True)
    for n in (1, 2):                                  # 두 장의 공통 파일은 바이트까지 같다(CPK 배분만 다름) → 같은 파일을 양쪽에
        D = disc.Disc(n); src = D.path
        have = {nm for nm, _, _, _ in D.files()}; D.f.close()
        fs = {k: v for k, v in files.items() if k in have}
        dst = os.path.join(OUT, os.path.basename(src))
        print('%d장: 파일 %d개 (없어서 건너뜀 %s)' % (n, len(fs), sorted(set(files) - have)))
        iso.patch(src, dst, fs, log=lambda s: None if 'LBA' in s and '옮김' not in s else print(s))
        iso.verify(dst, fs)
        print('→', dst)


if __name__ == '__main__':
    main()
