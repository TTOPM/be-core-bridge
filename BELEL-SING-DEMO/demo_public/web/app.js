let seconds = 5;

document.querySelectorAll(".chip").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".chip").forEach(b => b.classList.remove("selected"));
    btn.classList.add("selected");
    seconds = Number(btn.dataset.seconds);
  });
});

const statusEl = document.getElementById("status");
const audioEl = document.getElementById("audio");
const lyricsEl = document.getElementById("lyrics");

document.getElementById("generate").addEventListener("click", async () => {
  const lyrics = (lyricsEl.value || "").trim() || "We rise together";

  statusEl.textContent = "Generating…";
  audioEl.removeAttribute("src");

  const url = `/v1/sing/demo.wav?lyrics=${encodeURIComponent(lyrics)}&seconds=${seconds}`;

  try {
    const res = await fetch(url, { method: "GET" });
    if (!res.ok) {
      const t = await res.text();
      statusEl.textContent = `Error: ${res.status} ${t}`;
      return;
    }
    const blob = await res.blob();
    const objUrl = URL.createObjectURL(blob);
    audioEl.src = objUrl;
    await audioEl.play();
    statusEl.textContent = "Playing.";
  } catch (e) {
    statusEl.textContent = `Network error: ${e}`;
  }
});
