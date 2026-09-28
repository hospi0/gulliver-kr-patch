# -*- coding: utf-8 -*-
r"""대사 밖 글 추출 (2026-09-27) — 대사 레코드(tools/extract.py)가 아닌 곳의 SJIS 문자열
  대상: 레코드 파일의 «대사 형식이 아닌» 레코드(날것·LZ) + 레코드 구조가 아닌 파일(1ST_READ.PRG 등) 통째
  문자열 = NUL(스태프롤처럼 CRLF 가 많은 조각은 CRLF)로 끝나는 «SJIS 2바이트 · ASCII 코드(글자 + 숫자 0‥3자리) · {NNN» 의 연속.
    시작 = 그 조각에서 끝까지 코드·글자로만 이어지는 가장 앞 SJIS(앞의 비문자 바이트는 버림).
    이벤트 스크립트(STARTUP·C1A 레코드 1 등)는 k1 z00 r q w16 … 코드와 «n»(뒤에 00 없음) 줄바꿈을 쓴다.
  아이템 이름(SYSDATA 레코드 1)은 포인터 표로 전부.
  그림 조각 거르기: 두 글자면 가나 둘, 반복 부호(ゝ・，…) 절반 이상이면 버림, 글자가 전부 가나·전각 부호·전각 영숫자·제1수준 한자이고, 가나 1자 이상, 2자 이상.
  → my files/tsv/gulliver_etc_NNN.tsv (29KB, 열: ID 위치 구분 공유 원문 번역) · work/trans/ids_etc.tsv (ID → 원문 바이트·위치:길이)
  위치 = 파일-레코드(z = LZ, raw = 파일 통째)-오프셋(hex) · 구분 = 종류 «최대 N바이트»(제자리 기준 원문 바이트 수)
  표기: 단독 n → \n · 그 밖의 코드 {k1}{z00}{q}… · {NNN → {vNNN}
  python tools/extract_other.py
"""
import collections, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import msg

CHUNK = 29 * 1024
TOK = re.compile(rb'[\x81-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc]|[a-z][0-9]{0,3}|\{[0-9]{3}')
PUNCT = set('　、。，．・：；？！゛゜ー―‐…‥「」『』（）［］〔〕＋－×÷＝＜＞％＆＊＠☆★○●◎◇◆□■△▲▽▼※〒～／＃＄')


def good_char(ch):
    o = ord(ch)
    if 0x3041 <= o <= 0x30FE or ch in PUNCT or 0xFF10 <= o <= 0xFF5A:
        return True
    try:
        b = ch.encode('cp932')
    except UnicodeEncodeError:
        return False
    return len(b) == 2 and 0x889F <= (b[0] << 8 | b[1]) <= 0x9872   # 제1수준 한자


def strings(b, crlf=False):
    """[(오프셋, 바이트)]"""
    out = []
    sep = b'\r\n' if crlf else b'\x00'
    prev = 0
    while True:
        e = b.find(sep, prev)
        if e < 0:
            break
        seg = b[prev:e]; base = prev; prev = e + len(sep)
        for s0 in range(len(seg)):
            if seg[s0] < 0x81:
                continue
            p = s0
            while p < len(seg):
                m = TOK.match(seg, p)
                if not m:
                    break
                p = m.end()
            if p == len(seg) and plausible(seg[s0:]):
                out.append((base + s0, seg[s0:])); break
    return out


def fmt(raw):
    out = []; p = 0
    while p < len(raw):
        m = TOK.match(raw, p); t = m.group(); p = m.end()
        if t[0] >= 0x81:
            out.append(t.decode('cp932', 'replace'))
        elif t == b'n':
            out.append('\\n')
        elif t[:1] == b'{':
            out.append('{v%s}' % t[1:].decode())
        else:
            out.append('{%s}' % t.decode())
    return ''.join(out)


def plausible(raw):
    body = re.sub(r'\\n|\{[^}]*\}', '', fmt(raw))
    if len(body) < 2 or not all(good_char(c) for c in body):
        return False
    if re.match(r'.\{v', fmt(raw)):                 # «茶{012リポン» = SJIS 뒷바이트 0x7B 를 코드로 오독한 조각
        return False
    kana = [c for c in body if 0x3041 <= ord(c) <= 0x30FE and c not in 'ゝゞヽヾ']
    if len(body) == 2 and len(kana) < 2:             # 두 글자 조각(«裾ワ»)은 가나 둘일 때만
        return False
    if sum(1 for c in body if c in 'ゝゞヽヾ・，、。『』') * 2 >= len(body):
        return False
    return len(kana) >= 1


