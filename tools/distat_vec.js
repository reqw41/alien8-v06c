#!/usr/bin/env node
// Длительность КАЖДОГО di-блока по месту его открытия (такты по слотам шины, cpu.vcycles).
// Нужен, чтобы сверить оценки vec_di_budget с реальностью: любой блок длиннее кадра (59904
// такта = 29952 тика ВИ53) гарантированно теряет обратный ход, а блок, чья оценка МЕНЬШЕ
// фактической длительности, теряет его случайно (это и ловит счётчик «обратный ход на di»).
//   node tools/distat_vec.js build/alien8_vec.r0m build/alien8_vec.sld <итераций> [комнаты|start] [inputs.txt]
// Комнаты — список через запятую, «start» = стартовая (по умолчанию start,104,39,56,88,48).
// Как в profile_vec.js: A8GAG=1 гасит seed_3 += mem[seed_2] (иначе сборки играют разный сценарий),
// номер комнаты подменяется в САМОЙ записи поля +8 объектов 0 и 1 в фазе init.
"use strict";
const fs=require("fs"),vm=require("vm");
const base="/Users/boris/projects/vector06js";
const [ROM,SLD,NS,ROOMS,INPUTS]=process.argv.slice(2); const N=+NS||200;
const LAG=+(process.env.A8_LAG||1);
const IRQDROP=!!process.env.A8_IRQDROP;
const L={},lab=[];
for(const l of fs.readFileSync(SLD,"latin1").split("\n")){const p=l.split("|");if(p.length>=8&&p[6]==="L"){const n=p[7].split(",")[1];if(n&&!(n in L)){L[n]=+p[5];lab.push([+p[5],n]);}}}
lab.sort((a,b)=>a[0]-b[0]);
const nameOf=a=>{let lo=0,hi=lab.length-1,r=-1;while(lo<=hi){const m=(lo+hi)>>1;if(lab[m][0]<=a){r=m;lo=m+1;}else hi=m-1;}
  return r<0?"?":lab[r][1]+(a>lab[r][0]?"+"+(a-lab[r][0]):"");};
const SEED2HI=L.seed_2+1, ROOM=L.curr_room_attrib, VKBD=L.vkbd, OBJ=L.graphic_objs_tbl;
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
const IMG=new Uint8Array(fs.readFileSync(ROM)).subarray(0,0x10000);
const rd=a=>memory.bytes[memory.tobank(a&0xffff)];
const KEYS={shift:[0,0],z:[0,1],x:[0,2],c:[0,3],v:[0,4],a:[1,0],s:[1,1],d:[1,2],f:[1,3],g:[1,4],q:[2,0],w:[2,1],e:[2,2],r:[2,3],t:[2,4],
  "1":[3,0],"2":[3,1],"3":[3,2],"4":[3,3],"5":[3,4],"0":[4,0],"9":[4,1],"8":[4,2],"7":[4,3],"6":[4,4],p:[5,0],o:[5,1],i:[5,2],u:[5,3],y:[5,4],
  enter:[6,0],l:[6,1],k:[6,2],j:[6,3],h:[6,4],space:[7,0],sym:[7,1],m:[7,2],n:[7,3],b:[7,4]};
const VKEYS={z:[7,0x04],x:[7,0x01],a:[4,0x02],q:[6,0x02],"0":[2,0x01],space:[7,0x80]};
const inputs={}; if(INPUTS&&fs.existsSync(INPUTS))for(const l of fs.readFileSync(INPUTS,"utf8").split("\n")){const m=l.trim().match(/^(\d+)\s+(\S+)\s+(down|up)/i);if(m)(inputs[+m[1]+LAG]=inputs[+m[1]+LAG]||[]).push([m[2].toLowerCase(),m[3].toLowerCase()==="down"]);}
const stat=new Map();   // адрес di -> {n, max, sum, mrg, msum, est}
const est=new Map();    // адрес di -> {n, sum, sum2, halt} — оценка блока (DE на входе vec_di_budget)
const VDB=L.vec_di_budget, FRAME=29952;  // тиков ВИ53 в кадре

