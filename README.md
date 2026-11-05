# Premarket pairs scanner

Scans 468 rival-company pairs every US trading morning (~8:05 ET) and flags spreads
that are stretched in premarket.

## How it works

For each pair, using the last 252 sessions:

- **Hedge ratio:** OLS of log(A) on log(B), giving `spread = log A − β·log B − α`.
- **Pair health:**
  - **Tier A:** cointegration p ≤ 0.05, return correlation ≥ 0.60, half-life ≤ 40 days.
  - **Tier B:** p ≤ 0.10, correlation ≥ 0.50, half-life ≤ 60 days.
  - Both tiers also require a stable hedge ratio (first half of the window vs second half).
  - **Dormant:** everything else. These pairs are not alerted; `pair_health.csv` says why.
- **Signal:** the spread z-score against its 60-session mean and standard deviation, computed at yesterday's close and at the latest premarket print.
- **What gets flagged:** Tier A and B pairs with premarket |z| ≥ 2.
  - |z| ≥ 4 is marked **EXTREME**. That's usually news and more often structural.
  - Each flag is tagged **new gap** (it was inside ±2 at yesterday's close) or **extended** (it was already outside ±2).
  - Flags also carry earnings dates within a few days and forward P/E.

## Files

| File | What |
|---|---|
| `pairs.csv` | Active universe. Edit it to add or remove pairs. |
| `removed_pairs.csv` | Pairs rejected on fundamentals, with reasons |
| `pair_health.csv` | Daily statistical vetting of every pair |
| `signals/latest.json` / `.md` | This morning's scan |
| `signals/archive/` | One JSON file per day |
| `build_pairs.py` | Regenerates the two pair CSVs |
| `tests/test_offline.py` | Synthetic-data tests (no network) |

## Running

- **Automatic:** `.github/workflows/premarket-scan.yml` runs on weekdays and skips NYSE holidays.
- **Manual:** Actions → premarket-scan → Run workflow (forces a run at any hour).
- **Locally:** `pip install -r requirements.txt && python scan.py --force`

Prices come from Yahoo Finance via `yfinance`. These are research signals, not trade recommendations.
