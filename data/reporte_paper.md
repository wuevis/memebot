# Reporte del bot

- Operaciones cerradas: **13**
- Win rate: **38%**
- PnL total: **-1.7359 SOL**
- Ganancia media: +0.3073 SOL
- Pérdida media: -0.4090 SOL
- Profit factor: 0.47
- Tiempo medio en posición: 133 min

### Por motivo de salida
| grupo | trades | win rate | PnL SOL | PnL medio % |
|---|---|---|---|---|
| liquidez | 4 | 25% | -1.9271 | -69.7% |
| stop | 5 | 0% | -1.3348 | -43.5% |
| tiempo | 2 | 100% | +0.6327 | +75.1% |
| trailing | 2 | 100% | +0.8934 | +102.1% |

### Por score de momentum
| grupo | trades | win rate | PnL SOL | PnL medio % |
|---|---|---|---|---|
| 0.5–0.6 | 7 | 57% | +0.7173 | +24.6% |
| 0.6–0.7 | 2 | 50% | -0.2146 | -20.6% |
| 0.7–0.8 | 2 | 0% | -0.9932 | -65.6% |
| 0.8–0.9 | 2 | 0% | -1.2455 | -70.6% |

### Por edad del token
| grupo | trades | win rate | PnL SOL | PnL medio % |
|---|---|---|---|---|
| 0h–1h | 5 | 20% | -0.9875 | -9.6% |
| 1h–3h | 8 | 50% | -0.7484 | -11.7% |

### Por liquidez (USD)
| grupo | trades | win rate | PnL SOL | PnL medio % |
|---|---|---|---|---|
| 0–25,000 | 5 | 0% | -1.5493 | -54.7% |
| 100,000–250,000 | 1 | 0% | -0.1206 | -27.7% |
| 25,000–50,000 | 6 | 67% | -0.0764 | +26.3% |
| 50,000–100,000 | 1 | 100% | +0.0104 | +1.8% |

### Por subida en 1h al entrar
| grupo | trades | win rate | PnL SOL | PnL medio % |
|---|---|---|---|---|
| 100%–150% | 2 | 100% | +0.7706 | +86.0% |
| 15%–30% | 2 | 50% | -0.5828 | -31.6% |
| 30%–60% | 2 | 50% | +0.3239 | +38.4% |
| 60%–100% | 7 | 14% | -2.2476 | -46.7% |

### Por ratio compras/ventas
| grupo | trades | win rate | PnL SOL | PnL medio % |
|---|---|---|---|---|
| 1.0–1.3 | 2 | 100% | +1.2047 | +137.3% |
| 1.3–1.6 | 5 | 0% | -1.5493 | -54.7% |
| 1.6–2.0 | 3 | 33% | -0.6484 | -26.4% |
| 2.0–3.0 | 3 | 67% | -0.7429 | -21.1% |

### Mejores y peores
| token | PnL SOL | salida |
|---|---|---|
| Eikon | +0.7602 | trailing stop (máx 370%, ahora 208%) |
| SAINDRA | +0.4445 | tiempo máximo (360m) |
| FIGHT | +0.1881 | tiempo máximo (361m) |
| GOMODOGE | +0.1332 | trailing stop (máx 66%, ahora 3%) |
| VEILDOGE | +0.0104 | liquidez cayó 96% |
| TW | -0.3351 | liquidez cayó 65% |
| LURK | -0.3530 | stop loss -70.6% |
| ROAD | -0.3591 | stop loss -41.9% |
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
  "paper_start_sol": 2.854424,
  "position_size_sol": 0.285442,
  "max_open_positions": 8,
  "max_daily_loss_sol": 0.570885,
  "min_sol_reserve": 0.028544,
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
