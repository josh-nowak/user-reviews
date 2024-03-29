import pandas as pd
import re
from app_store_scraper import AppStore
from datetime import datetime
import io
from openai import OpenAI
import tiktoken
import threading


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

def app_store_reviews_with_timeout(url: str, n_last_reviews: int = 100, start_date: str = None, end_date: str = None, timeout: int = 60):
    # Placeholders for results and completion flag
    reviews_list = []
    completed = False
    end_date_dt = datetime.now()
    
    def scrape_reviews():
        nonlocal reviews_list, completed, end_date_dt

        # Create AppStore object based on URL
        country, app_name, app_id = app_data_from_url(url)
        app = AppStore(country=country, app_name=app_name, app_id=app_id)

        # Convert dates to datetime objects
        if start_date:
            start_date_dt = datetime.strptime(start_date, "%Y-%m-%d")
        else:
            start_date_dt = datetime.strptime("2000-01-01", "%Y-%m-%d")

        if end_date:
            end_date_dt = datetime.strptime(end_date, "%Y-%m-%d")
        else:
            end_date_dt = datetime.now()

        # Scrape reviews for the specified App
        app.review(how_many=n_last_reviews, after=start_date_dt)

        # Store the scraped reviews
        reviews_list = app.reviews
        
        # Mark completion
        completed = True

    # Start scraping in a separate thread
    thread = threading.Thread(target=scrape_reviews)
    thread.start()

    # Wait for 30 seconds or until the thread finishes
    thread.join(timeout=timeout)

    if not completed:
        raise TimeoutError(f"Review scraping did not complete within {timeout} seconds.")
    
    # Convert response to dataframe, assuming scraping was successful
    reviews = pd.DataFrame(reviews_list)

    # Throw an error if there are no reviews
    if len(reviews) == 0:
        raise FileExistsError("Couldn't load reviews. Either there are no \
                            reviews existing in the specified date range \
                            or Apple returned a 429 error (too many requests).")

    # Final filtering and sorting
    reviews = reviews.loc[:, ["date", "title", "review", "rating"]]
    reviews = reviews[reviews["date"] < end_date_dt]
    reviews = reviews.sort_values(by="date", ascending=False)

    return reviews

def build_prompt(reviews=None):

    prompt = """
Synthesize the key points from the following app store reviews into one single summary in English language using bullet points. 
Create between 3 and 5 bullet points in order to mention only the most important and frequent feedback. 
You can find the reviews below, along with their respective ratings, where 1/5 is worst and 5/5 ist best.
Output only the bullet points and nothing else. Each bullet point should contain 2 sentences.
Use bolded text for important aspects to improve readability.

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


def get_llm_summary(prompt: str, api_key: str = None, model: str = "gpt-3.5-turbo"):
    if api_key is None and model == "gpt-3.5-turbo":
        client = OpenAI() # use environment variable
    elif api_key is None and model != "gpt-3.5-turbo":
        raise ValueError("Please provide an OpenAI API key.")
    else:
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

def get_llm_recommendations(summaries: list, app_name: str, api_key: str = None, model: str = "gpt-3.5-turbo"):
    if api_key is None and model == "gpt-3.5-turbo":
        client = OpenAI() # use environment variable
    elif api_key is None and model != "gpt-3.5-turbo":
        raise ValueError("Please provide an OpenAI API key.")
    else:
        client = OpenAI(api_key=api_key)

    prompt = f"Below you will find summarized user feedback for the \
            app {app_name} based on App Store reviews. Suggest concrete improvements to improve \
            the app based on this feedback, using 3 to 5 bullet points. Output only the bullet points and nothing else.\
                 Each bullet point should contain 2 sentences. Use bolded text for important aspects to improve readability. \n\n"

    for summary in summaries:
        if summary is None:
            continue
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

def estimate_token_cost(input_token_count,
                        output_token_count,
                        model_name = "gpt-3.5-turbo"):
    
    if model_name == "gpt-3.5-turbo":
        cost_estimate = input_token_count * 0.0005 / 1000
        cost_estimate += output_token_count * 0.0015 / 1000
    elif model_name == "gpt-4-0125-preview":
        cost_estimate = input_token_count * 0.01 / 1000
        cost_estimate += output_token_count * 0.06 / 1000
    else:
        raise ValueError(f"Model name {model_name} is unknown.")
    return cost_estimate