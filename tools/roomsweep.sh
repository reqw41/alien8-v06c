#!/bin/bash
# ОБХОД ВСЕХ КОМНАТ ИГРЫ ПРОТИВ ОРИГИНАЛА ZX.
#
# Покрытие гейтов держалось на ВЫБОРЕ КОМНАТ, а не сценариев: два дефекта рекомпиляции
# (робомышь, журнал 2026-09-15) прожили до владельца только потому, что ни в одной из семи
# гейтовых комнат робомыши не было. Этот скрипт снимает вопрос целиком: для КАЖДОЙ комнаты
# из location_tbl (их 128, номера 2..248 вразбивку — см. tools/a8_rooms.py) снимается
# журнал ZX и прогоняется гейт пикселей порта.
#
#   сторона ZX   — zx-stand/zx_screen.lua под MAME: ZXSCR_ROOM=<номер>, дамп экрана
#                  (6912 Б/итерацию) и те же 1928 Б состояния рядом (<OUT>.st.bin);
#   сторона Вектора — tools/zxpix_vec.js: A8ROOM=<тот же номер>, сверяет И состояние
#                  (1928 Б, иначе сценарии разные и пиксели сравнивать бессмысленно),
#                  И пиксели плоскости 0 против дампа ZX.
#
# Один прогон комнаты ~4 с (ZX 2.8 с + Вектор 1.1 с), 128 комнат на 4 ядрах ~2.5 мин.
#
#   tools/roomsweep.sh                          # покой, 300 итераций, 4 потока
#   tools/roomsweep.sh inputs_alive.txt 300 6   # другой сценарий / итерации / потоки
#   tools/roomsweep.sh inputs_idle.txt 300 4 "39 48 137"   # только эти комнаты
#
# Итог — таблица «комната | грузится | состояние | пиксели | первое расхождение» на stdout
# и в build/roomsweep/<метка>/TABLE.txt; журналы каждой комнаты там же (дампы экрана
# удаляются сразу после сверки — иначе 128 × 2 ГБ). Код возврата 1, если покраснела
# хоть одна комната или хоть одна не прогналась.
set -u
cd "$(dirname "$0")/.."
ROOT=$(pwd)
STAND=${A8_RESEARCH:-$HOME/projects/alien8-research}/zx-stand
MAME=${MAME:-/opt/homebrew/bin/mame}

INPUTS=${1:-inputs_idle.txt}
ITERS=${2:-300}
JOBS=${3:-4}
ROOMLIST=${4:-}

TAG="${INPUTS%.txt}_$ITERS"
WORK=$ROOT/build/roomsweep/$TAG
rm -rf "$WORK"; mkdir -p "$WORK/res"

[ -f build/alien8_vec.r0m ] || { echo "нет build/alien8_vec.r0m — сначала ./build.sh vec"; exit 2; }
[ -f "$STAND/$INPUTS" ]     || { echo "нет $STAND/$INPUTS"; exit 2; }
[ -x "$MAME" ]              || { echo "нет mame ($MAME) — задайте MAME=<путь>"; exit 2; }

if [ -n "$ROOMLIST" ]; then
  printf '%s\n' $ROOMLIST > "$WORK/rooms.txt"
else
  python3 tools/a8_rooms.py > "$WORK/rooms.txt" || exit 2
fi
NROOMS=$(wc -l < "$WORK/rooms.txt" | tr -d ' ')
echo "ОБХОД КОМНАТ: $NROOMS комнат, сценарий $INPUTS, $ITERS итераций, $JOBS потоков -> $WORK"

# ---- один прогон: комната целиком, обе стороны ----
cat > "$WORK/one.sh" <<'ONE'
#!/bin/bash
set -u
R=$1
cd "$ROOT"
Z=$WORK/zx_r$R
# сторона ZX. Запускать ОБЯЗАТЕЛЬНО из каталога стенда: zx_screen.lua ищет там и файл
# сценария, и снимок. -seconds_to_run — только страховка: lua сам зовёт m:exit() на NITER-й.
( cd "$STAND" && ZXSCR_ROOM=$R ZXSCR_ITERS=$ITERS ZXSCR_INPUTS=$INPUTS ZXSCR_OUT=$Z \
  SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy "$MAME" spectrum \
  -rompath . -dump alien8_orig_det.z80 -video none -sound none -nothrottle \
  -seconds_to_run 180 -snapshot_directory "$WORK/snaps" -script zx_screen.lua ) \
  > "$Z.mame.log" 2>&1
