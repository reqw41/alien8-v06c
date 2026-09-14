#!/usr/bin/env node
// ЗАМЕР разворотов спрайтов: сколько раз за итерацию игра разворачивает спрайты, какие,
// какого размера, V или H, и есть ли трэшинг (один спрайт гоняется туда-сюда).
//   A8GAG=1 [A8ROOM=n] node tools/flipstat_vec.js build/alien8_vec.r0m build/alien8_vec.sld <итераций> [inputs.txt]
// Стенд — как в profile_vec.js (тот же прогон, та же подмена комнаты и та же заглушка seed_3).
// Точка съёма — вход в vflip_sprite_data (flip_sprite прыгает туда, если спрайт не пустой):
// DE = адрес данных спрайта, (ix+7) = требуемая ориентация, (DE) = хранимая.
// Такты считаются по стеку: от входа до момента, когда SP поднялся выше точки входа.
"use strict";
const fs=require("fs"),vm=require("vm");
const base="/Users/boris/projects/vector06js";
const [ROM,SLD,NS,INPUTS]=process.argv.slice(2); const N=+NS||150;
const LAG=+(process.env.A8_LAG||1);
const L={};
for(const l of fs.readFileSync(SLD,"latin1").split("\n")){const p=l.split("|");if(p.length>=8&&p[6]==="L"){const n=p[7].split(",")[1];if(n&&!(n in L))L[n]=+p[5];}}
const SEED2HI=L.seed_2+1, ROOM=L.curr_room_attrib, VKBD=L.vkbd;
const FS=L.flip_sprite, VFSD=L.vflip_sprite_data, IXC=L.z80_ix;
if(FS===undefined||VFSD===undefined||IXC===undefined)throw new Error("нет меток flip_sprite/vflip_sprite_data/z80_ix");
const lst=fs.readFileSync(ROM.replace(/\.r0m$/,".lst"),"latin1").split("\n");
let SYNC=-1;for(const l of lst){const m=l.match(/^\s*\d+\+?\s+([0-9A-F]{4})\s.*\s+call\s+init_start_location/);if(m){SYNC=parseInt(m[1],16);break;}}
if(SYNC<0)throw new Error("не нашёл call init_start_location");
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
cpu.pc=0;cpu.sp=0xBC00;cpu.iff=false;
if(VKBD!==undefined)for(let r=0;r<8;r++)memory.write(VKBD+r,0xFF,false);
const ow=memory.write.bind(memory); const poke=(a,v)=>ow(a&0xffff,v&0xff,false);
const rd=a=>memory.read(a&0xffff,false);
const KEYS={shift:[0,0],z:[0,1],x:[0,2],c:[0,3],v:[0,4],a:[1,0],s:[1,1],d:[1,2],f:[1,3],g:[1,4],q:[2,0],w:[2,1],e:[2,2],r:[2,3],t:[2,4],
  "1":[3,0],"2":[3,1],"3":[3,2],"4":[3,3],"5":[3,4],"0":[4,0],"9":[4,1],"8":[4,2],"7":[4,3],"6":[4,4],p:[5,0],o:[5,1],i:[5,2],u:[5,3],y:[5,4],
  enter:[6,0],l:[6,1],k:[6,2],j:[6,3],h:[6,4],space:[7,0],sym:[7,1],m:[7,2],n:[7,3],b:[7,4]};
const VKEYS={z:[7,0x04],x:[7,0x01],a:[4,0x02],q:[6,0x02],"0":[2,0x01],space:[7,0x80]};
const rows=new Uint8Array(8).fill(0xFF);
function key(k,down){
  if(VKBD===undefined){const [r,b]=VKEYS[k];if(down)keyboard.matrix[r]|=b;else keyboard.matrix[r]&=~b;return;}
  const [r,b]=KEYS[k];if(down)rows[r]&=~(1<<b);else rows[r]|=(1<<b);poke(VKBD+r,rows[r]);}
const inputs={}; if(INPUTS&&fs.existsSync(INPUTS))for(const l of fs.readFileSync(INPUTS,"utf8").split("\n")){const m=l.trim().match(/^(\d+)\s+(\S+)\s+(down|up)/i);if(m)(inputs[+m[1]+LAG]=inputs[+m[1]+LAG]||[]).push([m[2].toLowerCase(),m[3].toLowerCase()==="down"]);}
let FR=0,TOT=0;
let phase="menu",iter=0,total=0;
if(process.env.A8GAG){ const rdb=a=>memory.bytes[memory.tobank(a&0xffff)];
  const s3=L.seed_3&0xff, s3h=(L.seed_3>>8)&0xff;
  const pat=[0x3A,s3,s3h,0x86,0x85,0x84,0x32,s3,s3h]; let at=-1;
  for(let a=0x100;a<0xF000&&at<0;a++){let ok=true;for(let i=0;i<pat.length;i++)if(rdb(a+i)!==pat[i]){ok=false;break;}if(ok)at=a;}
  if(at<0)throw new Error("не нашёл seed_3 += mem[seed_2]");
  ow(at+3,0x00,false); }
