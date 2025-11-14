import streamlit as st
import yfinance as yf
import random
import pandas as pd
from datetime import datetime, timedelta
import sqlite3

# Game database functions
def init_game_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS game_scores
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_email TEXT NOT NULL,
                  score REAL NOT NULL,
                  date TEXT NOT NULL)''')
    conn.commit()
    conn.close()

def save_game_score(user_id, score):
    init_game_db()  # Ensure table exists
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT INTO game_scores (user_email, score, date) VALUES (?, ?, ?)",
              (user_id, score, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()

def get_leaderboard():
    init_game_db()  # Ensure table exists
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT user_email, MAX(score) as max_score FROM game_scores GROUP BY user_email ORDER BY max_score DESC LIMIT 10")
    results = c.fetchall()
    conn.close()
    return results

def show_game():
    st.header("📈 Stock Trading Simulator")
    st.markdown("""
    **Game Overview:**  
    This is a stock trading simulator where you start with $10,000 in cash. Buy and sell real stocks (using live prices from Yahoo Finance) to build your portfolio. Scenarios temporarily change stock prices for fun challenges. Complete challenges to learn trading basics and climb the leaderboard based on your total portfolio value.
    """)


    # Available stocks
    stocks = {
        "AAPL": "Apple Inc.",
        "GOOGL": "Alphabet Inc.",
        "MSFT": "Microsoft Corp.",
        "TSLA": "Tesla Inc.",
        "AMZN": "Amazon.com Inc.",
        "NVDA": "NVIDIA Corp."
    }

    # Initialize game state
    if 'portfolio' not in st.session_state:
        st.session_state.portfolio = {}
    if 'cash' not in st.session_state:
        st.session_state.cash = 10000.0
    if 'trades' not in st.session_state:
        st.session_state.trades = []
    if 'challenges' not in st.session_state:
        st.session_state.challenges = {
            "Beginner": {"desc": "Make your first trade", "completed": False},
            "Profit Seeker": {"desc": "Achieve 5% ROI", "completed": False},
            "Trader": {"desc": "Complete 10 trades", "completed": False},
            "Survivor": {"desc": "Keep total portfolio value above $9,000 during a market crash scenario", "completed": False}

        }
    if 'tutorial_step' not in st.session_state:
        st.session_state.tutorial_step = 0
    if 'scenario_active' not in st.session_state:
        st.session_state.scenario_active = False
    if 'scenario' not in st.session_state:
        st.session_state.scenario = None

    # Fetch real prices
    @st.cache_data(ttl=300)  # Cache for 5 min
    def get_prices():
        prices = {}
        for symbol in stocks:
            try:
                data = yf.Ticker(symbol).history(period="1d")
                prices[symbol] = data['Close'].iloc[-1] if not data.empty else 100
            except:
                prices[symbol] = 100
        return prices

    prices = get_prices()

    # Apply scenario impact
    if st.session_state.scenario_active and st.session_state.scenario:
        for stock, impact in st.session_state.scenario['impacts'].items():
            prices[stock] *= (1 + impact)

    # Calculate portfolio value
    portfolio_value = sum(st.session_state.portfolio.get(stock, 0) * prices[stock] for stock in stocks)
    total_value = st.session_state.cash + portfolio_value
    roi = ((total_value - 10000) / 10000) * 100

    # Update challenges
    if len(st.session_state.trades) >= 1 and not st.session_state.challenges["Beginner"]["completed"]:
        st.session_state.challenges["Beginner"]["completed"] = True
    if roi >= 5 and not st.session_state.challenges["Profit Seeker"]["completed"]:
        st.session_state.challenges["Profit Seeker"]["completed"] = True
    if len(st.session_state.trades) >= 10 and not st.session_state.challenges["Trader"]["completed"]:
        st.session_state.challenges["Trader"]["completed"] = True

    # UI Layout
    col1, col2 = st.columns([2, 1])

    with col1:
        # Tutorial
        if st.session_state.tutorial_step < 4:
            st.subheader("🎓 Tutorial")
            tutorials = [
                "Welcome! Start with $10,000. Buy/sell stocks to build your portfolio.",
                "Use the Trading section to buy/sell. Watch for fees (0.5%).",
                "Check your Portfolio for performance. Complete challenges to learn!",
                "Try scenarios for fun events. Good luck!"
            ]
            st.info(tutorials[st.session_state.tutorial_step])
            if st.button("Next Tip"):
                st.session_state.tutorial_step += 1
                st.rerun()

        # Trading Interface
        st.subheader("💼 Trading")
        with st.container():
            stock = st.selectbox("Select Stock", list(stocks.keys()), format_func=lambda x: f"{x} - {stocks[x]}")
            action = st.selectbox("Action", ["Buy", "Sell"])
            shares = st.number_input("Shares", min_value=1, step=1)
            current_price = prices[stock]
            cost = shares * current_price * 1.005  # 0.5% fee

            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Current Price", f"${current_price:.2f}")
            with col_b:
                st.metric("Total Cost", f"${cost:.2f}" if action == "Buy" else f"${shares * current_price * 0.995:.2f}")

            if st.button("Execute Trade"):
                if action == "Buy":
                    if st.session_state.cash >= cost:
                        st.session_state.portfolio[stock] = st.session_state.portfolio.get(stock, 0) + shares
                        st.session_state.cash -= cost
                        st.session_state.trades.append({"stock": stock, "action": "Buy", "shares": shares, "price": current_price, "time": datetime.now()})
                        st.success(f"Bought {shares} {stock}!")
                    else:
                        st.error("Not enough cash.")
                else:
                    if st.session_state.portfolio.get(stock, 0) >= shares:
                        st.session_state.portfolio[stock] -= shares
                        st.session_state.cash += shares * current_price * 0.995
                        st.session_state.trades.append({"stock": stock, "action": "Sell", "shares": shares, "price": current_price, "time": datetime.now()})
                        st.success(f"Sold {shares} {stock}!")
                    else:
                        st.error("Not enough shares.")
                st.rerun()

        # Scenario
        st.subheader("🌪️ Scenario Challenge")
        st.write("Scenarios change stock prices temporarily. For crashes, survive by keeping your total value above $9,000.")
        if not st.session_state.scenario_active:
            if st.button("Trigger Random Scenario"):
                scenarios = [
                    {"text": "Market Crash! Tech stocks down 10%.", "impacts": {"AAPL": -0.1, "GOOGL": -0.1, "MSFT": -0.1, "TSLA": -0.15}},
                    {"text": "AI Boom! NVIDIA surges 20%.", "impacts": {"NVDA": 0.2}},
                    {"text": "Oil Rally! Energy stocks up 15%.", "impacts": {"XOM": 0.15} if "XOM" in stocks else {}}
                ]
                st.session_state.scenario = random.choice(scenarios)
                st.session_state.scenario_active = True
                st.rerun()
        else:
            st.warning(st.session_state.scenario["text"])
            st.write(f"Your current total value: ${total_value:.2f}")
            if "Crash" in st.session_state.scenario["text"]:
                st.write("Survival threshold: > $9,000")
            if st.button("End Scenario"):
                if st.session_state.scenario and "Crash" in st.session_state.scenario["text"] and total_value > 9000:  # Survived if >90% of initial
                    st.session_state.challenges["Survivor"]["completed"] = True
                st.session_state.scenario_active = False
                st.session_state.scenario = None
                st.rerun()


    with col2:
        # Portfolio Dashboard
        st.subheader("📊 Portfolio")
        st.metric("Cash", f"${st.session_state.cash:.2f}")
        st.metric("Portfolio Value", f"${portfolio_value:.2f}")
        st.metric("Total Value", f"${total_value:.2f}")
        st.metric("ROI", f"{roi:.2f}%")

        # Holdings
        st.write("Holdings:")
        for stock, shares in st.session_state.portfolio.items():
            if shares > 0:
                st.write(f"{stock}: {shares} shares (${shares * prices[stock]:.2f})")

        # Progress Bar for ROI
        st.progress(min(max(roi / 50, 0), 1))  # Up to 50% ROI

        # Challenges
        st.subheader("🏆 Challenges")
        for name, data in st.session_state.challenges.items():
            status = "✅" if data["completed"] else "❌"
            st.write(f"{status} {name}: {data['desc']}")

        # Leaderboard
        st.subheader("🥇 Leaderboard")
        if st.button("Update Score"):
            user_id = st.session_state.get('user_id', f"user_{datetime.now().strftime('%Y%m%d%H%M%S')}")
            save_game_score(user_id, total_value)
            st.success("Score updated!")
        leaderboard = get_leaderboard()
        for i, (user_id, score) in enumerate(leaderboard[:5], 1):
            st.write(f"{i}. {user_id}: ${score:.2f}")

        # Recent Trades
        st.subheader("📝 Recent Trades")
        if st.session_state.trades:
            df = pd.DataFrame(st.session_state.trades[-5:])  # Last 5
            st.dataframe(df)
        else:
            st.write("No trades yet.")
