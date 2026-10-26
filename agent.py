"""The Bazaar Saathi agent: Sarvam-105B with tools for live market data and signals."""

from __future__ import annotations

import json

import market
import sarvam_ai
import signals

MAX_TOOL_ROUNDS = 6

PERSONA = """You are Bazaar Saathi, a friendly market companion for first-time Indian investors.
You teach, analyse with transparent indicator rules, and protect people from scams.
Reply in {language} only, in simple everyday words, as if talking to someone new to investing.
Explain jargon with a local analogy (kirana shop, cricket, monsoon) when it helps.
Keep replies under 130 words, because they are read aloud. No markdown headings, no emoji.
Copy numbers exactly from the data, written as digits (e.g. 22,753 or ₹1,201.80) - never
spell numbers out in words. A confidence of "5 of 6" means 5 out of 6 indicators agree."""

ASK_PROMPT = PERSONA + """

Rules:
- For any price, change, trend or signal, call a tool. Never guess numbers.
- If you don't know a ticker, call search_stock first. NSE tickers end in .NS.
  Indices: ^NSEI = Nifty 50, ^BSESN = Sensex, ^NSEBANK = Bank Nifty.
- For "should I buy/sell", "how does X look", or technical questions, call analyze_stock and
  explain its BUY/SELL/HOLD signal with the 2-3 strongest indicator reasons. For BUY/SELL give
  the stop-loss and target from the card. HOLD has no stop-loss or target - only mention
  support_20d and resistance_20d as levels to watch.
- Mention that signals are rule-based and for learning when you give one."""

TOOLS = [
    {"type": "function", "function": {
        "name": "search_stock",
        "description": "Find NSE/BSE tickers for a company name, e.g. 'tata steel'.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "Company name"}}, "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "get_quote",
        "description": "Latest price, day change and day range for a stock or index.",
        "parameters": {"type": "object", "properties": {
            "ticker": {"type": "string", "description": "Yahoo ticker, e.g. TCS.NS or ^NSEI"}},
            "required": ["ticker"]}}},
    {"type": "function", "function": {
        "name": "get_performance",
        "description": "Price change, high and low over a period. Use for comparisons and trends.",
        "parameters": {"type": "object", "properties": {
            "ticker": {"type": "string", "description": "Yahoo ticker"},
            "period": {"type": "string", "enum": ["5d", "1mo", "3mo", "6mo", "1y", "5y"]}},
            "required": ["ticker", "period"]}}},
    {"type": "function", "function": {
        "name": "analyze_stock",
        "description": "Technical signal card: RSI, MACD, moving averages, Bollinger Bands, volume, "
                       "52-week range, each voting bullish/bearish, giving BUY/SELL/HOLD with "
                       "stop-loss and target.",
        "parameters": {"type": "object", "properties": {
            "ticker": {"type": "string", "description": "Yahoo ticker"}}, "required": ["ticker"]}}},
]

TOOL_FUNCTIONS = {
    "search_stock": lambda query: market.search(query),
    "get_quote": market.quote,
    "get_performance": market.performance,
    "analyze_stock": signals.analyze,
}


def run_tool(name: str, raw_args: str):
    func = TOOL_FUNCTIONS.get(name)
    if func is None:
        return {"error": f"Unknown tool {name}"}
    try:
        return func(**json.loads(raw_args or "{}"))
    except Exception as exc:  # hand the error to the model instead of crashing the chat
        return {"error": f"{type(exc).__name__}: {exc}"}


def ask(client, history: list[dict], question: str, language: str) -> tuple[str, list[dict]]:
    """Answer one question. Returns the reply and the tool calls made (shown in the UI)."""
    system = ASK_PROMPT.format(language=sarvam_ai.LANGUAGE_NAMES[language])
    messages = [{"role": "system", "content": system}, *history[-8:],
                {"role": "user", "content": question}]
    trace = []
    for _ in range(MAX_TOOL_ROUNDS):
        message = sarvam_ai.chat(client, messages, tools=TOOLS)
        if not message.tool_calls:
            return (message.content or "").strip(), trace
        messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [{"id": c.id, "type": "function",
                            "function": {"name": c.function.name, "arguments": c.function.arguments}}
                           for c in message.tool_calls],
        })
        for call in message.tool_calls:
            result = run_tool(call.function.name, call.function.arguments)
            trace.append({"tool": call.function.name, "args": json.loads(call.function.arguments or "{}"),
                          "result": result})
            messages.append({"role": "tool", "tool_call_id": call.id,
                             "content": json.dumps(result, ensure_ascii=False)})
    return "Sorry, I could not finish that. Please ask in a simpler way.", trace