memory.write=function(a,w,s){a&=0xffff;
  if(phase==="menu"&&cpu.pc===SYNC){poke(L.seed_1,0x34);poke(L.seed_1+1,0x12);poke(L.seed_2,0x78);poke(L.seed_2+1,0x56);poke(L.seed_3,0x9A);phase="init";}
  if(process.env.A8ROOM&&phase==="init"&&(a===L.graphic_objs_tbl+8||a===L.graphic_objs_tbl+40)){w=+process.env.A8ROOM;}
  if(a===ROOM&&phase==="init"&&w!==0){phase="game";key("0",false);}
  if(a===SEED2HI&&phase==="game"){iter++;for(const [k,d] of (inputs[iter]||[]))key(k,d);}
  return ow(a,w,s);};
for(let f=0;f<60;f++)v06c.oneInterrupt(true); key("0",true);
let guard=0; while(phase!=="game"&&guard++<3000)v06c.oneInterrupt(true);
if(phase!=="game")throw new Error("не дошли до комнаты");
const startIter=iter;

// A8SPRTRACE=1: кто вообще читает и пишет БАЙТЫ данных спрайтов (для доказательства, что
// разворот — единственный писатель, а print_sprite — единственный читатель).
const FLAB=Object.entries(L).filter(([n,a])=>a>=0x80&&!/^(spr_|\.)/.test(n)).sort((x,y)=>x[1]-y[1]);
function fname(pc){let lo=0,hi=FLAB.length-1,r="?";while(lo<=hi){const m=(lo+hi)>>1;if(FLAB[m][1]<=pc){r=FLAB[m][0];lo=m+1;}else hi=m-1;}return r;}
const sprmap=new Uint8Array(0x10000);
if(process.env.A8SPRTRACE){
  for(const [n,a] of Object.entries(L)) if(/^spr_\d+$/.test(n)){
    const w=rd(a)&0x0F,h=rd(a+1); if(!w||!h||h>64)continue;
    for(let i=0;i<2+2*w*h;i++)sprmap[(a+i)&0xffff]=1;}
  const rdo=memory.read.bind(memory);
  memory.read=function(a,s){a&=0xffff;if(sprmap[a])(sprRd[fname(cpu.pc)]=(sprRd[fname(cpu.pc)]||0)+1);return rdo(a,s);};
  const wro=memory.write.bind(memory);
  memory.write=function(a,w,s){a&=0xffff;if(sprmap[a])(sprWr[fname(cpu.pc)]=(sprWr[fname(cpu.pc)]||0)+1);return wro(a,w,s);};
}
const sprRd={},sprWr={};

