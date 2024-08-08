from fastapi import APIRouter
import aiohttp
from datetime import datetime, timedelta
import asyncio
from utils.utils import fetch_sitemap, fetch_page_content, create_article, log_article_counts, headers
from config.loggers import logger

router = APIRouter()

# Define an endpoint to scrape articles from CryptoPotato's sitemap
@router.get("/cryptoPotatoScrapped")
async def crypto_potato_scrapped():
    sitemap_url = 'https://cryptopotato.com/post-sitemap34.xml'  # Sitemap URL for CryptoPotato
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
        loc_tag = url_tag.find('loc')  # Find the location tag
        date_tag = url_tag.find('lastmod')  # Find the last modification date tag
        if date_tag:
            date_only = date_tag.text.split('T')[0]
            # Check if the article was modified today or yesterday
            if date_only == today or date_only == yesterday:
                page_soup = await fetch_page_content(session, loc_tag.text)  # Fetch the page content
                if page_soup:
                    title, author, content_text = extract_crypto_potato_details(page_soup)  # Extract article details

                    # Ensure all required details are present before creating the article
                    if title and content_text and author:
                        return create_article(title, loc_tag.text, author, content_text, "CryptoPotato")
                    else:
                        log_incomplete_article(loc_tag.text, title, content_text, author)  # Log any incomplete articles
                        return None
    except Exception as e:
        logger.error(f"Error fetching article: {e}")  # Log any errors encountered while fetching the article
        return None

# Function to extract article details from the page content
def extract_crypto_potato_details(page_soup):
    # Extracting the title
    title_div = page_soup.find('div', class_='page-title')
    title = title_div.find('h1').text.strip() if title_div else None

    # Extracting the author
    author_span = page_soup.find('span', class_='entry-user')
    author_link = author_span.find('a', class_='fn') if author_span else None
    author = author_link.text.strip() if author_link else None

    # Extracting the content
    content_div = page_soup.find('div', class_='coincodex-content')
    paragraphs = content_div.find_all('p') if content_div else []
    content_text = "\n".join([p.text for p in paragraphs])

    return title, author, content_text  # Return extracted details

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
