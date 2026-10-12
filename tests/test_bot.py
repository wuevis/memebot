"""Pruebas offline (sin red). Ejecutar:  python -m unittest discover tests"""
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from memebot import analyze, bot as botmod, dexscreener, safety, strategy
from memebot.config import Config, SOL_MINT
from memebot.jupiter import Quote

NOW_MS = int(time.time() * 1000)


def api_pair(token="TOK1", liq=60_000, mcap=500_000, age_min=120, buys=300, sells=200,
             m5=3.0, h1=25.0, vol_h1=90_000, b5=40, s5=25, quote=SOL_MINT, price=0.001):
    return {
        "chainId": "solana", "dexId": "raydium", "url": f"https://dexscreener.com/solana/{token}",
        "pairAddress": "PAIR" + token,
        "baseToken": {"address": token, "symbol": token[:6], "name": token},
        "quoteToken": {"address": quote, "symbol": "SOL"},
        "priceUsd": str(price), "liquidity": {"usd": liq}, "marketCap": mcap,
        "volume": {"h1": vol_h1, "m5": vol_h1 / 8},
        "txns": {"h1": {"buys": buys, "sells": sells}, "m5": {"buys": b5, "sells": s5}},
        "priceChange": {"m5": m5, "h1": h1, "h6": h1 * 1.5},
        "pairCreatedAt": NOW_MS - age_min * 60_000,
    }


class StrategyTests(unittest.TestCase):
    def setUp(self):
        self.cfg = Config()

    def test_good_pair_passes(self):
        p = dexscreener.PairInfo.from_api(api_pair())
        self.assertEqual(strategy.entry_filters(p, self.cfg, NOW_MS), [])
        self.assertGreaterEqual(strategy.momentum_score(p), self.cfg.min_score)

    def test_bad_pairs_rejected(self):
        cases = {
            "muy nuevo": api_pair(age_min=5),
            "liquidez baja": api_pair(liq=5_000),
            "sospechoso": api_pair(buys=500, sells=50),
            "5m negativo": api_pair(m5=-4),
            "cambio 1h": api_pair(h1=400),
        }
        for expected, raw in cases.items():
            reasons = strategy.entry_filters(dexscreener.PairInfo.from_api(raw), self.cfg, NOW_MS)
            self.assertTrue(any(expected in r for r in reasons), (expected, reasons))

    def test_best_sol_pair(self):
        pairs = [api_pair(liq=10_000), api_pair(liq=90_000), api_pair(liq=200_000, quote="USDC")]
        self.assertEqual(dexscreener.best_sol_pair(pairs)["liquidity"]["usd"], 90_000)

    def test_exits(self):
        c = self.cfg
        kw = dict(tp_done=False, held_min=10, liq_now=50_000, liq_entry=50_000, cfg=c)
        self.assertIsNone(strategy.exit_decision(pnl_pct=10, peak_pnl_pct=10, **kw))
        self.assertEqual(strategy.exit_decision(pnl_pct=-26, peak_pnl_pct=0, **kw).fraction, 1.0)
        tp = strategy.exit_decision(pnl_pct=65, peak_pnl_pct=65, **kw)
        self.assertEqual(tp.fraction, c.take_profit_sell_fraction)
        # máximo +100% (valor 2x); ahora +55% (1.55x) => cayó 22.5% desde el máximo
        tr = strategy.exit_decision(pnl_pct=55, peak_pnl_pct=100, **{**kw, "tp_done": True})
        self.assertIn("trailing", tr.reason)
        rug = strategy.exit_decision(pnl_pct=5, peak_pnl_pct=5, **{**kw, "liq_now": 20_000})
        self.assertIn("liquidez", rug.reason)
        self.assertIn("tiempo", strategy.exit_decision(pnl_pct=0, peak_pnl_pct=0,
                                                       **{**kw, "held_min": 999}).reason)

    def test_roundtrip(self):
        self.assertAlmostEqual(strategy.roundtrip_loss_pct(1000, 950), 5.0)

    def test_rugcheck_eval(self):
        bad = safety.evaluate_rugcheck({"score_normalised": 80,
                                        "risks": [{"name": "Mutable metadata", "level": "warn"},
                                                  {"name": "Top 10 holders", "level": "danger"}]}, 30)
        self.assertFalse(bad.ok)
        self.assertEqual(len(bad.reasons), 2)
        self.assertTrue(safety.evaluate_rugcheck({"score_normalised": 5, "risks": []}, 30).ok)

    def test_config_from_env(self):
        with tempfile.TemporaryDirectory() as d:
            env = Path(d) / ".env"
            env.write_text("POSITION_SIZE_SOL=0.1\nDRY_RUN=false\nMAX_OPEN_POSITIONS=5\n")
            with mock.patch.dict("os.environ", {}, clear=True):
                cfg = Config.from_env(env)
            self.assertEqual(cfg.position_size_sol, 0.1)
            self.assertEqual(cfg.max_open_positions, 5)
            self.assertFalse(cfg.is_live)   # sin LIVE_CONFIRM nunca opera en real


