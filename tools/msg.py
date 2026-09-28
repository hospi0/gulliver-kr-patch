# -*- coding: utf-8 -*-
r"""걸리버 보이 대사 — 파일 = [u32 BE 길이 L][내용 L] 레코드의 연속(끝 0000_0000). 내용은 LZ 조각([원래크기][압축]) 또는 날것.
  대사 레코드(풀린 내용) = 메시지의 연속, 끝 00 00:
    메시지 = [u8 쪽 수 N] + N × ([u8 쪽 길이 = 글 바이트 + 끝 00][글…][00])
  글: SJIS 2바이트 · «n 00» 줄바꿈 · «g 숫자2» · «z 숫자2» · o · c 숫자 · i (선택지 등 제어, 아직 뜻 미확정)
  python tools/msg.py stats   → 파일별 메시지·글자 수, 줄 폭 분포
"""
import os, re, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import lz

DISC = os.path.join(ROOT, 'work', 'disc1')


def records(d):
    """[(위치, 길이, 풀린 내용 또는 None, 날것)]"""
    out = []; i = 0
    while i + 4 <= len(d):
        L = struct.unpack_from('>I', d, i)[0]
        if L == 0 or i + 4 + L > len(d):
            break
        raw = d[i + 4:i + 4 + L]
        o = None
        if L >= 8:
            n = struct.unpack_from('>I', d, i + 4)[0]
            if n < 0x200000:
                o = lz.dec(d, i + 8, L - 4, n)
        out.append((i, L, o, raw)); i += 4 + L
    return out


def page_ok(b):
    """쪽 글이 SJIS·제어로 끝까지 읽히나"""
    p = 0
    while p < len(b):
        c = b[p]
        if 0x81 <= c <= 0x9F or 0xE0 <= c <= 0xEF:
            if p + 1 >= len(b):
                return False
            p += 2
        elif c == 0x6E and p + 1 < len(b) and b[p + 1] == 0:
            p += 2
        elif 0x20 <= c < 0x7F:
            p += 1
        else:
            return False
    return True


def messages(t):
    """대사 레코드면 [(위치, [쪽 바이트…])], 아니면 None"""
    out = []; p = 0
    while p < len(t):
        if t[p:] in (b'\0\0', b'\0'):
            return out if out else None
        n = t[p]; s = p; p += 1; pages = []
        if n == 0 or n > 16:
            return None
        for _ in range(n):
            if p >= len(t):
                return None
            L = t[p]
            if L < 1 or p + 1 + L > len(t) or t[p + L] != 0:
                return None
            b = t[p + 1:p + L]
            if not page_ok(b):
                return None
            pages.append(b); p += 1 + L
        out.append((s, pages))
    return None


def show(b):
    out = []; p = 0
    while p < len(b):
        c = b[p]
        if 0x81 <= c <= 0x9F or 0xE0 <= c <= 0xEF:
            out.append(b[p:p + 2].decode('cp932', 'replace')); p += 2
        elif c == 0x6E and p + 1 < len(b) and b[p + 1] == 0:
            out.append('\\n'); p += 2
        else:
            out.append(chr(c)); p += 1
    return ''.join(out)


def blocks():
    """(파일, 레코드 번호, 메시지 목록) — 대사 레코드 전부"""
    for fn in sorted(os.listdir(DISC)):
        d = open(os.path.join(DISC, fn), 'rb').read()
        for k, (i, L, o, raw) in enumerate(records(d)):
            if o is None:
                continue
            m = messages(o)
            if m:
                yield fn, k, m


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if sys.argv[1:] == ['stats']:
        import collections
        W = collections.Counter(); files = collections.Counter(); nm = 0; ch = 0; uniq = set()
        for fn, k, m in blocks():
            for s, pages in m:
                nm += 1
                for b in pages:
                    t = show(b); uniq.add(t)
                    body = re.sub(r'[a-z][0-9]{2}|[a-z]', '', t.replace('\\n', '\n'))
                    ch += len(body.replace('\n', '')); files[fn] += 1
                    for line in body.split('\n'):
                        W[len(line)] += 1
        print('메시지', nm, '글자', ch, '서로 다른 쪽', len(uniq), '파일', len(files))
        print('줄 폭 분포(칸:줄 수)', sorted(W.items())[-12:])
