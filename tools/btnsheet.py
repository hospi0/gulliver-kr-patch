# -*- coding: utf-8 -*-
r"""걸리버 보이 — SYSDATA 레코드 9 버튼 셀 시트 (2026-09-28)
  버튼 한 열 = 레코드 셀 (홀수 위, +1 아래) · 한 버튼 = 3열. VRAM 셀 = 0x80 + 레코드 셀, 상태 파일 work/mem/m_main, 팔레트 1
  python tools/btnsheet.py [시작셀 끝셀] → work/menu/btn_sheet.png (3열마다 칸 띄움, 위에 시작 셀 번호)
"""
import os, sys
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('MEM', 'm_main')
import vdp2

a, b = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) > 2 else (1, 223)
S, PER = 5, 8                                   # 확대, 한 줄 버튼 수
cols = list(range(a, b, 2))                     # 열 = 위 셀 번호
btns = [cols[i:i + 3] for i in range(0, len(cols), 3)]
BW, BH = (24 + 6) * S, (16 + 12) * S
im = Image.new('RGB', (PER * BW, ((len(btns) + PER - 1) // PER) * BH), (50, 50, 50))
d = ImageDraw.Draw(im)
try:
    f = ImageFont.truetype('arial.ttf', 11 * S // 3)
except OSError:
    f = None
for k, bt in enumerate(btns):
    ox, oy = (k % PER) * BW, (k // PER) * BH
    d.text((ox + 2, oy), str(bt[0]), fill=(255, 255, 0), font=f)
    for j, c0 in enumerate(bt):
        for half in (0, 1):
            c = vdp2.cell(0x80 + c0 + half, 1)
            for y in range(8):
                for x in range(8):
                    v = c[y][x]
                    if v is not None:
                        d.rectangle([ox + (j * 8 + x) * S, oy + 12 * S + (half * 8 + y) * S,
                                     ox + (j * 8 + x + 1) * S - 1, oy + 12 * S + (half * 8 + y + 1) * S - 1], fill=vdp2.color(v))
out = os.path.join(vdp2.ROOT, 'work', 'menu', 'btn_sheet.png')
im.save(out)
print(out, im.size)
