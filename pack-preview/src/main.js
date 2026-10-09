import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {createIcons, Backpack, ZoomIn, ZoomOut, Scan, Camera} from 'lucide';
import './style.css';

createIcons({icons:{Backpack,ZoomIn,ZoomOut,Scan,Camera}});
const el = (id) => document.getElementById(id);
const scene = new THREE.Scene();
scene.background = new THREE.Color('#e4e7e5');
const camera = new THREE.PerspectiveCamera(35,1,.1,1000);
const renderer = new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.NoToneMapping;
el('viewport').appendChild(renderer.domElement);
const controls = new OrbitControls(camera,renderer.domElement);
controls.enableDamping = true;
controls.minDistance = 24;
controls.maxDistance = 250;
controls.maxPolarAngle = Math.PI*.92;
const ambient = new THREE.HemisphereLight('#e9f3ff','#99917f',2.0);
scene.add(ambient);
const key = new THREE.DirectionalLight('#fff4df',3.1);
key.position.set(-40,65,55);key.castShadow=true;
key.shadow.mapSize.set(2048,2048);
Object.assign(key.shadow.camera,{left:-60,right:60,top:60,bottom:-60,near:1,far:220});
key.shadow.normalBias=.2;scene.add(key);
const fill = new THREE.DirectionalLight('#c7dfeb',1.4);fill.position.set(45,15,-35);scene.add(fill);
const floor = new THREE.Mesh(new THREE.PlaneGeometry(2000,2000),new THREE.ShadowMaterial({opacity:.13}));
floor.rotation.x=-Math.PI/2;floor.receiveShadow=true;scene.add(floor);
let model, current, material, texture, surface='textured', baseHeight=32, data;
const reference = new THREE.Group();
const refMaterial = new THREE.MeshStandardMaterial({color:'#b1c3ba',transparent:true,opacity:.25,roughness:1,depthWrite:false});
reference.visible=false;scene.add(reference);

