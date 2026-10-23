"""J.A.R.V.I.S. - your own Iron Man assistant.

A free OpenRouter model is the brain, Fish Audio is the voice, your browser is the HUD.
Start it with run.bat (Windows) or ./run.sh (Mac/Linux).
"""
from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"
INDEX_HTML = ROOT / "web" / "index.html"
PROTOCOLS_FILE = ROOT / "protocols.json"

FISH_TTS_URL = "https://api.fish.audio/v1/tts"
FISH_SIGNUP_URL = "https://ariacodez.ai/l/fish-audio"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_KEYS_URL = "https://openrouter.ai/keys"

DEFAULTS = {
    "FISH_VOICE_ID": "41f0953d7a6b4c078445c7e65d620eeb",  # "JARVIS" in the Fish Audio voice library
    "FISH_MODEL": "s2.1-pro-free",  # S2.1 Pro at $0, free on the Fish Audio API until Nov 30, 2026
    "OPENROUTER_MODEL": "apodex/apodex-1.1-mini:free",  # the brain, free on OpenRouter
    "JARVIS_CALLS_YOU": "sir",
    "PORT": "8765",
}

NO_BROWSER = os.environ.get("JARVIS_NO_BROWSER") == "1"  # for testing: never open browser tabs


def log(message: str) -> None:
    print(f"  {time.strftime('%H:%M:%S')}  {message}", flush=True)


# ---------------------------------------------------------------- settings

def read_env_file() -> dict[str, str]:
    values: dict[str, str] = {}
    if ENV_FILE.exists():
        for raw in ENV_FILE.read_text(encoding="utf-8-sig").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_settings() -> dict[str, str]:
    cfg = dict(DEFAULTS)
    cfg.update({k: v for k, v in read_env_file().items() if v})
    # Keys come from the .env file only, so a key another app left in the system environment
    # never gets used by surprise. The other settings can be overridden for testing.
    for key in DEFAULTS:
        if os.environ.get(key):
            cfg[key] = os.environ[key].strip()
    return cfg


def save_to_env(updates: dict[str, str]) -> None:
    if ENV_FILE.exists():
        template = ENV_FILE.read_text(encoding="utf-8-sig")
    elif ENV_EXAMPLE.exists():
        template = ENV_EXAMPLE.read_text(encoding="utf-8")
    else:
        template = ""
    lines = template.splitlines()
    written = set()
    for i, line in enumerate(lines):
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key = line.split("=", 1)[0].strip()
        if key in updates:
            lines[i] = f"{key}={updates[key]}"
            written.add(key)
    lines += [f"{key}={value}" for key, value in updates.items() if key not in written]
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def ask(prompt: str) -> str:
    try:
        return input(prompt).strip().strip('"').strip("'")
    except EOFError:
        return ""


def first_run(cfg: dict[str, str]) -> dict[str, str]:
    """Ask for any missing key in the console and save it to .env."""
    missing = [k for k in ("FISH_API_KEY", "OPENROUTER_API_KEY") if not cfg.get(k)]
    if not missing:
        return cfg
    print("\n  Welcome. JARVIS needs two keys, then he's yours.")
    print("  Paste each one and press Enter (right-click or Ctrl+V pastes).")
    updates: dict[str, str] = {}
    if "FISH_API_KEY" in missing:
        print("\n  1) THE VOICE - your Fish Audio API key")
        print(f"     Get it here: {FISH_SIGNUP_URL}  (profile > API Keys > Create)")
        key = ask("     Fish Audio key: ")
        if key:
            updates["FISH_API_KEY"] = key
    if "OPENROUTER_API_KEY" in missing:
        print("\n  2) THE BRAIN - your free OpenRouter API key")
        print(f"     Get it here: {OPENROUTER_KEYS_URL}  (sign up and create a key, it starts with sk-or-)")
        key = ask("     OpenRouter key: ")
        if key and not key.startswith("sk-or-"):
            print("     That doesn't look like an OpenRouter key (they start with sk-or-). Saving it anyway.")
        if key:
            updates["OPENROUTER_API_KEY"] = key
    if updates:
        save_to_env(updates)
        print("\n  Saved to the .env file in this folder. You won't be asked again.")
    cfg = load_settings()
    still = [k for k in ("FISH_API_KEY", "OPENROUTER_API_KEY") if not cfg.get(k)]
    if still:
        print(f"\n  Still missing: {', '.join(still)}. JARVIS will start, and tells you what's missing.")
    return cfg


