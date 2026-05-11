import streamlit as st
import pickle
from datetime import datetime
import pandas as pd

from supabase import create_client
from streamlit_cookies_manager import EncryptedCookieManager

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Fake News Detection System",
    page_icon="🔎",
    layout="wide"
)

# =========================================================
# SUPABASE CONNECTION
# =========================================================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================================================
# SESSION STATE
# =========================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user" not in st.session_state:
    st.session_state.user = None

# =========================================================
# COOKIE MANAGER
# =========================================================
cookies = EncryptedCookieManager(
    prefix="fake_news_app",
    password="super_secret_password"
)

if not cookies.ready():
    st.stop()

# =========================================================
# LOAD MODEL + VECTORIZER
# =========================================================
model = pickle.load(open("model.pkl", "rb"))
vectorizer = pickle.load(open("vectorizer.pkl", "rb"))

# =========================================================
# RESTORE SESSION
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
# GET USER PROFILE
# =========================================================
def get_user_profile():

    if not st.session_state.user:
        return None

    user_id = st.session_state.user.id

    response = supabase.table("users") \
        .select("*") \
        .eq("user_id", user_id) \
        .execute()

    if response.data:
        return response.data[0]

    return None


# =========================================================
# LOGIN
# =========================================================
def login():

    st.title("🔐 Login")

    email = st.text_input("Email").strip()
    password = st.text_input("Password", type="password").strip()

    if st.button("Login"):

        if not email or not password:
            st.warning("Please enter email and password.")
            return

        try:

            with st.spinner("Logging in..."):

                response = supabase.auth.sign_in_with_password({
                    "email": email,
                    "password": password
                })

            if response.session:

                cookies["access_token"] = response.session.access_token
                cookies.save()

                st.session_state.user = response.user
                st.session_state.logged_in = True

                st.success("Login successful!")
                st.rerun()

        except Exception as e:

            error_msg = str(e).lower()

            if "invalid" in error_msg or "credentials" in error_msg:
                st.error("Invalid email or password.")

            elif "network" in error_msg or "connect" in error_msg:
                st.error("Server is waking up. Try again in a few seconds.")

            else:
                st.error("Login failed.")


# =========================================================
# REGISTER
# =========================================================
def register():

    st.title("📝 Register")

    username = st.text_input("Username").strip()
    email = st.text_input("Email").strip()
    password = st.text_input("Password", type="password").strip()

    if st.button("Register"):

        if not username or not email or not password:
            st.warning("Please fill all fields.")
            return

        if len(password) < 6:
            st.error("Password must be at least 6 characters.")
            return

        try:

            response = supabase.auth.sign_up({
                "email": email,
                "password": password
            })

            if response.user:

                user_id = response.user.id

                supabase.table("users").insert({
                    "user_id": user_id,
                    "username": username,
                    "email": email,
                    "role": "user"
                }).execute()

                st.success("Account created successfully!")

            else:
                st.error("Registration failed.")

        except:
            st.error("Registration failed. Email may already exist.")


# =========================================================
# LOGOUT
# =========================================================
def logout():

    if st.sidebar.button("Logout"):

        supabase.auth.sign_out()

        cookies["access_token"] = ""
        cookies.save()

        st.session_state.user = None
        st.session_state.logged_in = False

        st.rerun()


# =========================================================
# PREDICTION PAGE
# =========================================================
def predict_page():

    st.subheader("🧠 Fake News Prediction")

    news = st.text_area("Enter News Text")
    language = st.selectbox("Language", ["English", "Bisaya"])

    if st.button("Predict"):

        if not news.strip():
            st.warning("Please enter news text.")
            return

        # =====================================
        # VECTORIZE
        # =====================================
        vec = vectorizer.transform([news])

        # =====================================
        # PREDICT
        # =====================================
        pred = model.predict(vec)[0]

        prob = model.predict_proba(vec)[0].max()

        result = "REAL" if pred == 1 else "FAKE"

        # =====================================
        # SAVE TO SUPABASE
        # =====================================
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
            "model_used": "Machine Learning",
            "date_predicted": datetime.now().isoformat()
        }).execute()

        # =====================================
        # DISPLAY RESULT
        # =====================================
        if result == "REAL":
            st.success(f"Prediction: {result}")
        else:
            st.error(f"Prediction: {result}")

        st.info(f"Confidence Score: {prob:.2f}")


