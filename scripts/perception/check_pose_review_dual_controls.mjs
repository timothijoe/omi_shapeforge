// Exercise the real browser UI against an isolated annotation workspace.
// Requires an existing Chrome remote-debugging port; never uses production saves.
import fs from 'node:fs';
import path from 'node:path';

const args=Object.fromEntries(process.argv.slice(2).reduce((rows,s,i,a)=>i%2?rows:[...rows,[s.replace(/^--/,''),a[i+1]]],[]));
const base=args.url||'http://127.0.0.1:8877';
const output=args.output;
if(!output)throw Error('--output is required');
fs.mkdirSync(output,{recursive:true});
const inventory=await(await fetch(base+'/api/index')).json();
if(!inventory.output.endsWith('/validation_workspace'))throw Error('Refusing to modify non-test annotations');
const version=await(await fetch(`http://127.0.0.1:${args['debug-port']||9227}/json/version`)).json();

async function connect(url){
 const socket=new WebSocket(url);await new Promise(r=>socket.addEventListener('open',r,{once:true}));
 let serial=0;const pending=new Map(),errors=[];
 socket.onmessage=e=>{const m=JSON.parse(e.data);if(m.method==='Runtime.exceptionThrown')errors.push(m.params);if(m.id){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(m.error):p.resolve(m.result)}};
 return {socket,errors,call:(method,params={})=>new Promise((resolve,reject)=>{const id=++serial;pending.set(id,{resolve,reject});socket.send(JSON.stringify({id,method,params}))})};
}

