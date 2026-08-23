import fs from 'fs';
const html = fs.readFileSync(process.argv[2],'utf8');
const js = html.slice(html.indexOf('<script>')+8, html.lastIndexOf('</script>'));

// minimal DOM
class El {
  constructor(tag){this.tag=tag;this.children=[];this._html='';this.classList=new Set();this.dataset={};this.onclick=null;this.onchange=null;this.checked=false;}
  set className(v){this.classList=new Set(String(v).split(/\s+/).filter(Boolean));}
  get className(){return [...this.classList].join(' ');}
  set innerHTML(v){this._html=String(v); this.children = v==='' ? [] : this.children;}
  get innerHTML(){return this._html;}
  set textContent(v){this._text=v;} get textContent(){return this._text;}
  appendChild(c){this.children.push(c); return c;}
  querySelector(){const e=new El('input'); e.onchange=null; return e;}
  get scrollTop(){return this._st||0;} set scrollTop(v){this._st=v;}
}
El.prototype.classList = null;
function mkClassList(){ const s=new Set(); s.toggle=(c,on)=>{on?s.add(c):s.delete(c);}; return s; }
const els = {};
for (const id of ['srcs','cats','doc','bar']) { const e=new El('div'); e.classList=mkClassList(); els[id]=e; }
global.document = {
  getElementById: id => els[id],
  createElement: t => { const e=new El(t); e.classList=mkClassList(); return e; }
};
eval(js + ";globalThis.__setAll=setAll;globalThis.__onlyPresent=onlyPresent;globalThis.__RAW=RAW;");
const setAll=globalThis.__setAll, onlyPresent=globalThis.__onlyPresent, RAW=globalThis.__RAW;

// --- assertions ---
let fail=0;
const chk=(name,cond,extra='')=>{ if(!cond){fail++;console.log('FAIL:',name,extra);} else console.log('ok  :',name); };

chk('4 source buttons after init', els.srcs.children.length===4, 'got '+els.srcs.children.length);
const clickSrc = k => els.srcs.children.find(c=>c.textContent===k).onclick();
clickSrc('r1');
chk('still 4 after clicking r1', els.srcs.children.length===4, 'got '+els.srcs.children.length);
clickSrc('r2'); clickSrc('gold'); clickSrc('r0'); clickSrc('r1');
chk('still 4 after 5 clicks', els.srcs.children.length===4, 'got '+els.srcs.children.length);
chk('exactly one active', els.srcs.children.filter(c=>c.classList.has('on')).length===1);
chk('active is r1', els.srcs.children.find(c=>c.classList.has('on')).textContent==='r1');
chk('41 category rows', els.cats.children.length===41, 'got '+els.cats.children.length);
clickSrc('gold');
chk('cats not duplicated on source switch', els.cats.children.length===41, 'got '+els.cats.children.length);
chk('doc rendered', els.doc.innerHTML.length>1000);
chk('doc has marks', els.doc.innerHTML.includes('<mark'));
setAll(0);
chk('none => no marks', !els.doc.innerHTML.includes('<mark'));
setAll(1);
chk('all => marks return', els.doc.innerHTML.includes('<mark'));
onlyPresent();
chk('onlyPresent keeps marks', els.doc.innerHTML.includes('<mark'));
// text integrity: strip tags, compare to RAW
const stripped = els.doc.innerHTML.replace(/<[^>]*>/g,'').replace(/&amp;/g,'&').replace(/&lt;/g,'<');
chk('rendered text == source text', stripped===RAW, 'len '+stripped.length+' vs '+RAW.length);
console.log(fail? '\n'+fail+' FAILURES' : '\nall passed');
process.exit(fail?1:0);
