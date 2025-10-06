
const API_BASE = "";
const MESSAGES = document.getElementById("messages");
const TEXT = document.getElementById("text");
const SEND = document.getElementById("send");
const MIC = document.getElementById("mic");
const PRESET = document.getElementById("preset");

const tone = document.getElementById("tone");
const pacing = document.getElementById("pacing");
const energy = document.getElementById("energy");
const toneVal = document.getElementById("toneVal");
const pacingVal = document.getElementById("pacingVal");
const energyVal = document.getElementById("energyVal");

[tone, pacing, energy].forEach(s => s.addEventListener("input", () => {
  toneVal.textContent = (+tone.value).toFixed(2);
  pacingVal.textContent = (+pacing.value).toFixed(2);
  energyVal.textContent = (+energy.value).toFixed(2);
}));

function addMsg(role, text) {
  const div = document.createElement("div");
  div.className = "msg " + role;
  div.textContent = text;
  MESSAGES.appendChild(div);
  MESSAGES.scrollTop = MESSAGES.scrollHeight;
}

async function loadPresets() {
  const r = await fetch("/api/presets");
  const data = await r.json();
  const keys = Object.keys(data.presets || {});
  PRESET.innerHTML = "";
  keys.forEach(k => {
    const opt = document.createElement("option");
    opt.value = k; opt.textContent = k;
    PRESET.appendChild(opt);
  });
  PRESET.value = "neutral";
}
loadPresets();

SEND.addEventListener("click", async () => {
  const msg = TEXT.value.trim();
  if (!msg) return;
  addMsg("user", msg);

  const body = {
    message: msg,
    preset: PRESET.value,
    tone: +tone.value,
    pacing: +pacing.value,
    energy: +energy.value
  };

  const r = await fetch("/api/chat", {
    method: "POST",
    headers: { "content-type": "application/json", "X-Session-Id": getSession() },
    body: JSON.stringify(body)
  });
  const data = await r.json();
  if (data.error) { addMsg("assistant", "Error: " + data.error); return; }

  addMsg("assistant", data.response);
  if (data.voice) {
    const audio = new Audio(data.voice);
    audio.play().catch(()=>{});
  }
  TEXT.value = "";
});

function getSession() {
  const k = "belel_session";
  let s = localStorage.getItem(k);
  if (!s) { s = Math.random().toString(36).slice(2); localStorage.setItem(k, s); }
  return s;
}

// Basic microphone streaming to Belel Voice STT WS (if available)
let mediaStream = null;
let mediaRecorder = null;
let ws = null;

MIC.addEventListener("click", async () => {
  if (!mediaRecorder) {
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (e) {
      alert("Microphone permission denied");
      return;
    }
    // WS endpoint for Belel Voice STT
    const host = location.hostname;
    const sttWs = `ws://${host}:8000/v1/asr/stream`;
    ws = new WebSocket(sttWs);

    ws.onopen = () => {
      addMsg("assistant", "(Mic started. Listening…)");

      mediaRecorder = new MediaRecorder(mediaStream, { mimeType: "audio/webm" });
      mediaRecorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0 && ws.readyState === 1) {
          e.data.arrayBuffer().then(buf => ws.send(buf));
        }
      };
      mediaRecorder.start(250);
    };

    ws.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data);
        if (data.partial) {
          // could show partials
        } else if (data.final) {
          addMsg("user", data.text);
          TEXT.value = data.text;
        }
      } catch { /* ignore non-JSON */ }
    };

    ws.onclose = () => {
      addMsg("assistant", "(Mic stopped.)");
      if (mediaRecorder && mediaRecorder.state !== "inactive") mediaRecorder.stop();
      mediaRecorder = null;
      ws = null;
    };
  } else {
    // Stop
    ws && ws.close();
  }
});
