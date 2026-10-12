"""Reporte de rendimiento para ajustar la estrategia.

Uso:  python -m memebot.analyze                 (modo simulación)
      python -m memebot.analyze --mode live
      python -m memebot.analyze --followup      (revisa cómo les fue a los tokens rechazados)
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


def _f(x, default=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def load_round_trips(trades_csv: Path) -> list[dict]:
    """Agrupa cada BUY con sus SELL posteriores del mismo token."""
    if not trades_csv.exists():
        return []
    open_: dict[str, dict] = {}
    trips: list[dict] = []
    with trades_csv.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            tok = row["token"]
            if row["action"] == "BUY":
                open_[tok] = {**row, "cost": _f(row["sol"]), "pnl_sol": 0.0, "exits": [],
                              "closed": False, "held_min": 0.0}
            elif row["action"] == "SELL" and tok in open_:
                t = open_[tok]
                t["pnl_sol"] += _f(row["pnl_sol"])
                t["exits"].append(row["reason"])
                t["held_min"] = _f(row["held_min"])
                if not row["reason"].startswith("take profit parcial"):
                    t["closed"] = True
                    trips.append(open_.pop(tok))
    return trips


def bucket(value: float, edges: list[float], fmt: str = "{:,.0f}") -> str:
    for lo, hi in zip(edges, edges[1:]):
        if lo <= value < hi:
            return f"{fmt.format(lo)}–{fmt.format(hi)}"
    return f"≥{fmt.format(edges[-1])}" if value >= edges[-1] else f"<{fmt.format(edges[0])}"


def group_table(trips: list[dict], key, title: str) -> list[str]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for t in trips:
        groups[key(t)].append(t)
    lines = [f"\n### {title}", "| grupo | trades | win rate | PnL SOL | PnL medio % |", "|---|---|---|---|---|"]
    for g, ts in sorted(groups.items()):
        wins = sum(1 for t in ts if t["pnl_sol"] > 0)
        pnl = sum(t["pnl_sol"] for t in ts)
        avg_pct = sum(t["pnl_sol"] / t["cost"] * 100 for t in ts if t["cost"]) / len(ts)
        lines.append(f"| {g} | {len(ts)} | {wins / len(ts):.0%} | {pnl:+.4f} | {avg_pct:+.1f}% |")
    return lines


def report(trips: list[dict]) -> str:
    out = ["# Reporte del bot", ""]
    if not trips:
        return "\n".join(out + ["Todavía no hay operaciones cerradas."])
    wins = [t for t in trips if t["pnl_sol"] > 0]
    losses = [t for t in trips if t["pnl_sol"] <= 0]
    gross_win = sum(t["pnl_sol"] for t in wins)
    gross_loss = -sum(t["pnl_sol"] for t in losses)
    total = gross_win - gross_loss
    out += [
        f"- Operaciones cerradas: **{len(trips)}**",
        f"- Win rate: **{len(wins) / len(trips):.0%}**",
        f"- PnL total: **{total:+.4f} SOL**",
        f"- Ganancia media: {gross_win / len(wins):+.4f} SOL" if wins else "- Ganancia media: n/a",
        f"- Pérdida media: {-gross_loss / len(losses):+.4f} SOL" if losses else "- Pérdida media: n/a",
        f"- Profit factor: {gross_win / gross_loss:.2f}" if gross_loss else "- Profit factor: ∞",
        f"- Tiempo medio en posición: {sum(t['held_min'] for t in trips) / len(trips):.0f} min",
    ]
    out += group_table(trips, lambda t: t["exits"][-1].split(" ")[0], "Por motivo de salida")
    out += group_table(trips, lambda t: bucket(_f(t["score"]), [0.5, 0.6, 0.7, 0.8, 0.9], "{:.1f}"),
                       "Por score de momentum")
    out += group_table(trips, lambda t: bucket(_f(t["age_min"]) / 60, [0, 1, 3, 6, 12, 24], "{:.0f}h"),
                       "Por edad del token")
    out += group_table(trips, lambda t: bucket(_f(t["liquidity_usd"]), [0, 25e3, 50e3, 100e3, 250e3]),
                       "Por liquidez (USD)")
    out += group_table(trips, lambda t: bucket(_f(t["change_h1"]), [0, 15, 30, 60, 100, 150], "{:.0f}%"),
                       "Por subida en 1h al entrar")
    out += group_table(trips, lambda t: bucket(_f(t["buy_sell_ratio"]), [1, 1.3, 1.6, 2, 3], "{:.1f}"),
                       "Por ratio compras/ventas")
    best = sorted(trips, key=lambda t: t["pnl_sol"], reverse=True)
    out += ["\n### Mejores y peores", "| token | PnL SOL | salida |", "|---|---|---|"]
    for t in best[:5] + best[-5:]:
        out.append(f"| {t['symbol']} | {t['pnl_sol']:+.4f} | {t['exits'][-1]} |")
    return "\n".join(out)


def followup(candidates: Path, limit: int = 120) -> str:
    """Compara el precio actual de tokens rechazados con el de cuando se evaluaron."""
    from .dexscreener import fetch_pairs

    if not candidates.exists():
        return ""
    latest: dict[str, dict] = {}
    for line in candidates.open(encoding="utf-8"):
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("decision") == "reject" and rec.get("price_usd"):
            latest.setdefault(rec["token"], rec)   # primera vez que se rechazó
    recs = list(latest.values())[-limit:]
    now = fetch_pairs([r["token"] for r in recs])
    reason_moves: dict[str, list[float]] = defaultdict(list)
    for r in recs:
        p = now.get(r["token"])
        move = (p.price_usd / r["price_usd"] - 1) * 100 if p and p.price_usd else -100.0
        key = (r.get("reasons") or ["?"])[0].split(" ")[0:2]
        reason_moves[" ".join(key)].append(move)
    lines = ["\n## Seguimiento de rechazados (precio ahora vs al rechazar)",
             "| motivo | tokens | mediana % | % que subió >50% |", "|---|---|---|---|"]
    for k, moves in sorted(reason_moves.items(), key=lambda kv: -len(kv[1])):
        moves.sort()
        med = moves[len(moves) // 2]
        pumped = sum(1 for m in moves if m > 50) / len(moves)
        lines.append(f"| {k} | {len(moves)} | {med:+.0f}% | {pumped:.0%} |")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="paper", choices=["paper", "live"])
    ap.add_argument("--data", default="data")
    ap.add_argument("--followup", action="store_true")
    args = ap.parse_args()
    d = Path(args.data)
    text = report(load_round_trips(d / f"trades_{args.mode}.csv"))
    if args.followup:
        text += "\n" + followup(d / f"candidates_{args.mode}.jsonl")
    from .config import Config
    text += "\n\n## Configuración usada\n```json\n" + json.dumps(
        Config.from_env().public_dict(), indent=2) + "\n```\n"
    out = d / f"reporte_{args.mode}.md"
    out.write_text(text, encoding="utf-8")
    print(text)
    print(f"\nGuardado en {out}. Compártelo conmigo para ajustar la estrategia.")


if __name__ == "__main__":
    main()
