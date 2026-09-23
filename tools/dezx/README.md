# dzx0 для i8080 (Ivan Gorodetsky)

`dzx0_8080_ivagor_v4.asm` — распаковщик формата ZX0 «classic» (v1) для Intel 8080,
**Ivan Gorodetsky (ivagor)**, v4 от 2021-02-23 (98 Б вперёд / 97 Б назад), «Based on ZX0 z80
decoder by Einar Saukas». Взят как есть из https://github.com/eiroca/DeZX (коммит e99a1a4,
2021-04-05; зеркало ivagorRetrocomp/DeZX, на которое ссылается README ZX0 — оригинал сейчас
отдаёт 404). `README.upstream.md` — README того репозитория.

**Лицензия.** В репозитории DeZX файла лицензии НЕТ (проверено: `git ls-files` — только README
и .asm; GitHub API: license = null). Код — производная от z80-распаковщика ZX0 Эйнара Саукаса,
который распространяется под BSD-3 (`tools/zx0/LICENSE`); авторство и BSD-3 указаны в
`tools/a8_pack.py` рядом с переводом в синтаксис sjasmplus. Вопрос для владельца: для публичного
релиза стоит спросить у автора явную лицензию (или заменить своим распаковщиком).

В сборку идёт ПЕРЕВОД ветки FORWARD в Z80-мнемоники (подмножество i8080) — `DZX0` в
`tools/a8_pack.py`, команда в команду, без правок.