# ---------------------------------------------------------------- brain (a free OpenRouter model)

_history: list[dict] = []
_lock = threading.Lock()


def system_prompt(cfg: dict[str, str]) -> str:
    title = cfg["JARVIS_CALLS_YOU"]
    return (
        "You are J.A.R.V.I.S., the AI assistant from Iron Man, now running on the user's computer. "
        f'Address the user as "{title}". Be calm, precise, quietly witty and loyal. '
        "Everything you write is spoken aloud by a voice engine, so reply in one or two short "
        "sentences of plain spoken English. Never use markdown, lists, emojis, URLs, code, or "
        "anything in square brackets or asterisks. Available tools can open a web search or an "
        "HTTP/HTTPS website, and launch Calculator, Notepad, File Explorer, Paint, or Spotify. "
        "Opening a search page does not mean you have read its results. You cannot read email, "
        "inspect web pages, run arbitrary commands, or access local files. Never claim an action "
        "was done unless a tool result confirms it succeeded. Never use tools for actions the user "
        "did not request. If a request needs an unavailable capability, say so directly. "
        f"The local date and time is {time.strftime('%A, %B %d, %Y, %I:%M %p')}."
    )


class OpenRouterError(Exception):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(f"{status}: {detail}")
        self.status = status
        self.detail = detail


