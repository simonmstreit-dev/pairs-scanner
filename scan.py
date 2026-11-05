#!/usr/bin/env python3
"""Premarket pairs scanner.

For every pair in pairs.csv:
  1. 1-year OLS hedge ratio on log prices, Engle-Granger cointegration p-value,
     half-life of mean reversion, daily-return correlation, hedge-ratio stability.
  2. Health tier: A (strong), B (tradeable) or dormant (not alerted).
  3. Spread z-score vs the last 60 sessions, at yesterday's close and at the
     latest premarket print.
Flags A/B pairs whose premarket |z| >= 2 and writes:
  signals/latest.json, signals/latest.md, signals/archive/<date>.json, pair_health.csv
"""
import argparse, csv, json, math, os, sys, time, traceback
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ET = ZoneInfo("America/New_York")
HERE = os.path.dirname(os.path.abspath(__file__))

CFG = dict(
    lookback=252,          # sessions used for hedge ratio / cointegration
    min_obs=200,           # minimum overlapping sessions
    z_window=60,           # sessions for spread mean / std
    z_flag=2.0,            # alert threshold
    z_extreme=4.0,         # beyond this: likely structural, stop-zone
    tier_a=dict(coint_p=0.05, corr=0.60, hl_max=40),
    tier_b=dict(coint_p=0.10, corr=0.50, hl_max=60),
    hl_min=1.0,
    beta_drift_max=0.5,    # |beta_2nd_half - beta_1st_half| / |beta| above this -> unstable
    thin_volume=5000,      # premarket shares below this = thin print
    chunk=100,
    window=((7, 50), (9, 25)),   # ET window in which scheduled runs proceed
    enrich_top=12,         # flagged pairs to fetch earnings / P/E for
)

# NYSE full-day holidays
HOLIDAYS = {date.fromisoformat(d) for d in """
2026-01-01 2026-01-19 2026-02-16 2026-04-03 2026-05-25 2026-06-19 2026-07-03 2026-09-07 2026-11-26 2026-12-25
2027-01-01 2027-01-18 2027-02-15 2027-03-26 2027-05-31 2027-06-18 2027-07-05 2027-09-06 2027-11-25 2027-12-24
2028-01-17 2028-02-21 2028-04-14 2028-05-29 2028-06-19 2028-07-04 2028-09-04 2028-11-23 2028-12-25
""".split()}


# ----------------------------------------------------------------------------- data

def _download(tickers, **kw):
    """yfinance batch download with retries; returns {field: DataFrame[tickers]}."""
    import yfinance as yf
    out = {}
    for i in range(0, len(tickers), CFG["chunk"]):
        chunk = tickers[i:i + CFG["chunk"]]
        df = None
        for attempt in range(4):
            try:
                df = yf.download(chunk, progress=False, threads=True, group_by="column",
                                 auto_adjust=True, actions=False, **kw)
                if df is not None and not df.empty:
                    break
                raise RuntimeError("empty response")
            except Exception as e:  # rate limit / network
                print(f"  chunk {i // CFG['chunk']} attempt {attempt + 1} failed: {e}", file=sys.stderr)
                df = None
                time.sleep(10 * (attempt + 1))
        if df is None:
            continue
        if not isinstance(df.columns, pd.MultiIndex):  # single ticker edge case
            df.columns = pd.MultiIndex.from_product([df.columns, chunk])
        for field in ("Close", "Volume"):
            if field in df.columns.get_level_values(0):
                part = df.xs(field, axis=1, level=0)
                out[field] = part if field not in out else out[field].join(part, how="outer")
        time.sleep(1)
    return out


def _to_et(index):
    idx = pd.DatetimeIndex(index)
    return idx.tz_localize("UTC").tz_convert(ET) if idx.tz is None else idx.tz_convert(ET)


def fetch_daily(tickers, today):
    d = _download(tickers, period="2y", interval="1d")
    if "Close" not in d:
        raise RuntimeError("daily price download returned nothing (Yahoo blocked or down)")
    close = d["Close"]
    idx = pd.DatetimeIndex(close.index)
    if idx.tz is not None:
        idx = idx.tz_convert(ET).tz_localize(None)
    close.index = idx.normalize()
    return close[close.index.date < today].sort_index()


def fetch_premarket(tickers, today):
    """Latest price printed today (ET) and today's volume so far, per ticker."""
    d = _download(tickers, period="2d", interval="5m", prepost=True, ignore_tz=False)
    if "Close" not in d:
        return pd.Series(dtype=float), pd.Series(dtype=float)
    close, vol = d["Close"], d.get("Volume")
    idx = _to_et(close.index)
    mask = idx.date == today
    close = close[mask]
    price = close.ffill().iloc[-1] if len(close) else pd.Series(dtype=float)
    volume = vol[mask].sum() if vol is not None and len(close) else pd.Series(dtype=float)
    return price.dropna(), volume


