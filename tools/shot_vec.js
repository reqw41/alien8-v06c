#!/usr/bin/env node
// Снимок экрана Alien 8 на Векторе (headless vector06js) в PGM/текст.
//   node tools/shot_vec.js build/alien8_vec.r0m <кадров> [клавиши.txt] [out.pgm]
// Клавиши: строки «<кадр> <клавиша> down|up», клавиши — имена матрицы Вектора (см. VKEYS).
// Печатает также состояние: PC, SP, кадры, ВИ53 тикает (иначе бюджет di стоит, §14).
"use strict";
const fs=require("fs"),vm=require("vm");
const base="/Users/boris/projects/vector06js";
const [ROM,NS,KEYS,OUT]=process.argv.slice(2); const N=+NS||600;
const g={};g.window=g;g.document={createElement:()=>fc(),getElementById:()=>fc()};
function fcx(){return{createImageData:()=>({data:new Uint8ClampedArray(4)}),putImageData:()=>{},getImageData:()=>({data:new Uint8ClampedArray(4)}),fillRect(){},drawImage(){}};}
function fc(){return{width:0,height:0,style:{},getContext:()=>fcx()};}
g.requestAnimationFrame=()=>0;g.setTimeout=()=>0;g.print=()=>0;g.console={log(){},debug(){},warn(){},error(){},info(){}};
const ctx=vm.createContext(g);
for(const f of ["i8080-js/i8080_trace.js","i8080-js/i8080_disasm.js","i8080-js/i8080.js","src/fili.js","src/ay.js","src/fd1793.js","src/fddimage.js","src/i8253.js","src/io.js","src/keyboard.js","src/memory.js","src/sound.js","src/tv.js"])
  vm.runInContext(fs.readFileSync(base+"/"+f,"utf8"),ctx,{filename:f});
const memory=new ctx.Memory(),keyboard=new ctx.Keyboard(),timer=new ctx.I8253(),ay=new ctx.AY(),
      floppy=new(ctx.Floppy().FD1793)(),io=new ctx.IO(keyboard,timer,memory,ay,floppy);
// ДЖОЙСТИК ВЕКТОРА (порт 0x0E, чтение) в vector06js СОБИРАЕТСЯ ИЗ МАТРИЦЫ (стрелки, пробел, W) —
// в стенде это подмешивало бы джойстик к каждому нажатию клавиши, чего на живом Векторе нет
// (там это отдельная микросхема). Подменяем чтение: по умолчанию покой, сценарий задаёт joy(...).
// Биты порта active-low: 0 RIGHT, 1 LEFT, 2 UP, 3 DOWN, 6 FIRE1, 7 FIRE2; биты 4,5 схема держит в 1.
const JOY_R=0x01, JOY_L=0x02, JOY_U=0x04, JOY_D=0x08, JOY_F1=0x40, JOY_F2=0x80, JOY_IDLE=0xFF;
let JOY = JOY_IDLE;
function joy(...bits){ JOY = JOY_IDLE; for(const b of bits) JOY &= ~b & 0xFF; return JOY; }
{ const _rd = io.input.bind(io); io.input = p => ((p & 0xFF) === 0x0E ? JOY : _rd(p)); }
const cpu=new ctx.I8080(memory,io),tape={advance:()=>{},sample:0,reset:()=>{}},v06c=new ctx.Vector06c(cpu,memory,io,ay,tape);
v06c.bmp=new Uint32Array(576*288);v06c.displayFrame=()=>{};v06c.check_breakpoint=()=>false;v06c.dbg=null;
memory.init_from_array(new Uint8Array(fs.readFileSync(ROM)).subarray(0,0x10000),0);memory.detach_boot&&memory.detach_boot();
cpu.pc=0;cpu.sp=0x8000;cpu.iff=false;
// матрица Вектора: ряд4 @ABCDEFG, ряд5 HIJKLMNO, ряд6 PQRSTUVW, ряд7 XYZ[\]^ПРБ, ряд2 0..7, ряд3 8,9, ряд0 ВК/стрелки
const VKEYS={a:[4,0x02],b:[4,0x04],c:[4,0x08],d:[4,0x10],e:[4,0x20],f:[4,0x40],g:[4,0x80],
  h:[5,0x01],i:[5,0x02],j:[5,0x04],k:[5,0x08],l:[5,0x10],m:[5,0x20],n:[5,0x40],o:[5,0x80],
  p:[6,0x01],q:[6,0x02],r:[6,0x04],s:[6,0x08],t:[6,0x10],u:[6,0x20],v:[6,0x40],w:[6,0x80],
  x:[7,0x01],y:[7,0x02],z:[7,0x04],space:[7,0x80],
  "0":[2,0x01],"1":[2,0x02],"2":[2,0x04],"3":[2,0x08],"4":[2,0x10],"5":[2,0x20],"6":[2,0x40],"7":[2,0x80],
  "8":[3,0x01],"9":[3,0x02],vk:[0,0x04],left:[0,0x10],up:[0,0x20],right:[0,0x40],down:[0,0x80]};
