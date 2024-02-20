import streamlit as st
from src.utils import (
    app_store_reviews,
    generate_wordcloud,
    create_rating_distribution_plot,
    build_prompt,
    get_llm_summary,
)
import datetime
import pandas as pd

st.title("App Store Review Analysis")

app_store_url = st.text_input(
    "**Your App Store URL** 📱",
    placeholder="https://apps.apple.com/...",
)

st.markdown(
    "*For a demo, try this URL: https://apps.apple.com/de/app/slack/id618783545*"
)

today = datetime.datetime.now()
default_start_date = datetime.date(today.year - 1, 1, 1)


date_range = st.date_input(
    "Date range",
    value=(default_start_date, today),
    max_value=today,
    format="DD.MM.YYYY",
)

start_date = date_range[0].strftime("%Y-%m-%d")
if len(date_range) > 1:
    end_date = date_range[1].strftime("%Y-%m-%d")

api_key = st.text_input("Enter your OpenAI API key", type="password")


def get_reviews():
    reviews = app_store_reviews(
        url=app_store_url, start_date=start_date, end_date=end_date
    )
    return reviews


# Initialize session state for reviews if it doesn't exist
if "reviews" not in st.session_state:
    st.session_state.reviews = None

if st.button("Analyze reviews"):
    if start_date and end_date:
        if start_date < end_date:
            st.session_state.reviews = get_reviews()  # Store reviews in session state

    st.header("Reviews")
    st.dataframe(st.session_state.reviews)

    st.header("Most Common Words in Reviews")
    image = generate_wordcloud(st.session_state.reviews)
    st.image(image, caption="Word Cloud", use_column_width=True)
    st.header("Distribution of Ratings")
    fig = create_rating_distribution_plot(st.session_state.reviews)
    st.plotly_chart(fig)

    st.header("Summary of reviews")
    prompt = build_prompt(st.session_state.reviews)
    summary = get_llm_summary(prompt, api_key)
    st.markdown(summary)
