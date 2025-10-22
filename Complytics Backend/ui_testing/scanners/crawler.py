"""
Website Crawler for Comprehensive UI Testing
Discovers pages from a given URL and queues them for accessibility/security scanning.
Supports sitemap.xml parsing, robots.txt respect, and intelligent URL filtering.
"""

import asyncio
import logging
import re
import time
from typing import Dict, List, Set, Optional, Any
from urllib.parse import urljoin, urlparse, urlunparse
from collections import deque

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException

logger = logging.getLogger("scanner.crawler")


class WebsiteCrawler:
    """
    Intelligent website crawler that discovers pages for UI testing.
    
    Features:
    - Respects robots.txt (basic check)
    - Parses sitemap.xml for comprehensive page list
    - Crawls HTML pages to discover links
    - Filters out non-HTML resources (images, PDFs, etc.)
    - Deduplicates URLs
    - Limits depth and page count for safety
    - Handles JavaScript-rendered content via Selenium
    """
    
    def __init__(
        self,
        max_pages: int = 50,
        max_depth: int = 3,
        timeout: int = 30,
        respect_robots: bool = True,
        follow_external: bool = False,
        use_selenium: bool = False
    ):
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.timeout = timeout
        self.respect_robots = respect_robots
        self.follow_external = follow_external
        self.use_selenium = use_selenium
        
        self.visited_urls: Set[str] = set()
        self.discovered_urls: Set[str] = set()
        self.queue: deque = deque()
        self.disallowed_paths: Set[str] = set()
        
        # URL patterns to ignore (common non-page resources)
        self.ignore_extensions = {
            '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.ico',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.tar', '.gz',
            '.mp4', '.mp3', '.avi', '.mov', '.wav',
            '.css', '.js', '.json', '.xml', '.txt'
        }
        
        # URL patterns that typically aren't pages
        self.ignore_patterns = [
            r'/api/',
            r'/download/',
            r'/print/',
            r'/feed/',
            r'/rss/',
            r'\?logout',
            r'\?download',
            r'#',  # Fragments only (SPA routes handled separately)
        ]
    
    def _normalize_url(self, url: str, base_url: str = None) -> Optional[str]:
        """Normalize and clean URL"""
        try:
            if base_url:
                url = urljoin(base_url, url)
            
            parsed = urlparse(url)
            
            # Remove fragment
            parsed = parsed._replace(fragment='')
            
            # Remove trailing slash for consistency
            path = parsed.path.rstrip('/')
            if not path:
                path = '/'
            parsed = parsed._replace(path=path)
            
            # Remove common tracking parameters
            if parsed.query:
                query_parts = parsed.query.split('&')
                filtered = [p for p in query_parts if not any(
                    p.startswith(f"{param}=") for param in ['utm_', 'fbclid', 'gclid', 'ref']
                )]
                parsed = parsed._replace(query='&'.join(filtered) if filtered else '')
            
            return urlunparse(parsed)
        except Exception as e:
            logger.warning(f"Failed to normalize URL {url}: {e}")
            return None
    
    def _should_crawl(self, url: str, base_domain: str) -> bool:
        """Check if URL should be crawled"""
        try:
            parsed = urlparse(url)
            
            # Check domain
            if not self.follow_external and parsed.netloc != base_domain:
                return False
            
            # Check file extensions
            path_lower = parsed.path.lower()
            if any(path_lower.endswith(ext) for ext in self.ignore_extensions):
                return False
            
            # Check ignore patterns
            url_lower = url.lower()
            if any(re.search(pattern, url_lower) for pattern in self.ignore_patterns):
                return False
            
            # Check robots.txt disallowed paths
            if self.respect_robots:
                for disallowed in self.disallowed_paths:
                    if parsed.path.startswith(disallowed):
                        logger.debug(f"Skipping disallowed path: {url}")
                        return False
            
            return True
        except Exception as e:
            logger.warning(f"Error checking URL {url}: {e}")
            return False
    
    def _fetch_robots_txt(self, base_url: str) -> None:
        """Fetch and parse robots.txt"""
        try:
            robots_url = urljoin(base_url, '/robots.txt')
            logger.info(f"Fetching robots.txt from {robots_url}")
            response = requests.get(robots_url, timeout=self.timeout, headers={'User-Agent': 'ComplyticsUITester/1.0'})
            
            if response.status_code == 200:
                disallow_count = 0
                for line in response.text.split('\n'):
                    line = line.strip()
                    if line.lower().startswith('disallow:'):
                        path = line.split(':', 1)[1].strip()
                        if path:
                            self.disallowed_paths.add(path)
                            disallow_count += 1
                logger.info(f"✓ Loaded robots.txt: found {len(self.disallowed_paths)} disallowed paths")
                if disallow_count > 0:
                    logger.debug(f"  Disallowed paths: {list(self.disallowed_paths)[:5]}...")
            else:
                logger.info(f"No robots.txt found (status {response.status_code})")
        except Exception as e:
            logger.warning(f"Could not fetch robots.txt: {e}")
    
    def _fetch_sitemap(self, base_url: str) -> List[str]:
        """Fetch and parse sitemap.xml"""
        urls = []
        try:
            sitemap_url = urljoin(base_url, '/sitemap.xml')
            logger.info(f"Fetching sitemap from {sitemap_url}")
            response = requests.get(sitemap_url, timeout=self.timeout, headers={'User-Agent': 'ComplyticsUITester/1.0'})
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'xml')
                
                # Handle sitemap index (multiple sitemaps)
                sitemap_tags = soup.find_all('sitemap')
                if sitemap_tags:
                    logger.info(f"  Found sitemap index with {len(sitemap_tags)} sitemaps")
                    for idx, sitemap_tag in enumerate(sitemap_tags[:10], 1):  # Limit to 10 sitemaps
                        loc = sitemap_tag.find('loc')
                        if loc and loc.text:
                            try:
                                logger.info(f"  Fetching sub-sitemap {idx}/10: {loc.text}")
                                sub_response = requests.get(loc.text, timeout=self.timeout)
                                if sub_response.status_code == 200:
                                    sub_soup = BeautifulSoup(sub_response.content, 'xml')
                                    url_count = 0
                                    for url_tag in sub_soup.find_all('url'):
                                        loc_tag = url_tag.find('loc')
                                        if loc_tag and loc_tag.text:
                                            urls.append(loc_tag.text)
                                            url_count += 1
                                    logger.info(f"    ✓ Found {url_count} URLs in sub-sitemap")
                            except Exception as e:
                                logger.warning(f"    ✗ Error fetching sub-sitemap {loc.text}: {e}")
                else:
                    # Single sitemap
                    logger.info(f"  Parsing single sitemap")
                    for url_tag in soup.find_all('url'):
                        loc = url_tag.find('loc')
                        if loc and loc.text:
                            urls.append(loc.text)
                
                logger.info(f"✓ Found {len(urls)} total URLs in sitemap(s)")
            else:
                logger.info(f"No sitemap.xml found (status {response.status_code})")
        except Exception as e:
            logger.warning(f"Could not fetch sitemap: {e}")
        
        return urls
    
    def _extract_links_with_requests(self, url: str, base_domain: str) -> List[str]:
        """Extract links from HTML using requests + BeautifulSoup"""
        links = []
        try:
            logger.debug(f"    Extracting links from {url}")
            response = requests.get(
                url,
                timeout=self.timeout,
                headers={'User-Agent': 'ComplyticsUITester/1.0'},
                allow_redirects=True
            )
            
            if response.status_code == 200 and 'text/html' in response.headers.get('Content-Type', ''):
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract from <a> tags
                link_count = 0
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    normalized = self._normalize_url(href, url)
                    if normalized and self._should_crawl(normalized, base_domain):
                        links.append(normalized)
                        link_count += 1
                
                # Extract from <link> tags (for alternate pages)
                for link in soup.find_all('link', href=True):
                    if link.get('rel') and 'alternate' in link['rel']:
                        href = link['href']
                        normalized = self._normalize_url(href, url)
                        if normalized and self._should_crawl(normalized, base_domain):
                            links.append(normalized)
                            link_count += 1
                
                logger.debug(f"    ✓ Found {link_count} valid links on page")
            else:
                logger.debug(f"    ✗ Non-HTML response (status {response.status_code})")
        
        except Exception as e:
            logger.warning(f"    ✗ Error extracting links from {url}: {e}")
        
        return links
    
    def _extract_links_with_selenium(self, url: str, base_domain: str) -> List[str]:
        """Extract links from JavaScript-rendered pages using Selenium"""
        links = []
        driver = None
        try:
            logger.debug(f"    Extracting links with Selenium from {url}")
            options = Options()
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.page_load_strategy = "eager"
            
            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(self.timeout)
            driver.get(url)
            
            # Wait for JS to render
            time.sleep(2)
            
            # Get all links
            link_elements = driver.find_elements("tag name", "a")
            logger.debug(f"    Found {len(link_elements)} total <a> elements")
            
            link_count = 0
            for element in link_elements:
                try:
                    href = element.get_attribute('href')
                    if href:
                        normalized = self._normalize_url(href, url)
                        if normalized and self._should_crawl(normalized, base_domain):
                            links.append(normalized)
                            link_count += 1
                except Exception:
                    continue
            
            logger.debug(f"    ✓ Found {link_count} valid links (Selenium)")
        
        except Exception as e:
            logger.warning(f"    ✗ Error extracting links with Selenium from {url}: {e}")
        
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
        
        return links
    
    async def crawl(self, start_url: str) -> Dict[str, Any]:
        """
        Crawl website starting from given URL.
        
        Returns:
            {
                "urls": List[str],  # All discovered URLs
                "stats": {
                    "total_discovered": int,
                    "total_visited": int,
                    "from_sitemap": int,
                    "from_crawl": int,
                    "duration_seconds": float
                },
                "errors": List[str]
            }
        """
        start_time = time.time()
        errors = []
        
        try:
            # Normalize start URL
            start_url = self._normalize_url(start_url)
            if not start_url:
                return {"urls": [], "stats": {}, "errors": ["Invalid start URL"]}
            
            parsed = urlparse(start_url)
            base_domain = parsed.netloc
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            
            logger.info(f"Starting crawl for {base_url} (max_pages={self.max_pages}, max_depth={self.max_depth})")
            
            # Step 1: Fetch robots.txt
            if self.respect_robots:
                self._fetch_robots_txt(base_url)
            
            # Step 2: Fetch sitemap.xml
            sitemap_urls = self._fetch_sitemap(base_url)
            from_sitemap = 0
            
            for url in sitemap_urls:
                normalized = self._normalize_url(url)
                if normalized and self._should_crawl(normalized, base_domain):
                    self.discovered_urls.add(normalized)
                    self.queue.append((normalized, 0))  # (url, depth)
                    from_sitemap += 1
                    if len(self.discovered_urls) >= self.max_pages:
                        break
            
            # Step 3: Add start URL to queue if not in sitemap
            if start_url not in self.discovered_urls:
                self.discovered_urls.add(start_url)
                self.queue.appendleft((start_url, 0))
            
            # Step 4: BFS crawl
            from_crawl = 0
            logger.info(f"\n{'='*60}")
            logger.info(f"Starting BFS crawl (max_pages={self.max_pages}, max_depth={self.max_depth})")
            logger.info(f"{'='*60}\n")
            
            while self.queue and len(self.visited_urls) < self.max_pages:
                url, depth = self.queue.popleft()
                
                if url in self.visited_urls or depth > self.max_depth:
                    if depth > self.max_depth:
                        logger.debug(f"  Skipping {url} (depth {depth} > max_depth {self.max_depth})")
                    continue
                
                self.visited_urls.add(url)
                progress_pct = (len(self.visited_urls) / self.max_pages) * 100
                logger.info(f"🔍 Crawling [{len(self.visited_urls)}/{self.max_pages}] ({progress_pct:.1f}%)")
                logger.info(f"   URL: {url}")
                logger.info(f"   Depth: {depth}/{self.max_depth}")
                logger.info(f"   Queue size: {len(self.queue)}")
                
                # Extract links from this page
                try:
                    if self.use_selenium:
                        links = self._extract_links_with_selenium(url, base_domain)
                    else:
                        links = self._extract_links_with_requests(url, base_domain)
                    
                    # Add new links to queue
                    new_links_added = 0
                    for link in links:
                        if link not in self.discovered_urls:
                            self.discovered_urls.add(link)
                            self.queue.append((link, depth + 1))
                            from_crawl += 1
                            new_links_added += 1
                            if len(self.discovered_urls) >= self.max_pages:
                                logger.info(f"   ⚠️  Reached max_pages limit ({self.max_pages})")
                                break
                    
                    logger.info(f"   ✓ Discovered {new_links_added} new URLs (total: {len(self.discovered_urls)})\n")
                
                except Exception as e:
                    error_msg = f"Error crawling {url}: {str(e)}"
                    logger.error(f"   ✗ {error_msg}\n")
                    errors.append(error_msg)
                
                # Rate limiting
                await asyncio.sleep(0.5)
            
            duration = time.time() - start_time
            
            result = {
                "urls": sorted(list(self.discovered_urls))[:self.max_pages],
                "stats": {
                    "total_discovered": len(self.discovered_urls),
                    "total_visited": len(self.visited_urls),
                    "from_sitemap": from_sitemap,
                    "from_crawl": from_crawl,
                    "duration_seconds": round(duration, 2)
                },
                "errors": errors
            }
            
            logger.info(f"Crawl complete: {result['stats']}")
            return result
        
        except Exception as e:
            logger.exception(f"Crawl failed for {start_url}")
            return {
                "urls": [],
                "stats": {},
                "errors": [f"Crawl failed: {str(e)}"]
            }


async def crawl_website(
    url: str,
    max_pages: int = 50,
    max_depth: int = 3,
    use_selenium: bool = False
) -> Dict[str, Any]:
    """
    Convenience function to crawl a website.
    
    Args:
        url: Starting URL
        max_pages: Maximum number of pages to discover
        max_depth: Maximum link depth to follow
        use_selenium: Use Selenium for JS-rendered sites
    
    Returns:
        Dictionary with discovered URLs and stats
    """
    crawler = WebsiteCrawler(
        max_pages=max_pages,
        max_depth=max_depth,
        use_selenium=use_selenium
    )
    return await crawler.crawl(url)

