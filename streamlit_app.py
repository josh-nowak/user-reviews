import streamlit as st
from src.utils import (
    app_store_reviews,
    generate_wordcloud,
    create_rating_distribution_plot,
    build_prompt,
    get_llm_summary,
    app_data_from_url,
)
import datetime
import pandas as pd
import time

st.title("App Store Review Analysis")

app_store_url = st.text_input(
    "**Your App Store URL** 📱",
    placeholder="https://apps.apple.com/...",
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

# Initialize session state for the "analyze" button to retain analysis
if "clicked" not in st.session_state:
    st.session_state.clicked = False


def click_button():
    if st.session_state.clicked:
        pass
    st.session_state.clicked = True


st.button("Analyze reviews", type="primary", on_click=click_button)

if st.session_state.clicked:
    with st.spinner("Loading reviews..."):
        if start_date and end_date:
            if start_date < end_date:
                # Store reviews in session state
                st.session_state.reviews = get_reviews()

    # Show a success message
    n_reviews_found = len(st.session_state.reviews)
    st.toast(f"🎉 Reviews successfully loaded!")

    # Generate an introductory text for the analysis
    country, app_name, app_id = app_data_from_url(app_store_url)
    p_positive_reviews = len(
        st.session_state.reviews[st.session_state.reviews["rating"] > 3]
    ) / len(st.session_state.reviews)
    intro_text = f'The App **"{app_name.capitalize()}"** received **{n_reviews_found} App Store reviews** in the \
        selected time frame. About **{round(p_positive_reviews*100)}% of these \
            reviews were positive**, with a rating 4 or 5 stars.'

    # Give the introductory text a streaming (ChatGPT-like) effect
    def stream_intro():
        for word in intro_text.split():
            yield word + " "
            time.sleep(0.02)

    st.write_stream(stream_intro)

    # Generate "highlights" section
    st.subheader("🤩 Highlights")
    prompt = build_prompt(
        st.session_state.reviews[st.session_state.reviews["rating"] > 3].sample(frac=1)
    )
    prompt += "\n\nFor this analysis, only the positive reviews have been selected. \
        Please summarize the positive highlights in the user feedback."
    with st.spinner("Summarizing positive reviews..."):
        positive_summary = get_llm_summary(prompt, api_key)

    st.write("The following points were highlighted by satisfied users:")
    st.write(positive_summary)
    # def stream_positive_summary():
    #     for word in positive_summary.split():
    #         yield word + " "
    #         time.sleep(0.02)

    # st.write_stream(stream_positive_summary)

    # Generate "room for improvement" section
    st.subheader("🤔 Room for improvement")
    prompt = build_prompt(
        st.session_state.reviews[st.session_state.reviews["rating"] < 4].sample(frac=1)
    )
    prompt += "\n\nFor this analysis, only critical reviews have been selected. \
    Please summarize the key critical issues raised in the user feedback."

    with st.spinner("Summarizing negative reviews..."):
        negative_summary = get_llm_summary(prompt, api_key)

    st.write("The following issues were raised by dissatisfied users:")
    st.write(negative_summary)
    # def stream_negative_summary():
    #     for word in negative_summary.split():
    #         yield word + " "
    #         time.sleep(0.02)

    # st.write_stream(stream_negative_summary)

    # Show rating distribution
    st.subheader("Rating distribution")
    fig = create_rating_distribution_plot(st.session_state.reviews)
    st.plotly_chart(fig)

    image = generate_wordcloud(st.session_state.reviews)
    st.image(image, caption="Word Cloud", use_column_width=True)

    with st.expander("Inspect raw data"):
        st.dataframe(st.session_state.reviews)
