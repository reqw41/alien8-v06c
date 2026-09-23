#!/usr/bin/env node
// ГЕЙТ РАСПАКОВКИ ИТОГОВОГО РЕЛИЗА (tools/a8_pack.py): к jp START память та же, что у эталона.
//
//   node tools/unpack_vec.js [релиз.r0m релиз.sld эталон.r0m эталон.sld]
//        (по умолчанию build/alien8_release.* и build/alien8_release_ref.*)
//   A8UP_KEYF=<кадр клавиши «0»> (по умолчанию 40), A8UP_POST=<кадров после START> (300)
//
// СЦЕНАРИЙ. Сброс, кадры по 59 904 такта, клавиша «0» на кадре KEYF и держится до START (так же
// у эталона: он уходит в START, пока клавиша ещё нажата). Эталон гоняется тем же сценарием.
//
// ПРОВЕРКИ (код 1 при любой):
//  1. IN-PLACE: во время распаковки потока L (spl_s2_u .. spl_s2_l) ни один байт потока
//     [spl_L, spl_L_end) не читается ПОСЛЕ того, как в него записали (чтение затёртого).
//  2. ТОЧКА spl_unpacked (распаковка кончилась, кода игры ещё не было): память [0, 0xF100) ==
//     образ эталона байт в байт, кроме плоскости 0 0x8000..0x9FFF — там нули (у эталона там его
//     1 bpp картинка, которую его же a8_sp_key_down стирает до jp START).
//  3. ТОЧКА START: SP = seed_1, прерывания разрешены; память [0, 0xF100) == та же цель, кроме
//     ячеек, записанных после spl_unpacked (vec_set_pal 7 и vec_isr — тот же код, что у эталона
//     между сбросом и START). Их множество обязано входить в множество адресов, которые до своего
//     START записал эталон (тот же код ISR/vec_boot — «те же ячейки»); каждый писатель — код игры.
//     Картинка плоскости 2 (смещения 0x20..0xDF страниц 0xC0..0xDF) — нули: к START плоскость 2
//     чиста (на заставке там была картинка — сторож a8_regions для релиза её пропускает).
//  4. 0xF100..0xFFFF (ступень 2, её стек, остатки картинки) — START переписывает ДО чтения: после
//     START первое обращение к КАЖДОМУ из 3840 адресов — запись (прогон POST кадров).
//  5. Сводка против эталона в ЕГО точке START (для отчёта): где и почему память разная.
"use strict";
const fs = require("fs");
const E = require("./vec_emu");
const [ROM, SLD, REF, REFSLD] = process.argv.length > 5 ? process.argv.slice(2) :
  ["build/alien8_release.r0m", "build/alien8_release.sld", "build/alien8_release_ref.r0m", "build/alien8_release_ref.sld"];
const KEYF = +(process.env.A8UP_KEYF || 40), POST = +(process.env.A8UP_POST || 300);
const L = E.labels(SLD), R = E.labels(REFSLD);
for (const n of ["spl_s2_start", "spl_s2_u", "spl_s2_l", "spl_unpacked", "spl_L", "spl_L_end", "G_START", "G_SEED_1"])
  if (L[n] === undefined) { console.log("нет метки " + n + " в " + SLD); process.exit(2); }
const I = new Uint8Array(fs.readFileSync(REF)).subarray(0, 0x10000);
const X1 = 0xF100;
const tgt = a => (a >= 0x8000 && a < 0xA000) ? 0 : I[a];
const rlabs = Object.entries(R).sort((a, b) => a[1] - b[1]);
function nm(pc) { let b = null; for (const [n, a] of rlabs) { if (a <= pc) b = [n, a]; else break; } return b ? `${b[0]}+${pc - b[1]}` : "?"; }
const hex = a => a.toString(16).padStart(4, "0");
let bad = 0;
const fail = s => { console.log("КРАСНЫЙ: " + s); bad++; };

// ---- эталон: память и записи до его START ----
const r = E.mk(REF);
const Wr = new Set();
let rstart = -1, rpc = 0;
r.onInstr = pc => { rpc = pc; if (pc === R.START && rstart < 0) rstart = r.frames; };
r.onWrite = a => { if (rstart < 0) Wr.add(a); };
for (let f = 0; f < KEYF + 400 && rstart < 0; f++) { if (f === KEYF) r.keyboard.matrix[2] |= 1; r.frame(); }
// кадр, в котором PC впервые = START, досчитываем командами: frame() идёт до конца кадра
if (rstart < 0) { console.log("эталон не дошёл до START"); process.exit(2); }
// точный снимок эталона в START: гоним заново до PC == START и снимаем в хуке
const r2 = E.mk(REF);
let Rdump = null;
r2.onInstr = pc => { if (pc === R.START && !Rdump) Rdump = r2.dump(); };
for (let f = 0; f < KEYF + 400 && !Rdump; f++) { if (f === KEYF) r2.keyboard.matrix[2] |= 1; r2.frame(); }