function key(k,down){const e=VKEYS[k];if(!e)throw new Error("нет клавиши "+k);if(down)keyboard.matrix[e[0]]|=e[1];else keyboard.matrix[e[0]]&=~e[1];}
const plan={};
if(KEYS&&fs.existsSync(KEYS))for(const l of fs.readFileSync(KEYS,"utf8").split("\n")){
  const m=l.trim().match(/^(\d+)\s+(\S+)\s+(down|up)/i);if(m)(plan[+m[1]]=plan[+m[1]]||[]).push([m[2].toLowerCase(),m[3].toLowerCase()==="down"]);}
for(let f=0;f<N;f++){for(const [k,d] of (plan[f]||[]))key(k,d);v06c.oneInterrupt(true);}
const rd=a=>memory.bytes[memory.tobank(a&0xffff)];
console.log(`кадров ${N}, PC=${cpu.pc.toString(16)} SP=${cpu.sp.toString(16)} iff=${cpu.iff}`);
// экран Вектора: 256x256, адрес = 0x8000 + столбец*256 + строка; строка 0 внизу, бит 7 = левый пиксель
let ink=0;
const W=256,H=256;const px=new Uint8Array(W*H);
for(let col=0;col<32;col++)for(let row=0;row<256;row++){
  const b=rd(0x8000+col*256+row);if(b)ink++;
  for(let k=0;k<8;k++)px[(255-row)*W+col*8+k]=(b>>(7-k))&1?255:0;}
console.log(`точек в плоскости 0: ${ink} байт ненулевых`);
if(OUT){const hdr=Buffer.from(`P5\n${W} ${H}\n255\n`);fs.writeFileSync(OUT,Buffer.concat([hdr,Buffer.from(px)]));console.log("снимок -> "+OUT);}
// грубый ASCII-предпросмотр 64x48 (шаг 4x5, точка = есть пиксели в клетке)
let art="";
for(let y=0;y<256;y+=5){let s="";for(let x=0;x<256;x+=4){let v=0;for(let dy=0;dy<5;dy++)for(let dx=0;dx<4;dx++)v|=px[(y+dy)*W+x+dx];s+=v?"#":".";}art+=s+"\n";}
console.log(art);
// координаты героя (graphic_objs_tbl+1..+3 = X,Y,Z) — видно, дошёл ли ввод до логики
if(process.env.A8SLD){const L={};for(const l of require("fs").readFileSync(process.env.A8SLD,"latin1").split("\n")){const p=l.split("|");if(p.length>=8&&p[6]==="L"){const n=p[7].split(",")[1];if(n&&!(n in L))L[n]=+p[5];}}
  const t=L.graphic_objs_tbl;console.log(`герой: X=${rd(t+1)} Y=${rd(t+2)} Z=${rd(t+3)} gfx=${rd(t+0)}; жизни=${rd(L.lives)}; ряды ZX=${[...Array(8)].map((_,r)=>rd(L.vec_zxrows+r).toString(16)).join(" ")}`);}
