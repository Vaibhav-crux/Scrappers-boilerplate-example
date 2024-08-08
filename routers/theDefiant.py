from fastapi import APIRouter
import aiohttp
from datetime import datetime, timedelta
import asyncio
from utils.utils import fetch_sitemap, fetch_page_content, create_article, log_article_counts, headers
from config.loggers import logger

router = APIRouter()

# Define an endpoint to scrape articles from The Defiant's sitemap
@router.get("/theDefiantScrapped")
async def the_defiant_scrapped():
    sitemap_url = "https://thedefiant.io/sitemap/post-sitemap.xml"  # Sitemap URL for The Defiant
    articles = []  # List to hold the articles
    complete_count = 0  # Counter for successfully fetched articles
    incomplete_count = 0  # Counter for articles with missing data

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            soup = await fetch_sitemap(session, sitemap_url)
            if soup:
                url_tags = soup.find_all('url')  # Extract all URL tags from the sitemap
                current_date = datetime.now().date()  # Get today's date
                one_day_before = current_date - timedelta(days=1)  # Get yesterday's date

                # Create a list of tasks to fetch articles concurrently
                tasks = [fetch_and_parse_article(session, url_tag, current_date, one_day_before) for url_tag in url_tags]
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
async def fetch_and_parse_article(session, url_tag, current_date, one_day_before):
    try:
        loc_tag = url_tag.find('loc')  # Find the location tag
        lastmod_tag = url_tag.find('lastmod')  # Find the last modification date tag
        if lastmod_tag:
            # Check if the article was modified today or yesterday
            lastmod_date = datetime.strptime(lastmod_tag.text, '%Y-%m-%d').date()
            if lastmod_date == current_date or lastmod_date == one_day_before:
                page_soup = await fetch_page_content(session, loc_tag.text)  # Fetch the page content
                if page_soup:
                    title, author, content_text = extract_the_defiant_details(page_soup)  # Extract article details

                    # Ensure all required details are present before creating the article
                    if title and content_text and author:
                        return create_article(title, loc_tag.text, author, content_text, "The Defiant")
                    else:
                        log_incomplete_article(loc_tag.text, title, content_text, author)  # Log any incomplete articles
                        return None
    except Exception as e:
        logger.error(f"Error fetching article: {e}")  # Log any errors encountered while fetching the article
        return None

# Function to extract article details from the page content
def extract_the_defiant_details(page_soup):
    # Extract title
    title_tag = page_soup.find('h1', class_="font-heading font-semibold text-default text-[24px] leading-[32px] md:text-[40px] md:leading-[48px] mb-1")
    title = title_tag.text if title_tag else None

    # Extract author
    author_tag = page_soup.find('a', class_="hover:text-primary-hover font-medium underline")
    author = author_tag.text if author_tag else None

    # Extract content
    content_div = page_soup.find('div', class_="prose font-heading marker:text-default prose-p:mb-4 prose-p:mt-0 prose-p:text-[#333] prose-p:text-base prose-a:text-[#0000FF] prose-ul:mb-2 prose-ul:mt-0 prose-li:m-0 prose-li:text-default prose-h2:text-[24px] prose-h2:font-bold prose-h2:leading-8 prose-h2:mt-6 prose-h2:mb-4 prose-h3:text-[20px] prose-h3:font-bold prose-h3:leading-8 prose-h4:text-[20px] prose-h4:font-bold prose-h4:leading-6 mt-7 mb-6")
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
