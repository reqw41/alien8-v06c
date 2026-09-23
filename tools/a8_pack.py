#!/usr/bin/env python3
"""УПАКОВКА РЕЛИЗА: эталон (несжатый образ) -> итоговый образ с 16-цветной заставкой.

    python3 tools/a8_pack.py            (зовёт ./build.sh release после сборки эталона)
    A8_PACK_SHIFT=n A8_PACK_NOCHECK=1   ТОЛЬКО негативный контроль: поток L на n байт ниже
                                        запаса, модель in-place не останавливает сборку

Вход:  build/alien8_release_ref.r0m + .sld — НЕСЖАТЫЙ релиз-эталон (A8_SPLASH=1, 1 bpp заставка,
       как собирался до сих пор; md5 57804f48… на 657c617), src/alien8_splash16.bin (4 плоскости +
       палитра, tools/a8_splash.py), src/c64_tune.bin (мелодия C64, tools/a8_tune_c64.py),
       плеер msx_tv — ТЕКСТ из tools/a8_sound_ay.DRIVER (копия с префиксом spl_tv, см. ниже).
Выход: build/alien8_release.asm (собирает build.sh -> build/alien8_release.r0m, .lst, .sld),
       build/pack/T.bin (цель распаковки), build/pack/{L,H,P3}.zx0 (потоки), build/pack/layout.txt.

ИДЕЯ. На время заставки вся игра лежит СЖАТОЙ (zx0, «classic»-формат v1) в нижних 32 КБ, а все
четыре плоскости 0x8000..0xFFFF — картинка 16 цветов (строки вне картинки — нули: индекс 0 =
чёрный бордюр). Исполняется только самодостаточный код заставки (свой ISR, опрос клавиатуры,
палитра, КОПИЯ плеера мелодии). Клавиша -> счётчики ВИ53 глушатся, палитра гаснет (все 16
записей чёрные: дальнейшая возня в плоскостях не видна), di, ступень 2 (распаковщик + хвост)
копируется в 0xFE00 — в страницы 0xF1..0xFF, которые START целиком переписывает таблицами
build_lookup_tbls, — и распаковывает:
  плоскости 0..2 [0x8000, 0xE000) — стековой заливкой в нули (в эталоне там нули везде, кроме
             строк вне картинки плоскостей 1/2 — упаковщик это проверяет);
  поток H  -> SPL_STG (поверх уже ненужных кода и мелодии заставки): строки вне картинки
             плоскостей 1/2 (32 страницы x (0x00..0x1F + 0xE0..0xFF) x 2 = 4096 Б кода игры),
             затем раскладка по местам — нули распаковщиком не гоняются (замер: 44 кадра на
             сплошной поток плоскостей против 29 так);
  поток P3 -> [0xE000, 0xF100): плоскость 3 — хвост спрайтов 0xE000..0xF0F9 и нули;
  поток L  -> [0, E_L): нижний регион, переменные, добивка — НА МЕСТЕ (in-place, вперёд):
             поток лежит так, что кончается на delta байт выше конца приёмника (README zx0);
             отсутствие записи раньше чтения ДОКАЗЫВАЕТСЯ здесь же моделью распаковщика по
             точным адресам (dzx0_model с mem) и ещё раз стендом (tools/unpack_vec.js);
  [E_L, 0x8000) — нули (в эталоне там нули, а лежал хвост потока L).
Источники H/P3 лежат в нижних 32 КБ выше SPL_STG+4096, приёмники — плоскости: не пересекаются.
Дальше — то, что делал vec_boot эталона перед START (порты 8255, счётчик 0 = 0x30 + 0xFFFF,
1/2 молчат, vec_set_pal 7, ei, ожидание vec_palreq), SP = seed_1, jp START.

ЦЕЛЬ РАСПАКОВКИ T = образ эталона байт в байт, кроме:
  0x8000..0x9FFF (плоскость 0) = 0 — в эталоне там 1 bpp картинка его заставки, которую его же
                  код (a8_sp_key_down) стирает перед jp START: к START у эталона там нули;
  0xF100..0xFFFF  — не распаковывается: тут ступень 2 и её стек; START переписывает все 3840 Б
                  (build_lookup_tbls: страницы 0xFF..0xF2 и 0xF1) до первого чтения.
"""
import hashlib
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
import a8_sound_ay  # noqa: E402

