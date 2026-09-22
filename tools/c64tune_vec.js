// c64tune_vec.js — гейт мелодии C64 на релизной заставке (build/alien8_release.r0m, A8_SPLASH=1).
// Тап на out 0x08/0x0B/0x0A/0x09: по кадрам восстанавливаем эффективный делитель каждого
// счётчика ВИ53 и сравниваем с эталоном decode() из tools/a8_tune_c64.py (8427 кадров цикла
// + 100 кадров зацикливания = 8527). Семантика Вектора: управляющее слово БЕЗ делителя
// (0x36/0x76/0xB6) останавливает счётчик = тишина; запись LSB+MSB загружает делитель.
// Затем: клавиша -> игра стартует (jp START, build_lookup_tbls затирает данные мелодии).
// Расхождений 0 -> PASS. Образцы: kbcheck_vec.js, tunecheck_vec.js.
const fs = require("fs"), vm = require("vm"), cp = require("child_process");
const base = "/Users/boris/projects/vector06js";
const ROM = process.argv[2] || "build/alien8_release.r0m";
const NREF = +(process.env.C64N || 8527); // 8427 кадров цикла + 100 кадров зацикливания
const g = {};
g.window = g; g.document = { createElement: () => fc(), getElementById: () => fc() };
function fcx(){return{createImageData:()=>({data:new Uint8ClampedArray(4)}),putImageData:()=>{},getImageData:()=>({data:new Uint8ClampedArray(4)}),fillRect(){},drawImage(){}};}
function fc(){return{width:0,height:0,style:{},getContext:()=>fcx()};}
g.requestAnimationFrame = () => 0; g.setTimeout = () => 0; g.print = () => 0;
g.console = { log(){}, debug(){}, warn(){}, error(){}, info(){} };
const ctx = vm.createContext(g);
for (const f of ["i8080-js/i8080_trace.js","i8080-js/i8080_disasm.js","i8080-js/i8080.js",
                 "src/fili.js","src/ay.js","src/fd1793.js","src/fddimage.js","src/i8253.js",
                 "src/io.js","src/keyboard.js","src/memory.js","src/sound.js","src/tv.js"])
  vm.runInContext(fs.readFileSync(base + "/" + f, "utf8"), ctx, { filename: f });
const memory = new ctx.Memory(), keyboard = new ctx.Keyboard(), timer = new ctx.I8253(),
      ay = new ctx.AY(), floppy = new (ctx.Floppy().FD1793)(),
      io = new ctx.IO(keyboard, timer, memory, ay, floppy);
let JOY = 0xFF;                          // джойстик в покое: клавишей не считается
{ const _rd = io.input.bind(io); io.input = p => ((p & 0xFF) === 0x0E ? JOY : _rd(p)); }
const cpu = new ctx.I8080(memory, io),
      tape = { advance: () => {}, sample: 0, reset: () => {} },
      v06c = new ctx.Vector06c(cpu, memory, io, ay, tape);
v06c.bmp = new Uint32Array(576 * 288); v06c.displayFrame = () => {};
v06c.check_breakpoint = () => false; v06c.dbg = null;
const IMG = new Uint8Array(fs.readFileSync(ROM).subarray(0, 0x10000));
if (IMG[0] !== 0xF3 || IMG[1] !== 0x31) throw new Error("загрузчик не `di / ld sp,imm` — база стека не читается");
const SPBASE = IMG[2] | (IMG[3] << 8);
memory.init_from_array(IMG, 0); memory.detach_boot && memory.detach_boot();
const rd = a => memory.bytes[memory.tobank(a & 0xffff)];
cpu.pc = 0; cpu.sp = SPBASE; cpu.iff = false;

// тап на out: пишем (порт, значение) в порядке исполнения
let taps = [];
{ const _wr = io.output.bind(io);
  io.output = (p, v) => { if ((p & 0xFF) >= 0x08 && (p & 0xFF) <= 0x0B) taps.push(p & 0xFF, v); _wr(p, v); }; }

// эталон: 8527 кадров делителей (голоса A,B,C = счётчики 0,1,2)
const ref = JSON.parse(cp.execSync("python3 -c \"import sys, json; sys.path.insert(0,'tools'); " +
  "import a8_tune_c64 as T; print(json.dumps(T.decode(open('src/c64_tune.bin','rb').read(), " + Math.max(NREF, 8527) + ")))\"").toString());
if (ref.length < NREF) throw new Error("эталон короче " + NREF);

// кадры до инициализации плеера (первый кадр, где заглушают все три счётчика)
let F0 = -1;
for (let f = 0; f < 3000 && F0 < 0; f++) {
  taps = []; v06c.oneInterrupt(true);
  const s = new Set();
  for (let i = 0; i < taps.length; i += 2) if (taps[i] === 0x08) s.add(taps[i + 1]);
  if (s.has(0x36) && s.has(0x76) && s.has(0xB6)) {
    F0 = f;
    if (process.env.C64D) {
      let q = "INIT-FRAME state: ";
      for (let v = 0; v < 3; v++) { q += `v${v}[`; for (let a = 0; a < 7; a++) q += rd(0xFF00 + v*41 + a).toString(16).padStart(2,'0') + ' '; q += '] '; }
      q += '| divs '; for (let a = 0xFF7B; a <= 0xFF7C; a++) q += rd(a).toString(16).padStart(2,'0') + ' ';
      console.log(q);
    }
  }
}
if (F0 < 0) { console.log("FAIL: за 3000 кадров не видно инициализации плеера (0x36/0x76/0xB6 в порт 0x08)"); process.exit(1); }

