chrome.declarativeNetRequest.onRuleMatchedDebug.addListener((info) => {
  console.log("[Belel Sentinel] Blocked:", info.request.url);
});
