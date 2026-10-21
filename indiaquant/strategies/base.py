from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class StrategySignal:
    strategy: str
    instrument_key: str
    side: str
    entry_ref: float          # reference price at signal (bar close)
    stop: float
    target: float | None
    style: str                # intraday / swing
    bar_ts: str
    explanation: str
    family: str = ""


@dataclass
class Strategy:
    name: str
    family: str               # trend / mean_reversion / breakout
    style: str                # intraday / swing
    timeframe: str            # 1m / 5m / 1d
    hypothesis: str
    rationale: str
    entry_rule: str
    exit_rule: str
    stop_rule: str
    evidence: str             # literature basis (established theory / published evidence)
    fails_when: str
    params: dict = field(default_factory=dict)
    param_grid: dict = field(default_factory=dict)
    needs_benchmark: bool = False

    def generate(self, df: pd.DataFrame, params: dict | None = None, context: dict | None = None) -> pd.DataFrame:
        """Return DataFrame indexed like df with columns:
        entry (bool), exit (bool), stop (float, valid on entry bars), target (float|NaN), why (str)."""
        raise NotImplementedError

    def describe(self) -> dict:
        return {k: getattr(self, k) for k in ("name", "family", "style", "timeframe", "hypothesis", "rationale",
                                              "entry_rule", "exit_rule", "stop_rule", "evidence", "fails_when",
                                              "params", "param_grid")}

    def latest_signal(self, df: pd.DataFrame, key: str, params: dict | None = None,
                      context: dict | None = None) -> StrategySignal | None:
        if len(df) < 30:
            return None
        sig = self.generate(df, params, context)
        last = sig.iloc[-1]
        if not bool(last["entry"]):
            return None
        tgt = last.get("target")
        return StrategySignal(self.name, key, "BUY", float(df["close"].iloc[-1]), float(last["stop"]),
                              None if pd.isna(tgt) else float(tgt), self.style, str(df.index[-1]),
                              str(last["why"]), self.family)
