# -*- coding: utf-8 -*-
r"""한글 → SJIS 코드 · 글꼴 칸 (2026-09-27)
  한글 2,350자(KS X 1001 순서) = 1수준 한자 JIS 번호 0x582 + i → SJIS 889F‥
  글꼴 칸 = JIS 번호 − 957 (0x06017816 글자 번호 함수) = 453 + i  → FONT.DAT 16×16 1bpp 32B/칸
  글: «\n» 줄바꿈(6E 00) · 제어 코드 r · zNN · wNN · gNN · o · i · cN 는 ASCII 그대로 · 공백은 전각
"""
import re, struct

HANGUL = [bytes([a, b]).decode('cp949') for a in range(0xB0, 0xC9) for b in range(0xA1, 0xFF)]
IDX = {c: i for i, c in enumerate(HANGUL)}
JIS0, CELL0 = 0x582, 453
CODE = re.compile(r'r|[zwg][0-9]{2}|\\n')


def jis_to_sjis(n):
    row, col = n // 94 + 1, n % 94 + 1          # 구점(1부터)
    lead = (row + 1) // 2 + (0x80 if row <= 62 else 0xC0)
    if row & 1:
        tr = col + 0x3F + (1 if col >= 64 else 0)
    else:
        tr = col + 0x9E
    return lead << 8 | tr


def sjis(ch):
    return jis_to_sjis(JIS0 + IDX[ch])


def encode(t):
    out = bytearray(); p = 0
    while p < len(t):
        m = CODE.match(t, p)
        if m:
            out += b'n\0' if m.group() == '\\n' else m.group().encode(); p = m.end(); continue
        ch = t[p]; p += 1
        if ch == ' ':
            ch = '　'
        if ch in IDX:
            out += struct.pack('>H', sjis(ch))
        else:
            b = ch.encode('cp932')
            assert len(b) == 2, ('반각 글자는 제어 코드로 읽힌다', ch)
            out += b
    return bytes(out)


assert jis_to_sjis(0x582) == 0x889F and sjis('가') == 0x889F
