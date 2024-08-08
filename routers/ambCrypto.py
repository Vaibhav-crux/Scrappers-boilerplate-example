from fastapi import APIRouter
import aiohttp
from datetime import datetime
import asyncio
from utils.utils import fetch_sitemap, fetch_page_content, create_article, log_article_counts, headers
from config.loggers import logger

router = APIRouter()

# Define an endpoint to scrape articles from AMB Crypto's sitemap
@router.get("/ambcryptoScrapped")
async def ambcrypto_scrapped():
    sitemap_url = 'https://ambcrypto.com/post-sitemap32.xml'  # Sitemap URL for AMB Crypto
    articles = []  # List to hold the articles
    complete_count = 0  # Counter for successfully fetched articles
    incomplete_count = 0  # Counter for articles with missing data

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            soup = await fetch_sitemap(session, sitemap_url)
            if soup:
                url_tags = soup.find_all('url')  # Extract all URL tags from the sitemap
                today = datetime.now().strftime('%Y-%m-%d')  # Get today's date

                # Create a list of tasks to fetch articles concurrently
                tasks = [fetch_article(session, url_tag, today) for url_tag in url_tags]
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

# Asynchronous function to fetch and process individual articles
async def fetch_article(session, url_tag, today):
    try:
        # Extract the last modification date of the article
        lastmod_tag = url_tag.find('lastmod')
        lastmod_text = lastmod_tag.text
        date_obj = datetime.strptime(lastmod_text, "%Y-%m-%dT%H:%M:%S%z")
        formatted_date = date_obj.strftime("%B %d, %Y")

        # Check if the article was modified today
        if lastmod_tag and today in lastmod_tag.text:
            loc_tag = url_tag.find('loc')
            page_soup = await fetch_page_content(session, loc_tag.text)  # Fetch the page content
            if page_soup:
                title, author_name, content_text, img_url = extract_article_details(page_soup)  # Extract article details

                # Ensure all required details are present before creating the article
                if title and content_text and author_name:
                    article = create_article(title, loc_tag.text, author_name, content_text, "AMB Crypto")
                    article["metadata"]["articlePublishedOn"] = formatted_date
                    article["imageURI"] = img_url

                    return article  # Return the complete article
                else:
                    log_incomplete_article(loc_tag.text, title, content_text, author_name)  # Log any incomplete articles
                    return None
            else:
                logger.error(f"Failed to fetch page content for URL: {loc_tag.text}")
                return None
    except Exception as e:
        logger.error(f"Error fetching article: {e}")  # Log any errors encountered while fetching the article
        return None

# Function to extract article details from the page content
def extract_article_details(page_soup):
    author_tag = page_soup.find('div', class_='single-author-box-name')
    author_name = author_tag.find('span', class_='author-name').text.strip() if author_tag else None  # Extract author name

    title_tag = page_soup.find('h1', class_='post-title entry-title')
    title = title_tag.text.strip() if title_tag else None  # Extract article title

    img_tag = page_soup.find('div', class_='single-post-image')
    img_url = "Image URL not found"
    if img_tag:
        img_element = img_tag.find('img')
        if img_element:
            if 'data-src' in img_element.attrs:
                img_url = img_element['data-src']  # Get image URL from 'data-src' attribute
            elif 'data-lazy-src' in img_element.attrs:
                img_url = img_element['data-lazy-src']  # Get image URL from 'data-lazy-src' attribute
            else:
                img_url = img_element['src']  # Get image URL from 'src' attribute

    content_tags = page_soup.find('div', class_='single-post-main-middle').find_all('p')
    content_text = " ".join(p_tag.get_text(separator=" ", strip=True) for p_tag in content_tags)  # Extract article content

    return title, author_name, content_text, img_url  # Return extracted details

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
