# -*- coding: utf-8 -*-
r"""번역용 원문 추출 — 대사 레코드(tools/msg.py blocks) 의 «쪽» 단위, 같은 바이트는 한 번만 (2026-09-27)
  → my files/tsv/gulliver_NNN.tsv (29KB 단위, 열: ID 위치 구분 공유 원문 번역)
  → work/trans/ids.tsv (ID → 전체 위치 목록)
  표기: 줄바꿈 \n · 음성 대사(r 로 시작)는 타이밍 코드 r·zNN·wNN 를 뺀다(빌더가 원문 타이밍을 새 글에 나눠 준다)
        그 밖의 코드는 {…}: {gNN}(기호 글자, g00 = «!!») {aN}{bN}(이름 등 변수) {cN}(색) {vNNN}(아이템 변수) {o}(선택지) {i} {q} {zNN}
        반각 공백은 그대로(전투 문구에 쓰임)
  위치 = 파일-레코드-메시지위치-쪽
  python tools/extract.py
"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import msg

CHUNK = 29 * 1024
TOKEN = re.compile(r'\\n|r(?=z)|[zwg][0-9]{2}|\{[0-9]{3}|[abc][0-9]|[oiq]')


def to_text(b):
    t = msg.show(b)
    voiced = t.startswith('r')
    out = []; p = 0
    while p < len(t):
        m = TOKEN.match(t, p)
        if not m:
            ch = t[p]
            assert not ('!' <= ch <= '~'), ('모르는 코드', t, p)
            out.append(ch); p += 1; continue
        s = m.group(); p = m.end()
        if s == '\\n':
            out.append('\\n')
        elif voiced and (s == 'r' or s[0] in 'zw'):
            continue
        elif s[0] == '{':
            out.append('{v%s}' % s[1:])
        else:
            out.append('{%s}' % s)
    return ('음성' if voiced else '대사'), ''.join(out)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    seen = {}; rows = []
    for fn, k, m in msg.blocks():
        for s, pages in m:
            for j, b in enumerate(pages):
                loc = '%s-%d-%d-%d' % (fn.split('.')[0], k, s, j)
                if b in seen:
                    seen[b][1].append(loc); continue
                kind, text = to_text(b)
                seen[b] = (len(rows), [loc]); rows.append((kind, text, b))
    os.makedirs(os.path.join(ROOT, 'work', 'trans'), exist_ok=True)
    tdir = os.path.join(ROOT, 'my files', 'tsv'); os.makedirs(tdir, exist_ok=True)
    head = 'ID\t위치\t구분\t공유\t원문\t번역\n'
    with open(os.path.join(ROOT, 'work', 'trans', 'ids.tsv'), 'w', encoding='utf-8') as f:
        f.write('ID\t원문바이트(hex)\t위치…\n')
        for i, (kind, text, b) in enumerate(rows):
            f.write('%05d\t%s\t%s\n' % (i + 1, b.hex(), '\t'.join(seen[b][1])))
    n = 0; buf = head; files = []
    for i, (kind, text, b) in enumerate(rows):
        locs = seen[b][1]
        line = '%05d\t%s\t%s\t%d\t%s\t\n' % (i + 1, locs[0], kind, len(locs), text)
        if len((buf + line).encode('utf-8')) > CHUNK and buf != head:
            files.append(buf); buf = head
        buf += line
    files.append(buf)
    for k, t in enumerate(files):
        open(os.path.join(tdir, 'gulliver_%03d.tsv' % (k + 1)), 'w', encoding='utf-8').write(t)
    chars = sum(len(re.sub(r'\{[^}]*\}|\\n', '', t)) for _, t, _ in rows)
    voiced = sum(1 for k, _, _ in rows if k == '음성')
    print('문장 %d (음성 %d) · 글자 %d · 출현 %d · 파일 %d개 → %s' % (len(rows), voiced, chars, sum(len(v[1]) for v in seen.values()), len(files), tdir))


if __name__ == '__main__':
    main()
