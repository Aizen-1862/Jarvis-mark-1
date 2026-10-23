# JARVIS

JARVIS is a local-first voice assistant with a browser interface, OpenRouter for responses, Fish Audio for speech, and an optional Windows Chrome extension bridge.

## Run locally on Windows

1. Run `run.bat` and enter your Fish Audio and OpenRouter API keys when prompted.
2. Open the local page in Chrome or Edge and allow microphone access.
3. For Spotify playback and Windows app launching, follow `spotify-extension/README.md`.

## Host the web assistant on Render

The included `render.yaml` configures a Python web service. In Render, create a Blueprint from this private GitHub repository, then enter these environment secrets when prompted:

- `JARVIS_ACCESS_PASSWORD`: a strong, unique password for the JARVIS website. The browser asks for username `jarvis` and this password.
- `FISH_API_KEY`: a newly rotated Fish Audio key.
- `OPENROUTER_API_KEY`: a newly rotated OpenRouter key.

Render supplies `PORT`; the service binds to `0.0.0.0`, disables browser auto-launch, and uses `/healthz` for health checks. JARVIS refuses to start publicly without the password and both API keys. The Render URL uses HTTPS, which protects Basic Auth credentials in transit.

Never upload `.env`, API keys, or passwords to GitHub. The `.env.example` file contains blank placeholders only. If an API key may have been exposed, revoke it and create a replacement before hosting.

## What works remotely

The hosted website can be opened from computers and phones using the same Render URL and password. The local Windows native app bridge is separate: it can only launch apps on a Windows computer where the Chrome extension and native host are installed. A cloud service cannot open Calculator on your local computer by itself. The extension's JARVIS page permission currently targets `127.0.0.1`; after the Render URL exists, update that permission to the exact hosted domain before using the Windows bridge through the hosted page.

The browser voice-input API is most consistent in desktop Chrome or Edge. Typed requests remain available when voice input is unsupported.
