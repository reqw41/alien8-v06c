#!/bin/bash
# Сборка Alien 8.
#   ./build.sh zx        — исходная ZX-версия из листинга tcdev + гейт «байт в байт с оригиналом»
#   ./build.sh lockstep  — рекомпиляция в i8080, логика 1:1, вывод заглушен (для локстепа)
#   ./build.sh release   — эталон (цель vec + 1 bpp заставка, несжатый) и итоговый релиз
#                          (16-цветная заставка, игра сжата zx0); гейты не здесь
#   ./build.sh roms      — готовые образы в rom/: alien8.r0m (итоговый релиз) и
#                          alien8-nosplash.r0m (цель vec, без заставки). Отдельной целью:
#                          gatecheck.py пересобирает vec/release с порчами и не должен
#                          трогать то, что лежит в git
set -e
cd "$(dirname "$0")"
TARGET=${1:-zx}
RESEARCH=${A8_RESEARCH:-$HOME/projects/alien8-research}
# Ассемблер: по умолчанию вложенный tools/sjasmplus (сборка под macOS arm64), иначе свой — SJASMPLUS=...
SJ=${SJASMPLUS:-./tools/sjasmplus}
mkdir -p build

if [ "$TARGET" = "zx" ]; then
  # оригинальный снимок -> образ ОЗУ 48К (эталон)
  if [ ! -f build/alien8_orig_ram.bin ]; then
    python3 tools/unz80.py "$RESEARCH/zx-original/alien8_orig.z80" build/alien8_orig_ram.bin
  fi
  PYTHONPATH=tools python3 tools/a8_lst2asm.py \
      "$RESEARCH/zx-tcdev/alien8_v09a1.lst.txt" src/alien8_zx.asm build/alien8_zx.bin
  "$SJ" --lst=build/alien8_zx.lst --sld=build/alien8_zx.sld --fullpath src/alien8_zx.asm
  python3 tools/a8_gate_zx.py build/alien8_zx.bin build/alien8_orig_ram.bin
elif [ "$TARGET" = "lockstep" ]; then
  python3 tools/a8_z80_to_8080.py src/alien8_zx.asm build/alien8_8080.asm --target lockstep
  "$SJ" --lst=build/alien8_8080.lst --sld=build/alien8_8080.sld --fullpath build/alien8_8080.asm
  python3 tools/check_i8080.py build/alien8_8080.lst
  python3 tools/check_ixflags.py build/alien8_8080.asm
  python3 tools/check_djnz.py build/alien8_8080.asm
  ls -la build/alien8_8080.r0m
elif [ "$TARGET" = "vec" ]; then
  # Вектор-06Ц: ч/б, одна плоскость, нативный столбцовый буфер (этап 4)
  PYTHONPATH=tools python3 tools/a8_z80_to_8080.py src/alien8_zx.asm build/alien8_vec.asm --target vec
  "$SJ" --lst=build/alien8_vec.lst --sld=build/alien8_vec.sld --fullpath build/alien8_vec.asm
  python3 tools/check_i8080.py build/alien8_vec.lst
  python3 tools/check_ixflags.py build/alien8_vec.asm
  python3 tools/check_djnz.py build/alien8_vec.asm
  python3 tools/check_plane1.py build/alien8_vec.lst --walk build/alien8_vec.asm
  python3 tools/check_plane2.py build/alien8_vec.lst --walk build/alien8_vec.asm
  ls -la build/alien8_vec.r0m
elif [ "$TARGET" = "release" ]; then
  # Релиз = ДВА образа.
  # 1) ЭТАЛОН build/alien8_release_ref.r0m — несжатый, как собирался всегда (A8_SPLASH=1:
  #    1 bpp заставка из src/alien8_splash.bin, мелодия C64). По нему судят гейты раскладки игры
  #    (check_plane1/2, a8_regions) и его память сверяет гейт распаковки.
  # 2) ИТОГОВЫЙ build/alien8_release.r0m — заливается на MiSTer: 16-цветная заставка на весь
  #    экран, игра на время заставки сжата zx0 и распаковывается по клавише (tools/a8_pack.py).
  [ -f src/alien8_splash.bin ] && [ -f src/alien8_splash16.bin ] || python3 tools/a8_splash.py
  A8_SPLASH=1 A8_BIN=build/alien8_release_ref.r0m \
    python3 tools/a8_z80_to_8080.py src/alien8_zx.asm build/alien8_release_ref.asm --target vec
  "$SJ" --lst=build/alien8_release_ref.lst --sld=build/alien8_release_ref.sld --fullpath build/alien8_release_ref.asm
  python3 tools/check_i8080.py build/alien8_release_ref.lst
  python3 tools/check_ixflags.py build/alien8_release_ref.asm
  python3 tools/check_djnz.py build/alien8_release_ref.asm
  python3 tools/check_plane1.py build/alien8_release_ref.lst --walk build/alien8_release_ref.asm
  python3 tools/check_plane2.py build/alien8_release_ref.lst --walk build/alien8_release_ref.asm
  # компрессор zx0 (Einar Saukas, BSD-3, tools/zx0/LICENSE) — собирается из исходников
  if [ ! -x build/zx0 ] || [ -n "$(find tools/zx0 -newer build/zx0 -name '*.[ch]')" ]; then
    ${CC:-cc} -O2 -o build/zx0 tools/zx0/zx0.c tools/zx0/compress.c tools/zx0/memory.c tools/zx0/optimize.c
  fi
  python3 tools/a8_pack.py
  "$SJ" --lst=build/alien8_release.lst --sld=build/alien8_release.sld --fullpath build/alien8_release.asm
  python3 tools/check_i8080.py build/alien8_release.lst
  ls -la build/alien8_release_ref.r0m build/alien8_release.r0m
elif [ "$TARGET" = "roms" ]; then
  ./build.sh vec
  ./build.sh release
  mkdir -p rom
  cp build/alien8_release.r0m rom/alien8.r0m
  cp build/alien8_vec.r0m rom/alien8-nosplash.r0m
  ls -la rom
else
  echo "неизвестная цель: $TARGET"; exit 1
fi
