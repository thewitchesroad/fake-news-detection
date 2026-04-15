import streamlit as st
from supabase import create_client, Client
import pickle
from datetime import datetime

# Load ML
model = pickle.load(open("model.pkl", "rb"))
vectorizer = pickle.load(open("vectorizer.pkl", "rb"))

# DB connection
SUPABASE_URL = "https://dpvzvywjxsmsjcmbbgif.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRwdnp2eXdqeHNtc2pjbWJiZ2lmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYxOTQ0ODQsImV4cCI6MjA5MTc3MDQ4NH0.Av6pQ6t4vuJwQkAZ_SUSYATOaarIMYdF7o1BOc0jjgU"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Session
if "user" not in st.session_state:
    st.session_state.user = None

# ---------------- LOGIN PAGE ----------------
def login():
    st.title("Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        response = supabase.table("users") \
            .select("*") \
            .eq("username", username) \
            .eq("password", password) \
            .execute()
        
        user = response.data[0] if response.data else None

        if user:
            st.session_state.user = user
            st.success("Login Successful")
            st.rerun()  # 🔥 THIS IS THE FIX
        else:
            st.error("Invalid credentials")

# ---------------- REGISTER ----------------
def register():
    st.title("Register")

    username = st.text_input("New Username")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Register"):
        supabase.table("users").insert({
            "username": username,
            "email": email,
            "password": password,
            "role": "user"
        }).execute()
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
            news_response = supabase.table("news_input").insert({
                "user_id": st.session_state.user["user_id"],
                "news_text": news,
                "language": language,
                "date_submitted": datetime.now().isoformat()
            }).execute()
            
            news_id = news_response.data[0]["news_id"]

            # Save result
            supabase.table("prediction_results").insert({
                "news_id": news_id,
                "prediction": result,
                "confidence_score": float(prob),
                "model_used": "Logistic Regression",
                "date_predicted": datetime.now().isoformat()
            }).execute()

            st.success(f"Result: {result}")
            st.info(f"Confidence: {prob:.2f}")

    # TRY AGAIN
    if st.button("Try Again"):
        st.rerun()

    # LOGOUT
    if st.sidebar.button("Logout"):
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
