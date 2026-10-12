"""Estado del bot (posiciones, saldo simulado, pérdidas del día) y registros para análisis."""
from __future__ import annotations

import csv
import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

TRADE_FIELDS = ["time", "mode", "action", "token", "symbol", "sol", "token_raw", "pnl_sol",
                "pnl_pct", "reason", "signature", "score", "liquidity_usd", "mcap_usd",
                "age_min", "change_h1", "buy_sell_ratio", "roundtrip_loss_pct", "held_min"]


def utc_day(ts: float | None = None) -> str:
    return datetime.fromtimestamp(ts or time.time(), tz=timezone.utc).strftime("%Y-%m-%d")


@dataclass
class Position:
    token: str
    symbol: str
    opened_at: float
    cost_sol: float          # costo restante (se reduce proporcionalmente en ventas parciales)
    raw_amount: int          # cantidad de tokens (unidades mínimas)
    entry_liq_usd: float
    features: dict = field(default_factory=dict)
    peak_pnl_pct: float = 0.0
    tp_done: bool = False
    last_value_sol: float = 0.0


@dataclass
class State:
    paper_sol: float = 0.0
    positions: dict[str, Position] = field(default_factory=dict)
    day: str = ""
    day_realized_sol: float = 0.0
    total_realized_sol: float = 0.0
    cooldown_until: dict[str, float] = field(default_factory=dict)


class Portfolio:
    def __init__(self, data_dir: str, mode: str, paper_start_sol: float):
        self.dir = Path(data_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.mode = mode
        self.state_path = self.dir / f"state_{mode}.json"
        self.trades_path = self.dir / f"trades_{mode}.csv"
        self.candidates_path = self.dir / f"candidates_{mode}.jsonl"
        self.state = self._load(paper_start_sol)

    # --- persistencia ---
    def _load(self, paper_start_sol: float) -> State:
        if self.state_path.exists():
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
            raw["positions"] = {k: Position(**v) for k, v in raw.get("positions", {}).items()}
            return State(**raw)
        return State(paper_sol=paper_start_sol, day=utc_day())

    def save(self) -> None:
        data = asdict(self.state)
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(self.state_path)

    # --- registros ---
    def log_trade(self, **row) -> None:
        new = not self.trades_path.exists()
        with self.trades_path.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=TRADE_FIELDS, extrasaction="ignore")
            if new:
                w.writeheader()
            row.setdefault("time", datetime.now(timezone.utc).isoformat(timespec="seconds"))
            row.setdefault("mode", self.mode)
            w.writerow(row)

    def log_candidate(self, record: dict) -> None:
        record.setdefault("time", datetime.now(timezone.utc).isoformat(timespec="seconds"))
        with self.candidates_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # --- reglas de cuenta ---
    def roll_day(self) -> None:
        today = utc_day()
        if self.state.day != today:
            self.state.day = today
            self.state.day_realized_sol = 0.0

    def unrealized_sol(self) -> float:
        return sum(p.last_value_sol - p.cost_sol for p in self.state.positions.values())

    def daily_loss_hit(self, limit_sol: float) -> bool:
        # Cuenta pérdidas realizadas del día + pérdidas abiertas, para no seguir comprando en una mala racha.
        return self.state.day_realized_sol + min(self.unrealized_sol(), 0) <= -abs(limit_sol)

    def in_cooldown(self, token: str) -> bool:
        return self.state.cooldown_until.get(token, 0) > time.time()

    def record_realized(self, pnl_sol: float) -> None:
        self.state.day_realized_sol += pnl_sol
        self.state.total_realized_sol += pnl_sol
