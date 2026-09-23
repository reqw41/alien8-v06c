#!/usr/bin/env node
// ГЕЙТ «ПОСЛЕ START ИГРА ИДЁТ КАК С НЕСЖАТОГО ЭТАЛОНА» (итоговый релиз, tools/a8_pack.py).
//
//   node tools/tracecmp_vec.js [релиз.r0m релиз.sld эталон.r0m эталон.sld]
//   A8TC_KEYF=<кадр «0» на заставке> (40), A8TC_N=<кадров после START> (1500)
//
// ТА ЖЕ ТОЧКА. Эталон гоняется ДВАЖДЫ одним сценарием (детерминирован) до PC == START:
//   A — как есть (память эталона в его START);
//   C — в START вся память 0..0xFFFF подменяется памятью ИТОГОВОГО релиза в его START (прогон P
//       тем же сценарием до PC == G_START). Процессор, таймер, порты, палитра у A и C одни.
// Разница памяти A/C в START — ровно то, чем итоговый релиз отличается от эталона к START
// (сводка tools/unpack_vec.js: F100..FFFF, картинка плоскости 1, стек ниже seed_1, ячейки msx_tv,
// ячейки ISR). Дальше оба идут N кадров с одним вводом: «0» отпускается, в меню снова «0»
// (новая игра, мелодия старта, комната), потом стрелки (ходьба/повороты).
// КРИТЕРИЙ (код 1): (1) выводы во ВСЕ порты за каждый кадр (звук ВИ53, палитра, бордюр, скролл,
// клавиатура) и регистры процессора в конце каждого кадра у A и C совпадают; (2) ни один адрес
// из начальной разницы не ПРОЧИТАН раньше, чем записан (ни у A, ни у C) — разница мертва, пока её
// не перепишут; (3) адреса разницы, которые за прогон никто не тронул, печатаются по классам.
// ЕДИНСТВЕННОЕ разрешённое «чтение раньше записи» — pace_el (счётчик кадров ограничителя темпа).
// Его значение к START зависит от того, СКОЛЬКО кадров прошло до START, у эталона тоже (клавиша
// раньше/позже — другое число), и это не дефект: читают его только (а) vec_isr/vcu_lost —
// `inc (hl)` с насыщением на 255, (б) vec_pace — `шаг - (hl)`: «прошло >= шага — не ждать», и
// сразу `ld (hl), 0`. Шаг — 1..2 кадра (PACE_INT + перенос), а первый vec_pace после START идёт
// не раньше конца мелодии старта (153 кадра): к нему pace_el >= шага у обоих, ветка одна, после
// неё — 0 у обоих. Гейт это не принимает на веру: выводы и регистры сверяются каждый кадр.
// Контроль хука: игра обязана дойти до комнаты — записи палитры (0x0C), звук ВИ53 и итерации
// игрового цикла (вызовы vec_pace) > 0.
"use strict";
const E = require("./vec_emu");
const [ROM, SLD, REF, REFSLD] = process.argv.length > 5 ? process.argv.slice(2) :
  ["build/alien8_release.r0m", "build/alien8_release.sld", "build/alien8_release_ref.r0m", "build/alien8_release_ref.sld"];
const KEYF = +(process.env.A8TC_KEYF || 40), N = +(process.env.A8TC_N || 1500);
const L = E.labels(SLD), R = E.labels(REFSLD);
const hex = a => a.toString(16).padStart(4, "0");

// P: итоговый релиз до G_START
const p = E.mk(ROM);
let D2 = null;
p.onInstr = pc => { if (pc === L.G_START && !D2) D2 = p.dump(); };
for (let f = 0; f < KEYF + 600 && !D2; f++) { if (f === KEYF) p.keyboard.matrix[2] |= 1; p.frame(); }
if (!D2) { console.log("итоговый релиз не дошёл до START"); process.exit(1); }

