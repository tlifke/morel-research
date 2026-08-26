import fs from 'fs';
const html = fs.readFileSync(process.argv[2],'utf8');
const js = html.slice(html.indexOf('<script>')+8, html.lastIndexOf('</script>'));

function mkClassList(){ const s=new Set(); s.toggle=(c,on)=>{on?s.add(c):s.delete(c);}; return s; }
class El {
  constructor(tag){this.tag=tag;this.children=[];this._html='';this.classList=mkClassList();
    this.dataset={};this.onclick=null;this.checked=false;this._st=0;this._listeners={};}
  set className(v){this.classList=mkClassList(); String(v).split(/\s+/).filter(Boolean).forEach(c=>this.classList.add(c));}
  get className(){return [...this.classList].join(' ');}
  set innerHTML(v){this._html=String(v); if(v==='') this.children=[];}
  get innerHTML(){return this._html;}
  set textContent(v){this._text=v;} get textContent(){return this._text;}
  appendChild(c){this.children.push(c);return c;}
  querySelector(){return new El('input');}
  addEventListener(k,f){(this._listeners[k]=this._listeners[k]||[]).push(f);}
  fire(k){(this._listeners[k]||[]).forEach(f=>f());}
  get scrollTop(){return this._st;} set scrollTop(v){this._st=v;}
}
const els={};
for(const id of ['srcsL','srcsR','cats','docL','docR','barL','barR','syncbox']) els[id]=new El('div');
els.syncbox.checked = true;
global.document={getElementById:id=>els[id], createElement:t=>new El(t)};
global.requestAnimationFrame=f=>f();

eval(js + ";globalThis.__x={setAll,onlyPresent,onlyDiff,RAW,DIFFS,CATS,side,KEYS,diffSet};");
const {setAll,onlyPresent,onlyDiff,RAW,DIFFS,CATS,side,KEYS,diffSet}=globalThis.__x;
const N = KEYS.length, MODELS = KEYS.filter(k=>k!=='gold');

let fail=0;
const chk=(n,c,e='')=>{ if(!c){fail++;console.log('FAIL:',n,e);} else console.log('ok  :',n); };
const click=(w,k)=>els['srcs'+w].children.find(c=>c.textContent===k).onclick();

chk('gold is a source', KEYS.includes('gold'), KEYS.join(','));
chk('at least one model source', MODELS.length>=1, KEYS.join(','));
chk('L has '+N+' sources', els.srcsL.children.length===N, els.srcsL.children.length);
chk('R has '+N+' sources', els.srcsR.children.length===N, els.srcsR.children.length);
chk('L defaults gold', els.srcsL.children.find(c=>c.classList.has('on')).textContent==='gold');
chk('R defaults to a model', els.srcsR.children.find(c=>c.classList.has('on')).textContent===MODELS[0]);

for(const k of KEYS){ click('L',k); click('R',k); }
click('L',MODELS[MODELS.length-1]); click('R',MODELS[0]);
chk('L still '+N+' after clicks', els.srcsL.children.length===N, els.srcsL.children.length);
chk('R still '+N+' after clicks', els.srcsR.children.length===N, els.srcsR.children.length);
chk('L exactly one active', els.srcsL.children.filter(c=>c.classList.has('on')).length===1);
chk('R exactly one active', els.srcsR.children.filter(c=>c.classList.has('on')).length===1);
chk('panes independent',
  els.srcsL.children.find(c=>c.classList.has('on')).textContent===MODELS[MODELS.length-1]
  && els.srcsR.children.find(c=>c.classList.has('on')).textContent===MODELS[0],
  MODELS.length>1 ? '' : '(single sample: both panes share one model source)');
chk('cats stay 41', els.cats.children.length===41, els.cats.children.length);

chk('both docs rendered', els.docL.innerHTML.length>1000 && els.docR.innerHTML.length>1000);
setAll(0);
chk('none clears both', !els.docL.innerHTML.includes('<mark') && !els.docR.innerHTML.includes('<mark'));
setAll(1);
chk('all restores both', els.docL.innerHTML.includes('<mark') && els.docR.innerHTML.includes('<mark'));

click('L','gold'); click('R',MODELS[0]);
onlyDiff();
const pair = ['gold', MODELS[0]].sort(), dk = pair[0]+'|'+pair[1], d = diffSet();
chk('diff set non-empty', d && d.length>0, dk+' -> '+JSON.stringify(d));
chk('diff key order matches python', DIFFS[dk] !== undefined, Object.keys(DIFFS).join(','));
chk('diffSet resolves to that key', d === DIFFS[dk]);
chk('all pairs present', Object.keys(DIFFS).length === KEYS.length*(KEYS.length-1)/2,
    Object.keys(DIFFS).length+' for '+KEYS.length+' keys');
onlyPresent();
chk('present keeps marks', els.docL.innerHTML.includes('<mark'));

setAll(1);
for(const w of ['L','R']){
  const s = els['doc'+w].innerHTML.replace(/<[^>]*>/g,'').replace(/&amp;/g,'&').replace(/&lt;/g,'<');
  chk(w+' text identical to source', s===RAW, s.length+' vs '+RAW.length);
}

els.docL.scrollTop = 500; els.docL.fire('scroll');
chk('scroll syncs L->R', els.docR.scrollTop===500, els.docR.scrollTop);
els.syncbox.checked=false;
els.docL.scrollTop = 900; els.docL.fire('scroll');
chk('sync respects checkbox', els.docR.scrollTop===500, els.docR.scrollTop);

console.log(fail? '\n'+fail+' FAILURES' : '\nall passed');
process.exit(fail?1:0);
