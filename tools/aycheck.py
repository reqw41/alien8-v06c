#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Гейт звука эффектов на ВИ53: журнал tools/aytrace_vec.js против модели MSX + конверсии слива.

    node tools/aytrace_vec.js build/alien8_vec.r0m build/alien8_vec.sld <итераций> > build/ay.txt
    python3 tools/aycheck.py build/ay.txt

Эталон строится НЕЗАВИСИМО от кода Вектора:
  1. регистры AY — модель движка эффектов MSX (~/projects/alien8-research/msx/msx_psg_model.py,
     класс Sfx: тики, микшер, гашение), по тикам в том порядке, в каком их выполнил Вектор
     (TK-строки журнала: 56 тиков на итерацию — у MSX тик стоит в цикле по 56 объектам; сколько
     их вышло на самом деле, тоже сверяется, см. ниже). Положение запуска эффекта среди TK-строк
     и есть его фаза t0 (0..55) — она наблюдается, а не подбирается: перебор фазы мог бы
     «спрятать» порчу порога громкости, подобрав фазу, при которой громкость на сливе другая;
  2. зеркало регистров: всё, что модель пишет в AY, плюс тишина после каждого слива
     (R7 := 0xBF, R8..R10 := 0; периоды и R6 остаются) и лесенка audio_msx_ladder (LAD-строка:
     тон канала A в тени R7, восемь ступеней, в конце громкость 0);
  3. слив раз в итерацию (FL-строка) — конверсия, переписанная с asm (tools/a8_sound_ay.py,
     msx_vcalc/msx_ay2vi/mvc_off/msx_viwant/msx_viemit, а не с описания):
       громкость R(8+c) < 6 -> канал молчит (байт целиком: бит огибающей 0x10 даёт >= 16 = полный);
       ~R7 & (0x09,0x12,0x24)[c] == 0 -> молчит; & 0x07 == 0 (только шум) -> делитель (R6&0x1F, 0->1)*256;
       тон: P = R(2c) | (R(2c+1)&0x0F)<<8, делитель = 13P + P//2; делитель < 64 -> молчит;
       отложенная нота msx_vhold (KL §20): гашение слота (msx_sfx_kill) ставит 1 (тон) / 2 (шум,
       эффект 1), если метка 0; живой голос на сливе ставит 3; молчащий канал на сливе метку
       обнуляет и, если было 1/2, звучит тоном/шумом по зеркалу (БЕЗ порога громкости);
       запуск эффекта через msx_sfx_start (SFX-строка) метку слота обнуляет, запуск стендом
       (SFXI, A8SFX) — нет;
       раскладка: B -> счётчик 1, C -> 2, A берёт свободный (сперва 2, потом 1), третий отброшен;
       выдача: управляющее слово только при смене владельца (и при уходе в тишину), делитель —
       только если отличается от кэша (при смене владельца кэш бьётся).
Сверка по кадрам: эффективный делитель счётчиков 1,2 на конец кадра (V) и число управляющих
слов / загрузок делителя за кадр (P). Кадры, в которых играет мелодия (TUNE..TEND), не
сверяются — мелодии судит tools/tunecheck_vec.js; на TUNE/TEND владельцы сбрасываются, как в
msx_tv_mute.

