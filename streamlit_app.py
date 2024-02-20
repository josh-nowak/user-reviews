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

n_last_reviews = st.number_input("Number of most recent reviews to analyze", value=100)

after_date = st.date_input(
    "Only reviews after this date",
    format="DD.MM.YYYY",
    value=datetime.strptime("2023-01-01", "%Y-%m-%d"),
)

if st.button("Get reviews"):

    def get_reviews():
        return app_store_reviews(
            url=app_store_url,
            n_last_reviews=n_last_reviews,
            after=after_date.strftime("%Y-%m-%d"),
        )

    reviews = get_reviews()

    st.dataframe(reviews)

    st.markdown("*For now, this app only shows the reviews without any analysis.*")

# Function to generate and display word cloud
def generate_wordcloud(data):
    # Combine all reviews into a single string
    text = " ".join(review for review in data['review'].astype(str))
    
    # Create and generate a word cloud image with transparent background
    wordcloud = WordCloud(background_color=None, mode="RGBA").generate(text)
    
    # Use plt to create a figure
    plt.figure(figsize=(10, 6))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    
    # Save plt figure to a bytes buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', transparent=True)
    buf.seek(0)
    
    # Use PIL to open the bytes buffer as an Image, and then display it in Streamlit
    image = Image.open(buf)
    st.image(image, caption='Word Cloud', use_column_width=True)

# Call the function to generate and display the word cloud
# only call function if reviews have been retrieved
if 'reviews' in locals():
    st.title('Most Common Words in Reviews')
    generate_wordcloud(reviews)

