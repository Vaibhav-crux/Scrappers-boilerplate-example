from fastapi import APIRouter
import aiohttp
from datetime import datetime, timedelta
import asyncio
from utils.utils import fetch_sitemap, fetch_page_content, create_article, log_article_counts, headers
from config.loggers import logger 

router = APIRouter()

# Define an endpoint to scrape articles from Blockworks's sitemap
@router.get("/blockWorksScrapped")
async def block_works_scrapped():
    sitemap_url = 'https://blockworks.co/news-sitemap/1'  # Sitemap URL for Blockworks
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
                    title, author, content = extract_block_works_details(page_soup)  # Extract article details

                    # Ensure all required details are present before creating the article
                    if title and content and author:
                        return create_article(title, loc_tag.text, author, content, "Blockworks")
                    else:
                        log_incomplete_article(loc_tag.text, title, content, author)  # Log any incomplete articles
                        return None
    except Exception as e:
        logger.error(f"Error fetching article: {e}")  # Log any errors encountered while fetching the article
        return None

# Function to extract article details from the page content
def extract_block_works_details(page_soup):
    # Extract title
    title_tag = page_soup.find('h1', class_="self-stretch flex-grow-0 flex-shrink-0 text-xl md:text-3xl lg:text-4xl xl:text-5xl font-headline text-left text-dark")
    title = title_tag.text if title_tag else None

    # Extract author
    author_div = page_soup.find('div', class_="flex flex-wrap gap-1 uppercase")
    author = author_div.find('a').text if author_div else None

    # Extract content
    div_section = page_soup.find('div', class_="p-2 basis-4/4 xl:basis-3/4")
    section = div_section.find('section', class_="w-full") if div_section else None
    paragraphs = section.find_all('p') if section else []
    content = ""
    for index, p in enumerate(paragraphs):
        # Skip specific unwanted text
        if "Don’t miss the next big story" in p.text:
            if index == len(paragraphs) - 1:
                continue
        content += p.text + "\n"

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
