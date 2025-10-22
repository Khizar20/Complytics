"""
Whole-Site Scanner
Orchestrates crawling and testing of multiple pages across a website.
Aggregates results for comprehensive accessibility and security analysis.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import time

from ui_testing.scanners.crawler import crawl_website
from ui_testing.scanners.wcag import run_wcag_scan
from ui_testing.scanners.security import run_security_scan
from ui_testing.scanners.interaction import run_interactive_test
from ui_testing.crawl_cache import (
    get_cached_crawl,
    set_cached_crawl,
    get_crawl_from_db,
    persist_crawl_to_db
)

logger = logging.getLogger("scanner.site")


class SiteScanOrchestrator:
    """
    Orchestrates whole-site testing by:
    1. Discovering pages via crawling
    2. Running WCAG + Security scans on each page
    3. Aggregating results into site-wide report
    """
    
    def __init__(
        self,
        max_pages: int = 50,
        max_depth: int = 3,
        scan_mode: str = "all",
        parallel_scans: int = 3,
        db = None,
        organization_id: str = None
    ):
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.scan_mode = scan_mode
        self.parallel_scans = parallel_scans
        self.db = db
        self.organization_id = organization_id
    
    async def scan_page(
        self,
        url: str,
        page_num: int,
        total_pages: int
    ) -> Dict[str, Any]:
        """Scan a single page"""
        progress_pct = (page_num / total_pages) * 100
        logger.info(f"\n{'='*70}")
        logger.info(f"📊 SCANNING PAGE [{page_num}/{total_pages}] ({progress_pct:.1f}%)")
        logger.info(f"{'='*70}")
        logger.info(f"URL: {url}")
        logger.info(f"Mode: {self.scan_mode}")
        
        result = {
            "url": url,
            "scan_time": datetime.utcnow().isoformat(),
            "wcag_results": None,
            "security_results": None,
            "interaction_results": None,
            "errors": []
        }
        
        try:
            # Run WCAG scan
            if self.scan_mode in ["all", "accessibility"]:
                try:
                    logger.info("  🔍 Running WCAG accessibility scan...")
                    wcag_result = await run_wcag_scan(url)
                    result["wcag_results"] = wcag_result
                    violations_count = len(wcag_result.get("violations", []))
                    logger.info(f"  ✓ WCAG scan complete: {violations_count} violations found")
                except Exception as e:
                    logger.error(f"  ✗ WCAG scan failed: {e}")
                    result["errors"].append(f"WCAG scan failed: {str(e)}")
            
            # Run Security scan (only on unique domains/subdomains)
            if self.scan_mode in ["all", "security"]:
                # Note: Security headers are typically domain-level, so we can optimize
                # by only scanning once per domain
                try:
                    logger.info("  🔒 Running security scan...")
                    security_result = await run_security_scan(url)
                    result["security_results"] = security_result
                    grade = security_result.get("securityheaders", {}).get("grade", "N/A")
                    logger.info(f"  ✓ Security scan complete: Grade {grade}")
                except Exception as e:
                    logger.error(f"  ✗ Security scan failed: {e}")
                    result["errors"].append(f"Security scan failed: {str(e)}")
            
            # Run interaction test (lightweight)
            if self.scan_mode == "all":
                try:
                    logger.info("  ⌨️  Running interaction test...")
                    interaction_result = await run_interactive_test(url)
                    result["interaction_results"] = interaction_result
                    logger.info(f"  ✓ Interaction test complete")
                except Exception as e:
                    logger.error(f"  ✗ Interaction test failed: {e}")
                    result["errors"].append(f"Interaction test failed: {str(e)}")
        
        except Exception as e:
            logger.exception(f"  ✗ Page scan failed: {e}")
            result["errors"].append(f"Page scan failed: {str(e)}")
        
        error_count = len(result["errors"])
        if error_count == 0:
            logger.info(f"✅ Page scan completed successfully\n")
        else:
            logger.warning(f"⚠️  Page scan completed with {error_count} error(s)\n")
        
        return result
    
    async def scan_pages_batch(
        self,
        urls: List[str]
    ) -> List[Dict[str, Any]]:
        """Scan multiple pages in parallel batches"""
        results = []
        total_pages = len(urls)
        batch_count = (len(urls) + self.parallel_scans - 1) // self.parallel_scans
        
        logger.info(f"\n{'#'*70}")
        logger.info(f"🚀 STARTING BATCH SCANNING")
        logger.info(f"{'#'*70}")
        logger.info(f"Total pages: {total_pages}")
        logger.info(f"Parallel scans: {self.parallel_scans}")
        logger.info(f"Batches: {batch_count}")
        logger.info(f"Scan mode: {self.scan_mode}")
        logger.info(f"{'#'*70}\n")
        
        # Process in batches to avoid overwhelming the system
        for batch_idx, i in enumerate(range(0, len(urls), self.parallel_scans), 1):
            batch = urls[i:i + self.parallel_scans]
            logger.info(f"\n┌─{'─'*68}┐")
            logger.info(f"│ BATCH {batch_idx}/{batch_count} - Scanning {len(batch)} page(s) in parallel...{' '*(26-len(str(batch_idx))-len(str(batch_count))-len(str(len(batch))))}│")
            logger.info(f"└─{'─'*68}┘")
            
            batch_tasks = [
                self.scan_page(url, idx + i + 1, total_pages)
                for idx, url in enumerate(batch)
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for url, scan_result in zip(batch, batch_results):
                if isinstance(scan_result, Exception):
                    logger.error(f"⚠️  Batch scan error for {url}: {scan_result}")
                    results.append({
                        "url": url,
                        "scan_time": datetime.utcnow().isoformat(),
                        "wcag_results": None,
                        "security_results": None,
                        "interaction_results": None,
                        "errors": [f"Scan exception: {str(scan_result)}"]
                    })
                else:
                    results.append(scan_result)
            
            logger.info(f"✓ Batch {batch_idx}/{batch_count} complete ({len(results)}/{total_pages} pages scanned)")
            
            # Rate limiting between batches
            if i + self.parallel_scans < len(urls):
                logger.info(f"⏳ Waiting 2s before next batch...\n")
                await asyncio.sleep(2)
        
        return results
    
    def aggregate_wcag_results(self, page_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate WCAG results across all pages"""
        total_violations = []
        violations_by_page = {}
        violations_by_rule = {}
        impact_counts = {"critical": 0, "serious": 0, "moderate": 0, "minor": 0}
        pages_with_issues = 0
        
        for page in page_results:
            url = page["url"]
            wcag = page.get("wcag_results", {})
            
            if not wcag or wcag.get("error"):
                continue
            
            violations = wcag.get("violations", [])
            
            if violations:
                pages_with_issues += 1
                violations_by_page[url] = len(violations)
            
            for violation in violations:
                # Track by rule ID
                rule_id = violation.get("id")
                if rule_id not in violations_by_rule:
                    violations_by_rule[rule_id] = {
                        "id": rule_id,
                        "description": violation.get("description"),
                        "impact": violation.get("impact"),
                        "help": violation.get("help"),
                        "helpUrl": violation.get("helpUrl"),
                        "tags": violation.get("tags", []),
                        "pages_affected": set(),
                        "total_instances": 0,
                        "sample_nodes": []  # Store sample nodes with HTML snippets
                    }
                
                violations_by_rule[rule_id]["pages_affected"].add(url)
                violations_by_rule[rule_id]["total_instances"] += len(violation.get("nodes", []))
                
                # Store sample nodes (limit to 5 samples per rule across all pages)
                if len(violations_by_rule[rule_id]["sample_nodes"]) < 5:
                    for node in violation.get("nodes", [])[:2]:  # Take up to 2 nodes per page
                        if len(violations_by_rule[rule_id]["sample_nodes"]) < 5:
                            violations_by_rule[rule_id]["sample_nodes"].append({
                                "html": node.get("html", ""),
                                "target": node.get("target", []),
                                "failureSummary": node.get("failureSummary", ""),
                                "page_url": url
                            })
                
                # Count by impact
                impact = violation.get("impact", "minor")
                impact_counts[impact] = impact_counts.get(impact, 0) + 1
                
                # Add to total violations
                total_violations.append({
                    "url": url,
                    "rule": rule_id,
                    "impact": impact,
                    "description": violation.get("description"),
                    "instances": len(violation.get("nodes", []))
                })
        
        # Convert violations_by_rule to list
        violations_summary = []
        for rule_id, data in violations_by_rule.items():
            violations_summary.append({
                "id": rule_id,
                "description": data["description"],
                "impact": data["impact"],
                "help": data["help"],
                "helpUrl": data["helpUrl"],
                "tags": data["tags"],
                "pages_affected": len(data["pages_affected"]),
                "pages_affected_urls": list(data["pages_affected"])[:10],  # Limit to 10 examples
                "total_instances": data["total_instances"],
                "sample_nodes": data["sample_nodes"]  # Include sample HTML snippets
            })
        
        # Sort by impact and page count
        impact_order = {"critical": 0, "serious": 1, "moderate": 2, "minor": 3}
        violations_summary.sort(
            key=lambda x: (impact_order.get(x["impact"], 4), -x["pages_affected"])
        )
        
        return {
            "total_pages_scanned": len(page_results),
            "pages_with_issues": pages_with_issues,
            "total_violations": len(total_violations),
            "unique_rules_violated": len(violations_by_rule),
            "impact_counts": impact_counts,
            "violations_by_page": violations_by_page,
            "violations_summary": violations_summary,
            "top_issues": violations_summary[:10]  # Top 10 most critical/widespread issues
        }
    
    def aggregate_security_results(self, page_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate security results (typically domain-level)"""
        # Security headers are usually consistent across a domain
        # We'll take the first valid security scan and note any variations
        
        primary_security = None
        security_variations = []
        
        for page in page_results:
            security = page.get("security_results")
            if security and not security.get("error"):
                if not primary_security:
                    primary_security = {
                        "url": page["url"],
                        "securityheaders": security.get("securityheaders"),
                        "ssllabs": security.get("ssllabs"),
                        "live_headers": security.get("live_headers")
                    }
                else:
                    # Check for variations
                    current_headers = security.get("live_headers", {}).get("headers", {})
                    primary_headers = primary_security["live_headers"].get("headers", {})
                    
                    if current_headers != primary_headers:
                        security_variations.append({
                            "url": page["url"],
                            "note": "Different security headers detected"
                        })
        
        if not primary_security:
            return {
                "error": "No valid security scan results",
                "pages_scanned": len(page_results)
            }
        
        return {
            "primary_scan": primary_security,
            "variations_detected": len(security_variations),
            "variations": security_variations,
            "note": "Security headers are typically consistent across a domain"
        }
    
    async def scan_pages_accessibility_only(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Scan pages for accessibility only (no security)"""
        results = []
        total_pages = len(urls)
        
        # More aggressive parallelism for accessibility-only
        batch_size = min(self.parallel_scans * 2, 8)
        batch_count = (len(urls) + batch_size - 1) // batch_size
        
        logger.info(f"\n{'#'*70}")
        logger.info(f"🚀 ACCESSIBILITY-ONLY SCANNING")
        logger.info(f"{'#'*70}")
        logger.info(f"Total pages: {total_pages}")
        logger.info(f"Parallel scans: {batch_size}")
        logger.info(f"Batches: {batch_count}")
        logger.info(f"{'#'*70}\n")
        
        for batch_idx, i in enumerate(range(0, len(urls), batch_size), 1):
            batch = urls[i:i + batch_size]
            logger.info(f"\n┌─{'─'*68}┐")
            logger.info(f"│ BATCH {batch_idx}/{batch_count} - Accessibility scanning {len(batch)} page(s)...{' '*(15-len(str(batch_idx))-len(str(batch_count)))}│")
            logger.info(f"└─{'─'*68}┘")
            
            batch_tasks = [
                self.scan_page_accessibility_only(url, idx + i + 1, total_pages)
                for idx, url in enumerate(batch)
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for url, scan_result in zip(batch, batch_results):
                if isinstance(scan_result, Exception):
                    logger.error(f"⚠️  Batch scan error for {url}: {scan_result}")
                    results.append({
                        "url": url,
                        "scan_time": datetime.utcnow().isoformat(),
                        "wcag_results": None,
                        "errors": [f"Scan exception: {str(scan_result)}"]
                    })
                else:
                    results.append(scan_result)
            
            logger.info(f"✓ Batch {batch_idx}/{batch_count} complete ({len(results)}/{total_pages} pages scanned)")
            
            # Shorter delay for accessibility-only
            if i + batch_size < len(urls):
                logger.info(f"⏳ Waiting 1s before next batch...\n")
                await asyncio.sleep(1)
        
        return results
    
    async def scan_page_accessibility_only(self, url: str, page_num: int, total_pages: int) -> Dict[str, Any]:
        """Scan a single page for accessibility only (no security)"""
        progress_pct = (page_num / total_pages) * 100
        logger.info(f"\n{'='*70}")
        logger.info(f"📊 ACCESSIBILITY SCAN [{page_num}/{total_pages}] ({progress_pct:.1f}%)")
        logger.info(f"{'='*70}")
        logger.info(f"URL: {url}")
        
        result = {
            "url": url,
            "scan_time": datetime.utcnow().isoformat(),
            "wcag_results": None,
            "errors": []
        }
        
        try:
            logger.info("  🔍 Running WCAG accessibility scan...")
            wcag_result = await run_wcag_scan(url)
            result["wcag_results"] = wcag_result
            violations_count = len(wcag_result.get("violations", []))
            logger.info(f"  ✓ WCAG scan complete: {violations_count} violations found")
        except Exception as e:
            logger.error(f"  ✗ Accessibility scan failed: {e}")
            result["errors"].append(f"Accessibility scan failed: {str(e)}")
        
        error_count = len(result["errors"])
        if error_count == 0:
            logger.info(f"✅ Accessibility scan completed successfully\n")
        else:
            logger.warning(f"⚠️  Accessibility scan completed with {error_count} error(s)\n")
        
        return result
    
    def generate_site_summary(
        self,
        crawl_result: Dict[str, Any],
        page_results: List[Dict[str, Any]],
        wcag_aggregate: Dict[str, Any],
        security_aggregate: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate executive summary for the whole site"""
        total_errors = sum(len(p.get("errors", [])) for p in page_results)
        pages_scanned_successfully = len([p for p in page_results if not p.get("errors")])
        
        # Calculate accessibility score (0-100)
        # Formula: Weighted deduction based on violation severity
        # Use logarithmic scale to handle high violation counts better
        import math
        
        impact_counts = wcag_aggregate.get("impact_counts", {})
        critical = impact_counts.get("critical", 0)
        serious = impact_counts.get("serious", 0)
        moderate = impact_counts.get("moderate", 0)
        minor = impact_counts.get("minor", 0)
        
        # Base deduction per violation (diminishing returns for many violations)
        # Formula balances severity while preventing scores from hitting 0 too easily
        critical_deduction = min(critical * 2.5, 40)  # Cap at 40 points
        serious_deduction = min(serious * 1.5, 30)    # Cap at 30 points
        moderate_deduction = min(moderate * 0.8, 25)  # Cap at 25 points
        minor_deduction = min(minor * 0.3, 10)        # Cap at 10 points
        
        total_deduction = critical_deduction + serious_deduction + moderate_deduction + minor_deduction
        score = max(0, min(100, 100 - total_deduction))
        
        return {
            "scan_timestamp": datetime.utcnow().isoformat(),
            "site_url": crawl_result.get("urls", [""])[0] if crawl_result.get("urls") else "unknown",
            "crawl_stats": crawl_result.get("stats", {}),
            "pages_discovered": len(crawl_result.get("urls", [])),
            "pages_scanned": len(page_results),
            "pages_scanned_successfully": pages_scanned_successfully,
            "pages_with_errors": total_errors,
            "accessibility_score": round(score, 1),
            "accessibility_summary": {
                "total_violations": wcag_aggregate.get("total_violations", 0),
                "unique_issues": wcag_aggregate.get("unique_rules_violated", 0),
                "pages_with_issues": wcag_aggregate.get("pages_with_issues", 0),
                "critical_issues": wcag_aggregate.get("impact_counts", {}).get("critical", 0),
                "serious_issues": wcag_aggregate.get("impact_counts", {}).get("serious", 0)
            },
            "security_summary": {
                "primary_url": security_aggregate.get("primary_scan", {}).get("url"),
                "securityheaders_grade": security_aggregate.get("primary_scan", {}).get("securityheaders", {}).get("grade"),
                "ssl_grade": security_aggregate.get("primary_scan", {}).get("ssllabs", {}).get("endpoints", [{}])[0].get("grade") if security_aggregate.get("primary_scan", {}).get("ssllabs", {}).get("endpoints") else None
            }
        }
    
    async def scan_site(self, start_url: str, use_selenium_crawler: bool = False) -> Dict[str, Any]:
        """
        Main entry point: Crawl and scan entire website with mode-specific optimization.
        
        Modes:
        - "accessibility": Crawl once, scan accessibility only (no security)
        - "security": Crawl once, scan security domain-level only (no accessibility)
        - "all": Crawl once, scan both accessibility and security
        
        Returns:
            {
                "summary": {...},
                "crawl_result": {...},
                "page_results": [...],
                "wcag_aggregate": {...},
                "security_aggregate": {...},
                "duration_seconds": float
            }
        """
        start_time = time.time()
        
        logger.info(f"\n{'*'*70}")
        logger.info(f"{'*'*70}")
        logger.info(f"🌐 WHOLE-SITE SCAN INITIATED")
        logger.info(f"{'*'*70}")
        logger.info(f"{'*'*70}")
        logger.info(f"Target URL: {start_url}")
        logger.info(f"Max Pages: {self.max_pages}")
        logger.info(f"Max Depth: {self.max_depth}")
        logger.info(f"Scan Mode: {self.scan_mode.upper()}")
        logger.info(f"Parallel Scans: {self.parallel_scans}")
        logger.info(f"Use Selenium Crawler: {use_selenium_crawler}")
        logger.info(f"{'*'*70}\n")
        
        # Step 1: Crawl website to discover pages (with caching)
        logger.info(f"📡 PHASE 1: CRAWLING WEBSITE (WITH CACHE)")
        logger.info(f"{'─'*70}\n")
        
        # Try to get cached crawl result
        crawl_result = get_cached_crawl(start_url, self.max_pages, self.max_depth)
        
        # If not in memory cache, try database cache
        if not crawl_result and self.db is not None and self.organization_id:
            crawl_result = await get_crawl_from_db(self.db, start_url, self.organization_id)
            if crawl_result:
                # Store in memory cache for faster subsequent access
                set_cached_crawl(start_url, self.max_pages, self.max_depth, crawl_result)
        
        # If still no cache, perform actual crawl
        if not crawl_result:
            logger.info("No cached crawl found, performing fresh crawl...")
            crawl_result = await crawl_website(
                start_url,
                max_pages=self.max_pages,
                max_depth=self.max_depth,
                use_selenium=use_selenium_crawler
            )
            
            # Cache the crawl result
            set_cached_crawl(start_url, self.max_pages, self.max_depth, crawl_result)
            
            # Persist to database if available
            if self.db is not None and self.organization_id:
                await persist_crawl_to_db(self.db, crawl_result, start_url, self.organization_id)
        
        urls = crawl_result.get("urls", [])
        if not urls:
            logger.error(f"❌ No pages discovered during crawl")
            return {
                "error": "No pages discovered during crawl",
                "crawl_result": crawl_result,
                "duration_seconds": time.time() - start_time
            }
        
        crawl_stats = crawl_result.get("stats", {})
        logger.info(f"\n✅ CRAWLING COMPLETE")
        logger.info(f"   Pages discovered: {len(urls)}")
        logger.info(f"   From sitemap: {crawl_stats.get('from_sitemap', 0)}")
        logger.info(f"   From crawling: {crawl_stats.get('from_crawl', 0)}")
        logger.info(f"   Duration: {crawl_stats.get('duration_seconds', 0):.2f}s\n")
        
        # Step 2: Mode-specific scanning
        if self.scan_mode == "security":
            # Security-only mode: Test domain-level security only (no accessibility)
            logger.info(f"🔒 PHASE 2: SECURITY SCAN (DOMAIN-LEVEL ONLY)")
            logger.info(f"{'─'*70}\n")
            
            logger.info("Running comprehensive security scan (SecurityHeaders + SSL Labs + Live Headers)...")
            security_result = await asyncio.to_thread(run_security_scan, start_url)
            
            security_aggregate = {
                "primary_scan": security_result,
                "variations_detected": 0,
                "note": "Security headers and SSL configuration are domain-level, tested once"
            }
            
            # Generate summary for security-only
            summary = {
                "scan_timestamp": datetime.utcnow().isoformat(),
                "site_url": start_url,
                "scan_mode": "security_only",
                "crawl_stats": crawl_stats,
                "pages_discovered": len(urls),
                "pages_scanned": 0,  # No per-page scanning
                "security_summary": {
                    "primary_url": start_url,
                    "securityheaders_grade": security_result.get("securityheaders", {}).get("grade"),
                    "ssl_grade": security_result.get("ssllabs", {}).get("endpoints", [{}])[0].get("grade") if security_result.get("ssllabs", {}).get("endpoints") else None,
                    "missing_headers": security_result.get("securityheaders", {}).get("missing", []),
                    "note": "Security headers and SSL are domain-level"
                }
            }
            
            duration = time.time() - start_time
            
            result = {
                "summary": summary,
                "crawl_result": crawl_result,
                "page_results": [],  # No per-page results for security-only
                "wcag_aggregate": {},
                "security_aggregate": security_aggregate,
                "duration_seconds": round(duration, 2)
            }
            
            logger.info(f"\n✅ SECURITY SCAN COMPLETE")
            logger.info(f"   SecurityHeaders Grade: {summary['security_summary']['securityheaders_grade']}")
            logger.info(f"   SSL Labs Grade: {summary['security_summary']['ssl_grade']}")
            logger.info(f"   Missing Headers: {len(summary['security_summary']['missing_headers'])}\n")
            
        elif self.scan_mode == "accessibility":
            # Accessibility-only mode: Test each page for accessibility only (no security)
            logger.info(f"🔍 PHASE 2: ACCESSIBILITY SCAN (PER-PAGE)")
            logger.info(f"{'─'*70}\n")
            
            page_results = await self.scan_pages_accessibility_only(urls)
            
            logger.info(f"\n✅ ACCESSIBILITY SCANNING COMPLETE")
            logger.info(f"   Total pages scanned: {len(page_results)}")
            logger.info(f"   Successful scans: {len([p for p in page_results if not p.get('errors')])}")
            logger.info(f"   Failed scans: {len([p for p in page_results if p.get('errors')])}\n")
            
            # Aggregate accessibility results
            logger.info(f"📊 PHASE 3: AGGREGATING ACCESSIBILITY RESULTS")
            logger.info(f"{'─'*70}\n")
            
            wcag_aggregate = self.aggregate_wcag_results(page_results)
            logger.info(f"   ✓ WCAG aggregation complete")
            logger.info(f"     - Total violations: {wcag_aggregate.get('total_violations', 0)}")
            logger.info(f"     - Unique issues: {wcag_aggregate.get('unique_rules_violated', 0)}")
            logger.info(f"     - Pages with issues: {wcag_aggregate.get('pages_with_issues', 0)}\n")
            
            # Calculate accessibility score
            impact_counts = wcag_aggregate.get("impact_counts", {})
            critical = impact_counts.get("critical", 0)
            serious = impact_counts.get("serious", 0)
            moderate = impact_counts.get("moderate", 0)
            minor = impact_counts.get("minor", 0)
            
            critical_deduction = min(critical * 2.5, 40)
            serious_deduction = min(serious * 1.5, 30)
            moderate_deduction = min(moderate * 0.8, 25)
            minor_deduction = min(minor * 0.3, 10)
            
            total_deduction = critical_deduction + serious_deduction + moderate_deduction + minor_deduction
            score = max(0, min(100, 100 - total_deduction))
            
            summary = {
                "scan_timestamp": datetime.utcnow().isoformat(),
                "site_url": start_url,
                "scan_mode": "accessibility_only",
                "crawl_stats": crawl_stats,
                "pages_discovered": len(urls),
                "pages_scanned": wcag_aggregate.get("total_pages_scanned", 0),
                "pages_scanned_successfully": len([p for p in page_results if not p.get('errors')]),
                "accessibility_score": round(score, 1),
                "accessibility_summary": {
                    "total_violations": wcag_aggregate.get("total_violations", 0),
                    "unique_issues": wcag_aggregate.get("unique_rules_violated", 0),
                    "pages_with_issues": wcag_aggregate.get("pages_with_issues", 0),
                    "critical_issues": impact_counts.get("critical", 0),
                    "serious_issues": impact_counts.get("serious", 0)
                }
            }
            
            duration = time.time() - start_time
            
            result = {
                "summary": summary,
                "crawl_result": crawl_result,
                "page_results": page_results,
                "wcag_aggregate": wcag_aggregate,
                "security_aggregate": {},
                "duration_seconds": round(duration, 2)
            }
            
        else:  # "all" mode
            # Combined mode: Test accessibility per-page + security once per domain
            logger.info(f"🔬 PHASE 2: COMBINED SCAN (ACCESSIBILITY + SECURITY)")
            logger.info(f"{'─'*70}\n")
            
            # Do accessibility scanning for all pages
            logger.info("🔍 Running accessibility scans on all pages...")
            page_results = await self.scan_pages_accessibility_only(urls)
            
            logger.info(f"\n✅ ACCESSIBILITY SCANNING COMPLETE")
            logger.info(f"   Total pages scanned: {len(page_results)}")
            logger.info(f"   Successful scans: {len([p for p in page_results if not p.get('errors')])}")
            logger.info(f"   Failed scans: {len([p for p in page_results if p.get('errors')])}\n")
            
            # Do security scan once per domain
            logger.info("🔒 Running domain-level security scan...")
            security_result = await asyncio.to_thread(run_security_scan, start_url)
            
            security_aggregate = {
                "primary_scan": security_result,
                "variations_detected": 0,
                "note": "Security headers and SSL configuration are domain-level, tested once"
            }
            
            # Aggregate results
            logger.info(f"\n📊 PHASE 3: AGGREGATING RESULTS")
            logger.info(f"{'─'*70}\n")
            
            wcag_aggregate = self.aggregate_wcag_results(page_results)
            logger.info(f"   ✓ WCAG aggregation complete")
            logger.info(f"     - Total violations: {wcag_aggregate.get('total_violations', 0)}")
            logger.info(f"     - Unique issues: {wcag_aggregate.get('unique_rules_violated', 0)}")
            logger.info(f"     - Pages with issues: {wcag_aggregate.get('pages_with_issues', 0)}")
            logger.info(f"   ✓ Security aggregation complete\n")
            
            # Generate summary
            summary = self.generate_site_summary(
                crawl_result,
                page_results,
                wcag_aggregate,
                security_aggregate
            )
            summary["scan_mode"] = "combined"
            
            duration = time.time() - start_time
            
            result = {
                "summary": summary,
                "crawl_result": crawl_result,
                "page_results": page_results,
                "wcag_aggregate": wcag_aggregate,
                "security_aggregate": security_aggregate,
                "duration_seconds": round(duration, 2)
            }
        
        # Final summary logging
        logger.info(f"{'*'*70}")
        logger.info(f"{'*'*70}")
        logger.info(f"🎉 WHOLE-SITE SCAN COMPLETE")
        logger.info(f"{'*'*70}")
        logger.info(f"Mode: {self.scan_mode.upper()}")
        logger.info(f"Duration: {result['duration_seconds']:.2f}s ({result['duration_seconds']/60:.1f} minutes)")
        logger.info(f"Pages Discovered: {len(urls)}")
        if self.scan_mode in ["accessibility", "all"]:
            logger.info(f"Accessibility Score: {result['summary'].get('accessibility_score', 'N/A')}/100")
        if self.scan_mode in ["security", "all"]:
            logger.info(f"Security Grade: {result['security_aggregate'].get('primary_scan', {}).get('securityheaders', {}).get('grade', 'N/A')}")
        logger.info(f"{'*'*70}")
        logger.info(f"{'*'*70}\n")
        
        return result


async def scan_whole_site(
    url: str,
    max_pages: int = 50,
    max_depth: int = 3,
    scan_mode: str = "all",
    parallel_scans: int = 3,
    use_selenium_crawler: bool = False,
    db = None,
    organization_id: str = None
) -> Dict[str, Any]:
    """
    Convenience function to scan an entire website with crawl caching.
    
    Args:
        url: Starting URL
        max_pages: Maximum pages to scan
        max_depth: Maximum crawl depth
        scan_mode: "all", "accessibility", or "security"
        parallel_scans: Number of concurrent page scans
        use_selenium_crawler: Use Selenium for crawling (slower but handles JS)
        db: Database instance for crawl caching (optional)
        organization_id: Organization ID for scoped caching (optional)
    
    Returns:
        Comprehensive site scan results
    """
    orchestrator = SiteScanOrchestrator(
        max_pages=max_pages,
        max_depth=max_depth,
        scan_mode=scan_mode,
        parallel_scans=parallel_scans,
        db=db,
        organization_id=organization_id
    )
    return await orchestrator.scan_site(url, use_selenium_crawler)