def item_names(r):
    """SYSDATA 레코드 1: 16바이트 항목의 u32 이름 포인터(가나 없는 이름도 모두)"""
    import struct
    out = []; k = 0
    while 0x10 + 16 * k + 4 <= 0x1000:
        q = struct.unpack_from('>I', r, 0x10 + 16 * k)[0]
        if not 0x1000 <= q < len(r):
            break
        e = r.index(b'\0', q)
        if e > q:
            out.append((q, r[q:e]))
        k += 1
    return out


def blobs():
    for fn in sorted(os.listdir(msg.DISC)):
        if fn.endswith('.CPK'):
            continue
        d = open(os.path.join(msg.DISC, fn), 'rb').read()
        R = msg.records(d)
        if R and sum(4 + L for _, L, _, _ in R) + 4 >= len(d) - 8:
            for k, (i, L, o, r) in enumerate(R):
                if o is not None and msg.messages(o):
                    continue
                yield fn, '%d%s' % (k, 'z' if o is not None else ''), (o if o is not None else r)
        else:
            yield fn, 'raw', d


def kind(fn, tag, text, crlf):
    if crlf:
        return '스태프롤'
    if fn == '1ST_READ.PRG':
        return '실행파일'
    if fn == 'SYSDATA.BIN':
        return {'1': '아이템', '2': '마법'}.get(tag, '시스템')
    if fn == 'STARTUP.BIN':
        return '시스템'
    if '{' in text or '\\n' in text:
        return '스크립트'
    if fn.startswith(('BM', 'D', 'V', 'CS0', 'C000', 'C200')) and tag in ('9z', '10z', '21z', '22z'):
        return '이름표'
    if fn.startswith('C') and len(text) <= 12:
        return '지명·이름'
    return '기타'


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    seen = {}; rows = []
    for fn, tag, b in blobs():
        crlf = b.count(b'\r\n') > 20
        found = item_names(b) if (fn, tag) == ('SYSDATA.BIN', '1') else strings(b, crlf)
        for off, raw in found:
            loc = '%s-%s-%X' % (fn.rsplit('.', 1)[0], tag, off)
            if raw in seen:
                seen[raw][1].append((loc, len(raw))); continue
            text = fmt(raw)
            seen[raw] = (len(rows), [(loc, len(raw))]); rows.append((kind(fn, tag, text, crlf), text, raw))
    os.makedirs(os.path.join(ROOT, 'work', 'trans'), exist_ok=True)
    with open(os.path.join(ROOT, 'work', 'trans', 'ids_etc.tsv'), 'w', encoding='utf-8') as f:
        f.write('ID\t원문바이트(hex)\t위치:길이…\n')
        for i, (k, text, raw) in enumerate(rows):
            f.write('E%05d\t%s\t%s\n' % (i + 1, raw.hex(), '\t'.join('%s:%d' % x for x in seen[raw][1])))
    tdir = os.path.join(ROOT, 'my files', 'tsv')
    for f in os.listdir(tdir):
        if f.startswith('gulliver_etc_'):
            os.remove(os.path.join(tdir, f))
    head = 'ID\t위치\t구분\t공유\t원문\t번역\n'
    files = []; buf = head
    for i, (k, text, raw) in enumerate(rows):
        locs = seen[raw][1]
        line = 'E%05d\t%s\t%s 최대%dB\t%d\t%s\t\n' % (i + 1, locs[0][0], k, len(raw), len(locs), text)
        if len((buf + line).encode('utf-8')) > CHUNK and buf != head:
            files.append(buf); buf = head
        buf += line
    files.append(buf)
    for n, t in enumerate(files):
        open(os.path.join(tdir, 'gulliver_etc_%03d.tsv' % (n + 1)), 'w', encoding='utf-8').write(t)
    C = collections.Counter(k for k, _, _ in rows); chars = collections.Counter()
    for k, text, _ in rows:
        chars[k] += len(re.sub(r'\{[^}]*\}|\\n', '', text))
    print('문장 %d · 글자 %d · 파일 %d개' % (len(rows), sum(chars.values()), len(files)))
    for k in C:
        print('  %-6s %4d문장 %5d자' % (k, C[k], chars[k]))


if __name__ == '__main__':
    main()