def fetch_enrichment(tickers, today):
    """Earnings dates near today and forward P/E for a handful of tickers."""
    import yfinance as yf
    info = {}
    for t in tickers:
        e = {"earnings_recent": None, "earnings_next": None, "forward_pe": None}
        try:
            tk = yf.Ticker(t)
            try:
                ed = tk.get_earnings_dates(limit=6)
                if ed is not None and len(ed):
                    days = sorted({ts.date() for ts in _to_et(ed.index)})
                    past = [x for x in days if today - timedelta(days=4) <= x <= today]
                    fut = [x for x in days if today < x <= today + timedelta(days=10)]
                    e["earnings_recent"] = past[-1].isoformat() if past else None
                    e["earnings_next"] = fut[0].isoformat() if fut else None
            except Exception:
                pass
            try:
                pe = (tk.info or {}).get("forwardPE")
                e["forward_pe"] = round(float(pe), 1) if pe else None
            except Exception:
                pass
        except Exception:
            pass
        info[t] = e
        time.sleep(0.5)
    return info


# ----------------------------------------------------------------------------- stats

def pair_stats(la, lb):
    """la, lb: aligned np arrays of log prices (oldest first)."""
    from statsmodels.tsa.stattools import coint
    X = np.column_stack([np.ones_like(lb), lb])
    alpha, beta = np.linalg.lstsq(X, la, rcond=None)[0]
    spread = la - alpha - beta * lb
    corr = float(np.corrcoef(np.diff(la), np.diff(lb))[0, 1])
    lam = np.polyfit(spread[:-1], np.diff(spread), 1)[0]
    hl = -math.log(2) / lam if lam < 0 else math.inf
    try:
        p = float(coint(la, lb)[1])
    except Exception:
        p = 1.0
    h = len(la) // 2
    b1 = np.polyfit(lb[:h], la[:h], 1)[0]
    b2 = np.polyfit(lb[h:], la[h:], 1)[0]
    drift = abs(b2 - b1) / max(abs(beta), 1e-9)
    return dict(alpha=float(alpha), beta=float(beta), spread=spread, corr=corr,
                half_life=float(hl), coint_p=p, beta_drift=float(drift))


def tier_of(s):
    reasons = []
    if s["beta"] <= 0:
        reasons.append("negative hedge ratio")
    for name, t in (("A", CFG["tier_a"]), ("B", CFG["tier_b"])):
        ok = (s["coint_p"] <= t["coint_p"] and s["corr"] >= t["corr"]
              and CFG["hl_min"] <= s["half_life"] <= t["hl_max"]
              and s["beta_drift"] <= CFG["beta_drift_max"] and s["beta"] > 0)
        if ok:
            return name, []
    b = CFG["tier_b"]
    if s["coint_p"] > b["coint_p"]:
        reasons.append(f"not cointegrated (p={s['coint_p']:.2f})")
    if s["corr"] < b["corr"]:
        reasons.append(f"low return correlation ({s['corr']:.2f})")
    if not (CFG["hl_min"] <= s["half_life"] <= b["hl_max"]):
        reasons.append("slow/no mean reversion" if s["half_life"] > b["hl_max"] else "half-life too short")
    if s["beta_drift"] > CFG["beta_drift_max"]:
        reasons.append(f"unstable hedge ratio (drift {s['beta_drift']:.2f})")
    return "dormant", reasons


def zscores(spread, w):
    s = pd.Series(spread)
    mu, sd = s.rolling(w).mean(), s.rolling(w).std()
    z = (s - mu) / sd
    return z, float(mu.iloc[-1]), float(sd.iloc[-1])


def consecutive_extended(z, thr):
    n = 0
    for v in reversed(z.dropna().values):
        if abs(v) >= thr:
            n += 1
        else:
            break
    return n


def pct(a, b):
    return None if a is None or b is None or b == 0 or pd.isna(a) or pd.isna(b) else round(100 * (a / b - 1), 2)


def r(x, n=2):
    return None if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))) else round(float(x), n)