// ---- итоговый релиз ----
const m = E.mk(ROM);
let phase = "splash", curpc = 0;
const ev = {};
const Lw = new Set(); let ipViol = 0, ipFirst = null, ipReads = 0, ipPtr = L.spl_L;
const Wp = new Map();            // адрес -> писатель (после spl_unpacked, до START)
let D1 = null, D2 = null, sp2 = -1, iff2 = null;
const x1First = new Map();       // после START: адрес X1 -> "r"/"w" первого обращения
m.onInstr = pc => {
  curpc = pc;
  if (pc === L.spl_s2_start && !("s2" in ev)) { ev.s2 = m.frames; phase = "s2"; }
  if (pc === L.spl_s2_u && !("L" in ev)) { ev.L = m.frames; phase = "L"; }
  if (pc === L.spl_s2_l && !("Lend" in ev)) { ev.Lend = m.frames; phase = "s2"; }
  if (pc === L.spl_unpacked && !D1) { D1 = m.dump(); ev.unpacked = m.frames; phase = "boot"; }
  if (pc === L.G_START && !D2) { D2 = m.dump(); ev.start = m.frames; sp2 = m.cpu.sp; iff2 = m.cpu.iff; phase = "game"; }
};
m.onRead = a => {
  // поток читается строго подряд (HL распаковщика, каждый байт ровно раз); чтение по адресу
  // «следующий непрочитанный байт потока» — это чтение потока, всё прочее — копия уже
  // распакованного (она законно может лежать поверх прочитанной части потока)
  if (phase === "L" && a === ipPtr) {
    ipReads++; ipPtr++;
    if (Lw.has(a)) { ipViol++; if (!ipFirst) ipFirst = `байт потока ${hex(a)} прочитан ПОСЛЕ записи в него (pc ${hex(curpc)})`; }
  }
  if (phase === "game" && a >= X1 && !x1First.has(a) && !(curpc === a)) x1First.set(a, "r:" + hex(curpc));
};
m.onWrite = a => {
  if (phase === "L" && a >= L.spl_L && a < L.spl_L_end) Lw.add(a);
  if (phase === "boot" && a < X1) Wp.set(a, curpc);
  if (phase === "game" && a >= X1 && !x1First.has(a)) x1First.set(a, "w");
};
for (let f = 0; f < KEYF + 600 && !D2; f++) { if (f === KEYF) m.keyboard.matrix[2] |= 1; m.frame(); }
if (!D2) { console.log(`START не достигнут за ${KEYF + 600} кадров; события ${JSON.stringify(ev)}`); process.exit(1); }
m.keyboard.matrix[2] &= ~1;
for (let f = 0; f < POST; f++) m.frame();

console.log(`клавиша «0» на кадре ${KEYF}: ступень 2 с кадра ${ev.s2}, поток L ${ev.L}..${ev.Lend}, ` +
            `распаковано ${ev.unpacked}, START на кадре ${ev.start} — ${ev.start - KEYF} кадров от клавиши ` +
            `(${((ev.start - KEYF) * 59904 / 3e6).toFixed(2)} с); у эталона START на кадре ${rstart}`);
// 1
console.log(`in-place: прочитано байт потока L ${ipReads} из ${L.spl_L_end - L.spl_L}, записей распаковщика в его ` +
            `адреса ${Lw.size}, байт потока, прочитанных после записи в них, ${ipViol}`);
if (!Lw.size) fail("in-place: хук слеп (нет записей в адреса потока L)");
if (ipReads !== L.spl_L_end - L.spl_L) fail("in-place: поток L прочитан не целиком и не подряд");
if (ipViol) fail("in-place: " + ipFirst);
// 2
{ let n = 0, first = [];
  for (let a = 0; a < X1; a++) if (D1[a] !== tgt(a)) { n++; if (first.length < 8) first.push(`${hex(a)}=${D1[a].toString(16)}/${tgt(a).toString(16)}`); }
  console.log(`spl_unpacked: [0000,F100) против эталона (плоскость 0 = 0): расхождений ${n}` + (n ? " — " + first.join(" ") : ""));
  if (n) fail("распаковка не дала образ эталона"); }
