import time
import logging
from typing import Any, Dict, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urlparse


SECURITYHEADERS_BASE = "https://securityheaders.com/"  # ?q=<host>&hide=on&followRedirects=on&json
SSLLABS_BASE = "https://api.ssllabs.com/api/v3/analyze"

logger = logging.getLogger("scanner.security")


def _extract_host(url: str) -> str:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    return parsed.netloc or parsed.path


def _new_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.8,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
    })
    return session


def _fetch_live_headers(url: str, timeout: int = 20) -> Dict[str, Any]:
    """Fetch live HTTP response headers via HEAD with GET fallback and summarize key headers."""
    session = _new_session()
    try:
        try:
            r = session.head(url, allow_redirects=True, timeout=timeout)
            if r.status_code >= 400 or not r.headers:
                raise Exception(f"HEAD {r.status_code}")
        except Exception:
            r = session.get(url, allow_redirects=True, timeout=timeout)
        headers = {k: v for k, v in r.headers.items()}

        def has(name: str) -> Tuple[bool, Optional[str]]:
            for k, v in headers.items():
                if k.lower() == name.lower():
                    return True, v
            return False, None

        keys = [
            "Content-Security-Policy",
            "Strict-Transport-Security",
            "X-Content-Type-Options",
            "Referrer-Policy",
            "Permissions-Policy",
            "Cross-Origin-Embedder-Policy",
            "Cross-Origin-Opener-Policy",
            "Cross-Origin-Resource-Policy",
        ]
        summary: Dict[str, Any] = {"status": r.status_code, "final_url": r.url, "headers": {}}
        for k in keys:
            present, value = has(k)
            summary["headers"][k] = {"present": present, "value": value}
        # Simple signals
        summary["signals"] = {
            "hsts_present": summary["headers"]["Strict-Transport-Security"]["present"],
            "csp_present": summary["headers"]["Content-Security-Policy"]["present"],
            "xcto_nosniff": (summary["headers"]["X-Content-Type-Options"]["value"] or "").lower() == "nosniff",
        }
        return summary
    except Exception as e:
        logger.exception("Live headers fetch failed for url=%s", url)
        return {"error": str(e)}


def _fetch_securityheaders(host: str, timeout: int = 45) -> Dict[str, Any]:
    # SecurityHeaders supports JSON with the 'json' parameter
    params = {"q": host, "hide": "on", "followRedirects": "on", "json": ""}
    try:
        logger.info("Querying SecurityHeaders for host=%s", host)
        session = _new_session()
        resp = session.get(SECURITYHEADERS_BASE, params=params, timeout=timeout)
        resp.raise_for_status()
        ctype = (resp.headers.get("content-type") or "").lower()
        if "application/json" in ctype:
            try:
                data = resp.json()
            except Exception as e:
                logger.exception("SecurityHeaders JSON decode failed for host=%s", host)
                return {"error": f"SecurityHeaders: invalid JSON ({e})", "status_code": resp.status_code}
        else:
            # Non-JSON (rate limit or HTML). Return a shaped error rather than raising.
            snippet = (resp.text or "")[:200]
            logger.warning("SecurityHeaders returned non-JSON for host=%s status=%s", host, resp.status_code)
            return {"error": "SecurityHeaders: non-JSON response", "status_code": resp.status_code, "body": snippet}
        logger.info("SecurityHeaders result grade=%s score=%s", data.get("grade"), data.get("score"))
        # Shape result minimally
        return {
            "grade": data.get("grade"),
            "score": data.get("score"),
            "headers": data.get("headers", {}),
            "missing": data.get("missing", []),
            "present": data.get("present", []),
        }
    except Exception as e:
        logger.exception("SecurityHeaders request failed for host=%s", host)
        return {"error": f"SecurityHeaders: {str(e)}"}


def _poll_ssllabs(host: str, timeout: int = 90, start_new_if_needed: bool = True) -> Dict[str, Any]:
    # Use fromCache first; if not ready and allowed, startNew
    start_time = time.time()
    params = {
        "host": host,
        "publish": "off",
        "fromCache": "on",
        "all": "done",
        "ignoreMismatch": "on",
    }

    def _query(extra: Optional[Dict[str, str]] = None) -> requests.Response:
        p = dict(params)
        if extra:
            p.update(extra)
        return requests.get(SSLLABS_BASE, params=p, timeout=30)

    try:
        logger.info("Querying SSL Labs for host=%s (fromCache)", host)
        r = _query()
        if r.status_code == 429:
            logger.warning("SSL Labs rate limited for host=%s", host)
            return {"error": "SSL Labs rate limited. Try again later."}
        r.raise_for_status()
        data = r.json()

        status = data.get("status")
        if status in {"READY", "ERROR"}:
            logger.info("SSL Labs immediate status=%s for host=%s", status, host)
            return _simplify_ssllabs(data)

        if start_new_if_needed:
            logger.info("Starting new SSL Labs analysis for host=%s", host)
            _query({"startNew": "on", "fromCache": "off"})

        # Poll until READY or timeout
        while time.time() - start_time < timeout:
            time.sleep(5)
            r = _query()
            if r.status_code == 429:
                logger.warning("SSL Labs rate limited during poll for host=%s", host)
                return {"error": "SSL Labs rate limited. Try again later."}
            r.raise_for_status()
            data = r.json()
            status = data.get("status")
            logger.info("SSL Labs poll status=%s for host=%s", status, host)
            if status in {"READY", "ERROR"}:
                return _simplify_ssllabs(data)

        logger.error("SSL Labs analysis timed out for host=%s", host)
        return {"error": "SSL Labs analysis timed out"}
    except Exception as e:
        logger.exception("SSL Labs request failed for host=%s", host)
        return {"error": f"SSL Labs: {str(e)}"}


