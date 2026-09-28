# -*- coding: utf-8 -*-
r"""저작권 화면 한글 (2026-09-27)
  원본(STARTUP 레코드 6 셀 + 레코드 4 맵, 팔레트 5): 바탕 14(0 도 투명 칸), 글자 15(흰색) + 1‥5 회색 가장자리, 256×256 맵(화면 x+32)
  줄: ① y61 «Copyright»(그대로) ② y89 «1995·1996 HUDSON SOFT/ワイワイカンパニー» — x<171 영어 부분은 원본 화소를 옮겨 쓰고 뒤를 한글로
      ③ y120 «広井王子・芦田豊雄/集英社» ④ y152 «フジテレビ・東映動画» → 한글. 한글 줄은 가운데 정렬(맵 폭 256 을 넘지 않게)
  글꼴: 갈무리11(BDF, 흰 15 한 색)
  python tools/copyright.py → my files/그래픽/저작권화면_시안.png (원본과 나란히, ×3), work/mem/copy_new.pkl
"""
import os, pickle, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, r'C:\claude\project\anearth-kr-patch\tools')
import bdf

GALMURI = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri11.bdf'
BG = (0, 14)
EN_END = 171                                    # ② 줄에서 영어 부분 끝(«/» 다음)
LINES = [
    (89, None, '와이와이 컴퍼니'),               # 영어 부분 뒤에 붙인다
    (120, 'c', '히로이 오지·아시다 토요오/슈에이샤'),
    (152, 'c', '후지TV·토에이 동화'),
]
SHOW = {0: (0, 0, 0), 14: (0, 0, 0), 15: (240, 224, 224), 1: (48, 48, 48), 2: (80, 80, 80), 3: (112, 112, 112), 4: (144, 144, 144), 5: (176, 176, 176)}


def text_pts(F, s):
    pts, w = F.draw(s, 0, -2)                    # 갈무리11 한글 윗줄 3 → 1
    return pts, w


def compose():
    orig = pickle.load(open(os.path.join(ROOT, 'work', 'mem', 'copy_idx.pkl'), 'rb'))
    img = [row[:] for row in orig]
    F = bdf.Font(GALMURI)
    y2 = 89
    # ② 줄: 영어 부분(x<EN_END) 화소를 모아 두고 줄 전체를 지운 뒤 [영어][한글] 을 가운데 정렬
    en = [[orig[y][x] for x in range(EN_END)] for y in range(y2, y2 + 12)]
    xs = [x for x in range(EN_END) for r in en if r[x] not in BG]
    ex0 = min(xs)
    for y0 in (89, 120, 152):
        for y in range(y0 - 1, y0 + 14):
            img[y] = [14] * 256
    for y0, align, s in LINES:
        pts, w = text_pts(F, s)
        if align is None:                         # 영어 + 한글
            enw = EN_END - ex0
            total = enw + 2 + w
            x0 = (256 - total) // 2
            assert x0 >= 0, ('② 줄 폭 초과', total)
            for dy, r in enumerate(en):
                for x in range(ex0, EN_END):
                    if r[x] not in BG:
                        img[y0 + dy][x0 + x - ex0] = r[x]
            kx = x0 + enw + 2
        else:
            assert w <= 256, (s, w)
            kx = (256 - w) // 2
        for x, y in pts:
            img[y0 + y][kx + x] = 15
        print('%3d  x %3d‥%3d  %s' % (y0, kx, kx + w, s))
    return orig, img


def to_png(img, box=(0, 50, 256, 120)):
    x0, y0, w, h = box
    im = Image.new('RGB', (w, h))
    for y in range(h):
        for x in range(w):
            im.putpixel((x, y), SHOW.get(img[y0 + y][x0 + x], (255, 0, 255)))
    return im


def main():
    orig, new = compose()
    a, b = to_png(orig), to_png(new)
    out = Image.new('RGB', (a.width, a.height * 2 + 4), (60, 60, 60))
    out.paste(a, (0, 0)); out.paste(b, (0, a.height + 4))
    p = os.path.join(ROOT, 'my files', '그래픽', '저작권화면_시안.png')
    out.resize((out.width * 3, out.height * 3), Image.NEAREST).save(p)
    pickle.dump(new, open(os.path.join(ROOT, 'work', 'mem', 'copy_new.pkl'), 'wb'))
    print(p)


if __name__ == '__main__':
    main()
