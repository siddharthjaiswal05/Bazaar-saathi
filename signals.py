"""Technical indicators and the rule-based Buy / Sell / Hold engine.

Everything here is plain arithmetic on price data, so a signal is reproducible and
every vote can be shown to the user. The AI only explains the result; it never
invents the numbers.

Rules: six indicators each vote +1 (bullish), 0 or -1 (bearish).
  total >= +3 -> BUY,  total <= -3 -> SELL,  otherwise HOLD.
Confidence counts the indicators backing the call (neutral ones for HOLD).
For BUY/SELL: stop-loss is 1.5 x ATR(14) from the entry, target is 2x that risk.
HOLD has no trade levels, only 20-day support and resistance to watch.
"""

from __future__ import annotations

import pandas as pd

import market

BUY_AT, SELL_AT = 3, -3
ATR_STOP = 1.5
REWARD_TO_RISK = 2.0


# --- indicators ------------------------------------------------------------

def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    return 100 - 100 / (1 + gain / loss)


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    line = close.ewm(span=fast, adjust=False).mean() - close.ewm(span=slow, adjust=False).mean()
    return line, line.ewm(span=signal, adjust=False).mean()


def bollinger(close: pd.Series, period: int = 20, width: float = 2.0):
    mid = close.rolling(period).mean()
    std = close.rolling(period).std()
    return mid + width * std, mid, mid - width * std


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    prev_close = df["Close"].shift()
    true_range = pd.concat([df["High"] - df["Low"],
                            (df["High"] - prev_close).abs(),
                            (df["Low"] - prev_close).abs()], axis=1).max(axis=1)
    return true_range.ewm(alpha=1 / period, adjust=False).mean()


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of an OHLCV frame with every indicator column added (for charts too)."""
    df = df.copy()
    close = df["Close"]
    df["RSI"] = rsi(close)
    df["MACD"], df["MACD_signal"] = macd(close)
    df["SMA50"] = close.rolling(50).mean()
    df["SMA200"] = close.rolling(200).mean()
    df["BB_upper"], df["BB_mid"], df["BB_lower"] = bollinger(close)
    df["ATR"] = atr(df)
    df["Vol_avg20"] = df["Volume"].rolling(20).mean()
    return df


# --- rules -----------------------------------------------------------------

def _crossed(a: pd.Series, b: pd.Series, days: int) -> int:
    """+1 if a crossed above b in the last `days` bars, -1 if below, else 0."""
    diff = (a - b).dropna().tail(days + 1)
    if len(diff) < 2:
        return 0
    signs = diff.gt(0)
    if not signs.iloc[0] and signs.iloc[-1]:
        return 1
    if signs.iloc[0] and not signs.iloc[-1]:
        return -1
    return 0


def _vote(name: str, value: str, vote: int, reason: str, lesson: str) -> dict:
    return {"indicator": name, "value": value, "vote": vote, "reason": reason, "lesson": lesson}


def votes(df: pd.DataFrame) -> list[dict]:
    last = df.iloc[-1]
    close = float(last["Close"])
    out = []

    r = float(last["RSI"])
    if r < 30:
        out.append(_vote("RSI (14)", f"{r:.0f}", 1, "Oversold: sellers may be exhausted, a bounce is possible", "rsi"))
    elif r > 70:
        out.append(_vote("RSI (14)", f"{r:.0f}", -1, "Overbought: price ran up fast, a pullback is possible", "rsi"))
    else:
        out.append(_vote("RSI (14)", f"{r:.0f}", 0, "Neutral zone (30-70)", "rsi"))

    m, s = float(last["MACD"]), float(last["MACD_signal"])
    cross = _crossed(df["MACD"], df["MACD_signal"], 5)
    if cross == 1 or (m > s and m > 0):
        why = "Fresh bullish crossover" if cross == 1 else "MACD above signal and above zero"
        out.append(_vote("MACD (12,26,9)", f"{m:.2f} vs {s:.2f}", 1, why + ": momentum is rising", "macd"))
    elif cross == -1 or (m < s and m < 0):
        why = "Fresh bearish crossover" if cross == -1 else "MACD below signal and below zero"
        out.append(_vote("MACD (12,26,9)", f"{m:.2f} vs {s:.2f}", -1, why + ": momentum is falling", "macd"))
    else:
        out.append(_vote("MACD (12,26,9)", f"{m:.2f} vs {s:.2f}", 0, "Mixed momentum", "macd"))

    sma50, sma200 = float(last["SMA50"]), last["SMA200"]
    if pd.isna(sma200):  # less than 200 days of history
        vote = 1 if close > sma50 else -1
        out.append(_vote("Moving averages", f"50-DMA ₹{sma50:,.0f}", vote,
                         ("Above" if vote > 0 else "Below") + " the 50-day average", "moving_averages"))
    else:
        sma200 = float(sma200)
        golden = _crossed(df["SMA50"], df["SMA200"], 10)
        value = f"50-DMA ₹{sma50:,.0f} / 200-DMA ₹{sma200:,.0f}"
        if golden == 1 or close > sma50 > sma200:
            why = "Golden cross" if golden == 1 else "Price above both averages, 50 above 200"
            out.append(_vote("Moving averages", value, 1, why + ": uptrend", "moving_averages"))
        elif golden == -1 or close < sma50 < sma200:
            why = "Death cross" if golden == -1 else "Price below both averages, 50 below 200"
            out.append(_vote("Moving averages", value, -1, why + ": downtrend", "moving_averages"))
        else:
            out.append(_vote("Moving averages", value, 0, "No clear trend", "moving_averages"))

    upper, lower = float(last["BB_upper"]), float(last["BB_lower"])
    value = f"₹{lower:,.0f} - ₹{upper:,.0f}"
    if close <= lower:
        out.append(_vote("Bollinger Bands (20,2)", value, 1, "At the lower band: stretched to the downside", "bollinger"))
    elif close >= upper:
        out.append(_vote("Bollinger Bands (20,2)", value, -1, "At the upper band: stretched to the upside", "bollinger"))
    else:
        out.append(_vote("Bollinger Bands (20,2)", value, 0, "Inside the bands", "bollinger"))

    ratio = float(last["Volume"] / last["Vol_avg20"]) if last["Vol_avg20"] else 0.0
    up_day = close >= float(df["Close"].iloc[-2])
    value = f"{ratio:.1f}x 20-day avg"
    if ratio > 1.5:
        vote = 1 if up_day else -1
        out.append(_vote("Volume", value, vote,
                         "Heavy buying on an up day" if up_day else "Heavy selling on a down day", "volume"))
    else:
        out.append(_vote("Volume", value, 0, "Normal volume", "volume"))

    year = df.tail(252)
    high52, low52 = float(year["High"].max()), float(year["Low"].min())
    pos = (close - low52) / (high52 - low52) * 100 if high52 > low52 else 50
    value = f"{pos:.0f}% of range (₹{low52:,.0f} - ₹{high52:,.0f})"
    if close >= high52 * 0.97:
        out.append(_vote("52-week range", value, 1, "Near the 52-week high: breakout strength", "range52"))
    elif close <= low52 * 1.03:
        out.append(_vote("52-week range", value, -1, "Near the 52-week low: breakdown weakness", "range52"))
    else:
        out.append(_vote("52-week range", value, 0, "Mid-range", "range52"))

    return out


def analyze(ticker: str) -> dict:
    """Full signal card for one ticker."""
    df = market.history(ticker, "2y")
    if df.empty or len(df) < 60:
        return {"error": f"Not enough price history for {ticker}."}
    df = add_indicators(df)
    vs = votes(df)
    score = sum(v["vote"] for v in vs)
    last = df.iloc[-1]
    close, atr_now = float(last["Close"]), float(last["ATR"])

    if score >= BUY_AT:
        signal = "BUY"
    elif score <= SELL_AT:
        signal = "SELL"
    else:
        signal = "HOLD"
    # Confidence = indicators backing the call: same-direction votes for BUY/SELL, neutral ones for HOLD
    backing = {"BUY": 1, "SELL": -1, "HOLD": 0}[signal]
    agree = sum(1 for v in vs if v["vote"] == backing)

    card = {
        "ticker": ticker,
        "name": market.name_of(ticker),
        "date": str(df.index[-1].date()),
        "price": round(close, 2),
        "signal": signal,
        "score": score,
        "confidence": f"{agree} of {len(vs)}",
        "votes": vs,
        "support_20d": round(float(df["Low"].tail(20).min()), 2),
        "resistance_20d": round(float(df["High"].tail(20).max()), 2),
    }
    if signal != "HOLD":
        risk = ATR_STOP * atr_now
        side = 1 if signal == "BUY" else -1
        card.update({
            "entry": round(close, 2),
            "stop_loss": round(close - side * risk, 2),
            "target": round(close + side * risk * REWARD_TO_RISK, 2),
        })
    return card
