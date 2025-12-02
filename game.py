import streamlit as st
import yfinance as yf
import random
import pandas as pd
from datetime import datetime, timedelta
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import re
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

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

def generate_recommendation(scenario, stocks, nse_tickers):
    """Generate trading recommendation based on scenario using chatbot"""
    try:
        llm = ChatGoogleGenerativeAI(
            temperature=0.7,
            model="gemini-2.5-flash"
        )
        
        # Prepare affected stocks info
        affected_stocks_info = []
        for stock_symbol, impact in scenario.get('impacts', {}).items():
            stock_name = stocks.get(stock_symbol, stock_symbol)
            impact_pct = impact * 100
            affected_stocks_info.append(f"{stock_name} ({impact_pct:+.1f}%)")
        
        prompt = f"""You are a stock market advisor. A market scenario has occurred:

Scenario: {scenario['text']}

Affected stocks and their price changes:
{chr(10).join(['- ' + info for info in affected_stocks_info])}

Provide a brief trading recommendation (2-3 sentences) on what actions a trader should take in this situation. Consider:
- Whether to buy, sell, or hold
- Risk management strategies
- Which stocks to focus on
- Timing considerations

Keep it concise, actionable, and professional. Maximum 150 words."""

        response = llm.invoke(prompt).content
        return response.strip()
    except Exception as e:
        return f"Based on the scenario, consider carefully analyzing the affected stocks before making trading decisions. Monitor price movements and manage risk appropriately."

def generate_feedback(scenario, scenario_trades, scenario_start_value, scenario_end_value, stocks):
    """Generate feedback on user's performance during scenario"""
    try:
        llm = ChatGoogleGenerativeAI(
            temperature=0.7,
            model="gemini-2.5-flash"
        )
        
        # Analyze trades
        trade_summary = []
        if scenario_trades:
            for trade in scenario_trades:
                stock_name = stocks.get(trade['stock'], trade['stock'])
                trade_summary.append(f"{trade['action']} {trade['shares']} shares of {stock_name} at ₹{trade['price']:.2f}")
        else:
            trade_summary.append("No trades made during scenario")
        
        value_change = scenario_end_value - scenario_start_value if scenario_start_value else 0
        value_change_pct = ((scenario_end_value / scenario_start_value - 1) * 100) if scenario_start_value and scenario_start_value > 0 else 0
        
        prompt = f"""You are a stock trading mentor providing feedback. A user just completed a market scenario:

Scenario: {scenario['text']}

User's trades during scenario:
{chr(10).join(['- ' + trade for trade in trade_summary])}

Portfolio value at start: ₹{scenario_start_value:,.2f if scenario_start_value else 0}
Portfolio value at end: ₹{scenario_end_value:,.2f}
Change: ₹{value_change:,.2f} ({value_change_pct:+.2f}%)

Provide constructive feedback (3-4 sentences) on:
- Whether the trades were appropriate for the scenario
- What went well or could be improved
- Lessons learned
- Specific advice for similar future scenarios

Be encouraging but honest. Maximum 200 words."""

        response = llm.invoke(prompt).content
        return response.strip()
    except Exception as e:
        # Fallback feedback
        value_change = scenario_end_value - scenario_start_value if scenario_start_value else 0
        value_change_pct = ((scenario_end_value / scenario_start_value - 1) * 100) if scenario_start_value and scenario_start_value > 0 else 0
        
        if len(scenario_trades) == 0:
            return "You didn't make any trades during the scenario. Consider analyzing market movements and taking calculated risks to improve your trading skills."
        elif value_change > 0:
            return f"Good job! Your portfolio value increased by ₹{value_change:,.2f} ({value_change_pct:.2f}%). Your trades during the scenario helped you capitalize on market movements."
        else:
            return f"Your portfolio value decreased by ₹{abs(value_change):,.2f} ({abs(value_change_pct):.2f}%). Consider reviewing your trading strategy and risk management techniques for similar scenarios in the future."

