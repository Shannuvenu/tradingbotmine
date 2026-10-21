# Security

* **Secrets** live only in `.env` (client id/secret, redirect URI) and `secrets/token.json` (daily access token). Both are
  in `.gitignore`. Nothing secret is stored in `config/settings.json` or the database.
* **Logging**: every handler carries `RedactingFilter` (bearer tokens, `access_token`, `client_secret`, `code`, `pin`,
  `otp`, plus the literal values of secret env vars). HTTP headers are never formatted into log messages. Unit-tested.
* **Login**: standard Upstox OAuth in your browser. Your password/2FA never touch this app. The TOTP+PIN token API is
  deliberately not used (it would require storing your PIN and TOTP secret on disk).
* **CSRF**: login uses a random `state` and rejects mismatches. The callback server binds only to `127.0.0.1` and
  handles exactly one request.
* **Dashboard** binds to `127.0.0.1` (`.streamlit/config.toml` and `RUN_DASHBOARD.bat`); `validate-config` flags any
  other host. Do not port-forward it. It has no login of its own because it is local-only.
* **Orders**: no code path places an order unless state is LIVE_ACTIVE for today's date, reached only via LIVE_READY
  checks + typed confirmation. Restart downgrades LIVE_ACTIVE → LIVE_READY. KILL file halts instantly.
* **Static IP**: Upstox only accepts order calls from the IPs you register. Do not try to bypass this.
* **Revoking access**: `python -m indiaquant.cli logout` (calls Upstox logout + deletes local token). To fully revoke,
  delete or regenerate the app secret at https://account.upstox.com/developer/apps and change your Upstox password if
  you suspect exposure.
* **Never** paste `.env` contents, tokens or the `secrets/` folder into chats, screenshots, issues or GitHub.
