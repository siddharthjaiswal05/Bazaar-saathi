"""Bacho: check a WhatsApp / Telegram stock tip for scam patterns.

The verdict is rule-based so it is consistent and explainable:
  1. Language flags  - guaranteed returns, urgency, "operator" talk (English, Hinglish, Hindi).
  2. Claim flags     - promised return too big for the timeframe.
  3. Data flags      - penny stock, tiny company, pumped price, volume explosion, unknown stock.
Each flag has a weight. Total >= 5 is HIGH RISK, >= 2 is CAUTION, else LOW RISK.
"""

from __future__ import annotations

import re

import market
import sarvam_ai

HIGH, MEDIUM, LOW = 3, 2, 1
HIGH_RISK_AT, CAUTION_AT = 5, 2

# (pattern, weight, explanation)
LANGUAGE_FLAGS = [
    (r"guarant|पक्का|गारंटी|sure\s*shot|100\s*%\s*(sure|safe)|no\s*risk|risk\s*free|zero\s*risk",
     HIGH, "Promises guaranteed or risk-free profit. No real investment can guarantee returns."),
    (r"jackpot|multibagger|rocket|double|triple|\d+\s*x\b|dugna|दुगना|lottery",
     MEDIUM, "Uses hype words like 'jackpot', 'multibagger' or '10x'."),
    (r"abhi|turant|jaldi|urgent|today\s*only|aaj\s*hi|last\s*chance|immediately|अभी|जल्दी|तुरंत|before\s*it'?s\s*too\s*late",
     MEDIUM, "Creates urgency so you buy before you can think or check."),
    (r"operator|insider|inside\s*news|andar\s*ki\s*khabar|अंदर\s*की|secret|confidential|leak",
     HIGH, "Claims insider or 'operator' information. Trading on real insider info is illegal; fake insider tips are a classic pump-and-dump."),
    (r"join|vip|premium\s*group|telegram|whatsapp\s*group|paid\s*group|subscription|fees?",
     MEDIUM, "Pushes you to join a paid or VIP group. Scammers earn from fees and from selling to the people they recruit."),
    (r"upper\s*circuit|circuit\s*lagega|u\.?c\.?\b",
     MEDIUM, "Predicts 'upper circuit' moves, typical of operated small stocks."),
]


def _language_flags(text: str) -> list[dict]:
    return [{"flag": why, "weight": weight, "type": "language"}
            for pattern, weight, why in LANGUAGE_FLAGS if re.search(pattern, text, re.I)]


def _claim_flags(claimed_pct: float | None, days: float | None) -> list[dict]:
    if not claimed_pct:
        return []
    days = days or 365
    yearly = claimed_pct * 365 / max(days, 1)
    if claimed_pct >= 50 and days <= 90:
        return [{"flag": f"Promises {claimed_pct:.0f}% in about {days:.0f} days. "
                         "Nifty averages roughly 12% a year; this claim is unrealistic.",
                 "weight": HIGH, "type": "claim"}]
    if yearly >= 40:
        return [{"flag": f"Promises {claimed_pct:.0f}% - that's far above normal market returns.",
                 "weight": MEDIUM, "type": "claim"}]
    return []


