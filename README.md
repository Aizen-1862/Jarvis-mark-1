# JARVIS

JARVIS is a local-first voice assistant with a browser interface, OpenRouter for responses, Fish Audio for speech, and an optional Windows Chrome extension bridge.

## Run locally on Windows

1. Run `run.bat` and enter your Fish Audio and OpenRouter API keys when prompted.
2. Open the local page in Chrome or Edge and allow microphone access.
3. For Spotify playback and Windows app launching, follow `spotify-extension/README.md`.

## Host the web assistant on Render

The included `render.yaml` configures a Python web service. In Render, create a Blueprint from this GitHub repository, then enter these environment secrets when prompted:

- `JARVIS_ACCESS_PASSWORD`: a strong, unique password for the JARVIS website. The browser asks for username `jarvis` and this password.
- `FISH_API_KEY`: a newly rotated Fish Audio key.
- `OPENROUTER_API_KEY`: a newly rotated OpenRouter key.
- `GOOGLE_CLIENT_ID`: optional Google OAuth Web client ID for Work Mode mail summaries. Enable the Gmail API, add the Render URL as an authorized JavaScript origin, and configure the OAuth consent screen and test users in Google Cloud. JARVIS requests only the `gmail.readonly` scope.

Render supplies `PORT`; the service binds to `0.0.0.0`, disables browser auto-launch, and uses `/healthz` for health checks. JARVIS refuses to start publicly without the password and both API keys. The Render URL uses HTTPS, which protects Basic Auth credentials in transit.

Never upload `.env`, API keys, or passwords to GitHub. The `.env.example` file contains blank placeholders only. If an API key may have been exposed, revoke it and create a replacement before hosting.

## What works remotely

The hosted website can be opened from computers and phones using the same Render URL and password. The Windows native app bridge is separate: on a Windows computer where the Chrome extension and native host are installed, the hosted website can request launching installed apps and opening existing folders under your Windows user folder. Folder requests are restricted to that home directory and block common sensitive locations. The bridge does not provide arbitrary shell access, file reads, file writes, or deletion. A cloud service cannot control your local computer unless this local bridge is installed and enabled. The extension allows both `127.0.0.1` and the current hosted domain `jarvis-mark-1-k6sq.onrender.com`.

The browser voice-input API is most consistent in desktop Chrome or Edge. Typed requests remain available when voice input is unsupported. General answers stream as they are generated; requests for changing facts use OpenRouter web search when supported by the selected model.

## Additional features and limits

- **Windows computer operator (local only):** in the local Windows app, JARVIS can list folders, read supported text/source files, open folders in File Explorer, and create new folders or text/source files under your Windows user home. It will not overwrite or delete files, run shell commands, or read credential locations. File contents you ask it to read are sent to the configured OpenRouter model for analysis. These tools are disabled when JARVIS is hosted remotely; the hosted server cannot access your PC's files.
- **Work Mode:** after Google OAuth is configured and you grant read-only permission, JARVIS summarizes up to 200 unread inbox messages. Mail content is sent to OpenRouter for summarization. It does not send, archive, delete, or modify messages.
- **Image generation:** ask JARVIS to generate an image. The configured OpenRouter image model may charge per image; JARVIS shows the reported cost.
- **Mobile app links:** Android has deep links for a small set of common apps; iOS support depends on app URL schemes. A web page cannot enumerate or launch every installed phone app. Computer apps still launch only through the Windows bridge on that computer.
- **Android app:** install the `J.A.R.V.I.S.` debug APK from the `Build JARVIS Mobile APK` workflow artifact in GitHub Actions. It opens the hosted JARVIS interface in an app-style full-screen view, including the reactor, conversation, streaming answers, and Fish Audio voice. Tap the wake overlay once to enable audio, then tap the reactor and allow microphone permission to speak. Enter the same JARVIS website password when prompted. The Android companion launches a fixed allowlist of apps on the phone; it does not read other app data or control playback. The APK is a test build and Android may ask you to allow installation from your browser.
- **E-girl mode:** say `activate e-girl mode`; say `activate JARVIS mode` to restore the default persona.

If a key has been exposed, revoke it at its provider and replace the value in the hosting dashboard or local `.env` file. Keep secrets out of GitHub.

