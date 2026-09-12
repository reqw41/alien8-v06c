#!/bin/bash
# Гейт картинки Alien 8: сравнить текущую сборку vec с эталонной ревизией побайтно
# (буфер плоскости 1 + экран плоскости 0, снимок на каждой итерации).
#   tools/render_gate.sh [ревизия] [итераций] [комнаты через запятую]
# Сценарии: rest (покой), alive (журнал ходьбы) и по одному на каждую комнату из списка
# (покой в комнате, номер подменяется через A8ROOM — как в profile_vec.js). Разные комнаты
# дают разный набор объектов и разные пути рендера: правка, невидимая в стартовой комнате,
# краснеет в другой.
# Эталон разворачивается через git archive в build/ref; инструменты всегда берутся из
# текущего дерева (сравнивается только код игры).
set -e
cd "$(dirname "$0")/.."
REF=${1:-HEAD}
N=${2:-150}
ROOMS=${3:-104,39,56,88,48}
STAND=${A8_RESEARCH:-$HOME/projects/alien8-research}/zx-stand
IFS=, read -r -a ROOMA <<< "$ROOMS"
./build.sh vec >/dev/null 2>&1            # текущее дерево обязано быть пересобрано
rm -rf build/ref && mkdir -p build/ref
git archive "$REF" | tar -x -C build/ref
# ВАЖНО: из текущего дерева берутся ТОЛЬКО измерительные инструменты (стенд .js и мелкие
# отчёты). Транслятор и склейка (a8_z80_to_8080.py, a8_vec.py, a8_native_logic.py, …) — это
# КОД ПОРТА, и копировать их в эталон нельзя: гейт сравнивал бы сборку саму с собой.
cp tools/*.js build/ref/tools/ 2>/dev/null || true
for t in a8_size.py a8_regions.py pgm2png.py; do
  [ -f "tools/$t" ] && cp "tools/$t" build/ref/tools/ 2>/dev/null
done
true
( cd build/ref && ./build.sh vec >/dev/null 2>&1 )
fail=0
# сценарии: rest, alive, по одному на комнату
SCEN=(rest alive); for r in "${ROOMA[@]}"; do SCEN+=("r$r"); done
for sc in "${SCEN[@]}"; do
  IN=""; ROOM=""
  case "$sc" in
    rest)  ;;
    alive) IN="$STAND/inputs_alive.txt" ;;
    r*)    ROOM=${sc#r} ;;
  esac
  A8ROOM=$ROOM node tools/screendiff_vec.js build/alien8_vec.r0m build/alien8_vec.sld "$N" "$IN" "new_$sc" >/dev/null
  A8ROOM=$ROOM node tools/screendiff_vec.js build/ref/build/alien8_vec.r0m build/ref/build/alien8_vec.sld "$N" "$IN" "ref_$sc" >/dev/null
  # ИТЕРАЦИЯ 1 СУДИТСЯ ОТДЕЛЬНО (§13 рецепта KL): на ней на экране (плоскость 0) ещё стоит
  # МЕНЮ — комнату туда выкладывает update_screen уже внутри первой итерации, — а меню порт
  # законно меняет (шесть строк, полоса подсветки). Поэтому вердикт выносится по итерациям
  # 2..N, а у первой сравнивается только БУФЕР (плоскость 1): в нём к этому моменту уже
  # нарисована комната, и расхождение там — настоящая порча рендера, а не смена меню.
  # Расхождение экрана на первой итерации печатается отдельной строкой-замечанием.
  tail -n +2 "build/scr_new_$sc.txt" > "build/scr_new_$sc.tail"
  tail -n +2 "build/scr_ref_$sc.txt" > "build/scr_ref_$sc.tail"
  newbuf=$(head -1 "build/scr_new_$sc.txt" | cut -d' ' -f2); refbuf=$(head -1 "build/scr_ref_$sc.txt" | cut -d' ' -f2)
  newscr=$(head -1 "build/scr_new_$sc.txt" | cut -d' ' -f3); refscr=$(head -1 "build/scr_ref_$sc.txt" | cut -d' ' -f3)
  if cmp -s "build/scr_new_$sc.tail" "build/scr_ref_$sc.tail" && cmp -s "build/scr_new_$sc.bin" "build/scr_ref_$sc.bin" \
     && [ "$newbuf" = "$refbuf" ]; then
    echo "render_gate [$sc]: СОВПАДЕНИЕ, итерации 2..$N (и буфер итерации 1)"
    [ "$newscr" = "$refscr" ] || echo "render_gate [$sc]: ЗАМЕЧАНИЕ — экран итерации 1 отличается ($refscr -> $newscr): на нём ещё меню"
  else
    echo "render_gate [$sc]: РАСХОЖДЕНИЕ"
    [ "$newbuf" = "$refbuf" ] || echo "  итерация 1: разошёлся БУФЕР ($refbuf -> $newbuf) — это не меню"
    diff "build/scr_ref_$sc.tail" "build/scr_new_$sc.tail" | head -4
    fail=1
  fi
done
exit $fail
