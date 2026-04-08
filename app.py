import streamlit as st
import pickle

# Load saved vectorizer and model
vectorizer = pickle.load(open('vectorizer.pkl', 'rb'))
model = pickle.load(open('model.pkl', 'rb'))

st.title("Fake News Detection System")

news = st.text_area("Enter news text here:")

if st.button("Predict"):
    news_vec = vectorizer.transform([news])
    prediction = model.predict(news_vec)[0]
    if prediction == 1:
        st.success("This news is REAL ✅")
    else:
        st.error("This news is FAKE ❌")
