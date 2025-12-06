import asyncio
import logging
from typing import Any, Dict, List, Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from axe_selenium_python import Axe

logger = logging.getLogger("scanner.wcag")


def _build_chrome_driver(page_load_timeout: int = 120) -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    # Suppress noisy SSL/network errors in logs
    options.add_argument("--disable-logging")
    options.add_argument("--log-level=3")  # Only show fatal errors
    options.add_argument("--silent")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    # Disable network service logging to reduce SSL handshake error noise
    options.add_argument("--disable-features=NetworkService,NetworkServiceLogging")
    # Use faster/eager page load to mitigate renderer timeouts on heavy pages
    try:
        options.page_load_strategy = "eager"
    except Exception:
        pass
    # Use Selenium Manager to resolve the correct ChromeDriver automatically
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(page_load_timeout)
    return driver


def _run_axe_sync(url: str, credentials: Optional[Dict[str, str]] = None, session_cookies: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    driver = None
    try:
        logger.info("Launching headless Chrome for WCAG scan | url=%s", url)
        driver = _build_chrome_driver()
        
        # If we have session cookies, add them before navigating
        if session_cookies:
            logger.info("Adding session cookies for authenticated scan")
            try:
                # First navigate to the domain to set cookies
                from urllib.parse import urlparse
                parsed = urlparse(url)
                base_url = f"{parsed.scheme}://{parsed.netloc}"
                driver.get(base_url)
                
                # Add all session cookies
                cookies_added = 0
                for cookie in session_cookies:
                    try:
                        # Ensure cookie has required fields
                        cookie_name = cookie.get('name')
                        cookie_value = cookie.get('value')
                        
                        if not cookie_name or not cookie_value:
                            continue
                        
                        # Get domain from cookie or use parsed domain
                        cookie_domain = cookie.get('domain')
                        if not cookie_domain:
                            # Use the domain from URL, removing www. prefix if present
                            cookie_domain = parsed.netloc
                            if cookie_domain.startswith('www.'):
                                cookie_domain = cookie_domain[4:]
                        
                        cookie_dict = {
                            'name': cookie_name,
                            'value': cookie_value,
                            'domain': cookie_domain
                        }
                        # Add optional fields if present
                        if 'path' in cookie:
                            cookie_dict['path'] = cookie['path']
                        if 'secure' in cookie:
                            cookie_dict['secure'] = cookie['secure']
                        if 'httpOnly' in cookie:
                            cookie_dict['httpOnly'] = cookie['httpOnly']
                        
                        driver.add_cookie(cookie_dict)
                        cookies_added += 1
                    except Exception as e:
                        logger.warning(f"Failed to add cookie {cookie.get('name', 'unknown')}: {str(e)}")
                logger.info(f"Added {cookies_added} of {len(session_cookies)} session cookies")
            except Exception as e:
                logger.warning(f"Failed to set session cookies: {str(e)}")
        
        # Track login page detection status
        login_page_detected = False
        
        # If we have credentials but no session cookies, try to authenticate first
        if credentials and not session_cookies:
            logger.info("Credentials provided but no session cookies - attempting authentication")
            try:
                from .auth_handler import AuthenticationHandler
                auth_handler = AuthenticationHandler(credentials)
                
                # Navigate to URL first
                try:
                    driver.get(url)
                except Exception as e:
                    logger.warning(f"Failed to navigate to URL for authentication: {str(e)}")
                    # Continue anyway - will try to scan the page
                    pass
                
                # Check if login is required
                try:
                    if auth_handler.detect_login_page(driver):
                        login_page_detected = True
                        logger.info("Login page detected, attempting authentication...")
                        login_form = auth_handler.find_login_form(driver)
                        if login_form:
                            if auth_handler.perform_login(driver, login_form):
                                logger.info("Authentication successful for WCAG scan")
                                # Get session cookies for future requests
                                session_info = auth_handler.get_authenticated_session(driver)
                                session_cookies = session_info.get("cookies", [])
                            else:
                                logger.warning("Authentication failed for WCAG scan - continuing with public page scan")
                        else:
                            logger.info("No login form found - scanning as public page")
                    else:
                        login_page_detected = False
                        logger.info("No login page detected - scanning as public page")
                except Exception as e:
                    logger.warning(f"Error during authentication check: {str(e)} - continuing with public page scan")
            except Exception as e:
                logger.warning(f"Authentication attempt failed: {str(e)} - continuing with public page scan")
        
        # Normalize URL: drop fragment/query-only hash to reduce SPA router stalls
        try:
            if isinstance(url, str) and '#' in url:
                base = url.split('#', 1)[0]
                if base:
                    url = base
        except Exception:
            pass
        
        # Navigate to the target URL
        try:
            driver.get(url)
        except Exception:
            # Retry once with extended timeout on heavy pages
            try:
                logger.warning("First navigation attempt failed, retrying with extended timeout")
                driver.set_page_load_timeout(180)
                driver.get(url)
            except Exception as e:
                logger.exception("Navigation failed on retry for url=%s", url)
                return {"error": str(e), "violations": []}
        
        logger.info("Page loaded, injecting axe-core")

        axe = Axe(driver)
        axe.inject()
        results = axe.run()
        logger.info("axe-core finished. violations=%d", len(results.get("violations", [])))

        # Simplify violations output
        simplified: List[Dict[str, Any]] = []
        for v in results.get("violations", []):
            nodes = []
            for n in v.get("nodes", []):
                nodes.append(
                    {
                        "target": n.get("target", []),
                        "html": n.get("html"),
                        "failureSummary": n.get("failureSummary"),
                    }
                )
            simplified.append(
                {
                    "id": v.get("id"),
                    "impact": v.get("impact"),
                    "description": v.get("description"),
                    "help": v.get("help"),
                    "helpUrl": v.get("helpUrl"),
                    "tags": v.get("tags", []),
                    "nodes": nodes,
                }
            )

        passes = results.get("passes", [])
        inapplicable = results.get("inapplicable", [])

        result_dict = {
            "violations": simplified,
            "passes_count": len(passes),
            "inapplicable_count": len(inapplicable),
        }
        
        # Add login page detection status if credentials were provided
        if credentials:
            result_dict["login_page_detected"] = login_page_detected
        
        return result_dict
    except Exception as e:
        logger.exception("WCAG scan failed for url=%s", url)
        return {"error": str(e), "violations": []}
    finally:
        try:
            if driver:
                driver.quit()
                logger.info("Closed Chrome driver")
        except Exception:
            logger.warning("Failed to close Chrome driver cleanly")


async def run_wcag_scan(url: str, credentials: Optional[Dict[str, str]] = None, session_cookies: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Run WCAG accessibility scan on a URL.
    
    Args:
        url: URL to scan
        credentials: Optional dict with 'username' and 'password' for authentication
        session_cookies: Optional list of cookie dicts to use for authenticated session
        
    Returns:
        Dict containing WCAG violations and results
    """
    return await asyncio.to_thread(_run_axe_sync, url, credentials, session_cookies)


def get_dom_snapshot(url: str) -> str:
    driver = None
    try:
        logger.info("Capturing DOM snapshot | url=%s", url)
        driver = _build_chrome_driver()
        driver.get(url)
        return driver.page_source or ""
    except Exception:
        logger.exception("DOM snapshot failed for url=%s", url)
        return ""
    finally:
        try:
            if driver:
                driver.quit()
        except Exception:
            pass


