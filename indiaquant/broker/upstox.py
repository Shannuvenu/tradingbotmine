"""Upstox REST adapter (documented HTTP endpoints, no hidden behaviour).

Endpoint verification status (see docs/RESEARCH.md for source URLs):
  VERIFIED on official docs 2026-10-21: authorize dialog, token, place order v3 (api-hft host),
  historical candle v3, LTP v3, funds v3, order details, option chain, brokerage, holidays,
  rate limits, static-IP rules.
  FROM DOCS INDEX, PATH NOT RE-READ THIS SESSION (marked `verify=True` below): positions,
  holdings, order book, order history, trades, modify v3, cancel v3, margin, profile,
  market status, intraday v3, logout, kill switch, static IP get. The health-check command
  calls each read-only one and reports any 404 so a path change is caught immediately.

Safety rules implemented here:
  * Order-mutating calls (place/modify/cancel) are NEVER retried automatically.
    A timeout raises OrderStatusUnknown; the OrderManager must reconcile by tag first.
  * Only GETs are retried (exponential backoff), and never on 4xx except 429.
  * Tokens/headers are never logged (RedactingFilter + we never format headers into messages).
  * MARKET orders are rejected client-side: Upstox no longer permits them via API (Apr 2026).
"""
from __future__ import annotations

import time
import urllib.parse
from dataclasses import dataclass

import pandas as pd
import requests

from ..logging_setup import get_logger
from .ratelimit import order_limiter, standard_limiter

log = get_logger("upstox")

API = "https://api.upstox.com"
HFT = "https://api-hft.upstox.com"
# Sandbox host is not printed on the docs' sandbox page; this matches the official SDK's sandbox
# configuration. Override with UPSTOX_SANDBOX_BASE if Upstox changes it.
import os as _os
SANDBOX = _os.environ.get("UPSTOX_SANDBOX_BASE", "https://api-sandbox.upstox.com")

ENDPOINTS = {
    "authorize": (API, "GET", "/v2/login/authorization/dialog"),
    "token": (API, "POST", "/v2/login/authorization/token"),
    "logout": (API, "DELETE", "/v2/logout"),
    "profile": (API, "GET", "/v2/user/profile"),
    "funds_v3": (API, "GET", "/v3/user/get-funds-and-margin"),
    "static_ip": (API, "GET", "/v2/user/ip"),
    "kill_switch": (API, "GET", "/v2/user/kill-switch"),
    "positions": (API, "GET", "/v2/portfolio/short-term-positions"),
    "holdings": (API, "GET", "/v2/portfolio/long-term-holdings"),
    "order_book": (API, "GET", "/v2/order/retrieve-all"),
    "order_details": (API, "GET", "/v2/order/details"),
    "order_history": (API, "GET", "/v2/order/history"),
    "trades_today": (API, "GET", "/v2/order/trades/get-trades-for-day"),
    "order_trades": (API, "GET", "/v2/order/trades"),
    "place_v3": (HFT, "POST", "/v3/order/place"),
    "modify_v3": (HFT, "PUT", "/v3/order/modify"),
    "cancel_v3": (HFT, "DELETE", "/v3/order/cancel"),
    "hist_v3": (API, "GET", "/v3/historical-candle/{key}/{unit}/{interval}/{to}/{frm}"),
    "intraday_v3": (API, "GET", "/v3/historical-candle/intraday/{key}/{unit}/{interval}"),
    "ltp_v3": (API, "GET", "/v3/market-quote/ltp"),
    "quote_full": (API, "GET", "/v2/market-quote/quotes"),
    "option_chain": (API, "GET", "/v2/option/chain"),
    "option_contracts": (API, "GET", "/v2/option/contract"),
    "brokerage": (API, "GET", "/v2/charges/brokerage"),
    "margin": (API, "POST", "/v2/charges/margin"),
    "holidays": (API, "GET", "/v2/market/holidays"),
    "market_status": (API, "GET", "/v2/market/status/{exchange}"),
    "feed_authorize_v3": (API, "GET", "/v3/feed/market-data-feed/authorize"),
    "news": (API, "GET", "/v2/news"),
    "corporate_actions": (API, "GET", "/v2/fundamentals/{isin}/corporate-actions"),
    "portfolio_feed_authorize": (API, "GET", "/v2/feed/portfolio-stream-feed/authorize"),
}

