"""Bucle principal del bot de momentum para meme coins en Solana."""
from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
from pathlib import Path

from . import dexscreener, safety, strategy
from .config import LAMPORTS_PER_SOL, SOL_MINT, Config
from .executor import LiveExecutor, PaperExecutor
from .jupiter import Jupiter
from .portfolio import Portfolio, Position

log = logging.getLogger("memebot")

MAX_DEEP_CHECKS_PER_CYCLE = 5   # cuántos candidatos pasan a chequeo de seguridad por ciclo
REJECT_LOG_EVERY_SEC = 3600     # registrar cada token rechazado como máximo 1 vez por hora


class Bot:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.jup = Jupiter(cfg.jupiter_api_key)
        mode = "live" if cfg.is_live else "paper"
        self.pf = Portfolio(cfg.data_dir, mode, cfg.paper_start_sol)
        self.ex = LiveExecutor(self.jup, cfg) if cfg.is_live else PaperExecutor(self.jup, self.pf)
        self._reject_logged: dict[str, float] = {}
        self._stop = False

    # ------------------------------------------------------------------ gestión de posiciones
    def manage_positions(self) -> None:
        positions = self.pf.state.positions
        if not positions:
            return
        pairs = dexscreener.fetch_pairs(list(positions))
        now = time.time()
        for token, pos in list(positions.items()):
            try:
                value = self.ex.value_sol(token, pos.raw_amount)
            except Exception as e:
                log.warning("No se pudo valorar %s: %s", pos.symbol, e)
                continue
            pos.last_value_sol = value
            pnl_pct = (value / pos.cost_sol - 1) * 100 if pos.cost_sol > 0 else 0.0
            pos.peak_pnl_pct = max(pos.peak_pnl_pct, pnl_pct)
            liq_now = pairs[token].liquidity_usd if token in pairs else 0.0
            held_min = (now - pos.opened_at) / 60
            d = strategy.exit_decision(pnl_pct=pnl_pct, peak_pnl_pct=pos.peak_pnl_pct,
                                       tp_done=pos.tp_done, held_min=held_min, liq_now=liq_now,
                                       liq_entry=pos.entry_liq_usd, cfg=self.cfg)
            log.info("  %-10s valor %.4f SOL  pnl %+6.1f%%  máx %+6.1f%%  %3.0fm",
                     pos.symbol, value, pnl_pct, pos.peak_pnl_pct, held_min)
            if d:
                self.sell(pos, d.fraction, d.reason, pnl_pct, held_min)

    def sell(self, pos: Position, fraction: float, reason: str, pnl_pct: float, held_min: float) -> None:
        held = self.ex.held_raw(pos.token, pos.raw_amount)
        raw = held if fraction >= 0.999 else int(held * fraction)
        if raw <= 0:
            log.warning("%s sin saldo para vender; se cierra la posición.", pos.symbol)
            self.pf.state.positions.pop(pos.token, None)
            return
        fill = self.ex.sell(pos.token, raw)
        if not fill.ok:
            log.error("Venta fallida %s: %s", pos.symbol, fill.error)
            return
        sold_frac = min(1.0, raw / max(held, 1))
        cost_part = pos.cost_sol * sold_frac
        pnl_sol = fill.sol - cost_part
        self.pf.record_realized(pnl_sol)
        log.info("VENTA %s %.0f%% -> %.4f SOL (%+.4f SOL) | %s", pos.symbol, sold_frac * 100,
                 fill.sol, pnl_sol, reason)
        self.pf.log_trade(action="SELL", token=pos.token, symbol=pos.symbol, sol=round(fill.sol, 6),
                          token_raw=raw, pnl_sol=round(pnl_sol, 6),
                          pnl_pct=round(pnl_sol / cost_part * 100, 2) if cost_part else 0,
                          reason=reason, signature=fill.signature, held_min=round(held_min, 1),
                          **{k: pos.features.get(k) for k in ("score", "liquidity_usd", "mcap_usd",
                                                              "age_min", "change_h1", "buy_sell_ratio",
                                                              "roundtrip_loss_pct")})
        if sold_frac >= 0.999:
            self.pf.state.positions.pop(pos.token, None)
            self.pf.state.cooldown_until[pos.token] = time.time() + self.cfg.cooldown_minutes * 60
        else:
            pos.cost_sol -= cost_part
            pos.raw_amount = held - raw
            pos.tp_done = True
        self.pf.save()

    # ------------------------------------------------------------------ búsqueda de entradas
    def can_buy(self) -> bool:
        st = self.pf.state
        if len(st.positions) >= self.cfg.max_open_positions:
            return False
        if self.pf.daily_loss_hit(self.cfg.max_daily_loss_sol):
            log.warning("Límite de pérdida diaria alcanzado: no se abren posiciones hoy.")
            return False
        try:
            bal = self.ex.available_sol()
        except Exception as e:
            log.warning("No se pudo leer saldo: %s", e)
            return False
        if bal - self.cfg.position_size_sol < self.cfg.min_sol_reserve:
            log.info("Saldo insuficiente (%.4f SOL).", bal)
            return False
        return True

    def scan_and_buy(self) -> None:
        if not self.can_buy():
            return
        tokens = [t for t in dexscreener.discover_candidate_tokens()
                  if t not in self.pf.state.positions and not self.pf.in_cooldown(t) and t != SOL_MINT]
        pairs = dexscreener.fetch_pairs(tokens)
        now_ms = int(time.time() * 1000)

        ranked = []
        for token, p in pairs.items():
            reasons = strategy.entry_filters(p, self.cfg, now_ms)
            score = strategy.momentum_score(p)
            if not reasons and score < self.cfg.min_score:
                reasons = [f"score bajo {score:.2f}"]
            feats = self._features(p, score, now_ms)
            if reasons:
                self._log_reject(token, feats, reasons)
            else:
                ranked.append((score, p, feats))
        ranked.sort(key=lambda x: x[0], reverse=True)
        log.info("Escaneados %d tokens, %d pasan filtros de momentum.", len(pairs), len(ranked))

        for score, p, feats in ranked[:MAX_DEEP_CHECKS_PER_CYCLE]:
            if not self.can_buy():
                break
            rep = safety.check_token(p.token, self.cfg.rpc_url, self.cfg.max_rugcheck_score)
            feats["rugcheck_score"] = rep.rugcheck_score
            feats["lp_locked_pct"] = rep.lp_locked_pct
            if not rep.ok:
                self._log_reject(p.token, feats, rep.reasons, force=True)
                continue
            rt = self._roundtrip(p.token)
            feats["roundtrip_loss_pct"] = round(rt, 2) if rt is not None else None
            if rt is None or rt > self.cfg.max_roundtrip_loss_pct:
                self._log_reject(p.token, feats, [f"ida y vuelta pierde {rt}%"], force=True)
                continue
            self.buy(p, feats)

    def _roundtrip(self, token: str) -> float | None:
        lamports = int(self.cfg.position_size_sol * LAMPORTS_PER_SOL)
        try:
            buy_q = self.jup.quote(SOL_MINT, token, lamports)
            if buy_q.out_amount <= 0:
                return None
            sell_q = self.jup.quote(token, SOL_MINT, buy_q.out_amount)
            return strategy.roundtrip_loss_pct(lamports, sell_q.out_amount)
        except Exception as e:
            log.debug("Ida y vuelta falló para %s: %s", token, e)
            return None

    def buy(self, p: dexscreener.PairInfo, feats: dict) -> None:
        fill = self.ex.buy(p.token, self.cfg.position_size_sol)
        if not fill.ok:
            log.error("Compra fallida %s: %s", p.symbol, fill.error)
            self.pf.log_candidate({**feats, "decision": "buy_failed", "reasons": [fill.error]})
            return
        self.pf.state.positions[p.token] = Position(
            token=p.token, symbol=p.symbol, opened_at=time.time(), cost_sol=fill.sol,
            raw_amount=fill.token_raw, entry_liq_usd=p.liquidity_usd, features=feats,
            last_value_sol=fill.sol)
        self.pf.save()
        log.info("COMPRA %s por %.4f SOL (score %.2f) %s", p.symbol, fill.sol, feats["score"], p.url)
        self.pf.log_candidate({**feats, "decision": "buy"})
        self.pf.log_trade(action="BUY", token=p.token, symbol=p.symbol, sol=round(fill.sol, 6),
                          token_raw=fill.token_raw, signature=fill.signature,
                          **{k: feats.get(k) for k in ("score", "liquidity_usd", "mcap_usd", "age_min",
                                                       "change_h1", "buy_sell_ratio", "roundtrip_loss_pct")})

    @staticmethod
    def _features(p: dexscreener.PairInfo, score: float, now_ms: int) -> dict:
        return {
            "token": p.token, "symbol": p.symbol, "score": score, "price_usd": p.price_usd,
            "liquidity_usd": round(p.liquidity_usd), "mcap_usd": round(p.mcap_usd),
            "age_min": round((now_ms - p.created_at_ms) / 60_000, 1) if p.created_at_ms else None,
            "volume_h1": round(p.volume_h1), "buys_h1": p.buys_h1, "sells_h1": p.sells_h1,
            "buy_sell_ratio": round(p.buys_h1 / max(p.sells_h1, 1), 2),
            "change_m5": p.change_m5, "change_h1": p.change_h1, "change_h6": p.change_h6,
            "dex": p.dex_id,
        }

    def _log_reject(self, token: str, feats: dict, reasons: list[str], force: bool = False) -> None:
        now = time.time()
        if not force and now - self._reject_logged.get(token, 0) < REJECT_LOG_EVERY_SEC:
            return
        self._reject_logged[token] = now
        self.pf.log_candidate({**feats, "decision": "reject", "reasons": reasons})

    # ------------------------------------------------------------------ bucle
    def cycle(self) -> None:
        self.pf.roll_day()
        self.manage_positions()
        self.scan_and_buy()
        self.pf.save()
        st = self.pf.state
        bal = st.paper_sol if not self.cfg.is_live else None
        log.info("Posiciones: %d | PnL hoy: %+.4f SOL | PnL total: %+.4f SOL%s",
                 len(st.positions), st.day_realized_sol, st.total_realized_sol,
                 f" | saldo simulado: {bal:.4f} SOL" if bal is not None else "")

    def run(self, once: bool = False, duration: float = 0) -> None:
        deadline = time.time() + duration if duration else None
        signal.signal(signal.SIGINT, lambda *_: setattr(self, "_stop", True))
        signal.signal(signal.SIGTERM, lambda *_: setattr(self, "_stop", True))
        while not self._stop:
            start = time.time()
            try:
                self.cycle()
            except Exception:
                log.exception("Error en el ciclo (el bot sigue).")
            if once or (deadline and time.time() + self.cfg.scan_interval_sec > deadline):
                break
            while not self._stop and time.time() - start < self.cfg.scan_interval_sec:
                time.sleep(0.5)
        self.pf.save()
        log.info("Bot detenido. Posiciones abiertas: %d", len(self.pf.state.positions))

    def sell_all(self) -> None:
        for pos in list(self.pf.state.positions.values()):
            self.sell(pos, 1.0, "venta manual (--sell-all)", 0.0, (time.time() - pos.opened_at) / 60)


