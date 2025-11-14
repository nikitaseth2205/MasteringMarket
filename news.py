import streamlit as st
import feedparser

def show_news():
    st.title("Market News and Current Affairs")
    st.write("This section provides the latest news and current affairs related to the stock market and economy.")
    def get_top_headlines(feed_url):
        feed = feedparser.parse(feed_url)
        return [entry.title for entry in feed.entries[:10]]

    headlines = get_top_headlines("https://www.livemint.com/rss/markets")

    news_title = ""
    for headline in headlines:
        news_title += f"  🔴 {headline}"
    st.markdown(
     f"""
     <div style="background-color:transparent; color:black; padding: 10px; border-radius: 5px; overflow: hidden;">
         <marquee behavior="scroll" direction="left" scrollamount="6" style="font-size: 20px;">
             {news_title }
         </marquee>
     </div>
     """,
     unsafe_allow_html=True
    )
    st.write("---" *20)
    # List of RSS feed URLs for news

    urls = [
    "https://www.moneycontrol.com/rss/markets.xml",
    "https://www.business-standard.com/rss/markets-5.rss",
    "https://www.livemint.com/rss/markets",
    ]

    for url in urls:
        print(f"Fetching news from: {url}")

        feed = feedparser.parse(url)
        flag = 0
        for entry in feed.entries:
            flag += 1
            st.subheader(f"**News {flag}: {entry.title}**")
            if 'media_content' in entry:
                st.image(entry.media_content[0]['url'])
            else:
                st.write("No Image Available")

            st.write(f"**Link:** {entry.link}")
            st.write (f"**Published:** {entry.published}")
            st.write(f"**Summary:** {entry.summary}")

            st.write("-----" *20)