READ_ONLY_HEALTH = ["profile", "funds_v3", "positions", "holdings", "order_book", "trades_today", "holidays"]


class UpstoxError(Exception):
    def __init__(self, message: str, status: int = 0, code: str = "", endpoint: str = ""):
        super().__init__(message)
        self.status, self.code, self.endpoint = status, code, endpoint


class AuthExpired(UpstoxError):
    pass


class OrderStatusUnknown(UpstoxError):
    """Request may or may not have reached the exchange. Reconcile before acting."""


class OrderRejected(UpstoxError):
    pass


@dataclass
class OrderRequest:
    instrument_key: str
    side: str            # BUY / SELL
    quantity: int
    price: float
    order_type: str = "LIMIT"   # LIMIT / SL (SL-M allowed only with market protection)
    product: str = "I"          # I intraday / D delivery
    validity: str = "DAY"
    trigger_price: float = 0.0
    tag: str = ""

    def payload(self) -> dict:
        return {
            "quantity": int(self.quantity), "product": self.product, "validity": self.validity,
            "price": float(self.price), "tag": self.tag, "instrument_token": self.instrument_key,
            "order_type": self.order_type, "transaction_type": self.side, "disclosed_quantity": 0,
            "trigger_price": float(self.trigger_price), "is_amo": False, "slice": False,
        }


