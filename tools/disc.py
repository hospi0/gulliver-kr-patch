# -*- coding: utf-8 -*-
r"""걸리버 보이 디스크(트랙 1, MODE1/2352) 읽기 — ISO9660 루트 한 단계(디렉터리 없음)
  python tools/disc.py ls 1            → 파일 목록(이름 LBA 크기)
  python tools/disc.py get 1 [이름…]   → work/disc1/ 에 뽑기(이름 없으면 CPK·ADPCM.DAT 뺀 전부)
"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
ROM = r'C:\claude\roms\ss\완료\Kuusou Kagaku Sekai Gulliver Boy (Japan) (Disc {0})\Kuusou Kagaku Sekai Gulliver Boy (Japan) (Disc {0}) (Track 1).bin'
BIG = ('.CPK', 'ADPCM.DAT')


class Disc:
    def __init__(self, n):
        self.path = ROM.format(n)
        self.f = open(self.path, 'rb')

    def sec(self, l, n=1):
        out = bytearray()
        for i in range(n):
            self.f.seek((l + i) * 2352 + 16); out += self.f.read(2048)
        return bytes(out)

    def files(self):
        root = self.sec(16)[156:190]
        l, s = struct.unpack_from('<I', root, 2)[0], struct.unpack_from('<I', root, 10)[0]
        d = self.sec(l, (s + 2047) // 2048); i = 0; out = []
        while i < len(d):
            n = d[i]
            if n == 0:
                i = (i // 2048 + 1) * 2048; continue
            rec = d[i:i + n]
            nl = rec[32]; name = rec[33:33 + nl].decode('latin1').split(';')[0]
            if name not in ('\x00', '\x01') and not rec[25] & 2:
                out.append((name, struct.unpack_from('<I', rec, 2)[0], struct.unpack_from('<I', rec, 10)[0], i))
            i += n
        return out

    def read(self, name):
        for nm, l, s, _ in self.files():
            if nm == name:
                return self.sec(l, (s + 2047) // 2048)[:s]
        raise KeyError(name)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    cmd, n = sys.argv[1], int(sys.argv[2])
    D = Disc(n)
    if cmd == 'ls':
        for nm, l, s, _ in D.files():
            print('%-14s %7d %10d' % (nm, l, s))
    elif cmd == 'get':
        out = os.path.join(ROOT, 'work', 'disc%d' % n); os.makedirs(out, exist_ok=True)
        want = sys.argv[3:]
        k = 0
        for nm, l, s, _ in D.files():
            if (want and nm in want) or (not want and not nm.endswith(BIG)):
                open(os.path.join(out, nm), 'wb').write(D.sec(l, (s + 2047) // 2048)[:s]); k += 1
        print(k, '개 →', out)
