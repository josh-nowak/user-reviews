import streamlit as st
from src.utils import (
    app_store_reviews,
    app_store_reviews_with_timeout,
    build_prompt,
    get_llm_summary,
    get_llm_recommendations,
    app_data_from_url,
    count_tokens,
    estimate_token_cost,
)
import datetime
import pandas as pd

st.title("App Review Summaries 📱")

st.subheader("Get AI-powered insights from App Store reviews")

st.caption(
    """
This is an early version of the app. If you encounter any issues or have feedback, [let me know](mailto:hi@joshua-nowak.com).
"""
)

# Initialize session states
if "reviews" not in st.session_state:
    st.session_state.reviews = None
if "data_source" not in st.session_state:
    st.session_state.data_source = None
if "app_store_url" not in st.session_state:
    st.session_state.app_store_url = None
if "prompt_positive" not in st.session_state:
    st.session_state.prompt_positive = None
if "prompt_negative" not in st.session_state:
    st.session_state.prompt_negative = None

# Data source selection
data_source = st.radio(
    label="**How would you like to load the app reviews?**",
    options=[
        "🌐 **Load reviews from the Apple App Store (beta)**",
        "📤 **Upload reviews**",
        "🧪 **Use demo data**",
    ],
    captions=[
        "This may take some time and is not guaranteed to work.",
        "Use your own .csv file containing reviews.",
        "Use a pre-loaded dataset with 60 recent reviews of the Slack App.",
    ],
)

##############################
##### OPTION 1: APP STORE
##############################

if "App Store" in data_source:
    st.session_state.data_source = "app_store"

    app_store_url = st.text_input(
        "Enter the **App Store URL** for the app to analyze",
        placeholder="https://apps.apple.com/...",
    )

    # Date selection
    today = datetime.datetime.now()
    default_start_date = datetime.date(today.year, 1, 1)
    date_range = st.date_input(
        "Set a **date range** for reviews to include in the analysis",
        value=(today - datetime.timedelta(days=7), today),
        max_value=today,
        format="DD.MM.YYYY",  # not included in older streamlit versions
        help="A maximum of 100 reviews will be downloaded in order \
                to prevent excessive scraping. \
                You can further constrain the amount with the date range, \
                but not extend it.",
    )
    start_date = date_range[0].strftime("%Y-%m-%d")
    if len(date_range) > 1:
        end_date = date_range[1].strftime("%Y-%m-%d")


##############################
##### OPTION 2: UPLOAD
##############################

elif "Upload" in data_source:
    st.session_state.data_source = "upload"

    st.info(
        """
**Your file with app store reviews should be in .csv format and contain the following columns**:  
- `title`: The review's title text
- `review`: The review's content text
- `rating`: The review's star rating (a number in the range of 1—5)   

Other columns can be present but will be ignored. If you upload more than 500 reviews, only a random sample of 500 reviews will be used.
                """
    )

    uploaded_file = st.file_uploader("Upload your **.csv file** here")

    st.warning(
        """
**You need to provide an OpenAI API key** when using your own data, because the amount of tokens can become quite high. Enter your API key in the advanced settings below.
"""
    )


##############################
##### OPTION 3: DEMO DATA
##############################

elif "demo" in data_source:
    st.session_state.data_source = "demo"


##############################

# Set session state URL variable
if st.session_state.data_source == "app_store":
    st.session_state.app_store_url = app_store_url
elif st.session_state.data_source == "demo":
    demo_url = "https://apps.apple.com/de/app/slack/id618783545"
    st.session_state.app_store_url = demo_url
elif st.session_state.data_source == "upload":
    st.session_state.app_store_url = None
    

# Model selection
with st.expander("Advanced settings"):
    model_name = st.radio(
        "Select a **model** to be used for summarization",
        options=["gpt-3.5-turbo", "gpt-4-0125-preview"],
        # captions are only included in newer versions of streamlit
        captions=["Faster and cheaper", "Higher-quality and more expensive"],
    )

    # API key
    api_key_input = st.text_input("Enter your **OpenAI API key**", type="password")
    if model_name == "gpt-3.5-turbo":
        st.info(
            "When selecting **GPT 3.5**, entering your own API key is **not required**."
        )
    elif len(api_key_input) == 0 and model_name != "gpt-3.5-turbo":
        st.warning(
            "When selecting **GPT-4**, an API key **needs to be provided**. \
                 You will receive a cost estimate before any API calls are made."
        )

    # Timeout
    if st.session_state.data_source == "app_store":
        timeout = st.number_input(
            "Scraping reviews can take time. Change the timeout (in seconds) below.",
            value=60,
        )

