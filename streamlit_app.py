import streamlit as st
from src.utils import (
    app_store_reviews,
    build_prompt,
    get_llm_summary,
    get_llm_recommendations,
    app_data_from_url,
    count_tokens,
    estimate_token_cost
)
import datetime
import pandas as pd

st.title("App Review Summaries 📱")

# Initialize session states
if "reviews" not in st.session_state:
    st.session_state.reviews = None
if "use_test_data" not in st.session_state:
    st.session_state.use_test_data = False
if "app_store_url" not in st.session_state:
    st.session_state.app_store_url = None

# App selection
st.subheader("Which app would you like to analyze?")
app_store_url = st.text_input(
    "Enter an **App Store URL**",
    placeholder="https://apps.apple.com/...",
    disabled=st.session_state.use_test_data
)

# Date selection
today = datetime.datetime.now()
default_start_date = datetime.date(today.year, 1, 1)
date_range = st.date_input(
    "Set a **date range** for reviews to include in the analysis",
    value=(default_start_date, today),
    max_value=today,
    format="DD.MM.YYYY", # not included in older streamlit versions
    disabled=st.session_state.use_test_data,
    help = "A maximum of 100 reviews will be downloaded in order \
            to prevent excessive scraping. \
            You can further constrain this limit with the date range, \
            but not extend it."
)
start_date = date_range[0].strftime("%Y-%m-%d")
if len(date_range) > 1:
    end_date = date_range[1].strftime("%Y-%m-%d")

# Allow users to use test dataset
st.checkbox("Use **demo data** instead (60 recent reviews of the Slack App)",
            key="use_test_data")

if st.session_state.use_test_data:
    demo_url = "https://apps.apple.com/de/app/slack/id618783545"
    st.session_state.app_store_url = demo_url
if not st.session_state.use_test_data:
    st.session_state.reviews = None
    st.session_state.app_store_url = app_store_url

# Model selection
with st.expander("Advanced options for LLM specification"):
    model_name = st.radio("Select a **model** to be used for summarization",
                        options=["gpt-3.5-turbo",
                    "gpt-4-0125-preview"],
                    # captions are only included in newer versions of streamlit
                    captions=["Faster and cheaper",
                                "Higher-quality and more expensive"]
                    ) 

    # API key 
    api_key_input = st.text_input("Enter your OpenAI API key",
                            type="password")
    if model_name == "gpt-3.5-turbo":
        st.info("When selecting **GPT 3.5**, entering your own API key is **not required**.")
    elif len(api_key_input) == 0 and model_name != "gpt-3.5-turbo":
        st.warning("When selecting **GPT-4**, an API key **needs to be provided**. \
                 You will receive a cost estimate before any API calls are made.")

if len(api_key_input) == 0:
    api_key = None
else:
    api_key = api_key_input

# Function for scraping reviews
def get_reviews():
    reviews = app_store_reviews(
        url=app_store_url, start_date=start_date, end_date=end_date
    )
    return reviews

# Initialize session states for the buttons to use them across scopes
# if "clicked_load" not in st.session_state:
#     st.session_state.clicked_load = False
# if "clicked_analysis" not in st.session_state:
#     st.session_state.clicked_analysis = False

# Alternative approach
if "stage" not in st.session_state:
    st.session_state.stage = 0

def set_stage(i):
    st.session_state.stage = i

# Initialize session states for the prompts
if "prompt_positive" not in st.session_state:
    st.session_state.prompt_positive = None
if "prompt_negative" not in st.session_state:
    st.session_state.prompt_negative = None

# Main CTA: Load reviews
st.button("Load reviews", type="primary", on_click=set_stage, args = [1])


###################
# DATA LOADING
###################

if st.session_state.stage == 1:
    # Load reviews if not already done
    if st.session_state.reviews is None:
        if st.session_state.use_test_data:
             st.session_state.reviews = pd.read_csv("reviews_test_data.csv")
        else:
            with st.spinner("Loading reviews... (this may take a while!)"):
                if start_date and end_date:
                    if start_date < end_date:
                        # Store reviews in session state
                        st.session_state.reviews = get_reviews()
        st.toast(f"🎉 Reviews successfully loaded!")

    positive_reviews = st.session_state.reviews[st.session_state.reviews["rating"] > 3].sample(frac=1)
    negative_reviews = st.session_state.reviews[st.session_state.reviews["rating"] < 4].sample(frac=1)

    # Build prompts for all summaries
    if len(positive_reviews) > 0:
        st.session_state.prompt_positive = build_prompt(
            st.session_state.reviews[st.session_state.reviews["rating"] > 3].sample(frac=1)
        )
        st.session_state.prompt_positive += "\n\nFor this analysis, only the positive reviews have been selected. \
            Please summarize the positive highlights in the user feedback."
        
    if len(negative_reviews) > 0:
        st.session_state.prompt_negative = build_prompt(
            st.session_state.reviews[st.session_state.reviews["rating"] < 4].sample(frac=1)
        )
        st.session_state.prompt_negative += "\n\nFor this analysis, only critical reviews have been selected. \
        Please summarize the key critical issues raised in the user feedback."
    
    # If user provided an API key, move on to cost estimation
    if api_key is not None:
        set_stage(2)
    # If user provided no API key, skip straight to analysis
    else:
        set_stage(3)

