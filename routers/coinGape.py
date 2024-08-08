from fastapi import APIRouter
import aiohttp
from datetime import datetime, timedelta
import re
import asyncio
from utils.utils import fetch_sitemap, fetch_page_content, create_article, log_article_counts, headers
from config.loggers import logger  

router = APIRouter()

# Define an endpoint to scrape articles from CoinGape's sitemap
@router.get("/coinGapeScrapped")
async def coin_gape_scrapped():
    sitemap_url = 'https://coingape.com/news-sitemap.xml'  # Sitemap URL for CoinGape
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
        date_tag = url_tag.find('news:publication_date')  # Find the publication date tag
        if date_tag:
            date_only = date_tag.text.split('T')[0]
            # Check if the article was published today or yesterday
            if date_only == today or date_only == yesterday:
                page_soup = await fetch_page_content(session, loc_tag.text)  # Fetch the page content
                if page_soup:
                    title, author_name, content = extract_coin_gape_details(page_soup)  # Extract article details
                    # Ensure all required details are present before creating the article
                    if title and content and author_name:
                        return create_article(title, loc_tag.text, author_name, content, "CoinGape")
                    else:
                        log_incomplete_article(loc_tag.text, title, content, author_name)  # Log any incomplete articles
                        return None
    except Exception as e:
        logger.error(f"Error fetching article: {e}")  # Log any errors encountered while fetching the article
        return None

# Function to extract article details from the page content
def extract_coin_gape_details(page_soup):
    # Extract breadcrumb and author
    breadcrumb = page_soup.find('div', class_='breadcrumb breadcrumbPag mt-lg-0 mt-3')
    author_span = page_soup.find('span', class_='auth-name')

    # Extract title and author
    title = breadcrumb.find('span', class_='breadcrumb_last').text if breadcrumb else None
    author_name = author_span.text.strip() if author_span else None

    # Extract and filter content paragraphs
    paragraphs = page_soup.find_all('p')
    filtered_paragraphs = [p for p in paragraphs if not p.find_parent('div', class_='footer-tags-container')]
    content = ' '.join([p.get_text(strip=True) for p in filtered_paragraphs])
    content = clean_content(content)  # Clean the content from unwanted text

    return title, author_name, content

# Function to clean unwanted text from the content
def clean_content(content):
    content = re.sub(r'News Markets Cryptoguru Collection Contact Follow us on:', '', content, flags=re.IGNORECASE)
    content = re.sub(r'DAILY NEWSLETTER Your daily dose of Crypto news, Prices & other updates\.\.', '', content, flags=re.IGNORECASE)
    content = re.sub(r'TRENDING TODAY', '', content, flags=re.IGNORECASE)
    content = re.sub(r'Top News Cryptocurrency Prices Popular Coingape Academy Blogs Popular Categories Exclusive Contact Exclusive Contact Close', '', content, flags=re.IGNORECASE)
    content = re.sub(r'Exclusive Contact Close', '', content, flags=re.IGNORECASE)
    return content

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
