# Alien 8 → Вектор-06Ц

Порт по рецепту, отработанному на Knight Lore: `~/projects/knightlore-v06c/docs/PORT_RECIPE.md`.
Обе игры — Ultimate 1984–85, движок Filmation, один автор дизассемблера (tcdev).

Материалы (образы игр, дизассемблер, стенды): `~/projects/alien8-research/`.
Готовый порт-образец со всеми инструментами: `~/projects/knightlore-v06c/`.

## Состояние (2026-09-11)
Этапы 1–3 закрыты, журнал и все числа — в `docs/PORT_RECIPE.md`.

| этап | состояние | гейт |
|---|---|---|
| 1. сборка дизассемблера tcdev | закрыт | `./build.sh zx` — 28515 байт $6288-$D1EA совпали с оригинальным снимком байт в байт |
| 2. журнал состояний оригинала | закрыт | `~/projects/alien8-research/zx-stand/` — три журнала по 600 итераций, каждый повторяется байт в байт в трёх прогонах |
| 3. рекомпиляция Z80 → i8080 | закрыт | `./build.sh lockstep` + `tools/lockstep_vec.js` — 600 из 600 итераций байт в байт на всех трёх сценариях |
| 4. склейка Вектора | не начат | |
| 5. звук, атрибуты, стековый вывод, HUD, цвет, темп | не начат | |

```bash
./build.sh zx          # ZX-версия из листинга tcdev + гейт «байт в байт»
./build.sh lockstep    # i8080, логика 1:1, вывод заглушен + три гейта
node tools/lockstep_vec.js build/alien8_8080.r0m build/alien8_8080.sld 600 \
  ~/projects/alien8-research/zx-stand/inputs_idle.txt \
  ~/projects/alien8-research/zx-stand/zx_idle600.bin
```

## Каталоги
- `tools/` — транслятор, гейты, профилировщики (берутся из knightlore-v06c и правятся под Alien 8)
- `src/` — asm-исходник игры (сборка дизассемблера tcdev под sjasmplus)
- `spec/` — спецификации процедур на Python для метода «спец → дамп → asm» (пока пусто)
- `docs/` — журнал порта
- `build/` — сборки (в индекс не берутся)
