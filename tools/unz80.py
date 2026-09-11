#!/usr/bin/env python3
"""Распаковка снимка ZX Spectrum .z80 (версии 1/2/3, только 48К) в образ ОЗУ 48К.

    python3 tools/unz80.py вход.z80 выход.bin [--meta]

Выход — 49152 байта, соответствующие адресам 0x4000..0xFFFF.
"""
import sys


def unrle(data):
    """Схема сжатия .z80: ED ED cnt val."""
    out = bytearray()
    i = 0
    n = len(data)
    while i < n:
        if i + 3 < n and data[i] == 0xED and data[i + 1] == 0xED:
            out.extend(bytes([data[i + 3]]) * data[i + 2])
            i += 4
        else:
            out.append(data[i])
            i += 1
    return bytes(out)


def load(path):
    raw = open(path, 'rb').read()
    hdr = raw[:30]
    pc = hdr[6] | (hdr[7] << 8)
    flags1 = hdr[12]
    if flags1 == 255:
        flags1 = 1
    compressed = bool(flags1 & 0x20)
    meta = {'pc': pc, 'a': hdr[0], 'f': hdr[1],
            'bc': hdr[2] | hdr[3] << 8, 'hl': hdr[4] | hdr[5] << 8,
            'sp': hdr[8] | hdr[9] << 8, 'i': hdr[10],
            'de': hdr[13] | hdr[14] << 8,
            'ix': hdr[25] | hdr[26] << 8, 'iy': hdr[23] | hdr[24] << 8,
            'im': hdr[29] & 3}

    if pc != 0:  # версия 1: сплошной блок 48К с 0x4000
        body = raw[30:]
        if compressed:
            # хвост-маркер 00 ED ED 00
            if body.endswith(b'\x00\xed\xed\x00'):
                body = body[:-4]
            body = unrle(body)
        meta['version'] = 1
        mem = bytearray(49152)
        mem[:len(body)] = body[:49152]
        return bytes(mem), meta

    # версии 2/3
    extlen = raw[30] | (raw[31] << 8)
    meta['version'] = 2 if extlen == 23 else 3
    meta['pc'] = raw[32] | (raw[33] << 8)
    hwmode = raw[34]
    meta['hwmode'] = hwmode
    pos = 32 + extlen
    # для 48К: страница 4 -> 0x8000, 5 -> 0xC000, 8 -> 0x4000
    pagemap = {4: 0x8000 - 0x4000, 5: 0xC000 - 0x4000, 8: 0x0000}
    mem = bytearray(49152)
    seen = set()
    while pos + 3 <= len(raw):
        blen = raw[pos] | (raw[pos + 1] << 8)
        page = raw[pos + 2]
        pos += 3
        if blen == 0xFFFF:
            block = raw[pos:pos + 16384]
            pos += 16384
        else:
            block = unrle(raw[pos:pos + blen])
            pos += blen
        if page in pagemap:
            off = pagemap[page]
            mem[off:off + 16384] = block[:16384]
            seen.add(page)
    meta['pages'] = sorted(seen)
    return bytes(mem), meta


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    mem, meta = load(sys.argv[1])
    open(sys.argv[2], 'wb').write(mem)
    print(f"{sys.argv[2]}: {len(mem)} байт (0x4000..0xFFFF)")
    for k in ('version', 'pc', 'sp', 'im', 'i', 'pages', 'hwmode'):
        if k in meta:
            v = meta[k]
            print(f"  {k} = {v if isinstance(v, list) else hex(v)}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
