const allowedApps = new Set(["calculator", "notepad", "file explorer", "paint", "spotify"]);

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== "launch_app" || !allowedApps.has(message.app)) return false;

  chrome.runtime.sendNativeMessage("com.jarvis.app_launcher", {
    action: "open_app",
    app: message.app,
  }, (response) => {
    const error = chrome.runtime.lastError;
    sendResponse(error
      ? { ok: false, error: error.message }
      : (response || { ok: false, error: "Windows launcher returned no response." }));
  });
  return true;
});
