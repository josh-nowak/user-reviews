import pandas as pd
import numpy as np
import json
import re
from app_store_scraper import AppStore
from datetime import datetime


def app_data_from_url(url):
    pattern = r".*apps.apple.com/(?P<country>[a-z]{2})/app/(?P<app_name>[^/]+)/id(?P<app_id>\d+)"
    match = re.match(pattern, url)

    if not match:
        raise ValueError("Please enter a valid App Store URL")

    country = match.group("country")
    app_name = match.group("app_name")
    app_id = match.group("app_id")
    return country, app_name, app_id


def app_store_reviews(url: str, n_last_reviews: int, after: str = False):
    country, app_name, app_id = app_data_from_url(url)
    app = AppStore(country=country, app_name=app_name, app_id=app_id)

    if after:
        after = datetime.strptime(after, "%Y-%m-%d")

    app.review(how_many=n_last_reviews, after=after)
    reviews = pd.DataFrame(app.reviews)
    reviews = reviews.loc[:, ["date", "title", "review", "rating"]]
    reviews = reviews.sort_values(by="date", ascending=False)
    return reviews

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
