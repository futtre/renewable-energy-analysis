from typing import Dict, List, Optional
import os
from googlesearch import search
import anthropic
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ExternalInfoFetcher:
    def __init__(self):
        load_dotenv()
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.anthropic_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
        
        self.client = anthropic.Anthropic(api_key=self.anthropic_key)

    def should_skip_url(self, url: str) -> bool:
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

    async def _fetch_url_content(self, url: str) -> Optional[str]:
        """Fetch and extract text content from a URL."""
        try:
            # Skip if URL is a document
            if self.should_skip_url(url):
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

    async def _search_entity(self, entity_name: str) -> List[Dict[str, str]]:
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
                urls = list(search(query, stop=3))  # Using stop parameter instead of num_results
                logger.info(f"Found {len(urls)} URLs for query: {query}")
                
                # Fetch content from each URL
                for url in urls:
                    logger.info(f"Fetching content from: {url}")
                    content = await self._fetch_url_content(url)
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

    def _summarize_with_claude(self, search_results: List[Dict[str, str]], entity_name: str) -> str:
        """Use Claude to generate a summary of the entity based on search results."""
        if not search_results:
            return f"No detailed information found for {entity_name}."

        context = "\n\n".join([
            f"Source: {result['url']}\nContent: {result['content']}"
            for result in search_results
        ])

        prompt = f"""Based on the following search results about {entity_name}, provide a concise summary focusing on:
1. Their role in renewable energy
2. Recent significant developments or projects
3. Any notable reputation issues or risks
4. Financial stability indicators

Search Results:
{context}

Please provide a factual, balanced summary in 3-4 sentences."""

        try:
            message = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=500,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )
            # Extract just the text content from the response
            return message.content if isinstance(message.content, str) else message.content[0].text
        except Exception as e:
            logger.error(f"Error generating summary with Claude: {str(e)}")
            return f"Error generating summary for {entity_name}."

    async def fetch_and_summarize_entity_info(self, entity_name: str) -> Optional[str]:
        """Main method to fetch and summarize information about an entity."""
        if not entity_name:
            return None
            
        try:
            logger.info(f"Starting information gathering for: {entity_name}")
            
            # Search for entity information
            search_results = await self._search_entity(entity_name)
            if not search_results:
                logger.warning(f"No search results found for: {entity_name}")
                return None
                
            logger.info(f"Found {len(search_results)} relevant sources for {entity_name}")
            
            # Generate summary using Claude
            summary = self._summarize_with_claude(search_results, entity_name)
            return summary
            
        except Exception as e:
            logger.error(f"Error fetching info for {entity_name}: {str(e)}")
            return None 