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

ДОЛГИЕ ПУТИ БЕЗ СЛИВА (дефект с железа: нота висит при смене комнаты). Слив раз в итерацию
держит ноту до следующего слива — на обычной итерации это 1..7 кадров, но смена комнаты
(GL: game_loop -> build_screen_objects + первая отрисовка), GAME OVER (GO: экран рисуется до
мелодии) и пауза (PZ: ждём отпускания ВК) идут десятки кадров без слива. У MSX на всех трёх
путях AY молчит: глушение 0x41A3 прошло в конце прошлой итерации, а тиков эффектов до входа
в путь нет (игрок — первый объект таблицы, exit_screen срабатывает до первого тика; GAME OVER
и пауза стоят после 0x41A3). Поэтому на входе в путь счётчики 1,2 глушатся (msx_tv_mute), и
гейт требует: в каждом кадре ПОСЛЕ кадра события и до следующего слива (VF) или мелодии
(TUNE) делители обоих счётчиков = 0. Кадр самого события не требуется: граница кадра может
лечь между событием и глушением. Модель на событии делает то же msx_tv_mute (владельцы 0xFF).
Ключ --need GL,GO,PZ — такие события обязаны встретиться хотя бы раз со звучащим на входе
счётчиком (иначе проверка вакуумна).

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
        self.lad = 0

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
        self.e.mix &= 0xFE               # msx_tone_on слота 0 (тень R7 остаётся с тоном A)
        self.regs[7] = self.e.mix
        self.lad = 8                     # ступени B = 8..1, слив (VF) после каждой

    def ladder_step(self):
        b = self.lad
        self.regs[0] = ((b - 1) << 4) & 0xFF     # период (B-1)*16
        self.regs[1] = 0
        self.regs[8] = 0x0F

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
        """msx_viflush. Тишину (msx_silence) после слива делает вызыватель — msx_frame_off."""
        last = False
        if self.lad:
            self.ladder_step()
            self.lad -= 1
            last = self.lad == 0
        w = self._flush()
        if last:
            self.regs[8] = 0                     # лесенка: `xor a / call msx_setvol` на выходе
        return w

    def _flush(self):
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
        return w


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--need')]
    need = set()
    for a in sys.argv[1:]:
        if a.startswith('--need='):
            need |= set(a.split('=', 1)[1].split(','))
    if not args:
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
    prev_busy_it = 0
    pend_sil = False                      # FL был, его слив (VF) ещё не пришёл
    nfl_lad = 0
    vopen = False                         # слив начат (VF), итог (VE) ещё не пришёл
    vexp = None
    nfr_open = 0
    tk_full = tk_bad = 0
    lines = [ln.split() for ln in open(args[0], encoding='utf-8')]
    lng = None                            # открытый долгий путь: [вид, кадр события]
    cur = [0, 0, 0]                       # делители счётчиков по журналу (последние V / VE)
    lng_n = {}                            # вид -> [событий, со звуком на входе]
    lng_bad = 0
    lng_hang = {}                         # вид -> худшее число кадров со звуком после события

    # Сверка кадра: делитель на конец кадра (V) и НАКОПИТЕЛЬНОЕ число управляющих слов и
    # загрузок (P) — накопительно, потому что слив может перейти границу кадра: в кадре, на конец
    # которого слив открыт (VF без VE), кадр не сверяется, но его записи учтутся в следующем.
    # Кадры мелодий не сверяются; после них счёт модели выравнивается по журналу.
    cum_tr = {1: [0, 0], 2: [0, 0]}
    cum_md = {1: [0, 0], 2: [0, 0]}

    def check_frame(f):
        nonlocal bad, shown, nfr, nfr_snd, nfr_open
        o = obs.pop(f, None)
        if o is None:
            return
        for c in (1, 2):
            _v, k, ld = o.get(c, [None, 0, 0])
            cum_tr[c][0] += k
            cum_tr[c][1] += ld
            cum_md[c][0] += m.nctl[c]
            cum_md[c][1] += m.nld[c]
        m.nctl = [0, 0, 0]
        m.nld = [0, 0, 0]
        if not started or tframe:
            for c in (1, 2):
                cum_md[c] = list(cum_tr[c])
            return
        if vopen:
            nfr_open += 1
            return
        if lng is not None and f > lng[1]:
            vs = [o.get(c, [0])[0] or 0 for c in (1, 2)]
            if vs[0] or vs[1]:
                nonlocal lng_bad
                lng_bad += 1
                bad += 1
                lng_hang[lng[0]] = max(lng_hang.get(lng[0], 0), f - lng[1])
                if shown < 12:
                    shown += 1
                    print('  кадр %d: %s с кадра %d, слива не было, а счётчики звучат: д1 д2 = %s'
                          % (f, lng[0], lng[1], vs))
        nfr += 1
        if m.eff[1] or m.eff[2]:
            nfr_snd += 1
        for c in (1, 2):
            v = o.get(c, [None])[0]
            if v != m.eff[c] or cum_tr[c] != cum_md[c]:
                bad += 1
                if shown < 12:
                    shown += 1
                    print('  кадр %d счётчик %d: у нас делитель %s, упр/загр с начала %s; модель %d, %s'
                          % (f, c, v, cum_tr[c], m.eff[c], cum_md[c]))
                cum_md[c] = list(cum_tr[c])          # одно расхождение — одна жалоба

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
            cur[c] = v
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
        if t in ('GL', 'GO', 'PZ'):
            ent = lng_n.setdefault(t, [0, 0])
            ent[0] += 1
            if cur[1] or cur[2]:
                ent[1] += 1
            lng = [t, int(p[1])]
            m.mute()                                   # msx_tv_mute на входе в путь
            continue
        if t in ('TUNE', 'VF'):
            lng = None
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
        elif t in ('ITER', 'TK', 'FL', 'VF', 'VE'):
            started = True
            if t == 'TK':
                ntk += 1
                m.tick()
            elif t == 'ITER':
                # тики итерации: объектный цикл лежит между двумя ITER-строками. Если движок был
                # занят весь цикл (занят на прошлой ITER и занят сейчас), тиков ровно 56
                if prev_busy_it and m.busy:
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
                prev_busy_it = m.busy
            elif t == 'FL':
                if m.lad:
                    bad += 1
                    print('  кадр %s: лесенка кончилась, а сливов в ней %d из 8' % (p[1], 8 - m.lad))
                    m.lad = 0
                if playing:
                    continue
                if pend_sil:
                    bad += 1
                    print('  кадр %s: msx_frame_off без слива в предыдущей итерации' % p[1])
                pend_sil = True
            elif t == 'VE':
                vopen = False
                got = [int(x) for x in p[2:8]]
                cur[1], cur[2] = got[0], got[1]
                if got != vexp:
                    bad += 1
                    if shown < 12:
                        shown += 1
                        print('  слив кадра %s: у нас д1 д2 у1 з1 у2 з2 = %s; модель %s' % (p[1], got, vexp))
            else:                                          # VF: слив
                vopen = True
                c0 = (m.nctl[1], m.nld[1], m.nctl[2], m.nld[2])
                lad = m.lad
                if not pend_sil and not lad:
                    bad += 1
                    print('  кадр %s: слив вне msx_frame_off и вне лесенки' % p[1])
                nfl += 1
                w = m.flush()
                vexp = [m.eff[1], m.eff[2], m.nctl[1] - c0[0], m.nld[1] - c0[1],
                        m.nctl[2] - c0[2], m.nld[2] - c0[3]]
                if lad:
                    nfl_lad += 1
                if pend_sil:
                    m.silence()
                    pend_sil = False
                if w[1] != FF or w[2] != FF:
                    nfl_snd += 1
                    for c in (1, 2):
                        if w[c] != FF:
                            heard.add('лесенка' if lad else live.get(w[c], 0))
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
            if m.lad:
                bad += 1
                print('  кадр %s: лесенка до конца прошлой — сливов в ней %d из 8' % (p[1], 8 - m.lad))
            m.ladder()
            nlad += 1
    if pend_f is not None:
        check_frame(pend_f)
    heard.discard(0)
    heard = set(map(str, heard))
    print('журнал: кадров сверено %d (со звуком по модели %d; на конец кадра слив открыт — %d), сливов %d (со звуком %d, из лесенки %d), '
          'запусков эффектов %d + стендом %d, лесенок %d'
          % (nfr, nfr_snd, nfr_open, nfl, nfl_snd, nfl_lad, nsfx, nsfxi, nlad))
    if m.lad or pend_sil:
        bad += 1
        print('  журнал оборван посреди лесенки/слива (лесенка: осталось ступеней %d)' % m.lad)
    print('эффекты: запущены id %s; слышны на сливе id %s'
          % (','.join(map(str, sorted(ids))) or '-', ','.join(sorted(heard)) or '-'))
    print('тики: итераций с занятым движком целиком %d, из них не по %d тиков: %d' % (tk_full, TICKS, tk_bad))
    print('долгие пути без слива (GL смена комнаты, GO GAME OVER, PZ пауза): %s; кадров со звуком после входа %d'
          % (', '.join('%s %d (со звуком на входе %d, худшее висение %d кадров)'
                       % (k, v[0], v[1], lng_hang.get(k, 0)) for k, v in sorted(lng_n.items())) or '-', lng_bad))
    for k in sorted(need):
        if lng_n.get(k, [0, 0])[1] == 0:
            bad += 1
            print('ГЕЙТ ВАКУУМЕН: событие %s со звучащим счётчиком на входе не встретилось' % k)
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
