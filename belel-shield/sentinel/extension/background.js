const BLOCKLIST_KEY = "belel_blocklist_v1";

async function loadBlocklist() {
  try {
    const value = await (browser?.storage?.local || chrome.storage.local).get(BLOCKLIST_KEY);
    return value[BLOCKLIST_KEY] || {domains: [], ip_ranges: []};
  } catch (e) {
    console.error("Blocklist read error", e);
    return {domains: [], ip_ranges: []};
  }
}

function endsWithAny(host, list){
  return list.some(d => host === d || host.endsWith("."+d));
}

(chrome.webRequest || browser.webRequest).onBeforeRequest.addListener(
  async function(details) {
    const bl = await loadBlocklist();
    try {
      const url = new URL(details.url);
      if (endsWithAny(url.hostname, bl.domains)) {
        console.log("Belel Sentinel blocked:", details.url);
        return {cancel: true};
      }
    } catch(e){}
    return {};
  },
  {urls: ["<all_urls>"]},
  ["blocking"]
);