function resize(){const b=el('viewport').getBoundingClientRect();renderer.setSize(b.width,b.height);camera.aspect=b.width/b.height;camera.updateProjectionMatrix();}
new ResizeObserver(resize).observe(el('viewport'));
function view(kind='front'){
  const framedHeight=reference.visible?Math.max(baseHeight,50):baseHeight;
  const distance=framedHeight*(camera.aspect<1?3.7:2.6);
  const directions={front:[.32,.23,1],side:[1,.2,.03],back:[-.3,.2,-1]};
  camera.position.set(...directions[kind]).normalize().multiplyScalar(distance);
  controls.target.set(0,reference.visible?4:0,0);controls.update();
  document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===kind));
}
function setSurface(kind){
  surface=kind;material.wireframe=kind==='wire';material.map=kind==='textured'?texture:null;
  material.vertexColors=kind==='textured';material.color.set(kind==='textured'?'#ffffff':kind==='wire'?'#355f4b':'#bbc5bf');
  material.needsUpdate=true;
  document.querySelectorAll('[data-surface]').forEach(b=>b.classList.toggle('active',b.dataset.surface===kind));
}
function selectPack(pack){
  current=pack;
  if(model){scene.remove(model);model.geometry.dispose();material.dispose();}
  const g=new THREE.BufferGeometry();
  const swap=(p)=>[p[0],p[2]-pack.height/2,-p[1]];
  g.setAttribute('position',new THREE.Float32BufferAttribute(pack.positions.flatMap(swap),3));
  g.setAttribute('normal',new THREE.Float32BufferAttribute(pack.normals.flatMap(p=>[p[0],p[2],-p[1]]),3));
  g.setAttribute('color',new THREE.Float32BufferAttribute(pack.colors.flatMap(c=>c.slice(0,3)),3));
  g.setAttribute('uv',new THREE.Float32BufferAttribute(pack.uvs.flat(),2));
  g.computeBoundingSphere();
  g.computeBoundingBox();
  const extent=g.boundingBox.getSize(new THREE.Vector3());
  baseHeight=Math.max(extent.x,extent.y,extent.z);
  reference.position.set(0,-pack.wornHeightOffset,-(pack.depth/2+pack.wornBackOffset));
  reference.rotation.y=0;
  material=new THREE.MeshStandardMaterial({map:texture,vertexColors:true,roughness:.92,metalness:0});
  model=new THREE.Mesh(g,material);model.castShadow=true;model.receiveShadow=true;scene.add(model);
  floor.position.y=-pack.height/2;
  el('model-title').textContent=pack.name;
  el('model-stats').textContent=`${pack.triangles.toLocaleString()} triangles / textured mesh`;
  el('effect').textContent=`Feather ${pack.feather}`;el('weight').textContent=`${pack.weight}`;
  el('dimensions').textContent=`${pack.width} x ${pack.height} x ${pack.depth}`;
  document.querySelectorAll('.asset').forEach(b=>{const active=b.dataset.id===pack.id;b.classList.toggle('active',active);b.setAttribute('aria-selected',active);});
  setSurface(surface);view();
  window.previewState={id:pack.id,triangles:pack.triangles,textureLoaded:true};
}
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>view(b.dataset.view));
document.querySelectorAll('[data-surface]').forEach(b=>b.onclick=()=>setSurface(b.dataset.surface));
el('reset').onclick=()=>{model.rotation.y=0;view();};
const zoom=(amount)=>{const d=camera.position.clone().sub(controls.target);d.multiplyScalar(amount);d.clampLength(controls.minDistance,controls.maxDistance);camera.position.copy(controls.target).add(d);controls.update();};
el('zoom-in').onclick=()=>zoom(.8);el('zoom-out').onclick=()=>zoom(1.25);
el('snapshot').onclick=()=>{renderer.render(scene,camera);const a=document.createElement('a');a.href=renderer.domElement.toDataURL('image/png');a.download=`${current.id}-preview.png`;a.click();};
el('reference').onchange=e=>{reference.visible=e.target.checked;view(document.querySelector('[data-view].active')?.dataset.view||'front');};
el('lighting').onchange=e=>{
  const mode=e.target.value;
  key.color.set(mode==='warm'?'#ffba78':'#fff4df');
  key.intensity=mode==='overcast'?1.0:3.1;
  ambient.intensity=mode==='warm'?1.2:2;
  fill.intensity=mode==='warm'?.6:1.4;
};
const clock=new THREE.Clock();
renderer.setAnimationLoop(()=>{const dt=Math.min(clock.getDelta(),.1);if(model){if(el('turntable').checked)model.rotation.y+=dt*.35;reference.rotation.y=model.rotation.y;}controls.update();renderer.render(scene,camera);});
async function init(){
  const response=await fetch('/assets/packs.json');if(!response.ok)throw new Error('Model data unavailable');data=await response.json();
  const fitResponse=await fetch('/assets/vanilla-fit.json');
  if(fitResponse.ok){
    const fit=await fitResponse.json();
    const geometry=new THREE.BufferGeometry();
    geometry.setAttribute('position',new THREE.Float32BufferAttribute(fit.positions.flatMap(p=>[-p[2],p[0],-p[1]]),3));
    geometry.computeVertexNormals();
    refMaterial.side=THREE.DoubleSide;
    reference.add(new THREE.Mesh(geometry,refMaterial));
  }else{el('reference').disabled=true;}
  texture=await new THREE.TextureLoader().loadAsync('/assets/leather.png');
  texture.colorSpace=THREE.SRGBColorSpace;texture.wrapS=texture.wrapT=THREE.RepeatWrapping;texture.anisotropy=renderer.capabilities.getMaxAnisotropy();
  el('texture-size').textContent=`${texture.image.width} x ${texture.image.height}`;
  el('version').textContent=`v${data.version}`;
  for(const pack of data.models){
    const b=document.createElement('button');b.className='asset';b.dataset.id=pack.id;b.role='tab';
    const img=document.createElement('img');img.src=`/assets/${pack.id}.png`;img.alt='';
    const text=document.createElement('div');const name=document.createElement('strong');name.textContent=pack.name;
    const detail=document.createElement('span');detail.textContent=`Feather ${pack.feather}`;text.append(name,detail);b.append(img,text);
    b.onclick=()=>selectPack(pack);el('collection').appendChild(b);
  }
  resize();selectPack(data.models.find(p=>p.id==='wfp_backpack'));el('status').hidden=true;
}
init().catch(error=>{el('status').textContent=`Unable to load preview: ${error.message}`;console.error(error);});
