"""Logging with mandatory secret redaction.

Every handler gets RedactingFilter, which scrubs bearer tokens, auth headers,
client secrets, OTP/PIN fields and any literal secret value loaded from env.
"""
from __future__ import annotations

import logging
import logging.handlers
import os
import re

from .config import LOG_DIR

_PATTERNS = [
    (re.compile(r"(Bearer\s+)[A-Za-z0-9\-\._~\+/=]+", re.I), r"\1[REDACTED]"),
    (re.compile(r"(['\"]?(?:authorization|access_token|extended_token|client_secret|api[_-]?secret|"
                r"password|totp|otp|pin|code)['\"]?\s*[:=]\s*['\"]?)([^'\"\s,&}]+)", re.I), r"\1[REDACTED]"),
]
_SECRET_ENV = ("UPSTOX_CLIENT_SECRET", "UPSTOX_ACCESS_TOKEN", "UPSTOX_CLIENT_ID")


def redact(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    for pat, rep in _PATTERNS:
        text = pat.sub(rep, text)
    for name in _SECRET_ENV:
        val = os.environ.get(name, "")
        if val and len(val) >= 6:
            text = text.replace(val, "[REDACTED]")
    return text


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            msg = str(record.msg)
        record.msg = redact(msg)
        record.args = ()
        return True


_configured = False


def setup_logging(level: str = "INFO", to_file: bool = True) -> logging.Logger:
    global _configured
    root = logging.getLogger("indiaquant")
    if _configured:
        return root
    root.setLevel(level)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    sh.addFilter(RedactingFilter())
    root.addHandler(sh)
    if to_file:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(LOG_DIR / "indiaquant.log", maxBytes=5_000_000,
                                                  backupCount=5, encoding="utf-8")
        fh.setFormatter(fmt)
        fh.addFilter(RedactingFilter())
        root.addHandler(fh)
    _configured = True
    return root


def get_logger(name: str) -> logging.Logger:
    lg = logging.getLogger(f"indiaquant.{name}")
    if not any(isinstance(f, RedactingFilter) for f in lg.filters):
        lg.addFilter(RedactingFilter())
    return lg
