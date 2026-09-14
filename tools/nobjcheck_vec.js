#!/usr/bin/env node
// Гейт инварианта a8_nobj: граница «занято/пусто» таблицы объектов (56 записей по 32 байта)
// не должна быть НИЖЕ последнего живого объекта, иначе укороченные циклы его пропустят.
//   node tools/nobjcheck_vec.js build/alien8_vec.r0m build/alien8_vec.sld <итераций> [inputs.txt]
// Проверяется дважды: на границе каждой итерации (a8_nobj против индекса последнего живого)
// и на КАЖДОЙ записи graphic_no != 0 в таблицу (индекс слота против a8_nobj).
// Без метки a8_nobj печатает только статистику «сколько записей реально занято».
"use strict";
const fs=require("fs"),vm=require("vm");
const base="/Users/boris/projects/vector06js";
const [ROM,SLD,NS,INPUTS]=process.argv.slice(2); const N=+NS||300;
const LAG=+(process.env.A8_LAG||1);
const L={};
for(const l of fs.readFileSync(SLD,"latin1").split("\n")){const p=l.split("|");if(p.length>=8&&p[6]==="L"){const n=p[7].split(",")[1];if(n&&!(n in L))L[n]=+p[5];}}
const SEED2HI=L.seed_2+1, ROOM=L.curr_room_attrib, VKBD=L.vkbd;
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
const cpu=new ctx.I8080(memory,io),tape={advance:()=>{},sample:0,reset:()=>{}},v06c=new ctx.Vector06c(cpu,memory,io,ay,tape);
v06c.bmp=new Uint32Array(576*288);v06c.displayFrame=()=>{};v06c.check_breakpoint=()=>false;v06c.dbg=null;
memory.init_from_array(new Uint8Array(fs.readFileSync(ROM)).subarray(0,0x10000),0);memory.detach_boot&&memory.detach_boot();
cpu.pc=0;cpu.sp=0xBC00;cpu.iff=false;
if(VKBD!==undefined)for(let r=0;r<8;r++)memory.write(VKBD+r,0xFF,false);
const ow=memory.write.bind(memory); const poke=(a,v)=>ow(a&0xffff,v&0xff,false);
const KEYS={shift:[0,0],z:[0,1],x:[0,2],c:[0,3],v:[0,4],a:[1,0],s:[1,1],d:[1,2],f:[1,3],g:[1,4],q:[2,0],w:[2,1],e:[2,2],r:[2,3],t:[2,4],
  "1":[3,0],"2":[3,1],"3":[3,2],"4":[3,3],"5":[3,4],"0":[4,0],"9":[4,1],"8":[4,2],"7":[4,3],"6":[4,4],p:[5,0],o:[5,1],i:[5,2],u:[5,3],y:[5,4],
  enter:[6,0],l:[6,1],k:[6,2],j:[6,3],h:[6,4],space:[7,0],sym:[7,1],m:[7,2],n:[7,3],b:[7,4]};
const VKEYS={z:[7,0x04],x:[7,0x01],a:[4,0x02],q:[6,0x02],"0":[2,0x01],space:[7,0x80]};
const rows=new Uint8Array(8).fill(0xFF);
function key(k,down){
  if(VKBD===undefined){const [r,b]=VKEYS[k];if(down)keyboard.matrix[r]|=b;else keyboard.matrix[r]&=~b;return;}
  const [r,b]=KEYS[k];if(down)rows[r]&=~(1<<b);else rows[r]|=(1<<b);poke(VKBD+r,rows[r]);}
const inputs={}; if(INPUTS&&fs.existsSync(INPUTS))for(const l of fs.readFileSync(INPUTS,"utf8").split("\n")){const m=l.trim().match(/^(\d+)\s+(\S+)\s+(down|up)/i);if(m)(inputs[+m[1]+LAG]=inputs[+m[1]+LAG]||[]).push([m[2].toLowerCase(),m[3].toLowerCase()==="down"]);}

