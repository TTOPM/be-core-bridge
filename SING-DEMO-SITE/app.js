// Set this to your deployed demo API endpoint (Render/Fly/Cloud Run/VPS).
// Example: https://belel-sing-demo.example.com
const DEMO_API_BASE = ""; // <- leave blank for now; site still plays static sample

const player = document.getElementById("player");
const statusEl = document.getElementById("status");
const btnGenerate = document.getElementById("btnGenerate");
const btnSample = document.getElementById("btnSample");

function setStatus(msg) { statusEl.textContent = msg; }

btnSample.addEventListener("click", () => {
  player.pause();
  player.src = "./samples/sample.wav";
  player.load();
  player.play().catch(() => {});
  setStatus("Loaded static sample from repository.");
});

btnGenerate.addEventListener("click", async () => {
  const lyrics = (document.getElementById("lyrics").value || "").trim();
  const seconds = document.getElementById("seconds").value;

  if (!lyrics) {
    setStatus("Enter short lyrics (max 64 chars).");
    return;
  }
  if (!DEMO_API_BASE) {
    setStatus("Demo API not configured. Deploy the demo API and set DEMO_API_BASE in app.js.");
    return;
  }

  btnGenerate.disabled = true;
  setStatus("Generating…");

  try {
    const url = new URL(DEMO_API_BASE.replace(/\/+$/, "") + "/v1/sing/demo.wav");
    url.searchParams.set("lyrics", lyrics);
    url.searchParams.set("seconds", seconds);

    const res = await fetch(url.toString(), { method: "GET" });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`API error ${res.status}: ${text.slice(0, 160)}`);
    }

    const blob = await res.blob();
    const objectUrl = URL.createObjectURL(blob);

    player.pause();
    player.src = objectUrl;
    player.load();
    await player.play().catch(() => {});
    setStatus("Generated capped WAV. Playback loaded.");
  } catch (err) {
    setStatus(String(err.message || err));
  } finally {
    btnGenerate.disabled = false;
  }
});
