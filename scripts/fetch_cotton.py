"""Fetch ICE Cotton #2 (CT=F) prices server-side and write data.json.
Runs in GitHub Actions, so no browser CORS proxies are needed."""
import json, sys, time, datetime as dt
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
HOSTS = ["query1.finance.yahoo.com", "query2.finance.yahoo.com"]

def yahoo(rng, interval):
    last = None
    for attempt in range(3):
        for h in HOSTS:
            url = f"https://{h}/v8/finance/chart/CT%3DF?range={rng}&interval={interval}&includePrePost=false"
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
                    res = json.load(r)["chart"]["result"][0]
                ts, closes = res["timestamp"], res["indicators"]["quote"][0]["close"]
                rows = [{"d": dt.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d"), "c": round(c, 2)}
                        for t, c in zip(ts, closes) if c is not None]
                return rows, res.get("meta", {})
            except Exception as e:
                last = e
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Yahoo fetch failed ({rng}/{interval}): {last}")

weekly, _ = yahoo("2y", "1wk")
daily, meta = yahoo("3mo", "1d")

# Sanity checks: refuse to overwrite good data with garbage
for rows, n in ((weekly, 60), (daily, 30)):
    if len(rows) < n or not all(20 < r["c"] < 300 for r in rows):
        sys.exit(f"Sanity check failed: {len(rows)} rows")

out = {
    "symbol": "CT=F",
    "source": "Yahoo Finance (ICE Futures US, front month)",
    "updated_utc": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "last_trade_utc": dt.datetime.utcfromtimestamp(meta["regularMarketTime"]).strftime("%Y-%m-%dT%H:%M:%SZ") if meta.get("regularMarketTime") else None,
    "weekly": weekly,
    "daily": daily,
}
with open("data.json", "w") as f:
    json.dump(out, f, separators=(",", ":"))
print(f"OK: {len(weekly)} weekly, {len(daily)} daily, last close {daily[-1]} ")
