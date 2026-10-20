// No browser dependency: exercise the shipped scripts across real history/storage boundaries.
const assert=require('node:assert/strict'), vm=require('node:vm'), fs=require('node:fs');
const scripts=JSON.parse(fs.readFileSync(0,'utf8'));
const rows=Array.from({length:85},(_,i)=>({id:'c'+i,title:'Memory '+i,month:i<50?'2026-10':'2026-09',created:'2026-10-01',last_chat:'2026-10-02',project_id:'g-p-'+(i%15),project_name:'Project '+(i%15),project_kind:'project',message_count:3,excerpt:'memory idea',html:'conversations/c'+i+'/overview.html'}));
const clone=x=>x==null?x:JSON.parse(JSON.stringify(x));
function browser({storageDisabled=false}={}){
 const store=new Map(),entries=[];let position=-1;
 const b={fetches:0,context:null};
 b.load=(url,kind='index',state=null,replace=false)=>{
  if(!replace){entries.splice(position+1);entries.push({url,state:clone(state)});position=entries.length-1}
  else{entries[position]={url,state:clone(state)}}
  const nodes={},events={},docEvents={};
  function node(value=''){return {value,textContent:'',innerHTML:'',disabled:false,children:[],addEventListener(k,fn){this[k]=fn},append(o){this.children.push(o)}}}
  for(const id of ['q','project','projects','all','month','role','branch','results','count','prev','next','full','status'])nodes[id]=node();
  nodes.role.value='user';nodes.branch.value='main';nodes.status.textContent='idle';
  const details=[{open:false,tagName:'DETAILS'},{open:false}],links=[{href:'../../index.html',getAttribute(){return this.href}},{href:'part-0002.html',getAttribute(){return this.href}}];
  const history={get state(){return entries[position].state},replaceState(s,t,u){entries[position]={url:u?new URL(u,entries[position].url).href:entries[position].url,state:clone(s)};if(u)ctx.location=new URL(entries[position].url)},pushState(s,t,u){const href=new URL(u,entries[position].url).href;entries.splice(position+1);entries.push({url:href,state:clone(s)});position++;ctx.location=new URL(href)}};
  const ctx={URL,URLSearchParams,AbortController,console,setTimeout,clearTimeout,ARCHIVE_ITEMS:rows,history,
   location:new URL(url),scrollY:0,requestAnimationFrame:fn=>fn(),scrollTo(x,y){ctx.scrollY=y},
   addEventListener(k,fn){(events[k]??=[]).push(fn)},
   sessionStorage:{getItem(k){if(storageDisabled)throw Error('blocked');return store.get(k)||null},setItem(k,v){if(storageDisabled)throw Error('blocked');store.set(k,v)}},
   navigator:{clipboard:{writeText:async()=>{}}},
   document:{currentScript:{src:new URL(kind==='index'?'index.js':'../../page.js',url).href},
    querySelector(s){return nodes[s.slice(1)]},
    querySelectorAll(s){if(s==='input,select')return [nodes.q,nodes.project,nodes.month,nodes.role,nodes.branch];if(s==='details')return details;if(s==='a[href]')return links;return []},
    getElementById(id){return id==='target'?{parentElement:details[0],querySelectorAll(){return [details[1]]},scrollIntoView(){ctx.scrollY=900}}:null},
    createElement(){return node()},addEventListener(k,fn){(docEvents[k]??=[]).push(fn)}},
   async fetch(url){b.fetches++;if(b.deferFetch)await new Promise(resolve=>{b.resumeFetch=resolve});const p=new URL(url).searchParams,start=Number(p.get('cursor'));const candidates=rows.filter(r=>!p.get('project')||r.project_id===p.get('project'));const results=candidates.slice(start,start+40).map(r=>({...r,message_count:undefined,message_id:r.id,role:'user',branch:'main',snippet:p.get('q')}));return {ok:true,json:async()=>({results,next_cursor:start+40<candidates.length?start+40:null,elapsed_seconds:0.01})}}
  };
  ctx.window=ctx;ctx.window.location=ctx.location;
  b.context=vm.createContext(ctx);b.nodes=nodes;b.links=links;b.details=details;b.events=events;
  b.fire=(event,arg={})=>{for(const fn of events[event]||[])fn(arg)};
  b.docFire=(event,arg={})=>{for(const fn of docEvents[event]||[])fn(arg)};
  vm.runInContext(kind==='index'?scripts.index:scripts.page,b.context);
  return b;
 };
 b.navigate=(url,kind='index')=>{const target=new URL(url,b.context.location).href;b.fire('pagehide');return b.load(target,kind)};
 b.reload=()=>{b.fire('pagehide');return b.load(entries[position].url,'index',entries[position].state,true)};
 b.back=()=>{b.fire('pagehide');position--;const e=clone(entries[position]);return b.load(e.url,'index',e.state,true)};
 b.forward=()=>{b.fire('pagehide');position++;const e=clone(entries[position]);return b.load(e.url,'index',e.state,true)};
 b.popBack=()=>{position--;b.context.location=new URL(entries[position].url);b.fire('popstate',{state:entries[position].state})};
 b.result=()=>new URL((b.nodes.results.innerHTML.match(/href="([^"]+)"/)||[])[1].replaceAll('&amp;','&'),b.context.location).href;
 return b;
}
const flush=async()=>{for(let i=0;i<4;i++)await new Promise(setImmediate)};
(async()=>{
 const b=browser().load('http://local/index.html?view=conversations');
 b.nodes.next.onclick();b.context.scrollTo(0,1200);
 const overview=b.result();
 b.navigate(overview,'page');
 b.navigate(b.links[0].href);assert.match(b.nodes.count.textContent,/第 2 \/ 3 页/);assert.equal(b.context.scrollY,1200);
 b.reload();assert.match(b.nodes.count.textContent,/第 2 \/ 3 页/);assert.equal(b.context.scrollY,1200);
 b.nodes.month.value='2026-10';b.nodes.month.onchange();assert.match(b.nodes.count.textContent,/共 50/);
 b.back();assert.equal(b.nodes.month.value,'');assert.match(b.nodes.count.textContent,/第 2 \/ 3 页/);
 b.forward();assert.equal(b.nodes.month.value,'2026-10');
 console.log('PASS catalog return, scroll, refresh, filter back/forward');
 const f=browser().load('http://local/index.html?view=conversations');f.nodes.q.value='memory';f.nodes.q.input();f.nodes.full.onclick();await flush();
 assert.match(f.nodes.count.textContent,/第 1 批/);f.nodes.next.onclick();await flush();assert.match(f.nodes.count.textContent,/第 2 批/);
 f.context.scrollTo(0,750);const result=f.result();const fetches=f.fetches;
 f.navigate(result,'page');f.navigate(f.links[0].href);await flush();assert.match(f.nodes.count.textContent,/第 2 批/);assert.equal(f.context.scrollY,750);assert.equal(f.fetches,fetches);
 f.nodes.prev.onclick();await flush();assert.match(f.nodes.count.textContent,/第 1 批/);
 f.nodes.role.value='all';f.nodes.role.onchange();f.back();await flush();assert.equal(f.nodes.role.value,'user');assert.match(f.nodes.count.textContent,/第 1 批/);
 console.log('PASS full-search return, batch previous/next, role history, cached results');
 const noStorage=browser({storageDisabled:true}).load('http://local/index.html?view=conversations');noStorage.nodes.next.onclick();const link=noStorage.result();noStorage.navigate(link,'page');noStorage.navigate(noStorage.links[0].href);assert.match(noStorage.nodes.count.textContent,/第 2 \/ 3 页/);
 console.log('PASS URL-based return when browser storage is blocked');
 const reading=browser().load('http://local/conversations/c0/part-0001.html#target','page');assert.equal(reading.context.scrollY,900);assert.equal(reading.details[0].open,true);reading.context.scrollTo(0,1500);reading.details[0].open=false;reading.fire('pagehide');
 const saved=clone(reading.context.history.state);reading.load(reading.context.location.href,'page',saved,true);assert.equal(reading.context.scrollY,1500);assert.equal(reading.details[0].open,false);
 console.log('PASS deep-link initial targeting and reading refresh position/details');
 const invalid=browser().load('http://local/index.html?page=9999&role=invalid&branch=invalid');assert.match(invalid.nodes.count.textContent,/第 3 \/ 3 页/);assert.equal(invalid.nodes.role.value,'user');
 console.log('PASS invalid/stale URL parameters are clamped');
 const pending=browser().load('http://local/index.html?view=conversations');pending.nodes.next.onclick();pending.nodes.q.value='memory';pending.nodes.q.input();pending.deferFetch=true;pending.nodes.full.onclick();await flush();pending.popBack();pending.resumeFetch();await flush();assert.match(pending.nodes.count.textContent,/第 1 \/ 3 页/);assert.equal(pending.nodes.q.value,'');assert.equal(pending.nodes.full.disabled,false);
 console.log('PASS browser back cancels an in-flight search without stale results');
 const early=browser().load('http://local/conversations/c0/part-0001.html#target','page');early.context.scrollTo(0,1500);early.fire('wheel');early.fire('pageshow',{persisted:false});assert.equal(early.context.scrollY,1500);early.fire('pagehide');const earlyState=clone(early.context.history.state);early.load(early.context.location.href,'page',earlyState,true);assert.equal(early.context.scrollY,1500);
 console.log('PASS late initial fragment restoration does not override manual scrolling');
 const grouped=browser().load('http://local/index.html');assert.match(grouped.nodes.count.textContent,/共 15 个分组/);grouped.nodes.next.onclick();assert.match(grouped.nodes.count.textContent,/第 2 \/ 2 页/);const selected=grouped.result();grouped.navigate(selected);assert.equal(grouped.nodes.project.value,'g-p-12');assert.match(grouped.nodes.count.textContent,/共 5 个会话/);const conversation=grouped.result();grouped.navigate(conversation,'page');grouped.navigate(grouped.links[0].href);assert.equal(grouped.nodes.project.value,'g-p-12');grouped.nodes.projects.onclick();assert.match(grouped.nodes.count.textContent,/第 2 \/ 2 页/);
 console.log('PASS paginated project directory -> project conversations -> reading -> original project page');
 const scoped=browser().load('http://local/index.html?view=conversations&project=g-p-2');scoped.nodes.q.value='memory';scoped.nodes.q.input();scoped.nodes.full.onclick();await flush();assert.match(scoped.nodes.count.textContent,/本批 6 处命中/);assert.equal(scoped.nodes.project.value,'g-p-2');
 console.log('PASS full-text search stays inside the original project ID');



})().catch(e=>{console.error(e);process.exitCode=1});
