#!/usr/bin/env python3
"""Релизная заставка: картинка -> данные заставки.

    python3 tools/a8_splash.py [картинка]

Два выхода (картинка по умолчанию — src/alien8_title.jpg):

1. src/alien8_splash16.bin — ЗАСТАВКА ИТОГОВОГО РЕЛИЗА (сжатый образ, tools/a8_pack.py):
   16 цветов на весь экран, четыре плоскости Вектора + палитра, 4*8192 + 16 = 32784 Б.
   +0x0000 плоскость 0 (ляжет по 0x8000), +0x2000 плоскость 1 (0xA000), +0x4000 плоскость 2
   (0xC000), +0x6000 плоскость 3 (0xE000); +0x8000 — 16 байт палитры BBGGGRRR по АППАРАТНОМУ
   индексу: индекс = p0<<3 | p1<<2 | p2<<1 | p3 (p0 — бит плоскости 0x8000; так собирает
   индекс vector06js, tv.js shiftOutPixels, и так его понимает vec_isr игры).
   Квантование (решение владельца, превью приняты 2026-09-24): LANCZOS 256x192 -> черновая
   палитра MEDIANCUT на 16 цветов без дизеринга -> каждый цвет к сетке Вектора 3-3-2 (R,G —
   8 уровней, B — 4; коллизия -> ближайший ещё свободный узел сетки) -> Floyd-Steinberg РОВНО
   в эти 16 цветов. Индекс 0 отдан ЧЁРНОМУ: строки вне картинки (0..31/224..255 каждого
   столбца) во всех четырёх плоскостях нулевые, то есть рисуются индексом 0 — бордюр и поля
   экрана чёрные (бордюр — тоже индекс 0, порт 0x02). Нет чёрного в палитре — ошибка сборки.
   Превью для приёмки глазами: build/splash16_preview.png (2x) — собирается ОБРАТНО из
   плоскостей и палитры (проверка раскладки), а не из промежуточной картинки.

2. src/alien8_splash.bin — 1 bpp, 8192 Б, раскладка плоскости 0: заставка НЕСЖАТОГО
   релиза-эталона (build/alien8_release_ref.r0m, A8_SPLASH=1). Алгоритм прежний, байт в байт:
   LANCZOS -> авторавнивание -> Floyd-Steinberg (белый = 1). Превью build/splash_preview.png.

Раскладка плоскости = раскладка vidbuf (tools/a8_vec.py: адрес = база + столбец*256 + 32 + Y,
Y растёт вверх): строка пикселей y (0 = верх экрана) ложится в столбец x по адресу
x*256 + (223 - y); промежутки строк 0..31 и 224..255 нулевые.
"""
import os
import sys

from PIL import Image, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, "..")
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "src", "alien8_title.jpg")
OUT1 = os.path.join(REPO, "src", "alien8_splash.bin")
OUT16 = os.path.join(REPO, "src", "alien8_splash16.bin")
PREV1 = os.path.join(REPO, "build", "splash_preview.png")
PREV16 = os.path.join(REPO, "build", "splash16_preview.png")

# сетка цветов Вектора: байт палитры BBGGGRRR
R_LEVELS = [round(i * 255 / 7) for i in range(8)]
G_LEVELS = R_LEVELS
B_LEVELS = [round(i * 255 / 3) for i in range(4)]


def _nearest(v, levels):
    return min(levels, key=lambda l: abs(l - v))


def _snap(rgb):
    return tuple(_nearest(c, L) for c, L in zip(rgb, (R_LEVELS, G_LEVELS, B_LEVELS)))


def rgb_to_byte(rgb):
    r, g, b = rgb
    return (B_LEVELS.index(b) << 6) | (G_LEVELS.index(g) << 3) | R_LEVELS.index(r)


def byte_to_rgb(v):
    return (R_LEVELS[v & 7], G_LEVELS[(v >> 3) & 7], B_LEVELS[v >> 6])