// --- сбор ---
let nCallFS=0, nEnter=0, nFlip=0, nV=0, nH=0, nVH=0, cycFlip=0, cycV=0, cycH=0;
const byspr=new Map();          // адрес спрайта -> {w,h,size,n,nv,nh,cyc,last,thrash,orients:Set}
let inFlip=false, flipSp=0, cur=null;
let inCall=false, callSp=0, cycCall=0, callFlipped=false, callRet=0;
const bycaller=new Map();       // возврат из flip_sprite -> {n, nflip, cyc}
const C2D=L.calc_2d_info, PS=L.print_sprite;
let steps=0, frc=0, tacc=0;
while(iter-startIter<N&&steps<3e8){
  if(frc>=59904){frc-=59904;FR++;v06c.irq=true;v06c.checkInterrupt();}
  const pc=cpu.pc;
  if(pc===FS&&!inCall){nCallFS++;inCall=true;callSp=cpu.sp;callFlipped=false;
    callRet=rd(cpu.sp)|(rd(cpu.sp+1)<<8);
    if(!bycaller.has(callRet))bycaller.set(callRet,{n:0,nflip:0,cyc:0});
    bycaller.get(callRet).n++;}
  if(pc===VFSD&&!inFlip){
    const de=cpu.de(), ix=rd(IXC)|(rd(IXC+1)<<8);
    const hdr=rd(de), want=rd(ix+7)&0xC0, have=hdr&0xC0, d=have^want;
    const w=hdr&0x0F, h=rd(de+1), size=2+2*w*h;
    nEnter++;
    let e=byspr.get(de);
    if(!e){e={w,h,size,n:0,nv:0,nh:0,cyc:0,last:-1,thrash:0,or:new Set()};byspr.set(de,e);}
    e.n++;
    if(d){
      nFlip++; if(d&0x80)nV++; if(d&0x40)nH++; if(d===0xC0)nVH++;
      if(d&0x80)e.nv++; if(d&0x40)e.nh++;
      e.or.add(want);
      if(e.last>=0&&e.last!==want)e.thrash++;
      e.last=want;
      inFlip=true; flipSp=cpu.sp; cur=e; callFlipped=true; if(inCall)bycaller.get(callRet).nflip++;
    }
  }
  const c=(cpu.instruction(),cpu.vcycles);steps++;total+=c;TOT+=c;frc+=c;
  tacc+=c;if(tacc>1){const tn=tacc>>1;tacc-=tn*2;timer.Count(tn);}
  if(cpu.last_opcode===0xd3)io.commit();
  if(inFlip){cycFlip+=c;cur.cyc+=c;if(cpu.sp>flipSp){inFlip=false;}}
  if(inCall){cycCall+=c;bycaller.get(callRet).cyc+=c;if(cpu.sp>callSp)inCall=false;}
}
const iters=iter-startIter;
const room=process.env.A8ROOM||"стартовая";
console.log(`комната ${room}: итераций ${iters}, тактов/итер ${(total/iters).toFixed(0)}`);
console.log(`flip_sprite вызовов ${(nCallFS/iters).toFixed(2)}/итер; из них дошло до разворота (спрайт не пуст) ${(nEnter/iters).toFixed(2)}/итер;`);
console.log(`  РЕАЛЬНЫХ разворотов ${(nFlip/iters).toFixed(2)}/итер: V ${(nV/iters).toFixed(2)}, H ${(nH/iters).toFixed(2)}, из них обе сразу ${(nVH/iters).toFixed(2)}`);
console.log(`  такты разворота ${(cycFlip/iters).toFixed(0)}/итер (${(100*cycFlip/total).toFixed(2)} % всех), ${(cycFlip/Math.max(1,nFlip)).toFixed(0)} тактов на разворот`);
console.log(`  ВСЕГО в flip_sprite ${(cycCall/iters).toFixed(0)} тактов/итер (${(100*cycCall/total).toFixed(2)} %); из них холостая проверка «ориентация уже та» ${((cycCall-cycFlip)/iters).toFixed(0)} тактов/итер = ${((cycCall-cycFlip)/Math.max(1,nCallFS-nFlip)).toFixed(0)} на вызов`);
const rows_=[...byspr.entries()].filter(([a,e])=>e.nv+e.nh>0).sort((a,b)=>b[1].cyc-a[1].cyc);
console.log("спрайт   w  h размер  разворотов/итер   V     H   тактов/итер  смен ориентации(трэшинг)");
for(const [a,e] of rows_.slice(0,+(process.env.A8TOP||12)))
  console.log(`${a.toString(16).toUpperCase().padStart(4)}  ${String(e.w).padStart(3)} ${String(e.h).padStart(2)} ${String(e.size).padStart(5)}  ${((e.nv+e.nh)/iters).toFixed(2).padStart(8)}  ${(e.nv/iters).toFixed(2).padStart(5)} ${(e.nh/iters).toFixed(2).padStart(5)}  ${(e.cyc/iters).toFixed(0).padStart(8)}  ${String(e.thrash).padStart(6)} (${e.or.size} ориентаций)`);
console.log("возврат из flip_sprite (кто звал)  вызовов/итер  разворотов/итер  тактов/итер");
for(const [a,e] of [...bycaller.entries()].sort((x,y)=>y[1].cyc-x[1].cyc)){
  const who=a>=C2D&&a<C2D+64?"calc_2d_info":(a>=PS&&a<PS+64?"print_sprite":"?");
  console.log(`${a.toString(16).toUpperCase().padStart(4)} (${who})`.padEnd(34)+`${(e.n/iters).toFixed(2).padStart(8)}  ${(e.nflip/iters).toFixed(3).padStart(12)}  ${(e.cyc/iters).toFixed(0).padStart(10)}`);}
if(process.env.A8SPRTRACE){
  console.log("ЧИТАЮТ байты спрайтов: "+Object.entries(sprRd).sort((a,b)=>b[1]-a[1]).map(([n,c])=>n+" "+c).join(", "));
  console.log("ПИШУТ  байты спрайтов: "+(Object.entries(sprWr).sort((a,b)=>b[1]-a[1]).map(([n,c])=>n+" "+c).join(", ")||"никто"));
}
const sizes=rows_.map(([a,e])=>e.size);
if(sizes.length)console.log(`размеры разворачиваемых спрайтов: min ${Math.min(...sizes)}, max ${Math.max(...sizes)}, уникальных спрайтов ${rows_.length}`);
