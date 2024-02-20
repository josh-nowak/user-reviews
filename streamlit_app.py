import streamlit as st
from src.utils import app_store_reviews
from datetime import datetime

st.header("App Store Review Analysis")

app_store_url = st.text_input(
    "**Your App Store URL** 📱",
    placeholder="https://apps.apple.com/...",
)

st.markdown(
    "*For a demo, try this URL: https://apps.apple.com/de/app/slack/id618783545*"
)

n_last_reviews = st.number_input("Number of most recent reviews to analyze", value=1000)
after_date = st.date_input(
    "Only reviews after this date",
    format="DD.MM.YYYY",
    value=datetime.strptime("2024-01-01", "%Y-%m-%d"),
)


if st.button("Get reviews"):

    st.markdown("*For now, this app only shows the reviews without any analysis.*")

    def get_reviews():
        return app_store_reviews(
            url=app_store_url, n_last_reviews=n_last_reviews, after=after_date
        )

    reviews = get_reviews()

    st.dataframe(reviews)
