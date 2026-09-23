#!/usr/bin/env node
// ГЕЙТ «НА ЗАСТАВКЕ ПИШЕТ ТОЛЬКО ЗАСТАВКА И ТОЛЬКО В СВОЁ» (итоговый релиз, tools/a8_pack.py).
//
//   node tools/splashzone_vec.js [build/alien8_release.r0m build/alien8_release.sld]
//   A8SZ_KEYF=<кадр клавиши «0»> (по умолчанию 8600: мелодия целиком, 8427 кадров, + петля)
//
// ЧТО СТЕРЕЖЁТ. На заставке итогового релиза в памяти лежат: сжатая игра (потоки L, H, P3), мелодия,
// код заставки, картинка во всех четырёх плоскостях. Исполняться может ТОЛЬКО самодостаточный код
// заставки (ступень 1: ISR, главный цикл, init/tick мелодии, копия плеера spl_tv) — кода игры ещё
// нет, он сжат. Любая запись вне ОЗУ заставки портит либо поток (распаковка даст не ту игру —
// увидит unpack только если байт ещё не прочитан), либо картинку (мусор на экране), либо код.
// Разрешённые адреса: ячейки spl_key..spl_tv_divs+1, состояние голосов spl_st (3 x 41), стек
// заставки spl_stack..spl_stack_top-1. Разрешённые писатели: код ступени 1 [spl_isr, spl_s2_src)
// и вход в прерывание (адрес возврата кладёт сам процессор).
// Прежний смысл гейта (5728180: «зону 3 переменных игры пишут только заставка, ISR и плеер»)
// переехал сюда целиком: у итоговой заставки кроме неё самой писать некому — это и проверяется.
//
// СЦЕНАРИЙ. Сброс, кадры по 59 904 такта, «0» на кадре KEYF; судим записи до PC == spl_exit
// (заставка кончилась, дальше распаковка — ей писать можно всюду; её судит tools/unpack_vec.js).
// КРИТЕРИЙ (код 1): spl_exit не достигнут; запись вне разрешённого; писатель не из ступени 1;
// КОНТРОЛЬ ХУКА — записей в состояние голосов 0 или в флаг кадра 0 (тогда «чисто» ничего не значит).
"use strict";
const E = require("./vec_emu");
const [ROM, SLD] = process.argv.length > 3 ? process.argv.slice(2) : ["build/alien8_release.r0m", "build/alien8_release.sld"];
const KEYF = +(process.env.A8SZ_KEYF || 8600);
const L = E.labels(SLD);
for (const t of ["spl_isr", "spl_s2_src", "spl_exit", "spl_key", "spl_flag", "spl_tv_divs", "spl_st", "spl_stack", "spl_stack_top"])
  if (L[t] === undefined) { console.log("нет метки " + t + " — образ не итоговый релиз (tools/a8_pack.py)?"); process.exit(2); }
const ALLOW = [[L.spl_key, L.spl_tv_divs + 2, "ячейки заставки"], [L.spl_st, L.spl_st + 41 * 3, "голоса мелодии"],
               [L.spl_stack, L.spl_stack_top, "стек заставки"]];
const CODE = [L.spl_isr, L.spl_s2_src];
const labs = Object.entries(L).sort((a, b) => a[1] - b[1]);
function nm(pc) { let b = null; for (const [n, a] of labs) { if (a <= pc) b = [n, a]; else break; } return b ? `${b[0]}+${pc - b[1]}` : "?"; }
const hex = a => a.toString(16).padStart(4, "0");
const m = E.mk(ROM);
let curpc = 0, done = -1;
const zone = {}; let nBad = 0, nWriter = 0, badList = [], nState = 0, nFlag = 0;
m.onInstr = pc => { curpc = pc; if (pc === L.spl_exit && done < 0) done = m.frames; };
m.onWrite = a => {
  if (done >= 0) return;
  const z = ALLOW.find(([lo, hi]) => a >= lo && a < hi);
  if (!z) { nBad++; if (badList.length < 8) badList.push(`${hex(a)} (pc ${hex(curpc)} ${nm(curpc)})`); }
  else zone[z[2]] = (zone[z[2]] || 0) + 1;
  if (curpc < CODE[0] || curpc >= CODE[1]) { nWriter++; if (badList.length < 8) badList.push(`писатель ${hex(curpc)} ${nm(curpc)} -> ${hex(a)}`); }
  if (a >= L.spl_st && a < L.spl_st + 41 * 3) nState++;
  if (a === L.spl_flag) nFlag++;
};
for (let f = 0; f < KEYF + 50 && done < 0; f++) { if (f === KEYF) m.keyboard.matrix[2] |= 1; m.frame(); }
let bad = 0;
console.log(`заставка: клавиша на кадре ${KEYF}, spl_exit на кадре ${done}; записи по зонам: ` +
            Object.entries(zone).map(([k, v]) => `${k} ${v}`).join(", ") +
            `; вне разрешённого ${nBad}, писателей не из ступени 1 ${nWriter}; контроль хука: голоса ${nState}, флаг кадра ${nFlag}`);
if (badList.length) console.log("  " + badList.join("\n  "));
if (done < 0) { console.log("spl_exit не достигнут"); bad++; }
if (!nState || !nFlag) { console.log("КОНТРОЛЬ ХУКА: нет записей в голоса или во флаг кадра — тап слеп или мелодия не играла"); bad++; }
if (nBad) { console.log(`ЗАПИСИ ВНЕ ОЗУ ЗАСТАВКИ: ${nBad}`); bad++; }
if (nWriter) { console.log(`ПИСАЛ НЕ КОД ЗАСТАВКИ: ${nWriter}`); bad++; }
console.log(bad ? `ГЕЙТ ЗОНЫ ЗАСТАВКИ КРАСНЫЙ: нарушений ${bad}` : "гейт зоны заставки зелёный");
process.exit(bad ? 1 : 0);
