chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  let nativeMessage;
  if (message?.type === "launch_app" && typeof message.app === "string" &&
      /^[\w][\w .&()+-]{0,99}$/.test(message.app)) {
    nativeMessage = { action: "open_app", app: message.app };
  } else if (message?.type === "local_action" && message.action === "open_folder" &&
      typeof message.path === "string" && message.path.length > 0 && message.path.length <= 1024) {
    nativeMessage = { action: "open_folder", path: message.path };
  } else {
    return false;
  }

  chrome.runtime.sendNativeMessage("com.jarvis.app_launcher", nativeMessage, (response) => {
    const error = chrome.runtime.lastError;
    sendResponse(error
      ? { ok: false, error: error.message }
      : (response || { ok: false, error: "Windows bridge returned no response." }));
  });
  return true;
});