def quantize16(img_rgb):
    """-> (картинка 'P' с индексами 0..15 в порядке PIL, список 16 RGB узлов сетки)."""
    rough = img_rgb.quantize(colors=16, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    pal = rough.getpalette()[:16 * 3]
    snapped, seen = [], set()
    for c in (tuple(pal[i:i + 3]) for i in range(0, len(pal), 3)):
        s = _snap(c)
        if s in seen:
            s = min(((r, g, b) for r in R_LEVELS for g in G_LEVELS for b in B_LEVELS
                     if (r, g, b) not in seen), key=lambda p: sum((a - b) ** 2 for a, b in zip(p, c)))
        seen.add(s)
        snapped.append(s)
    while len(snapped) < 16:
        s = next((r, g, b) for r in R_LEVELS for g in G_LEVELS for b in B_LEVELS if (r, g, b) not in seen)
        seen.add(s)
        snapped.append(s)
    pimg = Image.new("P", (1, 1))
    flat = [v for c in snapped for v in c] + [0, 0, 0] * (256 - 16)
    pimg.putpalette(flat)
    return img_rgb.quantize(palette=pimg, dither=Image.Dither.FLOYDSTEINBERG), snapped


def build16():
    img = Image.open(SRC).convert("RGB").resize((256, 192), Image.LANCZOS)
    q, colors = quantize16(img)
    black = (0, 0, 0)
    if black not in colors:
        raise SystemExit("a8_splash: в палитре заставки нет чёрного — бордюр и строки вне картинки "
                         "(индекс 0) вышли бы цветными")
    # перестановка: чёрный -> номер 0, остальные — в порядке PIL
    order = [colors.index(black)] + [i for i in range(16) if colors[i] != black]
    remap = {old: new for new, old in enumerate(order)}
    pal = bytes(rgb_to_byte(colors[old]) for old in order)
    px = q.load()
    planes = [bytearray(8192) for _ in range(4)]
    for y in range(192):
        for xb in range(32):
            bits = [0, 0, 0, 0]
            for bit in range(8):
                k = remap[px[xb * 8 + bit, y]]   # номер цвета = аппаратный индекс
                for p in range(4):
                    bits[p] = (bits[p] << 1) | ((k >> (3 - p)) & 1)
            for p in range(4):
                planes[p][xb * 256 + (223 - y)] = bits[p]
    data = b"".join(bytes(p) for p in planes) + pal
    # обратная сборка из плоскостей — превью и самопроверка раскладки
    out = Image.new("RGB", (256, 192))
    op = out.load()
    for y in range(192):
        for x in range(256):
            a = (x >> 3) * 256 + (223 - y)
            m = 0x80 >> (x & 7)
            k = sum(((planes[p][a] & m) != 0) << (3 - p) for p in range(4))
            op[x, y] = byte_to_rgb(pal[k])
            assert op[x, y] == colors[order[k]] and k == remap[px[x, y]]
    for p in range(4):          # строки вне картинки — нули (бордюр рисуется индексом 0 = чёрный)
        for col in range(32):
            assert not any(planes[p][col * 256 + r] for r in list(range(0, 32)) + list(range(224, 256)))
    return data, pal, out


def build1():
    img = Image.open(SRC).convert("L").resize((256, 192), Image.LANCZOS)
    img = ImageOps.autocontrast(img)
    bits = img.convert("1")  # Floyd-Steinberg, инверсия не нужна: белый = 1
    px = bits.load()
    buf = bytearray(8192)
    for y in range(192):
        for xb in range(32):
            b = 0
            for bit in range(8):
                b = (b << 1) | (1 if px[xb * 8 + bit, y] else 0)
            buf[xb * 256 + (223 - y)] = b
    return bytes(buf), bits


def main():
    os.makedirs(os.path.dirname(PREV1), exist_ok=True)
    data1, bits = build1()
    open(OUT1, "wb").write(data1)
    bits.resize((512, 384), Image.NEAREST).save(PREV1)
    white = sum(bin(b).count("1") for b in data1)
    print(f"{OUT1}: 8192 байт (эталон, 1 bpp), белых пикселей {white}/49152 "
          f"({white / 49152 * 100:.1f} %), превью {PREV1}")
    data16, pal, out = build16()
    open(OUT16, "wb").write(data16)
    out.resize((512, 384), Image.NEAREST).save(PREV16)
    print(f"{OUT16}: {len(data16)} байт (4 плоскости x 8192 + палитра 16), палитра по индексу "
          + ", ".join(f"0x{v:02X}" for v in pal) + f"; превью {PREV16}")


if __name__ == "__main__":
    main()
