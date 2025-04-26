import asyncio
import logging
import os
from typing import Dict, List, Optional
from googlesearch import search
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def should_skip_url(url: str) -> bool:
    """Check if URL should be skipped (e.g., PDFs, documents, etc.)"""
    # Skip common document formats
    skip_extensions = [
        '.pdf', '.doc', '.docx', '.ppt', '.pptx', 
        '.xls', '.xlsx', '.csv', '.zip', '.rar'
    ]
    
    # Skip URLs from document hosting sites
    skip_domains = [
        'docs.google.com',
        'drive.google.com',
        'dropbox.com',
        'box.com'
    ]
    
    parsed_url = urlparse(url.lower())
    
    # Check file extension
    path = parsed_url.path
    if any(path.endswith(ext) for ext in skip_extensions):
        logger.info(f"Skipping document URL: {url}")
        return True
        
    # Check domain
    domain = parsed_url.netloc
    if any(skip_domain in domain for skip_domain in skip_domains):
        logger.info(f"Skipping document hosting site: {url}")
        return True
        
    return False

async def fetch_url_content(url: str) -> Optional[str]:
    """Fetch and extract text content from a URL."""
    try:
        # Skip if URL is a document
        if should_skip_url(url):
            return None
            
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    # Check content type
                    content_type = response.headers.get('Content-Type', '').lower()
                    if 'text/html' not in content_type:
                        logger.info(f"Skipping non-HTML content ({content_type}): {url}")
                        return None
                        
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Remove script and style elements
                    for script in soup(["script", "style"]):
                        script.decompose()
                        
                    # Get text and clean it up
                    text = soup.get_text()
                    lines = (line.strip() for line in text.splitlines())
                    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                    text = ' '.join(chunk for chunk in chunks if chunk)
                    
                    return text[:1000]  # Return first 1000 chars
    except Exception as e:
        logger.error(f"Error fetching {url}: {str(e)}")
    return None

async def search_entity(entity_name: str) -> List[Dict[str, str]]:
    """Perform Google searches for the entity using multiple queries."""
    search_queries = [
        f'"{entity_name}" company profile renewable energy',
        f'"{entity_name}" recent news financial performance',
        f'"{entity_name}" reputation issues OR lawsuits',
    ]
    
    all_results = []
    for query in search_queries:
        try:
            logger.info(f"Searching for query: {query}")
            # Get top 3 results for each query
            # search() returns an iterator, so we need to use list() to get all results
            urls = list(search(query, stop=3))  # stop parameter limits number of results
            logger.info(f"Found {len(urls)} URLs for query: {query}")
            
            # Fetch content from each URL
            for url in urls:
                logger.info(f"Fetching content from: {url}")
                content = await fetch_url_content(url)
                if content:
                    all_results.append({
                        'url': url,
                        'content': content
                    })
                    
            # Add delay between searches to avoid rate limiting
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"Error searching for {query}: {str(e)}")
            continue
    
    return all_results

async def test_search():
    """Test the search functionality."""
    try:
        # Test companies
        test_companies = [
            "Orsted",  # Major renewable energy company
            "EDF Energy Renewables Limited",  # Your actual example
            "NextEra Energy"  # Another well-known renewable company
        ]
        
        for company in test_companies:
            logger.info(f"\n=== Testing search for {company} ===")
            
            # Test search and content fetching
            search_results = await search_entity(company)
            logger.info(f"Found {len(search_results)} total results")
            
            # Log results
            for i, result in enumerate(search_results, 1):
                logger.info(f"\nResult {i}:")
                logger.info(f"URL: {result['url']}")
                logger.info(f"Content preview: {result['content'][:200]}...")
            
            logger.info("=== Test complete ===\n")
            
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)

if __name__ == "__main__":
    logger.info("Starting search functionality test")
    asyncio.run(test_search())
    logger.info("Test complete") 