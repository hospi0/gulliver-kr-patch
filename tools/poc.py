# -*- coding: utf-8 -*-
r"""첫 장면 PoC — 교실(C03.BIN 레코드 5) 음성 대사 9개를 한글로 (2026-09-27)
  1) FONT.DAT: 1수준 한자 칸 453‥2802 에 한글 2,350자(KS X 1001 순) — 갈무리11 을 칸 (0,1) 에 (원본 한자도 x0‥11·y1‥12)
  2) 대사: 음성 대사의 z(글자 속도?)·w(대기) 는 원문과 같은 순서로 두고, z 구간마다 «원문 글자 수 / 번역 글자 수» 로 z 값을 늘리고 줄인다
  3) 레코드 LZ 재압축(tools/lz.py enc) → C03.BIN 재조립 → 섹터 여유 안이면 ISO 제자리 교체(+디렉터리 크기) + MODE1 EDC/ECC
  python tools/poc.py [--write]  → work/out/
"""
import os, re, shutil, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, r'C:\claude\project\anearth-kr-patch\tools')
import lz, msg, kenc, disc
import bdf, cdmode1

GALMURI = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri11.bdf'
OUT = os.path.join(ROOT, 'work', 'out')
LINE_MAX = 19
FILE, REC = 'C03.BIN', 5

LINES = {
    3912: 'rz00z06이놈z00g00　w12z09걸리버z00g00w15\\nz13또z00　w03z09수업을 빼먹는 게냐z00！w14',
    4001: 'rz00z09네놈은w06z00　z06이제w07　한 과목만 더 떨어지면w11\\nz08낙제란 말이다z00g00w08',
    4084: 'rz00z10시로지 선생님z00g00w35\\nz05난 좀 더z00　w08z07즐겁게w06\\n마법을z00　w11z04배우고 싶다구요z00．w13',
    4193: 'rz00z11맨날 이렇게z00　w03z06책만z00　z06읽고 있다간w11\\nz08머리가z00　w04z03썩어 버리겠다구z00！w34\\nz04그럼 간다z00g00w11',
    4325: 'rz00z05어이w20z06이놈z00　w20z05걸리버z00g00w16\\nz10…w14z05걸리버z00g00w15',
    4407: 'rz00w01z21오오z00　w38z12땡땡이쟁이 w03z13걸리버 군z00g00w38\\nz08이거z00　w01z08느긋하게도z00　z12납셨구먼z00！w57\\nz11곧바로z00　w03z10재시험 내용인데…w31z09에헴z00！w41',
    4588: 'rz00w03z07듣거라z00　w10z07걸리w01버z00！　w31z11시련의 동굴에 가서w30\\nz00『z13검은 통z00』z13을z00　w05z08가져오는 것이다z00！w39\\nz12…거기는z00　w01z10무서운 곳이니라z00g00w15',
    4771: 'rz00w03z03뭐z00　w39z09무리다 싶으면\\n냉큼z00　w02z07포기하고w01\\nz10여기로z00　w02z08돌아오도록 해라…w11',
    4894: 'rz00z06그리고z00　w07z12일 년 더z00　w26z10빡빡하게w03\\nz12공부를z00　w02z08해 줘야겠구w07먼z00！w12',
    5004: 'rz00w05z10이것이z00　w03z11동굴 열쇠니라z00！w72\\nz05자z00　『w48z30검z16은 z37통z00』z37을z10가져오너라z00！w29',
}

TOK = re.compile(r'(r|[zwg][0-9]{2}|\\n)')
PUNCT_SP = re.compile(r'([！？。．、，…』]|g0[01])((?:[zw][0-9]{2})*)[ 　]')


def squeeze(t):
    """문장부호(g00 «!!» 포함) 뒤 공백은 뺀다 — 전프로젝트 규칙"""
    return PUNCT_SP.sub(r'\1\2', t)


def split(t):
    return [s for s in TOK.split(t) if s]


def skeleton(t):
    return [s if s[0] in 'wg' or s in ('r', '\\n') else 'z' for s in split(t) if TOK.fullmatch(s)]


def retime(jp, ko):
    """z 구간(다음 z 까지)의 글자 수 비율로 z 값을 맞춘다"""
    assert skeleton(jp) == skeleton(ko), ('제어 코드 순서가 원문과 다르다', skeleton(jp), skeleton(ko))

    def seglens(t):
        out = []
        for s in split(t):
            if s[0] == 'z' and TOK.fullmatch(s):
                out.append([int(s[1:]), 0])
            elif not TOK.fullmatch(s) and out:
                out[-1][1] += len(s)
        return out
    J, K = seglens(jp), seglens(ko)
    new = iter([z if z == 0 or kl == 0 else max(1, min(99, round(z * jl / kl))) for (z, jl), (_, kl) in zip(J, K)])
    return ''.join('z%02d' % next(new) if s[0] == 'z' and TOK.fullmatch(s) else s for s in split(ko))


def width_check(t):
    for ln in t.split('\\n'):
        body = re.sub(r'r|[zw][0-9]{2}', '', ln)
        n = len(re.sub(r'g[0-9]{2}', '#', body))
        assert n <= LINE_MAX, ('줄 폭 초과', ln, n)


