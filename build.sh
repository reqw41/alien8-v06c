#!/bin/bash
# Сборка Alien 8.
#   ./build.sh zx        — исходная ZX-версия из листинга tcdev + гейт «байт в байт с оригиналом»
#   ./build.sh lockstep  — рекомпиляция в i8080, логика 1:1, вывод заглушен (для локстепа)
set -e
cd "$(dirname "$0")"
TARGET=${1:-zx}
RESEARCH=${A8_RESEARCH:-$HOME/projects/alien8-research}
mkdir -p build

if [ "$TARGET" = "zx" ]; then
  # оригинальный снимок -> образ ОЗУ 48К (эталон)
  if [ ! -f build/alien8_orig_ram.bin ]; then
    python3 tools/unz80.py "$RESEARCH/zx-original/alien8_orig.z80" build/alien8_orig_ram.bin
  fi
  PYTHONPATH=tools python3 tools/a8_lst2asm.py \
      "$RESEARCH/zx-tcdev/alien8_v09a1.lst.txt" src/alien8_zx.asm build/alien8_zx.bin
  ./tools/sjasmplus --lst=build/alien8_zx.lst --sld=build/alien8_zx.sld --fullpath src/alien8_zx.asm
  python3 tools/a8_gate_zx.py build/alien8_zx.bin build/alien8_orig_ram.bin
elif [ "$TARGET" = "lockstep" ]; then
  python3 tools/a8_z80_to_8080.py src/alien8_zx.asm build/alien8_8080.asm --target lockstep
  ./tools/sjasmplus --lst=build/alien8_8080.lst --sld=build/alien8_8080.sld --fullpath build/alien8_8080.asm
  python3 tools/check_i8080.py build/alien8_8080.lst
  python3 tools/check_ixflags.py build/alien8_8080.asm
  ls -la build/alien8_8080.r0m
else
  echo "неизвестная цель: $TARGET"; exit 1
fi
