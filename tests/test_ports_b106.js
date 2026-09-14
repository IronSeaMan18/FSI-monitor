const store={"fsi13_p":"[]"};  // saved state: NO ports selected
global.localStorage={getItem:k=>store[k]??null,setItem:(k,v)=>{store[k]=String(v)},removeItem:k=>{delete store[k]}};
const els={};
const mk=id=>els[id]||(els[id]={id,style:{},innerHTML:"",textContent:"",value:"",checked:false,classList:{add(){},remove(){},toggle(){}},addEventListener(){},remove(){},appendChild(){},querySelector:()=>mk("q"),querySelectorAll:()=>[]});
global.document={getElementById:id=>mk(id),createElement:()=>mk("new"),body:mk("body"),querySelector:()=>mk("q"),querySelectorAll:()=>[]};
global.window=global;
const V=[{name:"CAPE CORFU",imo:"9857432",flagCode:"CY",portId:"ESVGO",portName:"Vigo",etaISO:"2026-09-12T22:00",eta:"12 Sep, 22:00"},
         {name:"FURNESS VICTORIA",imo:"9640621",flagCode:"PA",portId:"ESGIJ",portName:"Gijón",etaISO:"2026-09-18T08:00",eta:"18 Sep, 08:00"},
         {name:"SEA EAGLE",imo:"9111111",flagCode:"LR",portId:"ESAVS",portName:"Avilés",etaISO:"2026-09-13T06:00",eta:"13 Sep, 06:00"}];
let nfetch=0;global.fetch=(u)=>{if(!/history|managers/.test(String(u)))nfetch++;return Promise.resolve({ok:true,json:()=>Promise.resolve(String(u).includes("history")?{vessels:{},meta:{runs:1}}:String(u).includes("managers")?{managers:{}}:{vessels:V,count:V.length})})};
global.setInterval=()=>0;global.setTimeout=(f,t)=>{if(t===undefined||t<100)f();return 0};global.alert=m=>console.log("  ALERT:",m);
global.AbortSignal={timeout:()=>({})};global.URL={createObjectURL:()=>""};global.Blob=class{};global.navigator={clipboard:{writeText(){}}};
process.on("unhandledRejection",e=>{console.log("UNHANDLED REJECTION:",e&&e.stack?e.stack.split("\n").slice(0,3).join("\n"):e)});
try{eval(require('fs').readFileSync(process.argv[2],'utf8')+';globalThis.S=S;globalThis.getF=getF;');}catch(e){console.log("SYNC THREW:",e.stack.split("\n").slice(0,3).join("\n"))}
setImmediate(()=>setImmediate(()=>setImmediate(async()=>{
  let pass=0,fail=0;const t=(n,c,x)=>{c?pass++:fail++;console.log((c?"  ok   ":"  FAIL ")+n+(c?"":"  <<"+x+">>"))};
  console.log("-- page load with saved ports=[] --");
  t("12 ports restored", S.ports.length===12, S.ports.length);
  t("restoration persisted", store["fsi13_p"]&&JSON.parse(store["fsi13_p"]).length===12);
  t("fetches issued", nfetch>0, nfetch);
  t("restore message survives fetchAll's log reset", S.logs.some(l=>l.includes("No ports were selected — restored all 12")), JSON.stringify(S.logs.slice(0,2)));
  t("vessels rendered", (els.tB.innerHTML.match(/<tr class/g)||[]).length>0);
  console.log("-- mid-session: user clicks None, then Refresh --");
  S.ports=[];render();
  t("None does NOT auto-restore", S.ports.length===0, S.ports.length);
  const before=nfetch; await fetchAll(); await new Promise(r=>setImmediate(r));
  t("Refresh with 0 ports issues no fetches", nfetch===before, nfetch-before);
  t("loading flag cleared (no stuck spinner)", S.loading===false);
  t("status line explains", S.logs.some(l=>l.includes("No ports selected — open + Add Ports")), JSON.stringify(S.logs));
  const txt=els.tB.innerHTML.replace(/<[^>]+>/g,"");
  t("table explains instead of 'No vessels match'", txt.includes("No ports selected")&&!txt.includes("No vessels match"), JSON.stringify(txt.slice(0,80)));
  console.log("-- recovery: pick Vigo, Refresh --");
  S.ports=["ESVGO"];await fetchAll();await new Promise(r=>setImmediate(r));
  t("fetches resume", nfetch>before, nfetch-before);
  t("rows back", (els.tB.innerHTML.match(/<tr class/g)||[]).length>0);
  console.log("");console.log(pass+" passed, "+fail+" failed");process.exit(fail?1:0);
  console.log("DATA FETCHES ISSUED:",nfetch);console.log("status line:",JSON.stringify(els.plog.innerHTML.slice(0,80)));console.log("saved fsi13_p now:",store["fsi13_p"]);console.log("S.flags =",JSON.stringify(S.flags),"| S.ports.length =",S.ports.length);
  console.log("S.combined.length =",S.combined.length,"| getF().length =",getF().length);
  console.log("table rows rendered:",(els.tB.innerHTML.match(/<tr/g)||[]).length,"| tB starts:",els.tB.innerHTML.slice(0,60));
  console.log("stats html length:",els.stats.innerHTML.length);
  console.log("sF (flag chips) html length:",els.sF.innerHTML.length);
})));
