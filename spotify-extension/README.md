# JARVIS Chrome bridge

This unpacked Chrome extension provides these integrations:

- On Spotify search pages, it can click Play on the first track only when JARVIS opened the page with `?jarvis=play`.
- On JARVIS's local `http://127.0.0.1` page or hosted Render page, it can request that this Windows computer launch installed apps by their Start Menu display names through a Chrome Native Messaging host.
- The hosted JARVIS page can request opening an existing folder under the current Windows user's home directory. The native host rejects paths outside that directory and blocks common sensitive folders such as AppData, .ssh, .aws, and .git. It does not read files, create files, delete anything, or execute shell commands.

The Windows host looks up an exact or unambiguous app name in the user's Start Menu and Windows packaged-app list. It never treats the requested name as a command or file path. The PowerShell installer compiles the included C# host with the Windows .NET Framework compiler when needed, including after its source changes. Chrome grants it the `nativeMessaging` permission and access only to JARVIS's loopback page and hosted Render page.

## One-time setup

1. In Chrome, open `chrome://extensions`, turn on **Developer mode**, choose **Load unpacked**, and select this `spotify-extension` folder.
2. Copy the extension ID shown on its card.
3. In PowerShell, run the following command, replacing the sample ID with that copied ID:

   ```powershell
   powershell -ExecutionPolicy Bypass -File "C:\path\to\make-your-own-jarvis\spotify-extension\install_native_host.ps1" -ExtensionId aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
   ```

   The script builds the native host if needed, writes a Native Messaging manifest beside this extension, and registers that manifest under the current Windows user's Chrome settings. Review the script before running it.
4. Restart Chrome and keep JARVIS open in Chrome.

Then say `Open Calculator`, `Open Paint`, or the Start Menu name of another installed app. JARVIS reports a launch failure if the bridge is missing, the name is ambiguous, or Windows rejects the request.

## Spotify playback

With the extension enabled and Spotify signed in, say `Play <track> in Spotify`. The extension clicks Play on the top result and shows a status message if Spotify confirms playback or if it could not start.

For the hosted app, open JARVIS on the same Windows computer that has this extension and native host installed. On `chrome://extensions`, click **Reload** on the extension card, then refresh the hosted JARVIS tab. The extension permits the current Render hostname `jarvis-mark-1-k6sq.onrender.com` and local `127.0.0.1`. On Android, JARVIS can offer app links for supported apps; Android decides whether an installed app accepts a link. A website cannot enumerate or launch every installed phone app directly. iPhone launching is limited to apps with an approved universal link or URL scheme.

After editing these files, click **Reload** on the extension card and refresh JARVIS and any Spotify search tab already open. If the extension ID changed, rerun `install_native_host.ps1` with the new ID and restart Chrome.