def generate_scenario_with_chatbot(nse_tickers):
    """Generate a random market scenario using chatbot AI"""
    try:
        llm = ChatGoogleGenerativeAI(
            temperature=0.8,
            model="gemini-2.5-flash"
        )
        
        # Get a random selection of stocks for the scenario
        available_stocks = list(nse_tickers.keys())
        selected_stocks = random.sample(available_stocks, min(5, len(available_stocks)))
        
        # Create a mapping for flexible matching
        stock_names_lower = {name.lower(): name for name in nse_tickers.keys()}
        
        prompt = f"""Generate a realistic and creative stock market scenario for Indian NSE stocks. 

Available stocks with exact names:
{chr(10).join([f'- {name}' for name in selected_stocks])}

Create a scenario that could realistically affect 2-4 of these stocks. Examples: policy changes, sector news, company announcements, market trends, economic events, RBI decisions, budget impacts, etc.

Respond in this EXACT JSON format (no other text, no markdown):
{{
    "description": "Brief exciting scenario description (max 120 chars)",
    "stocks": {{
        "Stock Name": percentage_change_as_number
    }}
}}

Rules:
- Use exact stock names as listed above
- Percentage changes: numbers between -25 and 25 (representing -25% to +25%)
- Include 2-4 stocks
- Make scenario realistic and engaging
- Return ONLY the JSON object, nothing else"""

        response = llm.invoke(prompt).content
        
        # Extract JSON from response (handle markdown code blocks if present)
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            scenario_json = json.loads(json_match.group())
            
            # Convert stock names to ticker symbols with flexible matching
            impacts = {}
            for stock_name, impact_value in scenario_json.get('stocks', {}).items():
                # Try exact match first
                if stock_name in nse_tickers:
                    ticker = nse_tickers[stock_name]
                # Try case-insensitive match
                elif stock_name.lower() in stock_names_lower:
                    ticker = nse_tickers[stock_names_lower[stock_name.lower()]]
                else:
                    # Try partial match
                    matched = False
                    for name in nse_tickers.keys():
                        if stock_name.lower() in name.lower() or name.lower() in stock_name.lower():
                            ticker = nse_tickers[name]
                            matched = True
                            break
                    if not matched:
                        continue
                
                # Handle impact value - could be percentage or decimal
                if isinstance(impact_value, (int, float)):
                    if abs(impact_value) > 1:  # If > 1, assume it's a percentage
                        impact_decimal = impact_value / 100.0
                    else:  # Already a decimal
                        impact_decimal = impact_value
                    # Clamp to reasonable range
                    impact_decimal = max(-0.25, min(0.25, impact_decimal))
                    impacts[ticker] = impact_decimal
            
            if impacts:
                description = scenario_json.get('description', 'Market event occurred!')
                if len(description) > 150:
                    description = description[:147] + "..."
                return {
                    "text": description,
                    "impacts": impacts
                }
    except Exception as e:
        # Silently fail and use fallback
        pass
    
    # Fallback to a simple scenario if chatbot fails
    fallback_stocks = random.sample(list(nse_tickers.values()), min(3, len(nse_tickers)))
    scenario_types = [
        "Market volatility! Random stock movements detected.",
        "Sector rotation underway! Stocks reacting to market shifts.",
        "News-driven volatility! Stocks responding to recent developments."
    ]
    return {
        "text": random.choice(scenario_types),
        "impacts": {stock: random.uniform(-0.15, 0.15) for stock in fallback_stocks}
    }

