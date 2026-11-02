import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime, time

# --- DATABASE SETUP ---
DB_FILE = "mess_booking.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT,
            is_admin INTEGER DEFAULT 0
        )
    ''')
    
    # Create Bookings Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            booking_date TEXT,
            meal_type TEXT,
            price REAL,
            timestamp TEXT,
            FOREIGN KEY (username) REFERENCES users(username)
        )
    ''')
    
    # Seed default Admin account if it doesn't exist
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        admin_hash = hashlib.sha256("adminpassword".encode()).hexdigest()
        cursor.execute("INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, 1)", ('admin', admin_hash))
        
    # Seed default test users if they don't exist
    cursor.execute("SELECT * FROM users WHERE username = 'rahul'")
    if not cursor.fetchone():
        u1_hash = hashlib.sha256("password123".encode()).hexdigest()
        cursor.execute("INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, 0)", ('rahul', u1_hash))
        
    cursor.execute("SELECT * FROM users WHERE username = 'amit'")
    if not cursor.fetchone():
        u2_hash = hashlib.sha256("mess456".encode()).hexdigest()
        cursor.execute("INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, 0)", ('amit', u2_hash))
        
    conn.commit()
    conn.close()

init_db()

# --- PRICING LOGIC ---
# Standard pricing matrix: Weekly repeating base rates (Monday=0, Sunday=6)
# Customize these values as required for your mess structure
WEEKLY_PRICES = {
    "Lunch": {0: 60, 1: 60, 2: 60, 3: 60, 4: 60, 5: 70, 6: 80},  # Weekend rates higher
    "Dinner": {0: 70, 1: 70, 2: 70, 3: 70, 4: 70, 5: 80, 6: 90}
}

def get_meal_price(meal_type, date_obj):
    day_of_week = date_obj.weekday()
    return WEEKLY_PRICES[meal_type].get(day_of_week, 60.0)

# --- TIME BOUNDARY CUTOFF RULES ---
LUNCH_CUTOFF = time(9, 30)
DINNER_CUTOFF = time(17, 30)

# --- AUTHENTICATION UTILITIES ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_user(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash, is_admin FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    if row and row['password_hash'] == hash_password(password):
        return {"authenticated": True, "is_admin": bool(row['is_admin'])}
    return {"authenticated": False, "is_admin": False}