###################
# API COST ESTIMATE
###################

if st.session_state.stage > 1 and api_key is not None:
    
    # Estimate input token amount and API cost
    input_token_count_total = 0
    
    # Add input token amount for summaries
    if st.session_state.prompt_positive is not None:
        input_token_count_prompt_positive = count_tokens(st.session_state.prompt_positive)
        input_token_count_total += input_token_count_prompt_positive
    if st.session_state.prompt_negative is not None:
        input_token_count_prompt_negative = count_tokens(st.session_state.prompt_negative)
        input_token_count_total += input_token_count_prompt_negative
    
    # Add estimated input token amount for recommendations
    input_token_count_total += 500 # heuristic value based on common summary outputs

    # Add estimated output token amount
    output_token_count_total = 1000

    token_cost = estimate_token_cost(input_token_count = input_token_count_total,
                                           output_token_count = output_token_count_total,
                                           model_name = model_name)
    
    if round(token_cost, 2) == 0:
        token_cost_explanation = "less than $0.01"
    else:
        token_cost_explanation = f"roughly ${round(token_cost, 2):.2f}"

    # Display cost estimation to user
    st.markdown(f"{len(st.session_state.reviews)} user reviews were loaded, find them below.")
    
    st.dataframe(st.session_state.reviews)
    
    st.markdown(f"Creating summaries with `{model_name}` for all reviews would cost you\
                 **{token_cost_explanation}**, accounting for both input and output tokens.")
    
    st.write("You can decrease the date range to limit the amount of reviews and lower the cost.")
    
    st.markdown(f"**Would you like to continue the analysis, using {token_cost_explanation} of your OpenAI API credits?**")

    st.button("Yes, continue analysis", type="primary", on_click=set_stage, args=[3])


###################
# SUMMARIZATION
###################
        
if st.session_state.stage == 3:
    st.markdown("---")

    if st.session_state.reviews is None:
        raise LookupError("Can't find the reviews anymore!!")
    
    # Generate an introductory text for the analysis
    country, app_name, app_id = app_data_from_url(st.session_state.app_store_url)
    n_reviews_found = len(st.session_state.reviews)
    p_positive_reviews = len(
        st.session_state.reviews[st.session_state.reviews["rating"] > 3]
    ) / n_reviews_found

    if n_reviews_found >= 100:
        st.write(f'The App **"{app_name.capitalize()}"** received **{n_reviews_found} or more App Store reviews** in the \
        selected time frame. (Additional reviews have not been loaded due to scraping limits.)')
    else:
        st.write(f'The App **"{app_name.capitalize()}"** received **{n_reviews_found} App Store reviews** in the \
        selected time frame.')

    st.write(f"About **{round(p_positive_reviews*100)}% of these \
            reviews were positive**, with a rating 4 or 5 stars.")

    # Generate "highlights" section
    st.subheader("🤩 Highlights")

    positive_summary = None
    if st.session_state.prompt_positive is not None:
        with st.spinner("Summarizing positive reviews..."):
            positive_summary = get_llm_summary(st.session_state.prompt_positive,
                                            api_key=api_key,
                                            model=model_name)
        st.write("The following points were highlighted by satisfied users:")
        st.write(positive_summary)
    else:
        st.write("No positive reviews (> 3 stars) were found. A summary cannot be created.")


    # Generate "room for improvement" section
    st.subheader("🤔 Problems")

    negative_summary = None
    if st.session_state.prompt_negative is not None:
        with st.spinner("Summarizing negative reviews..."):
            negative_summary = get_llm_summary(st.session_state.prompt_negative,
                                            api_key=api_key,
                                            model=model_name)
        st.write("The following issues were raised by dissatisfied users:")
        st.write(negative_summary)
    else:
        st.write("No negative reviews (< 4 stars) were found. A summary cannot be created.")


    # Generate "recommendations" section
    st.subheader("🧭 Recommended improvements")
    summaries = [positive_summary, negative_summary]

    if positive_summary is not None or negative_summary is not None:
        with st.spinner("Generating recommendations..."):
            recommendations = get_llm_recommendations(summaries=summaries,
                                api_key=api_key,
                                app_name=app_name,
                                model=model_name)
        st.write("Based on the user feedback, consider the following product recommendations:")
        st.write(recommendations)
    else:
        st.write("No reviews were found.")