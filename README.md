# AI-Generated App Store Review Summaries

This tool **summarizes user reviews** for any app in the Apple App Store using GPT-3.5 or GPT-4. It's targeted at developers and product people looking to improve their apps.

#### [👉 Run the app on Streamlit](https://user-reviews.streamlit.app/)

## Main features
- **Retrieve reviews from any app** by entering the App Store URL
- **Upload your own app store reviews** as a CSV file
- Run a **free AI-generated analysis** of users' highlights, problems, and product opportunities using GPT-3.5
- Specify **your own OpenAI API key** to generate an improved analysis with GPT-4
- Get an **API cost estimation** before running the analysis when using your own API key

## Preview 
![](assets/app_demo.webm)

## Local installation
If you want to run the streamlit app locally, create an environment with Python version `3.10.0` and install the requirements from your terminal:
```
pip install requirements.txt
```

Run the streamlit app with the following command:
```
streamlit run streamlit_app.py
```