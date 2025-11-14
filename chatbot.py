from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from dashboard_fixed import nse_tickers, fetch_stock_data  
load_dotenv()
import streamlit as st
from langgraph.prebuilt import create_react_agent
from langchain_tavily import TavilySearch
from langchain_core.messages import AIMessage, SystemMessage

llm = ChatGoogleGenerativeAI(
    temperature=0.7,
    model="gemini-2.5-flash"
)


search_tool = [TavilySearch(max_results=2)]


agent = create_react_agent(
    model=llm,
    tools=search_tool,
    prompt=SystemMessage(content="You are a helpful assistant that can answer questions and help with tasks.")
)




def get_response(user_input):
    state={"messages":user_input}
    response = agent.invoke(state)
    messages = response.get('messages')
    ai_message = [message.content for message in messages if isinstance(message,AIMessage)]
    return ai_message[-1]

def show_chatbot():
    st.title("Chatbot")
    user_input = st.text_input("Enter your question")
    if st.button("Ask"):
        response = get_response(user_input)
        st.write(response)