REF = os.path.join(ROOT, "build", "alien8_release_ref.r0m")
REF_SLD = os.path.join(ROOT, "build", "alien8_release_ref.sld")
SPLASH16 = os.path.join(ROOT, "src", "alien8_splash16.bin")
TUNE = os.path.join(ROOT, "src", "c64_tune.bin")
ZX0 = os.environ.get("A8_ZX0", os.path.join(ROOT, "build", "zx0"))
PACKDIR = os.path.join(ROOT, "build", "pack")
OUT_ASM = os.path.join(ROOT, "build", "alien8_release.asm")

P3_DST, P3_END = 0xE000, 0xF100    # поток P3: плоскость 3 до таблиц (хвост спрайтов 0xE000..0xF0F9)
HOLE_PLANES = (0xA000, 0xC000)     # поток H: дыры вне картинки плоскостей 1 и 2 (код игры)
FILL_LO, FILL_HI = 0x8000, 0xE000  # плоскости 0..2 — нули, кроме дыр плоскостей 1/2
SPL_STG = 0x0040                   # сюда распаковывается H перед раскладкой по дырам (4096 Б)
X1_LO = 0xF100                     # 0xF100..0xFFFF: START переписывает целиком
STAGE2 = 0xFE00                    # ступень 2 (распаковщик + хвост); стек — ниже, от 0xFE00 вниз
STAGE2_SP = 0xFE00


def labels(sld):
    L = {}
    for line in open(sld, encoding="latin-1"):
        p = line.rstrip("\n").split("|")
        if len(p) >= 8 and p[6] == "L":
            n = p[7].split(",")[1]
            if n and n not in L:
                L[n] = int(p[5])
    return L


def zx0(data, tag):
    """zx0 -c (classic v1 — его понимает dzx0 Городецкого) с кэшем по md5 входа: сжатие 32 КБ
    идёт ~25 с, а gatecheck пересобирает релиз после каждой порчи."""
    os.makedirs(os.path.join(PACKDIR, "cache"), exist_ok=True)
    h = hashlib.md5(data).hexdigest()
    cz = os.path.join(PACKDIR, "cache", h + ".zx0")
    cd = os.path.join(PACKDIR, "cache", h + ".delta")
    if not (os.path.exists(cz) and os.path.exists(cd)):
        src = os.path.join(PACKDIR, "cache", h + ".bin")
        open(src, "wb").write(data)
        r = subprocess.run([ZX0, "-f", "-c", src, cz + ".tmp"], capture_output=True, text=True)
        if r.returncode:
            raise SystemExit("a8_pack: zx0 упал на потоке %s: %s" % (tag, r.stdout + r.stderr))
        m = re.search(r"delta (\d+)", r.stdout)
        if not m:
            raise SystemExit("a8_pack: zx0 не сообщил delta: " + r.stdout)
        os.replace(cz + ".tmp", cz)
        open(cd, "w").write(m.group(1))
        os.remove(src)
    return open(cz, "rb").read(), int(open(cd).read())


def dzx0_model(comp, src_at, dst_at, mem=None):
    """Модель распаковщика classic (порядок чтений — как у dzx0.c и у i8080-ветки Городецкого:
    байт битового буфера берётся только когда кончились биты, байт смещения — сразу за гаммой
    старшей части). Если mem задана, работает ПО АДРЕСАМ в ней (in-place): читает поток из mem,
    пишет результат в mem и проверяет, что ни одна запись не попала в ещё не прочитанный байт
    потока. -> (выход, число нарушений, первая запись-нарушитель)."""
    ip = [0]
    viol = [0, None]

    def rd():
        if mem is not None:
            b = mem[src_at + ip[0]]
        else:
            b = comp[ip[0]]
        ip[0] += 1
        return b
    st = {"mask": 0, "bt": False, "val": 0, "last": 0}   # val — байт битового буфера

    def bit():
        if st["bt"]:                    # «backtrack»: бит — младший бит байта смещения
            st["bt"] = False
            return st["last"] & 1
        st["mask"] >>= 1
        if st["mask"] == 0:
            st["mask"] = 128
            st["val"] = rd()
        return 1 if st["val"] & st["mask"] else 0

    def gamma():
        v = 1
        while not bit():
            v = (v << 1) | bit()
        return v
    out = bytearray()

    def put(v):
        a = dst_at + len(out)
        if mem is not None:
            if src_at + ip[0] <= a < src_at + len(comp):   # байт потока ещё не прочитан
                viol[0] += 1
                if viol[1] is None:
                    viol[1] = (a, src_at + ip[0])
            mem[a] = v
        out.append(v)
    last = 1
    state = "lit"
    while True:
        if state == "lit":
            for _ in range(gamma()):
                put(rd())
            state = "new" if bit() else "rep"
        elif state == "rep":
            for _ in range(gamma()):
                put(out[len(out) - last])
            state = "lit" if not bit() else "new"
        else:
            msb = gamma()
            if msb == 256:
                break
            b = rd()
            last = msb * 128 - (b >> 1)
            st["bt"], st["last"] = True, b
            n = gamma() + 1
            if last <= 0 or last > len(out):
                raise SystemExit("a8_pack: модель dzx0: плохое смещение %d" % last)
            for _ in range(n):
                put(out[len(out) - last])
            state = "new" if bit() else "lit"
    if ip[0] != len(comp):
        raise SystemExit("a8_pack: модель dzx0: прочитано %d из %d байт потока" % (ip[0], len(comp)))
    return bytes(out), viol[0], viol[1]


