# -*- coding: utf-8 -*-
r"""걸리버 보이 — 세이브스테이트 NBG1 맵에서 파란 버튼 셀 배치 읽기 (2026-09-28)
  python tools/menumap.py m_main m_item …   (work/mem/<이름> — tools/state.py 로 먼저 풀기)
  버튼 셀 = VRAM 셀 0x80+(SYSDATA 레코드 9 셀) · 한 버튼 = 위·아래 2줄 × 3열, 셀 순서 «열마다 위·아래»
  출력: 줄마다 (열, 레코드 셀 위/아래, 팔레트) — 레코드 9 밖 셀도 같이 보여 준다(다른 파일 버튼 찾기용)
"""
import os, struct, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = 16384


def load(name):
    d = os.path.join(ROOT, 'work', 'mem', name)
    V = open(os.path.join(d, 'VDP2_VRAM.bin'), 'rb').read()
    R = struct.unpack('>256H', open(os.path.join(d, 'VDP2_REGS.bin'), 'rb').read())
    return V, R


def nbg_map(V, R, n):
    base = (R[(0x40 + 4 * n) // 2] & 0x3F) * PAGE
    g = {}
    for ty in range(64):
        for tx in range(64):
            w0, w1 = struct.unpack_from('>HH', V, base + (ty * 64 + tx) * 4)
            g[tx, ty] = (w1 & 0x7FFF, w0 & 0x7F)
    return base, g


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    for name in sys.argv[1:]:
        V, R = load(name)
        base, g = nbg_map(V, R, 1)
        print('== %s NBG1 맵 0x%05X' % (name, base))
        for ty in range(63):
            row = []
            for tx in range(64):
                (a, pa), (b, pb) = g[tx, ty], g[tx, ty + 1]
                if 0x80 <= a < 0x180 and 0x80 <= b < 0x180 and b == a + 1 and (a - 0x80) % 2 == 1:
                    row.append((tx, a - 0x80, pa))
            if row:
                print(' 줄 %2d: %s' % (ty, ' '.join('%d:%d/%d(p%d)' % (tx, c, c + 1, p) for tx, c, p in row)))


if __name__ == '__main__':
    main()
