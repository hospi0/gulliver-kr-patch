# -*- coding: utf-8 -*-
r"""걸리버 보이 — 메뉴 파란 버튼 28개 한글 (2026-09-28, docs/01 «메뉴 파란 버튼»)
  그림 = SYSDATA 레코드 9(LZ, 4bpp 셀 224, VRAM 셀 0x80+). 한 버튼 = 3열(열 = 위 셀·아래 셀), 24×16px
  테두리: x0·y0·x23·y15 = 7 · x1·y1 = f(노랑) · x22·y14 = 2(그림자) · 안쪽 x2‥21 × y2‥13 바탕 1 · 글자 7
  ★셋째 열을 빌려 쓰는 버튼(与える·預ける·買う·売る·やめる)과 빌려주는 버튼(使う·守る·捨てる)은
    한글을 앞 두 열 안쪽(x2‥15)에만 — 빌려주는 셋째 열은 빈 바탕 + 오른쪽 테두리 → 어느 열을 빌려도 맞다
  글꼴 = 갈무리11 콘덴스드(7×11, 사용자 «전부 7px 통일» 2026-09-28)
  python tools/buttons.py → work/kr/SYSDATA.BIN (레코드 9 교체, 없으면 원본에서) + my files/그래픽/버튼_비교.png
"""
import os, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, r'C:\claude\project\astronoka-kr-patch\tools')
import msg
from build import rebuild_file
from bdf import Font

FONT = Font(r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri11-Condensed.bdf')
SRC = os.path.join(ROOT, 'work', 'disc1', 'SYSDATA.BIN')
OUT = os.path.join(ROOT, 'work', 'kr', 'SYSDATA.BIN')

# (한글, 자기 열의 위 셀 목록, 글자 칸 열 수, 셋째 열을 빈 칸으로 = 빌려주는 버튼)
B = [(n, [49 + 6 * k, 51 + 6 * k, 53 + 6 * k], 3, False) for k, n in enumerate(
    '왼손 반지 해제 마법 노래 발명 도구 사용 장착 능력 교환 상태 정리 버림 피비 설정 방어 도망'.split())]
LEND = {'사용', '버림', '방어'}
B = [(n, c, 2 if n in LEND else w, n in LEND) for n, c, w, _ in B]
B += [('주기', [163, 165], 2, False), ('꺼냄', [167, 169, 171], 3, False), ('맡김', [173, 175], 2, False),
      ('구입', [178, 180], 2, False), ('판매', [182, 184], 2, False), ('그만', [186, 188], 2, False),
      ('금화', [190, 192, 194], 3, False), ('설명', [196, 198, 200], 3, False), ('지도', [202, 204, 206], 3, False)]


def get(R, n):
    return [[(R[n * 32 + y * 4 + x // 2] >> (4 if x % 2 == 0 else 0)) & 15 for x in range(8)] for y in range(8)]


def put(R, n, px):
    for y in range(8):
        for x in range(0, 8, 2):
            R[n * 32 + y * 4 + x // 2] = px[y][x] << 4 | px[y][x + 1]


def glyph(ch):
    pts, _ = FONT.draw(ch)
    x0 = min(x for x, y in pts); y0 = min(y for x, y in pts)
    return {(x - x0, y - y0) for x, y in pts}, max(x for x, y in pts) - x0 + 1, max(y for x, y in pts) - y0 + 1


def label(text, width):
    """글자 칸(폭 width, 높이 12) 안 잉크 좌표 — 가운데, 글자 사이 1px(안 들어가면 0)"""
    gs = [glyph(c) for c in text]
    gap = 1 if sum(w for _, w, _ in gs) + len(gs) - 1 <= width else 0
    tw = sum(w for _, w, _ in gs) + gap * (len(gs) - 1)
    if tw > width:
        sys.exit('⛔%s 폭 %d > %d' % (text, tw, width))
    h = max(h for _, _, h in gs)
    x = (width - tw) // 2; y = (12 - h + 1) // 2; out = set()
    for pts, w, gh in gs:
        out |= {(x + px, y + py + (h - gh)) for px, py in pts}
        x += w + gap
    return out


def main():
    d = open(OUT if os.path.exists(OUT) else SRC, 'rb').read()
    R = bytearray(msg.records(d)[9][2]); orig = bytes(R)
    before, after = [], []
    for name, cols, w, lend in B:
        px = [[0] * (8 * len(cols)) for _ in range(16)]
        for j, c in enumerate(cols):
            for h in (0, 1):
                g = get(R, c + h)
                for y in range(8):
                    px[h * 8 + y][j * 8:j * 8 + 8] = g[y]
        before.append([r[:] for r in px])
        W = len(cols) * 8
        clear_to = 15 if len(cols) == 2 else 21
        for y in range(2, 14):
            for x in range(2, clear_to + 1):
                px[y][x] = 1
        if lend:                                # 빌려주는 셋째 열: 빈 바탕 + 오른쪽 테두리(원본 그대로의 틀)
            for y in range(2, 14):
                for x in range(16, 22):
                    px[y][x] = 1
        # 테두리를 표준 틀로 다시(원본 逃げる·やめる 는 글자가 테두리 위까지 그려져 있었다). 2열 버튼은 x0‥15 만
        for y in range(16):
            for x in range(W):
                if y == 0 or y == 15 or x == 0 or x == 23:
                    px[y][x] = 7
                elif y == 1:
                    px[y][x] = 1 if x == 22 else 15
                elif y == 14:
                    px[y][x] = 1 if x == 1 else 2
                elif x == 1:
                    px[y][x] = 15
                elif x == 22:
                    px[y][x] = 2
        for x, y in label(name, 14 if w == 2 else 20):
            px[2 + y][2 + x] = 7
        after.append(px)
        for j, c in enumerate(cols):
            for h in (0, 1):
                put(R, c + h, [row[j * 8:j * 8 + 8] for row in px[h * 8:h * 8 + 8]])
    nd = rebuild_file(d, {9: bytes(R)})
    open(OUT, 'wb').write(nd)
    # 비교 그림(팔레트 1 근사색, ×4): 위 = 원본, 아래 = 한글
    pal = {0: (0, 0, 0), 1: (128, 160, 232), 2: (0, 64, 200), 7: (0, 0, 0), 15: (200, 200, 40)}
    cw = 26; im = Image.new('RGB', (cw * len(B), 36), (60, 60, 60))
    for k, (a, b) in enumerate(zip(before, after)):
        for row, pxs in ((0, a), (18, b)):
            for y, r in enumerate(pxs):
                for x, v in enumerate(r):
                    im.putpixel((k * cw + x, row + y), pal.get(v, (255, 0, 255)))
    os.makedirs(os.path.join(ROOT, 'my files', '그래픽'), exist_ok=True)
    p = os.path.join(ROOT, 'my files', '그래픽', '버튼_비교.png')
    im.resize((im.width * 4, im.height * 4), Image.NEAREST).save(p)
    print('버튼 %d개 · 레코드 9 %s · SYSDATA %d → %d B → %s' % (len(B), '바뀜' if bytes(R) != orig else '그대로', len(d), len(nd), OUT))
    print(p)


if __name__ == '__main__':
    main()
