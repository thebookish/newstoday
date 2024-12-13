import os
import requests
import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class FacebookPosts:
    def __init__(self):
        self.fb_access_token = os.getenv("FACEBOOK_ACCESS_TOKEN")  # Add your Facebook access token here
        self.fb_api_url = "https://graph.facebook.com/v16.0"

    def fetch_public_facebook_posts(self, page_id):
        """Fetches and returns public posts from a specific Facebook page using Graph API."""
        url = f"{self.fb_api_url}/{page_id}/posts?access_token={self.fb_access_token}"

        try:
            response = requests.get(url)
            response.raise_for_status()

            data = response.json()

            if "data" in data:
                posts = [post["message"] for post in data["data"] if "message" in post]
                if not posts:
                    raise Exception("No public posts found.")
                return posts
            else:
                raise Exception("Error fetching posts from the page.")
        except requests.RequestException as e:
            raise Exception(f"Error fetching public Facebook posts: {e}")

def create_streamlit_app(facebook_posts):
    st.title("📰 Trending News and Facebook Posts")

    # Tabs for different views
    tab1, tab2 = st.tabs(["Trending News", "Trending Facebook Posts"])

    # Tab for Trending Facebook Posts
    with tab2:
        st.header("Trending Facebook Posts")
        page_id = st.text_input("Enter a Facebook Page ID:", value="theinquestbd")  # Example page ID

        if st.button("Fetch Facebook Posts"):
            try:
                facebook_posts_list = facebook_posts.fetch_public_facebook_posts(page_id)
                st.subheader(f"Trending Posts from {page_id}:")
                for idx, post in enumerate(facebook_posts_list, 1):
                    st.write(f"{idx}. {post}")
            except Exception as e:
                st.error(f"An error occurred: {e}")

if __name__ == "__main__":
    # Create an instance of the FacebookPosts class
    facebook_posts = FacebookPosts()

    # Set Streamlit configuration
    st.set_page_config(layout="wide", page_title="Trending News & Posts", page_icon="📰")

    # Launch the Streamlit app
    create_streamlit_app(facebook_posts)
