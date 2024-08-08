from fastapi import APIRouter
import aiohttp
from datetime import datetime, timedelta
import uuid
import asyncio
from utils.utils import fetch_sitemap, fetch_page_content, create_article, log_article_counts, headers
from config.loggers import logger

router = APIRouter()

# Define an endpoint to scrape articles from CoinDesk's sitemap
@router.get("/coinDeskScrapped")
async def coin_desk_scrapped():
    sitemap_url = 'https://www.coindesk.com/arc/outboundfeeds/news-sitemap-index/?outputType=xml'  # Sitemap URL for CoinDesk
    articles = []  # List to hold the articles
    complete_count = 0  # Counter for successfully fetched articles
    incomplete_count = 0  # Counter for articles with missing data

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            soup = await fetch_sitemap(session, sitemap_url)
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

# Asynchronous function to fetch and parse individual articles
async def fetch_and_parse_article(session, url_tag, today, yesterday):
    try:
        # Check if the article is in English
        if not is_article_language_english(url_tag):
            return None

        loc_tag = url_tag.find('loc')  # Find the location tag
        # Check if the article was published today or yesterday
        if not is_article_published_today_or_yesterday(url_tag, today, yesterday):
            return None

        page_soup = await fetch_page_content(session, loc_tag.text)  # Fetch the page content
        if page_soup:
            title, author_name, content = extract_coin_desk_details(page_soup)  # Extract article details

            # Ensure all required details are present before creating the article
            if title and content and author_name:
                return create_article(title, loc_tag.text, author_name, content, "Coin Desk")
            else:
                log_incomplete_article(loc_tag.text, title, content, author_name)  # Log any incomplete articles
                return None
    except Exception as e:
        logger.error(f"Error fetching article: {e}")  # Log any errors encountered while fetching the article
        return None

# Function to check if the article language is English
def is_article_language_english(url_tag):
    language_tag = url_tag.find('news:language')
    return not (language_tag and language_tag.text != 'en')

# Function to check if the article was published today or yesterday
def is_article_published_today_or_yesterday(url_tag, today, yesterday):
    date_tag = url_tag.find('lastmod')
    if date_tag:
        date_only = date_tag.text.split('T')[0]
        return date_only == today or date_only == yesterday
    return False

# Function to extract article details from the page content
def extract_coin_desk_details(page_soup):
    # Extract title
    title_tag = page_soup.find('h1', class_='typography__StyledTypography-sc-owin6q-0 kbFhjp')
    title = title_tag.text if title_tag else None
    
    # Extract content
    section = page_soup.find('section', class_='at-body')
    content = "\n".join(p.text for p in section.find_all('p')) if section else None
    
    # Extract author name
    author_div = page_soup.find('div', class_='at-authors')
    author_name = author_div.find('a').text if author_div and author_div.find('a') else None

    return title, author_name, content  # Return extracted details

# Function to log incomplete articles with missing fields
def log_incomplete_article(url, title, content, author_name):
    missing_fields = []
    if not title:
        missing_fields.append("title")
    if not content:
        missing_fields.append("content")
    if not author_name:
        missing_fields.append("author_name")
    logger.warning(f"Incomplete article at {url} missing fields: {', '.join(missing_fields)}")
