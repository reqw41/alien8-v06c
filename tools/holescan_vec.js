#!/usr/bin/env node
// ДЫРЫ ВНЕ КАРТИНКИ: какие СТРОКИ каждой страницы видеопамяти (0x8000+) реально пишутся.
// Картинка занимает строки 32..223 каждого из 32 столбцов плоскости (адрес = база + столбец*256
// + 32 + Y). Строки 224..255 столбца c и 0..31 столбца c+1 лежат в памяти подряд — 64 непрерывных
// байта, куда не должен писать ни рендер, ни очистка буфера. Если так — туда можно класть код
// (a8_pack_holes в tools/a8_z80_to_8080.py). Этот стенд — ЗАМЕР, доказывающий посылку, и
// одновременно СТОРОЖ: любая запись вне строк 32..223 печатается с PC писателя и даёт код 1.
//
//   node tools/holescan_vec.js build/alien8_vec.r0m build/alien8_vec.sld <итераций> [inputs.txt]
//   A8ROOM=<номер>  — подменить комнату (как в zxpix_vec.js / profile_vec.js)
//   A8HOLE_ALL=1    — считать ВСЁ, включая фазу до входа в комнату (по умолчанию тоже всё:
//                     стирание экрана на старте — это как раз то, что надо проверить)
//   A8HOLE_GAME=1   — только фаза игры (без старта комнаты), для разведения причин
//   A8HOLE_PC=N     — сколько нарушителей печатать (по умолчанию 20)
//   A8HOLE_PLANE=A000 — какая плоскость судится (по умолчанию плоскость 1 = буфер)
// Судится ОДНА плоскость — та, чьи дыры отданы под код. У Alien 8 это плоскость 1 (буфер
// 0xA000..0xBFFF): только её очистка (clear_scrn_buffer) идёт постолбцово по строкам 32..223.
// Прочие плоскости печатаются справочно и приговора не выносят:
//   плоскость 0 (экран) — vec_boot/vb_clr стирает её СПЛОШНЫМ циклом 8 КБ, дыры там заняты
//     нулями очистки; класть туда код нельзя (и не нужно — плоскости 1 хватает);
//   плоскость 2 — переменные игры (0xC800..0xCF87), цепочки print_sprite и блок Вектора;
//   плоскость 3 — таблицы сдвига 0xF100+ (их строит build_lookup_tbls).
// Код возврата: 0 — в судимой плоскости вне строк 32..223 не записано ни байта; 1 — записано.
"use strict";
const fs=require("fs"),vm=require("vm");
const base = process.env.V06 || (process.env.HOME + "/projects/vector06js");
const [ROM,SLD,NS,INPUTS]=process.argv.slice(2); const N=+NS||300;
const NPC=+(process.env.A8HOLE_PC||20);
const JUDGE=parseInt(process.env.A8HOLE_PLANE||"A000",16)>>8;   // страница-база судимой плоскости
const L={}; const LBYADDR=[];
for(const l of fs.readFileSync(SLD,"latin1").split("\n")){const p=l.split("|");if(p.length>=8&&p[6]==="L"){const n=p[7].split(",")[1];if(n&&!(n in L))L[n]=+p[5];}}
for(const n in L)if(L[n]>=0x40)LBYADDR.push([L[n],n]);
LBYADDR.sort((a,b)=>a[0]-b[0]);
function who(pc){let lo=0,hi=LBYADDR.length-1,r=-1;while(lo<=hi){const m=(lo+hi)>>1;if(LBYADDR[m][0]<=pc){r=m;lo=m+1;}else hi=m-1;}
  return r<0?"?":`${LBYADDR[r][1]}+${pc-LBYADDR[r][0]}`;}
const SEED2HI=L.seed_2+1, ROOM=L.curr_room_attrib, VKBD=L.vkbd;
const lst=fs.readFileSync(ROM.replace(/\.r0m$/,".lst"),"latin1").split("\n");
let SYNC=-1;for(const l of lst){const m=l.match(/^\s*\d+\+?\s+([0-9A-F]{4})\s.*\s+call\s+init_start_location/);if(m){SYNC=parseInt(m[1],16);break;}}
if(SYNC<0)throw new Error("не нашёл call init_start_location в листинге");
const GAMEONLY=!!process.env.A8HOLE_GAME;
const g={};g.window=g;g.document={createElement:()=>fc(),getElementById:()=>fc()};
function fcx(){return{createImageData:()=>({data:new Uint8ClampedArray(4)}),putImageData:()=>{},getImageData:()=>({data:new Uint8ClampedArray(4)}),fillRect(){},drawImage(){}};}
function fc(){return{width:0,height:0,style:{},getContext:()=>fcx()};}
g.requestAnimationFrame=()=>0;g.setTimeout=()=>0;g.print=()=>0;g.console={log(){},debug(){},warn(){},error(){},info(){}};
const ctx=vm.createContext(g);
for(const f of ["i8080-js/i8080_trace.js","i8080-js/i8080_disasm.js","i8080-js/i8080.js","src/fili.js","src/ay.js","src/fd1793.js","src/fddimage.js","src/i8253.js","src/io.js","src/keyboard.js","src/memory.js","src/sound.js","src/tv.js"])
  vm.runInContext(fs.readFileSync(base+"/"+f,"utf8"),ctx,{filename:f});
