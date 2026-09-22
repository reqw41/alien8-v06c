#!/usr/bin/env python3
"""Релизная заставка: картинка -> src/alien8_splash.bin (8192 Б, раскладка плоскости 0 Вектора).

    python3 tools/a8_splash.py [картинка]

Картинка (по умолчанию src/alien8_title.jpg) приводится к 256x192 1bpp:
LANCZOS-ресайз -> авторавнивание -> дизеринг Floyd-Steinberg (белый = 1, как
в vidbuf: бит выставлен = белый пиксель).Preview для приёмки глазами:
build/splash_preview.png (2x).

Раскладка плоскости 0 = раскладка vidbuf (tools/a8_vec.py: адрес = база +
столбец*256 + 32 + Y, Y растёт вверх, экран = буфер - 0x2000). Строка пикселей
y (0 = верх экрана) ложится в столбец x по адресу x*256 + (223 - y);
промежутки строк 0..31 и 224..255 обнулены.
"""
import os
import sys

from PIL import Image, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, "..")
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "src", "alien8_title.jpg")
OUT = os.path.join(REPO, "src", "alien8_splash.bin")
PREV = os.path.join(REPO, "build", "splash_preview.png")

img = Image.open(SRC).convert("L").resize((256, 192), Image.LANCZOS)
img = ImageOps.autocontrast(img)
bits = img.convert("1")  # Floyd-Steinberg, инверсия не нужна: белый = 1
os.makedirs(os.path.dirname(PREV), exist_ok=True)
bits.resize((512, 384), Image.NEAREST).save(PREV)

px = bits.load()
buf = bytearray(8192)
for y in range(192):
    for xb in range(32):
        b = 0
        for bit in range(8):
            b = (b << 1) | (1 if px[xb * 8 + bit, y] else 0)
        buf[xb * 256 + (223 - y)] = b
open(OUT, "wb").write(bytes(buf))
white = sum(bin(b).count("1") for b in buf)
print(f"{OUT}: 8192 байт, белых пикселей {white}/49152 ({white/49152*100:.1f} %), превью {PREV}")
