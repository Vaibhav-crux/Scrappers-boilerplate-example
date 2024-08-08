from fastapi import APIRouter
import aiohttp
from datetime import datetime
import asyncio
from utils.utils import fetch_sitemap, fetch_page_content, create_article, log_article_counts, headers
from config.loggers import logger  

router = APIRouter()

# Define an endpoint to scrape articles from Forbes' sitemap
@router.get("/forbesScrapped")
async def forbes_scrapped():
    sitemap_url = 'https://www.forbes.com/news_sitemap.xml'  # Sitemap URL for Forbes
    articles = []  # List to hold the articles
    complete_count = 0  # Counter for successfully fetched articles
    incomplete_count = 0  # Counter for articles with missing data

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            soup = await fetch_sitemap(session, sitemap_url)
            if soup:
                url_tags = soup.find_all('url')  # Extract all URL tags from the sitemap
                current_date = datetime.now().strftime('%Y-%m-%d')  # Get today's date

                # Create a list of tasks to fetch articles concurrently
                tasks = [fetch_and_parse_article(session, url_tag, current_date) for url_tag in url_tags]
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
async def fetch_and_parse_article(session, url_tag, current_date):
    try:
        loc_tag = url_tag.find('loc')  # Find the location tag
        lastmod_tag = url_tag.find('lastmod')  # Find the last modification date tag
        news_title_tag = url_tag.find('news:title')  # Find the news title tag

        if loc_tag and lastmod_tag and news_title_tag:
            # Check if the article was modified today
            lastmod_date = datetime.strptime(lastmod_tag.text, "%Y-%m-%dT%H:%M:%SZ").strftime('%Y-%m-%d')
            if lastmod_date == current_date:
                page_soup = await fetch_page_content(session, loc_tag.text)  # Fetch the page content
                if page_soup:
                    title, author_name, content = extract_forbes_details(page_soup, news_title_tag)  # Extract article details

                    # Ensure all required details are present before creating the article
                    if title and content and author_name:
                        return create_article(title, loc_tag.text, author_name, content, "Forbes")
                    else:
                        log_incomplete_article(loc_tag.text, title, content, author_name)  # Log any incomplete articles
                        return None
    except Exception as e:
        logger.error(f"Error fetching article: {e}")  # Log any errors encountered while fetching the article
        return None

# Function to extract article details from the page content
def extract_forbes_details(page_soup, news_title_tag):
    # Extract title
    title = news_title_tag.text if news_title_tag else None

    # Extract author name
    author_tag = page_soup.find('a', class_='contrib-link--name remove-underline author-name--tracking not-premium-contrib-link--name')
    author_name = author_tag.text if author_tag else None

    # Extract article content
    article_div = page_soup.find('div', class_='article-body fs-article fs-responsive-text current-article')
    content = " ".join([p.get_text() for p in article_div.find_all('p')]) if article_div else None

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