NIT=$(sed -n 's/^итераций=\([0-9]*\) .*/\1/p' "$Z.log" 2>/dev/null)
ATTR=$(sed -n 's/.*(attr \([0-9a-f]*\)).*/\1/p' "$Z.log" 2>/dev/null | head -1)
if [ "${NIT:-0}" != "$ITERS" ]; then
  echo "$R|НЕТ|—|—|ZX-сторона не сняла журнал (итераций ${NIT:-0} из $ITERS)" > "$WORK/res/$R.txt"
  rm -f "$Z.bin" "$Z.st.bin"; exit 0
fi
# сторона Вектора: состояние + пиксели против того же прогона
A8ROOM=$R A8_IRQDROP=1 node tools/zxpix_vec.js build/alien8_vec.r0m build/alien8_vec.sld \
  "$ITERS" "$STAND/$INPUTS" "$Z.bin" > "$Z.vec.log" 2>&1
RC=$?
rm -f "$Z.bin" "$Z.st.bin"          # 2 ГБ на комнату — держать нельзя
ST=$(sed -n 's/^состояние: расхождений итераций \(.*\)$/\1/p' "$Z.vec.log")
CMP=$(sed -n 's/^сценарий .*сравнено \([0-9]*\) (из.*/\1/p' "$Z.vec.log")
LAST=$(tail -1 "$Z.vec.log")
FIRST="—"
case "$ST" in
  0) STC="$CMP/$CMP" ;;
  *) STC="РАЗОШЛОСЬ ($ST)"; FIRST=$(sed -n 's/.*первое на \([0-9]*\).*/итерация \1 (состояние)/p' <<< "$ST") ;;
esac
case "$LAST" in
  ЗЕЛЁНЫЙ*) PIX="$CMP/$CMP" ;;
  *)        PIX="КРАСНЫЙ"
            F2=$(sed -n 's/^ПЕРВОЕ РАСХОЖДЕНИЕ ПИКСЕЛЕЙ: итерация \([0-9]*\).*/итерация \1 (пиксели)/p' "$Z.vec.log" | head -1)
            [ "$FIRST" = "—" ] && FIRST=${F2:-"см. $Z.vec.log"} ;;
esac
[ $RC -eq 0 ] && PIX="$CMP/$CMP"
echo "$R|да (attr $ATTR)|$STC|$PIX|$FIRST" > "$WORK/res/$R.txt"
ONE
chmod +x "$WORK/one.sh"
export ROOT WORK STAND MAME INPUTS ITERS

t0=$(date +%s)
xargs -P "$JOBS" -n 1 "$WORK/one.sh" < "$WORK/rooms.txt"
t1=$(date +%s)

# ---- таблица ----
{
  echo "| комната | грузится | состояние $ITERS итер. | пиксели | первое расхождение |"
  echo "|---|---|---|---|---|"
  while read -r R; do
    if [ -f "$WORK/res/$R.txt" ]; then
      IFS='|' read -r a b c d e < "$WORK/res/$R.txt"
      printf '| %s | %s | %s | %s | %s |\n' "$a" "$b" "$c" "$d" "$e"
    else
      printf '| %s | ПРОГОН НЕ СОСТОЯЛСЯ | — | — | — |\n' "$R"
    fi
  done < "$WORK/rooms.txt"
} > "$WORK/TABLE.txt"

GREEN=$(grep -c 'КРАСНЫЙ\|РАЗОШЛОСЬ\|НЕТ\|НЕ СОСТОЯЛСЯ' "$WORK/TABLE.txt")
BAD=$GREEN
OK=$(( NROOMS - BAD ))
cat "$WORK/TABLE.txt"
echo
echo "ИТОГ: комнат $NROOMS, зелёных (состояние И пиксели) $OK, красных $BAD, $((t1-t0)) с"
[ "$BAD" -eq 0 ] || grep -n 'КРАСНЫЙ\|РАЗОШЛОСЬ\|НЕТ\|НЕ СОСТОЯЛСЯ' "$WORK/TABLE.txt"
[ "$BAD" -eq 0 ]
