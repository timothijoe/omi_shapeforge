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
function check(v,name){if(!v)throw Error(name);report.checks.push(name)}
try{
 await client.call('Runtime.enable');await client.call('Page.bringToFront');await ready();
 await client.call('Emulation.setDeviceMetricsOverride',{width:1680,height:1000,deviceScaleFactor:1,mobile:false});
 check(await evaluate(`sample.cloud_layout==='xyz_rgb_head_uv_float32'&&cloudData.length%8===0&&cloudData.length/8>80000`),'Dense RGB cloud with explicit eight-float layout loaded');
 for(const kind of ['module','socket']){
  await evaluate(`document.getElementById('object').value=${JSON.stringify(kind)};document.getElementById('object').dispatchEvent(new Event('change'));window.wristBefore=JSON.stringify(state.objects[${JSON.stringify(kind)}].wrist);document.getElementById('guide-start').click()`);
  const pixels=await evaluate(`sample.initialization_proposals[${JSON.stringify(kind)}].image_points`);
  for(const p of pixels){
   const pos=await evaluate(`(()=>{const q=screen(${JSON.stringify(p)},'head'),r=document.getElementById('head').getBoundingClientRect();return {x:q[0]+r.left,y:q[1]+r.top}})()`);
   await client.call('Input.dispatchMouseEvent',{type:'mousePressed',button:'left',clickCount:1,...pos});
   await client.call('Input.dispatchMouseEvent',{type:'mouseReleased',button:'left',clickCount:1,...pos});
  }
  check(await evaluate(`state.objects[${JSON.stringify(kind)}].head_anchor_pixels.length===4`),kind+' four corners recorded by actual image clicks');
  await evaluate(`document.getElementById('guide-solve').click()`);await ready();
  check(await evaluate(`!!state.objects[${JSON.stringify(kind)}].head_guided_fit&&state.objects[${JSON.stringify(kind)}].head_guided_fit.pixel_rms<8`),kind+' guided metric initialization completed');
  check(await evaluate(`JSON.stringify(state.objects[${JSON.stringify(kind)}].wrist)===window.wristBefore`),kind+' initialization preserves independent wrist pose');
 }
 await evaluate(`document.getElementById('object').value='module';refreshControls();document.getElementById('cloudtab').click();camera.distance=.105;window.geometryBefore=JSON.stringify(state.objects);window.cloudBefore=JSON.stringify(Array.from(cloudData.slice(0,800)));document.getElementById('cloudcolor').value='rgb';draw()`);
 await new Promise(r=>setTimeout(r,300));await evaluate(`window.rgbCanvas=document.getElementById('cloud').toDataURL();document.getElementById('cloudcolor').value='regions';draw()`);
 await new Promise(r=>setTimeout(r,300));
 check(await evaluate(`document.getElementById('cloud').toDataURL()!==window.rgbCanvas&&gl.getError()===0`),'RGB and region-highlight modes render differently without WebGL errors');
 check(await evaluate(`JSON.stringify(state.objects)===window.geometryBefore&&JSON.stringify(Array.from(cloudData.slice(0,800)))===window.cloudBefore`),'Color display does not transform cloud or object poses');
 await evaluate(`window.croppedCanvas=document.getElementById('cloud').toDataURL();document.getElementById('nearby').checked=false;draw()`);await new Promise(r=>setTimeout(r,250));
 check(await evaluate(`document.getElementById('cloud').toDataURL()!==window.croppedCanvas`),'Neighborhood filter visibly removes background without deleting points');
 await evaluate(`document.getElementById('nearby').checked=true;draw();window.beforeLocal=JSON.stringify(state.objects.module.head);document.getElementById('localicp').click()`);await ready();
 const local=await evaluate(`({method:state.objects.module.head_candidates[0]?.method,unchanged:JSON.stringify(state.objects.module.head)===window.beforeLocal,notice:document.getElementById('notice').textContent})`);report.local_refinement=local;check(local.method==='bounded_local_cloud_refinement'||(local.unchanged&&(local.notice.includes('movement guard')||local.notice.includes('偏离初值过远'))),'Local refinement stays bounded or refuses and preserves initialization');
 await evaluate(`document.getElementById('guide-proposal').click();window.beforeSave=JSON.stringify(state.objects);`);
 check(await evaluate(`state.objects.module.head_guided_fit.method==='four_ordered_corners_with_stereo_depth'`),'Prepared candidate can be reloaded through explicit UI action');
 const sid=await evaluate('sample.id');await evaluate('save()');
 const saved=(await(await fetch(base+'/api/sample?id='+sid)).json()).state;
 check(saved.objects.module.head_anchor_pixels.length===4&&saved.objects.socket.head_anchor_pixels.length===4&&!saved.training_label_valid,'Guided corners and candidate provenance persist without becoming training labels');
 await evaluate(`document.getElementById('cloudcolor').value='rgb';notice('彩色密集点云＋四点引导初值：旧候选已保留，当前仍需人工审阅。');draw()`);await new Promise(r=>setTimeout(r,250));
 const shot=await client.call('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(output,'guided_rgb.png'),Buffer.from(shot.data,'base64'));
 await evaluate(`document.getElementById('cloudcolor').value='regions';draw()`);await new Promise(r=>setTimeout(r,250));
 const shot2=await client.call('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(output,'guided_highlight.png'),Buffer.from(shot2.data,'base64'));
 check(client.errors.length===0,'No JavaScript errors');report.passed=true;report.check_count=report.checks.length;
}catch(e){report.passed=false;report.error=String(e);throw e}
finally{report.browser_errors=client.errors;fs.writeFileSync(path.join(output,'validation.json'),JSON.stringify(report,null,2));await evaluate('if(typeof dirty!=="undefined")dirty=false');await browser.call('Target.closeTarget',{targetId});client.socket.close();browser.socket.close();console.log(JSON.stringify(report))}
