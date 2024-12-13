import streamlit as st
from bs4 import BeautifulSoup
import os
import requests
import tweepy
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from textblob import TextBlob
from translate import Translator
import pandas as pd
import plotly.express as px
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from deep_translator import GoogleTranslator
from transformers import pipeline
from fpdf import FPDF
import time

# Load environment variables
load_dotenv()

# Twitter API keys and tokens
API_KEY = os.getenv('TWITTER_API_KEY')
API_SECRET_KEY = os.getenv('TWITTER_API_SECRET_KEY')
BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')

# Authenticate to Twitter using v2 Bearer token
client = tweepy.Client(bearer_token=BEARER_TOKEN)

# NewsChain class with all the functions
class NewsChain:
    def __init__(self):
        self.llm = ChatGroq(
            temperature=0,
            groq_api_key=os.getenv("GROQ_API_KEY"),
            model_name="llama-3.1-70b-versatile"
        )
        self.news_api_key = os.getenv("NEWS_API_KEY")  # NewsAPI key
        self.translator = Translator(to_lang="en")  # Google Translator for language support
        self.fake_news_detector = pipeline("text-classification", model="facebook/bart-large-mnli")

    def fetch_global_trending_news(self):
        """Fetches global trending news using the NewsAPI."""
        url = f'https://newsapi.org/v2/top-headlines?country=us&apiKey={self.news_api_key}'  
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "ok":
                articles = data.get('articles', [])
                if not articles:
                    raise Exception("No global trending news found.")
                return [(article['title'], article.get('url', '#')) for article in articles]
            else:
                st.write("Error fetching the news")
        except requests.RequestException as e:
            st.write("Error fetching the news")

    def summarize_headlines(self, headlines):
        """Summarizes the headlines into a concise format."""
        prompt_summarize = PromptTemplate.from_template(
            """
            ### HEADLINES:
            {headlines}

            ### INSTRUCTION:
            Summarize the following news headlines into a concise bullet-point list.
            ### SUMMARY:
            """
        )
        chain_summarize = prompt_summarize | self.llm
        res = chain_summarize.invoke({"headlines": "\n".join(headlines)})
        return res.content

    def perform_sentiment_analysis(self, text):
        """Perform sentiment analysis on a text using TextBlob."""
        blob = TextBlob(text)
        sentiment = blob.sentiment.polarity
        return sentiment  # Returns a value between -1 (negative) and 1 (positive)

    def translate_text(self, text, target_language='en'):
        """Translates the given text into the target language using Google Translate."""
        translation = GoogleTranslator(source='auto', target=target_language).translate(text)
        return translation

    def generate_word_cloud(self, text_data):
        """Generate and display a word cloud."""
        wordcloud = WordCloud(width=800, height=400, background_color='white').generate(text_data)
        plt.figure(figsize=(10, 5))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis("off")
        st.pyplot(plt)

    def check_fake_news(self, article_text):
        """Detect fake news using a transformer model."""
        result = self.fake_news_detector(article_text)
        return result[0]['label'], result[0]['score']

    def categorize_headline(self, text):
        """Categorize news headlines."""
        categories = {
            'Technology': ['tech', 'AI', 'robotics'],
            'Health': ['health', 'COVID', 'medicine'],
            'Politics': ['election', 'government'],
            'Sports': ['sports', 'football', 'basketball'],
            'Business': ['business', 'economy', 'stocks'],
        }
        for category, keywords in categories.items():
            if any(keyword in text.lower() for keyword in keywords):
                return category
        return "General"

    def fetch_live_news(self):
        """Fetch and display live news updates every few seconds."""
        while True:
            latest_news = self.fetch_global_trending_news()
            st.write("Latest News Updates:")
            for idx, (headline, link) in enumerate(latest_news, 1):
                st.markdown(f"{idx}. [{headline}]({link})")
            time.sleep(30)

# Function to generate PDF from headlines
def generate_pdf(headlines):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Trending News Summary", ln=True, align='C')

    for idx, (headline, _) in enumerate(headlines, 1):
        pdf.cell(200, 10, txt=f"{idx}. {headline}", ln=True, align='L')

    pdf.output("trending_news.pdf")
    return "trending_news.pdf"

def create_streamlit_app(news_chain):
    st.title("📰 Trending News Portal")

    # Sidebar for Subscription
    with st.sidebar:
        subscription_status = st.radio("Subscription Status", ["Free", "Premium"])
        if subscription_status == "Free":
            st.markdown("**Upgrade to Premium for an Ad-Free Experience and Exclusive Features!**")
            st.sidebar.write("Ad Placeholder")
    
    # Sidebar for User Preferences
    user_preferences = st.sidebar.multiselect(
        "Select Your Interests", 
        ['Technology', 'Health', 'Sports', 'Politics', 'Business'], 
        default=['Technology']
    )
    
    # Sidebar for Language Selection
    user_language = st.sidebar.selectbox("Select Language", ['en', 'fr', 'es', 'de'])

    # Fetch Global News Headlines
    global_headlines = news_chain.fetch_global_trending_news()

    # Personalized Daily Digest (Filter by user preferences)
    filtered_news = [
        (headline, link) 
        for headline, link in global_headlines 
        if any(interest.lower() in headline.lower() for interest in user_preferences)
    ]

    st.subheader("Your Personalized Daily Digest:")
    for idx, (headline, link) in enumerate(filtered_news, 1):
        st.markdown(f"{idx}. [{headline}]({link})")

    # Show Categorized News
    categorized_headlines = [
        (headline, news_chain.categorize_headline(headline)) 
        for headline, _ in global_headlines
    ]
    st.subheader("Categorized News:")
    for headline, category in categorized_headlines:
        st.write(f"**{category}**: {headline}")

    # AI-Driven Fake News Detection
    article = st.text_area("Paste an article text to check for fake news:")
    if st.button("Check for Fake News"):
        if article:
            label, confidence = news_chain.check_fake_news(article)
            st.write(f"Prediction: **{label}** (Confidence: {confidence:.2f})")

    # Language Localization: Translate Headlines
    translated_headlines = [
        (news_chain.translate_text(headline, target_language=user_language), link)
        for headline, link in global_headlines
    ]
    
    st.subheader(f"Headlines in {user_language.upper()}:")
    for headline, link in translated_headlines:
        st.markdown(f"- [{headline}]({link})")

    # Interactive News Map
    geo_data = pd.DataFrame({
        'Country': ['US', 'UK', 'India', 'Australia'], 
        'Trending Topic': ['AI Advancements', 'Elections', 'Sports Events', 'Climate Action']
    })

    fig = px.choropleth(
        geo_data, 
        locations='Country', 
        locationmode='country names', 
        color='Trending Topic', 
        title="Global Trending Topics"
    )
    st.plotly_chart(fig)

    # Export Content to PDF
    if st.button("Export as PDF"):
        file_path = generate_pdf(global_headlines)
        st.download_button(label="Download PDF", data=open(file_path, "rb").read(), file_name="news_summary.pdf")

    # Track User Engagement: Points for Liking an Article
    if "points" not in st.session_state:
        st.session_state.points = 0

    st.session_state.points += st.button("Like an Article") * 10
    st.sidebar.write(f"🎉 Your Points: {st.session_state.points}")

    if st.session_state.points >= 100:
        st.sidebar.markdown("**Congratulations! You've earned a reward badge!** 🏆")

    # Real-Time News Updates
    if st.button("Start Live Updates"):
        news_chain.fetch_live_news()

# Initialize the NewsChain
news_chain = NewsChain()

# Run the Streamlit App
create_streamlit_app(news_chain)