def font():
    f = bytearray(open(os.path.join(ROOT, 'work', 'disc1', 'FONT.DAT'), 'rb').read())
    F = bdf.Font(GALMURI)
    for i, ch in enumerate(kenc.HANGUL):
        pts, _ = F.draw(ch, 0, -2)                   # 갈무리11 한글 윗줄 = 3 → 칸의 1행
        g = bytearray(32)
        for x, y in pts:
            assert 0 <= x < 12 and 1 <= y < 13, (ch, x, y)
            g[2 * y + x // 8] |= 0x80 >> (x % 8)
        o = (kenc.CELL0 + i) * 32
        f[o:o + 32] = g
    return bytes(f)


def dialog():
    d = open(os.path.join(ROOT, 'work', 'disc1', FILE), 'rb').read()
    R = msg.records(d)
    t = R[REC][2]
    M = dict(msg.messages(t))
    out = bytearray(); p = 0
    for s in sorted(M):
        pages = M[s]
        out += t[p:s]
        if s in LINES:
            assert len(pages) == 1
            jp = msg.show(pages[0])
            ko = retime(jp, squeeze(LINES[s]))
            width_check(ko)
            b = kenc.encode(ko)
            assert len(b) + 1 <= 255
            print(' ', jp, '\n→', ko)
            out += bytes([1, len(b) + 1]) + b + b'\0'
        else:
            out += bytes([len(pages)]) + b''.join(bytes([len(b) + 1]) + b + b'\0' for b in pages)
        p = s + 1 + sum(len(b) + 2 for b in pages)
    out += t[p:]
    assert len(msg.messages(bytes(out))) == len(M)
    c = lz.enc(out)
    c += bytes(-len(c) % 4)                           # 레코드 길이는 전부 4의 배수
    rec = struct.pack('>II', len(c) + 4, len(out)) + c
    i, L = R[REC][0], R[REC][1]
    nd = d[:i] + rec + d[i + 4 + L:]
    print('레코드 %d: 풀림 %d → %d · 압축 %d → %d · 파일 %d → %d' % (REC, len(t), len(out), L, len(c) + 4, len(d), len(nd)))
    # 되읽기
    R2 = msg.records(nd)
    assert len(R2) == len(R) and R2[REC][2] == bytes(out)
    assert all(a[3] == b[3] for k, (a, b) in enumerate(zip(R, R2)) if k != REC)
    return nd


def patch_disc(files):
    D = disc.Disc(1)
    ents = {nm: (l, s, off) for nm, l, s, off in D.files()}
    root = D.sec(16)[156:190]
    dir_lba = struct.unpack_from('<I', root, 2)[0]
    D.f.close()
    os.makedirs(OUT, exist_ok=True)
    src = os.path.dirname(D.path); base = os.path.basename(D.path).replace(' (Track 1).bin', '')
    t1 = os.path.join(OUT, base + ' (Track 1).bin')
    shutil.copyfile(D.path, t1)
    with open(t1, 'r+b') as fh:
        def write(lba, data):
            fh.seek(lba * 2352); sec = bytearray(fh.read(2352))
            sec[16:2064] = data
            fh.seek(lba * 2352); fh.write(cdmode1.fix(sec))
        for nm, data in files.items():
            l, s, off = ents[nm]
            have = (s + 2047) // 2048
            assert (len(data) + 2047) // 2048 <= have, ('섹터 여유 초과 — ISO 재구성 필요', nm, len(data), have * 2048)
            pad = data + bytes(have * 2048 - len(data))
            for k in range(have):
                write(l + k, pad[k * 2048:k * 2048 + 2048])
            if len(data) != s:                        # 디렉터리 크기(양 엔디안)
                dl = dir_lba + off // 2048; o = off % 2048
                fh.seek(dl * 2352 + 16); sec = bytearray(fh.read(2048))
                struct.pack_into('<I', sec, o + 10, len(data)); struct.pack_into('>I', sec, o + 14, len(data))
                write(dl, bytes(sec))
            print('  %s %d → %d (LBA %d, %d섹터)' % (nm, s, len(data), l, have))
    for fn in os.listdir(src):
        if 'Track 1' not in fn:
            dst = os.path.join(OUT, fn)
            if not os.path.exists(dst) or os.path.getsize(dst) != os.path.getsize(os.path.join(src, fn)):
                shutil.copyfile(os.path.join(src, fn), dst)
    print('→', OUT)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    files = {'FONT.DAT': font(), FILE: dialog()}
    for fn in sorted(os.listdir(os.path.join(ROOT, 'work', 'kr'))):   # 자막 동영상(moviesub.py --encode)·STARTUP 그림(startup_gfx.py) 등
        files[fn] = open(os.path.join(ROOT, 'work', 'kr', fn), 'rb').read()
    if '--write' not in sys.argv:
        print('예행 끝 — 쓰려면 --write'); return
    import iso                                        # 넘치는 파일만 파일 영역 끝으로(--move = 전부 옮겨 보기)
    D = disc.Disc(1); src = D.path; D.f.close()
    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, os.path.basename(src))
    iso.patch(src, dst, files, force_move=tuple(files) if '--move' in sys.argv else ())
    iso.verify(dst, files)
    print('→', dst)


if __name__ == '__main__':
    main()
