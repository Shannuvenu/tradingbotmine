"""Execution state machine. Persisted in the DB so a restart can never silently
resume live trading.

SETUP -> ANALYSIS -> RESEARCH -> LIVE_READY -> LIVE_ACTIVE ; any -> HALTED

Invariants enforced here (and tested):
  * Process start: a persisted LIVE_ACTIVE is downgraded to LIVE_READY.
  * LIVE_ACTIVE requires LIVE_READY + the exact confirmation phrase, and is valid only
    for the IST trading date on which it was activated.
  * HALTED blocks new orders until an explicit `resume` (which returns to LIVE_READY,
    never directly to LIVE_ACTIVE).
  * A KILL file in the project root halts immediately (works even if the UI is down).
"""
from __future__ import annotations

from ..config import ROOT
from ..data.calendar import now_ist
from ..logging_setup import get_logger

log = get_logger("state")

STATES = ("SETUP", "ANALYSIS", "RESEARCH", "LIVE_READY", "LIVE_ACTIVE", "HALTED")
CONFIRM_PHRASE = "I UNDERSTAND REAL MONEY IS AT RISK"
KILL_FILE = ROOT / "KILL"


class StateError(Exception):
    pass


class ExecutionState:
    KEY = "exec_state"

    def __init__(self, db, kill_file=KILL_FILE):
        self.db = db
        self.kill_file = kill_file
        st = self.db.get_state(self.KEY) or {"state": "SETUP"}
        if st.get("state") == "LIVE_ACTIVE":
            st = {"state": "LIVE_READY", "note": "downgraded from LIVE_ACTIVE on process start"}
            self.db.set_state(self.KEY, st)
            self.db.audit("state", "LIVE_ACTIVE downgraded to LIVE_READY on startup (never auto-resume live)")
        self._st = st

    # ------------------------------------------------------------- queries
    @property
    def state(self) -> str:
        self._check_kill_file()
        return self._st["state"]

    @property
    def info(self) -> dict:
        self._check_kill_file()
        return dict(self._st)

    def _check_kill_file(self):
        if self.kill_file is not None and self.kill_file.exists() and self._st.get("state") != "HALTED":
            self._set({"state": "HALTED", "reason": "KILL file present", "at": now_ist().isoformat()})
            log.error("KILL file detected -> HALTED")

    def can_place_orders(self) -> tuple[bool, str]:
        s = self.state
        if s != "LIVE_ACTIVE":
            return False, f"state is {s}, not LIVE_ACTIVE"
        if self._st.get("activation_date") != now_ist().date().isoformat():
            self._set({"state": "LIVE_READY", "note": "activation expired at day change"})
            return False, "live activation expired (new trading day); re-activate deliberately"
        return True, "ok"

    # --------------------------------------------------------- transitions
    def _set(self, st: dict):
        self._st = st
        self.db.set_state(self.KEY, st)
        self.db.audit("state", f"-> {st['state']}", st)

    def to_analysis(self):
        if self.state in ("LIVE_ACTIVE",):
            raise StateError("halt live trading first")
        self._set({"state": "ANALYSIS"})

    def to_research(self):
        if self.state in ("LIVE_ACTIVE",):
            raise StateError("halt live trading first")
        self._set({"state": "RESEARCH"})

    def mark_live_ready(self, checks: dict):
        failed = [k for k, v in checks.items() if not v.get("ok")]
        if failed:
            raise StateError(f"readiness checks failed: {failed}")
        if self.state == "HALTED":
            raise StateError("system is HALTED; use resume after reviewing the halt reason")
        self._set({"state": "LIVE_READY", "checks": {k: v.get("detail", "") for k, v in checks.items()},
                   "at": now_ist().isoformat()})

    def activate_live(self, confirmation: str, operator: str = "local-user"):
        if self.state != "LIVE_READY":
            raise StateError(f"can only activate from LIVE_READY (current {self.state})")
        if confirmation.strip() != CONFIRM_PHRASE:
            raise StateError(f"confirmation phrase mismatch; type exactly: {CONFIRM_PHRASE}")
        if self.kill_file is not None and self.kill_file.exists():
            raise StateError("KILL file present; remove it deliberately first")
        self._set({"state": "LIVE_ACTIVE", "activation_date": now_ist().date().isoformat(),
                   "at": now_ist().isoformat(), "operator": operator})
        log.warning("LIVE TRADING ACTIVATED for %s", self._st["activation_date"])

    def halt(self, reason: str):
        self._set({"state": "HALTED", "reason": reason, "at": now_ist().isoformat(),
                   "previous": self._st.get("state")})
        log.error("HALTED: %s", reason)

    def resume(self, acknowledge_reason: str):
        if self._st.get("state") != "HALTED":
            raise StateError("not halted")
        if self.kill_file is not None and self.kill_file.exists():
            raise StateError("remove the KILL file first")
        if not acknowledge_reason.strip():
            raise StateError("provide an acknowledgement note")
        self._set({"state": "LIVE_READY", "resumed_from_halt": self._st.get("reason"), "ack": acknowledge_reason,
                   "at": now_ist().isoformat()})