// 3
{ let n = 0, first = [];
  const writers = new Map();
  for (let a = 0; a < X1; a++) {
    if (Wp.has(a)) continue;
    if (D2[a] !== tgt(a)) { n++; if (first.length < 8) first.push(`${hex(a)}=${D2[a].toString(16)}/${tgt(a).toString(16)}`); }
  }
  let notRef = [], notGame = 0;
  for (const [a, pc] of Wp) {
    if (!Wr.has(a)) notRef.push(hex(a));
    if (pc >= X1) notGame++;
    const k = nm(pc).replace(/\+\d+$/, "");
    writers.set(k, (writers.get(k) || 0) + 1);
  }
  console.log(`START: SP=${hex(sp2)} (seed_1 ${hex(L.G_SEED_1)}), iff=${iff2}; записей игры после распаковки ` +
              `${Wp.size} адресов (${[...writers].map(([k, v]) => k + ":" + v).join(", ")}); ` +
              `вне их расхождений с целью ${n}` + (n ? " — " + first.join(" ") : ""));
  if (sp2 !== L.G_SEED_1) fail("SP на START не seed_1");
  if (!iff2) fail("на START прерывания запрещены (у эталона разрешены)");
  if (n) fail("память на START разошлась с эталоном вне ячеек ISR/vec_set_pal");
  if (notRef.length) fail(`после распаковки записаны ячейки, которых эталон до START не писал: ${notRef.slice(0, 10).join(" ")}`);
  if (notGame) fail(`после распаковки ${notGame} записей ниже 0xF100 сделал код ступени 2, а не игры`);
  let p2 = 0;
  for (let a = 0xC000; a < 0xE000; a++) if ((a & 0xFF) >= 0x20 && (a & 0xFF) <= 0xDF && D2[a]) p2++;
  console.log(`START: картинка плоскости 2 — ненулевых байт ${p2}`);
  if (p2) fail("к START плоскость 2 не чиста"); }
// 4
{ let rf = [], unw = 0;
  for (let a = X1; a < 0x10000; a++) { const v = x1First.get(a); if (!v) unw++; else if (v !== "w") rf.push(hex(a) + "@" + v.slice(2)); }
  console.log(`0xF100..0xFFFF после START (${POST} кадров): первым — запись у ${0x10000 - X1 - unw - rf.length}, ` +
              `чтение у ${rf.length}, не тронуто ${unw}`);
  if (rf.length) fail("читается до записи: " + rf.slice(0, 8).join(" "));
  if (unw) fail(`${unw} адресов 0xF100..0xFFFF не переписаны — исключение не доказано`); }
// 5
{ const cls = {};
  const put = (k) => { cls[k] = (cls[k] || 0) + 1; };
  for (let a = 0; a < 0x10000; a++) if (D2[a] !== Rdump[a]) {
    if (a >= X1) put("F100..FFFF (таблицы build_lookup_tbls)");
    else if (a >= 0xA000 && a < 0xC000 && (a & 0xFF) >= 0x20 && (a & 0xFF) <= 0xDF) put("картинка плоскости 1 (у эталона — копия его 1 bpp заставки)");
    else if (a >= R.msx_tv_stub && a < R.msx_tv_v1 + 16) put("ячейки плеера msx_tv (эталон играл ими заставку)");
    else if (a >= R.seed_1 - 0x100 && a < R.seed_1) put("стек ниже seed_1 (мусор вызовов заставки эталона)");
    else if (Wp.has(a) || Wr.has(a)) put("ячейки ISR/vec_boot (клавиатура, темп, палитра)");
    else put("ПРОЧЕЕ " + hex(a));
  }
  console.log("против эталона в ЕГО START: " + (Object.keys(cls).length ? Object.entries(cls).map(([k, v]) => `${k}: ${v}`).join("; ") : "совпало всё"));
  for (const k of Object.keys(cls)) if (k.startsWith("ПРОЧЕЕ")) fail("расхождение с эталоном вне классов: " + k); }
console.log(bad ? `ГЕЙТ РАСПАКОВКИ КРАСНЫЙ: нарушений ${bad}` : "гейт распаковки зелёный");
process.exit(bad ? 1 : 0);
