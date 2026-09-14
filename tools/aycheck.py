#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Гейт звука: поканальная сверка журнала записей AY Вектора с моделью MSX.

    node tools/aytrace_vec.js build/alien8_vec.r0m build/alien8_vec.sld ... > build/ay.txt
    python3 tools/aycheck.py build/ay.txt [--frames N]

Зачем поканально. У MSX проигрыватель обходит три канала по разу за «проход», а у нас
каждый канал отматывает свои 114 проходов подряд — ГЛОБАЛЬНЫЙ порядок записей разный,
а последовательность ВНУТРИ канала обязана совпасть байт в байт. То же у эффектов:
слот жёстко привязан к каналу (0 -> A, 1 -> B, 2 -> C).

Регистр 7 (микшер) общий для трёх каналов, поэтому в поканальную сверку он не входит:
при двух одновременных эффектах его значение зависит от порядка, которого у MSX и у нас
быть одинаковым не может. Он проверяется отдельно — по числу записей на эффект.

Код возврата: 0 — расхождений нет; 1 — есть расхождения или выборка пуста.
"""
import os
import sys

sys.path.insert(0, os.path.expanduser('~/projects/alien8-research/msx'))
import msx_psg_model as M   # noqa: E402

PASSES = 114        # «проходов» MSX за видеокадр (живой замер, SOUND.md §2.4)

# регистр AY -> канал (0 = A, 1 = B, 2 = C); None — общий
CHAN = {0: 0, 1: 0, 8: 0, 2: 1, 3: 1, 9: 1, 4: 2, 5: 2, 10: 2}
CHNAME = 'ABC'
# слот эффекта -> канал AY
SLOT_CH = {0: 0, 1: 1, 2: 2}


def parse(path):
    """Журнал разбирается С СОХРАНЕНИЕМ ПОРЯДКА: у события и у записи одного кадра номер
    кадра одинаков, поэтому «после метки TUNE» отличается от «в кадре метки» — список
    инициализации PSG пишется в том же кадре, но ДО метки."""
    ev, w = [], []
    for line in open(path, encoding='utf-8'):
        p = line.split()
        if not p:
            continue
        if p[0] == 'W':
            w.append((int(p[1]), int(p[2]), int(p[3])))
        elif p[0] in ('TUNE', 'SFX', 'ITER'):
            ev.append((p[0], [int(x) for x in p[1:]], len(w)))   # len(w) = позиция в потоке записей
    return ev, w


def tune_by_offset(off):
    """Смещение потока канала 2 в пуле -> имя мелодии."""
    lo, _hi = M.stream_bounds()
    for i, nm in enumerate(M.TUNE_NAMES):
        if M.rw(M.A_HEADERS + 6 * i + 4) - lo == off:
            return i, nm
    return None, None


STOP = [(7, 0xBF), (8, 0), (9, 0), (10, 0)]


def strip_stop(writes):
    out, i, n = [], 0, len(writes)
    while i < n:
        if [(r, v) for _f, r, v in writes[i:i + 4]] == STOP:
            i += 4
            continue
        out.append(writes[i])
        i += 1
    return out


def split(writes, chan):
    return [(f, r, v) for f, r, v in writes if CHAN.get(r) == chan]


def check_tune(idx, name, f0, writes, nframes, rep):
    """Сверка одной мелодии: модель на nframes кадров, поканально."""
    t = M.Tune(M.A_HEADERS + 6 * idx)
    t.run(nframes * PASSES)
    mlog = t.log[len(M.rlist(M.A_INIT)):]        # список инициализации PSG идёт до метки TUNE
    ours = writes
    bad = 0
    for ch in range(3):
        mc = [(p, r, v) for p, r, v in mlog if CHAN.get(r) == ch]
        oc = split(ours, ch)
        n = min(len(mc), len(oc))
        if n == 0:
            continue
        mism = 0
        tail = 0
        shift = set()
        for i in range(n):
            (p, r, v), (f, r2, v2) = mc[i], oc[i]
            if (r, v) != (r2, v2):
                # ХВОСТ ПОСЛЕ END. У MSX END останавливает проигрыватель посреди «прохода»,
                # и каналы, до которых очередь в этом проходе не дошла, замолкают сразу.
                # У нас каждый канал отматывает свои 114 проходов ПОДРЯД, поэтому канал,
                # обслуживаемый раньше канала с END, успевает сделать ещё одну выборку в
                # последнем кадре. Слышимого следа нет: сразу за ней идёт список тишины.
                # Допуск — не больше одной такой записи на канал.
                if (r, v) in STOP and i >= len(mc) - len(STOP):
                    tail += 1
                    continue
                mism += 1
                if mism <= 3:
                    print('  канал %s запись %d: модель R%d=%02X, у нас R%d=%02X'
                          % (CHNAME[ch], i, r, v, r2, v2))
            shift.add(f - (f0 + (p - 1) // PASSES + 1))
        if tail > 1:
            print('  канал %s: хвост после END длиннее одной записи (%d) — это уже дефект' % (CHNAME[ch], tail))
            mism += tail
        bad += mism
        print('  канал %s: сверено %d записей (модель %d, у нас %d), расхождений %d%s, сдвиг кадра %s'
              % (CHNAME[ch], n, len(mc), len(oc), mism,
                 (', хвост после END %d' % tail) if tail else '',
                 ','.join(str(x) for x in sorted(shift)) if shift else '-'))
    rep.append((name, bad))
    return bad


def check_sfx(slot, sid, ticks, hi, lo, f0, writes, rep, stepc=0, plx=0, ply=0):
    """Сверка одного эффекта: модель тикает ticks раз, сверяем канал слота (плюс R6 у шума).

    Эффекту 3 («шаги») нужны живые счётчик шагов и координаты игрока — их журнал снимает
    в момент запуска. Внутри итерации они не меняются (обработчик игрока отрабатывает
    ДО звука), а все 23 тика укладываются в одну итерацию.
    """
    e = M.Sfx(stepc=stepc, plx=plx, ply=ply)
    e.start(sid, ticks, hi, lo, slot)
    for _ in range(ticks):
        e.tick()
    ch = SLOT_CH[slot]
    # Глушение AY в конце игровой итерации (msx_frame_off, MSX 0x41A3) — список из четырёх
    # записей R7=BF,R8=0,R9=0,R10=0. В модели одного эффекта его нет, поэтому убираем.
    writes = strip_stop(writes)
    regs = {0: [0, 1, 8], 1: [2, 3, 9], 2: [4, 5, 10]}[ch]
    if sid == 1:
        regs = regs + [6]
    mc = [(r, v) for _t, r, v in e.log if r in regs]
    oc = [(r, v) for f, r, v in writes if r in regs]
    n = min(len(mc), len(oc))
    mism = sum(1 for i in range(n) if mc[i] != oc[i])
    shown = 0
    for i in range(n):
        if mc[i] != oc[i] and shown < 3:
            shown += 1
            print('  эффект %d слот %d запись %d: модель R%d=%02X, у нас R%d=%02X'
                  % (sid, slot, i, mc[i][0], mc[i][1], oc[i][0], oc[i][1]))
    full = (n == len(mc) and n > 0)
    print('  эффект %d (слот %d, канал %s, %d тиков, параметр %02X%02X): сверено %d из %d%s, расхождений %d'
          % (sid, slot, CHNAME[ch], ticks, hi, lo, n, len(mc),
             '' if full else ' (оборван следующим эффектом того же слота)', mism))
    rep.append(('эффект %d' % sid, mism))
    return mism, n, full


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    ev, w = parse(sys.argv[1])
    if not w:
        print('ГЕЙТ ПУСТ: в журнале нет ни одной записи в AY')
        return 1
    lastf = w[-1][0]
    rep = []
    tunes = [e for e in ev if e[0] == 'TUNE']
    sfxs = [e for e in ev if e[0] == 'SFX']
    if not tunes and not sfxs:
        print('ГЕЙТ ПУСТ: в журнале нет ни мелодий, ни эффектов (записей %d)' % len(w))
        return 1
    print('журнал: записей %d, кадров %d, мелодий %d, эффектов %d' % (len(w), lastf, len(tunes), len(sfxs)))
    for k, (_, a, pos) in enumerate(tunes):
        f0, off = a[0], a[1]
        idx, name = tune_by_offset(off)
        if idx is None:
            print('МЕЛОДИЯ на кадре %d: смещение %d не совпало ни с одним заголовком' % (f0, off))
            rep.append(('мелодия@%d' % f0, 1))
            continue
        nxt = tunes[k + 1][2] if k + 1 < len(tunes) else len(w)
        seg = w[pos:nxt]
        print('мелодия %s, кадр %d..%d:' % (name, f0, seg[-1][0] if seg else f0))
        check_tune(idx, name, f0, seg, (seg[-1][0] if seg else f0) - f0 + 1, rep)
    # эффекты: сверяем только те, что начались в тишине (ни мелодии, ни другого эффекта
    # на том же канале в этот момент) — иначе журнал канала содержит чужие записи
    seen = set()
    cov = [0, 0]
    ids = set()
    for k, (_, a, pos) in enumerate(sfxs):
        f0, slot, sid, ticks, hi, lo = a[:6]
        stepc, plx, ply = (a[6:] + [0, 0, 0])[:3]
        if (slot, sid, hi, lo) in seen:
            continue
        seen.add((slot, sid, hi, lo))
        nxt = next((x[2] for x in sfxs[k + 1:] if x[1][1] == slot), len(w))
        if nxt <= pos:
            continue
        _m, _n, full = check_sfx(slot, sid, ticks, hi, lo, f0, w[pos:nxt], rep, stepc, plx, ply)
        cov[0] += _n
        cov[1] += 1 if full else 0
        ids.add(sid)
    total = sum(b for _, b in rep)
    print('---')
    if sfxs:
        print('эффекты: сверено записей %d, эффектов целиком %d, встречены id %s'
              % (cov[0], cov[1], ','.join(str(x) for x in sorted(ids))))
        if cov[1] == 0:
            print('ГЕЙТ ВАКУУМЕН: ни один эффект не досверен до конца (все оборваны)')
            total += 1
    print('проверено: %s' % ', '.join('%s %s' % (n, 'ОК' if b == 0 else 'РАСХОЖДЕНИЙ %d' % b) for n, b in rep))
    print('ИТОГО расхождений: %d' % total)
    return 1 if total else 0


if __name__ == '__main__':
    sys.exit(main())
