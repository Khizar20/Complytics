import logging
from typing import Dict, Any, Optional, List
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
import time

logger = logging.getLogger("auth_handler")


class AuthenticationHandler:
    """
    Handles authentication for login-protected pages during UI testing scans.
    Detects login pages, finds login forms, and performs authentication.
    """
    
    def __init__(self, credentials: Dict[str, str]):
        self.credentials = credentials
        self.logger = logging.getLogger("auth_handler")
        self.authenticated_session = None
    
    def detect_login_page(self, driver) -> bool:
        """
        Detect if current page is a login page based on common indicators.
        
        Returns:
            bool: True if login page is detected
        """
        login_indicators = [
            "input[type='password']",
            "input[name*='password']",
            "input[id*='password']",
            "input[placeholder*='password']",
            "form[action*='login']",
            "form[id*='login']",
            "form[class*='login']",
            ".login-form",
            "#login",
            "[data-testid*='login']",
            "[class*='signin']",
            "[class*='sign-in']"
        ]
        
        for selector in login_indicators:
            try:
                if driver.find_element(By.CSS_SELECTOR, selector):
                    self.logger.info(f"Login page detected using selector: {selector}")
                    return True
            except NoSuchElementException:
                continue
        
        # Additional text-based detection
        page_text = driver.page_source.lower()
        login_keywords = [
            "sign in", "log in", "login", "signin", "authenticate",
            "enter your password", "forgot password", "remember me"
        ]
        
        keyword_count = sum(1 for keyword in login_keywords if keyword in page_text)
        if keyword_count >= 2:
            self.logger.info(f"Login page detected by keywords (count: {keyword_count})")
            return True
            
        return False
    
    def find_login_form(self, driver) -> Optional[Dict[str, Any]]:
        """
        Find and analyze login form elements.
        
        Returns:
            Dict containing form elements or None if not found
        """
        try:
            # Look for password field first (strongest indicator)
            password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            
            # Find associated username/email field
            username_field = None
            username_selectors = [
                "input[type='email']",
                "input[name*='email']",
                "input[name*='username']",
                "input[name*='user']",
                "input[id*='email']",
                "input[id*='username']",
                "input[id*='user']",
                "input[type='text']"
            ]
            
            for selector in username_selectors:
                try:
                    username_field = driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue
            
            if username_field and password_field:
                # Find the form element
                form_element = None
                try:
                    form_element = password_field.find_element(By.XPATH, "./ancestor::form")
                except NoSuchElementException:
                    # If no form ancestor, create a virtual form
                    form_element = None
                
                return {
                    "username_field": username_field,
                    "password_field": password_field,
                    "form": form_element,
                    "username_selector": username_field.get_attribute("name") or username_field.get_attribute("id"),
                    "password_selector": password_field.get_attribute("name") or password_field.get_attribute("id")
                }
        except NoSuchElementException:
            self.logger.warning("No password field found on page")
        except Exception as e:
            self.logger.error(f"Error finding login form: {str(e)}")
        
        return None
    
    def perform_login(self, driver, login_form: Dict[str, Any]) -> bool:
        """
        Attempt to login with provided credentials.
        
        Args:
            driver: Selenium WebDriver instance
            login_form: Form elements from find_login_form()
            
        Returns:
            bool: True if login appears successful
        """
        try:
            self.logger.info("Attempting to perform login")
            
            # Clear and fill username
            username_field = login_form["username_field"]
            username_field.clear()
            username_field.send_keys(self.credentials.get("username", ""))
            self.logger.info("Username field filled")
            
            # Clear and fill password
            password_field = login_form["password_field"]
            password_field.clear()
            password_field.send_keys(self.credentials.get("password", ""))
            self.logger.info("Password field filled")
            
            # Small delay to ensure fields are filled
            time.sleep(0.5)
            
            # Find and click submit button
            submit_success = False
            submit_selectors = [
                "button#submit-login",  # Specific ID from the form
                "#submit-login",  # Direct ID selector
                "button[name='submit-login']",  # Name attribute
                "button#submit",
                "input#submit", 
                "button[type='submit']",
                "input[type='submit']",
                "button.submit",
                ".login-button",
                ".submit-button",
                "#login-button",
                "#submit-button",
                "[data-testid*='submit']",
                "[data-testid*='login']",
                "button"
            ]
            
            for selector in submit_selectors:
                try:
                    submit_btn = driver.find_element(By.CSS_SELECTOR, selector)
                    
                    # Scroll button into view to avoid click interception
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
                    time.sleep(0.3)  # Wait for scroll
                    
                    # Wait for button to be clickable
                    try:
                        WebDriverWait(driver, 2).until(
                            EC.element_to_be_clickable(submit_btn)
                        )
                    except TimeoutException:
                        pass  # Continue anyway
                    
                    # Try regular click first
                    try:
                        submit_btn.click()
                        submit_success = True
                        self.logger.info(f"Submit button clicked using selector: {selector}")
                        break
                    except Exception as click_error:
                        # If click is intercepted, try JavaScript click
                        if "click intercepted" in str(click_error).lower() or "not clickable" in str(click_error).lower():
                            self.logger.warning(f"Click intercepted for {selector}, trying JavaScript click")
                            try:
                                driver.execute_script("arguments[0].click();", submit_btn)
                                submit_success = True
                                self.logger.info(f"Submit button clicked using JavaScript: {selector}")
                                break
                            except Exception as js_error:
                                self.logger.warning(f"JavaScript click also failed: {str(js_error)}")
                                continue
                        else:
                            raise
                            
                except NoSuchElementException:
                    continue
                except Exception as e:
                    self.logger.warning(f"Error with selector {selector}: {str(e)}")
                    continue
            
            # If CSS selectors didn't work, try XPath for text-based matching
            if not submit_success:
                xpath_selectors = [
                    "//button[@id='submit-login']",  # Specific ID
                    "//button[@name='submit-login']",  # Name attribute
                    "//button[@id='submit']",
                    "//input[@id='submit']",
                    "//button[contains(text(), 'Login')]",
                    "//button[contains(text(), 'Sign In')]",
                    "//button[contains(text(), 'Log In')]",
                    "//button[contains(text(), 'Submit')]",
                    "//input[@type='submit']",
                    "//button[@type='submit']"
                ]
                
                for xpath in xpath_selectors:
                    try:
                        submit_btn = driver.find_element(By.XPATH, xpath)
                        
                        # Scroll button into view
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
                        time.sleep(0.3)
                        
                        # Wait for button to be clickable
                        try:
                            WebDriverWait(driver, 2).until(
                                EC.element_to_be_clickable(submit_btn)
                            )
                        except TimeoutException:
                            pass
                        
                        # Try regular click first
                        try:
                            submit_btn.click()
                            submit_success = True
                            self.logger.info(f"Submit button clicked using XPath: {xpath}")
                            break
                        except Exception as click_error:
                            # If click is intercepted, try JavaScript click
                            if "click intercepted" in str(click_error).lower() or "not clickable" in str(click_error).lower():
                                self.logger.warning(f"Click intercepted for XPath {xpath}, trying JavaScript click")
                                try:
                                    driver.execute_script("arguments[0].click();", submit_btn)
                                    submit_success = True
                                    self.logger.info(f"Submit button clicked using JavaScript XPath: {xpath}")
                                    break
                                except Exception as js_error:
                                    self.logger.warning(f"JavaScript click also failed: {str(js_error)}")
                                    continue
                            else:
                                raise
                                
                    except NoSuchElementException:
                        continue
                    except Exception as e:
                        self.logger.warning(f"Error with XPath {xpath}: {str(e)}")
                        continue
            
            if not submit_success:
                # Try submitting the form directly if we have a form element
                if login_form.get("form"):
                    try:
                        form = login_form["form"]
                        # Try JavaScript form submission
                        driver.execute_script("arguments[0].submit();", form)
                        submit_success = True
                        self.logger.info("Form submitted using JavaScript")
                    except Exception as e:
                        self.logger.warning(f"Could not submit form via JavaScript: {str(e)}")
                
                # Try pressing Enter on password field
                if not submit_success:
                    try:
                        password_field.send_keys(Keys.RETURN)
                        submit_success = True
                        self.logger.info("Login submitted using Enter key")
                    except Exception as e:
                        self.logger.warning(f"Could not submit form using Enter key: {str(e)}")
                
                # Last resort: Try to find and click any submit button within the form
                if not submit_success and login_form.get("form"):
                    try:
                        form = login_form["form"]
                        # Find submit button within the form
                        submit_in_form = form.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit'], button#submit-login, #submit-login")
                        driver.execute_script("arguments[0].click();", submit_in_form)
                        submit_success = True
                        self.logger.info("Submit button clicked within form using JavaScript")
                    except Exception as e:
                        self.logger.warning(f"Could not find/click submit button in form: {str(e)}")
            
            if submit_success:
                # Wait for navigation or success indicator
                try:
                    WebDriverWait(driver, 10).until(
                        lambda d: self.detect_successful_login(d) or 
                                 d.current_url != driver.current_url
                    )
                    self.logger.info("Login appears successful")
                    return True
                except TimeoutException:
                    self.logger.warning("Login timeout - checking for success indicators")
                    return self.detect_successful_login(driver)
            
        except Exception as e:
            self.logger.error(f"Login failed: {str(e)}")
        
        return False
    
    def detect_successful_login(self, driver) -> bool:
        """
        Detect if login was successful based on page indicators.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            bool: True if login appears successful
        """
        try:
            current_url = driver.current_url.lower()
            page_source = driver.page_source.lower()
            
            # Success indicators
            success_indicators = [
                "dashboard", "profile", "account", "logout", "welcome",
                "admin", "panel", "home", "main", "overview"
            ]
            
            # Failure indicators
            failure_indicators = [
                "invalid", "incorrect", "wrong", "error", "failed",
                "denied", "unauthorized", "forbidden"
            ]
            
            # Check for failure indicators first
            for indicator in failure_indicators:
                if indicator in current_url or indicator in page_source:
                    self.logger.warning(f"Login failure detected: {indicator}")
                    return False
            
            # Check for success indicators
            success_count = 0
            for indicator in success_indicators:
                if indicator in current_url or indicator in page_source:
                    success_count += 1
            
            # Also check for absence of login form
            try:
                driver.find_element(By.CSS_SELECTOR, "input[type='password']")
                # If password field still exists, might not be logged in
                if success_count < 2:
                    return False
            except NoSuchElementException:
                # No password field found - good sign
                pass
            
            # URL change is a good indicator
            if current_url != driver.current_url:
                return True
            
            return success_count >= 1
            
        except Exception as e:
            self.logger.error(f"Error detecting login success: {str(e)}")
            return False
    
    def get_authenticated_session(self, driver) -> Dict[str, Any]:
        """
        Extract session information after successful authentication.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            Dict containing session cookies and other auth data
        """
        try:
            cookies = driver.get_cookies()
            session_cookies = {}
            
            # Extract important session cookies
            important_cookies = [
                "sessionid", "JSESSIONID", "PHPSESSID", "ASP.NET_SessionId",
                "connect.sid", "auth_token", "access_token", "jwt"
            ]
            
            for cookie in cookies:
                if cookie["name"].lower() in [name.lower() for name in important_cookies]:
                    session_cookies[cookie["name"]] = cookie["value"]
            
            return {
                "cookies": cookies,
                "session_cookies": session_cookies,
                "current_url": driver.current_url,
                "page_title": driver.title
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting session: {str(e)}")
            return {}
    
    def is_authenticated(self, driver) -> bool:
        """
        Check if current page indicates user is authenticated.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            bool: True if appears authenticated
        """
        try:
            # Check for logout links/buttons
            logout_selectors = [
                "a[href*='logout']",
                ".logout", "#logout"
            ]
            
            for selector in logout_selectors:
                try:
                    driver.find_element(By.CSS_SELECTOR, selector)
                    return True
                except NoSuchElementException:
                    continue
            
            # Try XPath for text-based logout detection
            logout_xpath_selectors = [
                "//button[contains(text(), 'Logout')]",
                "//a[contains(text(), 'Logout')]",
                "//button[contains(text(), 'Sign Out')]",
                "//a[contains(text(), 'Sign Out')]"
            ]
            
            for xpath in logout_xpath_selectors:
                try:
                    driver.find_element(By.XPATH, xpath)
                    return True
                except NoSuchElementException:
                    continue
            
            # Check URL patterns
            current_url = driver.current_url.lower()
            auth_url_patterns = [
                "/dashboard", "/admin", "/profile", "/account",
                "/home", "/main", "/panel"
            ]
            
            for pattern in auth_url_patterns:
                if pattern in current_url:
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking authentication status: {str(e)}")
            return False