const memory=new ctx.Memory(),keyboard=new ctx.Keyboard(),timer=new ctx.I8253(),ay=new ctx.AY(),
      floppy=new(ctx.Floppy().FD1793)(),io=new ctx.IO(keyboard,timer,memory,ay,floppy);
// ДЖОЙСТИК ВЕКТОРА (порт 0x0E) в vector06js собирается из матрицы — на живом Векторе это
// отдельная микросхема. Подменяем чтение: покой (как в остальных стендах порта).
const JOY_IDLE=0xFF; let JOY=JOY_IDLE;
{ const _rd=io.input.bind(io); io.input=p=>((p&0xFF)===0x0E?JOY:_rd(p)); }
const cpu=new ctx.I8080(memory,io),tape={advance:()=>{},sample:0,reset:()=>{}},v06c=new ctx.Vector06c(cpu,memory,io,ay,tape);
v06c.bmp=new Uint32Array(576*288);v06c.displayFrame=()=>{};v06c.check_breakpoint=()=>false;v06c.dbg=null;
memory.init_from_array(new Uint8Array(fs.readFileSync(ROM)).subarray(0,0x10000),0);memory.detach_boot&&memory.detach_boot();
cpu.pc=0;cpu.sp=0x8000;cpu.iff=false;
if(VKBD!==undefined)for(let r=0;r<8;r++)memory.write(VKBD+r,0xFF,false);
const rd=a=>memory.bytes[memory.tobank(a&0xffff)];
const ow=memory.write.bind(memory); const poke=(a,v)=>ow(a&0xffff,v&0xff,false);
// seed_3 += mem[seed_2]: игра подмешивает в случайное число байт памяти по адресу-счётчику
// (на Векторе это собственный код). Гасим, как в screendiff_vec.js: иначе сдвиг кода меняет
// всю случайную последовательность и два прогона сравнивать нельзя.
{ const s3=L.seed_3&0xff, s3h=(L.seed_3>>8)&0xff;
  const pat=[0x3A,s3,s3h,0x86,0x85,0x84,0x32,s3,s3h]; let at=-1;
  for(let a=0x100;a<0xF000&&at<0;a++){let ok=true;for(let i=0;i<pat.length;i++)if(rd(a+i)!==pat[i]){ok=false;break;}if(ok)at=a;}
  if(at<0)throw new Error("не нашёл seed_3 += mem[seed_2]");
  memory.write(at+3,0x00,false); }
const KEYS={z:[0,1],x:[0,2],a:[1,0],q:[2,0],"0":[4,0],space:[7,0]}; const rows=new Uint8Array(8).fill(0xFF);
const VKEYS={z:[7,0x04],x:[7,0x01],a:[4,0x02],q:[6,0x02],"0":[2,0x01],space:[7,0x80]};
const HWKB=process.env.A8KB==="hw";
const ZXROWS=(!HWKB&&VKBD===undefined&&L.vec_zxbuild!==undefined)?L.vec_zxrows:undefined;
const KBMAT=(ZXROWS!==undefined&&L.vec_scan!==undefined)?L.vec_kbmat:undefined;
if(ZXROWS!==undefined){memory.write(L.vec_zxbuild,0xC9,false);
  for(let r=0;r<8;r++)memory.write(ZXROWS+r,0xFF,false);}
const kbm=new Uint8Array(8);
if(KBMAT!==undefined){memory.write(L.vec_scan,0xC9,false);
  for(let r=0;r<8;r++)memory.write(KBMAT+r,0,false);}
function key(k,down){
  if(VKBD===undefined&&ZXROWS===undefined){const [r,b]=VKEYS[k];if(down)keyboard.matrix[r]|=b;else keyboard.matrix[r]&=~b;return;}
  if(KBMAT!==undefined){const [vr,vb]=VKEYS[k];if(down)kbm[vr]|=vb;else kbm[vr]&=~vb;poke(KBMAT+vr,kbm[vr]);}
  const [r,b]=KEYS[k];if(down)rows[r]&=~(1<<b);else rows[r]|=(1<<b);poke((VKBD!==undefined?VKBD:ZXROWS)+r,rows[r]);}
