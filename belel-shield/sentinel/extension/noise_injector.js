(function(){
  // Local-only markers for UI; no network activity here.
  if (!window.__belelNoiseLog) window.__belelNoiseLog = [];
  setInterval(()=> {
    if (Math.random()<0.05) window.__belelNoiseLog.push({ts: Date.now(), ev: "fake_click"});
  }, 5000);
})();
