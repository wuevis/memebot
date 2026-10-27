# Reporte del bot

- Operaciones cerradas: **22**
- Win rate: **41%**
- PnL total: **-2.6684 SOL**
- Ganancia media: +0.2819 SOL
- Pérdida media: -0.4004 SOL
- Profit factor: 0.49
- Tiempo medio en posición: 126 min

### Por motivo de salida
| grupo | trades | win rate | PnL SOL | PnL medio % |
|---|---|---|---|---|
| liquidez | 7 | 14% | -3.5668 | -80.2% |
| stop | 8 | 12% | -1.5738 | -32.4% |
| tiempo | 3 | 100% | +1.0240 | +86.5% |
| trailing | 4 | 100% | +1.4482 | +74.9% |

### Por score de momentum
| grupo | trades | win rate | PnL SOL | PnL medio % |
|---|---|---|---|---|
| 0.5–0.6 | 11 | 45% | -0.1980 | +1.1% |
| 0.6–0.7 | 3 | 33% | -0.3630 | -23.5% |
| 0.7–0.8 | 3 | 33% | -0.6018 | -7.3% |
| 0.8–0.9 | 4 | 25% | -1.5603 | -50.0% |
| <0.5 | 1 | 100% | +0.0546 | +19.0% |

### Por edad del token
| grupo | trades | win rate | PnL SOL | PnL medio % |
|---|---|---|---|---|
| 0h–1h | 7 | 29% | -1.0484 | -13.1% |
| 1h–3h | 12 | 50% | -1.7178 | -18.2% |
| 6h–12h | 2 | 50% | +0.2430 | +40.0% |
| ≥24h | 1 | 0% | -0.1452 | -31.5% |

### Por liquidez (USD)
| grupo | trades | win rate | PnL SOL | PnL medio % |
|---|---|---|---|---|
| 0–25,000 | 6 | 17% | -1.1822 | -38.9% |
| 100,000–250,000 | 2 | 50% | +0.2708 | +40.8% |
| 25,000–50,000 | 10 | 60% | -0.4105 | +11.9% |
| 50,000–100,000 | 4 | 25% | -1.3465 | -57.2% |

### Por subida en 1h al entrar
| grupo | trades | win rate | PnL SOL | PnL medio % |
|---|---|---|---|---|
| 0%–15% | 2 | 0% | -0.2936 | -30.4% |
| 100%–150% | 3 | 67% | +0.3426 | +29.3% |
| 15%–30% | 5 | 80% | +0.0508 | +24.0% |
| 30%–60% | 2 | 50% | +0.3239 | +38.4% |
| 60%–100% | 10 | 20% | -3.0922 | -48.6% |

### Por ratio compras/ventas
| grupo | trades | win rate | PnL SOL | PnL medio % |
|---|---|---|---|---|
| 1.0–1.3 | 3 | 100% | +1.2593 | +97.8% |
| 1.3–1.6 | 10 | 20% | -2.1007 | -39.1% |
| 1.6–2.0 | 4 | 25% | -0.7936 | -27.7% |
| 2.0–3.0 | 5 | 60% | -1.0334 | -10.7% |

### Mejores y peores
| token | PnL SOL | salida |
|---|---|---|
| Eikon | +0.7602 | trailing stop (máx 370%, ahora 208%) |
| SAINDRA | +0.4445 | tiempo máximo (360m) |
| STREAM | +0.3914 | tiempo máximo (360m) |
| H20 | +0.3671 | trailing stop (máx 109%, ahora -20%) |
| FIGHT | +0.1881 | tiempo máximo (361m) |
| Polarpine | -0.4280 | liquidez cayó 61% |
| HELLCAT | -0.5298 | liquidez cayó 97% |
| LEEKDUCK | -0.6819 | liquidez cayó 96% |
| FEED | -0.7160 | liquidez cayó 89% |
| DOGELON | -0.8864 | liquidez cayó 95% |

## Configuración usada
```json
{
  "dry_run": true,
  "live_confirm": "",
  "rpc_url": "https://api.mainnet-beta.solana.com",
  "data_dir": "data",
  "scan_interval_sec": 20,
  "paper_start_sol": 2.970053,
  "position_size_sol": 0.297005,
  "max_open_positions": 8,
  "max_daily_loss_sol": 0.594011,
  "min_sol_reserve": 0.029701,
  "cooldown_minutes": 720,
  "min_age_minutes": 10,
  "max_age_hours": 48,
  "min_liquidity_usd": 15000,
  "min_mcap_usd": 60000,
  "max_mcap_usd": 8000000,
  "min_volume_h1_usd": 15000,
  "min_buys_h1": 40,
  "min_buy_sell_ratio_h1": 1.15,
  "max_buy_sell_ratio_h1": 4.0,
  "min_change_m5_pct": 0.0,
  "min_change_h1_pct": 8.0,
  "max_change_h1_pct": 150.0,
  "min_liq_to_mcap": 0.05,
  "min_score": 0.4,
  "max_rugcheck_score": 30,
  "max_roundtrip_loss_pct": 6.0,
  "stop_loss_pct": 25.0,
  "take_profit_pct": 60.0,
  "take_profit_sell_fraction": 0.5,
  "trailing_activate_pct": 30.0,
  "trailing_stop_pct": 20.0,
  "max_hold_minutes": 360,
  "liquidity_drop_exit_pct": 50.0
}
```
