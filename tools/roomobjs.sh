#!/bin/bash
# ПЕРЕПИСЬ КЛАССОВ ОБЪЕКТОВ ПО КОМНАТАМ: какой обработчик `upd_NN` работает в какой комнате.
#
# Зачем. Два дефекта рекомпиляции (робомышь, журнал 2026-09-15) дожили до владельца потому,
# что обработчик `upd_5E_5F` не работал НИ В ОДНОЙ из семи гейтовых комнат. Вопрос «какие
# ещё классы объектов не покрыты» решается переписью: прогнать каждую комнату и посмотреть,
# какие метки диспетчера `jump_to_upd_object` вообще посещаются.
#
# Считает tools/pcstat_vec.js (счётчик посещений меток), по одному прогону на комнату,
# короткому (по умолчанию 60 итераций покоя) — класс объекта виден с первой же итерации.
# A8GAG=1, как в profile_vec.js: подмешивание байта памяти в seed_3 гасится, иначе прогоны
# двух сборок расходятся; для переписи КЛАССОВ этого достаточно.
#
#   tools/roomobjs.sh                 # все комнаты, 60 итераций, 8 потоков
#   tools/roomobjs.sh 60 8 "19 137"   # итерации, потоки, список комнат
#
# Выход: build/roomobjs/CENSUS.txt — «комната: upd_XX upd_YY ...» и сводка
# «обработчик -> в скольких комнатах, в каких».
set -u
cd "$(dirname "$0")/.."
ROOT=$(pwd)
ITERS=${1:-60}
JOBS=${2:-8}
ROOMLIST=${3:-}
WORK=$ROOT/build/roomobjs
rm -rf "$WORK"; mkdir -p "$WORK/res"
[ -f build/alien8_vec.r0m ] || { echo "нет build/alien8_vec.r0m — сначала ./build.sh vec"; exit 2; }

grep -oE '^upd_[0-9A-Fa-f_to]+' src/alien8_zx.asm | sort -u | paste -sd, - > "$WORK/upds.txt"
if [ -n "$ROOMLIST" ]; then printf '%s\n' $ROOMLIST > "$WORK/rooms.txt"
else python3 tools/a8_rooms.py > "$WORK/rooms.txt" || exit 2; fi

cat > "$WORK/one.sh" <<'ONE'
#!/bin/bash
set -u
R=$1
cd "$ROOT"
A8GAG=1 node tools/pcstat_vec.js build/alien8_vec.r0m build/alien8_vec.sld "$ITERS" \
  "$(cat "$WORK/upds.txt")" "$R" 2>&1 \
  | awk '$1 ~ /^upd_/ && $2+0 > 0 {printf "%s ", $1}' > "$WORK/res/$R.txt"
ONE
chmod +x "$WORK/one.sh"
export ROOT WORK ITERS
xargs -P "$JOBS" -n 1 "$WORK/one.sh" < "$WORK/rooms.txt"

python3 - "$WORK" <<'PY' | tee "$WORK/CENSUS.txt"
import os, sys, collections
w = sys.argv[1]
rooms = [int(x) for x in open(os.path.join(w, 'rooms.txt'))]
per = {}
for r in rooms:
    p = os.path.join(w, 'res', '%d.txt' % r)
    per[r] = open(p).read().split() if os.path.exists(p) else []
print('КОМНАТА -> КЛАССЫ ОБЪЕКТОВ (работавшие обработчики upd_NN)')
for r in rooms:
    print('%4d: %s' % (r, ' '.join(per[r]) or '(ни одного)'))
inv = collections.defaultdict(list)
for r in rooms:
    for u in per[r]:
        inv[u].append(r)
print()
print('ОБРАБОТЧИК -> В СКОЛЬКИХ КОМНАТАХ')
for u in sorted(inv, key=lambda u: (-len(inv[u]), u)):
    rs = inv[u]
    print('%-18s %3d  %s' % (u, len(rs), ' '.join(map(str, rs)) if len(rs) <= 20 else
                             ' '.join(map(str, rs[:20])) + ' ...'))
alls = set()
for u in inv:
    alls.add(u)
names = [l.split()[0] for l in open(os.path.join(w, 'upds.txt')).read().replace(',', '\n').split('\n') if l.strip()]
never = [u for u in names if u not in alls]
print()
print('НИ РАЗУ НЕ РАБОТАЛИ в этом прогоне (%d из %d): %s' % (len(never), len(names), ' '.join(never)))
PY
