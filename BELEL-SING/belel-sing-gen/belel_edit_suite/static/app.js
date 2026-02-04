async function loadLanguages() {
  const res = await fetch("/api/languages");
  const obj = await res.json();
  const sel = document.getElementById("language");
  sel.innerHTML = "";
  obj.languages.forEach(l => {
    const opt = document.createElement("option");
    opt.value = l.code;
    opt.textContent = `${l.name} (${l.code})`;
    sel.appendChild(opt);
  });
  document.getElementById("langCount").textContent = `Documented languages: ${obj.count}`;
}

function setDownloads(jobId) {
  document.getElementById("lastJob").value = jobId || "";
  document.getElementById("dlWav").href = jobId ? `/api/download/${jobId}/wav` : "#";
  document.getElementById("dlJson").href = jobId ? `/api/download/${jobId}/json` : "#";
  document.getElementById("dlMel").href = jobId ? `/api/download/${jobId}/mel` : "#";
}

async function generate() {
  const fd = new FormData();
  fd.append("prompt", document.getElementById("genPrompt").value || "");
  fd.append("lyrics", document.getElementById("genLyrics").value || "");
  fd.append("language", document.getElementById("language").value || "en");
  fd.append("duration_sec", document.getElementById("genDuration").value || "60");
  fd.append("steps", document.getElementById("genSteps").value || "2");
  fd.append("guidance", document.getElementById("genGuidance").value || "6.0");

  const out = document.getElementById("genResult");
  out.textContent = "Generating...";
  const res = await fetch("/api/generate", { method: "POST", body: fd });
  const obj = await res.json();
  out.textContent = JSON.stringify(obj, null, 2);
  if (obj.job_id) setDownloads(obj.job_id);
}

async function edit() {
  const wav = document.getElementById("sourceWav").files[0];
  if (!wav) {
    alert("Please upload a source WAV.");
    return;
  }
  const json = document.getElementById("sourceJson").files[0] || null;

  const fd = new FormData();
  fd.append("mode", document.getElementById("mode").value);
  fd.append("source_wav", wav);
  if (json) fd.append("source_json", json);

  fd.append("t_start_sec", document.getElementById("tStart").value || "0");
  fd.append("t_end_sec", document.getElementById("tEnd").value || "0");
  fd.append("extend_sec", document.getElementById("extendSec").value || "0");

  fd.append("prompt", document.getElementById("editPrompt").value || "");
  fd.append("lyrics", document.getElementById("editLyrics").value || "");
  fd.append("new_lyrics", document.getElementById("newLyrics").value || "");

  fd.append("language", document.getElementById("language").value || "en");
  fd.append("steps", document.getElementById("editSteps").value || "2");
  fd.append("guidance", document.getElementById("editGuidance").value || "6.0");

  fd.append("crossfade_ms", document.getElementById("crossfadeMs").value || "60");
  fd.append("repaint_strength", document.getElementById("repaintStrength").value || "0.65");

  const out = document.getElementById("editResult");
  out.textContent = "Editing...";
  const res = await fetch("/api/edit", { method: "POST", body: fd });
  const obj = await res.json();
  out.textContent = JSON.stringify(obj, null, 2);
  if (obj.job_id) setDownloads(obj.job_id);
}

window.addEventListener("load", () => {
  loadLanguages();
  document.getElementById("btnGenerate").addEventListener("click", generate);
  document.getElementById("btnEdit").addEventListener("click", edit);
  setDownloads("");
});
