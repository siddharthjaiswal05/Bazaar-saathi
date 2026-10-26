# Bazaar Saathi

A voice-first AI market companion for first-time Indian investors. It teaches the stock market, analyses stocks with transparent indicator rules, catches WhatsApp tip scams and answers questions, in 11 Indian languages.

Built on [Sarvam AI](https://docs.sarvam.ai).

**Live demo: [bazaar-saathi-49asgflkj66o5nfzksejff.streamlit.app](https://bazaar-saathi-49asgflkj66o5nfzksejff.streamlit.app)**

To try it, pick a language in the sidebar, then:
1. **Bacho:** run one of the sample WhatsApp tips through the checker.
2. **Poocho:** ask a question by voice, e.g. "Infosys ka chart kaisa hai?"
3. **Seekho:** open the RSI lesson and take its quiz.

If the app has been idle, Streamlit Cloud may take about 30 seconds to wake it up.

## The problem

Millions of new investors in India's smaller cities learn about the market from WhatsApp forwards and finfluencers. They often can't read charts, and much of the trustworthy information is in English. Bazaar Saathi gives them one place to **learn**, **analyse**, **check tips** and **ask questions**, all in their own language and by voice.

## Features

| Tab | What it does | Sarvam APIs |
|---|---|---|
| **Poocho · Ask** | Voice or text Q&A. The agent calls tools for live prices, performance and signals, then answers in the language you used, with a chart and a spoken reply. | Saaras v3, Sarvam-105B (tool calling), Bulbul v3 |
| **Samjho · Analyse** | A Buy / Sell / Hold signal card from 6 indicators, with entry, stop-loss and target, a candlestick chart, and a spoken explanation. | Sarvam-105B, Bulbul v3 |
| **Bacho · Tip Checker** | Paste a tip, upload a screenshot of it, or read it out. You get a LOW RISK / CAUTION / HIGH RISK verdict with reasons, checked against real market data. | Document AI, Saaras v3, Sarvam-105B, Bulbul v3 |
| **Seekho · Learn** | 9 lessons (basics, investing, trading), each with a live example on a real stock and a 3-question quiz. | Sarvam-Translate, Bulbul v3 |
| **Portfolio X-ray** | Upload a screenshot of your broker holdings. You get P&L, a signal for each stock and a concentration check. | Document AI, Sarvam-105B, Bulbul v3 |
| **Bazaar Ki Baat** | A 60-second spoken market brief for your watchlist. | Sarvam-105B, Bulbul v3 |

## How signals work

The rules are fixed and every vote is shown. The AI explains the numbers but never makes them up.

| Indicator | Bullish (+1) | Bearish (-1) |
|---|---|---|
| RSI (14) | below 30 | above 70 |
| MACD (12, 26, 9) | bullish crossover, or above signal and zero | bearish crossover, or below signal and zero |
| 50 / 200-day averages | golden cross, or price > 50-DMA > 200-DMA | death cross, or price < 50-DMA < 200-DMA |
| Bollinger Bands (20, 2) | at the lower band | at the upper band |
| Volume | > 1.5× the 20-day average on an up day | > 1.5× the 20-day average on a down day |
| 52-week range | within 3% of the high | within 3% of the low |

- **Signal:** a total of **+3 or more is BUY**, **-3 or less is SELL**, and anything else is HOLD.
- **Stop-loss:** 1.5 × ATR(14) from the entry price.
- **Target:** 2 × the risk (a 2:1 reward-to-risk ratio).

The Tip Checker scores red flags in the same transparent way:
- **Language:** guaranteed returns, urgency, "operator" or insider claims, and VIP groups.
- **Claims:** promised returns that are unrealistic for the timeframe.
- **Market data:** penny stocks, tiny market caps, a price pumped more than 40% in a month, and volume more than 3× normal.

> Competition demo. Signals are rule-based and educational, designed for delivery through a SEBI-registered Research Analyst partner. Not investment advice.

## Run locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then put your key in .env: SARVAM_API_KEY=...
streamlit run app.py
```

To check your key with a single API call, run `python sarvam_hello.py`.

Market data comes from Yahoo Finance through `yfinance`, which needs no key.

## Deploy your own copy (Streamlit Community Cloud)

The live demo above runs on Streamlit Community Cloud. To deploy your own:

1. Fork this repo. `.env` is git-ignored, so keys never reach GitHub.
2. On [share.streamlit.io](https://share.streamlit.io), click **Create app** and choose your fork, branch `main`, main file `app.py`.
3. In **App settings → Secrets**, add your key from the [Sarvam dashboard](https://dashboard.sarvam.ai), then click **Save changes** and reboot the app:
   ```toml
   SARVAM_API_KEY = "your-key"
   ```
   The app reads the key from Streamlit secrets, or from `.env` when running locally.

## Project layout

| File | Purpose |
|---|---|
| `app.py` | Streamlit UI with the six tabs |
| `agent.py` | The tool-calling agent, the portfolio X-ray and the daily brief |
| `signals.py` | Indicators and the Buy / Sell / Hold rules |
| `tipcheck.py` | Scam red-flag rules for the Tip Checker |
| `lessons.py` | Lesson content and quizzes |
| `market.py` | Yahoo Finance data, ticker search and caching |
| `sarvam_ai.py` | Wrappers for the Sarvam APIs: speech-to-text, chat, text-to-speech, translation and Document AI |
