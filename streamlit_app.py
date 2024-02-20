import streamlit as st
from src.utils import app_store_reviews
from datetime import datetime
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from PIL import Image
import io

st.header("App Store Review Analysis")

app_store_url = st.text_input(
    "**Your App Store URL** 📱",
    placeholder="https://apps.apple.com/...",
)

st.markdown(
    "*For a demo, try this URL: https://apps.apple.com/de/app/slack/id618783545*"
)

today = datetime.datetime.now()
jan_1 = datetime.date(today.year, 1, 1)


date_range = st.date_input(
    "Date range",
    value=(jan_1, today),
    max_value=today,
    format="DD.MM.YYYY",
)
start_date = date_range[0].strftime("%Y-%m-%d")

if len(date_range) > 1:
    end_date = date_range[1].strftime("%Y-%m-%d")


def get_reviews():
    reviews = app_store_reviews(
        url=app_store_url, start_date=start_date, end_date=end_date
    )
    return reviews


if st.button("Get reviews"):

    if start_date and end_date:
        if start_date < end_date:
            reviews = get_reviews()
            st.dataframe(reviews)
            st.markdown(
                "*For now, this app only shows the reviews without any analysis.*"
            )


# Function to generate and display word cloud
def generate_wordcloud(data):
    # Combine all reviews into a single string
    text = " ".join(review for review in data["review"].astype(str))

    # Create and generate a word cloud image with transparent background
    wordcloud = WordCloud(background_color=None, mode="RGBA").generate(text)

    # Use plt to create a figure
    plt.figure(figsize=(10, 6))
    plt.imshow(wordcloud, interpolation="bilinear")
    plt.axis("off")

    # Save plt figure to a bytes buffer
    buf = io.BytesIO()
    plt.savefig(buf, format="png", transparent=True)
    buf.seek(0)

    # Use PIL to open the bytes buffer as an Image, and then display it in Streamlit
    image = Image.open(buf)
    st.image(image, caption="Word Cloud", use_column_width=True)


# Call the function to generate and display the word cloud
# only call function if reviews have been retrieved
if "reviews" in locals():
    st.title("Most Common Words in Reviews")
    generate_wordcloud(reviews)
