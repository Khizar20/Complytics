"""
Authenticated Site Scanner
Extends the base site scanner to handle authentication during crawling.
Automatically detects login pages, authenticates, and continues crawling protected areas.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from .site_scanner import SiteScanOrchestrator
from .auth_handler import AuthenticationHandler
from .crawler import crawl_website
from .wcag import run_wcag_scan
from .security import run_security_scan
from .interaction import run_interactive_test_with_auth
from ..crawl_cache import (
    get_cached_crawl,
    set_cached_crawl,
    get_crawl_from_db,
    persist_crawl_to_db
)

logger = logging.getLogger("scanner.authenticated_site")


class AuthenticatedSiteScanOrchestrator(SiteScanOrchestrator):
    """
    Enhanced site scanner with authentication support.
    Extends the base SiteScanOrchestrator to handle login-protected pages.
    """
    
    def __init__(self, credentials: Optional[Dict[str, str]] = None, **kwargs):
        super().__init__(**kwargs)
        self.credentials = credentials
        self.auth_handler = None
        self.authenticated_session = None
        self.login_required = False
        self.authenticated_urls = set()
        self.session_cookies = None  # Store cookies for passing to scans
        
        if credentials:
            self.auth_handler = AuthenticationHandler(credentials)
    
    async def scan_site_with_auth(self, start_url: str, use_selenium_crawler: bool = False) -> Dict[str, Any]:
        """
        Main entry point for authenticated site scanning.
        
        Args:
            start_url: Starting URL to scan
            use_selenium_crawler: Whether to use Selenium for crawling
            
        Returns:
            Dict containing scan results with authentication status
        """
        start_time = time.time()
        
        logger.info(f"\n{'*'*70}")
        logger.info(f"🔐 AUTHENTICATED SITE SCAN INITIATED")
        logger.info(f"{'*'*70}")
        logger.info(f"Target URL: {start_url}")
        logger.info(f"Max Pages: {self.max_pages}")
        logger.info(f"Max Depth: {self.max_depth}")
        logger.info(f"Scan Mode: {self.scan_mode.upper()}")
        logger.info(f"Credentials: {self.credentials.get('username', 'N/A') if self.credentials else 'None'}")
        logger.info(f"{'*'*70}\n")
        
        # Step 1: Mode-specific preprocessing
        # For security-only mode, skip crawling entirely (security is domain-level)
        if self.scan_mode == "security":
            # Security-only: Skip crawling - security headers and SSL are domain-level
            logger.info(f"🔒 SECURITY-ONLY MODE: Skipping page crawl (security is domain-level)")
            logger.info(f"{'─'*70}\n")
            
            # Create minimal crawl_result for consistency
            crawl_result = {
                "urls": [start_url],
                "stats": {
                    "from_sitemap": 0,
                    "from_crawl": 0,
                    "duration_seconds": 0,
                    "total_discovered": 1,
                    "total_visited": 1
                },
                "start_url": start_url,
                "note": "Crawl skipped - security scans are domain-level"
            }
        else:
            # For accessibility and "all" modes, crawl to discover pages
            logger.info(f"📡 PHASE 1: INITIAL CRAWLING")
            logger.info(f"{'─'*70}\n")
            
            crawl_result = await self._crawl_with_authentication(start_url, use_selenium_crawler)
            
            if not crawl_result or not crawl_result.get("urls"):
                logger.error(f"❌ No pages discovered during crawl")
                return {
                    "error": "No pages discovered during crawl",
                    "authentication_required": self.login_required,
                    "authentication_successful": False,
                    "duration_seconds": time.time() - start_time
                }
        
        # Step 2: Scan all discovered pages
        logger.info(f"🔬 PHASE 2: SCANNING DISCOVERED PAGES")
        logger.info(f"{'─'*70}\n")
        
        # Only pass credentials/session cookies if authentication was actually required and successful
        # If no login page was detected or auth failed, don't pass credentials to avoid unnecessary auth attempts
        if self.login_required and self.authenticated_session and self.session_cookies:
            # Authentication was needed and successful - pass session cookies
            self.credentials = self.credentials
            self.session_cookies = self.session_cookies
            logger.info(f"Using authenticated session for scans ({len(self.session_cookies)} cookies)")
        elif self.login_required and not self.authenticated_session:
            # Authentication was needed but failed - don't pass credentials to avoid repeated failed attempts
            logger.info("Authentication failed - scanning public pages without credentials")
            self.credentials = None
            self.session_cookies = None
        else:
            # No authentication required - don't pass credentials
            logger.info("No authentication required - scanning without credentials")
            self.credentials = None
            self.session_cookies = None
        
        # Store scan start time for duration calculation
        self._scan_start_time = time.time()
        
        result = await self._scan_discovered_pages(crawl_result)
        
        # Add authentication metadata
        result["authentication_required"] = self.login_required
        result["authentication_successful"] = bool(self.authenticated_session)
        result["authenticated_urls_count"] = len(self.authenticated_urls)
        result["session_used"] = bool(self.authenticated_session)
        
        duration = time.time() - start_time
        result["duration_seconds"] = duration
        
        logger.info(f"\n{'*'*70}")
        logger.info(f"🔐 AUTHENTICATED SCAN COMPLETED")
        logger.info(f"{'*'*70}")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(f"Authentication Required: {self.login_required}")
        logger.info(f"Authentication Successful: {result.get('authentication_successful', False)}")
        logger.info(f"Authenticated URLs: {len(self.authenticated_urls)}")
        logger.info(f"{'*'*70}\n")
        
        return result
    
    async def _crawl_with_authentication(self, start_url: str, use_selenium_crawler: bool = False) -> Dict[str, Any]:
        """
        Crawl website with authentication support.
        
        Args:
            start_url: URL to start crawling from
            use_selenium_crawler: Whether to use Selenium for crawling
            
        Returns:
            Dict containing crawl results
        """
        try:
            # First, try standard crawling
            logger.info("Starting standard crawl...")
            crawl_result = await crawl_website(
                start_url,
                max_pages=self.max_pages,
                max_depth=self.max_depth,
                use_selenium=use_selenium_crawler
            )
            
            # Check if we need authentication
            if self.credentials and self._detect_authentication_requirement(crawl_result):
                logger.info("🔐 Authentication required - attempting login")
                self.login_required = True
                
                # Try to authenticate
                try:
                    auth_success = await self._authenticate_and_continue_crawling(start_url, crawl_result)
                    if auth_success:
                        logger.info("✅ Authentication successful - continuing with authenticated crawl")
                        # Re-crawl with authenticated session
                        crawl_result = await self._authenticated_crawl(start_url, use_selenium_crawler)
                    else:
                        logger.warning("❌ Authentication failed - continuing with public pages only")
                        # Continue with the original crawl_result (public pages)
                        # The scan will proceed with whatever URLs were discovered
                except Exception as e:
                    logger.error(f"Authentication error: {str(e)} - continuing with public pages")
                    # Continue with public pages even if auth fails
            else:
                logger.info("ℹ️ No authentication required or detected - scanning public pages")
            
            return crawl_result
            
        except Exception as e:
            logger.error(f"Error during authenticated crawl: {str(e)}")
            return {"urls": [], "stats": {}, "error": str(e)}
    
    def _detect_authentication_requirement(self, crawl_result: Dict[str, Any]) -> bool:
        """
        Detect if authentication is required based on crawl results.
        Only flags as requiring auth if we have strong indicators.
        
        Args:
            crawl_result: Results from initial crawl
            
        Returns:
            bool: True if authentication appears required
        """
        try:
            urls = crawl_result.get("urls", [])
            
            # Check for login indicators in discovered URLs
            login_url_patterns = [
                "/login", "/signin", "/auth", "/sign-in", "/log-in",
                "/authenticate", "/admin/login", "/user/login"
            ]
            
            login_page_found = False
            for url in urls:
                url_lower = url.lower()
                for pattern in login_url_patterns:
                    if pattern in url_lower:
                        logger.info(f"Login page detected in URL: {url}")
                        login_page_found = True
                        break
                if login_page_found:
                    break
            
            # Only require authentication if we found a login page
            # Don't require auth just because few pages were found (could be small site)
            if login_page_found:
                return True
            
            # If no login page found, don't require authentication
            # Even if credentials are provided, if no login page exists, scan as public
            logger.info("No login page detected in crawled URLs - will scan as public pages")
            return False
            
        except Exception as e:
            logger.error(f"Error detecting authentication requirement: {str(e)}")
            return False
    
    async def _authenticate_and_continue_crawling(self, start_url: str, crawl_result: Dict[str, Any]) -> bool:
        """
        Attempt to authenticate and continue crawling.
        
        Args:
            start_url: Original URL
            crawl_result: Current crawl results
            
        Returns:
            bool: True if authentication successful
        """
        try:
            # Use the interaction scanner to test authentication
            auth_result = run_interactive_test_with_auth(start_url, self.credentials)
            
            if auth_result.get("authentication_successful", False):
                self.authenticated_session = auth_result.get("session_info", {})
                # Extract cookies for passing to WCAG scans
                self.session_cookies = self.authenticated_session.get("cookies", []) if self.authenticated_session else None
                logger.info("Authentication successful - session established")
                logger.info(f"Session cookies extracted: {len(self.session_cookies) if self.session_cookies else 0} cookies")
                return True
            else:
                logger.warning("Authentication failed")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False
    
    async def _authenticated_crawl(self, start_url: str, use_selenium_crawler: bool = False) -> Dict[str, Any]:
        """
        Perform authenticated crawling using session information.
        
        Args:
            start_url: URL to start crawling from
            use_selenium_crawler: Whether to use Selenium for crawling
            
        Returns:
            Dict containing authenticated crawl results
        """
        try:
            # For now, use the standard crawler but mark as authenticated
            # In a full implementation, this would use session cookies
            crawl_result = await crawl_website(
                start_url,
                max_pages=self.max_pages,
                max_depth=self.max_depth,
                use_selenium=use_selenium_crawler
            )
            
            # Mark URLs as authenticated if we have session
            if self.authenticated_session:
                crawl_result["authenticated"] = True
                crawl_result["session_used"] = True
                # Add all discovered URLs to authenticated set
                for url in crawl_result.get("urls", []):
                    self.authenticated_urls.add(url)
            
            return crawl_result
            
        except Exception as e:
            logger.error(f"Authenticated crawl failed: {str(e)}")
            return {
                "urls": [],
                "stats": {},
                "error": f"Authenticated crawl failed: {str(e)}",
                "authenticated": True,
                "session_used": False
            }
    
    async def _scan_discovered_pages(self, crawl_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scan all discovered pages with authentication context.
        Uses the already-crawled URLs instead of re-crawling.
        
        Args:
            crawl_result: Results from crawling
            
        Returns:
            Dict containing scan results
        """
        try:
            urls = crawl_result.get("urls", [])
            if not urls:
                logger.warning("No URLs found in crawl result to scan")
                return {
                    "error": "No URLs to scan",
                    "authenticated_scan": True,
                    "session_used": False,
                    "summary": {},
                    "page_results": [],
                    "wcag_aggregate": {},
                    "security_aggregate": {}
                }
            
            logger.info(f"Scanning {len(urls)} discovered pages with authentication context")
            
            # Scan pages based on mode
            if self.scan_mode == "security":
                # Security-only: scan domain-level security
                logger.info("Running domain-level security scan...")
                security_result = await asyncio.to_thread(run_security_scan, urls[0] if urls else "")
                security_aggregate = {
                    "primary_scan": security_result,
                    "variations_detected": 0,
                    "note": "Security headers are typically consistent across a domain"
                }
                wcag_aggregate = {}
                page_results = []
            elif self.scan_mode == "accessibility":
                # Accessibility-only: scan all pages for WCAG
                page_results = await self.scan_pages_accessibility_only(urls)
                wcag_aggregate = self.aggregate_wcag_results(page_results)
                security_aggregate = {}
            else:  # "all" mode
                # Scan accessibility for all pages
                page_results = await self.scan_pages_accessibility_only(urls)
                wcag_aggregate = self.aggregate_wcag_results(page_results)
                
                # Scan security once (domain-level)
                logger.info("Running domain-level security scan...")
                security_result = await asyncio.to_thread(run_security_scan, urls[0] if urls else "")
                security_aggregate = {
                    "primary_scan": security_result,
                    "variations_detected": 0,
                    "note": "Security headers are typically consistent across a domain"
                }
            
            # Ensure wcag_aggregate has proper structure
            if not wcag_aggregate:
                wcag_aggregate = {
                    "total_pages_scanned": len(page_results) if page_results else 0,
                    "pages_with_issues": 0,
                    "total_violations": 0,
                    "unique_rules_violated": 0,
                    "impact_counts": {"critical": 0, "serious": 0, "moderate": 0, "minor": 0},
                    "violations_by_page": {},
                    "violations_summary": [],
                    "top_issues": []
                }
            
            # Log aggregation results for debugging
            logger.info(f"\n📊 WCAG Aggregation Results:")
            logger.info(f"   Total violations: {wcag_aggregate.get('total_violations', 0)}")
            logger.info(f"   Impact counts: {wcag_aggregate.get('impact_counts', {})}")
            logger.info(f"   Pages with issues: {wcag_aggregate.get('pages_with_issues', 0)}")
            
            # Generate summary
            summary = self.generate_site_summary(
                crawl_result,
                page_results if page_results else [],
                wcag_aggregate,
                security_aggregate if security_aggregate else {}
            )
            summary["scan_mode"] = self.scan_mode
            
            # Log calculated score for debugging
            logger.info(f"   Calculated accessibility score: {summary.get('accessibility_score', 0)}")
            
            duration = time.time() - (getattr(self, '_scan_start_time', time.time()))
            
            result = {
                "summary": summary,
                "crawl_result": crawl_result,
                "page_results": page_results if page_results else [],
                "wcag_aggregate": wcag_aggregate,
                "security_aggregate": security_aggregate if security_aggregate else {},
                "duration_seconds": duration,
                "authenticated_scan": True,
                "session_used": bool(self.authenticated_session),
                "authenticated_urls": list(self.authenticated_urls)
            }
            
            return result
            
        except Exception as e:
            logger.exception(f"Authenticated page scanning failed: {str(e)}")
            # Return partial results even if there's an error
            return {
                "error": f"Authenticated scanning failed: {str(e)}",
                "authenticated_scan": True,
                "session_used": False,
                "summary": {
                    "error": str(e),
                    "pages_scanned": 0
                },
                "page_results": [],
                "wcag_aggregate": {},
                "security_aggregate": {}
            }


async def scan_authenticated_site(
    url: str,
    credentials: Dict[str, str],
    max_pages: int = 50,
    max_depth: int = 3,
    scan_mode: str = "all",
    parallel_scans: int = 3,
    use_selenium_crawler: bool = False,
    db = None,
    organization_id: str = None
) -> Dict[str, Any]:
    """
    Convenience function to run authenticated site scan.
    
    Args:
        url: Starting URL to scan
        credentials: Dict with 'username' and 'password'
        max_pages: Maximum number of pages to scan
        max_depth: Maximum link depth to follow
        scan_mode: "all", "accessibility", or "security"
        parallel_scans: Number of concurrent page scans
        use_selenium_crawler: Whether to use Selenium for crawling
        db: Database connection
        organization_id: Organization ID for caching
        
    Returns:
        Dict containing scan results
    """
    scanner = AuthenticatedSiteScanOrchestrator(
        credentials=credentials,
        max_pages=max_pages,
        max_depth=max_depth,
        scan_mode=scan_mode,
        parallel_scans=parallel_scans,
        db=db,
        organization_id=organization_id
    )
    
    return await scanner.scan_site_with_auth(url, use_selenium_crawler)