def _data_flags(stock: str) -> tuple[str | None, list[dict], dict]:
    ticker = market.resolve(stock)
    if not ticker:
        return None, [{"flag": f"Could not find '{stock}' on NSE/BSE. Tips about obscure or "
                               "unlisted names are a big warning sign.",
                       "weight": MEDIUM, "type": "data"}], {}
    df = market.history(ticker, "6mo")
    if df.empty or len(df) < 25:
        return ticker, [{"flag": f"{ticker} has very little trading history.",
                         "weight": MEDIUM, "type": "data"}], {}

    flags = []
    close = float(df["Close"].iloc[-1])
    month_ago = float(df["Close"].iloc[-22])
    month_change = (close - month_ago) / month_ago * 100
    recent_vol = float(df["Volume"].tail(5).mean())
    base_vol = float(df["Volume"].iloc[-65:-5].mean()) or 1.0
    vol_ratio = recent_vol / base_vol
    facts = {"ticker": ticker, "name": market.name_of(ticker), "price": round(close, 2),
             "change_1m_pct": round(month_change, 1), "volume_vs_normal": round(vol_ratio, 1)}

    if close < 20:
        flags.append({"flag": f"Penny stock at ₹{close:.2f}. Very cheap shares are easy to manipulate.",
                      "weight": HIGH, "type": "data"})
    if month_change > 40:
        flags.append({"flag": f"Already up {month_change:.0f}% in a month. You may be buying "
                              "from the people who pumped it.", "weight": HIGH, "type": "data"})
    if vol_ratio > 3:
        flags.append({"flag": f"Trading volume is {vol_ratio:.1f}x normal - a sudden crowd rush, "
                              "a classic pump sign.", "weight": MEDIUM, "type": "data"})
    try:
        cap = market.yf.Ticker(ticker).fast_info.get("marketCap")
    except Exception:
        cap = None
    if cap:
        facts["market_cap_cr"] = round(cap / 1e7)
        if cap < 500 * 1e7:
            flags.append({"flag": f"Tiny company (market value about ₹{cap / 1e7:,.0f} crore). "
                                  "Small companies are the easiest to operate.",
                          "weight": MEDIUM, "type": "data"})
    return ticker, flags, facts


EXTRACT_PROMPT = """You read stock tips forwarded on WhatsApp/Telegram in any Indian language.
Return JSON only:
{"stocks": [company names or symbols mentioned],
 "claimed_return_pct": number or null (e.g. "200% dega" -> 200, "double" -> 100),
 "timeframe_days": number or null (e.g. "1 week" -> 7, "is mahine" -> 30),
 "summary": one short English sentence of what the tip asks people to do}"""

EXPLAIN_PROMPT = """You are Bazaar Saathi, protecting first-time Indian investors from stock-tip scams.
Write the verdict for the user in {language}, simple and warm, under 110 words.
State the verdict first, then the 2-3 most important reasons from the flags, then one
practical tip (e.g. check on NSE website, never pay for tips, report to SEBI SCORES).
Use only the facts given. No markdown headings, no emoji."""


def check(client, tip_text: str, language: str) -> dict:
    parsed = sarvam_ai.chat_json(client, EXTRACT_PROMPT, tip_text) or {}
    flags = _language_flags(tip_text)
    flags += _claim_flags(parsed.get("claimed_return_pct"), parsed.get("timeframe_days"))

    stocks = []
    for name in (parsed.get("stocks") or [])[:3]:
        ticker, data_flags, facts = _data_flags(str(name))
        flags += data_flags
        stocks.append({"mentioned": name, "ticker": ticker, **facts})

    score = sum(f["weight"] for f in flags)
    if score >= HIGH_RISK_AT:
        verdict = "HIGH RISK"
    elif score >= CAUTION_AT:
        verdict = "CAUTION"
    else:
        verdict = "LOW RISK"

    result = {"verdict": verdict, "score": score, "flags": flags,
              "stocks": stocks, "summary": parsed.get("summary", ""),
              "claimed_return_pct": parsed.get("claimed_return_pct"),
              "timeframe_days": parsed.get("timeframe_days")}
    facts = {k: result[k] for k in ("verdict", "score", "stocks", "summary")}
    facts["flags"] = [f["flag"] for f in flags]
    result["explanation"] = sarvam_ai.chat_text(
        client, EXPLAIN_PROMPT.format(language=sarvam_ai.LANGUAGE_NAMES[language]),
        f"Tip: {tip_text}\n\nAnalysis: {facts}")
    return result


TIP_SCHEMA = {
    "type": "object",
    "properties": {
        "message": {"type": "string",
                    "description": "The full text of the stock tip message in the screenshot"},
    },
}


def read_screenshot(client, image: bytes, filename: str) -> str:
    return sarvam_ai.extract_from_image(client, image, filename, TIP_SCHEMA).get("message", "")