# ---------------------------------------------------------------------------------------------
# Распаковщик: DeZX/ZX0/8080/dzx0.asm, Ivan Gorodetsky (ivagor), v4 2021-02-23, ветка FORWARD,
# «Based on ZX0 z80 decoder by Einar Saukas» (ZX0 — BSD-3, tools/zx0/LICENSE). Исходник как
# есть — tools/dezx/dzx0_8080_ivagor_v4.asm. В репозитории eiroca/DeZX (зеркало ivagorRetrocomp/
# DeZX) ФАЙЛА ЛИЦЕНЗИИ НЕТ — авторство указано, условие BSD-3 ZX0 соблюдено ссылкой выше.
# Перевод 8080-мнемоник в синтаксис Z80 (sjasmplus, подмножество i8080 — tools/check_i8080.py)
# команда в команду: lxi d->ld de, xthl->ex (sp),hl, dad b->add hl,bc, pop psw->pop af, mov a,m->
# ld a,(hl), stax b->ld (bc),a, ral/rar->rla/rra, cnc->call nc, rc->ret c, rz->ret z.
# Вход: HL = начало потока, BC = начало приёмника. Портит всё. 98 Б, без правок (замер: цикл
# копии со счётом по E/D вместо dcx d на этих потоках МЕДЛЕННЕЕ — средняя длина копии 3.5 Б).
DZX0 = """\
dzx0:			ld		de, 0xFFFF
				push	de
				inc		de
				ld		a, 0x80
dzx0_lit:		call	dzx0_elias
				call	dzx0_ldir
				add		a, a
				jp		c, dzx0_new
				call	dzx0_elias
dzx0_copy:		ex		(sp), hl
				push	hl
				add		hl, bc
				call	dzx0_ldir
				pop		hl
				ex		(sp), hl
				add		a, a
				jp		nc, dzx0_lit
dzx0_new:		call	dzx0_elias
				ld		d, a
				pop		af
				xor		a
				sub		e
				ret		z
				ld		e, d
				ld		d, a
				ld		a, e
				push	bc
				ld		b, a
				ld		a, d
				rra
				ld		d, a
				ld		a, (hl)
				rra
				ld		e, a
				ld		a, b
				pop		bc
				inc		hl
				push	de
				ld		de, 1
				call	nc, dzx0_back
				inc		de
				jp		dzx0_copy
dzx0_elias:		inc		e
dzx0_eloop:		add		a, a
				jp		nz, dzx0_eskip
				ld		a, (hl)
				inc		hl
				rla
dzx0_eskip:		ret		c
dzx0_back:		ex		de, hl
				add		hl, hl
				ex		de, hl
				add		a, a
				jp		nc, dzx0_eloop
				inc		e
				jp		dzx0_eloop
dzx0_ldir:		push	af
dzx0_ldl:		ld		a, (hl)
				ld		(bc), a
				inc		hl
				inc		bc
				dec		de
				ld		a, d
				or		e
				jp		nz, dzx0_ldl
				pop		af
				ret
dzx0_end:
"""


def player_copy():
    """Копия интерпретатора msx_tv игры (a8_sound_ay.DRIVER) под именами spl_tv*: во время
    заставки код игры сжат, общий плеер недоступен. Тот же ТЕКСТ, а не пересказ: правка плеера
    игры попадает и сюда (гейт c64tune сверяет заставку с decode() по кадрам)."""
    d = a8_sound_ay.DRIVER
    a = d.index("; голос: HL = запись состояния, (msx_tv_c)")
    b = d.index("\nmsx_frame:")
    t = d[a:b]
    if "%" in t:
        raise SystemExit("a8_pack: в тексте плеера есть %% — DRIVER стал шаблоном, копию не снять")
    t = re.sub(r"\bmsx_tv", "spl_tv", t)
    ext = set(re.findall(r"\b(msx_\w+|a8_\w+|vec_\w+)", t))
    if ext:
        raise SystemExit("a8_pack: копия плеера ссылается на игру: " + ", ".join(sorted(ext)))
    return t