const T=L.graphic_objs_tbl, NB=L.a8_nobj, NOBJ=56, BTB=L.block_type_tbl_base;
let loading=false;
let phase="menu",iter=0,steps=0,bad=0,worst=999,wcase=null,maxlive=-1,sumlive=0,cntlive=0;
function chk(tag){ let ml=-1;
  for(let i=0;i<NOBJ;i++) if(memory.read(T+i*32,false)!==0) ml=i;
  if(ml>maxlive)maxlive=ml; sumlive+=ml+1; cntlive++;
  if(NB===undefined)return;
  const n=memory.read(NB,false); const slack=n-1-ml;
  if(slack<worst){worst=slack;wcase=[tag,n,ml];}
  if(ml>=n){bad++;if(bad<6)console.log("НАРУШЕНИЕ",tag,": a8_nobj",n,"последний живой",ml);} }
memory.write=function(a,w,s){a&=0xffff;
  if(phase==="menu"&&cpu.pc===SYNC){poke(L.seed_1,0x34);poke(L.seed_1+1,0x12);poke(L.seed_2,0x78);poke(L.seed_2+1,0x56);poke(L.seed_3,0x9A);phase="init";}
  if(process.env.A8ROOM&&phase==="init"&&(a===T+8||a===T+40)){w=+process.env.A8ROOM;}
  if(a===ROOM&&phase==="init"&&w!==0){phase="game";key("0",false);}
  if(a===SEED2HI&&phase==="game"){iter++;for(const [k,d] of (inputs[iter]||[]))key(k,d);chk("итерация "+iter);}
  // Загрузка комнаты: retrieve_screen раскладывает объекты ПОДРЯД, а границу ставит в самом
  // конце (zero_end_of_graphic_objs_tbl), поэтому во время загрузки записи выше СТАРОЙ границы
  // законны — циклы по объектам в это время не работают. Признак начала загрузки — запись
  // block_type_tbl_base (первая инструкция retrieve_screen), конца — запись a8_nobj.
  if(a===BTB||a===BTB+1)loading=true;
  if(a===NB)loading=false;
  if(phase==="game"&&!loading&&NB!==undefined&&a>=T&&a<T+32*NOBJ&&((a-T)%32)===0&&w!==0){
    const i=(a-T)/32,n=memory.read(NB,false);
    if(i>=n){bad++;if(bad<9)console.log("ЗАПИСЬ ВЫШЕ ГРАНИЦЫ: слот",i,"a8_nobj",n,"pc",cpu.pc.toString(16));}}
  return ow(a,w,s);};
for(let f=0;f<60;f++)v06c.oneInterrupt(true); key("0",true);
let guard=0; while(phase!=="game"&&guard++<4000)v06c.oneInterrupt(true);
if(phase!=="game"){console.log("не дошли до комнаты");process.exit(2);}
const startIter=iter; let frc=0,tacc=0;
// A8_IRQDROP=1 — модель железа: прерывание Вектора не защёлкивается, обратный ход под di теряется.
const IRQDROP=!!process.env.A8_IRQDROP;
while(iter-startIter<N&&steps<3e8){if(frc>=59904){frc-=59904;if(!(IRQDROP&&!cpu.iff)){v06c.irq=true;v06c.checkInterrupt();}}
  const c=(cpu.instruction(),cpu.vcycles);steps++;frc+=c;tacc+=c;if(tacc>1){const tn=tacc>>1;tacc-=tn*2;timer.Count(tn);}
  if(cpu.last_opcode===0xd3)io.commit();}
console.log(`итераций ${iter-startIter}, последний живой слот: максимум ${maxlive}, среднее занятых ${(sumlive/Math.max(1,cntlive)).toFixed(1)} из ${NOBJ}`
  +(NB===undefined?" (метки a8_nobj в сборке нет)":`, a8_nobj ${memory.read(NB,false)}, минимальный запас ${worst} (${wcase?wcase[0]+": a8_nobj "+wcase[1]+", живой "+wcase[2]:"-"}), НАРУШЕНИЙ ${bad}`));
process.exit(bad?1:0);