# Assign api_key variable for easier/safer logic flow later
if len(api_key_input) == 0:
    api_key = None
else:
    api_key = api_key_input


# Define function for scraping reviews with caching
@st.cache_data
def get_reviews():
    reviews = app_store_reviews_with_timeout(
        url=app_store_url, start_date=start_date, end_date=end_date, timeout=timeout
    )
    return reviews


# STAGE LOGIC
# Set "stage logic" for controlling user flow
# 0 — Initial state
# 1 — Inputs were given, user requested loading
# 2 — Loading completed, user requested analysis
if "stage" not in st.session_state:
    st.session_state.stage = 0


def set_stage(i):
    st.session_state["stage"] = i


# Main CTA: Load reviews
st.button("Load reviews", type="primary", on_click=set_stage, args=[1])

###################
# DATA LOADING
###################

if st.session_state.stage > 0:

    # Catch missing API key when using own data
    if api_key is None and st.session_state.data_source == "upload":
        raise ValueError(
            "An API key is required when using your own data. Please enter your API key in the advanced settings."
        )

    # Load reviews if not already done
    if st.session_state.reviews is None:

        # Option 1: Scrape review data
        if st.session_state.data_source == "app_store":
            with st.spinner("Loading reviews... (this may take a while!)"):
                if start_date and end_date:
                    if start_date < end_date:
                        # Store reviews in session state
                        st.session_state.reviews = get_reviews()

        # Option 2: Read demo data
        elif st.session_state.data_source == "demo":
            st.session_state.reviews = pd.read_csv("reviews_test_data.csv")

        # Option 3: Read uploaded file
        elif st.session_state.data_source == "upload":
            if uploaded_file is not None:
                st.session_state.reviews = pd.read_csv(uploaded_file)
                # Check if the required columns are present
                required_columns = ["title", "review", "rating"]
                if not all(
                    col in st.session_state.reviews.columns for col in required_columns
                ):
                    raise ValueError(
                        'The uploaded file does not contain the required columns "title", "review", and "rating".'
                    )
                
                # If the file is larger than 500 rows, only use a random sample of 500 rows
                if len(st.session_state.reviews) > 500:
                    st.session_state.reviews = st.session_state.reviews.sample(500)

                    # Warn the user about the sample
                    st.warning(
                        "The uploaded file contains more than 500 reviews. A random sample of 500 reviews will be used for the analysis."
                    )

            else:
                raise FileNotFoundError(
                    "A review file could not be found. Please reload the page and try uploading your file again."
                )

        # If the user did not give an API key, proceed to analysis
        # (Otherwise, the API cost estimation section will show first.)
        if api_key is None:
            st.session_state.stage = 2

    positive_reviews = st.session_state.reviews[
        st.session_state.reviews["rating"] > 3
    ].sample(frac=1)
    negative_reviews = st.session_state.reviews[
        st.session_state.reviews["rating"] < 4
    ].sample(frac=1)

    # Build prompts for all summaries
    if len(positive_reviews) > 0:
        st.session_state.prompt_positive = build_prompt(
            st.session_state.reviews[st.session_state.reviews["rating"] > 3].sample(
                frac=1
            )
        )
        st.session_state.prompt_positive += "\n\nFor this analysis, only the positive reviews have been selected. \
            Please summarize the positive highlights in the user feedback."

    if len(negative_reviews) > 0:
        st.session_state.prompt_negative = build_prompt(
            st.session_state.reviews[st.session_state.reviews["rating"] < 4].sample(
                frac=1
            )
        )
        st.session_state.prompt_negative += "\n\nFor this analysis, only critical reviews have been selected. \
        Please summarize the key critical issues raised in the user feedback."

###################
# API COST ESTIMATE
###################

