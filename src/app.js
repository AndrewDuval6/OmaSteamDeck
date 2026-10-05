const app=document.querySelector("#app");
let screen="splash",focus=0,user="Andrew";
const sections=[["Games","Your Steam and game library"],["Media","Streaming and entertainment"],["Store","Discover apps and services"],["Library","Everything you've installed"],["Apps","Tools and utilities"],["Settings","System, controllers and profiles"]];
const profiles=["Andrew","Guest","+ Add profile"];
function render(){
 if(screen==="splash"){app.innerHTML='<section class="screen splash"><div class="mark">OMA STEAM DECK</div><div class="sub">POWERED BY OMARCHY</div><div class="loader"></div></section>';setTimeout(()=>{screen="profiles";focus=0;render()},1800);return}
 if(screen==="profiles"){app.innerHTML='<section class="screen profiles"><h1>Who’s playing?</h1><div class="profile-row">'+profiles.map((p,i)=>'<button class="profile '+(i===focus?"focused":"")+'" data-i="'+i+'"><span>PROFILE</span><strong>'+p+'</strong></button>').join("")+'</div><div class="footer">D-pad / stick to move · A / Enter to select</div></section>';return}
 app.innerHTML='<section class="screen home"><header><div><div class="sub">OMA STEAM DECK</div><h1>Welcome, '+user+'</h1></div><div class="status">Deck mode · 1280×800</div></header><div class="tiles">'+sections.map((s,i)=>'<button class="tile '+(i===focus?"focused":"")+'" data-i="'+i+'"><b>'+s[0]+'</b><span>'+s[1]+'</span></button>').join("")+'</div><div class="footer">A / Enter select · B / Esc back · Controller support enabled through Gamepad API</div></section>'
}
function move(d){const n=screen==="profiles"?profiles.length:sections.length;focus=(focus+d+n)%n;render()}
function select(){if(screen==="profiles"&&focus<2){user=profiles[focus];screen="home";focus=0;render()}}
addEventListener("keydown",e=>{if(["ArrowRight","ArrowDown"].includes(e.key))move(1);if(["ArrowLeft","ArrowUp"].includes(e.key))move(-1);if(e.key==="Enter")select();if(e.key==="Escape"&&screen==="home"){screen="profiles";focus=0;render()}});
let last=0;function poll(){const g=navigator.getGamepads?.()[0];if(g){const now=Date.now();if(now-last>180){if(g.buttons[0]?.pressed){select();last=now}else if(g.buttons[1]?.pressed&&screen==="home"){screen="profiles";focus=0;render();last=now}else if(g.buttons[15]?.pressed||g.axes[0]>.6){move(1);last=now}else if(g.buttons[14]?.pressed||g.axes[0]<-.6){move(-1);last=now}}}requestAnimationFrame(poll)}render();poll();app.focus();
