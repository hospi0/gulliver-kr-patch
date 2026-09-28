# -*- coding: utf-8 -*-
r"""동영상 대사 자막 전부 (2026-09-28) — 사용자 받아쓰기 `my files/movie script.txt`(영상 시각 그대로) → 번역 work/text/movie_all.tsv
  열: 영상 · 시작 · 끝 · 원문 · 번역(«\n» = 다음 자막, 한 행 시간을 글자 수 비례로 나눔) · 비고
  시간: 받아쓰기 구간 [시작, 끝] 을 쓰되, 읽을 시간(글자×0.18초 + 조각×1.0초, 조각당 최소 1.3초)보다 짧으면 다음 행 앞까지 늘리고,
        지나치게 길면(받아쓰기 구간에 무음이 섞임) 읽을 시간 + 1초로 줄인다.
  그리기·굽기 = tools/moviesub.py 와 같음(나눔고딕 Bold 14px 흰+검은 1px, 아래 가운데, 부호 뒤 공백 삭제) → opening_enc 키 구간만 재굽기
  → work/kr/GNN.CPK(원본 크기로 0 채움; 못 맞추면 원본보다 크게 — iso.py 가 끝으로 옮김) + 미리보기 work/movie/sub/GNN_kr.mp4
  python tools/moviesub_all.py [G02 G03 …]   (없으면 TSV 의 영상 전부)
"""
import glob, os, re, subprocess, sys
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import moviesub, opening_enc
FFBIN = moviesub.FFBIN
W, H, FPS = moviesub.W, moviesub.H, moviesub.FPS
TSV = os.path.join(ROOT, 'work', 'text', 'movie_all.tsv')
# 부호 뒤 공백 삭제(전프로젝트 규칙) — 반각·전각 표준 목록
PUNCT_SP = re.compile(r'([,.!?:;)\]}\'"~、。，．！？：；）］｝」』】〉》”’…‥・·～〜♪♥]) (?! )')


def secs(t):
    m, s = t.split(':')
    return int(m) * 60 + float(s)


def rows():
    out = {}
    for ln in open(TSV, encoding='utf-8'):
        if ln.startswith('#') or not ln.strip():
            continue
        c = ln.rstrip('\n').split('\t')
        parts = [PUNCT_SP.sub(r'\1', p.strip()) for p in c[4].split('\\n')]
        out.setdefault(c[0], []).append((secs(c[1]), secs(c[2]), parts))
    return out


def events(rs, dur):
    ev = []
    for k, (s, e, parts) in enumerate(rs):
        nxt = rs[k + 1][0] if k + 1 < len(rs) else dur
        chars = sum(len(p) for p in parts)
        need = max(chars * 0.18 + 1.0 * len(parts), 1.3 * len(parts))
        end = min(e, s + need + 1.0)
        if end - s < need:
            end = s + need
        end = min(end, nxt - 0.07, dur - 0.05)
        a = s
        for p in parts:
            d = (end - s) * max(len(p), 4) / sum(max(len(q), 4) for q in parts)
            ev.append((a, a + d, p)); a += d
    return ev


def plates(ev, out):
    F = ImageFont.truetype(moviesub.FONT, moviesub.PX)
    os.makedirs(out, exist_ok=True)
    for f in glob.glob(os.path.join(out, 's*.png')):
        os.remove(f)
    for k, (a, b, text) in enumerate(ev):
        im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        lines = moviesub.wrap(text, F)
        y = H - 12 - (len(lines) - 1) * 17
        for ln in lines:
            d.text((W / 2, y), ln, font=F, anchor='mm', fill=(255, 255, 255), stroke_width=1, stroke_fill=(0, 0, 0)); y += 17
        px = im.load()
        for yy in range(H):
            for xx in range(W):
                r, g, bb, al = px[xx, yy]
                px[xx, yy] = (r, g, bb, 255) if al >= 128 else (0, 0, 0, 0)
        im.save(os.path.join(out, 's%03d.png' % k))


def frames(name):
    fr = os.path.join(ROOT, 'work', 'movie', 'frames', name.lower())
    if not glob.glob(os.path.join(fr, 'f*.png')):
        os.makedirs(fr, exist_ok=True)
        subprocess.run([os.path.join(FFBIN, 'ffmpeg.exe'), '-v', 'error', '-y', '-i',
                        os.path.join(ROOT, 'work', 'movie', 'cpk', name + '.CPK'), '-fps_mode', 'passthrough',
                        os.path.join(fr, 'f%04d.png')], check=True)
    return fr


def encode(name, ev, pl, log):
    fr = frames(name)
    kr = os.path.join(fr, 'kr'); os.makedirs(kr, exist_ok=True)
    for f in glob.glob(os.path.join(kr, 'f*.png')):
        os.remove(f)
    nf = len(glob.glob(os.path.join(fr, 'f*.png')))
    done = 0
    for k, (a, b, _) in enumerate(ev):
        plate = Image.open(os.path.join(pl, 's%03d.png' % k))
        for f in range(nf):
            if a <= f / FPS < b:
                im = Image.open(os.path.join(fr, 'f%04d.png' % (f + 1))).convert('RGBA')
                im.alpha_composite(plate)
                im.convert('RGB').save(os.path.join(kr, 'f%04d.png' % (f + 1))); done += 1
    src = os.path.join(ROOT, 'work', 'movie', 'cpk', name + '.CPK')
    dst = os.path.join(ROOT, 'work', 'kr', name + '.CPK')
    size = os.path.getsize(src)
    try:
        opening_enc.reencode(src, fr, kr, dst, size, log=log)
        d = open(dst, 'rb').read()
        open(dst, 'wb').write(d + bytes(size - len(d)))
        note = '원본 크기'
    except AssertionError as ex:                    # 자리 초과 → 원본보다 크게(iso.py 가 파일 영역 끝으로 옮김)
        log('  ⚠%s — 원본보다 크게 씀' % (ex,))
        n = opening_enc.reencode(src, fr, kr, dst, size * 2, log=log)
        note = '⚠원본보다 %d B 큼' % (n - size)
    log('%s 덮은 프레임 %d → %s (%s)' % (name, done, dst, note))


def preview(name):
    subprocess.run([os.path.join(FFBIN, 'ffmpeg.exe'), '-v', 'error', '-y', '-i', os.path.join(ROOT, 'work', 'kr', name + '.CPK'),
                    '-vf', 'scale=%d:%d:flags=neighbor' % (W * 3, H * 3), '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac', '-b:a', '192k', os.path.join(ROOT, 'work', 'movie', 'sub', name + '_kr.mp4')], check=True)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    allr = rows()
    names = [a for a in sys.argv[1:] if a.startswith('G')] or sorted(allr)
    log = lambda *a: print(*a, flush=True)
    for name in names:
        dur = moviesub.duration(os.path.join(ROOT, 'work', 'movie', 'cpk', name + '.CPK'))
        ev = events(allr[name], dur)
        log('== %s 자막 %d개 (%.1f초)' % (name, len(ev), dur))
        for a, b, t in ev:
            log('   %6.2f‥%6.2f  %s' % (a, b, t))
        pl = os.path.join(ROOT, 'work', 'movie', 'sub', name.lower())
        plates(ev, pl)
        encode(name, ev, pl, log)
        preview(name)


if __name__ == '__main__':
    main()