# =========================================================
# HISTORY PAGE
# =========================================================
def history_page():

    st.subheader("📜 Prediction History")

    user_id = st.session_state.user.id

    response = supabase.table("prediction_results") \
        .select("""
            prediction,
            confidence_score,
            date_predicted,
            news_input(news_text, user_id)
        """) \
        .execute()

    filtered = []

    for row in response.data:

        if row.get("news_input"):

            if row["news_input"]["user_id"] == user_id:

                filtered.append([
                    row["news_input"]["news_text"],
                    row["prediction"],
                    row["confidence_score"],
                    row["date_predicted"]
                ])

    if filtered:

        df = pd.DataFrame(
            filtered,
            columns=["News", "Result", "Confidence", "Date"]
        )

        st.dataframe(df, use_container_width=True)

    else:
        st.info("No history yet.")


# =========================================================
# DATASET UPLOAD
# =========================================================
def upload_dataset():

    st.subheader("📤 Dataset Upload")

    profile = get_user_profile()

    if not profile:
        st.error("Profile not found.")
        return

    if profile["role"] != "admin":
        st.error("Access denied. Admin only.")
        return

    file = st.file_uploader(
        "Upload CSV File",
        type=["csv"]
    )

    if file:

        try:

            df = pd.read_csv(file)

            df.columns = df.columns.str.strip()

            st.write("### Dataset Preview")
            st.dataframe(df.head())

            st.success("Dataset uploaded successfully!")

        except:
            st.error("Invalid CSV file.")


# =========================================================
# ADMIN DASHBOARD
# =========================================================
def admin_dashboard():

    st.subheader("🛡️ Admin Dashboard")

    profile = get_user_profile()

    if not profile:
        st.error("Profile not found.")
        return

    if profile["role"] != "admin":
        st.error("Access denied.")
        return

    # =====================================
    # USERS
    # =====================================
    st.write("## Users")

    users = supabase.table("users") \
        .select("*") \
        .execute() \
        .data

    st.dataframe(pd.DataFrame(users), use_container_width=True)

    # =====================================
    # NEWS INPUT
    # =====================================
    st.write("## News Inputs")

    news = supabase.table("news_input") \
        .select("*") \
        .execute() \
        .data

    st.dataframe(pd.DataFrame(news), use_container_width=True)

    # =====================================
    # PREDICTIONS
    # =====================================
    st.write("## Prediction Results")

    preds = supabase.table("prediction_results") \
        .select("*") \
        .execute() \
        .data

    st.dataframe(pd.DataFrame(preds), use_container_width=True)

    # =====================================
    # MODELS
    # =====================================
    st.write("## Models")

    models = supabase.table("models") \
        .select("*") \
        .execute() \
        .data

    st.dataframe(pd.DataFrame(models), use_container_width=True)


# =========================================================
# MAIN APP
# =========================================================
def main_app():

    st.title("🔎Localized Fake News Detection System in Barobo, Surigao Del sur")

    profile = get_user_profile()

    if profile:
        st.sidebar.success(f"Logged in as: {profile['username']}")

    menu = [
        "Predict",
        "History",
        "Upload Dataset"
    ]

    if profile and profile["role"] == "admin":
        menu.append("Admin Dashboard")

    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Predict":
        predict_page()

    elif choice == "History":
        history_page()

    elif choice == "Upload Dataset":
        upload_dataset()

    elif choice == "Admin Dashboard":
        admin_dashboard()

    logout()


# =========================================================
# ROUTER
# =========================================================
def app_router():

    restore_session()

    if st.session_state.logged_in:

        main_app()

    else:

        menu = st.sidebar.selectbox(
            "Menu",
            ["Login", "Register"]
        )

        if menu == "Login":
            login()

        else:
            register()


# =========================================================
# RUN APP
# =========================================================
app_router()
