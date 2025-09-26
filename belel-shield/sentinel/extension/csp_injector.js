(function installCSPOverride() {
  try {
    const meta = document.createElement('meta');
    meta.httpEquiv = "Content-Security-Policy";
    meta.content = "default-src 'self' 'unsafe-inline'; script-src 'self'; object-src 'none'; img-src 'self' data:;";
    document.documentElement.prepend(meta);
  } catch (e) {}
})();
