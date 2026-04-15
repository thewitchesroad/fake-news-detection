import streamlit as st
import pickle
from datetime import datetime
import pandas as pd
from supabase import create_client, Client

# ---------------- SUPABASE ----------------
SUPABASE_URL = "https://dpvzvywjxsmsjcmbbgif.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRwdnp2eXdqeHNtc2pjbWJiZ2lmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYxOTQ0ODQsImV4cCI6MjA5MTc3MDQ4NH0.Av6pQ6t4vuJwQkAZ_SUSYATOaarIMYdF7o1BOc0jjgU"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------- LOAD MODEL ----------------
model = pickle.load(open("model.pkl", "rb"))
vectorizer = pickle.load(open("vectorizer.pkl", "rb"))

# ---------------- SESSION PERSISTENCE (IMPORTANT FIX) ----------------
session = supabase.auth.get_user()

if "user" not in st.session_state:
    st.session_state.user = session.user if session else None

if "logged_in" not in st.session_state:
    st.session_state.logged_in = session.user is not None if session else False


# =========================================================
# 🔐 AUTH: LOGIN (SUPABASE AUTH)
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

            if response.user:
                st.session_state.user = response.user
                st.session_state.logged_in = True
                st.success("Login Successful")
                st.rerun()
            else:
                st.error("Invalid credentials")

        except Exception as e:
            st.error(f"Login error: {str(e)}")


# =========================================================
# 📝 REGISTER (SUPABASE AUTH)
# =========================================================
def register():
    st.title("Register")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Register"):
        try:
            response = supabase.auth.sign_up({
                "email": email,
                "password": password
            })

            if response.user:
                st.success("Account created! Check email for verification.")
            else:
                st.error("Registration failed")

        except Exception as e:
            st.error(f"Error: {str(e)}")


# =========================================================
# 🚪 LOGOUT (FIXED PROPERLY)
# =========================================================
def logout():
    if st.sidebar.button("Logout"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.session_state.logged_in = False
        st.rerun()


# =========================================================
# 🧠 PREDICT PAGE (UNCHANGED LOGIC, FIXED USER ID SOURCE)
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

            # Save news
            news_response = supabase.table("news_input").insert({
                "user_id": user_id,
                "news_text": news,
                "language": language,
                "date_submitted": datetime.now().isoformat()
            }).execute()

            news_id = news_response.data[0]["news_id"]

            # Save prediction
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
# 📜 HISTORY PAGE (FILTER BY AUTH USER)
# =========================================================
def history_page():
    st.subheader("Prediction History")

    user_id = st.session_state.user.id

    response = supabase.table("prediction_results") \
        .select("prediction, confidence_score, date_predicted, news_input(news_text, user_id)") \
        .execute()

    data = response.data
    filtered = []

    for row in data:
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
# 🧑‍💼 ADMIN DASHBOARD (UNCHANGED LOGIC)
# =========================================================
def admin_dashboard():
    st.subheader("Admin Dashboard")

    users = supabase.table("users").select("username,email,role").execute().data
    st.write("### Users")
    st.dataframe(pd.DataFrame(users))

    models = supabase.table("models").select("model_name,algorithm,accuracy").execute().data
    st.write("### Models")
    st.dataframe(pd.DataFrame(models))


# =========================================================
# 📤 UPLOAD DATASET
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
    st.title("Fake News Detection System")

    menu = ["Predict", "History", "Upload Dataset"]

    if st.session_state.user and hasattr(st.session_state.user, "email"):
        pass

    # Optional role check (kept safe)
    if supabase.table("users").select("*").eq("email", st.session_state.user.email).execute().data:
        user_data = supabase.table("users").select("*").eq("email", st.session_state.user.email).execute().data[0]
        if user_data.get("role") == "admin":
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
# 🔀 ROUTER (FIXED PERSISTENT LOGIN)
# =========================================================
def app_router():
    if st.session_state.logged_in:
        main_app()
    else:
        menu = st.sidebar.selectbox("Menu", ["Login", "Register"])

        if menu == "Login":
            login()
        else:
            register()


# ---------------- RUN ----------------
app_router()
