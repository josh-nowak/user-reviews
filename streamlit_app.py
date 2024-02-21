import streamlit as st
from src.utils import (
    app_store_reviews,
    generate_wordcloud,
    create_rating_distribution_plot,
    build_prompt,
    get_llm_summary,
    get_llm_recommendations,
    app_data_from_url,
    count_tokens,
    estimate_token_cost
)
import datetime
import pandas as pd

st.title("App Store Review Summary")

# Initialize session states
if "reviews" not in st.session_state:
    st.session_state.reviews = None
if "use_test_data" not in st.session_state:
    st.session_state.use_test_data = False
if "app_store_url" not in st.session_state:
    st.session_state.app_store_url = None

# App selection
app_store_url = st.text_input(
    "Enter an **App Store URL**",
    placeholder="https://apps.apple.com/...",
    disabled=st.session_state.use_test_data
)

# Allow users to use test dataset
st.checkbox("Use demo data instead (60 reviews of the Slack App)",
            key="use_test_data")
if st.session_state.use_test_data:
    st.session_state.reviews = pd.read_csv("reviews_test_data.csv")
    demo_url = "https://apps.apple.com/de/app/slack/id618783545"
    st.session_state.app_store_url = demo_url

if not st.session_state.use_test_data:
    st.session_state.reviews = None
    st.session_state.app_store_url = app_store_url


# Date selection
today = datetime.datetime.now()
default_start_date = datetime.date(today.year, 1, 1)
date_range = st.date_input(
    "Set a **date range** for reviews to analyze",
    value=(default_start_date, today),
    max_value=today,
    format="DD.MM.YYYY", # not included in older streamlit versions
)
start_date = date_range[0].strftime("%Y-%m-%d")
if len(date_range) > 1:
    end_date = date_range[1].strftime("%Y-%m-%d")

st.markdown(":grey[Note: Only the last 100 reviews can be downloaded, since \
            excessive scraping is blocked by Apple. \
            You can further constrain this limit with the date range, \
            but not extend it.]")

# Model selection
model_name = st.radio("Select the LLM to be used for summarization",
                    options=["gpt-3.5-turbo",
                  "gpt-4-0125-preview"],
                # captions are only included in newer versions of streamlit
                  captions=["Faster and low-cost",
                            "More thorough and higher-cost"]
                ) 

# API key 
api_key = st.text_input("Enter your OpenAI API key",
                        type="password")

# Function for scraping reviews
def get_reviews():
    reviews = app_store_reviews(
        url=app_store_url, start_date=start_date, end_date=end_date
    )
    return reviews



# Initialize session states for the buttons to use them across scopes
if "clicked_load" not in st.session_state:
    st.session_state.clicked_load = False
if "clicked_analysis" not in st.session_state:
    st.session_state.clicked_analysis = False

# Initialize session states for the prompts
if "prompt_positive" not in st.session_state:
    st.session_state.prompt_positive = None
if "prompt_negative" not in st.session_state:
    st.session_state.prompt_negative = None

# Main CTA: Load reviews
if st.button("Load reviews", type="primary"):
    st.session_state.clicked_load = True


# Perform general preparation (data loading and prompt generation) when
    # any button is clicked
if st.session_state.clicked_load:

    # Load reviews
    if st.session_state.reviews is None:
        with st.spinner("Loading reviews..."):
            if start_date and end_date:
                if start_date < end_date:
                    # Store reviews in session state
                    st.session_state.reviews = get_reviews()
        print("len", len(st.session_state.reviews))

        # Show a success message
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
    
    # Estimate input token amount and API cost
    input_token_count_total = 0
    if st.session_state.prompt_positive is not None:
        input_token_count_prompt_positive = count_tokens(st.session_state.prompt_positive)
        input_token_count_total += input_token_count_prompt_positive
    
    if st.session_state.prompt_negative is not None:
        input_token_count_prompt_negative = count_tokens(st.session_state.prompt_negative)
        input_token_count_total += input_token_count_prompt_negative

    input_token_cost = estimate_token_cost(token_count = input_token_count_total,
                                           model_name = model_name)

    # Display cost estimation to user
    st.markdown(f"{len(st.session_state.reviews)} reviews were downloaded, resulting in\
                 a total of {input_token_count_total} input tokens. Find the retrieved reviews below.")
    st.dataframe(st.session_state.reviews)
    st.markdown(f"Creating summaries with `{model_name}` would cost you approximately\
                 **${round(input_token_cost, 2)}**. You can decrease the date range to decrease the cost.")
    st.markdown("**Would you like to continue the analysis, using your OpenAI API budget?**")

    if st.button("Yes, continue analysis", type="primary"):
        st.session_state.clicked_analysis = True

# Perform analysis when button is clicked
if st.session_state.clicked_analysis:
    st.markdown("---")

    # Generate an introductory text for the analysis
    country, app_name, app_id = app_data_from_url(st.session_state.app_store_url)
    n_reviews_found = len(st.session_state.reviews)
    p_positive_reviews = len(
        st.session_state.reviews[st.session_state.reviews["rating"] > 3]
    ) / n_reviews_found
    intro_text = f'The App **"{app_name.capitalize()}"** received **{n_reviews_found} App Store reviews** in the \
        selected time frame. About **{round(p_positive_reviews*100)}% of these \
            reviews were positive**, with a rating 4 or 5 stars.'
    # Display the intro text
    st.write(intro_text)

    # Generate "highlights" section
    st.subheader("🤩 Highlights")

    positive_summary = None
    if st.session_state.prompt_positive is not None:
        with st.spinner("Summarizing positive reviews..."):
            positive_summary = get_llm_summary(st.session_state.prompt_positive, api_key)
        st.write("The following points were highlighted by satisfied users:")
        st.write(positive_summary)
    else:
        st.write("No positive reviews (> 3 stars) were found. A summary cannot be created.")


    # Generate "room for improvement" section
    st.subheader("🤔 Room for improvement")

    negative_summary = None
    if st.session_state.prompt_negative is not None:
        with st.spinner("Summarizing negative reviews..."):
            negative_summary = get_llm_summary(st.session_state.prompt_negative, api_key)
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
        st.write(recommendations)
    else:
        st.write("No reviews were found.")

    # st.subheader("Rating distribution")
    # fig = create_rating_distribution_plot(st.session_state.reviews)
    # st.plotly_chart(fig)

    # image = generate_wordcloud(st.session_state.reviews)
    # st.image(image, caption="Word Cloud", use_column_width=True)
