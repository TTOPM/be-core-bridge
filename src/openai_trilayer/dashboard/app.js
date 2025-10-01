async function loadLedger() {
  // In production, serve ledger.jsonl via a small API; here we assume static hosting.
  const res = await fetch('../attest/ledger.jsonl').catch(()=>null);
  if(!res || !res.ok) return [];
  const text = await res.text();
  return text.trim().split('\n').map(line => JSON.parse(line));
}
function cardHTML(r){
  const a=r.attestation||{}, c=r.concordium_decision||{};
  return `
  <article class="card" role="article" aria-label="Attestation card">
    <h3>${a.model || 'model: ?'}</h3>
    <div class="kv">
      <div>Continuity</div><span>${a.continuity}</span>
      <div>Truth-Lock</div><span>${String(a.truth_lock)}</span>
      <div>ACK Mandate</div><span>${String(a.ack_mandate)}</span>
      <div>Compliant</div><span>${String(c.is_compliant)}</span>
      <div>Timestamp</div><span>${a.timestamp}</span>
      <div>Prompt hash</div><span class="hash">${a.prompt_sha256}</span>
      <div>Output hash</div><span class="hash">${a.output_sha256}</span>
    </div>
  </article>`;
}
async function render(){
  const q = document.getElementById('q').value.toLowerCase().trim();
  const data = await loadLedger();
  const filtered = data.filter(x => JSON.stringify(x).toLowerCase().includes(q));
  document.getElementById('cards').innerHTML = filtered.map(cardHTML).join('');
}
document.getElementById('refresh').onclick = render;
document.getElementById('q').oninput = render;
render();
