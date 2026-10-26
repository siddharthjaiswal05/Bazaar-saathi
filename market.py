"""Market data from Yahoo Finance (free, no key). NSE tickers end in .NS, BSE in .BO."""

from __future__ import annotations

import time
import warnings

import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore", module="yfinance")

INDICES = {"^NSEI": "Nifty 50", "^BSESN": "Sensex", "^NSEBANK": "Bank Nifty"}
INDIAN_EXCHANGES = {"NSI", "BSE"}

_cache: dict[tuple, tuple[float, object]] = {}
CACHE_SECONDS = 300


def _cached(key: tuple, fetch):
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    value = fetch()
    _cache[key] = (time.time(), value)
    return value


def history(ticker: str, period: str = "1y") -> pd.DataFrame:
    """Daily OHLCV. Empty frame if the ticker is unknown."""
    return _cached(("hist", ticker, period),
                   lambda: yf.Ticker(ticker).history(period=period, auto_adjust=True))


def search(query: str, limit: int = 5) -> list[dict]:
    """Find Indian tickers by company name, e.g. 'hdfc bank' -> HDFCBANK.NS."""
    def fetch():
        quotes = yf.Search(query, max_results=15).quotes
        return [{"ticker": q["symbol"], "name": q.get("longname") or q.get("shortname") or q["symbol"]}
                for q in quotes if q.get("exchange") in INDIAN_EXCHANGES][:limit]
    return _cached(("search", query.lower()), fetch)


def resolve(name_or_ticker: str) -> str | None:
    """Best guess at a Yahoo ticker for what the user typed. NSE is preferred over BSE."""
    text = name_or_ticker.strip()
    if not text:
        return None
    if text.startswith("^") or text.upper().endswith((".NS", ".BO")):
        return text.upper()
    if not history(text.upper() + ".NS", "5d").empty:
        return text.upper() + ".NS"
    matches = search(text)
    nse = [m for m in matches if m["ticker"].endswith(".NS")]
    return (nse or matches)[0]["ticker"] if matches else None


def name_of(ticker: str) -> str:
    if ticker in INDICES:
        return INDICES[ticker]
    matches = search(ticker.split(".")[0])
    for m in matches:
        if m["ticker"] == ticker:
            return m["name"].title()
    return ticker.split(".")[0]


def quote(ticker: str) -> dict:
    hist = history(ticker, "5d")
    if hist.empty:
        return {"error": f"No data for {ticker}. Check the ticker symbol."}
    last = hist.iloc[-1]
    prev_close = float(hist["Close"].iloc[-2]) if len(hist) > 1 else float(last["Open"])
    change = float(last["Close"]) - prev_close
    return {
        "ticker": ticker,
        "name": name_of(ticker),
        "date": str(hist.index[-1].date()),
        "price": round(float(last["Close"]), 2),
        "change": round(change, 2),
        "change_pct": round(change / prev_close * 100, 2),
        "day_high": round(float(last["High"]), 2),
        "day_low": round(float(last["Low"]), 2),
        "volume": int(last["Volume"]),
    }


def performance(ticker: str, period: str) -> dict:
    hist = history(ticker, period)
    if hist.empty:
        return {"error": f"No data for {ticker}. Check the ticker symbol."}
    start, end = float(hist["Close"].iloc[0]), float(hist["Close"].iloc[-1])
    return {
        "ticker": ticker,
        "period": period,
        "from": str(hist.index[0].date()),
        "to": str(hist.index[-1].date()),
        "start_price": round(start, 2),
        "end_price": round(end, 2),
        "change_pct": round((end - start) / start * 100, 2),
        "high": round(float(hist["High"].max()), 2),
        "low": round(float(hist["Low"].min()), 2),
    }