function runRoom(room){
  memory.init_from_array(IMG,0);memory.detach_boot&&memory.detach_boot();
  cpu.pc=0;cpu.sp=0xBC00;cpu.iff=false; for(let r=0;r<8;r++)keyboard.matrix[r]=0;
  const ow=memory.write.bind(memory); const poke=(a,v)=>ow(a&0xffff,v&0xff,false);
  if(VKBD!==undefined)for(let r=0;r<8;r++)ow(VKBD+r,0xFF,false);
  const rows=new Uint8Array(8).fill(0xFF);
  const key=(k,down)=>{if(VKBD===undefined){const v=VKEYS[k];if(!v)return;const [r,b]=v;if(down)keyboard.matrix[r]|=b;else keyboard.matrix[r]&=~b;return;}
    const [r,b]=KEYS[k];if(down)rows[r]&=~(1<<b);else rows[r]|=(1<<b);poke(VKBD+r,rows[r]);};
  if(process.env.A8GAG){const s3=L.seed_3&0xff,s3h=(L.seed_3>>8)&0xff;
    const pat=[0x3A,s3,s3h,0x86,0x85,0x84,0x32,s3,s3h];let at=-1;
    for(let a=0x100;a<0xF000&&at<0;a++){let ok=true;for(let i=0;i<pat.length;i++)if(rd(a+i)!==pat[i]){ok=false;break;}if(ok)at=a;}
    if(at<0)throw new Error("не нашёл seed_3 += mem[seed_2]");ow(at+3,0x00,false);}
  let phase="menu",iter=0;
  memory.write=function(a,w,s){a&=0xffff;
    if(phase==="menu"&&cpu.pc===SYNC){poke(L.seed_1,0x34);poke(L.seed_1+1,0x12);poke(L.seed_2,0x78);poke(L.seed_2+1,0x56);poke(L.seed_3,0x9A);phase="init";}
    if(room!==null&&phase==="init"&&(a===OBJ+8||a===OBJ+40))w=room;
    if(a===ROOM&&phase==="init"&&w!==0){phase="game";key("0",false);}
    if(a===SEED2HI&&phase==="game"){iter++;for(const [k,d] of (inputs[iter]||[]))key(k,d);}
    return ow(a,w,s);};
  for(let f=0;f<60;f++)v06c.oneInterrupt(true); key("0",true);
  let guard=0; while(phase!=="game"&&guard++<3000)v06c.oneInterrupt(true);
  if(phase!=="game")return null;
  const start=iter; let curEst=0,frc=0,steps=0,tacc=0,tot=0,diAt=-1,diT=0,frames=0,lost=0,lostAt=new Map(),pendEst=0,pendHalt=0;
  while(iter-start<N&&steps<2e8){
    if(frc>=59904){frc-=59904;frames++;if(!cpu.iff){lost++;if(diAt>=0)lostAt.set(diAt,(lostAt.get(diAt)||0)+1);}
      // A8_IRQDROP=1 — модель железа: прерывание не защёлкивается, кадр под di теряется насовсем.
      if(!(IRQDROP&&!cpu.iff)){v06c.irq=true;v06c.checkInterrupt();}}
    const pc=cpu.pc, op=rd(pc);
    if(pc===VDB){pendEst=(cpu.regs[2]<<8)|cpu.regs[3];}                  // оценка блока в тиках ВИ53 (DE)
    if(op===0xF3&&cpu.iff){diAt=pc;diT=tot;
      const e=est.get(pc)||{n:0,sum:0,sum2:0,halt:0};e.n++;e.sum+=pendEst;e.sum2+=pendEst*pendEst;e.halt+=pendHalt;est.set(pc,e);pendHalt=0;curEst=pendEst;}
    if(cpu.last_opcode===0x76)pendHalt+=cpu.vcycles;          // halt перед di = ожидание кадра
    const c=(cpu.instruction(),cpu.vcycles);steps++;tot+=c;frc+=c;
    tacc+=c;if(tacc>1){const tn=tacc>>1;tacc-=tn*2;timer.Count(tn);}
    if(cpu.last_opcode===0xFB&&diAt>=0){                     // ei — блок закрыт
      const d=tot-diT, s=stat.get(diAt)||{n:0,max:0,sum:0,mrg:1e9,msum:0,est:0};
      s.n++;s.sum+=d;if(d>s.max)s.max=d;
      const mg=2*curEst-d;if(mg<s.mrg)s.mrg=mg;s.msum+=mg;s.est+=2*curEst;stat.set(diAt,s);diAt=-1;}
    if(cpu.last_opcode===0xd3)io.commit();
  }
  return {iters:iter-start,frames,lost,lostAt};
}
const rooms=(ROOMS||"start,104,39,56,88,48").split(",").map(s=>s.trim()==="start"?null:+s.trim());
let tf=0,tl=0; const allLost=new Map();
for(const r of rooms){const s=runRoom(r);if(!s){console.log("не дошли:",r===null?"start":r);continue;}
  tf+=s.frames;tl+=s.lost;for(const [k,v] of s.lostAt)allLost.set(k,(allLost.get(k)||0)+v);}
console.log(`комнаты: ${rooms.map(r=>r===null?"start":r).join(",")}${INPUTS?" + "+INPUTS:""}`);
console.log(`кадров ${tf}, обратный ход пришёлся на di: ${tl}`);
for(const [k,v] of [...allLost].sort((a,b)=>b[1]-a[1]))console.log(`  потери в блоке ${k.toString(16)} (${nameOf(k)}): ${v}`);
console.log("\nоценка блока и halt (модель: если фаза кадра равномерна, E[halt] = оценка^2/(2*кадр) тактов)");
console.log("блок                вызовов  средн.оценка  halt/вызов(такт)  модель E[halt]  всего halt(такт)");
for(const [a,e] of est){const mean=e.sum/e.n, mod=e.sum2/e.n/(2*FRAME)*2;  // *2: тик -> такт
  console.log(`${(a.toString(16)+" "+nameOf(a)).padEnd(20)} ${String(e.n).padStart(7)} ${mean.toFixed(0).padStart(13)} ${(e.halt/e.n).toFixed(0).padStart(17)} ${mod.toFixed(0).padStart(15)} ${e.halt.toFixed(0).padStart(17)}`);}
console.log("\nблок (адрес di)        вызовов   макс.тактов  макс.тиков ВИ53   средн.тактов  запас оценки: мин  средн.  средн.оценка/факт");
for(const [a,s] of [...stat].sort((x,y)=>y[1].max-x[1].max))
  console.log(`${(a.toString(16)+" "+nameOf(a)).padEnd(28)} ${String(s.n).padStart(8)} ${String(s.max).padStart(12)} ${String(Math.ceil(s.max/2)).padStart(14)} ${(s.sum/s.n).toFixed(0).padStart(14)}  ${String(s.mrg).padStart(9)} ${(s.msum/s.n).toFixed(0).padStart(7)}  ${(s.est/s.sum).toFixed(3).padStart(8)}`);