def check_wallet(cfg: Config) -> None:
    """Carga la wallet, lee el saldo y firma una orden de prueba (0.001 SOL -> USDC) sin enviarla."""
    from .wallet import Wallet
    usdc = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    w = Wallet(cfg.solana_private_key, cfg.rpc_url)
    log.info("Dirección: %s", w.address)
    log.info("Saldo: %.4f SOL", w.sol_balance_lamports() / LAMPORTS_PER_SOL)
    q = Jupiter(cfg.jupiter_api_key).order(SOL_MINT, usdc, 1_000_000, taker=w.address)
    if not q.transaction:
        log.error("Jupiter no devolvió transacción (¿saldo insuficiente?).")
        return
    w.sign_b64(q.transaction)
    log.info("Firma local OK (router %s). No se envió nada. La wallet está lista.", q.router)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Bot de momentum para meme coins en Solana")
    ap.add_argument("--env", default=".env", help="archivo de configuración")
    ap.add_argument("--once", action="store_true", help="ejecuta un solo ciclo")
    ap.add_argument("--sell-all", action="store_true", help="vende todas las posiciones y sale")
    ap.add_argument("--check-wallet", action="store_true",
                    help="verifica clave, saldo y firma SIN enviar ninguna transacción")
    ap.add_argument("--duration", type=float, default=0,
                    help="corre ciclos durante N segundos y sale (para GitHub Actions)")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    cfg = Config.from_env(args.env)
    Path(cfg.data_dir).mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout),
                  logging.FileHandler(Path(cfg.data_dir) / "bot.log", encoding="utf-8")])

    if not cfg.dry_run and not cfg.is_live:
        log.error("DRY_RUN=false pero falta LIVE_CONFIRM=SI_ENTIENDO_EL_RIESGO. Sigo en simulación.")
    log.info("Modo: %s | tamaño %.3f SOL | máx %d posiciones | pérdida diaria máx %.3f SOL",
             "REAL" if cfg.is_live else "SIMULACIÓN", cfg.position_size_sol,
             cfg.max_open_positions, cfg.max_daily_loss_sol)

    if args.check_wallet:
        check_wallet(cfg)
        return

    bot = Bot(cfg)
    if args.sell_all:
        bot.sell_all()
        return
    bot.run(once=args.once, duration=args.duration)


if __name__ == "__main__":
    main()