def keymasks(img, L):
    """Маски «любой клавиши» по рядам матрицы Вектора — ТА ЖЕ семантика, что a8_anykey эталона
    (read_key(0) по рядам ZX от vec_zxbuild + vec_joyraw): бит ряда r считается клавишей, если
    vec_kbzx[r*8+b] даёт хоть один бит ряда ZX (маска & 0x1F != 0x1F) или это стрелка ряда 0
    из vec_arrzx. Таблицы читаются из образа эталона."""
    kz = img[L["vec_kbzx"]:L["vec_kbzx"] + 64]
    m = [0] * 8
    for r in range(8):
        for b in range(8):
            if (kz[r * 8 + b] & 0x1F) != 0x1F:
                m[r] |= 1 << b
    az = L["vec_arrzx"]
    for i in range(4):
        m[0] |= img[az + 3 * i]
    return m


def main():
    img = open(REF, "rb").read()
    if len(img) != 0x10000 or img[0] != 0xF3 or img[1] != 0x31:
        raise SystemExit("a8_pack: %s — не образ с загрузчиком di / ld sp,imm" % REF)
    L = labels(REF_SLD)
    for n in ("START", "vec_isr", "vec_set_pal", "vec_palreq", "seed_1", "vec_kbzx", "vec_arrzx",
              "build_lookup_tbls"):
        if n not in L:
            raise SystemExit("a8_pack: в эталоне нет метки " + n)
    seed = img[2] | img[3] << 8
    if seed != L["seed_1"]:
        raise SystemExit("a8_pack: загрузчик эталона ставит SP=%04X, а seed_1=%04X" % (seed, L["seed_1"]))
    pic = open(SPLASH16, "rb").read()
    if len(pic) != 4 * 8192 + 16:
        raise SystemExit("a8_pack: src/alien8_splash16.bin — не 32784 Б (tools/a8_splash.py)")
    tune = open(TUNE, "rb").read()

    T = bytearray(img)
    T[0x8000:0xA000] = bytes(0x2000)   # эталон стирает плоскость 0 сам (a8_sp_key_down)
    nz = [a for a in range(0x8000) if T[a]]
    E_L = nz[-1] + 1
    os.makedirs(PACKDIR, exist_ok=True)
    open(os.path.join(PACKDIR, "T.bin"), "wb").write(T)
    # плоскости 0..2 — нули везде, кроме строк вне картинки плоскостей 1/2: их собираем подряд
    # (32 страницы x (0x00..0x1F + 0xE0..0xFF) на плоскость = 4096 Б), остальное — быстрая заливка
    H = bytearray()
    for base in HOLE_PLANES:
        for pg in range(32):
            a = base + pg * 256
            H += T[a:a + 0x20] + T[a + 0xE0:a + 0x100]
    for a in range(FILL_LO, FILL_HI):
        hole = a >= HOLE_PLANES[0] and ((a & 0xFF) < 0x20 or (a & 0xFF) >= 0xE0)
        if not hole and T[a]:
            raise SystemExit("a8_pack: в картинке плоскостей 0..2 эталона не ноль (%04X) — заливка "
                             "нулями разошлась бы с эталоном" % a)

    with ThreadPoolExecutor(3) as ex:
        fl = ex.submit(zx0, bytes(T[0:E_L]), "L")
        fh = ex.submit(zx0, bytes(H), "H")
        fp = ex.submit(zx0, bytes(T[P3_DST:P3_END]), "P3")
        (cl, dl), (ch, dh), (cp, dp) = fl.result(), fh.result(), fp.result()
    for n, c in (("L", cl), ("H", ch), ("P3", cp)):
        open(os.path.join(PACKDIR, n + ".zx0"), "wb").write(c)
    # поток L: конец потока на delta байт выше конца приёмника (README zx0, «in-place»)
    shift = int(os.environ.get("A8_PACK_SHIFT", "0"))   # ТОЛЬКО для негативного контроля
    SPL_L = E_L + dl - len(cl) - shift
    if SPL_L + len(cl) > 0x8000:
        raise SystemExit("a8_pack: поток L (%d Б) с запасом delta=%d не влезает под 0x8000 (E_L=%04X)"
                         % (len(cl), dl, E_L))
    # ---- доказательство: модель по адресам ----
    if dzx0_model(ch, 0, 0)[0] != bytes(H) or dzx0_model(cp, 0, 0)[0] != bytes(T[P3_DST:P3_END]):
        raise SystemExit("a8_pack: поток H или P3 не распаковывается в цель")
    mem = bytearray(0x10000)
    mem[SPL_L:SPL_L + len(cl)] = cl
    # модель ПО АДРЕСАМ: поток читается из той же памяти, куда пишется результат
    try:
        out, nviol, first = dzx0_model(cl, SPL_L, 0, mem)
        why = None if out == bytes(T[0:E_L]) else "результат на месте разошёлся с целью"
    except (SystemExit, IndexError) as e:     # затёртый поток декодируется в мусор
        out, nviol, first, why = None, -1, None, "затёртый поток не декодируется (%s)" % e
    if nviol:
        why = (why + "; " if why else "") + ("записей в непрочитанный поток %d, первая в %04X (читатель "
                                             "на %04X)" % (nviol, first[0], first[1]) if first else "")
    if why and not os.environ.get("A8_PACK_NOCHECK"):   # NOCHECK — только негативный контроль стенда
        raise SystemExit("a8_pack: IN-PLACE НАРУШЕН: " + why)
    km = keymasks(img, L)

    lay = dict(E_L=E_L, SPL_L=SPL_L, lenL=len(cl), dL=dl, lenH=len(ch), lenP3=len(cp), nviol=nviol)
    asm = gen_asm(L, lay, cl, ch, cp, tune, pic, km)
    open(OUT_ASM, "w", encoding="utf-8").write(asm)
    with open(os.path.join(PACKDIR, "layout.txt"), "w") as fh:
        for k, v in lay.items():
            fh.write("%s %d\n" % (k, v))
    print("a8_pack: L = T[0,%04X) %d -> %d Б (delta %d, поток %04X..%04X, in-place: записей в "
          "непрочитанное %d); H = дыры плоскостей 1/2 4096 -> %d Б; P3 = T[E000,F100) 4352 -> %d Б; "
          "итого потоков %d Б; маски клавиш %s"
          % (E_L, E_L, len(cl), dl, SPL_L, SPL_L + len(cl) - 1, nviol, len(ch), len(cp),
             len(cl) + len(ch) + len(cp), " ".join("%02X" % v for v in km)))


