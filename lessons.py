"""Seekho: short lessons with a live example and a 3-question quiz.

Lessons are written in simple English and translated on demand with Sarvam-Translate.
`indicator` links a lesson to a vote in signals.py, so the app can show today's real
reading for any stock ("TCS's RSI today is 72 - this is overbought").
"""

from __future__ import annotations

LESSONS = [
    {
        "id": "share",
        "level": "Basics",
        "title": "What is a share?",
        "body": """A share is a small piece of ownership in a company. If a company is divided into 100 crore shares and you own 1, you own a tiny part of that business.

When the company grows and earns more, more people want its shares, so the price usually goes up. When it struggles, the price usually falls.

In India, shares trade on two stock exchanges: NSE and BSE. To buy them you need a demat account (where shares are stored) and a trading account with a broker such as Zerodha, Groww or Upstox.

Think of it like owning a part of your neighbourhood kirana shop. If the shop does well, your part becomes more valuable.""",
        "indicator": None,
        "quiz": [
            {"q": "What does owning a share mean?",
             "options": ["You lent money to the company", "You own a small part of the company",
                         "You work for the company", "You get a fixed monthly salary"],
             "answer": 1, "why": "A share is a piece of ownership, not a loan."},
            {"q": "Which are India's two main stock exchanges?",
             "options": ["RBI and SEBI", "NSE and BSE", "SBI and LIC", "NASDAQ and NYSE"],
             "answer": 1, "why": "NSE and BSE are exchanges. SEBI is the regulator, RBI is the central bank."},
            {"q": "Where are your shares stored?",
             "options": ["Bank locker", "Demat account", "Savings account", "With the company"],
             "answer": 1, "why": "Shares are held electronically in a demat account."},
        ],
    },
    {
        "id": "sip",
        "level": "Investing",
        "title": "SIP and the power of compounding",
        "body": """A SIP (Systematic Investment Plan) means investing a fixed amount every month, for example ₹1,000, usually into a mutual fund.

Compounding means your returns also start earning returns. ₹1,000 a month for 20 years is ₹2.4 lakh invested. At 12% a year it can grow to about ₹10 lakh. Most of that growth comes in the later years, which is why starting early matters more than starting big.

A SIP also removes the need to "time the market". When prices are low, your fixed amount buys more units; when high, fewer. This is called rupee cost averaging.

The key rules: start early, stay regular, and don't stop your SIP when markets fall.""",
        "indicator": None,
        "quiz": [
            {"q": "What is a SIP?",
             "options": ["A one-time big investment", "Investing a fixed amount regularly",
                         "A type of bank loan", "A government tax"],
             "answer": 1, "why": "SIP = Systematic Investment Plan, a fixed amount every month."},
            {"q": "Why does starting early matter so much?",
             "options": ["Prices are always lower earlier", "Compounding needs time to grow",
                         "Brokers charge less", "It doesn't matter"],
             "answer": 1, "why": "Compounding grows fastest in later years, so more years means much more growth."},
            {"q": "Markets fall 10%. What should a SIP investor usually do?",
             "options": ["Stop the SIP immediately", "Continue - the same money buys more units",
                         "Sell everything", "Switch to gold"],
             "answer": 1, "why": "Falls let your SIP buy more units cheaply (rupee cost averaging)."},
        ],
    },
    {
        "id": "diversify",
        "level": "Investing",
        "title": "Diversification: don't put all eggs in one basket",
        "body": """Diversification means spreading your money across different companies, sectors and asset types, so one bad event can't wipe you out.

If all your money is in one stock and it falls 50%, you lose half. If it is spread across 15 stocks in different sectors, one stock falling 50% hurts you only about 3%.

A simple beginner approach: an index fund that tracks Nifty 50 gives you 50 large companies across sectors in one investment.

A warning sign: if one stock or one sector is more than 25-30% of your portfolio, you are taking concentrated risk. Portfolio X-ray in this app checks this for you.""",
        "indicator": None,
        "quiz": [
            {"q": "What is diversification?",
             "options": ["Buying only the best stock", "Spreading money across many investments",
                         "Trading every day", "Keeping all money in cash"],
             "answer": 1, "why": "Spreading out means no single failure can sink you."},
            {"q": "What does a Nifty 50 index fund give you?",
             "options": ["One company", "50 large companies in one investment",
                         "Guaranteed returns", "Only bank stocks"],
             "answer": 1, "why": "It tracks the 50 companies in the Nifty 50 index."},
            {"q": "One stock is 60% of your portfolio. This is...",
             "options": ["Well diversified", "Concentrated risk", "Risk free", "Required by SEBI"],
             "answer": 1, "why": "Above 25-30% in one stock is concentrated risk."},
        ],
    },
    {
        "id": "rsi",
        "level": "Trading",
        "title": "RSI: is the stock overbought or oversold?",
        "body": """RSI (Relative Strength Index) measures how fast and how much a price has moved recently, on a scale of 0 to 100. We use the last 14 days.

Above 70 = overbought. The price has risen very fast; buyers may be tired, and a pullback is possible.
Below 30 = oversold. The price has fallen very fast; sellers may be exhausted, and a bounce is possible.
Between 30 and 70 = neutral.

Think of a runner: after a long sprint (RSI above 70) they need to slow down and catch their breath.

Careful: in a strong trend RSI can stay above 70 for weeks. That's why Bazaar Saathi never relies on RSI alone - it combines six indicators.""",
        "indicator": "rsi",
        "quiz": [
            {"q": "RSI is 78. What does it suggest?",
             "options": ["Oversold", "Overbought", "Neutral", "Company is bankrupt"],
             "answer": 1, "why": "Above 70 is overbought."},
            {"q": "RSI is 25. What might happen next?",
             "options": ["A bounce is possible", "It must fall more", "Nothing", "Stock gets delisted"],
             "answer": 0, "why": "Below 30 is oversold - sellers may be exhausted."},
            {"q": "Why shouldn't you trade on RSI alone?",
             "options": ["It is illegal", "It can stay extreme in strong trends",
                         "It is always wrong", "It only works for Nifty"],
             "answer": 1, "why": "Strong trends keep RSI extreme, so confirm with other indicators."},
        ],
    },
    {
        "id": "macd",
        "level": "Trading",
        "title": "MACD: is momentum rising or falling?",
        "body": """MACD (Moving Average Convergence Divergence) shows momentum - whether the price is speeding up or slowing down.

It has two lines: the MACD line (difference between a 12-day and 26-day average) and the signal line (a 9-day average of MACD).

When MACD crosses above the signal line, momentum is turning up - a bullish crossover.
When MACD crosses below the signal line, momentum is turning down - a bearish crossover.
When both are above zero, the overall trend is up; below zero, down.

Think of a car's speedometer: MACD tells you if the car is accelerating or braking, not just where it is.""",
        "indicator": "macd",
        "quiz": [
            {"q": "MACD crosses above its signal line. This is...",
             "options": ["Bearish crossover", "Bullish crossover", "Death cross", "Upper circuit"],
             "answer": 1, "why": "Crossing above the signal line means momentum is turning up."},
            {"q": "What does MACD mainly measure?",
             "options": ["Company profit", "Momentum", "Dividend", "Number of shareholders"],
             "answer": 1, "why": "MACD measures momentum - speeding up or slowing down."},
            {"q": "MACD and signal are both below zero. The broad trend is...",
             "options": ["Up", "Down", "Guaranteed to reverse", "Unknown"],
             "answer": 1, "why": "Below zero means the short-term average is under the long-term one."},
        ],
    },
    {
        "id": "moving_averages",
        "level": "Trading",
        "title": "Moving averages, golden cross and death cross",
        "body": """A moving average smooths out daily noise. The 50-day moving average (50-DMA) is the average closing price of the last 50 days; the 200-DMA uses 200 days.

Price above both averages, with the 50-DMA above the 200-DMA = uptrend.
Price below both, with the 50-DMA below the 200-DMA = downtrend.

Golden cross: the 50-DMA crosses above the 200-DMA. A widely watched bullish sign.
Death cross: the 50-DMA crosses below the 200-DMA. A bearish sign.

Many big investors watch the 200-DMA as the line between a healthy and an unhealthy stock.""",
        "indicator": "moving_averages",
        "quiz": [
            {"q": "The 50-DMA crosses above the 200-DMA. This is called...",
             "options": ["Death cross", "Golden cross", "Bull trap", "Gap up"],
             "answer": 1, "why": "50 crossing above 200 is the golden cross."},
            {"q": "Price is below both the 50-DMA and 200-DMA. The trend is...",
             "options": ["Uptrend", "Downtrend", "Sideways for sure", "Not measurable"],
             "answer": 1, "why": "Below both key averages signals a downtrend."},
            {"q": "What does a moving average do?",
             "options": ["Predicts the exact future price", "Smooths out daily price noise",
                         "Shows company debt", "Shows dividends"],
             "answer": 1, "why": "It averages recent prices to show the underlying trend."},
        ],
    },
    {
        "id": "bollinger",
        "level": "Trading",
        "title": "Bollinger Bands: how stretched is the price?",
        "body": """Bollinger Bands draw a channel around the 20-day average: an upper band and a lower band, each 2 standard deviations away.

About 95% of the time, prices stay inside the bands. So:
Price touching the upper band = stretched upward, may cool off.
Price touching the lower band = stretched downward, may bounce back.

When the bands squeeze close together, the market is quiet - often a big move comes next.

Think of a rubber band: the further it stretches, the stronger the pull back to the middle.""",
        "indicator": "bollinger",
        "quiz": [
            {"q": "Price touches the lower Bollinger Band. This suggests...",
             "options": ["Stretched downward, may bounce", "Guaranteed crash",
                         "Company is growing", "Upper circuit"],
             "answer": 0, "why": "The lower band means the price is stretched to the downside."},
            {"q": "Bollinger Bands are built around which average?",
             "options": ["200-day", "20-day", "5-year", "1-day"],
             "answer": 1, "why": "The middle line is the 20-day average."},
            {"q": "The bands squeeze very tight. What often follows?",
             "options": ["A big move", "The stock gets delisted", "Nothing ever", "A dividend"],
             "answer": 0, "why": "Low volatility squeezes often come before big moves."},
        ],
    },
    {
        "id": "volume",
        "level": "Trading",
        "title": "Volume and the 52-week range",
        "body": """Volume is the number of shares traded in a day. It shows how strongly people believe in a move.

A price rise on heavy volume (more than 1.5 times the 20-day average) means many buyers agree - a strong move. A rise on low volume is weaker and less trustworthy. A fall on heavy volume means strong selling.

The 52-week range is the lowest and highest price in the last year. A stock breaking out near its 52-week high shows strength; one breaking down near its 52-week low shows weakness.

Warning: a sudden volume explosion in a small, unknown stock is a classic sign of a pump-and-dump. The Tip Checker looks for exactly this.""",
        "indicator": "volume",
        "quiz": [
            {"q": "Price rises on 3x normal volume. The move is...",
             "options": ["Weak", "Strong - many buyers agree", "Meaningless", "Illegal"],
             "answer": 1, "why": "High volume confirms that many participants support the move."},
            {"q": "What is the 52-week range?",
             "options": ["Price over the last week", "Lowest and highest price in the last year",
                         "Company's yearly profit", "52 stocks in an index"],
             "answer": 1, "why": "It's the low-to-high price range over the past year."},
            {"q": "A tiny unknown stock suddenly trades 10x normal volume after a WhatsApp tip. Be...",
             "options": ["Excited", "Suspicious - possible pump-and-dump", "Sure it will double", "Calm, it's normal"],
             "answer": 1, "why": "Sudden volume spikes in small stocks after tips are a classic scam pattern."},
        ],
    },
    {
        "id": "stop_loss",
        "level": "Trading",
        "title": "Stop-loss and position sizing",
        "body": """A stop-loss is a price at which you exit a trade to limit your loss. Decide it before you buy, never after.

Bazaar Saathi places the stop-loss 1.5 times the ATR (Average True Range - the stock's normal daily movement) away from the entry. This gives the stock room to move normally but cuts the loss if the idea is wrong.

The target is set at 2 times the risk. If you risk ₹50 per share, the target is ₹100 above entry. With this 2:1 ratio, you can be wrong more than half the time and still make money overall.

Position sizing: never risk more than 1-2% of your total capital on one trade. With ₹1 lakh, risk at most ₹1,000-2,000 per trade.""",
        "indicator": None,
        "quiz": [
            {"q": "When should you decide your stop-loss?",
             "options": ["After the price falls", "Before you buy", "Never", "Only on Fridays"],
             "answer": 1, "why": "Plan your exit before entering, when you're calm."},
            {"q": "You risk ₹40 per share with a 2:1 reward-to-risk. The target is how far above entry?",
             "options": ["₹20", "₹40", "₹80", "₹400"],
             "answer": 2, "why": "2 x ₹40 = ₹80."},
            {"q": "With ₹1 lakh capital, the maximum risk per trade should be about...",
             "options": ["₹1,000-2,000", "₹25,000", "₹50,000", "All of it"],
             "answer": 0, "why": "Risking 1-2% per trade keeps you in the game after losses."},
        ],
    },
]

BY_ID = {lesson["id"]: lesson for lesson in LESSONS}
# signals.py vote lessons -> lesson id here
VOTE_LESSON = {"rsi": "rsi", "macd": "macd", "moving_averages": "moving_averages",
               "bollinger": "bollinger", "volume": "volume", "range52": "volume"}
