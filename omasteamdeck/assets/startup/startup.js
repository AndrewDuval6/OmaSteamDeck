import * as THREE from './vendor/three.module.js';
import {mark as contours} from './mark.js';

const params=new URLSearchParams(location.search);
const reduced=params.get('motion')==='0'||matchMedia('(prefers-reduced-motion: reduce)').matches;
const preview=params.get('preview')==='1';
const fixture=params.get('frame');
const status={ready:false,finished:false,disposed:false,renderer:'three-webgl',version:THREE.REVISION,drawCalls:0,triangles:0,error:null};
window.omaflowStatus=status;
let renderer,scene,camera,mark,bridge,started,animation,lastPaint=-Infinity,finished=false;
if(window.qt?.webChannelTransport&&!window.QWebChannel){
  await new Promise((resolve,reject)=>{const script=document.createElement('script');script.src='qrc:///qtwebchannel/qwebchannel.js';script.onload=resolve;script.onerror=reject;document.head.appendChild(script);});
}
let readinessResolve;
const bridgeReady=new Promise(resolve=>{readinessResolve=resolve});
if(window.qt?.webChannelTransport&&window.QWebChannel){
  new QWebChannel(qt.webChannelTransport,channel=>{bridge=channel.objects.startup;readinessResolve();});
}else readinessResolve();
const notify=(name,...args)=>bridgeReady.then(()=>bridge?.[name]?.(...args));
const clamp=value=>Math.max(0,Math.min(1,value));
const ease=value=>1-Math.pow(1-clamp(value),3);
function trace(commands,path){
  for(const [op,...v] of commands){
    const xy=[];for(let i=0;i<v.length;i+=2)xy.push((v[i]-90)/45,(90-v[i+1])/45);
    if(op==='M')path.moveTo(...xy);else if(op==='L')path.lineTo(...xy);else if(op==='C')path.bezierCurveTo(...xy);else path.closePath();
  }
  return path;
}
function dispose(){
  if(status.disposed)return;
  status.disposed=true;
  renderer?.setAnimationLoop(null);
  scene?.traverse(object=>{object.geometry?.dispose();for(const material of [].concat(object.material||[]))material.dispose();});
  scene?.userData.reflection?.dispose();renderer?.dispose();renderer?.forceContextLoss();
}
async function finish(){
  if(finished||status.disposed)return;finished=true;status.finished=true;
  document.body.classList.add('leaving');
  if(!reduced)await new Promise(resolve=>setTimeout(resolve,280));
  dispose();notify('complete');
  window.dispatchEvent(new CustomEvent('omaflow-complete'));
}
window.omaflowFinish=finish;
window.omaflowDispose=dispose;
const skip=document.querySelector('#skip');
if(preview){skip.textContent='↻  Replay startup';skip.setAttribute('aria-label','Replay startup');}
skip.addEventListener('click',preview?()=>location.reload():finish);
addEventListener('keydown',event=>{if(['Enter','Escape',' '].includes(event.key)){event.preventDefault();finish();}});
addEventListener('pagehide',dispose);
addEventListener('visibilitychange',()=>{if(document.hidden)renderer?.setAnimationLoop(null);else if(!finished&&!status.disposed&&!reduced&&fixture===null)renderer?.setAnimationLoop(animation);});
try{
  document.body.classList.toggle('reduced',reduced);
  renderer=new THREE.WebGLRenderer({antialias:true,alpha:true,powerPreference:'low-power'});
  // Render at native Deck resolution even on a high-DPI desktop.
  renderer.setPixelRatio(Math.min(devicePixelRatio,1));renderer.setSize(innerWidth,innerHeight);
  renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.15;
  document.querySelector('#scene').appendChild(renderer.domElement);
  renderer.domElement.addEventListener('webglcontextlost',()=>{if(!finished&&!status.disposed){status.error='WebGL context lost';notify('failed',status.error);finish();}});
  scene=new THREE.Scene();camera=new THREE.PerspectiveCamera(35,innerWidth/innerHeight,.1,50);
  scene.add(new THREE.HemisphereLight(0xc3dcff,0x101822,.65));
  const key=new THREE.DirectionalLight(0xfff3e6,2);key.position.set(-3,5,6);scene.add(key);
  const rim=new THREE.DirectionalLight(0x74b9ff,3);rim.position.set(4,1,-2);scene.add(rim);
  const fill=new THREE.DirectionalLight(0xd7deff,.45);fill.position.set(0,-3,3);scene.add(fill);
  const shape=trace(contours.outer,new THREE.Shape());shape.holes=contours.holes.map(commands=>trace(commands,new THREE.Path()));
  const geometry=new THREE.ExtrudeGeometry(shape,{depth:.32,steps:1,curveSegments:24,bevelEnabled:true,bevelSegments:3,bevelThickness:.035,bevelSize:.035});
  geometry.translate(0,0,-.16);
  // Bend the solid through depth; transform normals with the same deformation.
  // This keeps the small vector silhouette while light travels over its surface.
  const positions=geometry.attributes.position,normals=geometry.attributes.normal;
  const normal=new THREE.Vector3();
  for(let i=0;i<positions.count;i++){
    const x=positions.getX(i),y=positions.getY(i);
    const bend=.13*Math.sin(x*1.7)+.09*Math.cos(y*2-x);
    const dx=.221*Math.cos(x*1.7)+.09*Math.sin(y*2-x),dy=-.18*Math.sin(y*2-x);
    positions.setZ(i,positions.getZ(i)+bend);
    normal.fromBufferAttribute(normals,i);normal.set(normal.x-dx*normal.z,normal.y-dy*normal.z,normal.z).normalize();
    normals.setXYZ(i,normal.x,normal.y,normal.z);
  }
  geometry.computeBoundingSphere();
  // A tiny procedural studio environment gives metal real reflected light bands.
  const environment=document.createElement('canvas');environment.width=256;environment.height=128;
  const ctx=environment.getContext('2d');const gradient=ctx.createLinearGradient(0,0,0,128);
  gradient.addColorStop(0,'#7795b8');gradient.addColorStop(.48,'#20364d');gradient.addColorStop(1,'#080c15');
  ctx.fillStyle=gradient;ctx.fillRect(0,0,256,128);ctx.fillStyle='#ecf4ff';ctx.fillRect(28,12,34,70);
  ctx.fillStyle='#aacbff';ctx.fillRect(173,23,14,89);ctx.fillStyle='#ffffff';ctx.fillRect(70,12,104,6);
  const source=new THREE.CanvasTexture(environment);source.mapping=THREE.EquirectangularReflectionMapping;
  const pmrem=new THREE.PMREMGenerator(renderer);const reflection=pmrem.fromEquirectangular(source);
  scene.environment=reflection.texture;source.dispose();pmrem.dispose();
  scene.userData.reflection=reflection;
  const material=new THREE.MeshStandardMaterial({color:0xd8e1ee,metalness:.78,roughness:.28,envMapIntensity:1.2});
  mark=new THREE.Mesh(geometry,material);mark.scale.setScalar(.49);mark.position.y=.57;scene.add(mark);
  // Real curved geometry for the softly lit horizon, with no postprocessing pass.
  const horizon=new THREE.Mesh(new THREE.TorusGeometry(7,.011,4,100),new THREE.MeshBasicMaterial({color:0x80bce9,transparent:true,opacity:.10}));
  horizon.position.set(0,-8.1,-3);horizon.rotation.x=.26;scene.add(horizon);
  function draw(time){
    const progress=reduced?1:ease(time/2.15);
    mark.rotation.y=THREE.MathUtils.lerp(-1.02,-.34,progress);
    mark.rotation.x=THREE.MathUtils.lerp(.20,-.075,progress);
    mark.rotation.z=THREE.MathUtils.lerp(-.10,0,progress);
    mark.position.y=.57+(reduced?0:Math.sin(time*1.6)*.035);
    camera.position.set(THREE.MathUtils.lerp(.4,0,progress),.1,THREE.MathUtils.lerp(8.3,7.1,progress));camera.lookAt(0,0,0);
    renderer.render(scene,camera);
    status.drawCalls=renderer.info.render.calls;status.triangles=renderer.info.render.triangles;
    document.body.classList.toggle('wordmark',reduced||time>.8);
    document.querySelector('#loader span').style.width=`${Math.min(100,time/3.1*100)}%`;
  }
  window.omaflowRenderAt=time=>{renderer.setAnimationLoop(null);draw(time);};
  draw(fixture===null?(reduced?2.2:0):Number(fixture));status.ready=true;
  notify('ready');window.dispatchEvent(new CustomEvent('omaflow-ready'));
  animation=now=>{
    if(finished||document.hidden)return;
    if(started===undefined)started=now;
    if(now-lastPaint<1000/30)return;lastPaint=now;
    const time=(now-started)/1000;draw(time);
    if(time>=3.2&&!preview)finish();
  };
  if(fixture===null){
    if(reduced){if(!preview)setTimeout(finish,900);}
    else renderer.setAnimationLoop(animation);
  }
  addEventListener('resize',()=>{if(!status.disposed){camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight);draw(2.2);}});
}catch(error){
  status.error=String(error);document.body.classList.add('failed');document.querySelector('#fallback').hidden=false;
  notify('failed',status.error);if(!preview)setTimeout(finish,700);
}