if st.session_state.stage > 0 and api_key is not None:

    st.header("API Cost Estimation")

    # Estimate input token amount and API cost
    input_token_count_total = 0

    # Add input token amount for summaries
    if st.session_state.prompt_positive is not None:
        input_token_count_prompt_positive = count_tokens(
            st.session_state.prompt_positive
        )
        input_token_count_total += input_token_count_prompt_positive
    if st.session_state.prompt_negative is not None:
        input_token_count_prompt_negative = count_tokens(
            st.session_state.prompt_negative
        )
        input_token_count_total += input_token_count_prompt_negative

    # Add estimated input token amount for recommendations
    input_token_count_total += 500  # heuristic value based on common summary outputs

    # Add estimated output token amount
    output_token_count_total = 1000

    token_cost = estimate_token_cost(
        input_token_count=input_token_count_total,
        output_token_count=output_token_count_total,
        model_name=model_name,
    )

    if round(token_cost, 2) == 0:
        token_cost_explanation = "less than $0.01"
    else:
        token_cost_explanation = f"roughly ${round(token_cost, 2):.2f}"

    # Walk the user through the cost estimation

    st.write(
        "Since you provided your API key, let's estimate the cost of the analysis before proceeding."
    )

    st.markdown(
        f"**{len(st.session_state.reviews)} user reviews** were loaded in total."
    )

    with st.expander("Show loaded reviews"):
        st.dataframe(st.session_state.reviews)

    st.markdown(
        f"Creating summaries with `{model_name}` would cost you\
                 **{token_cost_explanation}** (based on input and output token estimates)."
    )

    st.markdown(
        f"**Would you like to continue and use {token_cost_explanation} of your OpenAI API credits?**"
    )

    st.button("Yes, generate insights", type="primary", on_click=set_stage, args=[2])


###################
# SUMMARIZATION
###################

if st.session_state.stage > 1:
    st.markdown("---")

    st.header("Insights")

    if st.session_state.reviews is None:
        raise ValueError(
            "The reviews can no longer be found. Please reload the page and try again."
        )

    # Get app name
    if (
        st.session_state.data_source == "demo"
        or st.session_state.data_source == "app_store"
    ):
        country, app_name, app_id = app_data_from_url(st.session_state.app_store_url)
    else:
        app_name = None

    n_reviews_found = len(st.session_state.reviews)
    p_positive_reviews = (
        len(st.session_state.reviews[st.session_state.reviews["rating"] > 3])
        / n_reviews_found
    )

    st.write(
        f"""
{n_reviews_found} reviews were found for {app_name.capitalize() if app_name is not None else 'your app'}.\
      About **{round(p_positive_reviews*100)}% of these reviews were positive**, with a rating 4 or 5 stars.
"""
    )

    st.write(f"")

    # Generate "highlights" section
    st.subheader("🤩 Highlights")

    positive_summary = None
    if st.session_state.prompt_positive is not None:
        with st.spinner("Summarizing positive reviews..."):
            positive_summary = get_llm_summary(
                st.session_state.prompt_positive, api_key=api_key, model=model_name
            )
        st.write("The following points were highlighted by satisfied users:")
        st.markdown(positive_summary)
    else:
        st.write(
            "No positive reviews (> 3 stars) were found. A summary cannot be created."
        )

    # Generate "room for improvement" section
    st.subheader("🤔 Problems")

    negative_summary = None
    if st.session_state.prompt_negative is not None:
        with st.spinner("Summarizing negative reviews..."):
            negative_summary = get_llm_summary(
                st.session_state.prompt_negative, api_key=api_key, model=model_name
            )
        st.write("The following issues were raised by dissatisfied users:")
        st.markdown(negative_summary)
    else:
        st.write(
            "No negative reviews (< 4 stars) were found. A summary cannot be created."
        )

    # Generate "recommendations" section
    st.subheader("🧭 Recommended improvements")
    summaries = [positive_summary, negative_summary]

    if positive_summary is not None or negative_summary is not None:
        with st.spinner("Generating recommendations..."):
            recommendations = get_llm_recommendations(
                summaries=summaries,
                api_key=api_key,
                app_name=app_name,
                model=model_name,
            )
        st.write(
            "Based on the user feedback, consider the following product recommendations:"
        )
        st.markdown(recommendations)
    else:
        st.write("No reviews were found.")

    st.markdown("---")

    st.info(
        """
**Feedback, issues, or concerns?** [Let me know](mailto:hi@joshua-nowak.com).  
For a new analysis, please reload the page.
"""
    )
