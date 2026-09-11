#!/bin/bash
# Гейт картинки Alien 8: сравнить текущую сборку vec с эталонной ревизией побайтно
# (буфер плоскости 1 + экран плоскости 0, снимок на каждой итерации).
#   tools/render_gate.sh [ревизия] [итераций]
# Эталон разворачивается через git archive в build/ref; инструменты всегда берутся из
# текущего дерева (сравнивается только код игры).
set -e
cd "$(dirname "$0")/.."
REF=${1:-HEAD}
N=${2:-150}
STAND=${A8_RESEARCH:-$HOME/projects/alien8-research}/zx-stand
rm -rf build/ref && mkdir -p build/ref
git archive "$REF" | tar -x -C build/ref
cp tools/*.js tools/*.py build/ref/tools/ 2>/dev/null || true
( cd build/ref && ./build.sh vec >/dev/null 2>&1 )
fail=0
for sc in rest alive; do
  if [ "$sc" = rest ]; then IN=""; else IN="$STAND/inputs_alive.txt"; fi
  node tools/screendiff_vec.js build/alien8_vec.r0m build/alien8_vec.sld "$N" "$IN" "new_$sc" >/dev/null
  node tools/screendiff_vec.js build/ref/build/alien8_vec.r0m build/ref/build/alien8_vec.sld "$N" "$IN" "ref_$sc" >/dev/null
  if cmp -s "build/scr_new_$sc.txt" "build/scr_ref_$sc.txt" && cmp -s "build/scr_new_$sc.bin" "build/scr_ref_$sc.bin"; then
    echo "render_gate [$sc]: СОВПАДЕНИЕ, $N итераций"
  else
    echo "render_gate [$sc]: РАСХОЖДЕНИЕ"
    diff "build/scr_ref_$sc.txt" "build/scr_new_$sc.txt" | head -4
    fail=1
  fi
done
exit $fail
