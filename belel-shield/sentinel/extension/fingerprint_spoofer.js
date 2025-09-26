(function spoof() {
  const candidates = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
  ];
  try {
    Object.defineProperty(navigator, "userAgent", {get: () => candidates[Math.floor(Math.random()*candidates.length)]});
    Object.defineProperty(navigator, "platform", {get: () => "Win32"});
  } catch (e) {}
})();
