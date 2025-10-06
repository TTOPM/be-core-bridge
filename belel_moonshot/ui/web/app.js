const API="http://localhost:8282";
const app=document.getElementById('app');
app.innerHTML=`
  <h1>Belel — continuous conversation</h1>
  <div><label>Tone <input id="tone" type="range" min="0" max="1" step="0.01" value="0.5"/></label>
  <label>Pacing <input id="pacing" type="range" min="0" max="1" step="0.01" value="0.5"/></label>
  <label>Energy <input id="energy" type="range" min="0" max="1" step="0.01" value="0.5"/></label></div>
  <div><label>Preset <select id="preset"></select></label>
  <label>Persona <input id="persona" value="Belel"/></label></div>
  <div><input id="text" placeholder="Say something..."/><button id="send">Send</button></div>
  <div id="messages"></div>
`;
function el(id){return document.getElementById(id)}
const M=el('messages');
function msg(role,text){const d=document.createElement('div'); d.textContent=role+': '+text; M.appendChild(d);}
async function load(){const r=await fetch(API+'/api/presets'); const data=await r.json(); const p=el('preset'); p.innerHTML='';
  Object.keys(data.presets).forEach(k=>{const o=document.createElement('option');o.value=k;o.textContent=k;p.appendChild(o)}); p.value='neutral';}
load();
el('send').onclick=async ()=>{
  const body={message:el('text').value, preset:el('preset').value, persona:el('persona').value,
              tone:+el('tone').value, pacing:+el('pacing').value, energy:+el('energy').value};
  msg('you', body.message);
  const r=await fetch(API+'/api/chat',{method:'POST',headers:{'content-type':'application/json','X-Session-Id':'demo','X-Disclosed':'true'},body:JSON.stringify(body)});
  const data=await r.json(); msg('Belel', data.response);
  if(data.voice_base64){ new Audio('data:'+data.mimetype+';base64,'+data.voice_base64).play().catch(()=>{}); }
  el('text').value='';
};


// --- Streaming voice WS (STT) + streaming TTS fallback ---
let mediaStream = null, mediaRecorder = null, sttWS = null;
async function startLive(){
  if(mediaRecorder) { stopLive(); return; }
  try { mediaStream = await navigator.mediaDevices.getUserMedia({audio:true}); }
  catch(e){ msg("assistant","(Mic denied)"); return; }
  const host = location.hostname || "localhost";
  const STT_WS = `ws://${host}:8000/v1/asr/stream`; // Belel Voice WS
  sttWS = new WebSocket(STT_WS);
  sttWS.binaryType = "arraybuffer";
  sttWS.onopen = () => {
    msg("assistant","(Live mode ON)");
    mediaRecorder = new MediaRecorder(mediaStream, {mimeType:"audio/webm"});
    mediaRecorder.ondataavailable = (e)=>{
      if(e.data && e.data.size>0 && sttWS && sttWS.readyState===1){
        e.data.arrayBuffer().then(buf=> sttWS.send(buf));
      }
    };
    mediaRecorder.start(200);
  };
  sttWS.onmessage = async (evt)=>{
    try{
      const data = JSON.parse(evt.data);
      if(data.partial){ /* show partials if desired */ }
      if(data.final && data.text){
        msg("user", data.text);
        // Immediately ask API to respond and speak
        await sendText(data.text, true);
      }
    }catch{ /* ignore non-json */ }
  };
  sttWS.onclose = stopLive;
}
function stopLive(){
  if(mediaRecorder && mediaRecorder.state!=="inactive") mediaRecorder.stop();
  mediaRecorder=null;
  if(sttWS) try{ sttWS.close(); }catch{} sttWS=null;
  if(mediaStream) mediaStream.getTracks().forEach(t=>t.stop());
  mediaStream=null;
  msg("assistant","(Live mode OFF)");
}
async function sendText(text, live=false){
  const body={ message:text, preset: document.getElementById("preset").value,
               persona: document.getElementById("persona").value || "Belel",
               tone:+document.getElementById("tone").value,
               pacing:+document.getElementById("pacing").value,
               energy:+document.getElementById("energy").value };
  const r = await fetch(API+"/api/chat", {
    method:"POST",
    headers:{ "content-type":"application/json", "X-Session-Id": session(), "X-Disclosed":"true" },
    body: JSON.stringify(body)
  });
  const data = await r.json();
  msg("assistant", data.response);
  // Streaming TTS (if your Voice GW supports /v1/tts/stream via MSE)
  if (data.voice_stream_url){
    try{
      const audio = new Audio(data.voice_stream_url);
      audio.play().catch(()=>{});
    }catch(e){ /* fall back */ }
  } else if (data.voice_base64){
    const audio = new Audio("data:"+data.mimetype+";base64,"+data.voice_base64);
    audio.play().catch(()=>{});
  }
  if(!live) document.getElementById("text").value="";
}
document.getElementById("mic").onclick = ()=> {
  if(!mediaRecorder) startLive(); else stopLive();
};
// Wire send button to use sendText()
document.getElementById("send").onclick = async ()=>{
  const text = document.getElementById("text").value.trim();
  if(!text) return;
  msg("user", text);
  await sendText(text, false);
};



async function loadVoices(){
  const r = await fetch(API+"/api/presets");
  const data = await r.json();
  const v = document.getElementById("voiceSel");
  v.innerHTML = "";
  (data.available_voices||[]).forEach(name=>{
    const o=document.createElement("option"); o.value=name; o.textContent=name; v.appendChild(o);
  });
  if(v.options.length){ v.value = "belel_resolve"; }
}
loadVoices();

const _oldSendText = sendText;
sendText = async function(text, live=false){
  const body={ message:text,
    preset: document.getElementById("preset").value,
    persona: document.getElementById("persona").value || "Belel",
    tone:+document.getElementById("tone").value,
    pacing:+document.getElementById("pacing").value,
    energy:+document.getElementById("energy").value,
    voice_name: document.getElementById("voiceSel").value || null,
    mode: document.getElementById("mode").value,
    melody: (document.getElementById("melody").value||"").split(",").map(s=>parseInt(s.trim())).filter(n=>!isNaN(n)),
    tempo: parseInt(document.getElementById("tempo").value||"90")
  };
  const r = await fetch(API+"/api/chat", {
    method:"POST",
    headers:{ "content-type":"application/json", "X-Session-Id": session(), "X-Disclosed":"true" },
    body: JSON.stringify(body)
  });
  const data = await r.json();
  msg("assistant", data.response);
  if (data.voice_stream_url){
    try{ new Audio(data.voice_stream_url).play().catch(()=>{}); }catch{}
  } else if (data.voice_base64){
    new Audio("data:"+data.mimetype+";base64,"+data.voice_base64).play().catch(()=>{});
  }
  if(!live) document.getElementById("text").value="";
};