// состояние счётчиков: делитель после всех записей кадра; 0 = молчит
const eff = [0, 0, 0], rx = [0, 0, 0], pend = [0, 0, 0];
let bad = 0, firstBad = null, badlist = [];
function applyTaps() {
  for (let i = 0; i < taps.length; i += 2) {
    const p = taps[i], v = taps[i + 1];
    if (p === 0x08) {
      const c = v >> 6;
      if ((v & 0x30) !== 0) { eff[c] = 0; rx[c] = 0; pend[c] = 0; } // управляющее без делителя = стоп
    } else {
      const c = 0x0B - p;
      if (rx[c] === 0) { pend[c] = v; rx[c] = 1; }
      else { eff[c] = ((v << 8) | pend[c]) & 0xFFFF; rx[c] = 0; }
    }
  }
}
// кадр F0: eff = 0 = кадр 0 эталона (мелодь ещё молчит); далее кадр F0+i сверяется с ref[i-1]
const DBG = +process.env.C64D || 0;
const taplog = [];
for (let i = 1; i <= NREF; i++) {
  taps = []; v06c.oneInterrupt(true); applyTaps();
  if (DBG) {
    if (i <= 10) console.log(`F${i}: pc=${cpu.pc.toString(16)} v38=${rd(0x38).toString(16)},${rd(0x39).toString(16)},${rd(0x3a).toString(16)} rows=` + (() => { let s=''; for (let r = 0; r < 8; r++) s += rd(0x48 + r).toString(16).padStart(2,'0'); return s; })() + ' joyraw=' + rd(0xC908).toString(16) + ' taps: ' + taps.join(','));
    if (i <= 6) {
      let s = `S${i}: `;
      for (let v = 0; v < 3; v++) { s += `v${v}[` ; for (let a = 0; a < 7; a++) s += rd(0xFF00 + v*41 + a).toString(16).padStart(2,'0') + ' '; s += '] '; }
      s += '| divs ' + rd(0xFF7B).toString(16) + ' c ' + rd(0xFF7F).toString(16) + ' stub ' + rd(0xFF84).toString(16);
      console.log(s);
    }
    if (i === 6) {
      let s = "voice1 state 0xFF29: ";
      for (let a = 0; a < 12; a++) s += rd(0xFF29 + a).toString(16).padStart(2, '0') + ' ';
      s += "| cells: ";
      for (let a = 0xFF7B; a <= 0xFF86; a++) s += rd(a).toString(16).padStart(2, '0') + ' ';
      s += "| voice0: ";
      for (let a = 0; a < 7; a++) s += rd(0xFF00 + a).toString(16).padStart(2, '0') + ' ';
      s += "| voice2: ";
      for (let a = 0; a < 7; a++) s += rd(0xFF52 + a).toString(16).padStart(2, '0') + ' ';
      console.log(s);
      console.log(taplog.join("\n"));
    }
    if (i <= DBG) console.log(`f${i}: eff=${eff.join(',')} ref=${ref[i-1].join(',')}`);
  }
  for (let c = 0; c < 3; c++) if (eff[c] !== ref[i - 1][c]) {
    bad++;
    if (!firstBad) firstBad = `кадр ${i}: счётчик ${c} = ${eff[c]}, эталон ${ref[i - 1][c]}`;
    if (badlist.length < 60) badlist.push(`f${i} c${c}: ${eff[c]} vs ${ref[i-1][c]}`);
  }
}
if (bad) { console.log(`FAIL: расхождений ${bad}; первое: ${firstBad}`); if (badlist.length) console.log(badlist.join("; ")); process.exit(1); }

// клавиша -> игра стартует: jp START и build_lookup_tbls затирает данные мелодии.
// Матрица vector06js: покой = 0, нажатие = бит 1 (как в tunecheck_vec.js); джойстик
// порта 0x0E наоборот (покой 0xFF) — его даёт обёртка JOY.
const sig = [];
for (let a = 0; a < 16; a++) sig.push(rd(0xF100 + a));
keyboard.matrix[2] |= 0x01;               // «0» — старт (как в tunecheck_vec.js): ряд 2, линия 0
let started = -1;
for (let f = 0; f < 400; f++) {
  if (f === 6) keyboard.matrix[2] &= ~0x01; // отпускаем
  v06c.oneInterrupt(true);
  if (started < 0) {
    let diff = false;
    for (let a = 0; a < 16; a++) if (rd(0xF100 + a) !== sig[a]) { diff = true; break; }
    if (diff) started = f;
  }
}
if (started < 0) { console.log("FAIL: через 400 кадров после «0» не стартовала игра (0xF100 не перезаписан таблицами)"); process.exit(1); }
if (cpu.pc >= 0xF100) { console.log(`FAIL: после старта pc=0x${cpu.pc.toString(16)} застрял в регионе мелодии`); process.exit(1); }
for (let f = 0; f < 100; f++) v06c.oneInterrupt(true);   // игра работает (меню), без краша
console.log(`PASS: мелодия C64 ${NREF} кадров × 3 счётчика без расхождений (иниц. кадр ${F0}); ` +
            `клавиша -> игра на кадре ${started}, pc=0x${cpu.pc.toString(16)}`);
