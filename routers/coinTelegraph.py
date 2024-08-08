from fastapi import APIRouter
from bs4 import BeautifulSoup
import aiohttp
import asyncio
from utils.utils import fetch_page_content, create_article, log_article_counts, headers
from config.loggers import logger

router = APIRouter()

# Define an endpoint to scrape articles from CoinTelegraph's website
@router.get("/coinTelegraphScrapped")
async def coin_telegraph_scrapped():
    url = "https://cointelegraph.com/tags/cryptocurrencies"  # URL for CoinTelegraph's cryptocurrencies section
    articles = []  # List to hold the articles
    complete_count = 0  # Counter for successfully fetched articles
    incomplete_count = 0  # Counter for articles with missing data

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            page_content = await fetch_page_content(session, url)
            if page_content:
                soup = BeautifulSoup(page_content, 'html.parser')
                # Extract article links from the main page
                article_links = ["https://cointelegraph.com" + link["href"] for link in soup.find_all("a", class_="post-card-inline__title-link")]

                # Create a list of tasks to fetch articles concurrently
                tasks = [fetch_and_parse_article(session, article_link) for article_link in article_links]
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
                logger.error(f"Failed to fetch main page content for URL: {url}")
                return {"error": "Failed to fetch main page."}
    except Exception as e:
        logger.error(f"Error: {e}")  # Log any errors encountered during the process
        return {"error": str(e)}

# Asynchronous function to fetch and parse individual articles
async def fetch_and_parse_article(session, article_link):
    try:
        # Fetch the page content for an individual article
        page_content = await fetch_page_content(session, article_link)
        if page_content:
            title, author, content = extract_coin_telegraph_details(page_content)  # Extract article details

            # Ensure all required details are present before creating the article
            if title and content and author:
                return create_article(title, article_link, author, content, "Cointelegraph")
            else:
                log_incomplete_article(article_link, title, content, author)  # Log any incomplete articles
                return None
        else:
            logger.error(f"Failed to fetch page content for article URL: {article_link}")
            return None
    except Exception as e:
        logger.error(f"Error fetching article from {article_link}: {e}")  # Log any errors encountered while fetching the article
        return None

# Function to extract article details from the page content
def extract_coin_telegraph_details(page_content):
    soup = BeautifulSoup(page_content, 'html.parser')

    # Extract author name
    author_name_tag = soup.find("a", class_="post-card-inline__link")
    author_name = author_name_tag.text.strip() if author_name_tag else None

    # Extract title
    title_tag = soup.find("h1", class_="post__title")
    title = title_tag.text.strip() if title_tag else None

    # Extract content
    content_div = soup.find("div", class_="post-content")
    article_content = []
    if content_div:
        related_found = False
        for p in content_div.find_all("p"):
            if related_found:
                break
            if "Related:" in p.text:
                related_found = True
                continue
            article_content.append(p.text.strip())

    content = "\n".join(article_content)

    return title, author_name, content  # Return extracted details

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