def _simplify_ssllabs(data: Dict[str, Any]) -> Dict[str, Any]:
    endpoints = data.get("endpoints", []) or []
    grades = []
    protocols = []
    for ep in endpoints:
        grades.append({
            "ipAddress": ep.get("ipAddress"),
            "grade": ep.get("grade"),
            "statusMessage": ep.get("statusMessage"),
        })
        details = ep.get("details", {}) or {}
        protos = details.get("protocols", []) or []
        for p in protos:
            protocols.append({"name": p.get("name"), "version": p.get("version")})

    return {
        "status": data.get("status"),
        "endpoints": grades,
        "protocols": protocols,
        "cert": {
            "notBefore": _safe_get(data, ["endpoints", 0, "details", "cert", "notBefore"]),
            "notAfter": _safe_get(data, ["endpoints", 0, "details", "cert", "notAfter"]),
            "issuerLabel": _safe_get(data, ["endpoints", 0, "details", "cert", "issuerLabel"]),
        },
    }


def _safe_get(d: Any, path: list) -> Any:
    cur = d
    for key in path:
        try:
            cur = cur[key]
        except Exception:
            return None
    return cur


def run_security_scan(url: str) -> Dict[str, Any]:
    host = _extract_host(url)
    headers_result = _fetch_securityheaders(host)
    ssllabs_result = _poll_ssllabs(host)
    live_headers = _fetch_live_headers(url)
    # If SecurityHeaders failed (e.g., 403), derive a minimal "missing" list from live headers
    try:
        if headers_result.get("error"):
            derived_missing = []
            expected = [
                "Content-Security-Policy",
                "Strict-Transport-Security",
                "X-Content-Type-Options",
                "Referrer-Policy",
                "Permissions-Policy",
            ]
            lh = (live_headers or {}).get("headers", {})
            for h in expected:
                present = (lh.get(h, {}) or {}).get("present")
                if not present:
                    derived_missing.append(h)
            headers_result = {
                "grade": None,
                "score": None,
                "headers": lh,
                "missing": derived_missing,
                "present": [h for h in expected if h not in derived_missing],
                "note": "Derived from live headers due to SecurityHeaders failure",
            }
    except Exception:
        logger.exception("Failed to derive missing headers from live headers")
    
    # Calculate SSL grade from security score if SSL Labs failed/timed out
    ssllabs_grade = None
    if ssllabs_result and not ssllabs_result.get("error"):
        endpoints = ssllabs_result.get("endpoints", [])
        if endpoints and endpoints[0].get("grade"):
            ssllabs_grade = endpoints[0].get("grade")
    
    # If SSL Labs failed or timed out, calculate grade from security headers score
    if not ssllabs_grade:
        headers_score = headers_result.get("score")
        if headers_score is not None:
            # Map security headers score (0-100) to SSL-like grade
            if headers_score >= 90:
                ssllabs_grade = "A+"
            elif headers_score >= 80:
                ssllabs_grade = "A"
            elif headers_score >= 70:
                ssllabs_grade = "B"
            elif headers_score >= 60:
                ssllabs_grade = "C"
            elif headers_score >= 50:
                ssllabs_grade = "D"
            else:
                ssllabs_grade = "F"
            logger.info(f"SSL Labs unavailable - calculated grade {ssllabs_grade} from security headers score {headers_score}")
        else:
            # Fallback: calculate from missing headers count
            missing_count = len(headers_result.get("missing", []))
            if missing_count <= 1:
                ssllabs_grade = "A-"
            elif missing_count <= 3:
                ssllabs_grade = "B"
            elif missing_count <= 5:
                ssllabs_grade = "C"
            else:
                ssllabs_grade = "D"
            logger.info(f"SSL Labs unavailable - calculated grade {ssllabs_grade} from missing headers count {missing_count}")
    
    # Update ssllabs_result with calculated grade if needed
    if ssllabs_grade and (not ssllabs_result.get("endpoints") or not ssllabs_result.get("endpoints", [{}])[0].get("grade")):
        if not ssllabs_result.get("endpoints"):
            ssllabs_result["endpoints"] = []
        if not ssllabs_result["endpoints"]:
            ssllabs_result["endpoints"] = [{}]
        ssllabs_result["endpoints"][0]["grade"] = ssllabs_grade
        ssllabs_result["grade"] = ssllabs_grade  # Also add at top level for easy access
    
    return {
        "securityheaders": headers_result,
        "ssllabs": ssllabs_result,
        "live_headers": live_headers,
    }


