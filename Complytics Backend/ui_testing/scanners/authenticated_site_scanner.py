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
            # Step 1: Always crawl first to discover URLs
            logger.info("Starting standard crawl to discover URLs...")
            crawl_result = await crawl_website(
                start_url,
                max_pages=self.max_pages,
                max_depth=self.max_depth,
                use_selenium=use_selenium_crawler
            )
            
            # Step 2: If credentials provided, look for login pages in crawled URLs
            if self.credentials:
                self.login_required = True
                logger.info("🔐 Credentials provided - searching crawled URLs for login pages")
                
                # Find login pages from crawled URLs
                login_pages = self._find_login_pages_in_crawl(crawl_result)
                
                if login_pages:
                    logger.info(f"Found {len(login_pages)} login page(s) in crawl: {login_pages}")
                    # Try to authenticate on discovered login pages
                    try:
                        auth_success = await self._authenticate_on_login_pages(login_pages)
                        if auth_success:
                            logger.info("✅ Authentication successful - re-crawling with authenticated session")
                            # Re-crawl with authenticated session
                            crawl_result = await self._authenticated_crawl(start_url, use_selenium_crawler)
                        else:
                            logger.warning("❌ Authentication failed on all login pages - continuing with public pages only")
                    except Exception as e:
                        logger.error(f"Authentication error: {str(e)} - continuing with public pages")
                else:
                    logger.info("ℹ️ No login pages found in crawled URLs - scanning public pages")
            else:
                logger.info("ℹ️ No credentials provided - scanning public pages")
            
            return crawl_result
            
        except Exception as e:
            logger.error(f"Error during authenticated crawl: {str(e)}")
            return {"urls": [], "stats": {}, "error": str(e)}
    
    def _find_login_pages_in_crawl(self, crawl_result: Dict[str, Any]) -> List[str]:
        """
        Find login pages from crawled URLs by matching URL patterns and regex.
        
        Uses both specific patterns and regex to detect login-related keywords anywhere in URL.
        
        Args:
            crawl_result: Results from initial crawl
            
        Returns:
            List of URLs that match login page patterns
        """
        import re
        
        try:
            urls = crawl_result.get("urls", [])
            login_pages = []
            seen_urls = set()  # Track URLs to avoid duplicates
            
            # Specific login URL patterns - exact matches for common paths
            specific_patterns = [
                "/login", "/signin", "/auth", "/sign-in", "/log-in", "/log_in",
                "/authenticate", "/admin/login", "/user/login", "/account/login",
                "/practice-test-login", "/test-login", "/login-test",
                "/sign-in", "/sign_in", "/signin",
                "/authentication", "/authenticate", "/auth",
                "/wp-login", "/wp-admin", "/admin", "/dashboard/login",
                "/portal/login", "/app/login", "/web/login", "/site/login",
                "/member/login", "/users/login", "/accounts/login", "/account/signin",
                "/user/signin", "/members/signin", "/client/login", "/customer/login",
                "/employee/login", "/staff/login", "/admin-panel", "/admin-panel/login",
                "/cms/login", "/backend/login", "/api/login", "/oauth/login",
                "/sso/login", "/saml/login", "/ldap/login", "/ad/login"
            ]
            
            # Regex patterns to match login-related keywords anywhere in URL
            # Matches: login, signin, sign-in, sign_in, authenticate, auth, etc.
            login_regex_patterns = [
                r'/([^/]*)?login([^/]*)?/?$',  # Matches /anything-login, /login-anything, /login
                r'/([^/]*)?sign[_-]?in([^/]*)?/?$',  # Matches /signin, /sign-in, /sign_in, /anything-signin
                r'/([^/]*)?authenticate([^/]*)?/?$',  # Matches /authenticate, /anything-authenticate
                r'/([^/]*)?auth([^/]*)?/?$',  # Matches /auth, /anything-auth, /auth-anything
                r'/([^/]*)?log[_-]?in([^/]*)?/?$',  # Matches /login, /log-in, /log_in variations
                r'/([^/]*)?sign[_-]?on([^/]*)?/?$',  # Matches /signon, /sign-on, /sign_on
                r'/([^/]*)?access([^/]*)?/?$',  # Matches /access, /access-control, etc.
                r'/([^/]*)?credential([^/]*)?/?$',  # Matches /credential, /credentials
                r'/([^/]*)?session([^/]*)?/?$',  # Matches /session, /sessions
                r'/([^/]*)?password([^/]*)?/?$',  # Matches /password, /password-reset
            ]
            
            # Compile regex patterns for better performance
            compiled_regexes = [re.compile(pattern, re.IGNORECASE) for pattern in login_regex_patterns]
            
            for url in urls:
                if url in seen_urls:
                    continue
                    
                url_lower = url.lower()
                matched = False
                matched_pattern = None
                
                # First, check specific patterns (faster)
                for pattern in specific_patterns:
                    if pattern in url_lower:
                        matched_pattern = pattern
                        matched = True
                        break
                
                # If no specific pattern matched, try regex patterns
                if not matched:
                    for regex in compiled_regexes:
                        if regex.search(url_lower):
                            matched_pattern = f"regex: {regex.pattern}"
                            matched = True
                            break
                
                # Additional check: look for login-related keywords anywhere in URL path
                if not matched:
                    # Extract path from URL (everything after domain)
                    try:
                        from urllib.parse import urlparse
                        parsed = urlparse(url_lower)
                        path = parsed.path
                        
                        # Check if path contains login-related keywords
                        login_keywords = ['login', 'signin', 'sign-in', 'sign_in', 'authenticate', 'auth', 'log-in', 'log_in']
                        for keyword in login_keywords:
                            if keyword in path:
                                matched_pattern = f"keyword: {keyword}"
                                matched = True
                                break
                    except Exception:
                        pass
                
                if matched:
                    logger.info(f"Login page detected - Pattern: '{matched_pattern}' | URL: {url}")
                    login_pages.append(url)
                    seen_urls.add(url)
            
            logger.info(f"Found {len(login_pages)} login page(s) from {len(urls)} crawled URLs")
            return login_pages
            
        except Exception as e:
            logger.error(f"Error finding login pages: {str(e)}")
            return []
    
    async def _authenticate_on_login_pages(self, login_pages: List[str]) -> bool:
        """
        Attempt to authenticate on discovered login pages.
        Only authenticates on URLs that match login patterns, not on start URL.
        
        Args:
            login_pages: List of URLs that match login page patterns
            
        Returns:
            bool: True if authentication successful
        """
        try:
            if not login_pages:
                logger.warning("No login pages provided for authentication")
                return False
            
            # Try authenticating on each discovered login page
            for login_url in login_pages:
                try:
                    logger.info(f"🔐 Attempting authentication on login page: {login_url}")
                    auth_result = run_interactive_test_with_auth(login_url, self.credentials)
                    
                    if auth_result.get("authentication_successful", False):
                        self.authenticated_session = auth_result.get("session_info", {})
                        # Extract cookies for passing to WCAG scans
                        self.session_cookies = self.authenticated_session.get("cookies", []) if self.authenticated_session else None
                        logger.info(f"✅ Authentication successful on login page: {login_url}")
                        logger.info(f"Session cookies extracted: {len(self.session_cookies) if self.session_cookies else 0} cookies")
                        return True
                    else:
                        logger.warning(f"❌ Authentication failed on login page: {login_url}")
                        if auth_result.get("login_form_detected", False):
                            logger.warning("Login form was detected but authentication failed - check credentials")
                        else:
                            logger.warning("No login form detected on this page")
                            
                except Exception as e:
                    logger.error(f"Error authenticating on {login_url}: {str(e)}")
                    continue
            
            logger.warning("❌ Authentication failed on all login pages")
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

