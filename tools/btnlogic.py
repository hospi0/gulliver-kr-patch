# -*- coding: utf-8 -*-
r"""걸리버 보이 — SYSDATA 레코드 5(논리 번호 → VRAM 셀, u16×256) 로 버튼 그리기 (2026-09-28)
  논리 6칸 = 버튼 1개(열마다 위·아래, 3열). VRAM 은 상태 파일(work/mem/m_main) 에서, 팔레트 1
  python tools/btnlogic.py [시작 논리번호] → work/menu/btn_logic.png
"""
import os, struct, sys
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
os.environ.setdefault('MEM', 'm_main')
import vdp2, msg

d = open(os.path.join(vdp2.ROOT, 'work', 'disc1', 'SYSDATA.BIN'), 'rb').read()
T = struct.unpack('>256H', msg.records(d)[5][3])
start = int(sys.argv[1]) if len(sys.argv) > 1 else 80
S, PER = 5, 8
groups = [list(range(p, min(p + 6, 256))) for p in range(start, 256, 6)]
groups = [g for g in groups if any(T[p] for p in g)]
BW, BH = 30 * S, 28 * S
im = Image.new('RGB', (PER * BW, ((len(groups) + PER - 1) // PER) * BH), (50, 50, 50))
dr = ImageDraw.Draw(im)
try:
    f = ImageFont.truetype('arial.ttf', 11 * S // 3)
except OSError:
    f = None
for k, g in enumerate(groups):
    ox, oy = (k % PER) * BW, (k // PER) * BH
    dr.text((ox + 2, oy), str(g[0]), fill=(255, 255, 0), font=f)
    for j, p in enumerate(g):
        if not T[p]:
            continue
        col, half = j // 2, j % 2
        c = vdp2.cell(T[p], 1)
        for y in range(8):
            for x in range(8):
                v = c[y][x]
                if v is not None:
                    dr.rectangle([ox + (col * 8 + x) * S, oy + 12 * S + (half * 8 + y) * S,
                                  ox + (col * 8 + x + 1) * S - 1, oy + 12 * S + (half * 8 + y + 1) * S - 1], fill=vdp2.color(v))
out = os.path.join(vdp2.ROOT, 'work', 'menu', 'btn_logic.png')
im.save(out)
print(out)