def register_user(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, 0)", 
                       (username, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

# --- STREAMLIT SESSION INITIALIZATION ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# --- UI INTERFACE GRAPHICS ---
st.set_page_config(page_title="Mess Booking System", page_icon="🍲", layout="wide")
st.title("🍲 Institutional Mess Booking & Ledger Portal")

# --- AUTHENTICATION SCREEN CONTROLLER ---
if not st.session_state.authenticated:
    auth_mode = st.radio("Choose Mode", ["Log In", "Sign Up / Register User"], horizontal=True)
    
    with st.form("auth_form"):
        username_input = st.text_input("Username").strip().lower()
        password_input = st.text_input("Password", type="password")
        submit_btn = st.form_submit_button("Submit Action")
        
        if submit_btn:
            if not username_input or not password_input:
                st.error("Please fill in all input verification credentials.")
            elif auth_mode == "Log In":
                res = verify_user(username_input, password_input)
                if res["authenticated"]:
                    st.session_state.authenticated = True
                    st.session_state.username = username_input
                    st.session_state.is_admin = res["is_admin"]
                    st.success(f"Welcome back, {username_input}!")
                    st.rerun()
                else:
                    st.error("Invalid credentials entered. Please try again.")
            elif auth_mode == "Sign Up / Register User":
                if username_input == "admin":
                    st.error("Reservations restricted. System namespace 'admin' is locked.")
                elif register_user(username_input, password_input):
                    st.success("Registration successful! You may now switch to Log In mode.")
                else:
                    st.error("Registration failed. Account username already exists in database.")
    st.stop()

# --- MAIN SYSTEM INTERFACE (AUTHENTICATED) ---
# Sidebar Controller
st.sidebar.markdown(f"### 👤 Active User: **{st.session_state.username}**")
if st.session_state.is_admin:
    st.sidebar.info("👑 Administrator Account Context Active")

if st.sidebar.button("Log Out System"):
    st.session_state.authenticated = False
    st.session_state.username = ""
    st.session_state.is_admin = False
    st.rerun()

# Global Context State Variables
now = datetime.now()
current_date_str = now.strftime("%Y-%m-%d")
current_time = now.time()

# Administrative Navigation Hub Routing
nav_options = ["Book Meals", "My Monthly Bill & History"]
if st.session_state.is_admin:
    nav_options.append("👑 Admin Management Console")

view_selection = st.sidebar.radio("Navigation Hub Menu", nav_options)

# --- PANEL 1: USER BOOKING ENGINE ---
if view_selection == "Book Meals":
    st.header("📅 Daily Meal Reservation Desk")
    st.write(f"**Current System Ledger Context Timestamp:** {now.strftime('%A, %d %B %Y - %I:%M %p')}")
    
    target_date = st.date_input("Select Date for Booking Selection Target", min_value=now.date())
    target_date_str = target_date.strftime("%Y-%m-%d")
    is_today = (target_date == now.date())
    
    # Calculate price rules for chosen targets
    lunch_price = get_meal_price("Lunch", target_date)
    dinner_price = get_meal_price("Dinner", target_date)
    
    # Look up existing records
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT meal_type FROM bookings WHERE username = ? AND booking_date = ?", 
                   (st.session_state.username, target_date_str))
    existing_bookings = [r['meal_type'] for r in cursor.fetchall()]
    conn.close()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader(f"☀️ Lunch Session (Price: ₹{lunch_price})")
        st.write("🕒 Daily Order Cutoff Lock: **9:30 AM**")
        
        if "Lunch" in existing_bookings:
            st.success("✅ Lunch Booked Successfully")
        else:
            # Time boundary validation enforcement logic
            if is_today and current_time > LUNCH_CUTOFF:
                st.error("❌ Cutoff Violation: System closed for Today's Lunch orders.")
            else:
                if st.button("Confirm Lunch Reservation Token", key="btn_lunch"):
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("INSERT INTO bookings (username, booking_date, meal_type, price, timestamp) VALUES (?, ?, ?, ?, ?)",
                              (st.session_state.username, target_date_str, "Lunch", lunch_price, now.strftime("%Y-%m-%d %H:%M:%S")))
                    conn.commit()
                    conn.close()
                    st.success("Reservation logged successfully.")
                    st.rerun()
                    
    with col2:
        st.subheader(f"🌙 Dinner Session (Price: ₹{dinner_price})")
        st.write("🕒 Daily Order Cutoff Lock: **5:30 PM**")
        
        if "Dinner" in existing_bookings:
            st.success("✅ Dinner Booked Successfully")
        else:
            if is_today and current_time > DINNER_CUTOFF:
                st.error("❌ Cutoff Violation: System closed for Today's Dinner orders.")
            else:
                if st.button("Confirm Dinner Reservation Token", key="btn_dinner"):
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("INSERT INTO bookings (username, booking_date, meal_type, price, timestamp) VALUES (?, ?, ?, ?, ?)",
                              (st.session_state.username, target_date_str, "Dinner", dinner_price, now.strftime("%Y-%m-%d %H:%M:%S")))
                    conn.commit()
                    conn.close()
                    st.success("Reservation logged successfully.")
                    st.rerun()

# --- PANEL 2: INDIVIDUAL BILLING RECORDS ---
elif view_selection == "My Monthly Bill & History":
    st.header("📊 Individual Statement & Reconciliation Desk")
    
    selected_year = st.selectbox("Select Target Year Frame", [2026, 2027], index=0)
    selected_month = st.selectbox("Select Target Billing Month Window", 
                                  ["January", "February", "March", "April", "May", "June", 
                                   "July", "August", "September", "October", "November", "December"])
