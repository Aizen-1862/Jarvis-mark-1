(() => {
  const allowedApps = new Set(["calculator", "notepad", "file explorer", "paint", "spotify"]);

  window.addEventListener("message", (event) => {
    if (event.source !== window || event.origin !== location.origin) return;
    const message = event.data;
    if (message?.source !== "JARVIS_PAGE" || message.type !== "LAUNCH_APP") return;
    if (typeof message.requestId !== "string" || !allowedApps.has(message.app)) return;

    chrome.runtime.sendMessage({
      type: "launch_app",
      app: message.app,
      requestId: message.requestId,
    }, (result) => {
      const error = chrome.runtime.lastError;
      window.postMessage({
        source: "JARVIS_BRIDGE",
        requestId: message.requestId,
        result: error ? { ok: false, error: error.message } : (result || { ok: false }),
      }, location.origin);
    });
  });
})();