def openrouter_post(cfg: dict[str, str], payload: dict) -> dict:
    request = urllib.request.Request(OPENROUTER_URL, data=json.dumps(payload).encode("utf-8"), method="POST", headers={
        "Authorization": f"Bearer {cfg['OPENROUTER_API_KEY']}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310 - fixed https URL
            data = json.loads(response.read())
    except urllib.error.HTTPError as err:
        raise OpenRouterError(err.code, err.read()[:400].decode("utf-8", "replace")) from err
    except (urllib.error.URLError, TimeoutError) as err:
        raise OpenRouterError(0, str(err)) from err
    except json.JSONDecodeError as err:
        raise OpenRouterError(502, "unreadable reply") from err
    # OpenRouter reports some failures inside a 200 response.
    choices = data.get("choices") or [{}]
    problem = data.get("error") or choices[0].get("error")
    if isinstance(problem, dict):
        code = problem.get("code")
        raise OpenRouterError(code if isinstance(code, int) else 502, str(problem.get("message") or problem))
    return data


AGENT_TOOLS = [{
    "type": "function",
    "function": {
        "name": "search_web",
        "description": "Open a web search in the user's browser. This opens results; it does not read them.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "What the user asked to search for"}},
            "required": ["query"],
            "additionalProperties": False,
        },
    },
}, {
    "type": "function",
    "function": {
        "name": "open_website",
        "description": "Open a website the user explicitly asked to open.",
        "parameters": {
            "type": "object",
            "properties": {"url": {"type": "string", "description": "HTTP or HTTPS URL"}},
            "required": ["url"],
            "additionalProperties": False,
        },
    },
}, {
    "type": "function",
    "function": {
        "name": "open_app",
        "description": "Launch one of the supported local apps: Calculator, Notepad, File Explorer, Paint, or Spotify.",
        "parameters": {
            "type": "object",
            "properties": {"app": {"type": "string", "enum": ["calculator", "notepad", "file explorer", "paint", "spotify"]}},
            "required": ["app"],
            "additionalProperties": False,
        },
    },
}]


def run_agent_tool(name: str, raw_arguments: str) -> dict:
    """Execute a narrow, allow-listed local action; never pass model text to a shell."""
    try:
        args = json.loads(raw_arguments or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "error": "Invalid tool arguments."}
    if not isinstance(args, dict):
        return {"ok": False, "error": "Tool arguments must be an object."}

    if name == "search_web":
        query = str(args.get("query") or "").strip()[:300]
        if not query:
            return {"ok": False, "error": "Search query was empty."}
        url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(query)
        return {"ok": True, "action": "open web search", "query": query, "open": [url]}

    if name == "open_website":
        url = str(args.get("url") or "").strip()[:2048]
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("https", "http") or not parsed.netloc or parsed.username or parsed.password:
            return {"ok": False, "error": "Only ordinary HTTP or HTTPS website URLs can be opened."}
        return {"ok": True, "action": "open website", "host": parsed.netloc, "open": [url]}

    if name == "open_app":
        app = str(args.get("app") or "").strip().lower()
        allowed = {"calculator", "notepad", "file explorer", "paint", "spotify"}
        if app not in allowed:
            return {"ok": False, "error": "That app is not in JARVIS's launch allowlist."}
        return {"ok": True, "action": f"request launch of {app}", "launch_app": app}

    return {"ok": False, "error": "That action is not available."}


def think(cfg: dict[str, str], text: str) -> tuple[str, list[str], list[str]]:
    with _lock:
        messages = list(_history) + [{"role": "user", "content": text}]
    payload = {
        "model": cfg["OPENROUTER_MODEL"],
        "messages": [{"role": "system", "content": system_prompt(cfg)}, *messages],
        "max_tokens": 4000,
        "reasoning": {"effort": "none"},  # skip the thinking step, so spoken replies come back fast
        "tools": AGENT_TOOLS,
        "tool_choice": "auto",
    }
    conversation = list(payload["messages"])
    action_results = []
    open_urls: list[str] = []
    launch_apps: list[str] = []
    for _ in range(3):
        payload["messages"] = conversation
        try:
            data = openrouter_post(cfg, payload)
        except OpenRouterError as err:
            if err.status != 400:
                raise
            if "reasoning" in payload:
                del payload["reasoning"]
                continue
            raise
        choices = data.get("choices") or [{}]
        message = choices[0].get("message") or {}
        calls = message.get("tool_calls") or []
        if not calls:
            content = message.get("content")
            reply = " ".join(content.split()) if isinstance(content, str) else ""
            break
        conversation.append({"role": "assistant", "content": message.get("content"), "tool_calls": calls})
        for call in calls:
            function = call.get("function") or {}
            result = run_agent_tool(str(function.get("name") or ""), str(function.get("arguments") or "{}"))
            action_results.append(result)
            open_urls.extend(str(url) for url in result.get("open") or [])
            if result.get("launch_app"):
                launch_apps.append(str(result["launch_app"]))
            conversation.append({
                "role": "tool",
                "tool_call_id": call.get("id"),
                "content": json.dumps(result, ensure_ascii=False),
            })
    else:
        reply = "I couldn't complete that action, sir. Please try one request at a time."

    if action_results and any(not result.get("ok") for result in action_results):
        reply = "I couldn't complete that action, sir. " + str(action_results[-1].get("error") or "Please try again.")
    elif action_results and not reply:
        reply = "; ".join(str(result.get("action")) for result in action_results if result.get("action"))
    reply = reply or f"I'm not sure what to say to that, {cfg['JARVIS_CALLS_YOU']}."
    with _lock:
        _history.extend([{"role": "user", "content": text}, {"role": "assistant", "content": reply}])
        del _history[:-16]  # keep the last 8 exchanges
    return reply, open_urls, launch_apps


def brain_error(err: OpenRouterError, cfg: dict[str, str]) -> str:
    title = cfg["JARVIS_CALLS_YOU"]
    if err.status == 401:
        return f"My brain key isn't working, {title}. Check OPENROUTER_API_KEY in the .env file."
    if err.status == 402:
        return f"Your OpenRouter account is out of credit, {title}. Check it at openrouter.ai."
    if err.status == 429:
        if "per-day" in err.detail:
            return f"I've used up today's free questions, {title}. They reset tomorrow."
        return f"I'm being rate limited, {title}. Give me a moment and try again."
    if err.status == 403:
        return f"OpenRouter blocked that request, {title}. The reason is in the JARVIS window."
    if err.status in (400, 404):
        return f"OpenRouter won't run the model {cfg['OPENROUTER_MODEL']}, {title}. The reason is in the JARVIS window."
    if err.status == 0:
        return f"I can't reach my brain, {title}. Check your internet connection."
    return f"OpenRouter is having a moment, {title}. Try again shortly."


# ---------------------------------------------------------------- voice (Fish Audio)

_voice_override: str | None = None  # set by a protocol with a "voice" field, until restart


def speak(cfg: dict[str, str], text: str) -> tuple[bytes | None, str | None]:
    key = cfg.get("FISH_API_KEY")
    if not key:
        return None, "No Fish Audio key yet, so you're hearing the backup voice. Add FISH_API_KEY to the .env file."
    body = json.dumps({
        "text": text,
        "reference_id": _voice_override or cfg["FISH_VOICE_ID"],
        "format": "mp3",
        "mp3_bitrate": 128,
        "normalize": True,
        "latency": "balanced",
    }).encode("utf-8")
    request = urllib.request.Request(FISH_TTS_URL, data=body, method="POST", headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "model": cfg["FISH_MODEL"],
    })
    try:
        with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310 - fixed https URL
            return response.read(), None
    except urllib.error.HTTPError as err:
        detail = err.read()[:300].decode("utf-8", "replace")
        log(f"Fish Audio error {err.code}: {detail}")
        if err.code in (401, 403):
            return None, "Fish Audio didn't accept the key. Check FISH_API_KEY in the .env file."
        if err.code == 402:
            return None, "Your Fish Audio API credit is empty. Add credit on fish.audio and JARVIS gets his voice back."
        if err.code in (400, 404, 422):
            return None, "Fish Audio couldn't use that voice. Check FISH_VOICE_ID and FISH_MODEL in the .env file."
        return None, f"Fish Audio returned an error ({err.code}). Using the backup voice for now."
    except (urllib.error.URLError, TimeoutError):
        return None, "Can't reach Fish Audio right now. Using the backup voice."


