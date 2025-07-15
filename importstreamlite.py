import streamlit as st
import tweepy
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import pandas as pd
import plotly.express as px
from datetime import datetime
import time

# Set up the Streamlit app
st.set_page_config(page_title="Social Media Sentiment Dashboard", layout="wide")
st.title("📊 Social Media Sentiment Dashboard")
st.markdown("Real-time analysis of public sentiment on civic topics")

# Sidebar for configuration
with st.sidebar:
    st.header("Configuration")
    
    # Twitter API credentials (should use st.secrets in production)
    st.subheader("Twitter API Settings")
    api_key = st.text_input("API Key", type="password")
    api_secret = st.text_input("API Secret", type="password")
    access_token = st.text_input("Access Token", type="password")
    access_secret = st.text_input("Access Secret", type="password")
    
    # Search parameters
    st.subheader("Search Parameters")
    search_query = st.text_input("Search Query", "#civic OR #government OR #publicservice")
    tweet_count = st.slider("Number of Tweets", 10, 200, 50)
    refresh_rate = st.slider("Refresh Rate (seconds)", 10, 300, 60)
    
    # Location filter
    st.subheader("Location Filter")
    use_location = st.checkbox("Filter by Location")
    if use_location:
        latitude = st.number_input("Latitude", value=40.7128)
        longitude = st.number_input("Longitude", value=-74.0060)
        radius = st.number_input("Radius (km)", value=50)
    
    # Admin controls
    st.subheader("Admin Controls")
    if st.button("Clear Cache"):
        st.cache_data.clear()

# Initialize sentiment analyzer
analyzer = SentimentIntensityAnalyzer()

# Function to authenticate with Twitter API
def authenticate_twitter(api_key, api_secret, access_token, access_secret):
    try:
        auth = tweepy.OAuthHandler(api_key, api_secret)
        auth.set_access_token(access_token, access_secret)
        return tweepy.API(auth)
    except Exception as e:
        st.error(f"Authentication failed: {e}")
        return None

# Function to fetch tweets
@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_tweets(api, query, count, location=None):
    try:
        if location:
            geocode = f"{location['latitude']},{location['longitude']},{location['radius']}km"
            tweets = tweepy.Cursor(api.search_tweets, q=query, tweet_mode='extended', geocode=geocode).items(count)
        else:
            tweets = tweepy.Cursor(api.search_tweets, q=query, tweet_mode='extended').items(count)
        
        tweet_data = []
        for tweet in tweets:
            sentiment = analyzer.polarity_scores(tweet.full_text)
            tweet_data.append({
                'text': tweet.full_text,
                'user': tweet.user.screen_name,
                'location': tweet.user.location,
                'created_at': tweet.created_at,
                'retweets': tweet.retweet_count,
                'favorites': tweet.favorite_count,
                'sentiment': sentiment['compound'],
                'sentiment_label': 'positive' if sentiment['compound'] >= 0.05 else 'negative' if sentiment['compound'] <= -0.05 else 'neutral'
            })
        return pd.DataFrame(tweet_data)
    except Exception as e:
        st.error(f"Error fetching tweets: {e}")
        return pd.DataFrame()

# Function to generate sentiment summary
def generate_summary(df):
    if df.empty:
        return None
    
    summary = {
        'total_tweets': len(df),
        'positive': len(df[df['sentiment_label'] == 'positive']),
        'neutral': len(df[df['sentiment_label'] == 'neutral']),
        'negative': len(df[df['sentiment_label'] == 'negative']),
        'avg_sentiment': df['sentiment'].mean()
    }
    return summary

# Main dashboard
if api_key and api_secret and access_token and access_secret:
    api = authenticate_twitter(api_key, api_secret, access_token, access_secret)
    
    if api:
        location = None
        if use_location:
            location = {'latitude': latitude, 'longitude': longitude, 'radius': radius}
        
        # Create a placeholder for the live updates
        placeholder = st.empty()
        
        while True:
            with placeholder.container():
                st.subheader(f"Real-time Analysis for: '{search_query}'")
                if location:
                    st.caption(f"Location: {location['latitude']}, {location['longitude']} (Radius: {location['radius']}km)")
                
                # Fetch tweets
                tweets_df = fetch_tweets(api, search_query, tweet_count, location)
                
                if not tweets_df.empty:
                    # Generate summary
                    summary = generate_summary(tweets_df)
                    
                    # Display summary metrics
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Total Tweets", summary['total_tweets'])
                    col2.metric("Positive Sentiment", summary['positive'], f"{summary['positive']/summary['total_tweets']*100:.1f}%")
                    col3.metric("Neutral Sentiment", summary['neutral'], f"{summary['neutral']/summary['total_tweets']*100:.1f}%")
                    col4.metric("Negative Sentiment", summary['negative'], f"{summary['negative']/summary['total_tweets']*100:.1f}%")
                    
                    # Sentiment distribution chart
                    st.subheader("Sentiment Distribution")
                    fig1 = px.pie(tweets_df, names='sentiment_label', title='Sentiment Breakdown')
                    st.plotly_chart(fig1, use_container_width=True)
                    
                    # Sentiment over time
                    st.subheader("Sentiment Over Time")
                    tweets_df['time'] = tweets_df['created_at'].dt.strftime('%H:%M')
                    fig2 = px.scatter(tweets_df, x='time', y='sentiment', color='sentiment_label',
                                     title='Sentiment by Time', hover_data=['text'])
                    st.plotly_chart(fig2, use_container_width=True)
                    
                    # Raw data table
                    st.subheader("Recent Tweets")
                    st.dataframe(tweets_df[['created_at', 'user', 'location', 'text', 'sentiment_label']].sort_values('created_at', ascending=False))
                
                else:
                    st.warning("No tweets found matching your criteria.")
                
                # Admin section
                with st.expander("Admin Monitoring"):
                    st.subheader("System Status")
                    st.write(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    if not tweets_df.empty:
                        st.download_button(
                            label="Download Data",
                            data=tweets_df.to_csv().encode('utf-8'),
                            file_name=f"sentiment_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime='text/csv'
                        )
                
                # Add a refresh countdown
                st.write(f"Refreshing in {refresh_rate} seconds...")
                time.sleep(refresh_rate)
                st.experimental_rerun()
    else:
        st.warning("Please enter valid Twitter API credentials to proceed.")
else:
    st.info("Please enter your Twitter API credentials in the sidebar to begin.")