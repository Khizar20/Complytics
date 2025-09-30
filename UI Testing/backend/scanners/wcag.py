import asyncio
import logging
from typing import Any, Dict, List

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from axe_selenium_python import Axe

logger = logging.getLogger("scanner.wcag")


def _build_chrome_driver(page_load_timeout: int = 60) -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    # Use faster/eager page load to mitigate renderer timeouts on heavy pages
    try:
        options.page_load_strategy = "eager"
    except Exception:
        pass
    # Use Selenium Manager to resolve the correct ChromeDriver automatically
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(page_load_timeout)
    return driver


def _run_axe_sync(url: str) -> Dict[str, Any]:
    driver = None
    try:
        logger.info("Launching headless Chrome for WCAG scan | url=%s", url)
        driver = _build_chrome_driver()
        driver.get(url)
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

        return {
            "violations": simplified,
            "passes_count": len(passes),
            "inapplicable_count": len(inapplicable),
        }
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


async def run_wcag_scan(url: str) -> Dict[str, Any]:
    return await asyncio.to_thread(_run_axe_sync, url)


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