def analyse(pairs, close, pre_px, pre_vol):
    health, flags, no_data = [], [], set()
    L, w = CFG["lookback"], CFG["z_window"]
    for p in pairs:
        a, b = p["ticker_a"], p["ticker_b"]
        row = dict(pair=f"{a}/{b}", **p)
        missing = [t for t in (a, b) if t not in close.columns or close[t].dropna().empty]
        if missing:
            no_data.update(missing)
            health.append({**row, "tier": "no_data", "reasons": f"no price data for {', '.join(missing)}"})
            continue
        df = close[[a, b]].dropna().tail(L)
        df = df[(df > 0).all(axis=1)]
        if len(df) < CFG["min_obs"]:
            health.append({**row, "tier": "no_data", "reasons": f"only {len(df)} overlapping sessions"})
            continue
        la, lb = np.log(df[a].values), np.log(df[b].values)
        s = pair_stats(la, lb)
        tier, reasons = tier_of(s)
        z, mu, sd = zscores(s["spread"], w)
        z_close = float(z.iloc[-1])
        last_a, last_b = float(df[a].iloc[-1]), float(df[b].iloc[-1])
        prev_a, prev_b = float(df[a].iloc[-2]), float(df[b].iloc[-2])
        pa, pb = pre_px.get(a), pre_px.get(b)
        has_pre = pa is not None and pb is not None and not pd.isna(pa) and not pd.isna(pb)
        if has_pre:
            s_pre = math.log(pa) - s["alpha"] - s["beta"] * math.log(pb)
            z_pre = (s_pre - mu) / sd
        else:
            pa, pb, z_pre = last_a, last_b, z_close
        h = {**row, "tier": tier, "reasons": "; ".join(reasons),
             "beta": r(s["beta"], 3), "coint_p": r(s["coint_p"], 3), "corr": r(s["corr"]),
             "half_life": r(s["half_life"], 1), "beta_drift": r(s["beta_drift"]),
             "z_close": r(z_close), "z_pre": r(z_pre), "last_close_date": df.index[-1].date().isoformat()}
        health.append(h)
        if tier in ("A", "B") and abs(z_pre) >= CFG["z_flag"]:
            rich, cheap = (a, b) if z_pre > 0 else (b, a)
            va, vb = pre_vol.get(a, 0) or 0, pre_vol.get(b, 0) or 0
            flags.append({
                "pair": f"{a}/{b}", "a": a, "b": b, "name_a": p["name_a"], "name_b": p["name_b"],
                "group": p["group"], "tier": tier,
                "z_pre": r(z_pre), "z_close": r(z_close), "z_change_overnight": r(z_pre - z_close),
                "kind": "new gap" if abs(z_close) < CFG["z_flag"] else "extended",
                "days_extended": consecutive_extended(z, CFG["z_flag"]),
                "extreme": bool(abs(z_pre) >= CFG["z_extreme"]),
                "trade": f"short {rich} / long {cheap}",
                "hedge": f"${10000 * s['beta']:,.0f} of {b} per $10,000 of {a}",
                "beta": r(s["beta"], 3), "half_life_days": r(s["half_life"], 1),
                "coint_p": r(s["coint_p"], 3), "corr": r(s["corr"]),
                "premarket_move_pct": {a: pct(pa, last_a), b: pct(pb, last_b)} if has_pre else None,
                "last_session_move_pct": {a: pct(last_a, prev_a), b: pct(last_b, prev_b)},
                "premarket_volume": {a: int(va), b: int(vb)} if has_pre else None,
                "thin_premarket": bool(has_pre and min(va, vb) < CFG["thin_volume"]),
                "used_premarket": has_pre,
                "prices": {a: r(pa), b: r(pb)},
            })
    order = {"A": 0, "B": 1}
    flags.sort(key=lambda f: (order[f["tier"]], -abs(f["z_pre"])))
    return health, flags, sorted(no_data)


# ----------------------------------------------------------------------------- io

