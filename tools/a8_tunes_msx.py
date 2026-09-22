#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Мелодии MSX-версии (меню, старт, проигрыш, финал, obj_5C, blip) -> готовые потоки ВИ53.

Заменяет проигрыватель MSX + пересчёт AY->ВИ53 на лету: звук считается здесь, заранее, по модели
драйвера MSX (~/projects/alien8-research/msx/msx_psg_model.py sim-tune), а в игре остаётся
только плеер потоков — тот же, что у темы C64 на заставке (формат tools/a8_tune_c64.py).

Пересчёт AY -> ВИ53 (правила как у Knight Lore §16, но офлайн):
  * такт ВИ53 1 497 600 Гц, AY MSX 1 789 772 / 16 -> делитель = период_AY * 13.388 (точный строй MSX);
  * тик проигрывателя MSX = 114 «проходов» = 1 кадр 50 Гц (замер SOUND.md §2.4, MSX_PASSES);
  * громкость: нота звучит, пока уровень >= 6 из 15 (порог KV/KL); огибающая AY (R13=0 — однократный
    спад, период R11/R12) моделируется по кадрам: 16 ступеней за 256*EP/f_AY секунд, R13 перезапускает;
  * шума и огибающей у ВИ53 нет; у этих шести мелодий шум не используется (проверяется здесь);
  * все мелодии <= 2 голосов: канал AY A -> счётчик 1, канал B -> счётчик 2 (счётчик 0 в игре = секундомер).

Выход: src/msx_tunes_vi53.bin:
  +0  слово N = 6 (число мелодий); далее N записей по 2 слова: смещение блоба, длина в кадрах;
  далее блобы в формате a8_tune_c64 (3 голоса: голос C всегда пустой — токен (0,255) + 0xFF).
Плеер играет ровно «длина в кадрах» тиков и глушит счётчики (мелодии не зациклены).
Превью: build/tmp/msx_tunes_vi53/<имя>.wav + all.wav (все подряд с паузой 1 с).
"""
import os
import re
import struct
import subprocess
import sys
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import a8_tune_c64 as T  # noqa: E402

MSX_DIR = os.path.expanduser('~/projects/alien8-research/msx')
MODEL = os.path.join(MSX_DIR, 'msx_psg_model.py')
OUT = os.path.join(HERE, '..', 'src', 'msx_tunes_vi53.bin')
PREVIEW = os.path.join(HERE, '..', 'build', 'tmp', 'msx_tunes_vi53')
TUNES = ['start_game', 'game_over', 'game_complete', 'menu', 'obj_5C', 'blip']
PASSES = 114
AYCLK = 1789772.0 / 16
TCLK = 1497600.0
VOL_MIN = 6
FPS = 50


def sim(tune):
    out = subprocess.run([sys.executable, MODEL, 'sim-tune', tune], capture_output=True, text=True, cwd=MSX_DIR).stdout
    ev = {}
    for l in out.splitlines():
        m = re.match(r'\s*(\d+)\s+R(\d+)\s+([0-9A-F]+)', l)
        if m:
            ev.setdefault(int(m[1]), []).append((int(m[2]), int(m[3], 16)))
    assert ev, 'sim-tune %s: нет событий' % tune
    return ev


def frames(ev):
    """События по проходам -> кадры: (делитель счётчика 1, делитель счётчика 2), 0 = молчит."""
    regs = [0] * 14
    regs[7] = 0x3F
    env_t = None          # кадр перезапуска огибающей
    nfr = max(ev) // PASSES + 1
    rows = []
    for f in range(nfr):
        for p in range(f * PASSES, (f + 1) * PASSES):
            for r, v in ev.get(p, []):
                regs[r] = v
                if r == 13:
                    env_t = f
        ep = regs[11] | (regs[12] << 8)
        if env_t is None or ep == 0:
            env_lvl = 0
        else:
            step_s = 256.0 * ep / (1789772.0 * 16)   # одна из 16 ступеней спада
            k = int((f - env_t) / FPS / step_s)
            env_lvl = max(0, 15 - k)                  # форма 0: спад 15 -> 0, затем 0
            assert regs[13] in (0, 9), 'форма огибающей %d не моделируется' % regs[13]
        row = []
        for c in range(3):
            per = regs[2 * c] | ((regs[2 * c + 1] & 15) << 8)
            tone = not (regs[7] & (1 << c))
            noise = not (regs[7] & (8 << c))
            assert not (noise and (regs[8 + c] & 31)), 'шум в мелодии — не ожидалось'
            lvl = env_lvl if (regs[8 + c] & 16) else (regs[8 + c] & 15)
            if tone and per and lvl >= VOL_MIN:
                row.append(max(2, min(65535, int(round(per * TCLK / AYCLK)))))
            else:
                row.append(0)
        assert row[2] == 0, 'канал C занят — мелодии считались двухголосными'
        rows.append(tuple(row))
    while rows and rows[-1] == (0, 0, 0):
        rows.pop()
    rows.append((0, 0, 0))   # последний кадр — тишина: плеер глушит счётчики
    return rows


def render_wav(rows, path):
    sr = 44100
    n = len(rows) * sr // FPS
    import array
    y = array.array('f', [0.0]) * n
    ph = [0.0, 0.0, 0.0]
    for i, row in enumerate(rows):
        s0, s1 = i * sr // FPS, (i + 1) * sr // FPS
        for c, dv in enumerate(row):
            if not dv:
                continue
            hz = TCLK / dv
            for s in range(s0, s1):
                ph[c] = (ph[c] + hz / sr) % 1.0
                y[s] += 0.3 if ph[c] < 0.5 else -0.3
    w = wave.open(path, 'wb')
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(sr)
    w.writeframes(array.array('h', [int(max(-1, min(1, v)) * 32000) for v in y]).tobytes())
    w.close()


def main():
    os.makedirs(PREVIEW, exist_ok=True)
    blobs, allrows = [], []
    for name in TUNES:
        rows = frames(sim(name))
        blob, nr, nd = T.build(rows)
        got = T.decode(blob, len(rows))
        assert got == rows, 'self-check %s: декодер не воспроизвёл поток' % name
        blobs.append((name, blob, len(rows)))
        with open(os.path.join(PREVIEW, name + '.vi53'), 'wb') as f:
            for r in rows:
                f.write(struct.pack('<3H', *r))
        render_wav(rows, os.path.join(PREVIEW, name + '.wav'))
        allrows += rows + [(0, 0, 0)] * FPS
        print('%-14s кадров %5d (%5.1f с) правил %3d делителей %2d -> %4d Б' % (name, len(rows), len(rows) / FPS, nr, nd, len(blob)))
    render_wav(allrows, os.path.join(PREVIEW, 'all.wav'))
    hdr = 2 + 4 * len(blobs)
    out = bytearray(struct.pack('<H', len(blobs)))
    off = hdr
    for name, blob, nfr in blobs:
        out += struct.pack('<HH', off, nfr)
        off += len(blob)
    for name, blob, nfr in blobs:
        out += blob
    with open(OUT, 'wb') as f:
        f.write(out)
    # self-check каталога
    d = bytes(out)
    n = struct.unpack_from('<H', d, 0)[0]
    for i, (name, blob, nfr) in enumerate(blobs):
        o, fr = struct.unpack_from('<HH', d, 2 + 4 * i)
        assert d[o:o + len(blob)] == blob and fr == nfr
    print('итого %s = %d Б (%d мелодий); превью %s' % (os.path.relpath(OUT, os.path.join(HERE, '..')), len(out), n, os.path.relpath(PREVIEW, os.path.join(HERE, '..'))))


if __name__ == '__main__':
    main()
