import streamlit as st
import pandas as pd
import hashlib
from datetime import datetime, time
import zoneinfo

# --- TIMEZONE CONFIGURATION ---
try:
    IST = zoneinfo.ZoneInfo("Asia/Kolkata")
except Exception:
    IST = zoneinfo.ZoneInfo("UTC")

# --- PRICING LOGIC (Veg & Non-Veg for Wed, Fri, Sun) ---
# Weekday indexing: 0:Mon, 1:Tue, 2:Wed, 3:Thu, 4:Fri, 5:Sat, 6:Sun
WEEKLY_PRICES = {
    "Lunch": {
        0: {"Veg": 90},
        1: {"Veg": 80},
        2: {"Veg": 100, "Non-Veg": 100},   # Wednesday
        3: {"Veg": 80},
        4: {"Veg": 100, "Non-Veg": 100},   # Friday
        5: {"Veg": 90},
        6: {"Veg": 110, "Non-Veg": 150}   # Sunday
    },
    "Dinner": {
        0: {"Veg": 90},
        1: {"Veg": 80},
        2: {"Veg": 110, "Non-Veg": 140},  # Wednesday
        3: {"Veg": 70},
        4: {"Veg": 70, "Non-Veg": 90},  # Friday
        5: {"Veg": 80},
        6: {"Veg": 90, "Non-Veg": 90}   # Sunday
    }
}

def get_meal_price(meal_type, date_obj, preference="Veg"):
    day_of_week = date_obj.weekday()
    day_prices = WEEKLY_PRICES[meal_type].get(day_of_week, {"Veg": 60.0})
    if isinstance(day_prices, dict):
        return day_prices.get(preference, day_prices.get("Veg", 60.0))
    return day_prices

# --- TIME BOUNDARY CUTOFF RULES ---
LUNCH_CUTOFF = time(9, 30)
DINNER_CUTOFF = time(17, 30)

# --- IN-MEMORY USER AND BOOKING SYSTEM ---
if "user_db" not in st.session_state:
    st.session_state.user_db = {
        "rahul": hashlib.sha256("password123".encode()).hexdigest(), 
        "amit": hashlib.sha256("mess456".encode()).hexdigest()
    }

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

# --- UI INTERFACE CONFIGURATION ---
st.set_page_config(page_title="GET Hostel Mess Booking ", page_icon="🍲", layout="wide")
st.title("🍲 GET Hostel Mess Booking")

# --- AUTHENTICATION CONTROLLER ---
if not st.session_state.authenticated:
    auth_mode = st.radio("Choose Mode", ["Log In", "Sign Up / Register User"], horizontal=True)
    
    with st.form("auth_form"):
        username_input = st.text_input("Username").strip().lower()
        password_input = st.text_input("Password", type="password")
        submit_btn = st.form_submit_button("Submit Action")
        
        if submit_btn:
            if not username_input or not password_input:
                st.error("Please fill in all credentials.")
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
                    st.error("System namespace 'admin' is locked.")
                elif register_user(username_input, password_input):
                    st.success("Registration successful! You may now switch to Log In mode.")
                else:
                    st.error("Registration failed. Username already exists.")
    st.stop()

# --- MAIN INTERFACE (AUTHENTICATED) ---
st.sidebar.markdown(f"### 👤 Active User: **{st.session_state.username}**")
if st.session_state.is_admin:
    st.sidebar.info("👑 Administrator Context Active")

if st.sidebar.button("Log Out System"):
    st.session_state.authenticated = False
    st.session_state.username = ""
    st.session_state.is_admin = False
    st.rerun()

