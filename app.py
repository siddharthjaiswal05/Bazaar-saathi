"""Bazaar Saathi - Streamlit front end.

    ~/.venvs/sarvam-build/bin/streamlit run app.py
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import agent
import lessons
import market
import sarvam_ai
import signals
import tipcheck

st.set_page_config(page_title="Bazaar Saathi", page_icon="📈", layout="wide")

SIGNAL_COLORS = {"BUY": "#1a7f37", "SELL": "#cf222e", "HOLD": "#9a6700",
                 "LOW RISK": "#1a7f37", "CAUTION": "#9a6700", "HIGH RISK": "#cf222e"}
DISCLAIMER = ("Competition demo. Signals are rule-based and educational, designed for delivery "
              "through a SEBI-registered Research Analyst partner. Not investment advice.")
SAMPLE_TIPS = [
    "JACKPOT ALERT! Suzlon me operator entry ho chuki hai. 1 hafte me 200% dega, sure shot. "
    "Abhi kharido, kal tak late ho jayega! Full target ke liye hamara VIP Telegram group join karo.",
    "Insider news: XYZ Infra Ltd will get a ₹5000 crore govt order next week. Upper circuit "
    "guaranteed for 10 days. Buy before it's too late!",
    "HDFC Bank has corrected about 20% this year. For long-term SIP investors it may be worth "
    "reading the latest quarterly results.",
]
SAMPLE_PORTFOLIO = [
    {"name": "RELIANCE", "quantity": 10, "avg_price": 1320.50},
    {"name": "TCS", "quantity": 5, "avg_price": 3410.00},
    {"name": "INFY", "quantity": 12, "avg_price": 1550.25},
    {"name": "HDFCBANK", "quantity": 8, "avg_price": 820.00},
    {"name": "SUZLON", "quantity": 400, "avg_price": 58.00},
]


# --- setup -----------------------------------------------------------------

@st.cache_resource
def get_client():
    # On Streamlit Cloud the key comes from Settings -> Secrets; locally from .env
    try:
        if "SARVAM_API_KEY" in st.secrets:
            os.environ.setdefault("SARVAM_API_KEY", str(st.secrets["SARVAM_API_KEY"]).strip())
    except Exception:  # no secrets.toml when running locally
        pass
    return sarvam_ai.make_client()


try:
    client = get_client()
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()

ss = st.session_state
ss.setdefault("chat", [])          # [{role, text, trace, audio, language}]
ss.setdefault("history", [])       # model-facing turns
ss.setdefault("completed", set())  # finished lesson ids
ss.setdefault("last_voice", None)


@st.cache_data(show_spinner=False, ttl=3600)
def translate_many(texts: tuple[str, ...], language: str) -> list[str]:
    if language == "en-IN":
        return list(texts)
    with ThreadPoolExecutor(max_workers=6) as pool:
        return list(pool.map(lambda t: sarvam_ai.translate(client, t, language), texts))


@st.cache_data(show_spinner=False, ttl=3600)
def tts(text: str, language: str, speaker: str) -> bytes | None:
    return sarvam_ai.speak(client, text, language, speaker)


@st.cache_data(show_spinner=False, ttl=300)
def analyze(ticker: str) -> dict:
    return signals.analyze(ticker)


def badge(label: str, extra: str = "") -> str:
    color = SIGNAL_COLORS.get(label, "#57606a")
    return (f"<span style='background:{color};color:white;padding:4px 14px;border-radius:6px;"
            f"font-weight:700;font-size:1.1rem'>{label}</span> "
            f"<span style='color:#57606a'>{extra}</span>")


def play(audio: bytes | None, autoplay: bool = False) -> None:
    if audio:
        st.audio(audio, format="audio/mpeg", autoplay=autoplay)


def price_chart(ticker: str) -> go.Figure:
    df = signals.add_indicators(market.history(ticker, "2y")).tail(130)
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.04,
                        row_heights=[0.6, 0.2, 0.2],
                        subplot_titles=("Price, moving averages & Bollinger Bands", "RSI (14)", "MACD"))
    fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"],
                                 close=df["Close"], name="Price"), row=1, col=1)
    for col, color, dash in [("SMA50", "#0969da", None), ("SMA200", "#8250df", None),
                             ("BB_upper", "#8c959f", "dot"), ("BB_lower", "#8c959f", "dot")]:
        fig.add_trace(go.Scatter(x=df.index, y=df[col], name=col, line=dict(color=color, width=1.3, dash=dash)),
                      row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI", line=dict(color="#bf3989")), row=2, col=1)
    for level in (30, 70):
        fig.add_hline(y=level, line=dict(color="#8c959f", dash="dash", width=1), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD", line=dict(color="#0969da")), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["MACD_signal"], name="Signal", line=dict(color="#fb8500")), row=3, col=1)
    fig.update_layout(height=640, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=40, b=10),
                      legend=dict(orientation="h", y=1.06))
    return fig


def signal_card(card: dict) -> None:
    left, right = st.columns([3, 2])
    with left:
        st.markdown(f"### {card['name']}  ·  ₹{card['price']:,.2f}")
        st.markdown(badge(card["signal"], f"confidence {card['confidence']} · score {card['score']:+d} · "
                                          f"as of {card['date']}"), unsafe_allow_html=True)
    with right:
        if card["signal"] != "HOLD":
            a, b, c = st.columns(3)
            a.metric("Entry", f"₹{card['entry']:,.2f}")
            b.metric("Stop-loss", f"₹{card['stop_loss']:,.2f}")
            c.metric("Target", f"₹{card['target']:,.2f}")
        else:
            a, b = st.columns(2)
            a.metric("Support (20d)", f"₹{card['support_20d']:,.2f}")
            b.metric("Resistance (20d)", f"₹{card['resistance_20d']:,.2f}")
    vote_label = {1: "Bullish", 0: "Neutral", -1: "Bearish"}
    st.dataframe(pd.DataFrame([{"Indicator": v["indicator"], "Reading": v["value"],
                                "Vote": vote_label[v["vote"]], "Why": v["reason"]} for v in card["votes"]]),
                 hide_index=True, width="stretch")


# --- sidebar ---------------------------------------------------------------

with st.sidebar:
    st.title("Bazaar Saathi")
    st.caption("Your market companion, in your language.")
    language = st.selectbox("Language", list(sarvam_ai.LANGUAGES), index=1,
                            format_func=sarvam_ai.LANGUAGES.get)
    speaker = st.selectbox("Voice", ["shubh", "ritu", "priya", "aditya", "kavya", "rahul"])
    watch_text = st.text_input("Watchlist", "RELIANCE, TCS, HDFCBANK, INFY")
    st.divider()
    st.caption("Lessons completed: " + str(len(ss.completed)) + f" / {len(lessons.LESSONS)}")
    st.progress(len(ss.completed) / len(lessons.LESSONS))
    st.divider()
    st.caption(DISCLAIMER)
    st.caption("Powered by Sarvam AI: Saaras (speech), Sarvam-105B (agent), Bulbul (voice), "
               "Sarvam-Translate, Document AI.")

st.markdown("## Bazaar Saathi")
st.caption("Learn, analyse and invest safely in your own language. Ask by voice in 11 Indian languages.")

tab_ask, tab_analyse, tab_protect, tab_learn, tab_xray, tab_brief = st.tabs(
    ["Poocho · Ask", "Samjho · Analyse", "Bacho · Tip Checker", "Seekho · Learn",
     "Portfolio X-ray", "Bazaar Ki Baat"])


# --- Poocho: voice Q&A -----------------------------------------------------

with tab_ask:
    st.markdown("Ask anything about Indian stocks, by voice or text. "
                "*e.g. \"Infosys ka chart kaisa hai?\", \"TCS vs Infosys pichle saal\", \"P/E ratio kya hai?\"*")
    match_lang = st.toggle("Reply in the language I speak or type", value=True)

    for i, turn in enumerate(ss.chat):
        with st.chat_message(turn["role"]):
            st.markdown(turn["text"])
            if turn.get("trace"):
                with st.expander("Tools the agent used"):
                    for t in turn["trace"]:
                        st.markdown(f"**{t['tool']}** `{t['args']}`")
                        st.json(t["result"], expanded=False)
                tickers = [t["args"]["ticker"] for t in turn["trace"]
                           if t["tool"] == "analyze_stock" and "error" not in t["result"]]
                if tickers:
                    st.plotly_chart(price_chart(tickers[-1]), width="stretch", key=f"chart{i}")
            play(turn.get("audio"), autoplay=turn.get("fresh", False))
            turn["fresh"] = False

    voice = st.audio_input("Ask by voice", key="ask_voice")
    typed = st.chat_input("Type your question...")

    question, spoken_lang = None, language
    try:
        if voice is not None and ss.last_voice != voice.file_id:
            ss.last_voice = voice.file_id
            with st.spinner("Listening..."):
                question, spoken_lang = sarvam_ai.transcribe(client, voice.getvalue())
        elif typed:
            question = typed
            if match_lang:
                spoken_lang = sarvam_ai.detect_language(client, typed)
        if question:
            reply_lang = spoken_lang if match_lang and spoken_lang in sarvam_ai.LANGUAGES else language
            with st.spinner("Checking the market..."):
                reply, trace = agent.ask(client, ss.history, question, reply_lang)
                audio = tts(reply, reply_lang, speaker)
            ss.history += [{"role": "user", "content": question}, {"role": "assistant", "content": reply}]
            ss.chat += [{"role": "user", "text": question},
                        {"role": "assistant", "text": reply, "trace": trace, "audio": audio, "fresh": True}]
            st.rerun()
    except Exception as exc:
        st.error(f"Something went wrong: {exc}")

    if ss.chat and st.button("Clear conversation"):
        ss.chat, ss.history = [], []
        st.rerun()


# --- Samjho: signal card ---------------------------------------------------

with tab_analyse:
    st.markdown("Six indicators vote. **+3 or more = BUY, -3 or less = SELL, otherwise HOLD.** "
                "Stop-loss is 1.5x ATR, target is 2x the risk.")
    col_in, col_btn = st.columns([4, 1])
    stock_query = col_in.text_input("Stock name or symbol", "Reliance", label_visibility="collapsed")
    if col_btn.button("Analyse", type="primary", width="stretch") or "card" not in ss:
        ticker = market.resolve(stock_query)
        if not ticker:
            st.warning(f"Couldn't find '{stock_query}' on NSE/BSE.")
        else:
            with st.spinner("Computing indicators..."):
                card = analyze(ticker)
            if "error" in card:
                st.warning(card["error"])
            else:
                ss.card, ss.card_text, ss.card_audio = card, None, None

    if "card" in ss:
        card = ss.card
        signal_card(card)
        st.plotly_chart(price_chart(card["ticker"]), width="stretch")
        if st.button(f"Explain in {sarvam_ai.LANGUAGE_NAMES[language]} and read aloud"):
            with st.spinner("Explaining..."):
                ss.card_text = agent.explain_signal(client, card, language)
                ss.card_audio = tts(ss.card_text, language, speaker)
        if ss.get("card_text"):
            st.info(ss.card_text)
            play(ss.card_audio, autoplay=True)
        st.caption("Want to understand an indicator? Open it in **Seekho · Learn**.")


# --- Bacho: Tip Checker ----------------------------------------------------

with tab_protect:
    st.markdown("Got a stock tip on WhatsApp or Telegram? Paste it, upload a screenshot, or read it out. "
                "Bazaar Saathi checks it for scam patterns and against real market data.")
    pick = st.selectbox("Or try a sample tip", ["-"] + SAMPLE_TIPS, format_func=lambda t: t[:90] + ("..." if len(t) > 90 else ""))
    tip_text = st.text_area("Tip message", value="" if pick == "-" else pick, height=110)
    c1, c2 = st.columns(2)
    shot = c1.file_uploader("Screenshot of the tip", type=["png", "jpg", "jpeg"])
    tip_voice = c2.audio_input("Read the tip aloud", key="tip_voice")

    if st.button("Check this tip", type="primary"):
        try:
            text = tip_text.strip()
            if not text and shot is not None:
                with st.spinner("Reading the screenshot with Sarvam Document AI..."):
                    text = tipcheck.read_screenshot(client, shot.getvalue(), shot.name)
            if not text and tip_voice is not None:
                with st.spinner("Listening..."):
                    text, _ = sarvam_ai.transcribe(client, tip_voice.getvalue())
            if not text:
                st.warning("Paste a tip, upload a screenshot or record one first.")
            else:
                with st.spinner("Checking claims and market data..."):
                    ss.tip = tipcheck.check(client, text, language)
                    ss.tip["text"] = text
                    ss.tip_audio = tts(ss.tip["explanation"], language, speaker)
        except Exception as exc:
            st.error(f"Something went wrong: {exc}")

    if "tip" in ss:
        r = ss.tip
        if r["text"] != tip_text.strip():
            st.caption(f"Message read: \"{r['text']}\"")
        st.markdown(badge(r["verdict"], f"risk score {r['score']}"), unsafe_allow_html=True)
        st.write("")
        st.info(r["explanation"])
        play(ss.tip_audio, autoplay=True)
        left, right = st.columns(2)
        with left:
            st.markdown("**Red flags found**")
            if r["flags"]:
                for f in r["flags"]:
                    st.markdown(f"- {f['flag']}  *(+{f['weight']}, {f['type']})*")
            else:
                st.markdown("None. Still verify on the NSE website before investing.")
        with right:
            st.markdown("**Real market data**")
            for s in r["stocks"]:
                if s.get("price"):
                    st.markdown(f"- **{s['name']}** ({s['ticker']}): ₹{s['price']:,.2f}, "
                                f"{s['change_1m_pct']:+.1f}% in a month, volume {s['volume_vs_normal']}x normal"
                                + (f", market cap ₹{s['market_cap_cr']:,} cr" if s.get("market_cap_cr") else ""))
                else:
                    st.markdown(f"- **{s['mentioned']}**: not found on NSE/BSE")
            if not r["stocks"]:
                st.markdown("No specific stock named.")


# --- Seekho: lessons and quiz ----------------------------------------------

with tab_learn:
    titles = {l["id"]: f"{l['level']} · {l['title']}" + (" (done)" if l["id"] in ss.completed else "")
              for l in lessons.LESSONS}
    lesson_id = st.selectbox("Choose a lesson", list(titles), format_func=titles.get)
    lesson = lessons.BY_ID[lesson_id]

    with st.spinner("Translating with Sarvam-Translate..."):
        title, body = translate_many((lesson["title"], lesson["body"]), language)
    st.markdown(f"### {title}")
    st.markdown(body)
    if st.button("Listen to this lesson"):
        with st.spinner("Generating audio..."):
            play(tts(f"{title}. {body}", language, speaker), autoplay=True)

    if lesson["indicator"]:
        st.markdown("#### Live example")
        ex_stock = st.text_input("See it on a real stock today", "TCS", key=f"ex_{lesson_id}")
        ticker = market.resolve(ex_stock)
        card = analyze(ticker) if ticker else {"error": "not found"}
        if "error" not in card:
            keys = {"volume": ("volume", "range52")}.get(lesson["indicator"], (lesson["indicator"],))
            for v in card["votes"]:
                if v["lesson"] in keys:
                    vote = {1: "Bullish", 0: "Neutral", -1: "Bearish"}[v["vote"]]
                    st.markdown(f"**{card['name']}** · {v['indicator']}: **{v['value']}** → {vote}. {v['reason']}.")
        else:
            st.caption("Stock not found.")

    st.markdown("#### Quick quiz")
    quiz = lesson["quiz"]
    flat = []
    for q in quiz:
        flat += [q["q"], *q["options"], q["why"]]
    with st.spinner("Preparing quiz..."):
        tr = translate_many(tuple(flat), language)
    answers, pos = [], 0
    with st.form(f"quiz_{lesson_id}"):
        for i, q in enumerate(quiz):
            n = len(q["options"])
            question, options, why = tr[pos], tr[pos + 1:pos + 1 + n], tr[pos + 1 + n]
            pos += n + 2
            choice = st.radio(f"{i + 1}. {question}", range(n), format_func=lambda k, o=options: o[k],
                              index=None, key=f"q_{lesson_id}_{i}")
            answers.append((choice, q["answer"], options, why))
        submitted = st.form_submit_button("Check answers")
    if submitted:
        score = sum(1 for choice, right, _, _ in answers if choice == right)
        for i, (choice, right, options, why) in enumerate(answers):
            if choice == right:
                st.success(f"{i + 1}. Correct. {why}")
            else:
                st.error(f"{i + 1}. Answer: {options[right]}. {why}")
        st.markdown(f"**Score: {score}/{len(quiz)}**")
        if score == len(quiz):
            ss.completed.add(lesson_id)
            st.balloons()


# --- Portfolio X-ray -------------------------------------------------------

with tab_xray:
    st.markdown("Upload a screenshot of your holdings from any broker app. Sarvam Document AI reads it, "
                "then every stock gets a live price, P&L, signal and a concentration check.")
    c1, c2 = st.columns([3, 1])
    holdings_img = c1.file_uploader("Holdings screenshot", type=["png", "jpg", "jpeg", "pdf"], key="holdings_upload")
    if c2.button("Use a sample portfolio", width="stretch"):
        ss.holdings = SAMPLE_PORTFOLIO
    if holdings_img is not None and ss.get("holdings_file") != holdings_img.file_id:
        ss.holdings_file = holdings_img.file_id
        try:
            with st.spinner("Reading holdings with Sarvam Document AI..."):
                ss.holdings = agent.read_holdings(client, holdings_img.getvalue(), holdings_img.name)
            if not ss.holdings:
                st.warning("Couldn't find any holdings in that image.")
        except Exception as exc:
            st.error(f"Couldn't read the screenshot: {exc}")

    if ss.get("holdings"):
        st.caption("Check the holdings below and fix anything that was misread.")
        edited = st.data_editor(pd.DataFrame(ss.holdings), num_rows="dynamic", width="stretch",
                                key="holdings_editor")
        if st.button("Run X-ray", type="primary"):
            try:
                with st.spinner("Pricing and analysing every stock..."):
                    rows = edited.dropna(subset=["name", "quantity"]).to_dict("records")
                    ss.xray = agent.xray(rows)
                    ss.xray_text = agent.explain_xray(client, ss.xray, language)
                    ss.xray_audio = tts(ss.xray_text, language, speaker)
            except Exception as exc:
                st.error(f"Something went wrong: {exc}")

    if ss.get("xray"):
        rep = ss.xray
        a, b, c = st.columns(3)
        a.metric("Current value", f"₹{rep['total_value']:,.0f}")
        b.metric("Invested", f"₹{rep['invested']:,.0f}")
        c.metric("Profit / loss", f"₹{rep['total_pnl']:,.0f}", f"{rep['total_pnl_pct']:+.2f}%")
        table = pd.DataFrame(rep["rows"])[["name", "quantity", "avg_price", "price", "value",
                                           "pnl_pct", "weight_pct", "signal", "confidence"]]
        st.dataframe(table.rename(columns={"name": "Stock", "quantity": "Qty", "avg_price": "Avg price",
                                           "price": "Price", "value": "Value", "pnl_pct": "P&L %",
                                           "weight_pct": "Weight %", "signal": "Signal",
                                           "confidence": "Confidence"}),
                     hide_index=True, width="stretch")
        left, right = st.columns([2, 3])
        left.plotly_chart(go.Figure(go.Pie(labels=table["name"], values=table["value"], hole=0.5))
                          .update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0), showlegend=False),
                          width="stretch")
        with right:
            for w in rep["warnings"]:
                st.warning(w)
            if rep["unknown"]:
                st.caption("Not found: " + ", ".join(map(str, rep["unknown"])))
        st.info(ss.xray_text)
        play(ss.xray_audio, autoplay=True)


# --- Bazaar Ki Baat: daily audio brief -------------------------------------

with tab_brief:
    st.markdown("A 60-second spoken market update for your watchlist, in your language.")
    if st.button("Generate today's brief", type="primary"):
        tickers = [t for t in (market.resolve(w) for w in watch_text.split(",") if w.strip()) if t]
        try:
            with st.spinner("Writing and recording your brief..."):
                ss.brief, ss.brief_facts = agent.daily_brief(client, tickers, language)
                ss.brief_audio = tts(ss.brief, language, speaker)
        except Exception as exc:
            st.error(f"Something went wrong: {exc}")
    if ss.get("brief"):
        play(ss.brief_audio, autoplay=True)
        st.markdown(ss.brief)
        cols = st.columns(len(ss.brief_facts["indices"]))
        for col, q in zip(cols, ss.brief_facts["indices"]):
            if "error" not in q:
                col.metric(q["name"], f"{q['price']:,.2f}", f"{q['change_pct']:+.2f}%")
