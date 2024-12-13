import os
import requests
from bs4 import BeautifulSoup
import tweepy
import streamlit as st
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate


# Load environment variables
load_dotenv()

# Replace the following strings with your own keys and tokens
API_KEY = os.getenv('TWITTER_API_KEY')
API_SECRET_KEY = os.getenv('TWITTER_API_SECRET_KEY')
BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')  # v2 Bearer Token

# Authenticate to Twitter using v2 Bearer token
client = tweepy.Client(bearer_token=BEARER_TOKEN)


class NewsChain:
    def __init__(self):
        # Initialize LLM (Large Language Model)
        self.llm = ChatGroq(
            temperature=0,
            groq_api_key=os.getenv("GROQ_API_KEY"),
            model_name="llama-3.1-70b-versatile"
        )
        self.news_api_key = os.getenv("NEWS_API_KEY")  # Add your NewsAPI key here

    def fetch_news_headlines(self, url):
        """Fetches and returns news headlines along with links from the given website URL."""
        try:
            response = requests.get(url)
            response.raise_for_status()
        except requests.RequestException as e:
            raise Exception(f"Error fetching the news: {e}")

        soup = BeautifulSoup(response.text, 'html.parser')

        # Adjust selectors based on the structure of the site
        headlines_with_links = []

        # Try finding common headline classes (tailor this to each site later)
        headline_selectors = ['h1 a', 'h2 a', 'h3 a', '.headline a', '.news-title a', '.entry-title a', '.post-title a']

        for selector in headline_selectors:
            for tag in soup.select(selector):
                text = tag.get_text(strip=True)
                link = tag.get('href', '#')  # Get the href attribute, use '#' as fallback if missing
                if text:
                    # Ensure the link is absolute
                    absolute_link = requests.compat.urljoin(url, link)
                    headlines_with_links.append((text, absolute_link))

        if not headlines_with_links:
            raise Exception("No headlines found. Ensure the website structure is correct.")

        return headlines_with_links

    def fetch_global_trending_news(self):
        """Fetches global trending news using the NewsAPI."""
        url = f'https://newsapi.org/v2/top-headlines?country=us&apiKey={self.news_api_key}'  # Modify the country code if needed
        try:
            response = requests.get(url)
            response.raise_for_status()

            data = response.json()

            if data.get("status") == "ok":
                articles = data.get('articles', [])
                if not articles:
                    raise Exception("No global trending news found.")
                # Return a list of tuples with title and URL
                return [(article['title'], article.get('url', '#')) for article in articles]
            else:
                raise Exception("Error fetching global trending news.")
        except requests.RequestException as e:
            raise Exception(f"Error fetching global trending news: {e}")

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

    def get_trending_tweets(self, query="trending", max_results=10):
        """Fetch trending tweets based on a query."""
        try:
            # Using the v2 search endpoint to fetch tweets related to the trending keyword
            response = client.search_recent_tweets(query=query, max_results=max_results, tweet_fields=["public_metrics", "created_at"])
            tweets = []

            for tweet in response.data:
                tweets.append({
                    "text": tweet.text,
                    "id": tweet.id,
                    "likes": tweet.public_metrics["like_count"],
                    "retweets": tweet.public_metrics["retweet_count"],
                })

            return tweets
        except Exception as e:
            st.error(f"An error occurred: {e}")
            return []


def create_streamlit_app(news_chain):
    st.title("📰 Trending News Portal")

    # Create tabs for different news categories
    tabs = st.tabs(["Global Trending News", "Portal Based News", "📈 Twitter Trending Topics", "Technology News"])

    # Global Trending News Tab
    with tabs[0]:
        if st.button("Fetch Global Trending News"):
            try:
                global_headlines = news_chain.fetch_global_trending_news()
                st.subheader("Global Trending News:")
                for idx, (headline, link) in enumerate(global_headlines, 1):
                    st.markdown(f"{idx}. [{headline}]({link})")  # Display headline as a hyperlink
            except Exception as e:
                st.error(f"An error occurred: {e}")

    # Local News Tab
    with tabs[1]:
        st.subheader("📍 Local News")
        st.title("📰 News Headlines Generator")

        # Input URL for the news website or Facebook page
        url_input = st.text_input("Enter a News Website URL:", value="https://www.yourwebsite.com/")
        fetch_button = st.button("Fetch Headlines")

        if fetch_button:
            try:
                # Fetch headlines from a news website
                headlines = news_chain.fetch_news_headlines(url_input)

                st.subheader("Fetched Headlines:")
                for idx, headline in enumerate(headlines, 1):
                    st.write(f"{idx}. {headline}")

                # Store headlines in session state
                st.session_state.headlines = headlines
            except Exception as e:
                st.write(f"Something went wrong: {e}")

    # Sports News Tab
    with tabs[2]:
        st.title("📈 Twitter Trending Topics")

        st.sidebar.header("Trending Topic Search")
        query = st.sidebar.text_input("Enter a keyword/hashtag for trending", value="trending")

        # Fetch and display tweets based on the search query
        if st.button("Get Trending Tweets"):
            trending_tweets = news_chain.get_trending_tweets(query=query)

            if trending_tweets:
                st.subheader(f"Trending Tweets about: '{query}'")
                for idx, tweet in enumerate(trending_tweets, 1):
                    tweet_url = f"https://twitter.com/i/web/status/{tweet['id']}"
                    st.markdown(f"{idx}. [**{tweet['text']}**]({tweet_url})")
                    st.write(f"👍 Likes: {tweet['likes']} | 🔁 Retweets: {tweet['retweets']}")
            else:
                st.warning("No trending tweets found.")

    # Technology News Tab (Placeholder)
    with tabs[3]:
        st.subheader("💻 Technology News")
        st.write("This section is under construction.")


if __name__ == "__main__":
    # Create an instance of the NewsChain class
    news_chain = NewsChain()

    # Set Streamlit configuration
    st.set_page_config(layout="wide", page_title="Trending News Portal", page_icon="📰")

    # Launch the Streamlit app
    create_streamlit_app(news_chain)
