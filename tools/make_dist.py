# -*- coding: utf-8 -*-
r"""걸리버 보이 배포 묶음 — dist/GulliverBoy_KR_<VER>/ : 장마다 트랙 1 xdelta + xdelta.exe + readme.txt(CP949) + 한글패치_적용.bat
  검증: 원본 트랙 1 → xdelta 적용 → md5 = 빌드 결과(work/out) md5 (두 장 모두).
  python tools/make_dist.py   (먼저 python tools/build.py --write)
"""
import hashlib, os, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)

VER = 'v0.9'
XDELTA = r'C:\claude\utils\xdelta.exe'
ROMS = r'C:\claude\roms\ss\완료'
OUT = os.path.join(ROOT, 'work', 'out')
NAME = 'GulliverBoy_KR_' + VER
TITLE = '걸리버 보이 (공상과학세계 걸리버 보이, 세가 새턴 일본판) 한글 패치 ' + VER
DISCS = [(1, 3), (2, 7)]                     # (장, 트랙 수)


def rom(n):
    return 'Kuusou Kagaku Sekai Gulliver Boy (Japan) (Disc %d)' % n


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest().upper()


HEAD = """{tracks}개의 트랙으로 이루어진 {rom} 의
트랙 1번에 패치하시면 됩니다.

원본md5 : {o}
패치md5 : {d}

입니다.
"""

BODY = """

[ 적용 방법 ]

  1) 원본 트랙 1 파일을 이 폴더에 복사
       "{bin1}"
       "{bin2}"
     (두 장 중 한 장만 있어도 그 장만 패치합니다)
  2) 한글패치_적용.bat 실행 → 이름 끝에 [KR] 이 붙은 파일이 만들어집니다
  3) 만든 파일 이름을 원본 트랙 1 이름으로 바꿔 넣고, 나머지 트랙과 cue 는 그대로 쓰세요

  직접 적용:
    xdelta.exe -d -s "원본 트랙 1" "{p1}" "결과 파일"   (1장)
    xdelta.exe -d -s "원본 트랙 1" "{p2}" "결과 파일"   (2장)
  (Delta Patcher 같은 xdelta3 GUI 도구로 적용해도 됩니다. 원본이 다르면 xdelta 가 적용을 거부합니다.)


[ 바뀌는 것 ]

  - 본편 대사 전부(음성 대사는 글자 속도를 한글 길이에 맞춰 다시 맞춤)
  - 메뉴·아이템·마법·상태 이상·상점·전투 문구, 세이브·설정 화면
  - 메뉴 파란 버튼 28개(도구·사용·상태·설정·지도, 전투·상점 버튼 등) 한글 그림
  - 타이틀 로고 '걸리버 보이', 저작권 화면, '공상과학세계' 화면
  - 동영상 23개 한글 자막
  - 스태프롤


[ 알려진 점 ]

  - 아직 끝까지 실기로 통독하지 못했습니다. 이상한 곳이 있으면 알려 주세요.
"""

BAT = r"""@echo off
chcp 949 >nul
set "XD=%~dp0xdelta.exe"
set DONE=0
{blocks}
if "%DONE%"=="0" (
  echo   [오류] 원본 트랙 1 파일을 이 폴더에 넣어 주세요(readme 참고).
  pause & exit /b 1
)
echo   완료
pause
"""

BLOCK = r"""if exist "%~dp0{bin}" (
  "%XD%" -d -f -s "%~dp0{bin}" "%~dp0{patch}" "%~dp0{kbin}"
  if errorlevel 1 (
    echo   [오류] {n}장 패치 실패 - 원본이 다를 수 있습니다(readme 의 원본md5 확인).
    pause & exit /b 1
  )
  echo   {n}장: "{kbin}"
  set DONE=1
)
"""


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    d = os.path.join(ROOT, 'dist', NAME)
    os.makedirs(d, exist_ok=True)
    heads, blocks, kw = [], [], {}
    for n, tracks in DISCS:
        b = rom(n) + ' (Track 1).bin'
        src = os.path.join(ROMS, rom(n), b); out = os.path.join(OUT, b)
        patch = '%s_Disc%d.xdelta' % (NAME, n); pp = os.path.join(d, patch)
        subprocess.run([XDELTA, '-e', '-9', '-f', '-s', src, out, pp], check=True)
        chk = os.path.join(d, '_check.bin')
        subprocess.run([XDELTA, '-d', '-f', '-s', src, pp, chk], check=True)
        o, want, got = md5(src), md5(out), md5(chk)
        os.remove(chk)
        assert got == want, ('패치 적용 결과가 빌드와 다름', n, got, want)
        heads.append(HEAD.format(tracks=tracks, rom=rom(n), o=o, d=want))
        kbin = rom(n) + ' (Track 1) [KR].bin'
        blocks.append(BLOCK.format(bin=b, patch=patch, kbin=kbin, n=n))
        kw['bin%d' % n] = b; kw['p%d' % n] = patch
        print('%d장 원본md5 %s → 패치md5 %s · %s %d B' % (n, o, want, patch, os.path.getsize(pp)))
    shutil.copy2(XDELTA, os.path.join(d, 'xdelta.exe'))
    readme = TITLE + '\n' + '=' * 60 + '\n\n' + '\n\n'.join(heads) + BODY.format(**kw)
    open(os.path.join(d, 'readme.txt'), 'wb').write(readme.replace('\n', '\r\n').encode('cp949'))
    open(os.path.join(d, '한글패치_적용.bat'), 'wb').write(BAT.format(blocks=''.join(blocks)).replace('\n', '\r\n').encode('cp949'))
    print('✅', d)
    for f in sorted(os.listdir(d)):
        print('  %-50s %12d' % (f, os.path.getsize(os.path.join(d, f))))


if __name__ == '__main__':
    main()
