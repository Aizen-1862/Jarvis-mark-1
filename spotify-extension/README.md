# JARVIS Chrome bridge

This unpacked Chrome extension provides two small integrations:

- On Spotify search pages, it can click Play on the first track only when JARVIS opened the page with `?jarvis=play`.
- On JARVIS's local `http://127.0.0.1` page, it can request that Windows launch Calculator, Notepad, File Explorer, Paint, or Spotify through a Chrome Native Messaging host.

The Windows host has a fixed app allowlist. It does not execute model text, shell commands, or arbitrary paths. The PowerShell installer compiles the included C# host with the Windows .NET Framework compiler when needed. Chrome grants it the `nativeMessaging` permission and access only to JARVIS's loopback page.

## One-time setup

1. In Chrome, open `chrome://extensions`, turn on **Developer mode**, choose **Load unpacked**, and select this `spotify-extension` folder.
2. Copy the extension ID shown on its card.
3. In PowerShell, run the following command, replacing the sample ID with that copied ID:

   ```powershell
   powershell -ExecutionPolicy Bypass -File "C:\path\to\make-your-own-jarvis\spotify-extension\install_native_host.ps1" -ExtensionId aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
   ```

   The script builds the native host if needed, writes a Native Messaging manifest beside this extension, and registers that manifest under the current Windows user's Chrome settings. Review the script before running it.
4. Restart Chrome and keep JARVIS open in Chrome.

Then say `Open Calculator`, `Open Notepad`, `Open File Explorer`, `Open Paint`, or `Open Spotify`. JARVIS reports a launch failure if the bridge is missing or Windows rejects the request.

## Spotify playback

With the extension enabled and Spotify signed in, say `Play <track> in Spotify`. The extension clicks Play on the top result and shows a status message if Spotify confirms playback or if it could not start.

After editing these files, click **Reload** on the extension card and refresh JARVIS and any Spotify search tab already open. The JARVIS app bridge supports the default port range on `127.0.0.1`; it does not grant access to other hosts.