// A и C: эталон; в C память в START подменяется
const A = E.mk(REF), C = E.mk(REF);
let S = null, sA = -1, sC = -1;
let nIter = 0;                   // контроль хука: итераций игры (вызовов vec_pace) у A
A.onInstr = pc => { if (pc === R.START && sA < 0) { sA = A.frames; A.after = true; } if (pc === R.vec_pace) nIter++; };
C.onInstr = pc => {
  if (pc === R.START && sC < 0) {
    sC = C.frames; C.after = true;
    S = new Set();
    for (let a = 0; a < 0x10000; a++) { if (C.rd(a) !== D2[a]) S.add(a); C.wr(a, D2[a]); }
  }
};
// первое обращение к адресам разницы после START
const firstA = new Map(), firstC = new Map();
let pcA = 0, pcC = 0;
const watch = (m, first, who) => {
  m.onRead = a => { if (m.after && S.has(a) && !first.has(a)) first.set(a, "r"); };
  m.onWrite = a => { if (m.after && S.has(a) && !first.has(a)) first.set(a, "w"); };
};
watch(A, firstA, "A"); watch(C, firstC, "C");
A.outs = []; C.outs = [];
let F = 0, bad = 0, firstDiv = null, sndFrames = 0, palOut = 0, startF = -1;
const K0 = 0x01, ROW2 = 2;
function input(m, f) {
  // до START «0» держится с KEYF; после START: отпустить, в меню снова «0», потом ходьба стрелками
  const kb = m.keyboard.matrix;
  if (f === KEYF) kb[ROW2] |= K0;
  if (startF < 0) return;
  const t = f - startF;
  if (t === 5) kb[ROW2] &= ~K0;
  if (t === 250) kb[ROW2] |= K0;
  if (t === 262) kb[ROW2] &= ~K0;
  const arrows = [[700, 0x40], [760, 0x20], [900, 0x10], [940, 0x20], [1100, 0x80], [1150, 0x20], [1300, 0x40], [1330, 0x20]];
  for (let i = 0; i < arrows.length; i++) {
    const [t0, bit] = arrows[i], t1 = i + 1 < arrows.length ? arrows[i + 1][0] : 1450;
    if (t === t0) kb[0] |= bit;
    if (t === t1) kb[0] &= ~bit;
  }
}
for (F = 0; F < KEYF + 600 + N; F++) {
  input(A, F); input(C, F);
  A.outs.length = 0; C.outs.length = 0;
  C.frame(); A.frame();        // C первым: разница S считается в его START, A судится после своего
  if (startF < 0 && sA >= 0) {
    if (sA !== sC) { console.log(`эталон недетерминирован: START у A на ${sA}, у C на ${sC}`); process.exit(2); }
    startF = sA;
  }
  if (startF < 0) continue;
  const oa = A.outs.join(","), oc = C.outs.join(",");
  if (oa !== oc || A.regs() !== C.regs()) {
    if (!firstDiv) firstDiv = `кадр ${F - startF} после START: ` + (oa !== oc ? "выводы в порты разошлись" : `регистры ${A.regs()} / ${C.regs()}`);
    bad++;
  }
  for (let i = 0; i < A.outs.length; i += 2) {
    if (A.outs[i] === 0x0C) palOut++;
  }
  for (let i = 0; i < A.outs.length; i += 2) if ((A.outs[i] === 0x09 || A.outs[i] === 0x0A) ) { sndFrames++; break; }
  if (F - startF >= N) break;
}
let rA = [], rC = [], untouched = {};
const cls = a => a >= 0xF100 ? "F100..FFFF" : (a >= 0xA000 && a < 0xC000) ? "плоскость 1" :
  (a >= R.seed_1 - 0x100 && a < R.seed_1) ? "стек ниже seed_1" :
  (a >= R.msx_tv_stub && a < R.msx_tv_v1 + 16) ? "ячейки msx_tv" : (a < 0x100 || (a >= 0x7200 && a < 0x7300)) ? "ячейки ISR" : "прочее " + hex(a);
const OKREAD = new Set([R.pace_el]);
let okRead = 0;
for (const a of S) {
  if (OKREAD.has(a) && (firstA.get(a) === "r" || firstC.get(a) === "r")) { okRead++; continue; }
  if (firstA.get(a) === "r") rA.push(hex(a));
  if (firstC.get(a) === "r") rC.push(hex(a));
  if (!firstA.has(a) && !firstC.has(a)) { const k = cls(a); untouched[k] = (untouched[k] || 0) + 1; }
}
let finalDiff = 0; for (let a = 0; a < 0x10000; a++) if (A.rd(a) !== C.rd(a)) finalDiff++;
console.log(`START эталона на кадре ${startF}; разница памяти A/C в START ${S.size} адресов; прогон ${N} кадров после START`);
console.log(`кадров с расхождением выводов/регистров ${bad}${firstDiv ? " — первое: " + firstDiv : ""}; записей палитры 0x0C ${palOut}, кадров со звуком 1/2 ${sndFrames}, итераций игры (vec_pace) ${nIter}`);
console.log(`адреса разницы: pace_el ${okRead ? "прочитан раньше записи (разрешено, см. шапку)" : "не читался до записи"}; прочие прочитаны раньше записи — у A ${rA.length}, у C ${rC.length}` + (rA.length + rC.length ? " (" + rA.concat(rC).slice(0, 10).join(" ") + ")" : ""));
console.log(`к концу разница памяти ${finalDiff}; не тронуты за прогон: ` + (Object.keys(untouched).length ? Object.entries(untouched).map(([k, v]) => `${k} ${v}`).join(", ") : "нет"));
let red = 0;
if (bad) { console.log("КРАСНЫЙ: после START итоговый релиз ведёт себя не как эталон"); red++; }
if (rA.length || rC.length) { console.log("КРАСНЫЙ: разница памяти к START прочитана до перезаписи — она не мёртвая"); red++; }
if (Object.keys(untouched).some(k => k.startsWith("прочее"))) { console.log("КРАСНЫЙ: нетронутая разница вне известных классов"); red++; }
if (!palOut || !sndFrames || !nIter) { console.log("КОНТРОЛЬ ХУКА: нет записей палитры или звука — игра не шла"); red++; }
console.log(red ? `ГЕЙТ СЛЕДА ПОСЛЕ START КРАСНЫЙ: нарушений ${red}` : "гейт следа после START зелёный");
process.exit(red ? 1 : 0);
