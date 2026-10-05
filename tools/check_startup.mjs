// Opt-in browser/WebGL checks: npm install playwright in a separate QA directory.
// PLAYWRIGHT_MODULE may point to that installation's index.mjs.
import assert from 'node:assert/strict';
import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const {chromium}=await import(process.env.PLAYWRIGHT_MODULE||'playwright');
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../omasteamdeck/assets/startup');
const types={'.js':'text/javascript','.css':'text/css','.html':'text/html'};
const server=http.createServer(async(req,res)=>{
  const name=new URL(req.url,'http://localhost').pathname;
  const file=path.resolve(root,'.'+(name==='/'?'/index.html':name));
  if(!file.startsWith(root+path.sep)){res.writeHead(403).end();return;}
  try{const data=await fs.readFile(file);res.setHeader('Content-Type',types[path.extname(file)]||'text/plain');res.end(data);}
  catch{res.writeHead(404).end();}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const origin=`http://127.0.0.1:${server.address().port}`;
const browser=await chromium.launch({executablePath:process.env.CHROMIUM_BIN||undefined,headless:true,
  // Software WebGL for repeatable browser QA only; production sets no GPU flags.
  args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try{
  const page=await browser.newPage({viewport:{width:1280,height:800},deviceScaleFactor:1});
  const failures=[],external=[];
  page.on('pageerror',e=>failures.push(e.message));
  page.on('request',r=>{if(!r.url().startsWith(origin)&&!r.url().startsWith('data:'))external.push(r.url());});
  const ready=()=>page.waitForFunction(()=>window.omaflowStatus?.ready);
  const disposed=()=>page.waitForFunction(()=>window.omaflowStatus?.disposed);
  await page.goto(origin);await ready();
  const status=await page.evaluate(()=>window.omaflowStatus);
  assert.equal(status.renderer,'three-webgl');assert.equal(status.drawCalls,2);
  assert(status.triangles>0&&status.triangles<10000);assert.equal(status.error,null);
  await page.waitForFunction(()=>document.body.classList.contains('wordmark'));
  await disposed();assert.equal(await page.evaluate(()=>window.omaflowStatus.finished),true);
  console.log('PASS WebGL geometry, wordmark, timed completion and disposal',status);
  for(const key of ['Enter','Escape']){
    await page.goto(origin);await ready();await page.keyboard.press(key);await disposed();
  }
  await page.goto(origin);await ready();await page.locator('#skip').click();await disposed();
  console.log('PASS Enter, Escape and pointer skip');
  await page.emulateMedia({reducedMotion:'reduce'});await page.goto(origin);await ready();
  assert(await page.locator('body').evaluate(el=>el.classList.contains('reduced')));await disposed();
  await page.emulateMedia({reducedMotion:'no-preference'});
  console.log('PASS system reduced-motion preference');
  await page.goto(origin+'?preview=1&frame=1.7');await ready();
  if(process.env.STARTUP_SCREENSHOT)await page.screenshot({path:process.env.STARTUP_SCREENSHOT});
  await page.evaluate(()=>document.querySelector('canvas').getContext('webgl2').getExtension('WEBGL_lose_context').loseContext());
  await disposed();assert.equal(await page.evaluate(()=>window.omaflowStatus.error),'WebGL context lost');
  console.log('PASS lost WebGL context exits safely');
  const noGL=await browser.newPage();
  await noGL.addInitScript(()=>{const original=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(kind,...args){return kind.includes('webgl')?null:original.call(this,kind,...args);};});
  await noGL.goto(origin);await noGL.waitForFunction(()=>window.omaflowStatus?.disposed);
  assert(await noGL.evaluate(()=>Boolean(window.omaflowStatus.error)));
  await noGL.close();assert.deepEqual(failures,[]);assert.deepEqual(external,[]);
  console.log('PASS unavailable WebGL fallback; no external resource requests or uncaught errors');
}finally{await browser.close();await new Promise(resolve=>server.close(resolve));}