const browser=await connect(version.webSocketDebuggerUrl);
const {targetId}=await browser.call('Target.createTarget',{url:base,background:true});
const pages=await(await fetch(`http://127.0.0.1:${args['debug-port']||9227}/json`)).json();
const client=await connect(pages.find(p=>p.id===targetId).webSocketDebuggerUrl);
async function evaluate(expression){const r=await client.call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value}
async function ready(expression='typeof state!=="undefined" && !!state && !busy && imgs.wrist.naturalWidth>0'){
 for(let i=0;i<140;i++){if(await evaluate(expression))return;await new Promise(r=>setTimeout(r,100))}throw Error('Timeout: '+expression);
}
const report={checks:[],production_annotations_modified:false};
function check(value,name){if(!value)throw Error(name);report.checks.push(name)}
try{
 await client.call('Runtime.enable');await ready();
 await client.call('Emulation.setDeviceMetricsOverride',{width:1680,height:1000,deviceScaleFactor:1,mobile:false});
 check(await evaluate(`document.querySelectorAll('#head-sliders input[type=range]').length===6 && document.querySelectorAll('#wrist-sliders input[type=range]').length===6 && !document.getElementById('frame')`),'Two separate six-axis banks, no coordinate-switch dropdown');
 check(await evaluate(`['head-controls','wrist-controls'].every(id=>{const r=document.getElementById(id).getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight})`),'Both adjustment banks visible in the same viewport');
 await evaluate(`window.initialTestState=clone(state);window.initialCloudSample=Array.from(cloudData.slice(0,600));window.initialRight=JSON.stringify(state.objects.module.wrist);window.initialSocket=JSON.stringify(state.objects.socket);window.initialExtrinsic=JSON.stringify(state.T_wrist_from_head);`);
 for(let i=0;i<6;i++){
  check(await evaluate(`(()=>{const n=document.getElementById('head-num${i}'),old=currentT('head');n.focus();n.value=vec(old)[${i}]+${i<3?1:2};n.dispatchEvent(new Event('input'));return JSON.stringify(currentT('head'))!==JSON.stringify(old)&&JSON.stringify(state.objects.module.wrist)===window.initialRight&&JSON.stringify(state.objects.socket)===window.initialSocket&&JSON.stringify(state.T_wrist_from_head)===window.initialExtrinsic})()`),`Head axis ${i} updates only module point-cloud pose`);
 }
 await evaluate(`window.changedHead=JSON.stringify(state.objects.module.head);`);
 for(let i=0;i<6;i++){
  check(await evaluate(`(()=>{const n=document.getElementById('wrist-num${i}'),old=currentT('wrist');n.focus();n.value=vec(old)[${i}]+${i<3?.5:1};n.dispatchEvent(new Event('input'));return JSON.stringify(currentT('wrist'))!==JSON.stringify(old)&&JSON.stringify(state.objects.module.head)===window.changedHead&&JSON.stringify(state.objects.socket)===window.initialSocket&&JSON.stringify(state.T_wrist_from_head)===window.initialExtrinsic})()`),`Wrist axis ${i} updates only module image pose`);
 }
 check(await evaluate(`JSON.stringify(Array.from(cloudData.slice(0,600)))===JSON.stringify(window.initialCloudSample)`),'Raw displayed point cloud remains fixed');
 check(await evaluate(`(()=>{const lo=document.getElementById('wrist-range0').min;document.getElementById('head-precision').value='coarse';document.getElementById('head-precision').dispatchEvent(new Event('change'));return +document.getElementById('head-range0').max-(+document.getElementById('head-range0').min)===300&&document.getElementById('wrist-range0').min===lo})()`),'Coarse/fine range is independent per bank');
 check(await evaluate(`(()=>{const right=JSON.stringify(state.objects.module.wrist);document.getElementById('head-reset').click();return JSON.stringify(state.objects.module.head)===JSON.stringify(window.initialTestState.objects.module.head)&&JSON.stringify(state.objects.module.wrist)===right})()`),'Reset restores only the selected frame to its load-time pose');
 await evaluate(`document.getElementById('undo').click();window.editedModule=JSON.stringify(state.objects.module);document.getElementById('object').value='socket';document.getElementById('object').dispatchEvent(new Event('change'));`);
 check(await evaluate(`document.getElementById('head-title').textContent.includes('插座')&&document.getElementById('wrist-title').textContent.includes('插座')`),'Both bank labels follow the selected object');
 for(let f of ['head','wrist']){
  check(await evaluate(`(()=>{const n=document.getElementById('${f}-num0');n.value=+n.value+.3;n.dispatchEvent(new Event('input'));return JSON.stringify(state.objects.module)===window.editedModule})()`),`Socket ${f} adjustment does not alter module`);
 }
 const expected=await evaluate('JSON.stringify(state.objects)'),sid=await evaluate('sample.id');
 await evaluate('save()');
 const stored=(await(await fetch(base+'/api/sample?id='+sid)).json()).state;
 check(JSON.stringify(stored.objects)===expected,'Save persists both pose banks and both objects');
 await evaluate(`document.getElementById('next').click()`);await ready(`!busy && sample.id!==${JSON.stringify(sid)}`);
 await evaluate(`document.getElementById('prev').click()`);await ready(`!busy && sample.id===${JSON.stringify(sid)}`);
 check(await evaluate(`JSON.stringify(state.objects)===${JSON.stringify(expected)}`),'Navigating away and back restores all independent poses');
 await evaluate(`document.getElementById('object').value='module';document.getElementById('object').dispatchEvent(new Event('change'));window.beforeMap=JSON.stringify(state.objects);document.getElementById('derive').click();`);
 check(await evaluate('JSON.stringify(state.objects)===window.beforeMap'),'Deriving extrinsic does not overwrite either pose bank');
 await evaluate(`const n=document.getElementById('extrinsic-num0');n.value=+n.value+2;n.dispatchEvent(new Event('input'));`);
 check(await evaluate('JSON.stringify(state.objects)===window.beforeMap'),'Editing extrinsic does not implicitly overwrite either pose bank');
 await evaluate(`document.getElementById('propagate').click()`);
 check(await evaluate(`JSON.stringify(state.objects.module.head)===JSON.stringify(JSON.parse(window.beforeMap).module.head)&&JSON.stringify(state.objects.module.wrist)!==JSON.stringify(JSON.parse(window.beforeMap).module.wrist)`),'Only explicit apply replaces wrist projection');
 await evaluate(`document.getElementById('undo').click()`);
 check(await evaluate('JSON.stringify(state.objects)===window.beforeMap'),'Undo restores the independent fits after explicit apply');
 await evaluate(`state.objects.module.wrist=null;refreshControls();window.headBeforeInit=JSON.stringify(state.objects.module.head);document.getElementById('wrist-initialize').click();`);
 check(await evaluate(`!!state.objects.module.wrist&&JSON.stringify(state.objects.module.head)===window.headBeforeInit`),'Missing wrist pose can be initialized without changing head pose');
 // Restore only the isolated test page for a representative screenshot.
 await evaluate(`state=clone(window.initialTestState);loadedPoses=clone(state.objects);dirty=false;refreshControls();document.getElementById('head-precision').value='fine';refreshBank('head');document.getElementById('zoomtarget').click();notice('左右各六轴：左调点云位置，右调像素匹配。两组独立保存；原始点云固定。');`);
 await new Promise(r=>setTimeout(r,300));
 await client.call('Page.bringToFront');
 const screenshot=await client.call('Page.captureScreenshot',{format:'png'});
 fs.writeFileSync(path.join(output,'dual_controls.png'),Buffer.from(screenshot.data,'base64'));
 check(client.errors.length===0,'No browser JavaScript exceptions');
 report.passed=true;report.check_count=report.checks.length;
}catch(e){report.passed=false;report.error=String(e);throw e}
finally{
 report.browser_errors=client.errors;fs.writeFileSync(path.join(output,'validation.json'),JSON.stringify(report,null,2));
 await evaluate('if(typeof dirty!=="undefined")dirty=false');
 await browser.call('Target.closeTarget',{targetId});client.socket.close();browser.socket.close();console.log(JSON.stringify(report));
}