# ---------------------------------------------------------------- protocols

def load_protocols() -> list[dict]:
    try:
        data = json.loads(PROTOCOLS_FILE.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return []
    except json.JSONDecodeError as err:
        log(f"protocols.json has a typo ({err}). Ignoring it until it's fixed.")
        return []
    return [p for p in data if isinstance(p, dict) and p.get("say")] if isinstance(data, list) else []


def _words(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", text.lower()).split())


def match_protocol(text: str) -> dict | None:
    said = f" {_words(text)} "
    for protocol in load_protocols():
        if f" {_words(protocol['say'])} " in said:
            return protocol
    return None


def open_url(url: str) -> None:
    if NO_BROWSER:
        log(f"(would open) {url}")
    else:
        webbrowser.open(url)


# ---------------------------------------------------------------- web server

class Handler(BaseHTTPRequestHandler):
    server_version = "JARVIS"

    def log_message(self, format: str, *args) -> None:  # keep the window readable
        pass

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        try:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, code: int, payload: dict) -> None:
        self._send(code, json.dumps(payload).encode("utf-8"), "application/json")

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > 100_000:
            return {}
        try:
            data = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            self._send(200, INDEX_HTML.read_bytes(), "text/html; charset=utf-8")
        elif path == "/api/status":
            cfg = load_settings()
            self._json(200, {
                "voice": bool(cfg.get("FISH_API_KEY")),
                "brain": bool(cfg.get("OPENROUTER_API_KEY")),
                "model": cfg["OPENROUTER_MODEL"],
                "calls": cfg["JARVIS_CALLS_YOU"],
                "protocols": [p["say"] for p in load_protocols()],
            })
        elif path == "/favicon.ico":
            self._send(204, b"", "image/x-icon")
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        global _voice_override
        path = self.path.split("?", 1)[0]
        cfg = load_settings()
        data = self._read_json()
        text = str(data.get("text") or "").strip()[:2000]
        title = cfg["JARVIS_CALLS_YOU"]

        if path == "/api/chat":
            if not text:
                self._json(400, {"error": "Say something first."})
                return
            log(f"You:    {text}")
            spotify = re.fullmatch(r"(?:please\s+)?play\s+(.+?)\s+(?:in|on)\s+spotify[.!?]*", text, re.IGNORECASE)
            if spotify:
                query = spotify.group(1).strip()
                url = f"https://open.spotify.com/search/{urllib.parse.quote(query)}?jarvis=play"
                reply = f"Searching Spotify for {query}, sir. The top track will start if the JARVIS Spotify extension is enabled."
                self._json(200, {"reply": reply, "protocol": "spotify search", "open": [url]})
                return
            open_site = re.fullmatch(
                r"(?:please\s+)?(?:(?:can|could)\s+you\s+)?(?:please\s+)?"
                r"open\s+(?:the\s+)?(https?://[^\s]+|(?:www\.)?[a-z0-9-]+(?:\.[a-z0-9-]+)+(?:/[^\s]*)?)[.!?]*",
                text,
                re.IGNORECASE,
            )
            if open_site:
                url = open_site.group(1).rstrip(".,!?")
                if not url.lower().startswith(("http://", "https://")):
                    url = "https://" + url
                parsed = urllib.parse.urlparse(url)
                if not parsed.netloc or parsed.username or parsed.password:
                    self._json(200, {"reply": f"I couldn't open that website, {title}.", "error": "invalid_url"})
                    return
                reply = f"Opening {parsed.netloc} in your browser, {title}."
                self._json(200, {"reply": reply, "open": [url]})
                return
            web_search = re.fullmatch(
                r"(?:please\s+)?(?:search|google|look\s+up)\s+(?:the\s+web\s+for\s+|online\s+for\s+|for\s+)?(.+?)[.!?]*",
                text,
                re.IGNORECASE,
            )
            if web_search:
                query = web_search.group(1).strip()
                url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(query)
                reply = f"Opening a web search for {query}, {title}."
                self._json(200, {"reply": reply, "open": [url]})
                return
            app_request = re.fullmatch(
                r"(?:please\s+)?(?:(?:can|could)\s+you\s+)?(?:please\s+)?"
                r"(?:open|launch|start|run)\s+(?:the\s+)?"
                r"(calculator|notepad|file\s+explorer|paint|spotify)[.!?]*",
                text,
                re.IGNORECASE,
            )
            if app_request:
                app = re.sub(r"\s+", " ", app_request.group(1).lower())
                result = run_agent_tool("open_app", json.dumps({"app": app}))
                if result.get("ok"):
                    reply = f"Requesting Windows to open {app.title()}, {title}."
                else:
                    reply = f"I couldn't open {app.title()}, {title}. {result.get('error', 'Please try again.')}"
                log(f"JARVIS: {reply} ({result.get('action') or result.get('error')})")
                self._json(200, {"reply": reply, "launch_apps": [app] if result.get("ok") else []})
                return
            mail_request = re.search(
                r"\b(?:check|read|summari[sz]e|review|show|fetch|retrieve|look\s+at)\b.*"
                r"\b(?:e-?mails?|mails?|messages?|inbox)\b|"
                r"\b(?:e-?mails?|mails?|messages?|inbox)\b.*"
                r"\b(?:check|read|summari[sz]e|review|show|fetch|retrieve)\b",
                text,
                re.IGNORECASE | re.DOTALL,
            )
            if mail_request:
                reply = (
                    f"I can't read or summarize your email yet, {title}; Gmail isn't connected "
                    "to this JARVIS app. I'll open Gmail so you can review your inbox."
                )
                self._json(200, {
                    "reply": reply,
                    "protocol": "open Gmail",
                    "open": ["https://mail.google.com"],
                    "error": "email_not_connected",
                })
                return
            protocol = match_protocol(text)
            if protocol:
                urls = [str(url) for url in protocol.get("open") or []]
                if protocol.get("voice"):
                    voice_id = str(protocol["voice"]).strip()
                    _voice_override = None if voice_id == "default" else voice_id
                reply = str(protocol.get("reply") or "Right away, {you}.").replace("{you}", title)
                log(f"JARVIS: {reply}  (protocol)")
                self._json(200, {"reply": reply, "protocol": protocol["say"], "open": urls})
                return
            if not cfg.get("OPENROUTER_API_KEY"):
                self._json(200, {"reply": f"My brain isn't connected yet, {title}. Add OPENROUTER_API_KEY to the .env file and restart me.", "error": "brain"})
                return
            try:
                reply, open_urls, launch_apps = think(cfg, text)
            except OpenRouterError as err:
                log(f"OpenRouter error {err}")
                self._json(200, {"reply": brain_error(err, cfg), "error": "brain"})
                return
            except Exception as err:  # noqa: BLE001 - keep JARVIS alive and report it
                log(f"Unexpected error: {err!r}")
                self._json(200, {"reply": f"Something went wrong in my head, {title}. The details are in the JARVIS window.", "error": "internal"})
                return
            log(f"JARVIS: {reply}")
            self._json(200, {"reply": reply, "open": open_urls, "launch_apps": launch_apps})
            return

        if path == "/api/tts":
            if not text:
                self._json(400, {"error": "Nothing to say."})
                return
            audio, problem = speak(cfg, text)
            if audio:
                self._send(200, audio, "audio/mpeg")
            else:
                self._json(502, {"error": problem})
            return

        if path == "/api/reset":
            with _lock:
                _history.clear()
            self._json(200, {"ok": True})
            return

        self._json(404, {"error": "not found"})


class Server(ThreadingHTTPServer):
    # Windows lets a second program share a port that's already taken when address reuse is on.
    # With it off the bind fails instead, so main() moves on to the next free port.
    allow_reuse_address = os.name != "nt"


BANNER = r"""
       _   _    ____  __     __ ___  ____
      | | / \  |  _ \ \ \   / /|_ _|/ ___|
   _  | |/ _ \ | |_) | \ \ / /  | | \___ \
  | |_| / ___ \|  _ <   \ V /   | |  ___) |
   \___/_/   \_\_| \_\   \_/   |___||____/
"""


def main() -> None:
    try:
        # Line-buffered, so the address shows up right away even when the output goes to a log file.
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except (AttributeError, ValueError):
        pass
    print(BANNER)
    cfg = first_run(load_settings())

    port = int(cfg.get("PORT") or 8765)
    server = None
    for candidate in range(port, port + 20):
        try:
            server = Server(("127.0.0.1", candidate), Handler)
            break
        except OSError:
            continue
    if server is None:
        print(f"\n  Couldn't find a free port near {port}. Close other apps or set PORT in .env.\n")
        sys.exit(1)

    url = f"http://127.0.0.1:{server.server_address[1]}"
    print("\n  ==================================================")
    print("    J.A.R.V.I.S. is online")
    print(f"    Open {url}  (Chrome or Edge, for voice input)")
    print(f"    Voice: Fish Audio {cfg['FISH_VOICE_ID']} ({cfg['FISH_MODEL']})")
    print(f"    Brain: OpenRouter {cfg['OPENROUTER_MODEL']}" if cfg.get("OPENROUTER_API_KEY") else "    Brain: not connected yet")
    print("    Close this window to shut JARVIS down.")
    print("  ==================================================\n")
    if not NO_BROWSER:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  JARVIS offline. Goodbye.\n")


if __name__ == "__main__":
    main()