def explain_signal(client, card: dict, language: str) -> str:
    system = PERSONA.format(language=sarvam_ai.LANGUAGE_NAMES[language]) + """
Explain this rule-based signal card: the signal and confidence first, then the 2-3
indicators that drove it in plain words. For BUY/SELL give the entry, stop-loss and target
from the card. HOLD has NO stop-loss or target: only mention support_20d and resistance_20d
as levels to watch. End with one line saying it's a rule-based learning signal."""
    return sarvam_ai.chat_text(client, system, json.dumps(card, ensure_ascii=False))


# --- Portfolio X-ray -------------------------------------------------------

HOLDINGS_SCHEMA = {
    "type": "object",
    "properties": {
        "holdings": {
            "type": "array",
            "description": "Every stock row in the broker holdings screenshot",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Stock name or trading symbol"},
                    "quantity": {"type": "number", "description": "Number of shares held"},
                    "avg_price": {"type": "number", "description": "Average buy price per share"},
                },
            },
        },
    },
}


def read_holdings(client, image: bytes, filename: str) -> list[dict]:
    data = sarvam_ai.extract_from_image(client, image, filename, HOLDINGS_SCHEMA)
    return [h for h in data.get("holdings", []) if h.get("name") and h.get("quantity")]


def xray(holdings: list[dict]) -> dict:
    """Value, P&L, weight and signal for each holding, plus concentration checks."""
    rows, unknown = [], []
    for h in holdings:
        ticker = market.resolve(str(h["name"]))
        q = market.quote(ticker) if ticker else {"error": "not found"}
        if "error" in q:
            unknown.append(h["name"])
            continue
        qty = float(h["quantity"])
        avg = float(h.get("avg_price") or 0) or q["price"]
        card = signals.analyze(ticker)
        rows.append({
            "name": q["name"], "ticker": ticker, "quantity": qty, "avg_price": avg,
            "price": q["price"], "value": round(qty * q["price"], 2),
            "pnl": round(qty * (q["price"] - avg), 2),
            "pnl_pct": round((q["price"] - avg) / avg * 100, 2),
            "signal": card.get("signal", "-"), "confidence": card.get("confidence", "-"),
        })
    total = sum(r["value"] for r in rows) or 1.0
    for r in rows:
        r["weight_pct"] = round(r["value"] / total * 100, 1)
    rows.sort(key=lambda r: r["value"], reverse=True)

    warnings = []
    if rows and rows[0]["weight_pct"] > 30:
        warnings.append(f"{rows[0]['name']} is {rows[0]['weight_pct']}% of your portfolio - concentrated risk.")
    if len(rows) < 5:
        warnings.append(f"Only {len(rows)} stocks - consider spreading across more companies or an index fund.")
    big_losers = [r["name"] for r in rows if r["pnl_pct"] < -20]
    if big_losers:
        warnings.append("Down more than 20%: " + ", ".join(big_losers) + ". Review why you hold them.")
    sells = [r["name"] for r in rows if r["signal"] == "SELL"]
    if sells:
        warnings.append("Bearish signal on: " + ", ".join(sells) + ".")

    invested = sum(r["quantity"] * r["avg_price"] for r in rows)
    return {"rows": rows, "unknown": unknown, "warnings": warnings,
            "total_value": round(total, 2), "invested": round(invested, 2),
            "total_pnl": round(total - invested, 2),
            "total_pnl_pct": round((total - invested) / invested * 100, 2) if invested else 0.0}


def explain_xray(client, report: dict, language: str) -> str:
    system = PERSONA.format(language=sarvam_ai.LANGUAGE_NAMES[language]) + """
You are giving a portfolio health check. Cover: overall profit/loss, the biggest
concentration risk, any stock with a bearish signal or a big loss, and one practical
improvement (e.g. diversify, add an index fund, set stop-losses). Under 150 words."""
    return sarvam_ai.chat_text(client, system, json.dumps(report, ensure_ascii=False))


# --- Bazaar Ki Baat (daily audio brief) -----------------------------------

def daily_brief(client, watchlist: list[str], language: str) -> tuple[str, dict]:
    facts = {"indices": [market.quote(t) for t in market.INDICES],
             "watchlist": []}
    for ticker in watchlist:
        card = signals.analyze(ticker)
        if "error" in card:
            continue
        q = market.quote(ticker)
        facts["watchlist"].append({"name": card["name"], "price": card["price"],
                                   "change_pct": q.get("change_pct"), "signal": card["signal"],
                                   "confidence": card["confidence"]})
    system = PERSONA.format(language=sarvam_ai.LANGUAGE_NAMES[language]) + """
Write a 60-second spoken market brief, like a friendly radio host. Start with a greeting
and the date, then Nifty, Sensex and Bank Nifty, then each watchlist stock in one line with
its move and signal, then one simple learning tip of the day. Under 170 words.
Round prices to whole numbers and percentages to one decimal."""
    return sarvam_ai.chat_text(client, system, json.dumps(facts, ensure_ascii=False)), facts
