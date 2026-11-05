"""Offline test: synthetic prices, no network. Run: python tests/test_offline.py"""
import csv, json, os, shutil, sys, tempfile, time
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import scan

TODAY = "2026-11-04"
rng = np.random.default_rng(7)
N = 504
dates = pd.bdate_range(end="2026-11-03", periods=N)


def walk(n, vol=0.015, start=100):
    return start * np.exp(np.cumsum(rng.normal(0, vol, n)))


def ou(n, theta=0.15, sigma=0.01):
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = x[i - 1] - theta * x[i - 1] + rng.normal(0, sigma)
    return x


def cointegrated(base, beta=1.0, theta=0.15, sigma=0.01):
    return np.exp(beta * np.log(base) + ou(len(base), theta, sigma) + 0.2)


def test_small():
    b = walk(N); d = walk(N)
    px = pd.DataFrame({
        "AAA": cointegrated(b), "BBB": b,           # cointegrated, AAA gaps +6% premarket
        "CCC": walk(N), "DDD": walk(N),             # independent random walks
        "EEE": cointegrated(d, 0.8), "FFF": d,      # cointegrated, no premarket move
        "HHH": walk(N),                             # GGG missing entirely
    }, index=dates)
    pairs = [dict(ticker_a=a, ticker_b=b_, name_a=a, name_b=b_, group="test")
             for a, b_ in [("AAA", "BBB"), ("CCC", "DDD"), ("EEE", "FFF"), ("GGG", "HHH")]]
    last = px.iloc[-1]
    pre = last.copy(); pre["AAA"] *= 1.06
    vol = pd.Series(50000, index=pre.index)
    tmp = tempfile.mkdtemp()
    pf = os.path.join(tmp, "pairs.csv")
    with open(pf, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(pairs[0])); w.writeheader(); w.writerows(pairs)
    fx = dict(daily=lambda t, d: px, pre=lambda t, d: (pre, vol),
              enrich=lambda t, d: {x: {"earnings_recent": None, "earnings_next": None, "forward_pe": 15.0} for x in t})
    assert scan.main(["--force", "--pairs", pf, "--out", tmp, "--today", TODAY], fetchers=fx) == 0
    res = json.load(open(os.path.join(tmp, "signals", "latest.json")))
    health = {r["pair"]: r for r in csv.DictReader(open(os.path.join(tmp, "pair_health.csv")))}
    print(json.dumps(res["counts"]), [(f["pair"], f["z_pre"], f["trade"]) for f in res["flags"]])
    for k, v in health.items():
        print(" ", k, v["tier"], v["coint_p"], v["half_life"], v["reasons"])
    assert res["status"] == "ok"
    assert health["AAA/BBB"]["tier"] in ("A", "B")
    assert health["EEE/FFF"]["tier"] in ("A", "B")
    assert health["GGG/HHH"]["tier"] == "no_data"
    assert health["CCC/DDD"]["tier"] == "dormant"
    pairs_flagged = [f["pair"] for f in res["flags"]]
    assert "AAA/BBB" in pairs_flagged and "CCC/DDD" not in pairs_flagged
    f = res["flags"][pairs_flagged.index("AAA/BBB")]
    assert f["z_pre"] > 2 and f["trade"] == "short AAA / long BBB" and f["kind"] == "new gap"
    assert os.path.exists(os.path.join(tmp, "signals", "archive", f"{TODAY}.json"))
    assert "AAA/BBB" in open(os.path.join(tmp, "signals", "latest.md")).read()
    # holiday and weekend handling
    assert scan.main(["--force", "--pairs", pf, "--out", tmp, "--today", "2026-11-26"], fetchers=fx) == 0
    assert json.load(open(os.path.join(tmp, "signals", "latest.json")))["status"] == "market_closed"
    # data failure -> error status written, nonzero exit
    def boom(t, d): raise RuntimeError("Yahoo down")
    assert scan.main(["--force", "--pairs", pf, "--out", tmp, "--today", TODAY], fetchers={**fx, "daily": boom}) == 1
    assert json.load(open(os.path.join(tmp, "signals", "latest.json")))["status"] == "error"
    shutil.rmtree(tmp)
    print("small test OK")


def test_full_universe():
    """All real pairs, random prices: checks speed and that nothing crashes."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pairs = scan.load_pairs(os.path.join(root, "pairs.csv"))
    tickers = sorted({t for p in pairs for t in (p["ticker_a"], p["ticker_b"])})
    px = pd.DataFrame({t: walk(N) for t in tickers[:-3]}, index=dates)   # last 3 tickers "missing"
    px.iloc[:400, 5] = np.nan                                              # short history for one ticker
    pre = px.iloc[-1] * np.exp(rng.normal(0, 0.02, px.shape[1]))
    vol = pd.Series(rng.integers(0, 100000, px.shape[1]), index=px.columns)
    tmp = tempfile.mkdtemp()
    fx = dict(daily=lambda t, d: px, pre=lambda t, d: (pre, vol), enrich=lambda t, d: {})
    t0 = time.time()
    assert scan.main(["--force", "--pairs", os.path.join(root, "pairs.csv"), "--out", tmp, "--today", TODAY],
                     fetchers=fx) == 0
    res = json.load(open(os.path.join(tmp, "signals", "latest.json")))
    print(f"full universe: {time.time() - t0:.1f}s", json.dumps(res["counts"]), "missing:", res["tickers_without_data"])
    assert res["counts"]["pairs"] == len(pairs)
    shutil.rmtree(tmp)
    print("full test OK")


if __name__ == "__main__":
    test_small()
    test_full_universe()