def load_pairs(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def write_outputs(out_dir, result, health=None):
    sig = os.path.join(out_dir, "signals")
    os.makedirs(os.path.join(sig, "archive"), exist_ok=True)
    with open(os.path.join(sig, "latest.json"), "w") as f:
        json.dump(result, f, indent=1, default=str)
    if result.get("status") == "ok":
        with open(os.path.join(sig, "archive", f"{result['trading_date']}.json"), "w") as f:
            json.dump(result, f, indent=1, default=str)
    with open(os.path.join(sig, "latest.md"), "w") as f:
        f.write(render_md(result))
    if health:
        cols = ["pair", "ticker_a", "ticker_b", "name_a", "name_b", "group", "tier", "reasons", "beta",
                "coint_p", "corr", "half_life", "beta_drift", "z_close", "z_pre", "last_close_date"]
        with open(os.path.join(out_dir, "pair_health.csv"), "w", newline="") as f:
            wr = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            wr.writeheader()
            order = {"A": 0, "B": 1, "dormant": 2, "no_data": 3}
            for h in sorted(health, key=lambda x: (order.get(x["tier"], 9), x["pair"])):
                wr.writerow(h)


def render_md(res):
    lines = [f"# Premarket pairs scan: {res.get('trading_date')}",
             f"Status: **{res['status']}**, generated {res.get('generated_at_et')} ET", ""]
    if res["status"] != "ok":
        lines.append(res.get("message", ""))
        return "\n".join(lines) + "\n"
    c = res["counts"]
    lines += [f"Pairs: {c['pairs']} | tier A: {c['tier_A']} | tier B: {c['tier_B']} | dormant: {c['dormant']} "
              f"| no data: {c['no_data']} | flagged: {c['flagged']}", ""]
    if not res["flags"]:
        lines.append("No active pair is beyond the threshold this morning.")
    else:
        lines += ["| Pair | Tier | z pre | z close | Kind | Trade | Half-life | Premarket moves | Notes |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for fl in res["flags"]:
            mv = fl["premarket_move_pct"] or {}
            notes = []
            if fl["extreme"]: notes.append("EXTREME")
            if fl["thin_premarket"]: notes.append("thin premarket")
            e = fl.get("enrichment") or {}
            for t in (fl["a"], fl["b"]):
                if (e.get(t) or {}).get("earnings_recent"): notes.append(f"{t} reported {e[t]['earnings_recent']}")
                if (e.get(t) or {}).get("earnings_next"): notes.append(f"{t} reports {e[t]['earnings_next']}")
            lines.append(f"| {fl['pair']} | {fl['tier']} | {fl['z_pre']:+.2f} | {fl['z_close']:+.2f} | {fl['kind']} "
                         f"| {fl['trade']} | {fl['half_life_days']}d | "
                         + ", ".join(f"{k} {v:+.1f}%" for k, v in mv.items() if v is not None)
                         + f" | {'; '.join(notes)} |")
    return "\n".join(lines) + "\n"


# ----------------------------------------------------------------------------- main

def main(argv=None, fetchers=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="ignore the ET time window / already-ran check")
    ap.add_argument("--pairs", default=os.path.join(HERE, "pairs.csv"))
    ap.add_argument("--out", default=HERE)
    ap.add_argument("--today", help="override trading date (YYYY-MM-DD), for testing")
    args = ap.parse_args(argv)
    fx = fetchers or dict(daily=fetch_daily, pre=fetch_premarket, enrich=fetch_enrichment)

    now = datetime.now(ET)
    today = date.fromisoformat(args.today) if args.today else now.date()
    base = dict(trading_date=today.isoformat(), generated_at_et=now.strftime("%Y-%m-%d %H:%M"),
                generated_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"))

    if not args.force:
        (h0, m0), (h1, m1) = CFG["window"]
        if not ((h0, m0) <= (now.hour, now.minute) <= (h1, m1)):
            print(f"outside run window ({now:%H:%M} ET); skipping"); return 0
        try:
            prev = json.load(open(os.path.join(args.out, "signals", "latest.json")))
            if prev.get("trading_date") == today.isoformat() and prev.get("status") in ("ok", "market_closed"):
                print("already ran today; skipping"); return 0
        except Exception:
            pass

    if today.weekday() >= 5 or today in HOLIDAYS:
        write_outputs(args.out, {**base, "status": "market_closed", "message": "US market closed today."})
        print("market closed"); return 0

    try:
        pairs = load_pairs(args.pairs)
        tickers = sorted({t for p in pairs for t in (p["ticker_a"], p["ticker_b"])})
        print(f"{len(pairs)} pairs, {len(tickers)} tickers")
        close = fx["daily"](tickers, today)
        pre_px, pre_vol = fx["pre"](tickers, today)
        print(f"daily history: {close.shape}, premarket prints: {len(pre_px)}")
        health, flags, no_data = analyse(pairs, close, pre_px, pre_vol)
        top = flags[:CFG["enrich_top"]]
        if top:
            enr = fx["enrich"](sorted({t for f in top for t in (f["a"], f["b"])}), today)
            for f in top:
                f["enrichment"] = {f["a"]: enr.get(f["a"]), f["b"]: enr.get(f["b"])}
        tiers = pd.Series([h["tier"] for h in health]).value_counts().to_dict()
        result = {**base, "status": "ok",
                  "premarket_coverage": f"{len(pre_px)}/{len(tickers)} tickers",
                  "thresholds": {"z_flag": CFG["z_flag"], "z_extreme": CFG["z_extreme"], "z_window": CFG["z_window"]},
                  "counts": {"pairs": len(pairs), "tier_A": tiers.get("A", 0), "tier_B": tiers.get("B", 0),
                             "dormant": tiers.get("dormant", 0), "no_data": tiers.get("no_data", 0),
                             "flagged": len(flags)},
                  "tickers_without_data": no_data, "flags": flags}
        if len(pre_px) < 0.3 * len(tickers):
            result["warning"] = "Low premarket coverage; many z-scores fall back to yesterday's close."
        write_outputs(args.out, result, health)
        print(render_md(result))
        return 0
    except Exception as e:
        traceback.print_exc()
        write_outputs(args.out, {**base, "status": "error", "message": f"{type(e).__name__}: {e}"})
        return 1


if __name__ == "__main__":
    sys.exit(main())
