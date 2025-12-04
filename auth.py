import streamlit as st
import sqlite3
import hashlib
from datetime import datetime

def init_auth_db():
    """Initialize the authentication database"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  email TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  name TEXT NOT NULL,
                  created_at TEXT NOT NULL)''')
    conn.commit()
    conn.close()

def hash_password(password):
    """Hash a password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(email, password, name):
    """Create a new user account"""
    init_auth_db()
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        hashed_password = hash_password(password)
        c.execute("INSERT INTO users (email, password, name, created_at) VALUES (?, ?, ?, ?)",
                  (email, hashed_password, name, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        return True, "Account created successfully!"
    except sqlite3.IntegrityError:
        return False, "Email already exists. Please use a different email."
    except Exception as e:
        return False, f"Error creating account: {str(e)}"
    finally:
        conn.close()

def verify_user(email, password):
    """Verify user credentials"""
    init_auth_db()
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        hashed_password = hash_password(password)
        c.execute("SELECT id, email, name FROM users WHERE email = ? AND password = ?",
                  (email, hashed_password))
        user = c.fetchone()
        if user:
            return True, {"id": user[0], "email": user[1], "name": user[2]}
        else:
            return False, "Invalid email or password."
    except Exception as e:
        return False, f"Error verifying credentials: {str(e)}"
    finally:
        conn.close()

def show_login_page():
    """Display the login/signup page"""
    st.set_page_config("MasteringMarket - Login", page_icon="🔐", layout="centered")
    
    # Custom CSS for login page
    st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
        background-color: #1f77b4;
        color: white;
        border-radius: 5px;
        padding: 0.5rem;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #0056b3;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Title
    st.title("🔐 MasteringMarket")
    st.markdown("### Welcome! Please login or create an account")
    
    # Tabs for Login and Sign Up
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        st.subheader("Login to Your Account")
        email = st.text_input("Email", key="login_email", placeholder="Enter your email")
        password = st.text_input("Password", type="password", key="login_password", placeholder="Enter your password")
        
        if st.button("Login", key="login_button"):
            if email and password:
                success, result = verify_user(email, password)
                if success:
                    st.session_state.authenticated = True
                    st.session_state.user = result
                    st.session_state.user_email = result["email"]
                    st.session_state.user_name = result["name"]
                    st.session_state.user_id = result["email"]  # Use email as user_id for game scores
                    st.success(f"Welcome back, {result['name']}!")
                    st.rerun()
                else:
                    st.error(result)
            else:
                st.warning("Please fill in all fields.")
    
    with tab2:
        st.subheader("Create New Account")
        name = st.text_input("Full Name", key="signup_name", placeholder="Enter your full name")
        email = st.text_input("Email", key="signup_email", placeholder="Enter your email")
        password = st.text_input("Password", type="password", key="signup_password", placeholder="Create a password")
        confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm_password", placeholder="Confirm your password")
        
        if st.button("Sign Up", key="signup_button"):
            if name and email and password and confirm_password:
                if password != confirm_password:
                    st.error("Passwords do not match. Please try again.")
                elif len(password) < 6:
                    st.error("Password must be at least 6 characters long.")
                else:
                    success, message = create_user(email, password, name)
                    if success:
                        # Auto-login after successful signup
                        st.success(message)
                        # Verify and login the user
                        verify_success, user_data = verify_user(email, password)
                        if verify_success:
                            st.session_state.authenticated = True
                            st.session_state.user = user_data
                            st.session_state.user_email = user_data["email"]
                            st.session_state.user_name = user_data["name"]
                            st.session_state.user_id = user_data["email"]  # Use email as user_id for game scores
                            st.success(f"Welcome, {user_data['name']}! You have been automatically logged in.")
                            st.rerun()
                        else:
                            st.info("Account created! Please login with your credentials.")
                    else:
                        st.error(message)
            else:
                st.warning("Please fill in all fields.")

def is_authenticated():
    """Check if user is authenticated"""
    return st.session_state.get('authenticated', False)

def logout():
    """Logout the current user"""
    st.session_state.authenticated = False
    if 'user' in st.session_state:
        del st.session_state['user']
    if 'user_email' in st.session_state:
        del st.session_state['user_email']
    if 'user_name' in st.session_state:
        del st.session_state['user_name']
    if 'user_id' in st.session_state:
        del st.session_state['user_id']
    st.rerun()

