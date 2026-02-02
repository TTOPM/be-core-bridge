# BELEL-SING — GitHub Pages Demo

This is a **static** GitHub Pages site that:
- Always plays a **repo-bundled** sample WAV (`sing-demo-site/samples/sample.wav`)
- Optionally calls a **separate demo API** (not hosted on GitHub Pages) to generate a **3–5s capped** WAV

## Configure generation
Edit `sing-demo-site/app.js` and set:

`const DEMO_API_BASE = "https://YOUR-DEPLOYED-DEMO-API";`

## Local preview
Open `sing-demo-site/index.html` directly, or serve it:

```bash
python -m http.server 8080 --directory sing-demo-site
