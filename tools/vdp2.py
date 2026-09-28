# -*- coding: utf-8 -*-
r"""세이브스테이트 VDP2 NBG0‥3 그리기(걸리버 메뉴 화면 기준: 4bpp·셀 1×1·패턴 이름 2워드·면 1×1)
  python tools/vdp2.py  → work/mem/nbgN.png (512×512, 스크롤 무시) + nbgN_map.txt
"""
import os, struct, sys
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
M = os.path.join(ROOT, 'work', 'mem', os.environ.get('MEM', ''))
V = open(os.path.join(M, 'VDP2_VRAM.bin'), 'rb').read()
C = open(os.path.join(M, 'CRAM.bin'), 'rb').read()
R = struct.unpack('>256H', open(os.path.join(M, 'VDP2_REGS.bin'), 'rb').read())


def color(i):
    c = C[(i * 2 + 1) & 0xFFF] << 8 | C[(i * 2) & 0xFFF] if os.environ.get("CLE") else C[(i * 2) & 0xFFF] << 8 | C[(i * 2 + 1) & 0xFFF]
    return ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3)


def cell(ch, pal):
    a = ch * 32; out = []
    for y in range(8):
        row = []
        for x in range(8):
            b = V[(a + y * 4 + x // 2) & 0x7FFFF]
            v = b >> 4 if x % 2 == 0 else b & 15
            row.append(None if v == 0 else pal * 16 + v)
        out.append(row)
    return out


def nbg(n):
    mp = R[(0x40 + 4 * n) // 2] & 0x3F           # 면 A
    base = mp * int(os.environ.get("PAGE", "8192"))
    im = Image.new('RGB', (512, 512)); px = im.load(); cells = []
    for ty in range(64):
        for tx in range(64):
            w0, w1 = struct.unpack_from('>HH', V, base + (ty * 64 + tx) * 4)
            ch = w1 & 0x7FFF; pal = w0 & 0x7F; hf, vf = w0 >> 14 & 1, w0 >> 15 & 1
            cells.append((tx, ty, ch, pal, w0))
            c = cell(ch, pal)
            for y in range(8):
                for x in range(8):
                    v = c[7 - y if vf else y][7 - x if hf else x]
                    if v is not None:
                        px[tx * 8 + x, ty * 8 + y] = color(v)
    return im, base, cells


if __name__ == '__main__':
    for n in range(4):
        im, base, cells = nbg(n)
        im.save(os.path.join(M, 'nbg%d.png' % n))
        print('NBG%d 맵 0x%05X' % (n, base))