const inputs={}; if(INPUTS&&fs.existsSync(INPUTS))for(const l of fs.readFileSync(INPUTS,"utf8").split("\n")){const m=l.trim().match(/^(\d+)\s+(\S+)\s+(down|up)/i);if(m)(inputs[+m[1]+1]=inputs[+m[1]+1]||[]).push([m[2].toLowerCase(),m[3].toLowerCase()==="down"]);}
// --- счётчики: по странице видеопамяти минимальная и максимальная тронутая строка ---
const lorow=new Uint16Array(256).fill(999), hirow=new Int32Array(256).fill(-1), wr=new Float64Array(256);
const bad=[]; let nbad=0;                       // записи ВНЕ строк 32..223
let phase="menu",iter=0;
memory.write=function(a,w,s){a&=0xffff;
  if(a>=0x8000&&(!GAMEONLY||phase==="game")){const p=a>>8,r=a&0xFF;
    if(r<lorow[p])lorow[p]=r;if(r>hirow[p])hirow[p]=r;wr[p]++;
    if((r<32||r>223)&&(p>>5)===(JUDGE>>5)){nbad++;if(bad.length<NPC)bad.push([a,cpu.pc,w,iter,phase]);}}
  if(phase==="menu"&&cpu.pc===SYNC){poke(L.seed_1,0x34);poke(L.seed_1+1,0x12);poke(L.seed_2,0x78);poke(L.seed_2+1,0x56);poke(L.seed_3,0x9A);phase="init";}
  if(process.env.A8ROOM&&phase==="init"&&(a===L.graphic_objs_tbl+8||a===L.graphic_objs_tbl+40)){
    w=+process.env.A8ROOM;}
  if(a===ROOM&&phase==="init"&&w!==0){phase="game";key("0",false);}
  if(a===SEED2HI&&phase==="game"){iter++;for(const [k,d] of (inputs[iter]||[]))key(k,d);}
  return ow(a,w,s);};
for(let f=0;f<60;f++)v06c.oneInterrupt(true); key("0",true);
let guard=0; while(phase!=="game"&&guard++<3000)v06c.oneInterrupt(true);
if(phase!=="game")throw new Error("не дошли до комнаты");
const startIter=iter; let steps=0,frc=0,tacc=0;
const IRQDROP=!!process.env.A8_IRQDROP;
while(iter-startIter<N&&steps<3e8){if(frc>=59904){frc-=59904;if(!(IRQDROP&&!cpu.iff)){v06c.irq=true;v06c.checkInterrupt();}}
  const c=(cpu.instruction(),cpu.vcycles);steps++;frc+=c;tacc+=c;if(tacc>1){const tn=tacc>>1;tacc-=tn*2;timer.Count(tn);}if(cpu.last_opcode===0xd3)io.commit();}
const tot=wr.reduce((a,b)=>a+b,0);
console.log(`комната ${process.env.A8ROOM||"стартовая"}, сценарий ${INPUTS?INPUTS.replace(/.*\//,""):"покой"}, `
  +`итераций ${iter-startIter}, записей в 0x8000+: ${tot}`);
const PL=[[0x80,"плоскость 0 (экран)"],[0xA0,"плоскость 1 (буфер)"],[0xC0,"плоскость 2"],[0xE0,"плоскость 3 (код)"]];
for(const [b,nm] of PL){
  let lo=999,hi=-1,t=0,pages=0,out=0;
  for(let p=b;p<b+32;p++){t+=wr[p];if(hirow[p]>=0){pages++;if(lorow[p]<lo)lo=lorow[p];if(hirow[p]>hi)hi=hirow[p];
    if(lorow[p]<32||hirow[p]>223)out++;}}
  console.log(`${nm}${b===JUDGE?" <- СУДИТСЯ":""}: страниц с записью ${pages}/32, записей ${t}, `
    +`строки ${hi<0?"-":lo+".."+hi}${out?`, вне картинки тронуто страниц ${out}`:""}`);
  if(b===JUDGE&&hi>=0)for(let p=b;p<b+32;p++)if(hirow[p]>=0&&(lorow[p]<32||hirow[p]>223))
    console.log(`   ВНЕ КАРТИНКИ: страница ${p.toString(16)} строки ${lorow[p]}..${hirow[p]} (${wr[p]} записей)`);
}
if(nbad){
  console.log(`НАРУШЕНИЕ: ${nbad} записей вне строк 32..223 судимой плоскости (первые ${bad.length}):`);
  for(const [a,pc,w,it,ph] of bad)
    console.log(`   ${a.toString(16)} <- ${w.toString(16).padStart(2,"0")}  PC ${pc.toString(16)} (${who(pc)})  итерация ${it} фаза ${ph}`);
  process.exit(1);
}
console.log(`ЗЕЛЁНЫЙ: в плоскости ${(JUDGE<<8).toString(16)} вне строк 32..223 не записано ни байта — дыры свободны`);
