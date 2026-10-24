(() => {
  window.addEventListener("message", (event) => {
    if (event.source !== window || event.origin !== location.origin) return;
    const message = event.data;
    if (message?.source !== "JARVIS_PAGE" ||
        !["LAUNCH_APP", "LOCAL_ACTION"].includes(message.type) ||
        typeof message.requestId !== "string") return;

    let request;
    if (message.type === "LAUNCH_APP" && typeof message.app === "string" &&
        /^[\w][\w .&()+-]{0,99}$/.test(message.app)) {
      request = { type: "launch_app", app: message.app };
    } else if (message.type === "LOCAL_ACTION" && message.action === "open_folder" &&
        typeof message.path === "string" && message.path.length > 0 && message.path.length <= 1024) {
      request = { type: "local_action", action: "open_folder", path: message.path };
    } else {
      return;
    }

    chrome.runtime.sendMessage(request, (result) => {
      const error = chrome.runtime.lastError;
      window.postMessage({
        source: "JARVIS_BRIDGE",
        requestId: message.requestId,
        result: error ? { ok: false, error: error.message } : (result || { ok: false, error: "The Windows bridge returned no response." }),
      }, location.origin);
    });
  });
})();
