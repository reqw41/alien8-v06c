# ZX0 (компрессор), Einar Saukas — BSD-3

Исходники оптимального компрессора ZX0 v2.2 (https://github.com/einar-saukas/ZX0, каталог
`src/`, без изменений): `zx0.c compress.c optimize.c memory.c zx0.h`, лицензия — `LICENSE`
(BSD 3-Clause, © 2021 Einar Saukas), README автора — `README.upstream.md`.
Собирается в `build/zx0` из `./build.sh release`; зовётся из `tools/a8_pack.py` с ключом `-c`
(«classic» формат v1 — единственный, который понимает dzx0 для i8080, `tools/dezx/`).
