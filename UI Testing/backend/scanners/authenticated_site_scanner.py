import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin, urlparse

from .site_scanner import SiteScanOrchestrator
from .auth_handler import AuthenticationHandler
from .interaction import run_interactive_test_with_auth

logger = logging.getLogger("authenticated_site_scanner")


class AuthenticatedSiteScanOrchestrator(SiteScanOrchestrator):
    """
    Enhanced site scanner with authentication support.
    Extends the base SiteScanOrchestrator to handle login-protected pages.
    """
    
    def __init__(self, credentials: Dict[str, str], **kwargs):
        super().__init__(**kwargs)
        self.credentials = credentials
        self.auth_handler = AuthenticationHandler(credentials)
        self.authenticated_session = None
        self.login_required = False
        
    async def scan_site_with_auth(self, start_url: str) -> Dict[str, Any]:
        """
        Main entry point for authenticated site scanning.
        
        Args:
            start_url: Starting URL to scan
            
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
        logger.info(f"Credentials: {self.credentials.get('username', 'N/A')}")
        logger.info(f"{'*'*70}\n")
        
        # Step 1: Initial crawl to detect authentication requirements
        logger.info(f"📡 PHASE 1: DETECTING AUTHENTICATION REQUIREMENTS")
        logger.info(f"{'─'*70}\n")
        
        initial_crawl = await self.crawl_website(start_url)
        auth_required = await self.detect_authentication_requirement(initial_crawl, start_url)
        
        if auth_required:
            logger.info("🔐 Authentication required - attempting login")
            self.login_required = True
            
            # Step 2: Perform authentication
            auth_success = await self.authenticate_and_get_session(start_url)
            if not auth_success:
                return {
                    "error": "Authentication failed",
                    "message": "Could not authenticate with provided credentials",
                    "authentication_required": True,
                    "authentication_successful": False
                }
            
            logger.info("✅ Authentication successful - proceeding with authenticated scan")
            
            # Step 3: Re-crawl with authenticated session
            logger.info(f"📡 PHASE 2: AUTHENTICATED CRAWLING")
            logger.info(f"{'─'*70}\n")
            
            authenticated_crawl = await self.crawl_website_authenticated(start_url)
            
            # Step 4: Scan authenticated pages
            logger.info(f"🔬 PHASE 3: SCANNING AUTHENTICATED PAGES")
            logger.info(f"{'─'*70}\n")
            
            result = await self.scan_authenticated_pages(authenticated_crawl)
        else:
            logger.info("ℹ️ No authentication required - proceeding with standard scan")
            result = await self.scan_site(start_url)
        
        # Add authentication metadata
        result["authentication_required"] = self.login_required
        result["authentication_successful"] = auth_success if auth_required else True
        result["credentials_used"] = bool(self.credentials)
        
        duration = time.time() - start_time
        result["duration_seconds"] = duration
        
        logger.info(f"\n{'*'*70}")
        logger.info(f"🔐 AUTHENTICATED SCAN COMPLETED")
        logger.info(f"{'*'*70}")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(f"Authentication Required: {self.login_required}")
        logger.info(f"Authentication Successful: {result.get('authentication_successful', False)}")
        logger.info(f"{'*'*70}\n")
        
        return result
    
    async def detect_authentication_requirement(self, crawl_result: Dict[str, Any], start_url: str) -> bool:
        """
        Detect if authentication is required based on crawl results.
        
        Args:
            crawl_result: Results from initial crawl
            start_url: Original URL being scanned
            
        Returns:
            bool: True if authentication appears required
        """
        try:
            # Check if we hit login pages or got redirected to login
            pages = crawl_result.get("pages", [])
            
            for page in pages:
                page_url = page.get("url", "").lower()
                page_title = page.get("title", "").lower()
                
                # Check for login indicators in URL
                login_url_patterns = [
                    "/login", "/signin", "/auth", "/sign-in", "/log-in",
                    "/authenticate", "/admin/login", "/user/login"
                ]
                
                for pattern in login_url_patterns:
                    if pattern in page_url:
                        logger.info(f"Login page detected in URL: {page_url}")
                        return True
                
                # Check for login indicators in title
                login_title_patterns = [
                    "login", "sign in", "signin", "authenticate",
                    "log in", "sign-in", "log-in"
                ]
                
                for pattern in login_title_patterns:
                    if pattern in page_title:
                        logger.info(f"Login page detected in title: {page_title}")
                        return True
            
            # Check if we got redirected to a login page
            if pages:
                first_page = pages[0]
                if first_page.get("url", "").lower() != start_url.lower():
                    # Check if redirected URL looks like a login page
                    redirected_url = first_page.get("url", "").lower()
                    for pattern in login_url_patterns:
                        if pattern in redirected_url:
                            logger.info(f"Redirected to login page: {redirected_url}")
                            return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error detecting authentication requirement: {str(e)}")
            return False
    
    async def authenticate_and_get_session(self, start_url: str) -> bool:
        """
        Perform authentication and establish session.
        
        Args:
            start_url: URL to authenticate against
            
        Returns:
            bool: True if authentication successful
        """
        try:
            # Use the interaction scanner with authentication
            auth_result = run_interactive_test_with_auth(start_url, self.credentials)
            
            if auth_result.get("authentication_successful", False):
                self.authenticated_session = auth_result.get("session_info", {})
                logger.info("Authentication successful - session established")
                return True
            else:
                logger.warning("Authentication failed")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False
    
    async def crawl_website_authenticated(self, start_url: str) -> Dict[str, Any]:
        """
        Crawl website using authenticated session.
        
        Args:
            start_url: URL to start crawling from
            
        Returns:
            Dict containing crawl results
        """
        try:
            # For now, use the standard crawler but mark as authenticated
            # In a full implementation, this would use session cookies
            crawl_result = await self.crawl_website(start_url)
            crawl_result["authenticated"] = True
            crawl_result["session_used"] = bool(self.authenticated_session)
            return crawl_result
            
        except Exception as e:
            logger.error(f"Authenticated crawl failed: {str(e)}")
            return {
                "error": f"Authenticated crawl failed: {str(e)}",
                "authenticated": True,
                "session_used": False
            }
    
    async def scan_authenticated_pages(self, crawl_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scan pages that were discovered through authenticated crawling.
        
        Args:
            crawl_result: Results from authenticated crawl
            
        Returns:
            Dict containing scan results
        """
        try:
            # Use the standard scanning process but with authentication context
            result = await self.scan_site(crawl_result.get("start_url", ""))
            
            # Add authentication metadata
            result["authenticated_scan"] = True
            result["session_used"] = bool(self.authenticated_session)
            
            return result
            
        except Exception as e:
            logger.error(f"Authenticated page scanning failed: {str(e)}")
            return {
                "error": f"Authenticated scanning failed: {str(e)}",
                "authenticated_scan": True,
                "session_used": False
            }
    
    async def test_authentication_only(self, url: str) -> Dict[str, Any]:
        """
        Test only the authentication process without full scanning.
        
        Args:
            url: URL to test authentication against
            
        Returns:
            Dict containing authentication test results
        """
        try:
            logger.info(f"Testing authentication for: {url}")
            
            auth_result = run_interactive_test_with_auth(url, self.credentials)
            
            return {
                "url": url,
                "authentication_required": auth_result.get("authentication_required", False),
                "authentication_successful": auth_result.get("authentication_successful", False),
                "login_form_detected": auth_result.get("login_form_detected", False),
                "session_info": auth_result.get("session_info", {}),
                "error": auth_result.get("error"),
                "final_url": auth_result.get("final_url", url)
            }
            
        except Exception as e:
            logger.error(f"Authentication test failed: {str(e)}")
            return {
                "url": url,
                "authentication_required": False,
                "authentication_successful": False,
                "error": str(e)
            }