class UpstoxClient:
    def __init__(self, access_token: str = "", db=None, timeout: float = 10.0, sandbox: bool = False,
                 algo_name: str = "", session: requests.Session | None = None):
        self._token = access_token
        self.db = db
        self.timeout = timeout
        self.sandbox = sandbox
        self.algo_name = algo_name
        self.s = session or requests.Session()
        self.order_rl = order_limiter()
        self.std_rl = standard_limiter()
        self.last_ok: float | None = None
        self.consecutive_errors = 0

    # ---------------------------------------------------------------- utils
    def set_token(self, token: str) -> None:
        self._token = token

    @property
    def has_token(self) -> bool:
        return bool(self._token)

    def _headers(self, api_version: str | None = None) -> dict:
        h = {"Accept": "application/json", "Content-Type": "application/json"}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        if api_version:
            h["Api-Version"] = api_version
        if self.algo_name:
            h["X-Algo-Name"] = self.algo_name
        return h

    def _url(self, name: str, **path) -> tuple[str, str]:
        host, method, p = ENDPOINTS[name]
        if self.sandbox and name in ("place_v3", "modify_v3", "cancel_v3"):
            host = SANDBOX
        if path:
            p = p.format(**{k: urllib.parse.quote(str(v), safe="") for k, v in path.items()})
        return method, host + p

    def _record_error(self, name: str, status: int, msg: str) -> None:
        self.consecutive_errors += 1
        log.warning("API error %s status=%s: %s", name, status, msg[:300])
        if self.db is not None:
            try:
                self.db.api_error(name, status, msg)
            except Exception:
                pass

    def _parse(self, name: str, resp: requests.Response) -> dict:
        try:
            body = resp.json()
        except ValueError:
            body = {"status": "error", "errors": [{"message": resp.text[:500]}]}
        if resp.status_code == 401:
            self._record_error(name, 401, "unauthorized / token expired")
            raise AuthExpired("Access token invalid or expired (Upstox tokens expire 03:30 IST daily). "
                              "Run: python -m indiaquant.cli login", 401, endpoint=name)
        if resp.status_code >= 400 or body.get("status") == "error":
            errs = body.get("errors") or [{}]
            e0 = errs[0] if isinstance(errs, list) and errs else {}
            msg = e0.get("message") or str(body)[:300]
            code = e0.get("errorCode") or e0.get("error_code") or ""
            self._record_error(name, resp.status_code, f"{code} {msg}")
            cls = OrderRejected if name in ("place_v3", "modify_v3", "cancel_v3") else UpstoxError
            raise cls(msg, resp.status_code, code, name)
        self.consecutive_errors = 0
        self.last_ok = time.time()
        return body

    def _get(self, name: str, params: dict | None = None, retries: int = 3, api_version: str | None = None,
             **path) -> dict:
        method, url = self._url(name, **path)
        delay = 1.0
        for attempt in range(retries + 1):
            self.std_rl.acquire()
            try:
                resp = self.s.request(method, url, params=params, headers=self._headers(api_version),
                                      timeout=self.timeout)
            except (requests.ConnectionError, requests.Timeout) as e:
                self._record_error(name, 0, f"network: {type(e).__name__}")
                if attempt == retries:
                    raise UpstoxError(f"network failure on {name}: {type(e).__name__}", 0, endpoint=name)
                time.sleep(delay)
                delay *= 2
                continue
            if resp.status_code in (429, 500, 502, 503, 504) and attempt < retries:
                self._record_error(name, resp.status_code, "retryable")
                time.sleep(delay)
                delay *= 2
                continue
            return self._parse(name, resp)
        raise UpstoxError("unreachable", endpoint=name)

    def _mutate(self, name: str, json_body: dict | None = None, params: dict | None = None) -> dict:
        """Single attempt. Network failure => OrderStatusUnknown (never retried here)."""
        method, url = self._url(name)
        self.order_rl.acquire()
        try:
            resp = self.s.request(method, url, json=json_body, params=params, headers=self._headers(),
                                  timeout=self.timeout)
        except (requests.ConnectionError, requests.Timeout) as e:
            self._record_error(name, 0, f"network: {type(e).__name__}")
            raise OrderStatusUnknown(f"{name} outcome unknown ({type(e).__name__}); reconcile by tag before retry",
                                     0, endpoint=name)
        if resp.status_code >= 500:
            self._record_error(name, resp.status_code, "server error; outcome unknown")
            raise OrderStatusUnknown(f"{name} returned {resp.status_code}; outcome unknown", resp.status_code,
                                     endpoint=name)
        return self._parse(name, resp)

    # --------------------------------------------------------------- auth
    @staticmethod
    def authorize_url(client_id: str, redirect_uri: str, state: str) -> str:
        q = urllib.parse.urlencode({"response_type": "code", "client_id": client_id,
                                    "redirect_uri": redirect_uri, "state": state})
        return f"{API}{ENDPOINTS['authorize'][2]}?{q}"

    def exchange_code(self, code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
        _, url = self._url("token")
        resp = self.s.post(url, data={"code": code, "client_id": client_id, "client_secret": client_secret,
                                      "redirect_uri": redirect_uri, "grant_type": "authorization_code"},
                           headers={"Accept": "application/json",
                                    "Content-Type": "application/x-www-form-urlencoded"},
                           timeout=self.timeout)
        body = self._parse("token", resp)
        return body.get("data", body)

    def logout(self) -> dict:
        method, url = self._url("logout")
        return self._parse("logout", self.s.request(method, url, headers=self._headers(), timeout=self.timeout))

    # ------------------------------------------------------------ account
    def profile(self) -> dict:
        return self._get("profile")["data"]

    def funds(self) -> dict:
        return self._get("funds_v3", api_version="3.0")["data"]

    def available_cash(self) -> float:
        d = self.funds()
        return float(d["available_to_trade"]["cash_available_to_trade"]["total"])

    def static_ips(self) -> dict:
        return self._get("static_ip").get("data", {})

    def positions(self) -> list[dict]:
        return self._get("positions").get("data") or []

    def holdings(self) -> list[dict]:
        return self._get("holdings").get("data") or []

    def order_book(self) -> list[dict]:
        return self._get("order_book").get("data") or []

    def order_details(self, order_id: str) -> dict:
        return self._get("order_details", {"order_id": order_id})["data"]

    def order_history_by_tag(self, tag: str) -> list[dict]:
        return self._get("order_history", {"tag": tag}).get("data") or []

    def trades_today(self) -> list[dict]:
        return self._get("trades_today").get("data") or []

    # ------------------------------------------------------------- orders
    def place_order(self, req: OrderRequest) -> list[str]:
        if req.order_type == "MARKET":
            raise OrderRejected("MARKET orders are not permitted via Upstox API since Apr 2026; use LIMIT",
                                endpoint="place_v3")
        if req.quantity <= 0 or req.price <= 0:
            raise OrderRejected("quantity and price must be positive", endpoint="place_v3")
        body = self._mutate("place_v3", req.payload())
        return list(body.get("data", {}).get("order_ids") or [])

    def modify_order(self, order_id: str, quantity: int, price: float, order_type: str = "LIMIT",
                     trigger_price: float = 0.0, validity: str = "DAY") -> dict:
        return self._mutate("modify_v3", {"order_id": order_id, "quantity": int(quantity), "price": float(price),
                                          "order_type": order_type, "trigger_price": float(trigger_price),
                                          "validity": validity, "disclosed_quantity": 0})

    def cancel_order(self, order_id: str) -> dict:
        return self._mutate("cancel_v3", params={"order_id": order_id})

    # --------------------------------------------------------- market data
    @staticmethod
    def candles_to_df(payload: dict) -> pd.DataFrame:
        rows = (payload.get("data") or {}).get("candles") or []
        if not rows:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume", "oi"])
        df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume", "oi"][:len(rows[0])])
        df["ts"] = pd.to_datetime(df["ts"], format="ISO8601")
        if "oi" not in df:
            df["oi"] = 0.0
        return df.set_index("ts").sort_index()

    def historical(self, key: str, unit: str, interval: int, to_date: str, from_date: str) -> pd.DataFrame:
        return self.candles_to_df(self._get("hist_v3", key=key, unit=unit, interval=interval, to=to_date,
                                            frm=from_date))

    def intraday(self, key: str, unit: str = "minutes", interval: int = 1) -> pd.DataFrame:
        return self.candles_to_df(self._get("intraday_v3", key=key, unit=unit, interval=interval))

    def ltp(self, keys: list[str]) -> dict[str, dict]:
        """Returns {instrument_key: {last_price, volume, cp, ...}} keyed by the request key.
        The response map is keyed by EXCHANGE:SYMBOL, so we re-key via instrument_token."""
        out = {}
        for i in range(0, len(keys), 500):
            body = self._get("ltp_v3", {"instrument_key": ",".join(keys[i:i + 500])})
            for _, v in (body.get("data") or {}).items():
                tok = v.get("instrument_token")
                if tok:
                    out[tok] = v
        return out

    def full_quote(self, keys: list[str]) -> dict[str, dict]:
        out = {}
        for i in range(0, len(keys), 500):
            body = self._get("quote_full", {"instrument_key": ",".join(keys[i:i + 500])})
            for _, v in (body.get("data") or {}).items():
                tok = v.get("instrument_token")
                if tok:
                    out[tok] = v
        return out

    def option_chain(self, underlying_key: str, expiry_date: str) -> list[dict]:
        return self._get("option_chain", {"instrument_key": underlying_key, "expiry_date": expiry_date}).get(
            "data") or []

    def brokerage(self, key: str, qty: int, product: str, side: str, price: float) -> dict:
        return self._get("brokerage", {"instrument_token": key, "quantity": qty, "product": product,
                                       "transaction_type": side, "price": price})["data"]["charges"]

    def margin(self, legs: list[dict]) -> dict:
        method, url = self._url("margin")
        self.std_rl.acquire()
        resp = self.s.request(method, url, json={"instruments": legs}, headers=self._headers(),
                              timeout=self.timeout)
        return self._parse("margin", resp).get("data", {})

    def holidays(self) -> list[dict]:
        return self._get("holidays").get("data") or []

    def market_status(self, exchange: str = "NSE") -> dict:
        return self._get("market_status", exchange=exchange).get("data", {})

    def news(self, keys: list[str], page_size: int = 50) -> dict:
        """Upstox News API (verified 2026-10-21). Returns {instrument_key: [items]}; max 30 keys/request."""
        out = {}
        for i in range(0, len(keys), 30):
            body = self._get("news", {"category": "instrument_keys", "instrument_keys": ",".join(keys[i:i + 30]),
                                      "page_size": page_size})
            out.update(body.get("data") or {})
        return out

    def corporate_actions(self, isin: str) -> list[dict]:
        return self._get("corporate_actions", isin=isin).get("data") or []

    def feed_authorize(self) -> str:
        d = self._get("feed_authorize_v3").get("data", {})
        return d.get("authorized_redirect_uri") or d.get("authorizedRedirectUri") or ""
