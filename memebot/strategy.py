"""Lógica de la estrategia (funciones puras, fáciles de probar y ajustar)."""
from __future__ import annotations

from dataclasses import dataclass

from .config import Config
from .dexscreener import PairInfo


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def entry_filters(p: PairInfo, cfg: Config, now_ms: int) -> list[str]:
    """Devuelve la lista de motivos de rechazo. Lista vacía = pasa."""
    r: list[str] = []
    if p.created_at_ms:
        age_min = (now_ms - p.created_at_ms) / 60_000
        if age_min < cfg.min_age_minutes:
            r.append(f"muy nuevo ({age_min:.0f}m)")
        if age_min > cfg.max_age_hours * 60:
            r.append(f"muy viejo ({age_min / 60:.0f}h)")
    else:
        r.append("sin fecha de creación")
    if p.liquidity_usd < cfg.min_liquidity_usd:
        r.append(f"liquidez baja ${p.liquidity_usd:,.0f}")
    if not (cfg.min_mcap_usd <= p.mcap_usd <= cfg.max_mcap_usd):
        r.append(f"mcap fuera de rango ${p.mcap_usd:,.0f}")
    if p.mcap_usd > 0 and p.liquidity_usd / p.mcap_usd < cfg.min_liq_to_mcap:
        r.append("liquidez/mcap bajo")
    if p.volume_h1 < cfg.min_volume_h1_usd:
        r.append(f"volumen 1h bajo ${p.volume_h1:,.0f}")
    if p.buys_h1 < cfg.min_buys_h1:
        r.append(f"pocas compras 1h ({p.buys_h1})")
    ratio = p.buys_h1 / max(p.sells_h1, 1)
    if ratio < cfg.min_buy_sell_ratio_h1:
        r.append(f"ratio compra/venta bajo {ratio:.2f}")
    if ratio > cfg.max_buy_sell_ratio_h1:
        r.append(f"ratio compra/venta sospechoso {ratio:.2f}")
    if p.change_m5 < cfg.min_change_m5_pct:
        r.append(f"5m negativo {p.change_m5:.1f}%")
    if not (cfg.min_change_h1_pct <= p.change_h1 <= cfg.max_change_h1_pct):
        r.append(f"cambio 1h fuera de rango {p.change_h1:.1f}%")
    return r


def momentum_score(p: PairInfo) -> float:
    """Puntuación 0-1. Premia presión compradora, aceleración reciente y rotación de volumen."""
    ratio = p.buys_h1 / max(p.sells_h1, 1)
    s_ratio = _clamp((ratio - 1.0) / 1.0)                    # 1.0 -> 0, 2.0 -> 1
    s_m5 = _clamp(p.change_m5 / 10.0)                        # +10% en 5m -> 1
    s_h1 = _clamp(p.change_h1 / 50.0)                        # +50% en 1h -> 1
    turnover = p.volume_h1 / max(p.liquidity_usd, 1)
    s_turn = _clamp(turnover / 3.0)                          # volumen 1h = 3x liquidez -> 1
    # Aceleración: actividad de los últimos 5m vs el promedio por 5m de la última hora
    avg_5m_tx = (p.buys_h1 + p.sells_h1) / 12
    s_accel = _clamp(((p.buys_m5 + p.sells_m5) / max(avg_5m_tx, 1) - 0.8) / 1.2)
    return round(0.30 * s_ratio + 0.20 * s_m5 + 0.15 * s_h1 + 0.15 * s_turn + 0.20 * s_accel, 4)


def roundtrip_loss_pct(sol_in: int, sol_back: int) -> float:
    """% que se pierde al comprar y vender al instante (fees + impacto + impuestos ocultos)."""
    if sol_in <= 0:
        return 100.0
    return (1 - sol_back / sol_in) * 100


@dataclass
class ExitDecision:
    fraction: float   # fracción de la posición a vender (0-1)
    reason: str


def exit_decision(*, pnl_pct: float, peak_pnl_pct: float, tp_done: bool, held_min: float,
                  liq_now: float, liq_entry: float, cfg: Config) -> ExitDecision | None:
    if liq_entry > 0 and liq_now > 0 and (1 - liq_now / liq_entry) * 100 >= cfg.liquidity_drop_exit_pct:
        return ExitDecision(1.0, f"liquidez cayó {100 * (1 - liq_now / liq_entry):.0f}%")
    if pnl_pct <= -cfg.stop_loss_pct:
        return ExitDecision(1.0, f"stop loss {pnl_pct:.1f}%")
    if peak_pnl_pct >= cfg.trailing_activate_pct:
        # El trailing se mide sobre el valor: cuánto cayó desde el máximo alcanzado.
        drop = (1 - (1 + pnl_pct / 100) / (1 + peak_pnl_pct / 100)) * 100
        if drop >= cfg.trailing_stop_pct:
            return ExitDecision(1.0, f"trailing stop (máx {peak_pnl_pct:.0f}%, ahora {pnl_pct:.0f}%)")
    if not tp_done and pnl_pct >= cfg.take_profit_pct:
        return ExitDecision(cfg.take_profit_sell_fraction, f"take profit parcial {pnl_pct:.0f}%")
    if held_min >= cfg.max_hold_minutes:
        return ExitDecision(1.0, f"tiempo máximo ({held_min:.0f}m)")
    return None
