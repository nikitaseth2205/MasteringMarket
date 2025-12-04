import streamlit as st
from auth import show_login_page, is_authenticated, logout

from dashboard_fixed import show_dashboard
from news import show_news
from chatbot import show_chatbot
from game import show_game

# Initialize authentication state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# Check authentication
if not is_authenticated():
    show_login_page()
else:
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = 'dashboard'

    query_params = st.query_params
    if 'tab' in query_params and query_params['tab'] in ['dashboard', 'news', 'chatbot', 'game']:
        st.session_state.active_tab = query_params['tab']

    st.set_page_config("MasteringMarket", layout="wide")

    # Header navigation with logout
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("MasteringMarket")
        if 'user_name' in st.session_state:
            st.write(f"Welcome back, {st.session_state.user_name}! 👋")
    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing
        if st.button("Logout", key="logout_button"):
            logout()
    
    # st.image("images.jpg", width='stretch')

    tab1, tab2, tab3, tab4 = st.tabs(["Stock Analysis Dashboard", "News and Current Affairs", "Chatbot", "Portfolio Game"])

    with tab1:
        show_dashboard()

    with tab2:
        show_news()

    with tab3:
        show_chatbot()

    with tab4:
        show_game()

# Custom CSS for background and styling
st.markdown(
    """
    <style>
    body {
        background-image: url('images.jpg');
        background-size: cover;
        background-attachment: fixed;
        background-repeat: no-repeat;
        background-position: center;
    }
    .main {
        background-color: rgba(255, 255, 255, 0.9);
        padding: 20px;
        border-radius: 10px;
    }
    .chatbot-icon {
        position: fixed;
        bottom: 20px;
        left: 20px;
        width: 60px;
        height: 60px;
        background-color: #007bff;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        z-index: 1000;
        transition: background-color 0.3s;
    }
    .chatbot-icon:hover {
        background-color: #0056b3;
    }
    .chatbot-icon img {
        width: 30px;
        height: 30px;
    }
    .stock-doodle {
        position: fixed;
        top: 10px;
        right: 10px;
        width: 100px;
        height: 100px;
        background-image: url('https://example.com/stock-doodle.png');
        background-size: contain;
        background-repeat: no-repeat;
        opacity: 0.5;
        z-index: 999;
    }
    </style>
    <div class="stock-doodle"></div>
    <div class="chatbot-icon" onclick="document.querySelector('button[data-baseweb=tab]:nth-child(3)').click()">
        <img src="https://img.icons8.com/material-outlined/24/ffffff/chat.png" alt="Chat">
    </div>
    """,
    unsafe_allow_html=True
)
