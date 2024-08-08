from fastapi import APIRouter
import aiohttp
from datetime import datetime, timedelta
import uuid
import asyncio
from utils.utils import fetch_sitemap, fetch_page_content, create_article, log_article_counts
from config.loggers import logger
from bs4 import BeautifulSoup

router = APIRouter()

# Update User-Agent to a more recent version
new_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

# Define an endpoint to scrape articles from BeinCrypto's sitemap
@router.get("/beinCryptoScrapped")
async def bein_crypto_scrapped():
    sitemap_url = 'https://beincrypto.com/wp-content/uploads/beincrypto-sitemaps/sitemap_index/news/sitemap.xml'
    articles = []  # List to hold the articles
    complete_count = 0  # Counter for successfully fetched articles
    incomplete_count = 0  # Counter for articles with missing data

    try:
        async with aiohttp.ClientSession(headers=new_headers) as session:
            soup = await fetch_sitemap_with_logging(session, sitemap_url)
            if soup:
                url_tags = soup.find_all('url')  # Extract all URL tags from the sitemap
                today = datetime.now().strftime('%Y-%m-%d')  # Get today's date
                yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')  # Get yesterday's date

                # Create a list of tasks to fetch articles concurrently
                tasks = [fetch_and_parse_article(session, url_tag, today, yesterday) for url_tag in url_tags]
                results = await asyncio.gather(*tasks)  # Execute all tasks concurrently

                # Process the results of the fetched articles
                for result in results:
                    if result:
                        articles.append(result)  # Add successful articles to the list
                        complete_count += 1  # Increment the complete count
                    else:
                        incomplete_count += 1  # Increment the incomplete count

                total_articles = len(articles)  # Get the total number of articles fetched

                # Log the counts of articles
                log_article_counts(total_articles, complete_count, incomplete_count)

                return articles  # Return the list of articles
            else:
                return {"error": "Failed to fetch sitemap."}
    except Exception as e:
        logger.error(f"Error: {e}")  # Log any errors encountered during the process
        return {"error": str(e)}

# Function to fetch the sitemap with detailed logging
async def fetch_sitemap_with_logging(session, sitemap_url):
    """Fetch the sitemap and return the BeautifulSoup object with detailed logging."""
    async with session.get(sitemap_url) as response:
        logger.info(f"Fetching sitemap from {sitemap_url}")
        logger.info(f"Response status code: {response.status}")
        logger.info(f"Response headers: {response.headers}")
        if response.status == 200:
            logger.info("Successfully fetched the sitemap.")
            return BeautifulSoup(await response.text(), 'lxml')
        else:
            logger.error(f"Error: Received status code {response.status} when trying to fetch the sitemap.")
            return None

# Asynchronous function to fetch and parse individual articles
async def fetch_and_parse_article(session, url_tag, today, yesterday):
    try:
        loc_tag = url_tag.find('loc')  # Find the location tag
        date_tag = url_tag.find('news:publication_date')  # Find the publication date tag
        if date_tag:
            date_only = date_tag.text.split('T')[0]
            # Check if the article was published today or yesterday
            if date_only == today or date_only == yesterday:
                await asyncio.sleep(1)  # Add a delay between requests
                page_soup = await fetch_page_content(session, loc_tag.text)  # Fetch the page content
                if page_soup:
                    title, author, content = extract_bein_crypto_details(page_soup)  # Extract article details

                    # Ensure all required details are present before creating the article
                    if title and content and author:
                        return create_article(title, loc_tag.text, author, content, "BeinCrypto")
                    else:
                        log_incomplete_article(loc_tag.text, title, content, author)  # Log any incomplete articles
                        return None
    except Exception as e:
        logger.error(f"Error fetching article: {e}")  # Log any errors encountered while fetching the article
        return None

# Function to extract article details from the page content
def extract_bein_crypto_details(page_soup):
    # Extract title
    title_tag = page_soup.find('h1', class_="h4 lg:h1 mt-3 mb-2 lg:mb-3 w-full")
    title = title_tag.text.strip() if title_tag else None

    # Extract author
    author_tag = page_soup.find('span', class_="text-blue-700 no-underline text-3")
    author = author_tag.text if author_tag else None

    # Extract content
    paragraphs = page_soup.find_all('p')
    content = ""
    for paragraph in paragraphs:
        # Check if the paragraph is inside specific unwanted parent elements
        parent_div = paragraph.find_parent('div', class_="p-5 mt-6 rounded-lg border border-grey-200")
        contains_strong = paragraph.find('strong') is not None
        inside_want_to_know_more_block = paragraph.find_parent('div', class_="want-to-know-more-block__inner") is not None
        inside_footer = paragraph.find_parent('footer', class_="px-6 pt-10 pb-10 mt-10 lg:mt-12 rounded-2xl lg:pt-11 lg:pb-15 lg:px-12 bg-grey-100 [.dark_&]:bg-dark-grey-500") is not None
        if parent_div is None and not contains_strong and not inside_want_to_know_more_block and not inside_footer:
            content += paragraph.get_text(strip=True) + "\n"

    return title, author, content  # Return extracted details

# Function to log incomplete articles with missing fields
def log_incomplete_article(url, title, content, author):
    missing_fields = []
    if not title:
        missing_fields.append("title")
    if not content:
        missing_fields.append("content")
    if not author:
        missing_fields.append("author")
    logger.warning(f"Incomplete article at {url} missing fields: {', '.join(missing_fields)}")