def _db(data, per=16):
    return "".join("\t\tDB\t" + ", ".join("0x%02X" % b for b in data[i:i + per]) + "\n"
                   for i in range(0, len(data), per))


def gen_asm(L, lay, cl, ch, cp, tune, pic, km):
    g = lambda n: "0x%04X" % L[n]  # noqa: E731
    pal = pic[4 * 8192:]
    s = []
    s.append("""\
; Alien 8 — ИТОГОВЫЙ РЕЛИЗ: 16-цветная заставка + игра, сжатая zx0 (tools/a8_pack.py — руками не
; править). Эталон (несжатый) — build/alien8_release_ref.r0m; цель распаковки — build/pack/T.bin.
        DEVICE ZXSPECTRUM48
; ---- символы игры (из build/alien8_release_ref.sld) ----
G_START			EQU		%(START)s
G_VEC_ISR		EQU		%(vec_isr)s
G_VEC_SET_PAL	EQU		%(vec_set_pal)s
G_VEC_PALREQ	EQU		%(vec_palreq)s
G_SEED_1		EQU		%(seed_1)s
; ---- раскладка ----
SPL_E_L			EQU		0x%(E_L)04X		; нижний приёмник [0, SPL_E_L), выше до 0x8000 — нули
SPL_P3_DST		EQU		0x%(P3)04X		; плоскость 3 [0xE000, 0xF100) — поток P3
SPL_STG			EQU		0x%(STG)04X		; H распаковывается сюда (4096 Б), потом — по дырам
SPL_STAGE2		EQU		0x%(STAGE2)04X	; ступень 2 во время распаковки (страницы build_lookup_tbls)

				ORG		0x0000
				di
				ld		sp, spl_stack_top
				jp		spl_main
				ORG		0x0038
				jp		spl_isr			; RST 38h на время заставки; T несёт тут jp vec_isr
				ORG		0x0040
""" % dict(START=g("START"), vec_isr=g("vec_isr"), vec_set_pal=g("vec_set_pal"),
           vec_palreq=g("vec_palreq"), seed_1=g("seed_1"), E_L=lay["E_L"], P3=P3_DST,
           STG=SPL_STG, STAGE2=STAGE2))
    s.append("""\
; ---- ISR заставки: палитра (все 16 записей каждый кадр, луч в обратном ходе), клавиатура
; (ряды 0..7 матрицы, маски «любой клавиши» как у a8_anykey эталона) и джойстик (порт 0x0E,
; как vec_joy: биты 4/5 после cpl != 0 — порта нет, считать «ничего»), флаг кадра для тика
; плеера. Счётчик 0 не трогает: на заставке он голос A. Порты 8255 — как vec_scan: порт B на
; ввод (0x8A) на время опроса, потом 0x88, скролл 0xFF и бордюр 0 вернуть до защёлки скролла.
spl_isr:		push	af
				push	bc
				push	de
				push	hl
				ld		hl, spl_pal + 15
				ld		e, 15
spl_ipal:		ld		a, e
				out		(0x02), a			; индекс = цвет бордюра (луч в обратном ходе)
				ld		a, (hl)
				dec		hl
				out		(0x0C), a
				out		(0x0C), a
				out		(0x0C), a
				out		(0x0C), a
				dec		e
				jp		p, spl_ipal
				xor		a
				out		(0x02), a			; бордюр — индекс 0 (чёрный)
				ld		a, 0x8A
				out		(0x00), a			; порт B на ввод
				ld		hl, spl_kmask
				ld		c, 0
				ld		e, 0xFE				; ряд 0
spl_irow:		ld		a, e
				out		(0x03), a
				in		a, (0x02)
				cpl							; 1 = нажата
				and		(hl)
				or		c
				ld		c, a
				inc		hl
				ld		a, e
				rlca
				ld		e, a
				jp		c, spl_irow			; 8 рядов: 0xFE..0x7F, после 0x7F перенос 0
				ld		a, 0x88
				out		(0x00), a
				ld		a, 0xFF
				out		(0x03), a			; вернуть скролл
				xor		a
				out		(0x02), a
				in		a, (0x0E)			; джойстик
				cpl
				ld		b, a
				and		0x30
				jp		z, spl_ijoy
				ld		b, 0				; порта нет — «отпущено всё» (как vj_chg)
spl_ijoy:		ld		a, b
				or		c
				ld		(spl_key), a		; != 0 — нажата «любая клавиша»
				ld		a, 0xFF
				ld		(spl_flag), a
				pop		hl
				pop		de
				pop		bc
				pop		af
				ei
				ret

; ---- главный цикл заставки ----
spl_main:		ld		a, 0x88				; 8255 как vec_boot: A и B на вывод
				out		(0x00), a
				xor		a
				out		(0x02), a			; бордюр 0, режим 256
				ld		a, 0xFF
				out		(0x03), a			; скролл
				call	spl_tune_init		; счётчики 0/1/2 молчат, голоса на начало, флаг 0
				ei
spl_loop:		ld		a, (spl_key)
				or		a
				jp		nz, spl_exit
				ld		a, (spl_flag)		; тик мелодии — ровно один за кадр
				or		a
				jp		z, spl_loop
				xor		a
				ld		(spl_flag), a
				call	spl_tune_tick
				jp		spl_loop

; ---- клавиша: заглушить, погасить, отдать память распаковке ----
spl_exit:		ld		a, 0x36				; все три счётчика: управляющее слово без делителя = стоп
				out		(0x08), a			; (голос A — счётчик 0, B/C — 1/2)
				ld		a, 0x76
				out		(0x08), a
				ld		a, 0xB6
				out		(0x08), a
				ld		hl, spl_pal			; палитра заставки -> все 16 записей чёрные
				ld		b, 16
spl_xblk:		ld		(hl), 0
				inc		hl
				dec		b
				jp		nz, spl_xblk
				xor		a
				ld		(spl_flag), a
spl_xwait:		ld		a, (spl_flag)		; ISR, выставивший флаг, уже загрузил чёрную палитру
				or		a
				jp		z, spl_xwait
				di							; до конца распаковки прерываний нет: 0x0038 и сам
											; обработчик затрёт поток L
				ld		hl, spl_s2_src		; ступень 2 -> 0xFE00 (там уже не видная картинка)
				ld		de, SPL_STAGE2
				ld		bc, spl_s2_end - spl_s2_start
spl_xcp:		ld		a, (hl)
				ld		(de), a
				inc		hl
				inc		de
				dec		bc
				ld		a, b
				or		c
				jp		nz, spl_xcp
				jp		spl_s2_start

; ---- мелодия C64: инициализация и тик (как a8_tune_init/a8_tune_tick эталона) ----
spl_tune_init:	ld		hl, spl_tune
				ld		(spl_tv_base), hl
				ld		hl, (spl_tune + 6)	; число правил nr -> divs = база + 10 + 2nr
				add		hl, hl
				ld		bc, spl_tune + 10
				add		hl, bc
				ld		(spl_tv_divs), hl
				ld		hl, spl_tv_stub		; заглушка out (порт),a / ret (у i8080 нет out (c))
				ld		(hl), 0xD3
				inc		hl
				inc		hl
				ld		(hl), 0xC9
				ld		a, 0x36				; заглушить счётчики 0/1/2
				out		(0x08), a
				ld		a, 0x76
				out		(0x08), a
				ld		a, 0xB6
				out		(0x08), a
				xor		a
				ld		(spl_flag), a
				ld		hl, spl_tune		; голосам: pc = start = база + указатель
				ld		de, spl_st
				ld		b, 3
spl_tiv:		ld		a, (hl)
				ld		(de), a				; pc lo
				ld		(spl_tv_len), a
				inc		hl
				ld		a, (hl)
				add		a, high spl_tune	; младший байт базы 0 — переноса нет
				inc		de
				ld		(de), a				; pc hi
				ld		a, (spl_tv_len)
				inc		de
				ld		(de), a				; start lo
				ld		a, (hl)
				add		a, high spl_tune
				inc		de
				ld		(de), a				; start hi
				xor		a
				inc		de
				ld		(de), a				; res
				inc		de
				ld		(de), a				; snd
				inc		de
				ld		(de), a				; depth
				ld		a, e
				add		a, 35				; следующая запись (шаг 41)
				ld		e, a
				inc		hl
				dec		b
				jp		nz, spl_tiv
				ret
spl_tune_tick:	ld		hl, spl_st
				xor		a
spl_ttv:		ld		(spl_tv_c), a		; голос A/B/C -> счётчик 0/1/2
				push	hl
				call	spl_tv
				pop		hl
				ld		a, l
				add		a, 41
				ld		l, a
				ld		a, (spl_tv_c)
				inc		a
				cp		3
				jp		c, spl_ttv
				ret

; ---- копия интерпретатора мелодий msx_tv игры (tools/a8_sound_ay.py, префикс spl_tv) ----
""")
    s.append(player_copy())
    s.append("""
; ---- ступень 2: распаковщик и хвост; лежит здесь, исполняется с 0xFE00. Порядок: плоскости
; 0..2 -> нули; H -> SPL_STG и по дырам плоскостей 1/2; P3 -> плоскость 3; L -> [0, E_L) на месте.
spl_s2_src:
				DISP	SPL_STAGE2
spl_s2_start:	ld		sp, 0x%(SP)04X			; стек ступени 2 — тоже в страницах таблиц
				ld		de, 0				; плоскости 0..2 [0x8000, 0xE000) — нули: стековая
				ld		hl, 0xE000			; заливка, 2 Б за push (под di, стек — ниже в SP)
				ld		sp, hl
				ld		bc, 0x0300			; 3 * 256 проходов по 16 push = 0x6000 Б
spl_s2_f:		push	de
				push	de
				push	de
				push	de
				push	de
				push	de
				push	de
				push	de
				push	de
				push	de
				push	de
				push	de
				push	de
				push	de
				push	de
				push	de
				dec		c
				jp		nz, spl_s2_f
				dec		b
				jp		nz, spl_s2_f
				ld		sp, 0x%(SP)04X
				ld		hl, spl_H			; H -> SPL_STG: дыры плоскостей 1/2 подряд (код заставки
				ld		bc, SPL_STG			;   и мелодия там больше не нужны)
				call	dzx0
				ld		hl, SPL_STG			; раскладка: плоскость 1, потом 2; в странице 32 Б
				ld		d, 0xA0				;   строк 0x00..0x1F и 32 Б строк 0xE0..0xFF
spl_s2_hp:		ld		e, 0
				call	spl_s2_h32
				ld		e, 0xE0
				call	spl_s2_h32
				inc		d
				ld		a, d
				cp		0xE0
				jp		nz, spl_s2_hp
				ld		hl, spl_P3			; P3 -> [0xE000, 0xF100): хвост спрайтов и нули
				ld		bc, SPL_P3_DST
				call	dzx0
spl_s2_u:		ld		hl, spl_L			; L -> [0, SPL_E_L) на месте, вперёд
				ld		bc, 0
				call	dzx0
spl_s2_l:		ld		hl, SPL_E_L			; [SPL_E_L, 0x8000): нули, как в эталоне
spl_s2_z:		ld		a, h
				cp		0x80
				jp		z, spl_unpacked
				ld		(hl), 0
				inc		hl
				jp		spl_s2_z
spl_unpacked:	; ТОЧКА ГЕЙТА: память [0, 0xF100) == цель T (tools/unpack_vec.js)
				ld		a, 0x88				; как vec_boot эталона: 8255, бордюр/режим, скролл
				out		(0x00), a
				xor		a
				out		(0x02), a
				ld		a, 0xFF
				out		(0x03), a
				ld		a, 0x30				; счётчик 0: режим 0, оба байта — секундомер (vec_boot)
				out		(0x08), a
				ld		a, 0xFF				; 0xFFFF, как a8_tune_off эталона и vec_isr каждый кадр
				out		(0x0B), a
				out		(0x0B), a
				ld		a, 0x76				; счётчики 1 и 2 молчат (a8_tune_off)
				out		(0x08), a
				ld		a, 0xB6
				out		(0x08), a
				ld		a, 7
				call	G_VEC_SET_PAL		; белая палитра меню, как vec_boot
				ei							; 0x0038 = jp vec_isr (из T): палитру грузит ISR игры
spl_s2_pw:		ld		a, (G_VEC_PALREQ)
				or		a
				jp		nz, spl_s2_pw
				di
				ld		sp, G_SEED_1		; как загрузчик эталона
				ei
				jp		G_START
spl_s2_h32:		ld		c, 32				; 32 Б (HL) -> (DE), E растёт внутри страницы
spl_s2_hc:		ld		a, (hl)
				ld		(de), a
				inc		hl
				inc		e
				dec		c
				jp		nz, spl_s2_hc
				ret
""" % dict(SP=STAGE2_SP))
    s.append(DZX0)
    s.append("""\
spl_s2_end:
        ASSERT $ <= 0x10000   ; заставка: ступень 2 (исполняется с 0xFE00) до конца памяти
				ENT
        ASSERT spl_s2_end <= 0x10000   ; ступень 2 в страницах таблиц build_lookup_tbls
        ASSERT SPL_STAGE2 - 0x40 >= 0x%(X1)04X   ; стек ступени 2 (до 64 Б: vec_isr + vec_set_pal) — тоже там

; ---- данные заставки ----
spl_kmask:		DB		%(km)s	; ряды 0..7: биты «любой клавиши»
spl_pal:		DB		%(pal)s	; палитра заставки по индексу
spl_key:		DB		0
spl_flag:		DB		0
spl_tv_stub:	DS		3
spl_tv_c:		DS		1
spl_tv_len:		DS		1
spl_tv_div:		DS		2
spl_tv_stp:		DS		2
spl_tv_base:	DS		2
spl_tv_divs:	DS		2
				ALIGN	256
spl_st:			DS		41*3			; состояние трёх голосов (шаг 41: стек возвратов 16)
        ASSERT high spl_st == high (spl_st + 41*3 - 1)   ; msx_tv считает поля по младшему байту
				ALIGN	256
spl_tune:
""" % dict(X1=X1_LO, km=", ".join("0x%02X" % v for v in km), pal=", ".join("0x%02X" % v for v in pal)))
    s.append(_db(tune))
    s.append("        ASSERT $ >= SPL_STG + 4096   ; H распаковывается поверх кода и мелодии, не потоков\n")
    s.append("spl_H:\n")
    s.append(_db(ch))
    s.append("spl_P3:\n")
    s.append(_db(cp))
    s.append("spl_streams_end:\n")
    s.append("spl_stack:\t\tDS\t\t128\t\t\t; стек заставки (ISR 8 Б + плеер)\nspl_stack_top:\n")
    s.append("        ASSERT $ <= 0x%04X   ; заставка: код, мелодия, потоки H/P3, стек — под потоком L\n" % lay["SPL_L"])
    s.append("\t\t\t\tORG\t\t0x%04X\t\t; поток L: конец на delta=%d выше конца приёмника 0x%04X\n"
             % (lay["SPL_L"], lay["dL"], lay["E_L"]))
    s.append("spl_L:\n")
    s.append(_db(cl))
    s.append("spl_L_end:\n")
    s.append("        ASSERT $ <= 0x8000   ; заставка: поток L под плоскостью 0 (in-place, запас delta)\n")
    s.append("        ASSERT spl_L_end >= SPL_E_L + %d   ; запас delta zx0 для распаковки на месте\n"
             % lay["dL"])
    for p in range(4):
        s.append("\t\t\t\tORG\t\t0x%04X\t\t; картинка, плоскость %d (строки вне картинки — нули)\n"
                 % (0x8000 + p * 0x2000, p))
        s.append("spl_plane%d:\n" % p)
        s.append(_db(pic[p * 8192:(p + 1) * 8192], 32))
    s.append('        SAVEBIN "build/alien8_release.r0m", 0, 0x10000\n')
    return "".join(s)


if __name__ == "__main__":
    main()
