# -*- coding: utf-8 -*-
r"""걸리버 보이 LZSS (2026-09-27 C01.BIN 대사 조각으로 확정)
  조각 = [u32 BE 크기 c][u32 BE 원래크기 n][압축 c-4 바이트]   ← c 는 «원래크기 필드 + 압축 바이트»
  압축: 플래그 1바이트(LSB 먼저, 1=평문 바이트) · 참조 2바이트 a b → 길이 (a>>4)+2, 링 위치 ((a&15)<<8)|b
        링 버퍼 4 KB, 0 으로 채움, 쓰기 위치 0 에서 시작(절대 위치 참조)
"""
import struct


def dec(d, p, n, outn):
    """d[p:p+n] 을 outn 바이트로 푼다. 실패하면 None"""
    ring = bytearray(0x1000); r = 0; out = bytearray(); end = p + n
    while p < end and len(out) < outn:
        fl = d[p]; p += 1
        for k in range(8):
            if p >= end or len(out) >= outn:
                break
            if fl >> k & 1:
                c = d[p]; p += 1; out.append(c); ring[r] = c; r = (r + 1) & 0xFFF
            else:
                if p + 1 >= len(d):
                    return None
                a, b = d[p], d[p + 1]; p += 2
                pos = ((a & 15) << 8) | b
                for i in range((a >> 4) + 2):
                    c = ring[(pos + i) & 0xFFF]; out.append(c); ring[r] = c; r = (r + 1) & 0xFFF
    return bytes(out) if len(out) == outn and end - 4 <= p <= end else None


def chunk(d, i):
    """i 에 조각이 있으면 (원래 바이트, 다음 위치), 아니면 None"""
    if i + 8 > len(d):
        return None
    c, n = struct.unpack_from('>II', d, i)
    if not (16 <= c <= len(d) - i - 4 and c - 4 <= n <= c * 9 and n < 0x200000):
        return None
    o = dec(d, i + 8, c - 4, n)
    return (o, i + 4 + c) if o is not None else None


def scan(d):
    """4바이트 정렬로 훑어 조각 목록 [(위치, 압축크기 c, 원래 바이트)]"""
    out = []; i = 0
    while i + 8 < len(d):
        r = chunk(d, i)
        if r:
            out.append((i, struct.unpack_from('>I', d, i)[0], r[0])); i = r[1]
        else:
            i += 4
    return out


def enc(data):
    """압축기 — 위 규약 그대로(길이 2‥17, 링 절대 위치, 쓰기 위치 0 시작). 최장 일치 탐욕, 거리 < 4096"""
    data = bytes(data); n = len(data); out = bytearray(); idx = {}; p = 0
    while p < n:
        fp = len(out); out.append(0); fl = 0
        for k in range(8):
            if p >= n:
                break
            bl, bm = 0, 0
            if p + 2 <= n:
                for m in reversed(idx.get(data[p:p + 2], [])):
                    if p - m >= 0x1000:
                        break
                    L = 0
                    while L < 17 and p + L < n and data[m + L] == data[p + L]:
                        L += 1
                    if L > bl:
                        bl, bm = L, m
                        if L == 17:
                            break
            step = bl if bl >= 2 else 1
            if bl >= 2:
                pos = bm & 0xFFF
                out += bytes([((bl - 2) << 4) | pos >> 8, pos & 0xFF])
            else:
                fl |= 1 << k; out.append(data[p])
            for q in range(p, p + step):
                if q + 2 <= n:
                    idx.setdefault(data[q:q + 2], []).append(q)
            p += step
        out[fp] = fl
    assert dec(bytes(out), 0, len(out), n) == data, '압축 되풀기 불일치'
    return bytes(out)
