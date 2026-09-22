#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Мелодия C64 (Saul Cross) для заставки: поток ВИ53 варианта E -> компактные данные плеера.

Вход: ~/projects/alien8-research/c64/final/alien8_c64_tune_E.vi53 — 8427 кадров × 3 uint16 LE
(делители ВИ53 при такте 1 497 600 Гц, режим меандра; 0 = канал молчит).
Выход: src/c64_tune.bin + self-check (декодер на Python обязан выдать те же 8427×3 кадра).

Формат (грамматика Re-Pair, плеер = интерпретатор со стеком возвратов на голос):
  +0   3 слова: указатели на последовательности голосов A, B, C (смещения от начала блока)
  +6   слово: число правил R; далее R слов — указатели правил
  далее слово: число делителей D; далее D слов — делители ВИ53 (индекс 0 всегда = 0 = тишина)
  далее тела: последовательности голосов и правила.
Байты тела:
  0x00..0x7E  индекс делителя; следующий байт — длина в кадрах 1..255
  0x80..0xFE  вызов правила: k = ((b & 0x7F) << 8) | следующий байт   (двухбайтовый всегда)
  0xFF        конец правила (возврат); на верхнем уровне голоса — начать голос сначала (цикл)
Глубина вложенности правил ограничена MAXDEPTH (стек возвратов на голос = MAXDEPTH слов).
"""
import collections
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.expanduser('~/projects/alien8-research/c64/final/alien8_c64_tune_E.vi53')
OUT = os.path.join(HERE, '..', 'src', 'c64_tune.bin')
MAXDEPTH = 16


def load_rows(path):
    d = open(path, 'rb').read()
    return [struct.unpack_from('<3H', d, i * 6) for i in range(len(d) // 6)]


def rle(rows, divs):
    idx = {v: i for i, v in enumerate(divs)}
    voices = []
    for c in range(3):
        s, p, n = [], None, 0
        for r in rows:
            v = r[c]
            if v == p and n < 255:
                n += 1
            else:
                if p is not None:
                    s.append(('t', idx[p], n))
                p, n = v, 1
        s.append(('t', idx[p], n))
        voices.append(s)
    return voices


def repair(seqs, maxdepth):
    rules = []
    forbidden = set()
    dmemo = {}

    def depth(tok):
        if tok[0] == 't':
            return 0
        k = tok[1]
        if k not in dmemo:
            dmemo[k] = 1 + max((depth(t) for t in rules[k]), default=0)
        return dmemo[k]

    def size(t):
        return 2 if t[0] == 't' else 2

    while True:
        cnt = collections.Counter()
        for s in seqs + rules:
            for a, b in zip(s, s[1:]):
                if (a, b) not in forbidden:
                    cnt[(a, b)] += 1
        best = None
        for (a, b), c in cnt.most_common():
            gain = c * (size(a) + size(b) - 2) - (size(a) + size(b) + 1)
            if gain <= 0:
                break
            if 1 + max(depth(a), depth(b)) > maxdepth:
                forbidden.add((a, b))
                continue
            best = (a, b)
            break
        if best is None:
            break
        a, b = best
        k = len(rules)
        rules.append([a, b])
        r = ('r', k)
        for s in seqs + rules[:-1]:
            i = 0
            while i < len(s) - 1:
                if s[i] == a and s[i + 1] == b:
                    s[i:i + 2] = [r]
                i += 1
    return rules


def encode(seq):
    out = bytearray()
    for t in seq:
        if t[0] == 't':
            out += bytes([t[1], t[2]])
        else:
            out += bytes([0x80 | (t[1] >> 8), t[1] & 0xFF])
    out.append(0xFF)
    return bytes(out)


def build(rows):
    divs = sorted(set(v for r in rows for v in r))
    assert divs[0] == 0, 'индекс 0 должен быть тишиной'
    assert len(divs) <= 0x7F
    seqs = rle(rows, divs)
    rules = repair(seqs, MAXDEPTH)
    assert len(rules) < 0x7F00
    bodies = [encode(s) for s in seqs] + [encode(r) for r in rules]
    hdr = 6 + 2 + 2 * len(rules) + 2 + 2 * len(divs)
    ptrs, off = [], hdr
    for b in bodies:
        ptrs.append(off)
        off += len(b)
    blob = bytearray()
    blob += struct.pack('<3H', *ptrs[:3])
    blob += struct.pack('<H', len(rules)) + b''.join(struct.pack('<H', p) for p in ptrs[3:])
    blob += struct.pack('<H', len(divs)) + b''.join(struct.pack('<H', v) for v in divs)
    for b in bodies:
        blob += b
    return bytes(blob), len(rules), len(divs)


def decode(blob, frames, maxdepth=MAXDEPTH):
    """Эталонный декодер = то, что должен делать плеер на i8080."""
    va, vb, vc = struct.unpack_from('<3H', blob, 0)
    nr = struct.unpack_from('<H', blob, 6)[0]
    rptr = [struct.unpack_from('<H', blob, 8 + 2 * k)[0] for k in range(nr)]
    o = 8 + 2 * nr
    nd = struct.unpack_from('<H', blob, o)[0]
    divs = [struct.unpack_from('<H', blob, o + 2 + 2 * k)[0] for k in range(nd)]
    out = []
    for start in (va, vb, vc):
        pc, stack, res, cur, frames_out = start, [], 0, 0, []
        while len(frames_out) < frames:
            if res:
                res -= 1
                frames_out.append(cur)
                continue
            b = blob[pc]
            if b == 0xFF:
                if stack:
                    pc = stack.pop()
                else:
                    pc = start
            elif b & 0x80:
                k = ((b & 0x7F) << 8) | blob[pc + 1]
                stack.append(pc + 2)
                assert len(stack) <= maxdepth
                pc = rptr[k]
            else:
                cur = divs[b]
                res = blob[pc + 1]
                pc += 2
        out.append(frames_out)
    return [tuple(out[c][i] for c in range(3)) for i in range(frames)]


def main():
    rows = load_rows(SRC)
    blob, nr, nd = build(rows)
    got = decode(blob, len(rows))
    assert got == rows, 'self-check: декодер не воспроизвёл поток'
    # цикл: декодер после конца голоса начинает сначала — проверим ещё 100 кадров
    got2 = decode(blob, len(rows) + 100)
    assert got2[len(rows):] == rows[:100], 'self-check: зацикливание'
    with open(OUT, 'wb') as f:
        f.write(blob)
    print('кадров %d, правил %d, делителей %d, глубина ≤ %d, %s = %d байт; self-check ok' %
          (len(rows), nr, nd, MAXDEPTH, os.path.relpath(OUT, os.path.join(HERE, '..')), len(blob)))


if __name__ == '__main__':
    main()
