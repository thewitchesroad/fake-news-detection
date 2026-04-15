import streamlit as st
import pickle
from datetime import datetime
import pandas as pd
from supabase import create_client, Client
from streamlit_cookies_manager import EncryptedCookieManager

# ---------------- SUPABASE ----------------
SUPABASE_URL = "https://dpvzvywjxsmsjcmbbgif.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRwdnp2eXdqeHNtc2pjbWJiZ2lmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYxOTQ0ODQsImV4cCI6MjA5MTc3MDQ4NH0.Av6pQ6t4vuJwQkAZ_SUSYATOaarIMYdF7o1BOc0jjgU"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------- COOKIE MANAGER ----------------
cookies = EncryptedCookieManager(
    prefix="my_app",
    password="super_secret_password"
)

if not cookies.ready():
    st.stop()

# ---------------- LOAD MODEL ----------------
model = pickle.load(open("model.pkl", "rb"))
vectorizer = pickle.load(open("vectorizer.pkl", "rb"))

# =========================================================
# 🔐 RESTORE SESSION FROM COOKIE
# =========================================================
def restore_session():
    token = cookies.get("access_token")

    if token:
        try:
            user = supabase.auth.get_user(token)

            if user and user.user:
                st.session_state.user = user.user
                st.session_state.logged_in = True
                return
        except:
            pass

    st.session_state.user = None
    st.session_state.logged_in = False


# =========================================================
# 🔐 LOGIN
# =========================================================
def login():
    st.title("Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        try:
            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if response.session:
                cookies["access_token"] = response.session.access_token
                cookies.save()

                st.success("Login successful")
                st.rerun()
            else:
                st.error("Invalid login")

        except Exception as e:
            st.error(f"Login error: {e}")


# =========================================================
# 📝 REGISTER (AUTH + USERS TABLE)
# =========================================================
def register():
    st.title("Register")

    username = st.text_input("Username")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Register"):
        try:
            # Step 1: Create auth user
            response = supabase.auth.sign_up({
                "email": email,
                "password": password
            })

            if response.user:
                user_id = response.user.id

                # Step 2: Insert into users table
                supabase.table("users").insert({
                    "user_id": user_id,
                    "username": username,
                    "email": email,
                    "role": "user"
                }).execute()

                st.success("Account created successfully!")

            else:
                st.error("Registration failed")

        except Exception as e:
            st.error(f"Error: {e}")


# =========================================================
# 🚪 LOGOUT
# =========================================================
def logout():
    if st.sidebar.button("Logout"):
        supabase.auth.sign_out()

        if "access_token" in cookies:
            del cookies["access_token"]
            cookies.save()

        st.session_state.user = None
        st.session_state.logged_in = False
        st.rerun()


# =========================================================
# 👤 GET USER PROFILE
# =========================================================
def get_user_profile():
    user_id = st.session_state.user.id

    response = supabase.table("users") \
        .select("*") \
        .eq("user_id", user_id) \
        .execute()

    if response.data:
        return response.data[0]
    return None


# =========================================================
# 🧠 PREDICT
# =========================================================
def predict_page():
    st.subheader("Fake News Detection")

    news = st.text_area("Enter News")
    language = st.selectbox("Language", ["English", "Bisaya"])

    if st.button("Predict"):
        if news:

            vec = vectorizer.transform([news])
            pred = model.predict(vec)[0]
            prob = model.predict_proba(vec)[0].max()

            result = "REAL" if pred == 1 else "FAKE"

            user_id = st.session_state.user.id

            news_response = supabase.table("news_input").insert({
                "user_id": user_id,
                "news_text": news,
                "language": language,
                "date_submitted": datetime.now().isoformat()
            }).execute()

            news_id = news_response.data[0]["news_id"]

            supabase.table("prediction_results").insert({
                "news_id": news_id,
                "prediction": result,
                "confidence_score": float(prob),
                "model_used": "Logistic Regression",
                "date_predicted": datetime.now().isoformat()
            }).execute()

            st.success(f"Result: {result}")
            st.info(f"Confidence: {prob:.2f}")


# =========================================================
# 📜 HISTORY
# =========================================================
def history_page():
    st.subheader("Prediction History")

    user_id = st.session_state.user.id

    response = supabase.table("prediction_results") \
        .select("prediction, confidence_score, date_predicted, news_input(news_text, user_id)") \
        .execute()

    filtered = []

    for row in response.data:
        if row.get("news_input") and row["news_input"]["user_id"] == user_id:
            filtered.append([
                row["news_input"]["news_text"],
                row["prediction"],
                row["confidence_score"],
                row["date_predicted"]
            ])

    if filtered:
        df = pd.DataFrame(filtered, columns=["News", "Result", "Confidence", "Date"])
        st.dataframe(df)
    else:
        st.info("No history yet.")


# =========================================================
# 📤 UPLOAD
# =========================================================
def upload_dataset():
    st.subheader("Upload Dataset")

    file = st.file_uploader("Upload CSV", type=["csv"])

    if file:
        df = pd.read_csv(file)
        st.dataframe(df.head())
        st.success("Dataset uploaded successfully!")


# =========================================================
# 🧠 MAIN APP
# =========================================================
def main_app():
    profile = get_user_profile()

    st.title("Fake News Detection System")

    if profile:
        st.write(f"Welcome, {profile['username']} 👋")

    menu = ["Predict", "History", "Upload Dataset"]

    # Admin check
    if profile and profile.get("role") == "admin":
        menu.append("Admin Dashboard")

    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Predict":
        predict_page()
    elif choice == "History":
        history_page()
    elif choice == "Upload Dataset":
        upload_dataset()
    elif choice == "Admin Dashboard":
        st.subheader("Admin Dashboard")
        users = supabase.table("users").select("*").execute().data
        st.dataframe(pd.DataFrame(users))

    logout()


# =========================================================
# 🔀 ROUTER
# =========================================================
def app_router():
    restore_session()

    if st.session_state.get("logged_in"):
        main_app()
    else:
        menu = st.sidebar.selectbox("Menu", ["Login", "Register"])

        if menu == "Login":
            login()
        else:
            register()


# ---------------- RUN ----------------
app_router()
