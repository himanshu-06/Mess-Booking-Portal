import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, time

# Database initialization
def init_db():
    conn = sqlite3.connect("mess_booking.db", check_same_thread=False)
    cursor = conn.cursor()
    
    # Create Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    ''')
    
    # Create Bookings Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            date TEXT,
            meal_type TEXT,
            price REAL,
            UNIQUE(username, date, meal_type)
        )
    ''')
    
    # Insert default users if table is empty
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO users VALUES (?, ?)", [
            ("rahul", "password123"),
            ("amit", "mess456")
        ])
    
    conn.commit()
    return conn

conn = init_db()

# Weekly Pricing Rules (0 = Monday, 6 = Sunday)
WEEKLY_PRICES = {
    "Lunch": {0: 60, 1: 60, 2: 60, 3: 60, 4: 60, 5: 70, 6: 80},
    "Dinner": {0: 70, 1: 70, 2: 70, 3: 70, 4: 70, 5: 80, 6: 90}
}

# Cutoff times
CUTOFFS = {
    "Lunch": time(9, 30),
    "Dinner": time(17, 30)
}

st.set_page_config(page_title="Mess Booking Portal", page_icon="🍲", layout="centered")

# Authentication State
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

if not st.session_state.logged_in:
    st.title("🍲 Mess Booking Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login", use_container_width=True):
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        if user:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.rerun()
        else:
            st.error("Invalid Username or Password")
else:
    # Top navbar
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title(f"Welcome, {st.session_state.username.capitalize()} 👋")
    with col2:
        if st.button("Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.rerun()
            
    menu = st.sidebar.radio("Navigation", ["Book Meals", "Monthly Invoices"])
    
    if menu == "Book Meals":
        st.subheader("📅 Reserve Your Meal")
        
        selected_date = st.date_input("Select Date", min_value=datetime.today().date())
        meal_type = st.selectbox("Select Meal", ["Lunch", "Dinner"])
        
        # Calculate price based on weekday
        weekday = selected_date.weekday()
        price = WEEKLY_PRICES[meal_type][weekday]
        
        st.info(f"Price for {meal_type} on this day: ₹{price}")
        
        if st.button("Confirm Booking", use_container_width=True):
            current_dt = datetime.now()
            current_date = current_dt.date()
            current_time = current_dt.time()
            
            # Check Time Limits if booking for today
            if selected_date == current_date and current_time > CUTOFFS[meal_type]:
                st.error(f"Booking Closed! The deadline for {meal_type} is {CUTOFFS[meal_type].strftime('%I:%M %p')}.")
            else:
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO bookings (username, date, meal_type, price) VALUES (?, ?, ?, ?)",
                        (st.session_state.username, str(selected_date), meal_type, price)
                    )
                    conn.commit()
                    st.success(f"Successfully booked {meal_type} for {selected_date}!")
                except sqlite3.IntegrityError:
                    st.warning(f"You have already booked {meal_type} for {selected_date}.")

    elif menu == "Monthly Invoices":
        st.subheader("📊 Your Billing Overview")
        
        # Filter monthly logic
        cursor = conn.cursor()
        cursor.execute("SELECT date, meal_type, price FROM bookings WHERE username = ?", (st.session_state.username,))
        rows = cursor.fetchall()
        
        if rows:
            df = pd.DataFrame(rows, columns=["Date", "Meal Type", "Cost (₹)"])
            df["Date"] = pd.to_datetime(df["Date"])
            df["Month-Year"] = df["Date"].dt.strftime("%B %Y")
            
            distinct_months = df["Month-Year"].unique()
            selected_month = st.selectbox("Select Month", distinct_months)
            
            # Filter details
            filtered_df = df[df["Month-Year"] == selected_month].copy()
            filtered_df["Date"] = filtered_df["Date"].dt.strftime("%Y-%m-%d")
            
            st.dataframe(filtered_df[["Date", "Meal Type", "Cost (₹)"]], use_container_width=True, hide_index=True)
            
            total_bill = filtered_df["Cost (₹)"].sum()
            st.metric(label=f"Total Bill for {selected_month}", value=f"₹{total_bill:,.2f}")
        else:
            st.info("No booking records found yet.")
