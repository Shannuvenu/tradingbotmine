"""Configuration: secrets from environment/.env, tunable limits from config/settings.json.

Secrets are NEVER read from settings.json and NEVER logged.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data_store"
LOG_DIR = ROOT / "logs"
REPORT_DIR = ROOT / "reports"
SETTINGS_FILE = CONFIG_DIR / "settings.json"
ENV_FILE = ROOT / ".env"


def load_env_file(path: Path = ENV_FILE) -> None:
    """Minimal .env loader (no dependency). Existing env vars win."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


@dataclass
class RiskLimits:
    """Conservative defaults for a ₹1,000 account. Rationale in docs/RISK.md."""
    starting_capital: float = 1000.0
    max_capital_exposure_pct: float = 0.80      # never deploy more than 80% of available cash
    max_risk_per_trade_pct: float = 0.02        # ₹20 modelled stop-loss risk on ₹1,000
    max_daily_loss_pct: float = 0.05            # ₹50/day -> automatic HALT
    max_open_positions: int = 2
    max_orders_per_session: int = 10
    max_order_notional: float = 800.0
    max_spread_pct: float = 0.005               # 0.5% bid/ask spread
    max_data_age_seconds: int = 30
    max_consecutive_failures: int = 3
    max_concentration_pct: float = 0.80
    max_cost_to_risk_ratio: float = 0.50        # reject if est. round-trip costs > 50% of planned risk
    min_reward_cost_ratio: float = 3.0          # expected move must be >= 3x costs
    allow_short: bool = False                   # intraday shorting off by default
    allow_derivatives: bool = False             # F&O off by default
    allow_option_buying: bool = False
    allow_option_writing: bool = False          # naked writing never enabled by code path
    allowed_products: tuple = ("I", "D")        # no MTF
    limit_price_buffer_pct: float = 0.002       # marketable-limit buffer (MARKET orders are not permitted via API)
    intraday_entry_cutoff: str = "14:45"
    intraday_squareoff_time: str = "15:10"


@dataclass
class Settings:
    risk: RiskLimits = field(default_factory=RiskLimits)
    watchlist: list = field(default_factory=lambda: [
        # Liquid large caps; several are priced below ₹1,000 so a 1-share position is possible.
        # Affordability is re-checked live against actual price and funds before any order.
        "NSE_EQ|INE154A01025",  # ITC
        "NSE_EQ|INE062A01020",  # SBIN
        "NSE_EQ|INE081A01020",  # TATASTEEL
        "NSE_EQ|INE733E01010",  # NTPC
        "NSE_EQ|INE213A01029",  # ONGC
        "NSE_EQ|INE522F01014",  # COALINDIA
        "NSE_EQ|INE263A01024",  # BEL
        "NSE_EQ|INE242A01010",  # IOC
        "NSE_EQ|INE009A01021",  # INFY
        "NSE_EQ|INE002A01018",  # RELIANCE
    ])
    benchmark_key: str = "NSE_INDEX|Nifty 50"
    sensex_key: str = "BSE_INDEX|SENSEX"
    vix_key: str = "NSE_INDEX|India VIX"
    db_path: str = "data_store/indiaquant.db"   # relative to the project folder
    dashboard_host: str = "127.0.0.1"
    algo_name: str = ""          # only for exchange-approved algos (X-Algo-Name header)
    order_tag_prefix: str = "IQ"
    enabled_strategies: list = field(default_factory=lambda: [
        "sma_crossover", "donchian_breakout", "rsi_reversion",
        "bollinger_reversion", "pullback_trend", "orb", "vwap_reversion"])

    def to_json(self) -> str:
        d = asdict(self)
        d["risk"]["allowed_products"] = list(self.risk.allowed_products)
        return json.dumps(d, indent=2)


def load_settings(path: Path = SETTINGS_FILE) -> Settings:
    s = Settings()
    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))
        risk_raw = raw.pop("risk", {})
        for k, v in risk_raw.items():
            if hasattr(s.risk, k):
                setattr(s.risk, k, tuple(v) if k == "allowed_products" else v)
        for k, v in raw.items():
            if hasattr(s, k):
                setattr(s, k, v)
    # relative paths are resolved against the project folder (portable across PCs)
    if s.db_path and not Path(s.db_path).is_absolute():
        s.db_path = str(ROOT / s.db_path)
    return s


def save_default_settings(path: Path = SETTINGS_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(Settings().to_json(), encoding="utf-8")
        return
    # repair settings copied from another machine whose db_path points outside this project
    raw = json.loads(path.read_text(encoding="utf-8"))
    dbp = raw.get("db_path", "")
    if dbp and Path(dbp).is_absolute() and not Path(dbp).parent.exists():
        raw["db_path"] = "data_store/indiaquant.db"
        path.write_text(json.dumps(raw, indent=2), encoding="utf-8")


@dataclass
class Secrets:
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = ""
    access_token: str = ""

    @classmethod
    def from_env(cls) -> "Secrets":
        load_env_file()
        return cls(
            client_id=os.environ.get("UPSTOX_CLIENT_ID", ""),
            client_secret=os.environ.get("UPSTOX_CLIENT_SECRET", ""),
            redirect_uri=os.environ.get("UPSTOX_REDIRECT_URI", ""),
            access_token=os.environ.get("UPSTOX_ACCESS_TOKEN", ""),
        )

    def __repr__(self) -> str:  # never leak
        return (f"Secrets(client_id={'set' if self.client_id else 'missing'}, "
                f"client_secret={'set' if self.client_secret else 'missing'}, "
                f"redirect_uri={self.redirect_uri or 'missing'}, "
                f"access_token={'set' if self.access_token else 'missing'})")

    __str__ = __repr__


def validate_settings(s: Settings) -> list[str]:
    """Return a list of problems (empty = OK)."""
    r = s.risk
    errs = []
    for name in ("max_capital_exposure_pct", "max_risk_per_trade_pct", "max_daily_loss_pct",
                 "max_spread_pct", "max_concentration_pct"):
        v = getattr(r, name)
        if not (0 < v <= 1):
            errs.append(f"risk.{name}={v} must be in (0, 1]")
    if r.max_risk_per_trade_pct > r.max_daily_loss_pct:
        errs.append("max_risk_per_trade_pct should not exceed max_daily_loss_pct")
    if r.max_open_positions < 1 or r.max_orders_per_session < 1:
        errs.append("max_open_positions and max_orders_per_session must be >= 1")
    if r.max_order_notional > r.starting_capital * 5:
        errs.append("max_order_notional is >5x starting capital; leverage is not allowed by default")
    if r.allow_option_writing:
        errs.append("allow_option_writing=True is not supported (unlimited-risk); set it to false")
    if "MTF" in r.allowed_products:
        errs.append("MTF (margin funding) is not permitted by default")
    for k in s.watchlist:
        if "|" not in k:
            errs.append(f"watchlist entry {k!r} is not an Upstox instrument_key (EXCHANGE_SEGMENT|ID)")
    if s.dashboard_host not in ("127.0.0.1", "localhost"):
        errs.append("dashboard_host is not localhost; exposing the dashboard publicly is unsafe")
    return errs
