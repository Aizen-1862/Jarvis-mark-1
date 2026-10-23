(() => {
  if (new URLSearchParams(location.search).get("jarvis") !== "play") return;

  const startedAt = Date.now();
  let clicked = false;

  function showStatus(message, error = false) {
    let toast = document.getElementById("jarvis-spotify-status");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "jarvis-spotify-status";
      Object.assign(toast.style, {
        position: "fixed",
        right: "24px",
        bottom: "96px",
        zIndex: "2147483647",
        maxWidth: "min(360px, calc(100vw - 48px))",
        padding: "12px 16px",
        borderRadius: "8px",
        color: "white",
        background: "#222",
        boxShadow: "0 4px 18px #0008",
        font: "14px/1.4 system-ui, sans-serif",
      });
      document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.style.background = error ? "#8b2525" : "#222";
    if (!error) setTimeout(() => toast?.remove(), 5000);
  }

  function findFirstTrackPlayButton() {
    // Spotify has used both native table markup and ARIA rows. Find the first
    // result row containing a real track link, then its explicit Play control.
    const rows = [...document.querySelectorAll('[role="row"], tr')];
    const firstTrack = rows.find((row) =>
      [...row.querySelectorAll('a[href*="/track/"]')].some((link) => {
        try { return new URL(link.href).pathname.includes("/track/"); }
        catch { return false; }
      })
    );
    if (!firstTrack) return null;

    const buttons = [...firstTrack.querySelectorAll("button")];
    return buttons.find((button) => {
      const label = `${button.getAttribute("aria-label") || ""} ${button.title || ""}`.trim();
      return /\bplay\b/i.test(label) && !button.disabled;
    }) || null;
  }

  const timer = setInterval(() => {
    if (clicked) return;
    const button = findFirstTrackPlayButton();
    if (button) {
      clicked = true;
      clearInterval(timer);
      const row = button.closest('[role="row"], tr');
      const title = row?.querySelector('a[href*="/track/"]')?.textContent?.trim() || "the top result";
      button.click();
      showStatus(`JARVIS: starting ${title}…`);

      // Verify Spotify changed the result's control to Pause. If it didn't,
      // report that clearly rather than silently claiming playback worked.
      setTimeout(() => {
        const nowPlaying = row?.querySelector('button[aria-label^="Pause"], button[title^="Pause"]');
        if (nowPlaying) showStatus(`JARVIS: playing ${title}`);
        else showStatus("JARVIS found the top result but Spotify did not start it. Click Play once, then try again.", true);
      }, 1800);
      return;
    }

    if (Date.now() - startedAt > 40000) {
      clearInterval(timer);
      showStatus("JARVIS couldn't find a playable track. Check that Spotify finished loading.", true);
    }
  }, 400);
})();