Код возврата: 0 — расхождений нет; 1 — есть расхождения или выборка пуста/вакуумна.
"""
import os
import sys

sys.path.insert(0, os.path.expanduser('~/projects/alien8-research/msx'))
import msx_psg_model as M   # noqa: E402

TICKS = 56                       # тиков движка эффектов за игровую итерацию (MSX: 56 объектов)
KMASK = (0x09, 0x12, 0x24)       # биты тона и шума канала в R7 (msx_kmask, MSX 0x4402)
VOL_MIN = 6                      # порог громкости 6/15
DIV_MIN = 64                     # делитель < 64 — выше 23 кГц, молчит
FF = 0xFF


class Sfx(M.Sfx):
    """Модель MSX + крючок гашения для отложенной ноты (msx_sfx_kill -> msx_vhkill)."""

    def __init__(self, box):
        super().__init__()
        self.box = box

    def kill(self, s):
        sid = self.slot[s][0]
        super().kill(s)
        if self.box.vhold[s] == 0:
            self.box.vhold[s] = 2 if sid == 1 else 1


class Model:
    def __init__(self):
        self.vhold = [0, 0, 0]
        self.e = Sfx(self)
        self.busy = 0
        self.regs = [0] * 16
        self.silence()
        self.own = [FF, FF, FF]
        self.cache = [0xFFFF] * 3
        self.eff = [0, 0, 0]
        self.nctl = [0, 0, 0]
        self.nld = [0, 0, 0]
        self.vdiv = [0, 0, 0]

    def drain(self):
        for _t, r, v in self.e.log:
            self.regs[r & 0x0F] = v & 0xFF
        self.e.log = []

    def silence(self):
        self.regs[7] = 0xBF
        self.regs[8] = self.regs[9] = self.regs[10] = 0

    def init(self):                      # msx_snd_init
        self.e.slot = [[0, 0, 0, 0] for _ in range(3)]
        self.e.mix = 0xBF
        self.busy = 0
        self.vhold = [0, 0, 0]
        self.silence()
        self.mute()

    def mute(self):                      # msx_tv_mute: оба счётчика стоят, владельцев нет
        for c in (1, 2):
            self.nctl[c] += 1
            self.own[c] = FF
            self.eff[c] = 0

    def start(self, slot, sid, ticks, hi, lo, stepc, x, y, vhnew):
        if vhnew:
            self.vhold[slot] = 0
        if sid == 3:
            self.e.stepc, self.e.plx, self.e.ply = stepc, x, y
        self.e.start(sid, ticks, hi, lo, slot)
        self.busy = 1

    def tick(self):
        self.e.tick()
        self.drain()
        if all(s[0] == 0 for s in self.e.slot):
            self.busy = 0

    def ladder(self):                    # audio_msx_ladder: мимо движка, прямо в зеркало
        self.e.mix &= 0xFE
        self.regs[7] = self.e.mix
        for b in range(8, 0, -1):
            self.regs[0] = ((b - 1) << 4) & 0xFF
            self.regs[1] = 0
            self.regs[8] = 0x0F
        self.regs[8] = 0

    # ---- слив (msx_viflush) ----
    def tone(self, c):
        p = self.regs[2 * c] | ((self.regs[2 * c + 1] & 0x0F) << 8)
        d = (13 * p + (p >> 1)) & 0xFFFF
        if d < DIV_MIN:
            return self.off(c)
        return self.on(c, d)

    def noise(self, c):
        n = self.regs[6] & 0x1F
        return self.on(c, (n or 1) << 8)

    def on(self, c, d):
        self.vdiv[c] = d
        self.vhold[c] = 3
        return True

    def off(self, c):
        h = self.vhold[c]
        self.vhold[c] = 0
        if h == 1:
            return self.tone(c)
        if h == 2:
            return self.noise(c)
        return False

    def vcalc(self, c):
        if self.regs[8 + c] < VOL_MIN:
            return self.off(c)
        a = KMASK[c] & (~self.regs[7] & 0xFF)
        if a == 0:
            return self.off(c)
        if a & 0x07 == 0:
            return self.noise(c)
        return self.tone(c)

    def flush(self):
        act = [self.vcalc(c) for c in range(3)]
        w = [FF, 1 if act[1] else FF, 2 if act[2] else FF]
        if act[0]:
            if w[2] == FF:
                w[2] = 0
            elif w[1] == FF:
                w[1] = 0
        for c in (1, 2):
            if w[c] == FF:
                if self.own[c] != FF:
                    self.own[c] = FF
                    self.nctl[c] += 1
                    self.eff[c] = 0
                continue
            if w[c] != self.own[c]:
                self.own[c] = w[c]
                self.nctl[c] += 1
                self.eff[c] = 0
                self.cache[c] = 0xFFFF
            d = self.vdiv[w[c]]
            if d != self.cache[c]:
                self.cache[c] = d
                self.nld[c] += 1
                self.eff[c] = d
        self.silence()
        return w


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    m = Model()
    playing = False
    tframe = False                        # в этом кадре играла мелодия — кадр не сверяется
    started = False                       # сверка — с первой игровой строки (ITER/TK/FL)
    obs = {}                              # кадр -> {c: [V, упр, загр]}
    bad = 0
    shown = 0
    nfr = nfr_snd = nfl = nfl_snd = 0
    ids = set()
    heard = set()
    live = {}                             # слот -> id эффекта, для учёта «кто звучал»
    nsfx = nsfxi = nlad = 0
    ntk = 0
    prev_busy_fl = 0
    tk_full = tk_bad = 0
    lines = [ln.split() for ln in open(sys.argv[1], encoding='utf-8')]

    def check_frame(f):
        nonlocal bad, shown, nfr, nfr_snd
        o = obs.pop(f, None)
        if o is None:
            return
        if started and not tframe:
            nfr += 1
            if m.eff[1] or m.eff[2]:
                nfr_snd += 1
            for c in (1, 2):
                v, k, ld = o.get(c, [None, 0, 0])
                exp = (m.eff[c], m.nctl[c], m.nld[c])
                if (v, k, ld) != exp:
                    bad += 1
                    if shown < 12:
                        shown += 1
                        print('  кадр %d счётчик %d: у нас делитель %s упр %d загр %d; модель %d упр %d загр %d'
                              % (f, c, v, k, ld, exp[0], exp[1], exp[2]))
        m.nctl = [0, 0, 0]
        m.nld = [0, 0, 0]

    # V/P-строки кадра f идут в журнале в конце кадра, после событий кадра: копим и сверяем
    # по приходу V счётчика 2 (последняя строка итога кадра, P печатается между V1 и V2)
    pend_f = None
    for p in lines:
        if not p:
            continue
        t = p[0]
        if t == 'V':
            f, c, v = int(p[1]), int(p[2]), int(p[3])
            if pend_f is not None and pend_f != f:     # итоги двух кадров подряд, без событий
                check_frame(pend_f)
                tframe = playing
            obs.setdefault(f, {}).setdefault(c, [v, 0, 0])[0] = v
            pend_f = f
            continue
        if t == 'P':
            f, c = int(p[1]), int(p[2])
            ent = obs.setdefault(f, {}).setdefault(c, [None, 0, 0])
            ent[1], ent[2] = int(p[3]), int(p[4])
            continue
        # любое событие после итога кадра — кадр закрыт
        if pend_f is not None:
            check_frame(pend_f)
            tframe = playing
            pend_f = None
        if t == 'TUNE':
            playing = True
            tframe = True
            m.mute()
        elif t == 'TEND':
            playing = False
            tframe = True
            m.mute()
        elif t == 'INIT':
            m.init()
        elif t in ('ITER', 'TK', 'FL'):
            started = True
            if t == 'TK':
                ntk += 1
                m.tick()
            elif t == 'FL':
                if playing:
                    continue
                nfl += 1
                # число тиков итерации: если движок был занят весь объектный цикл (занят на
                # прошлом сливе и занят сейчас), тиков ровно 56
                if prev_busy_fl and m.busy:
                    tk_full += 1
                    if ntk != TICKS:
                        tk_bad += 1
                        bad += 1
                        if shown < 12:
                            shown += 1
                            print('  кадр %s: за итерацию тиков %d, у MSX %d' % (p[1], ntk, TICKS))
                elif ntk > TICKS:
                    tk_bad += 1
                    bad += 1
                    print('  кадр %s: за итерацию тиков %d > %d' % (p[1], ntk, TICKS))
                ntk = 0
                w = m.flush()
                if w[1] != FF or w[2] != FF:
                    nfl_snd += 1
                    for c in (1, 2):
                        if w[c] != FF and w[c] in live:
                            heard.add(live[w[c]])
                prev_busy_fl = m.busy
                live = {s: m.e.slot[s][0] for s in range(3) if m.e.slot[s][0]}
        elif t in ('SFX', 'SFXI'):
            a = [int(x) for x in p[1:]]
            f0, slot, sid, ticks, hi, lo = a[:6]
            stepc, x, y = (a[6:] + [0, 0, 0])[:3]
            m.start(slot, sid, ticks, hi, lo, stepc, x, y, vhnew=(t == 'SFX'))
            ids.add(sid)
            live[slot] = sid
            if t == 'SFX':
                nsfx += 1
            else:
                nsfxi += 1
        elif t == 'LAD':
            m.ladder()
            nlad += 1
    if pend_f is not None:
        check_frame(pend_f)
    heard.discard(0)
    print('журнал: кадров сверено %d (со звуком по модели %d), сливов %d (со звуком %d), '
          'запусков эффектов %d + стендом %d, лесенок %d'
          % (nfr, nfr_snd, nfl, nfl_snd, nsfx, nsfxi, nlad))
    print('эффекты: запущены id %s; слышны на сливе id %s'
          % (','.join(map(str, sorted(ids))) or '-', ','.join(map(str, sorted(heard))) or '-'))
    print('тики: итераций с занятым движком целиком %d, из них не по %d тиков: %d' % (tk_full, TICKS, tk_bad))
    if nfr == 0 or nfl == 0:
        print('ГЕЙТ ПУСТ: нет ни сверенных кадров, ни сливов')
        return 1
    if nfr_snd == 0:
        print('ГЕЙТ ВАКУУМЕН: по модели ни в одном кадре счётчики не звучат')
        return 1
    print('ИТОГО расхождений: %d' % bad)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