def show_game():
    st.header("📈 Stock Trading Simulator")
    st.markdown("""
    **Game Overview:**  
    This is a stock trading simulator where you start with ₹10,00,000 in cash. Buy and sell real NSE stocks (using live prices from Yahoo Finance) to build your portfolio. Scenarios temporarily change stock prices for fun challenges. Complete challenges to learn trading basics and climb the leaderboard based on your total portfolio value.
    """)


    # NSE Ticker names (same as dashboard)
    nse_tickers = {
        "Reliance Industries": "RELIANCE.NS",
        "Tata Consultancy Services": "TCS.NS",
        "Infosys": "INFY.NS",
        "HDFC Bank": "HDFCBANK.NS",
        "ICICI Bank": "ICICIBANK.NS",
        "Hindustan Unilever": "HINDUNILVR.NS",
        "State Bank of India": "SBIN.NS",
        "Kotak Mahindra Bank": "KOTAKBANK.NS",
        "Larsen & Toubro": "LT.NS",
        "Axis Bank": "AXISBANK.NS",
        "Bharti Airtel": "BHARTIARTL.NS",
        "ITC": "ITC.NS",
        "Wipro": "WIPRO.NS",
        "Maruti Suzuki": "MARUTI.NS",
        "Mahindra & Mahindra": "M&M.NS",
        "Tata Steel": "TATASTEEL.NS",
        "HCL Technologies": "HCLTECH.NS",
        "Bajaj Finance": "BAJFINANCE.NS",
        "Zensar Technolgies Ltd.": "ZENSARTECH.NS",
        "NTPC": "NTPC.NS"
    }
    
    # Create a mapping of ticker symbols to company names for easier access
    stocks = {ticker: name for name, ticker in nse_tickers.items()}
    stock_names = nse_tickers  # For reverse lookup

    # Initialize game state
    if 'portfolio' not in st.session_state:
        st.session_state.portfolio = {}
    if 'cash' not in st.session_state:
        st.session_state.cash = 1000000.0  # ₹10,00,000
    if 'trades' not in st.session_state:
        st.session_state.trades = []
    if 'challenges' not in st.session_state:
        st.session_state.challenges = {
            "Beginner": {"desc": "Make your first trade", "completed": False},
            "Profit Seeker": {"desc": "Achieve 5% ROI", "completed": False},
            "Trader": {"desc": "Complete 10 trades", "completed": False},
            "Survivor": {"desc": "Keep total portfolio value above ₹9,00,000 during a market crash scenario", "completed": False}

        }
    if 'tutorial_step' not in st.session_state:
        st.session_state.tutorial_step = 0
    if 'scenario_active' not in st.session_state:
        st.session_state.scenario_active = False
    if 'scenario' not in st.session_state:
        st.session_state.scenario = None
    if 'credits' not in st.session_state:
        st.session_state.credits = 5  # Start with 5 free credits
    if 'scenario_trades' not in st.session_state:
        st.session_state.scenario_trades = []  # Track trades during scenario
    if 'scenario_start_value' not in st.session_state:
        st.session_state.scenario_start_value = None
    if 'recommendation_purchased' not in st.session_state:
        st.session_state.recommendation_purchased = False
    if 'recommendation_text' not in st.session_state:
        st.session_state.recommendation_text = None
    if 'show_feedback' not in st.session_state:
        st.session_state.show_feedback = False
    if 'show_feedback_modal' not in st.session_state:
        st.session_state.show_feedback_modal = False
    if 'feedback_text' not in st.session_state:
        st.session_state.feedback_text = None
    if 'last_scenario' not in st.session_state:
        st.session_state.last_scenario = None
    if 'scenario_end_value' not in st.session_state:
        st.session_state.scenario_end_value = None

    # Fetch real prices
    @st.cache_data(ttl=300)  # Cache for 5 min
    def get_prices():
        prices = {}
        for symbol in stocks:
            try:
                data = yf.Ticker(symbol).history(period="1d")
                prices[symbol] = data['Close'].iloc[-1] if not data.empty else 1000
            except:
                prices[symbol] = 1000
        return prices
    
    @st.cache_data(ttl=300)  # Cache for 5 min
    def get_historical_data(ticker_symbol, period="3mo"):
        try:
            ticker = yf.Ticker(ticker_symbol)
            data = ticker.history(period=period, auto_adjust=True)
            data.reset_index(inplace=True)
            if 'Date' in data.columns:
                data['Date'] = data['Date'].astype(str)
                data['Date'] = data['Date'].str.split(" ").str[0]
            return data
        except:
            return pd.DataFrame()

    prices = get_prices()

    # Apply scenario impact
    if st.session_state.scenario_active and st.session_state.scenario:
        for stock, impact in st.session_state.scenario['impacts'].items():
            prices[stock] *= (1 + impact)

    # Calculate portfolio value
    portfolio_value = sum(st.session_state.portfolio.get(stock, 0) * prices[stock] for stock in stocks)
    total_value = st.session_state.cash + portfolio_value
    roi = ((total_value - 1000000) / 1000000) * 100

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
                "Welcome! Start with ₹10,00,000. Buy/sell NSE stocks to build your portfolio.",
                "Use the Trading section to buy/sell. Watch for fees (0.5%).",
                "Check your Portfolio for performance. Complete challenges to learn!",
                "Try scenarios for fun events. View charts to analyze stock trends. Good luck!"
            ]
            st.info(tutorials[st.session_state.tutorial_step])
            if st.button("Next Tip"):
                st.session_state.tutorial_step += 1
                st.rerun()

        # Trading Interface
        st.subheader("💼 Trading")
        with st.container():
            stock_symbol = st.selectbox("Select Stock", list(stocks.keys()), format_func=lambda x: f"{x} - {stocks[x]}")
            stock_name = stocks[stock_symbol]
            action = st.selectbox("Action", ["Buy", "Sell"])
            shares = st.number_input("Shares", min_value=1, step=1)
            current_price = prices[stock_symbol]
            cost = shares * current_price * 1.005  # 0.5% fee

            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Current Price", f"₹{current_price:.2f}")
            with col_b:
                st.metric("Total Cost", f"₹{cost:.2f}" if action == "Buy" else f"₹{shares * current_price * 0.995:.2f}")

            if st.button("Execute Trade"):
                if action == "Buy":
                    if st.session_state.cash >= cost:
                        st.session_state.portfolio[stock_symbol] = st.session_state.portfolio.get(stock_symbol, 0) + shares
                        st.session_state.cash -= cost
                        trade_record = {"stock": stock_symbol, "action": "Buy", "shares": shares, "price": current_price, "time": datetime.now()}
                        st.session_state.trades.append(trade_record)
                        # Track trade during scenario
                        if st.session_state.scenario_active:
                            st.session_state.scenario_trades.append(trade_record)
                        st.success(f"Bought {shares} shares of {stock_name}!")
                    else:
                        st.error("Not enough cash.")
                else:
                    if st.session_state.portfolio.get(stock_symbol, 0) >= shares:
                        st.session_state.portfolio[stock_symbol] -= shares
                        st.session_state.cash += shares * current_price * 0.995
                        trade_record = {"stock": stock_symbol, "action": "Sell", "shares": shares, "price": current_price, "time": datetime.now()}
                        st.session_state.trades.append(trade_record)
                        # Track trade during scenario
                        if st.session_state.scenario_active:
                            st.session_state.scenario_trades.append(trade_record)
                        st.success(f"Sold {shares} shares of {stock_name}!")
                    else:
                        st.error("Not enough shares.")
                st.rerun()

        # Stock Charts Section
        st.subheader("📊 Stock Charts")
        chart_stock = st.selectbox("Select Stock for Chart", list(stocks.keys()), format_func=lambda x: f"{x} - {stocks[x]}", key="chart_stock")
        chart_data = get_historical_data(chart_stock, period="3mo")
        
        if not chart_data.empty and len(chart_data) > 0:
            # Check if scenario is active for this stock
            scenario_impact = None
            if st.session_state.scenario_active and st.session_state.scenario:
                scenario_impact = st.session_state.scenario.get('impacts', {}).get(chart_stock)
            
            # Closing Price Chart
            fig_close = px.line(chart_data, x='Date', y='Close', title=f"Closing Price of {stocks[chart_stock]} (Last 3 Months)")
            fig_close.update_layout(title_x=0.5, title_font=dict(size=16), template='plotly_white')
            fig_close.update_layout(xaxis_title='Date', yaxis_title='Closing Price (₹)')
            
            # Add scenario impact visualization if active
            if scenario_impact is not None:
                last_idx = len(chart_data) - 1
                last_date = chart_data['Date'].iloc[last_idx]
                last_close = chart_data['Close'].iloc[last_idx]
                scenario_close = last_close * (1 + scenario_impact)
                
                # Add historical data line
                fig_close.update_traces(line=dict(color='blue', width=2), name='Historical Price')
                
                # Add scenario-affected price point
                fig_close.add_scatter(
                    x=[last_date],
                    y=[scenario_close],
                    mode='markers',
                    marker=dict(size=15, color='red', symbol='star'),
                    name=f'Scenario Price ({scenario_impact*100:+.1f}%)',
                    showlegend=True
                )
                
                # Add line connecting actual to scenario price
                fig_close.add_scatter(
                    x=[last_date, last_date],
                    y=[last_close, scenario_close],
                    mode='lines',
                    line=dict(color='red', width=2, dash='dash'),
                    name='Scenario Impact',
                    showlegend=False,
                    hoverinfo='skip'
                )
                
                # Add annotation
                fig_close.add_annotation(
                    x=last_date,
                    y=scenario_close,
                    text=f"Scenario: {scenario_impact*100:+.1f}%",
                    showarrow=True,
                    arrowhead=2,
                    bgcolor="red",
                    bordercolor="red",
                    font=dict(color="white", size=10)
                )
                
                fig_close.update_layout(
                    title=f"Closing Price of {stocks[chart_stock]} (Last 3 Months) - Scenario Active! ⚠️"
                )
            
            st.plotly_chart(fig_close, use_container_width=True)
            
            # Candlestick Chart
            candlestick_data = chart_data.copy()
            if scenario_impact is not None:
                # Apply scenario impact to the last candlestick
                last_idx = candlestick_data.index[-1]
                candlestick_data.loc[last_idx, 'Close'] *= (1 + scenario_impact)
                candlestick_data.loc[last_idx, 'Open'] *= (1 + scenario_impact)
                candlestick_data.loc[last_idx, 'High'] *= (1 + scenario_impact)
                candlestick_data.loc[last_idx, 'Low'] *= (1 + scenario_impact)
            
            fig_candle = go.Figure(data=[go.Candlestick(
                x=candlestick_data['Date'] if 'Date' in candlestick_data.columns else candlestick_data.index,
                open=candlestick_data['Open'],
                high=candlestick_data['High'],
                low=candlestick_data['Low'],
                close=candlestick_data['Close'],
                name='Price'
            )])
            
            candle_title = f'Candlestick Chart - {stocks[chart_stock]}'
            if scenario_impact is not None:
                candle_title += f' (Scenario: {scenario_impact*100:+.1f}%)'
            
            fig_candle.update_layout(
                title=candle_title,
                xaxis_title='Date',
                yaxis_title='Price (₹)',
                xaxis_rangeslider_visible=False,
                template='plotly_white'
            )
            st.plotly_chart(fig_candle, use_container_width=True)

        # Scenario
        st.subheader("🌪️ Scenario Challenge")
        st.write("AI-generated scenarios change stock prices temporarily. For crashes, survive by keeping your total value above ₹9,00,000.")
        if not st.session_state.scenario_active:
            if st.button("🎲 Generate AI Scenario", type="primary"):
                with st.spinner("🤖 AI is generating a unique market scenario..."):
                    scenario = generate_scenario_with_chatbot(nse_tickers)
                    st.session_state.scenario = scenario
                    st.session_state.scenario_active = True
                    st.session_state.scenario_trades = []  # Reset scenario trades
                    st.session_state.scenario_start_value = total_value  # Record start value
                    st.session_state.recommendation_purchased = False  # Reset recommendation
                    st.session_state.recommendation_text = None
                    st.rerun()
        else:
            st.warning(f"⚠️ {st.session_state.scenario['text']}")
            
            # Show affected stocks
            if st.session_state.scenario.get('impacts'):
                st.write("**Affected Stocks:**")
                for stock_symbol, impact in st.session_state.scenario['impacts'].items():
                    stock_name = stocks.get(stock_symbol, stock_symbol)
                    impact_pct = impact * 100
                    impact_sign = "+" if impact > 0 else ""
                    color = "🟢" if impact > 0 else "🔴"
                    st.write(f"{color} {stock_name}: {impact_sign}{impact_pct:.1f}%")
            
            st.write(f"**Your current total value:** ₹{total_value:,.2f}")
            
            # Check if it's a crash scenario
            scenario_text_lower = st.session_state.scenario["text"].lower()
            is_crash = any(word in scenario_text_lower for word in ["crash", "down", "fall", "drop", "decline", "plunge", "collapse"])
            if is_crash:
                st.write("**Survival threshold:** > ₹9,00,000")
            
            # Recommendation button
            st.write("---")
            st.markdown("### 💡 AI Trading Recommendation")
            if not st.session_state.recommendation_purchased:
                if st.session_state.credits >= 1:
                    if st.button("💡 Get AI Recommendation (Costs 1 Credit)", type="primary"):
                        with st.spinner("🤖 Generating personalized recommendation..."):
                            recommendation = generate_recommendation(st.session_state.scenario, stocks, nse_tickers)
                            st.session_state.recommendation_text = recommendation
                            st.session_state.recommendation_purchased = True
                            st.session_state.credits -= 1
                            st.rerun()
                else:
                    st.warning("💰 **Not enough credits!** Purchase credits from the Portfolio section to get AI-powered trading recommendations.")
                    st.info(f"You have {st.session_state.credits} credit(s). You need at least 1 credit.")
            else:
                st.success("✅ Recommendation purchased! Credits remaining: " + str(st.session_state.credits))
                with st.expander("📋 View AI Recommendation", expanded=True):
                    st.markdown(f"""
                    <div style="background-color: #e8f4f8; padding: 15px; border-radius: 10px; border-left: 4px solid #1f77b4;">
                    <strong>🤖 AI Advisor Recommendation:</strong><br><br>
                    {st.session_state.recommendation_text.replace(chr(10), '<br>')}
                    </div>
                    """, unsafe_allow_html=True)
            
            if st.button("End Scenario"):
                scenario_end_value = total_value
                last_scenario = st.session_state.scenario.copy()
                
                if st.session_state.scenario and is_crash and total_value > 900000:
                    st.session_state.challenges["Survivor"]["completed"] = True
                    st.success("🎉 You survived the crash! Challenge completed!")
                
                # Store scenario data for feedback
                st.session_state.scenario_end_value = scenario_end_value
                st.session_state.last_scenario = last_scenario
                st.session_state.scenario_active = False
                st.session_state.scenario = None
                st.session_state.show_feedback = True  # Flag to show feedback
                st.session_state.recommendation_purchased = False  # Reset for next scenario
                st.session_state.recommendation_text = None
                st.rerun()
        
        # Show feedback section if scenario just ended
        if st.session_state.get('show_feedback', False) and not st.session_state.scenario_active:
            st.write("---")
            st.subheader("📊 Scenario Feedback")
            st.info("💡 Get personalized feedback on your trading decisions during the scenario!")
            
            if not st.session_state.get('show_feedback_modal', False):
                if st.button("💬 Get AI Feedback on My Performance", type="primary"):
                    with st.spinner("🤖 Analyzing your performance..."):
                        feedback = generate_feedback(
                            st.session_state.get('last_scenario', {}),
                            st.session_state.scenario_trades,
                            st.session_state.scenario_start_value,
                            st.session_state.get('scenario_end_value', total_value),
                            stocks
                        )
                        st.session_state.feedback_text = feedback
                        st.session_state.show_feedback_modal = True
                        st.rerun()
            
            if st.session_state.get('show_feedback_modal', False) and st.session_state.feedback_text:
                st.success("✅ Feedback Generated!")
                with st.container():
                    st.markdown("### 📋 Performance Analysis")
                    st.markdown(f"""
                    <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 4px solid #1f77b4;">
                    {st.session_state.feedback_text.replace(chr(10), '<br>')}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Show scenario summary
                    if st.session_state.get('last_scenario'):
                        st.markdown("### 📈 Scenario Summary")
                        st.write(f"**Scenario:** {st.session_state.last_scenario.get('text', 'N/A')}")
                        if st.session_state.scenario_start_value:
                            st.write(f"**Starting Value:** ₹{st.session_state.scenario_start_value:,.2f}")
                        if st.session_state.get('scenario_end_value'):
                            st.write(f"**Ending Value:** ₹{st.session_state.scenario_end_value:,.2f}")
                            change = st.session_state.scenario_end_value - st.session_state.scenario_start_value
                            change_pct = ((st.session_state.scenario_end_value / st.session_state.scenario_start_value - 1) * 100) if st.session_state.scenario_start_value > 0 else 0
                            st.write(f"**Change:** ₹{change:,.2f} ({change_pct:+.2f}%)")
                        if st.session_state.scenario_trades:
                            st.write(f"**Trades Made:** {len(st.session_state.scenario_trades)}")
                    
                if st.button("✅ Close Feedback", type="secondary"):
                    st.session_state.show_feedback = False
                    st.session_state.show_feedback_modal = False
                    st.session_state.feedback_text = None
                    st.session_state.scenario_trades = []
                    st.session_state.last_scenario = None
                    st.session_state.scenario_start_value = None
                    st.session_state.scenario_end_value = None
                    st.rerun()


    with col2:
        # Portfolio Dashboard
        st.subheader("📊 Portfolio")
        st.metric("Cash", f"₹{st.session_state.cash:,.2f}")
        st.metric("Portfolio Value", f"₹{portfolio_value:,.2f}")
        st.metric("Total Value", f"₹{total_value:,.2f}")
        st.metric("ROI", f"{roi:.2f}%")
        
        # Credits Section
        st.write("---")
        st.subheader("💰 Credits")
        st.metric("Available Credits", f"{st.session_state.credits}")
        
        with st.expander("💳 Purchase Credits"):
            credit_packages = [
                {"credits": 5, "price": 50, "label": "5 Credits - ₹50"},
                {"credits": 10, "price": 90, "label": "10 Credits - ₹90 (10% off)"},
                {"credits": 20, "price": 160, "label": "20 Credits - ₹160 (20% off)"},
                {"credits": 50, "price": 350, "label": "50 Credits - ₹350 (30% off)"}
            ]
            
            selected_package = st.selectbox(
                "Select Credit Package",
                options=range(len(credit_packages)),
                format_func=lambda x: credit_packages[x]["label"]
            )
            
            package = credit_packages[selected_package]
            
            if st.button(f"Purchase {package['credits']} Credits", type="primary"):
                if st.session_state.cash >= package['price']:
                    st.session_state.cash -= package['price']
                    st.session_state.credits += package['credits']
                    st.success(f"✅ Purchased {package['credits']} credits for ₹{package['price']}!")
                    st.rerun()
                else:
                    st.error(f"❌ Insufficient cash! Need ₹{package['price']}, but you have ₹{st.session_state.cash:,.2f}")

        # Holdings
        st.write("Holdings:")
        for stock_symbol, shares in st.session_state.portfolio.items():
            if shares > 0:
                stock_display_name = stocks.get(stock_symbol, stock_symbol)
                st.write(f"{stock_display_name}: {shares} shares (₹{shares * prices[stock_symbol]:,.2f})")

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
            st.write(f"{i}. {user_id}: ₹{score:,.2f}")

        # Recent Trades
        st.subheader("📝 Recent Trades")
        if st.session_state.trades:
            df = pd.DataFrame(st.session_state.trades[-5:])  # Last 5
            st.dataframe(df)
        else:
            st.write("No trades yet.")
