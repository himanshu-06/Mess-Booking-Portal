import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime, time

# --- PRICING LOGIC ---
WEEKLY_PRICES = {
    "Lunch": {0: 60, 1: 60, 2: 60, 3: 60, 4: 60, 5: 70, 6: 80},
    "Dinner": {0: 70, 1: 70, 2: 70, 3: 70, 4: 70, 5: 80, 6: 90}
}

def get_meal_price(meal_type, date_obj):
    day_of_week = date_obj.weekday()
    return WEEKLY_PRICES[meal_type].get(day_of_week, 60.0)

# --- TIME BOUNDARY CUTOFF RULES ---
LUNCH_CUTOFF = time(9, 30)
DINNER_CUTOFF = time(17, 30)

# --- IN-MEMORY/PERSISTENT USER AND BOOKING MATRIX ---
if "user_db" not in st.session_state:
    st.session_state.user_db = {"rahul": hashlib.sha256("password123".encode()).hexdigest(), "amit": hashlib.sha256("mess456".encode()).hexdigest()}

if "bookings_list" not in st.session_state:
    st.session_state.bookings_list = []

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_user(username, password):
    if username == "admin" and password == "adminpassword":
        return {"authenticated": True, "is_admin": True}
    
    stored_hash = st.session_state.user_db.get(username)
    if stored_hash and stored_hash == hash_password(password):
        return {"authenticated": True, "is_admin": False}
    return {"authenticated": False, "is_admin": False}

def register_user(username, password):
    if username in st.session_state.user_db or username == "admin":
        return False
    st.session_state.user_db[username] = hash_password(password)
    return True

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
                    st.error("Registration failed. Account username already exists.")
    st.stop()

# --- MAIN SYSTEM INTERFACE (AUTHENTICATED) ---
st.sidebar.markdown(f"### 👤 Active User: **{st.session_state.username}**")
if st.session_state.is_admin:
    st.sidebar.info("👑 Administrator Account Context Active")

if st.sidebar.button("Log Out System"):
    st.session_state.authenticated = False
    st.session_state.username = ""
    st.session_state.is_admin = False
    st.rerun()

now = datetime.now()
current_time = now.time()

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
    
    lunch_price = get_meal_price("Lunch", target_date)
    dinner_price = get_meal_price("Dinner", target_date)
    
    existing_bookings = [b['meal_type'] for b in st.session_state.bookings_list if b['username'] == st.session_state.username and b['booking_date'] == target_date_str]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader(f"☀️ Lunch Session (Price: ₹{lunch_price})")
        st.write("🕒 Daily Order Cutoff Lock: **9:30 AM**")
        
        if "Lunch" in existing_bookings:
            st.success("✅ Lunch Booked Successfully")
        else:
            if is_today and current_time > LUNCH_CUTOFF:
                st.error("❌ Cutoff Violation: System closed for Today's Lunch orders.")
            else:
                if st.button("Confirm Lunch Reservation Token", key="btn_lunch"):
                    st.session_state.bookings_list.append({
                        "username": st.session_state.username,
                        "booking_date": target_date_str,
                        "meal_type": "Lunch",
                        "price": lunch_price,
                        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S")
                    })
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
                    st.session_state.bookings_list.append({
                        "username": st.session_state.username,
                        "booking_date": target_date_str,
                        "meal_type": "Dinner",
                        "price": dinner_price,
                        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S")
                    })
                    st.success("Reservation logged successfully.")
                    st.rerun()

# --- PANEL 2: INDIVIDUAL BILLING RECORDS ---
elif view_selection == "My Monthly Bill & History":
    st.header("📊 Individual Statement & Reconciliation Desk")
    
    selected_year = st.selectbox("Select Target Year Frame", ["2026", "2027"], index=0)
    selected_month = st.selectbox("Select Target Billing Month Window", 
                                  ["January", "February", "March", "April", "May", "June", 
                                   "July", "August", "September", "October", "November", "December"],
                                  index=now.month - 1)
    
    month_num_str = f"{['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'].index(selected_month) + 1:02d}"
    filter_prefix = f"{selected_year}-{month_num_str}"
    
    user_records = [b for b in st.session_state.bookings_list if b['username'] == st.session_state.username and b['booking_date'].startswith(filter_prefix)]
    
    if not user_records:
        st.info(f"No reservation transaction records found matching user frame filter: {selected_month} {selected_year}")
    else:
        df = pd.DataFrame(user_records)
        df_display = df[['booking_date', 'meal_type', 'price', 'timestamp']].copy()
        df_display.columns = ['Reservation Date', 'Meal Type', 'Rate Charged (₹)', 'Transaction Time Log']
        
        total_accrued = df_display['Rate Charged (₹)'].sum()
        st.metric(label=f"Total Amount Due Summary ({selected_month} {selected_year})", value=f"₹ {total_accrued:,.2f}")
        st.subheader("Itemized Transaction Statement History Logs")
        st.dataframe(df_display, use_container_width=True)

# --- PANEL 3: ADMINISTRATIVE PRIVILEGED DASHBOARD ---
elif view_selection == "👑 Admin Management Console" and st.session_state.is_admin:
    st.header("👑 Centralized System Administrative Command Panel")
    
    admin_year = st.selectbox("Select Operational Scope Year", ["2026", "2027"], index=0, key="admin_yr")
    admin_month = st.selectbox("Select Operational Scope Month", 
                               ["January", "February", "March", "April", "May", "June", 
                                "July", "August", "September", "October", "November", "December"],
                               index=now.month - 1, key="admin_mnth")
    
    a_month_num_str = f"{['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'].index(admin_month) + 1:02d}"
    admin_filter_prefix = f"{admin_year}-{a_month_num_str}"
    
    admin_records = [b for b in st.session_state.bookings_list if b['booking_date'].startswith(admin_filter_prefix)]
    
    tab1, tab2 = st.tabs(["💰 User Invoicing Balance Sheets", "🔍 Detailed System Audit Trail Logs"])
    
    if not admin_records:
        with tab1: st.info("No active operations invoices found inside the selected billing month.")
