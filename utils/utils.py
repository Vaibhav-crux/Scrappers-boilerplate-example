import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime
from config.loggers import logger  # Import the logger
import uuid

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

async def fetch_sitemap(session, sitemap_url):
    """Fetch the sitemap and return the BeautifulSoup object."""
    async with session.get(sitemap_url) as response:
        if response.status == 200:
            logger.info("Successfully fetched the sitemap.")
            return BeautifulSoup(await response.text(), 'lxml')
        else:
            logger.error(f"Error: Received status code {response.status} when trying to fetch the sitemap.")
            return None

async def fetch_page_content(session, url):
    """Fetch the page content and return the BeautifulSoup object."""
    async with session.get(url) as response:
        if response.status == 200:
            return BeautifulSoup(await response.text(), 'html.parser')
        else:
            logger.error(f"Failed to fetch page content for URL: {url}")
            return None

def create_article(title, link, author, content, source):
    """Create an article dictionary."""
    return {
        "articleId": str(uuid.uuid4()),
        "title": title if title else "Title not found",
        "link": link,
        "imageURI": "",
        "translatedArticles": {},
        "metadata": {
            "articleSource": source,
            "articleBaseUrl": link,
            "articleTimeStampExtracted": int(datetime.now().timestamp() * 1000000),
            "category": "",
            "articlePublishedOn": datetime.now().strftime('%d %B, %Y'),
            "tags": "",
            "articleMetrics": {
                "articleLiked": 20,
                "articleDisliked": 0,
            },
            "author": author if author else "Author not found",
            "articleLastUpdatedOn": "N/A"
        },
        "content": content if content else "Content not found"
    }

def log_article_counts(total_articles, complete_count, incomplete_count):
    """Log the counts of total, complete, and incomplete articles."""
    current_time = datetime.now().strftime("%H:%M:%S")  # Get the current time in hh:mm:ss format
    current_date_str = datetime.now().strftime('%Y-%m-%d')

    logger.info(f"totalArticlesExtracted: {total_articles}")
    logger.info(f"completeArticles: {complete_count}")
    logger.info(f"incompleteArticles: {incomplete_count}")
    logger.info(f"currentDate: {current_date_str}")
    logger.info(f"currentTime: {current_time}")
