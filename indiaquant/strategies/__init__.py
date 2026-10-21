"""Strategy catalogue. Every strategy is long-only by default (shorting is disabled for a
₹1,000 cash account) and emits signals evaluated at bar close; the backtester and the
live engine fill on the NEXT bar / next quote, never on the signal bar."""
from .base import Strategy, StrategySignal
from .catalog import REGISTRY, get_strategy, list_strategies

__all__ = ["Strategy", "StrategySignal", "REGISTRY", "get_strategy", "list_strategies"]
