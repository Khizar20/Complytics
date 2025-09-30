import logging
from typing import Any, Dict, List

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException


logger = logging.getLogger("scanner.interaction")


def _build_chrome_driver(page_load_timeout: int = 60) -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    # Reduce renderer stalls and noisy GPU/WebGL warnings in CI/headless
    options.add_argument("--use-gl=swiftshader")
    options.add_argument("--enable-unsafe-swiftshader")
    try:
        options.page_load_strategy = "eager"
    except Exception:
        pass
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(page_load_timeout)
    return driver


def _safe_text(el) -> str:
    try:
        return (el.text or "").strip()
    except Exception:
        return ""


def _sample_value(input_type: str) -> str:
    t = (input_type or "text").lower()
    return {
        "email": "tester@example.com",
        "password": "P@ssw0rd123!",
        "tel": "+1234567890",
        "search": "test",
        "number": "42",
        "url": "https://example.com",
    }.get(t, "test")


def _interact_with_forms(driver: webdriver.Chrome) -> List[Dict[str, Any]]:
    steps: List[Dict[str, Any]] = []
    forms = driver.find_elements(By.TAG_NAME, "form")
    # Record forms count for downstream reporting
    try:
        steps.append({"action": "forms-meta", "forms_count": len(forms)})
    except Exception:
        pass
    for idx, form in enumerate(forms[:5]):  # cap to avoid long runs
        try:
            inputs = form.find_elements(By.CSS_SELECTOR, "input, textarea, select")
            for inp in inputs[:8]:
                try:
                    typ = (inp.get_attribute("type") or inp.tag_name or "text").lower()
                    name = inp.get_attribute("name") or inp.get_attribute("id") or ""
                    if inp.tag_name.lower() in {"select"}:
                        steps.append({"action": "select-skip", "field": name})
                        continue
                    if typ in {"hidden", "submit", "button", "image", "file"}:
                        continue
                    inp.clear()
                    val = _sample_value(typ)
                    inp.send_keys(val)
                    steps.append({"action": "type", "field": name, "type": typ, "value": val})
                except Exception as e:
                    steps.append({"action": "type", "error": str(e)})
            # try submit
            try:
                form.submit()
                steps.append({"action": "submit", "form_index": idx, "status": "submitted"})
            except Exception:
                try:
                    btn = form.find_element(By.CSS_SELECTOR, "button[type=submit], input[type=submit]")
                    btn.click()
                    steps.append({"action": "click-submit", "form_index": idx, "status": "clicked"})
                except Exception as e:
                    steps.append({"action": "submit", "form_index": idx, "error": str(e)})
        except Exception as e:
            steps.append({"action": "form", "index": idx, "error": str(e)})
    return steps


def _keyboard_navigation(driver: webdriver.Chrome) -> List[Dict[str, Any]]:
    steps: List[Dict[str, Any]] = []
    try:
        body = driver.find_element(By.TAG_NAME, "body")
        for _ in range(10):
            body.send_keys(Keys.TAB)
            active = driver.switch_to.active_element
            desc = active.get_attribute("outerHTML")
            steps.append({"action": "tab", "focused": (desc or "")[:200]})
    except Exception as e:
        steps.append({"action": "tab", "error": str(e)})
    return steps


def run_interactive_test(url: str) -> Dict[str, Any]:
    driver = None
    log: Dict[str, Any] = {"steps": []}
    try:
        logger.info("Interactive test start | url=%s", url)
        driver = _build_chrome_driver()
        try:
            driver.get(url)
        except TimeoutException as e:
            # Continue with whatever loaded to still collect partial signals
            log["warning"] = f"Navigation timeout: {e}"
        log["title"] = driver.title
        log["url"] = driver.current_url
        try:
            log["steps"] += _keyboard_navigation(driver)
        except Exception as e:
            log["steps"].append({"action": "tab", "error": str(e)})
        try:
            log["steps"] += _interact_with_forms(driver)
        except Exception as e:
            log["steps"].append({"action": "forms", "error": str(e)})
        log["final_url"] = driver.current_url
    except Exception as e:
        logger.exception("Interactive test failed for url=%s", url)
        log["error"] = str(e)
    finally:
        try:
            if driver:
                driver.quit()
        except Exception:
            pass
    return log


