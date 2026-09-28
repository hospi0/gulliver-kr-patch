# -*- coding: utf-8 -*-
r"""STARTUP.BIN 그림 다시 쓰기 — 저작권 화면(레코드 4 맵) + 타이틀 로고(레코드 7 맵), 셀 = 레코드 6 (2026-09-27)
  + «공상과학세계»(레코드 8 맵, 셀 = 레코드 10, 원래 75칸) — work/mem/kuusou_new.pkl(tools/kuusou.py)
  레코드 6 = [u16 셀 수][4bpp 셀 32B …] (VRAM 셀 0x160 부터) — 레코드 4·7 이 쓴다(레코드 8 맵은 레코드 10 셀을 쓴다)
  맵 = [u8 32][u8 32][u16 v × 1024], 셀 k = (v & 63)*16 + (v >> 12), 팔레트 = (v >> 8) & 15 (저작권 1 → 5, 타이틀 0 → 4)
  입력 그림(256×256 색 번호): work/mem/copy_new.pkl(tools/copyright.py) · title_new.pkl(tools/logo.py)
  python tools/startup_gfx.py → work/kr/STARTUP.BIN
"""
import os, pickle, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import lz, msg

SRC = os.path.join(ROOT, 'work', 'disc1', 'STARTUP.BIN')
OUT = os.path.join(ROOT, 'work', 'kr', 'STARTUP.BIN')
CELLS_MAX = 232                                   # 원본 셀 수(VRAM 0x160 + 232 까지만 쓴다)


def cell_bytes(img, cx, cy):
    b = bytearray()
    for y in range(8):
        r = img[cy * 8 + y]
        for x in range(0, 8, 2):
            b.append(r[cx * 8 + x] << 4 | r[cx * 8 + x + 1])
    return bytes(b)


def build(copy_img, title_img, pairs=None, cmax=CELLS_MAX):
    cells = []; index = {}
    maps = []
    for img, pal in (pairs or ((copy_img, 1), (title_img, 0))):
        m = []
        for cy in range(32):
            for cx in range(32):
                c = cell_bytes(img, cx, cy)
                if c not in index:
                    index[c] = len(cells); cells.append(c)
                k = index[c]
                m.append((k & 15) << 12 | pal << 8 | k >> 4)
        maps.append(bytes([32, 32]) + struct.pack('>1024H', *m))
    assert len(cells) <= cmax, ('셀 수 초과', len(cells), cmax)
    rec = struct.pack('>H', len(cells)) + b''.join(cells)
    return (rec,) + tuple(maps) + (len(cells),)


def decode_check(rec6, mp, img):
    """맵 + 셀로 되그려서 입력 그림과 같은지"""
    m = struct.unpack('>1024H', mp[2:])
    for cy in range(32):
        for cx in range(32):
            v = m[cy * 32 + cx]; k = (v & 63) * 16 + (v >> 12)
            assert rec6[2 + k * 32:2 + k * 32 + 32] == cell_bytes(img, cx, cy)


def rebuild_file(d, repl):
    """레코드 파일에서 {번호: 풀린 내용} 을 LZ 로 다시 넣는다(다른 레코드·끝 바이트는 그대로)"""
    R = msg.records(d)
    out = bytearray(); p = 0
    for k, (i, L, o, r) in enumerate(R):
        out += d[p:i]
        if k in repl:
            assert o is not None, ('LZ 레코드가 아님', k)
            c = lz.enc(repl[k]); c += bytes(-len(c) % 4)
            out += struct.pack('>II', len(c) + 4, len(repl[k])) + c
        else:
            out += d[i:i + 4 + L]
        p = i + 4 + L
    out += d[p:]
    R2 = msg.records(bytes(out))
    assert len(R2) == len(R)
    for k, (i, L, o, r) in enumerate(R2):
        if k in repl:
            assert o == repl[k]
        else:
            assert r == R[k][3]
    return bytes(out)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    ci = pickle.load(open(os.path.join(ROOT, 'work', 'mem', 'copy_new.pkl'), 'rb'))
    ti = pickle.load(open(os.path.join(ROOT, 'work', 'mem', 'title_new.pkl'), 'rb'))
    rec6, m4, m7, n = build(ci, ti)
    decode_check(rec6, m4, ci); decode_check(rec6, m7, ti)
    ki = pickle.load(open(os.path.join(ROOT, 'work', 'mem', 'kuusou_new.pkl'), 'rb'))   # tools/kuusou.py
    rec10, m8, n10 = build(None, None, pairs=((ki, 0),), cmax=75)                        # «공상과학세계»: 셀 레코드 10(원래 75) + 맵 레코드 8
    decode_check(rec10, m8, ki)
    print('공상과학세계 셀 %d/75' % n10)
    d = open(SRC, 'rb').read()
    nd = rebuild_file(d, {4: m4, 6: rec6, 7: m7, 8: m8, 10: rec10})
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'wb').write(nd)
    print('셀 %d/%d · STARTUP.BIN %d → %d B → %s' % (n, CELLS_MAX, len(d), len(nd), OUT))


if __name__ == '__main__':
    main()