class FakeMarket:
    """Precio de un token que podemos mover a mano. 1 SOL = 1e6 unidades del token * precio."""

    def __init__(self):
        self.mult = 1.0      # multiplicador del precio respecto al de entrada
        self.liq = 60_000

    def quote(self, inp, out, amount):
        fee = 0.99           # 1% de costo por lado
        if inp == SOL_MINT:
            return Quote(amount, int(amount * 1_000 / self.mult * fee), 0.1, "metis", 10)
        return Quote(amount, int(amount / 1_000 * self.mult * fee), 0.1, "metis", 10)


class SimulatedRunTests(unittest.TestCase):
    def test_full_cycle_paper(self):
        market = FakeMarket()
        with tempfile.TemporaryDirectory() as d:
            cfg = Config(data_dir=d, position_size_sol=0.1, paper_start_sol=1.0, max_open_positions=1)
            pairs = lambda toks: {t: dexscreener.PairInfo.from_api(api_pair(t, liq=market.liq))
                                  for t in toks}
            with mock.patch.object(dexscreener, "discover_candidate_tokens", return_value=["TOK1", "TOK2"]), \
                 mock.patch.object(dexscreener, "fetch_pairs", side_effect=pairs), \
                 mock.patch.object(safety, "check_token",
                                   return_value=safety.SafetyReport(True, [], 10, 100)), \
                 mock.patch("memebot.jupiter.Jupiter.quote", side_effect=market.quote):
                b = botmod.Bot(cfg)
                b.cycle()                                  # compra
                self.assertEqual(len(b.pf.state.positions), 1)
                market.mult = 1.8; b.cycle()               # take profit parcial
                pos = next(iter(b.pf.state.positions.values()))
                self.assertTrue(pos.tp_done)
                market.mult = 2.6; b.cycle()               # nuevo máximo
                market.mult = 1.9; b.cycle()               # cae >20% desde el máximo -> trailing
                self.assertEqual(len(b.pf.state.positions), 1)  # recompra el otro token disponible
                self.assertGreater(b.pf.state.total_realized_sol, 0)
                trips = analyze.load_round_trips(Path(d) / "trades_paper.csv")
                self.assertEqual(len(trips), 1)
                self.assertIn("trailing", trips[0]["exits"][-1])
                self.assertIn("Win rate", analyze.report(trips))

    def test_daily_loss_blocks_buys(self):
        market = FakeMarket()
        with tempfile.TemporaryDirectory() as d:
            cfg = Config(data_dir=d, position_size_sol=0.1, max_daily_loss_sol=0.05, max_open_positions=1)
            pairs = lambda toks: {t: dexscreener.PairInfo.from_api(api_pair(t)) for t in toks}
            with mock.patch.object(dexscreener, "discover_candidate_tokens", return_value=["A1", "B2"]), \
                 mock.patch.object(dexscreener, "fetch_pairs", side_effect=pairs), \
                 mock.patch.object(safety, "check_token",
                                   return_value=safety.SafetyReport(True, [], 10, 100)), \
                 mock.patch("memebot.jupiter.Jupiter.quote", side_effect=market.quote):
                b = botmod.Bot(cfg)
                b.cycle()
                market.mult = 0.5; b.cycle()               # stop loss: pierde ~0.05 SOL
                self.assertEqual(len(b.pf.state.positions), 0)
                self.assertTrue(b.pf.daily_loss_hit(cfg.max_daily_loss_sol))

    def test_honeypot_skipped(self):
        """Si vender cuesta mucho más que comprar (impuesto oculto), no se compra."""
        class Honeypot(FakeMarket):
            def quote(self, inp, out, amount):
                q = super().quote(inp, out, amount)
                if out == SOL_MINT:
                    q.out_amount = int(q.out_amount * 0.7)
                return q
        market = Honeypot()
        with tempfile.TemporaryDirectory() as d:
            cfg = Config(data_dir=d)
            with mock.patch.object(dexscreener, "discover_candidate_tokens", return_value=["HP1"]), \
                 mock.patch.object(dexscreener, "fetch_pairs",
                                   side_effect=lambda t: {x: dexscreener.PairInfo.from_api(api_pair(x)) for x in t}), \
                 mock.patch.object(safety, "check_token", return_value=safety.SafetyReport(True)), \
                 mock.patch("memebot.jupiter.Jupiter.quote", side_effect=market.quote):
                b = botmod.Bot(cfg)
                b.cycle()
                self.assertEqual(len(b.pf.state.positions), 0)


if __name__ == "__main__":
    unittest.main()