now = datetime.now(IST)
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
    day_of_week = target_date.weekday()
    
    # Wednesday (2), Friday (4), Sunday (6) have Veg/Non-Veg options
    has_options = day_of_week in [2, 4, 6]
    day_name = target_date.strftime("%A")
    
    if has_options:
        st.info(f"✨ **{day_name} Special Menu Available:** Choose between Veg and Non-Veg preferences.")

    existing_bookings = {b['meal_type']: b for b in st.session_state.bookings_list if b['username'] == st.session_state.username and b['booking_date'] == target_date_str}
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("☀️ Lunch Session")
        
        lunch_pref = "Veg"
        if has_options:
            lunch_pref = st.radio(f"Lunch Option for {day_name}", ["Veg", "Non-Veg"], key=f"lunch_pref_{target_date_str}")
        
        lunch_price = get_meal_price("Lunch", target_date, lunch_pref)
        st.write(f"**Selected Preference:** {lunch_pref} | **Price:** ₹{lunch_price}")
        st.write("🕒 Daily Order Cutoff Lock: **9:30 AM**")
        
        if "Lunch" in existing_bookings:
            b_info = existing_bookings["Lunch"]
            st.success(f"✅ Lunch Booked ({b_info.get('preference', 'Veg')} - ₹{b_info['price']})")
            
            if is_today and current_time > LUNCH_CUTOFF:
                st.warning("🔒 Cancellation closed. Today's 9:30 AM cutoff has passed.")
            else:
                if st.button("Cancel Lunch Booking", key="cancel_lunch"):
                    st.session_state.bookings_list = [b for b in st.session_state.bookings_list if not (b['username'] == st.session_state.username and b['booking_date'] == target_date_str and b['meal_type'] == 'Lunch')]
                    st.success("Lunch booking cancelled successfully.")
                    st.rerun()
        else:
            if is_today and current_time > LUNCH_CUTOFF:
                st.error("❌ Cutoff Violation: System closed for Today's Lunch orders.")
            else:
                if st.button("Confirm Lunch Reservation Token", key="btn_lunch"):
                    st.session_state.bookings_list.append({
                        "username": st.session_state.username,
                        "booking_date": target_date_str,
                        "meal_type": "Lunch",
                        "preference": lunch_pref,
                        "price": lunch_price,
                        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S")
                    })
                    st.success("Reservation logged successfully.")
                    st.rerun()
                    
    with col2:
        st.subheader("🌙 Dinner Session")
        
        dinner_pref = "Veg"
        if has_options:
            dinner_pref = st.radio(f"Dinner Option for {day_name}", ["Veg", "Non-Veg"], key=f"dinner_pref_{target_date_str}")
        
        dinner_price = get_meal_price("Dinner", target_date, dinner_pref)
        st.write(f"**Selected Preference:** {dinner_pref} | **Price:** ₹{dinner_price}")
        st.write("🕒 Daily Order Cutoff Lock: **5:30 PM**")
        
        if "Dinner" in existing_bookings:
            b_info = existing_bookings["Dinner"]
            st.success(f"✅ Dinner Booked ({b_info.get('preference', 'Veg')} - ₹{b_info['price']})")
            
            if is_today and current_time > DINNER_CUTOFF:
                st.warning("🔒 Cancellation closed. Today's 5:30 PM cutoff has passed.")
            else:
                if st.button("Cancel Dinner Booking", key="cancel_dinner"):
                    st.session_state.bookings_list = [b for b in st.session_state.bookings_list if not (b['username'] == st.session_state.username and b['booking_date'] == target_date_str and b['meal_type'] == 'Dinner')]
                    st.success("Dinner booking cancelled successfully.")
                    st.rerun()
        else:
            if is_today and current_time > DINNER_CUTOFF:
                st.error("❌ Cutoff Violation: System closed for Today's Dinner orders.")
            else:
                if st.button("Confirm Dinner Reservation Token", key="btn_dinner"):
                    st.session_state.bookings_list.append({
                        "username": st.session_state.username,
                        "booking_date": target_date_str,
                        "meal_type": "Dinner",
                        "preference": dinner_pref,
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
    
    months_list = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    month_num_str = f"{months_list.index(selected_month) + 1:02d}"
    filter_prefix = f"{selected_year}-{month_num_str}"
    
    user_records = [b for b in st.session_state.bookings_list if b['username'] == st.session_state.username and b['booking_date'].startswith(filter_prefix)]
    
    if not user_records:
        st.info(f"No reservation transaction records found matching: {selected_month} {selected_year}")
    else:
        df = pd.DataFrame(user_records)
        if 'preference' not in df.columns:
            df['preference'] = 'Veg'
        df_display = df[['booking_date', 'meal_type', 'preference', 'price', 'timestamp']].copy()
        df_display.columns = ['Reservation Date', 'Meal Type', 'Preference', 'Rate Charged (₹)', 'Transaction Time Log']
        
        total_accrued = df_display['Rate Charged (₹)'].sum()
        st.metric(label=f"Total Amount Due Summary ({selected_month} {selected_year})", value=f"₹ {total_accrued:,.2f}")
        st.subheader("Itemized Transaction Statement History Logs")
        st.dataframe(df_display, use_container_width=True)

# --- PANEL 3: ADMIN MANAGEMENT CONSOLE ---
elif view_selection == "👑 Admin Management Console" and st.session_state.is_admin:
    st.header("👑 Admin Management & Master Ledger Console")
    st.write("Overview of all institutional mess bookings and user billing records.")
    
    if not st.session_state.bookings_list:
        st.info("No bookings recorded in the system yet.")
    else:
        df_all = pd.DataFrame(st.session_state.bookings_list)
        if 'preference' not in df_all.columns:
            df_all['preference'] = 'Veg'
            
        st.subheader("All User Reservations")
        st.dataframe(df_all[['username', 'booking_date', 'meal_type', 'preference', 'price', 'timestamp']], use_container_width=True)
        
        st.subheader("User-wise Total Billing Summary")
        summary_df = df_all.groupby('username')['price'].sum().reset_index()
        summary_df.columns = ['Username', 'Total Due (₹)']
        st.dataframe(summary_df, use_container_width=True)
