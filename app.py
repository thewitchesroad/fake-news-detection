import streamlit as st
import sqlite3
import pickle
from datetime import datetime

# Load ML
model = pickle.load(open("model.pkl", "rb"))
vectorizer = pickle.load(open("vectorizer.pkl", "rb"))

# DB connection
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

# Session
if "user" not in st.session_state:
    st.session_state.user = None

# ---------------- LOGIN PAGE ----------------
def login():
    st.title("Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()

        if user:
            st.session_state.user = user
            st.success("Login Successful")
        else:
            st.error("Invalid credentials")

# ---------------- REGISTER ----------------
def register():
    st.title("Register")

    username = st.text_input("New Username")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Register"):
        cursor.execute("INSERT INTO users (username,email,password,role) VALUES (?,?,?,?)",
                       (username, email, password, "user"))
        conn.commit()
        st.success("Account created!")

# ---------------- MAIN APP ----------------
def main_app():
    st.title("Fake News Detection System")

    news = st.text_area("Enter News Text")
    language = st.selectbox("Language", ["English", "Bisaya"])

    if st.button("Predict"):
        if news:
            vec = vectorizer.transform([news])
            pred = model.predict(vec)[0]
            prob = model.predict_proba(vec)[0].max()

            result = "REAL" if pred == 1 else "FAKE"

            # Save input
            cursor.execute(
                "INSERT INTO news_input (user_id, news_text, language, date_submitted) VALUES (?,?,?,?)",
                (st.session_state.user[0], news, language, datetime.now())
            )
            news_id = cursor.lastrowid

            # Save result
            cursor.execute(
                "INSERT INTO prediction_results (news_id, prediction, confidence_score, model_used, date_predicted) VALUES (?,?,?,?,?)",
                (news_id, result, prob, "Logistic Regression", datetime.now())
            )
            conn.commit()

            st.success(f"Result: {result}")
            st.info(f"Confidence: {prob:.2f}")

    # TRY AGAIN
    if st.button("Try Again"):
        st.rerun()

    # LOGOUT
    if st.button("Logout"):
        st.session_state.user = None
        st.rerun()

# ---------------- ROUTER ----------------
menu = ["Login", "Register"]

if st.session_state.user is None:
    choice = st.sidebar.selectbox("Menu", menu)
    if choice == "Login":
        login()
    else:
        register()
else:
    main_app()