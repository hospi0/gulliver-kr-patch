# -*- coding: utf-8 -*-
r"""타이틀 로고 «걸리버 보이» (2026-09-27)
  원본(STARTUP 레코드 6 셀 + 레코드 7 맵, 팔레트 4): 빨강(4) 글자 + 오른쪽 아래로 검정(7) 2px 두께 + 회색(1) 1px 그림자, 바탕 = 0(투명)/13(검정)
  시안: 굵은 한글(Black Han Sans)을 문턱값으로 1비트 → 같은 입체 효과 → 256×256 맵 영역(화면 x+32) 가운데, 원본과 같은 높이대
  python tools/logo.py [글자] → my files/그래픽/타이틀로고_시안.png (원본과 나란히, ×3)
"""
import os, pickle, struct, sys
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
FONT = r'C:\claude\utils\font\logo\BlackHanSans.ttf'
PAL = {0: (0, 0, 0), 13: (0, 0, 0), 4: (160, 0, 0), 7: (0, 0, 0), 1: (32, 32, 32)}
SHOW = {0: (0, 0, 0), 13: (0, 0, 0), 1: (72, 72, 72), 2: (64, 0, 0), 3: (96, 0, 0), 4: (200, 0, 0), 5: (128, 0, 0), 6: (40, 0, 0), 7: (16, 16, 16)}


def mask(text, px, sx=1.0):
    F = ImageFont.truetype(FONT, px)
    d = ImageDraw.Draw(Image.new('L', (1, 1)))
    l, t, r, b = d.textbbox((0, 0), text, font=F)
    im = Image.new('L', (r - l + 8, b - t + 8), 0)
    ImageDraw.Draw(im).text((4 - l, 4 - t), text, font=F, fill=255)
    if sx != 1.0:
        im = im.resize((int(im.width * sx), im.height), Image.LANCZOS)
    return im.point(lambda v: 255 if v >= 128 else 0)


def compose(text, px=36, sx=1.0, top=91):
    m = mask(text, px, sx)
    W, H = 256, 256
    ox = (W - m.width) // 2; oy = top - 4
    M = [[False] * W for _ in range(H)]
    for y in range(m.height):
        for x in range(m.width):
            if m.getpixel((x, y)) and 0 <= ox + x < W and 0 <= oy + y < H:
                M[oy + y][ox + x] = True
    img = [[0] * W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            if M[y][x]:
                img[y][x] = 4
    for dy, dx, c in ((1, 1, 7), (2, 2, 7), (3, 3, 1)):          # 두께·그림자
        for y in range(H - dy):
            for x in range(W - dx):
                if M[y][x] and img[y + dy][x + dx] == 0:
                    img[y + dy][x + dx] = c
    return img


def to_png(img, x0=32, y0=80, w=200, h=64):
    im = Image.new('RGB', (w, h))
    for y in range(h):
        for x in range(w):
            im.putpixel((x, y), SHOW.get(img[y0 + y][x0 + x], (255, 0, 255)))
    return im


def main():
    text = sys.argv[1] if len(sys.argv) > 1 else '걸리버 보이'
    orig = pickle.load(open(os.path.join(ROOT, 'work', 'mem', 'title_idx.pkl'), 'rb'))
    new = compose(text)
    a, b = to_png(orig), to_png(new)
    out = Image.new('RGB', (a.width, a.height * 2 + 4), (60, 60, 60))
    out.paste(a, (0, 0)); out.paste(b, (0, a.height + 4))
    os.makedirs(os.path.join(ROOT, 'my files', '그래픽'), exist_ok=True)
    p = os.path.join(ROOT, 'my files', '그래픽', '타이틀로고_시안.png')
    out.resize((out.width * 3, out.height * 3), Image.NEAREST).save(p)
    pickle.dump(new, open(os.path.join(ROOT, 'work', 'mem', 'title_new.pkl'), 'wb'))
    print(p)


if __name__ == '__main__':
    main()
