from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from dashboard_fixed import nse_tickers, fetch_stock_data
import streamlit as st
from langgraph.prebuilt import create_react_agent
from langchain_tavily import TavilySearch
from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.prompts import PromptTemplate

load_dotenv()

llm = ChatGoogleGenerativeAI(
    temperature=0.7,
    model="gemini-2.5-flash",
)

system_prompt = """You are a Stock Market Expert Chatbot.
You must answer only questions related to the stock market, including: stocks, indices, trading strategies, technical analysis, fundamental analysis, risk management, financial news, investor psychology, and market instruments.

If the user asks anything outside the stock market, you must respond with:
"Sorry, I can only answer stock-market-related questions."

Keep answers simple, clear, and accurate."""

# This PromptTemplate strictly frames the task as stock-market-only
# and allows arbitrary comparison data to be injected as context.
prompt_template = PromptTemplate(
    input_variables=["question", "comparison_data"],
    template=system_prompt
    + """

User question:
{question}

Additional data for comparison (if any):
{comparison_data}
""",
)

search_tool = [TavilySearch(max_results=2)]

agent = create_react_agent(
    model=llm,
    tools=search_tool,
    prompt=SystemMessage(content=system_prompt),
)


def get_response(user_input, comparison_data=None):
    """Get a response from the stock-market-only chatbot.

    Args:
        user_input (str): The user's question.
        comparison_data (Any, optional): Extra data (e.g., dict, JSON, text)
            that the user wants the model to use for comparison.
    """
    if not isinstance(user_input, str) or not user_input.strip():
        return "Please enter a valid stock-market-related question."

    # Prepare comparison data as a readable string for the prompt
    if comparison_data is None or comparison_data == "":
        comparison_data_str = "No additional comparison data was provided."
    else:
        comparison_data_str = str(comparison_data)

    # Use the PromptTemplate to build the final input text
    formatted_input = prompt_template.format(
        question=user_input.strip(),
        comparison_data=comparison_data_str,
    )

    # Pass the formatted prompt into the LangGraph ReAct agent
    state = {"messages": formatted_input}
    response = agent.invoke(state)
    messages = response.get("messages", [])
    ai_message_contents = [
        message.content
        for message in messages
        if isinstance(message, AIMessage)
    ]

    if not ai_message_contents:
        return "No response generated."

    last_content = ai_message_contents[-1]

    # If the content is already a plain string, just return it
    if isinstance(last_content, str):
        return last_content

    # If the content is a list of parts (e.g. [{"type":"text", "text": ...}, ...]),
    # extract and join only the text fields so the user sees clean text.
    if isinstance(last_content, list):
        collected_texts = []
        for part in last_content:
            # plain string part
            if isinstance(part, str):
                collected_texts.append(part)
            # dict-like content from some LLM backends
            elif isinstance(part, dict):
                if part.get("type") == "text" and "text" in part:
                    collected_texts.append(part["text"])
            else:
                # objects with a .text attribute
                text_attr = getattr(part, "text", None)
                if isinstance(text_attr, str):
                    collected_texts.append(text_attr)

        if collected_texts:
            return "\n\n".join(collected_texts)
        # Fallback: stringify if we couldn't parse parts
        return str(last_content)

    # Fallback for any other unexpected content type
    return str(last_content)


def show_chatbot():
    st.title("Chatbot")
    user_input = st.text_input("Enter your question")
    
    # Option to compare stocks
    compare_stocks = st.checkbox("Compare Stocks", value=False)
    comparison_data = None
    
    if compare_stocks:
        st.subheader("Select Stocks to Compare")
        col1, col2 = st.columns(2)
        
        with col1:
            stock1 = st.selectbox("Select First Stock", list(nse_tickers.keys()), key="stock1")
            ticker_symbol1 = nse_tickers[stock1]
            time_period1 = st.selectbox("Time Period", ["1d", "5d", "1mo"], index=2, key="time1")
        
        with col2:
            stock2 = st.selectbox("Select Second Stock", list(nse_tickers.keys()), key="stock2")
            ticker_symbol2 = nse_tickers[stock2]
            time_period2 = st.selectbox("Time Period", ["1d", "5d", "1mo"], index=2, key="time2")
        
        if st.button("Fetch Comparison Data"):
            with st.spinner("Fetching stock data..."):
                try:
                    stock_data1 = fetch_stock_data(stock1, time_period1, ticker_symbol1)
                    stock_data2 = fetch_stock_data(stock2, time_period2, ticker_symbol2)
                    
                    if not stock_data1.empty and not stock_data2.empty:
                        # Prepare comparison data
                        latest_price1 = stock_data1['Close'].iloc[-1]
                        previous_price1 = stock_data1['Close'].iloc[-2] if len(stock_data1) > 1 else latest_price1
                        change1 = latest_price1 - previous_price1
                        change_pct1 = (change1 / previous_price1 * 100) if previous_price1 > 0 else 0
                        
                        latest_price2 = stock_data2['Close'].iloc[-1]
                        previous_price2 = stock_data2['Close'].iloc[-2] if len(stock_data2) > 1 else latest_price2
                        change2 = latest_price2 - previous_price2
                        change_pct2 = (change2 / previous_price2 * 100) if previous_price2 > 0 else 0
                        
                        comparison_data = f"""
STOCK COMPARISON:

Stock 1: {stock1} ({ticker_symbol1})
- Current Price: ₹{latest_price1:.2f}
- Price Change: ₹{change1:.2f} ({change_pct1:+.2f}%)
- Period: {time_period1}

Stock 2: {stock2} ({ticker_symbol2})
- Current Price: ₹{latest_price2:.2f}
- Price Change: ₹{change2:.2f} ({change_pct2:+.2f}%)
- Period: {time_period2}

Price Difference: ₹{abs(latest_price1 - latest_price2):.2f}
"""
                        st.session_state.stock_comparison_data = comparison_data
                        st.success("Stock comparison data fetched successfully!")
                        st.text_area("Comparison Summary", comparison_data, height=150, key="comparison_display", disabled=True)
                    else:
                        st.error("Unable to fetch data for one or both stocks.")
                        st.session_state.stock_comparison_data = None
                except Exception as e:
                    st.error(f"Error fetching stock data: {str(e)}")
                    st.session_state.stock_comparison_data = None
        
        # Use stored comparison data if available
        if 'stock_comparison_data' in st.session_state and st.session_state.stock_comparison_data:
            comparison_data = st.session_state.stock_comparison_data
    else:
        # Clear stored data if not comparing stocks
        if 'stock_comparison_data' in st.session_state:
            st.session_state.stock_comparison_data = None

    if st.button("Ask"):
        if not user_input.strip():
            st.warning("Please enter a question.")
        else:
            response = get_response(user_input, comparison_data=comparison_data)
            # Only display the model's final answer text
            st.write(response)
