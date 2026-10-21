"""OAuth 2.0 authorization-code login for Upstox, run locally.

Flow (https://upstox.com/developer/api-documentation/authentication):
 1. Open https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id=..&redirect_uri=..&state=..
 2. You log in on upstox.com (with your own 2FA/TOTP — never bypassed or automated here).
 3. Upstox redirects to UPSTOX_REDIRECT_URI?code=...&state=...
 4. We POST the single-use code to /v2/login/authorization/token and store the access token.

Access tokens expire at 03:30 IST the next day regardless of issue time, so the
stored token carries an expiry and the app requires re-login each trading day.

The token is stored in secrets/token.json (git-ignored). It can also be supplied
via UPSTOX_ACCESS_TOKEN in .env (e.g. a token you generated manually on the
developer portal); env wins only if token.json is absent or expired.
"""
from __future__ import annotations

import json
import os
import secrets as pysecrets
import threading
import webbrowser
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from ..config import ROOT, Secrets
from ..data.calendar import IST, now_ist
from ..logging_setup import get_logger
from .upstox import UpstoxClient

log = get_logger("auth")
TOKEN_FILE = ROOT / "secrets" / "token.json"


def token_expiry(issued: datetime) -> datetime:
    """Upstox rule: valid until 03:30 IST on the following day; a token issued
    before 03:30 expires at 03:30 the same day."""
    issued = issued.astimezone(IST)
    cutoff = issued.replace(hour=3, minute=30, second=0, microsecond=0)
    return cutoff if issued < cutoff else cutoff + timedelta(days=1)


def save_token(access_token: str, profile: dict | None = None, path: Path = TOKEN_FILE) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    issued = now_ist()
    rec = {"access_token": access_token, "issued_at": issued.isoformat(),
           "expires_at": token_expiry(issued).isoformat(),
           "user_id": (profile or {}).get("user_id"),
           "exchanges": (profile or {}).get("exchanges"), "products": (profile or {}).get("products"),
           "order_types": (profile or {}).get("order_types")}
    path.write_text(json.dumps(rec, indent=2), encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return rec


def load_token(path: Path = TOKEN_FILE) -> dict | None:
    """Returns a valid (unexpired) token record or None."""
    if path.exists():
        rec = json.loads(path.read_text(encoding="utf-8"))
        if datetime.fromisoformat(rec["expires_at"]) > now_ist():
            return rec
    env = Secrets.from_env().access_token
    if env:
        return {"access_token": env, "expires_at": None, "source": "env (expiry unknown; validated by API call)"}
    return None


def clear_token(path: Path = TOKEN_FILE) -> None:
    if path.exists():
        path.unlink()


class _Handler(BaseHTTPRequestHandler):
    result: dict = {}

    def do_GET(self):  # noqa: N802
        q = parse_qs(urlparse(self.path).query)
        _Handler.result = {"code": (q.get("code") or [""])[0], "state": (q.get("state") or [""])[0]}
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"<h2>INDIA QUANT: login received.</h2><p>You can close this tab and return to the "
                         b"terminal.</p>")

    def log_message(self, *a):  # silence: query string contains the auth code
        pass


def interactive_login(open_browser: bool = True, timeout_s: int = 300) -> dict:
    sec = Secrets.from_env()
    missing = [n for n, v in (("UPSTOX_CLIENT_ID", sec.client_id), ("UPSTOX_CLIENT_SECRET", sec.client_secret),
                              ("UPSTOX_REDIRECT_URI", sec.redirect_uri)) if not v]
    if missing:
        raise SystemExit(f"Missing in .env: {', '.join(missing)}. See README 'FINAL STEP'.")
    ru = urlparse(sec.redirect_uri)
    if ru.hostname not in ("127.0.0.1", "localhost"):
        raise SystemExit("UPSTOX_REDIRECT_URI must point to this PC, e.g. http://127.0.0.1:8765/callback")
    state = pysecrets.token_urlsafe(16)
    url = UpstoxClient.authorize_url(sec.client_id, sec.redirect_uri, state)
    srv = HTTPServer((ru.hostname, ru.port or 80), _Handler)
    t = threading.Thread(target=srv.handle_request, daemon=True)
    _Handler.result = {}
    t.start()
    print("\nOpen this URL and log in to Upstox (your password/2FA stay on upstox.com):\n")
    print(url, "\n")
    if open_browser:
        webbrowser.open(url)
    t.join(timeout_s)
    srv.server_close()
    res = _Handler.result
    if not res.get("code"):
        raise SystemExit("No authorization code received (timed out or cancelled).")
    if res.get("state") != state:
        raise SystemExit("State mismatch: possible CSRF. Aborting login.")
    client = UpstoxClient()
    data = client.exchange_code(res["code"], sec.client_id, sec.client_secret, sec.redirect_uri)
    rec = save_token(data["access_token"], data)
    log.info("Login OK for user %s; token expires %s", rec.get("user_id"), rec["expires_at"])
    return rec
