import pandas as pd
import re
from app_store_scraper import AppStore
from datetime import datetime
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import io
from PIL import Image
import plotly.express as px
from openai import OpenAI
import tiktoken


def app_data_from_url(url):
    pattern = r".*apps.apple.com/(?P<country>[a-z]{2})/app/(?P<app_name>[^/]+)/id(?P<app_id>\d+)"
    match = re.match(pattern, url)

    if not match:
        raise ValueError("Please enter a valid App Store URL")

    country = match.group("country")
    app_name = match.group("app_name")
    app_id = match.group("app_id")
    return country, app_name, app_id


def app_store_reviews(
    url: str, n_last_reviews: int = 100, start_date: str = None, end_date: str = None
):

    # Create AppStore object based on URL
    country, app_name, app_id = app_data_from_url(url)
    app = AppStore(country=country, app_name=app_name, app_id=app_id)

    # Convert dates to datetime objects
    if start_date:
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
    else:
        start_date = datetime.strptime("2000-01-01", "%Y-%m-%d")

    if end_date:
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
    else:
        end_date = datetime.now()

    # Scrape reviews for the specified App
    app.review(how_many=n_last_reviews, after=start_date)

    # Convert response to dataframe
    reviews = pd.DataFrame(app.reviews)

    # Throw an error if there are no reviews
    if len(reviews) == 0:
        raise FileExistsError("Couldn't load reviews. Either there are no \
                            reviews existing in the specified date range \
                            or Apple returned a 429 error (too many requests).")
    
    # Keep only relevant columns
    reviews = reviews.loc[:, ["date", "title", "review", "rating"]]

    # Filter using end_date (start_date is implemented in app_store_scraper already)
    reviews = reviews[reviews["date"] < end_date]

    # Sort by date
    reviews = reviews.sort_values(by="date", ascending=False)
    return reviews


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

    return image


def create_rating_distribution_plot(reviews):
    # Count the occurrences of each rating
    rating_counts = reviews["rating"].value_counts().reset_index()
    rating_counts.columns = ["rating", "count"]

    # Ensure we have all ratings from 1 to 5, even if some are missing in the data
    all_ratings = pd.DataFrame({"rating": range(1, 6)})
    rating_counts = pd.merge(
        all_ratings, rating_counts, on="rating", how="left"
    ).fillna(0)

    # Create a bar plot with white bars
    fig = px.bar(
        rating_counts,
        x="rating",
        y="count",
        labels={"count": "Count", "rating": "Rating"},  # Customizing axis labels
        color_discrete_sequence=["white"] * len(rating_counts),
    )  # Making bars white

    # Update layout for aesthetics
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",  # Transparent plot background
        paper_bgcolor="rgba(0,0,0,0)",  # Transparent paper background
        font=dict(size=12, color="Yellow"),  # Update font style and color
        # title_font=dict(size=20, color="Yellow"),  # Update title font style and color
    )

    return fig


def build_prompt(reviews=None):

    prompt = """
Synthesize the key points from the following app store reviews into one single summary in English language using bullet points. 
Create between 3 and 10 bullet points in order to mention only the most important and frequent feedback. 
You can find the reviews below, along with their respective ratings, where 1/5 is worst and 5/5 ist best.

"""

    reviews["complete_info_for_prompting"] = (
        "Review title: "
        + reviews["title"]
        + "\nReview rating: "
        + reviews["rating"].astype("str")
        + "/5"
        "\nReview text: " + reviews["review"] + "\n\n"
    )

    prompt += reviews["complete_info_for_prompting"].sum()

    return prompt


def get_llm_summary(prompt: str, api_key: str, model: str = "gpt-3.5-turbo"):
    client = OpenAI(api_key=api_key)
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are an expert user researcher, skilled in summarizing and explaining user feedback.",
            },
            {"role": "user", "content": prompt},
        ],
    )
    return completion.choices[0].message.content

def get_llm_recommendations(summaries: list, api_key: str, app_name: str, model: str = "gpt-3.5-turbo"):
    client = OpenAI(api_key=api_key)

    prompt = f"Below you will find summarized user feedback for the \
        app {app_name} based on App Store reviews. Suggest concrete improvements to improve \
            the app based on this feedback, using 3 to 10 bullet points. \n\n"

    for summary in summaries:
        if summary is None:
            next()
        prompt += summary + "\n\n"

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are an expert user researcher, skilled in providing\
                      actionable product recommendations based on user feedback.",
            },
            {"role": "user", "content": prompt},
        ],
    )
    return completion.choices[0].message.content

def count_tokens(prompt):
    enc = tiktoken.get_encoding("cl100k_base")
    token_count = len(enc.encode(prompt))
    return token_count

def estimate_token_cost(token_count, model_name = "gpt-3.5-turbo"):
    if model_name == "gpt-3.5-turbo":
        cost_estimate = token_count * 0.0005 / 1000
    elif model_name == "gpt-4-0125-preview":
        cost_estimate = token_count * 0.01 / 1000
    else:
        raise ValueError(f"Model name {model_name} is unknown.")
    return cost_estimate