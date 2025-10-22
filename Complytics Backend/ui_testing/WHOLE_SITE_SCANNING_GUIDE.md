# Whole-Site Scanning User Guide

## Overview

The Whole-Site Scanning feature provides comprehensive accessibility and security analysis for entire websites, not just individual pages. It automatically discovers pages, tests them in parallel, and aggregates results into actionable insights.

## Quick Start

### Basic Whole-Site Scan

```bash
curl -X POST "http://localhost:8000/api/ui/scan-site" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "max_pages": 50,
    "max_depth": 3,
    "scan_mode": "all"
  }'
```

### Preview Pages (Crawl Only)

```bash
curl -X POST "http://localhost:8000/api/ui/crawl-only" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "max_pages": 50,
    "max_depth": 3
  }'
```

## API Reference

### POST /api/ui/scan-site

Scan an entire website by crawling and testing multiple pages.

**Request Body:**
```json
{
  "url": "https://example.com",
  "max_pages": 50,
  "max_depth": 3,
  "scan_mode": "all",
  "parallel_scans": 3,
  "use_selenium_crawler": false
}
```

**Parameters:**

- `url` (string, required): Starting URL to crawl from
- `max_pages` (int, default: 50): Maximum number of pages to scan
- `max_depth` (int, default: 3): Maximum link depth to follow from starting URL
- `scan_mode` (string, default: "all"): Scan mode - "all", "accessibility", or "security"
- `parallel_scans` (int, default: 3): Number of pages to scan concurrently
- `use_selenium_crawler` (bool, default: false): Use Selenium for JavaScript-heavy sites (slower but more thorough)

**Response:**
```json
{
  "summary": {
    "scan_timestamp": "2025-10-11T12:00:00",
    "site_url": "https://example.com",
    "pages_discovered": 45,
    "pages_scanned": 45,
    "pages_scanned_successfully": 43,
    "pages_with_errors": 2,
    "accessibility_score": 72.5,
    "accessibility_summary": {
      "total_violations": 127,
      "unique_issues": 8,
      "pages_with_issues": 32,
      "critical_issues": 3,
      "serious_issues": 12
    },
    "security_summary": {
      "primary_url": "https://example.com",
      "securityheaders_grade": "A",
      "ssl_grade": "A+"
    }
  },
  "crawl_result": {
    "urls": ["https://example.com", "https://example.com/about", ...],
    "stats": {
      "total_discovered": 45,
      "total_visited": 45,
      "from_sitemap": 38,
      "from_crawl": 7,
      "duration_seconds": 12.4
    },
    "errors": []
  },
  "page_results": [
    {
      "url": "https://example.com",
      "scan_time": "2025-10-11T12:01:23",
      "wcag_results": {
        "violations": [...]
      },
      "security_results": {...},
      "errors": []
    }
  ],
  "wcag_aggregate": {
    "total_pages_scanned": 45,
    "pages_with_issues": 32,
    "total_violations": 127,
    "unique_rules_violated": 8,
    "impact_counts": {
      "critical": 15,
      "serious": 45,
      "moderate": 50,
      "minor": 17
    },
    "violations_summary": [
      {
        "id": "image-alt",
        "description": "Images must have alternate text",
        "impact": "critical",
        "help": "...",
        "helpUrl": "https://dequeuniversity.com/rules/axe/4.7/image-alt",
        "pages_affected": 25,
        "pages_affected_urls": ["https://example.com/page1", ...],
        "total_instances": 38
      }
    ],
    "top_issues": [...]
  },
  "security_aggregate": {
    "primary_scan": {...},
    "variations_detected": 0
  },
  "duration_seconds": 124.5
}
```

### POST /api/ui/crawl-only

Crawl a website to discover pages without running scans (preview mode).

**Request Body:**
```json
{
  "url": "https://example.com",
  "max_pages": 50,
  "max_depth": 3,
  "use_selenium": false
}
```

**Response:**
```json
{
  "urls": [
    "https://example.com",
    "https://example.com/about",
    "https://example.com/contact",
    ...
  ],
  "stats": {
    "total_discovered": 45,
    "total_visited": 45,
    "from_sitemap": 38,
    "from_crawl": 7,
    "duration_seconds": 12.4
  },
  "errors": []
}
```

### GET /api/ui/site/latest

Get the most recent whole-site scan result for your organization.

**Response:** Same as POST /api/ui/scan-site response, plus `_id`, `organization_id`, `user_id`, `mode`, and `created_at` fields.

### GET /api/ui/site/history?limit=10

Get history of whole-site scans for your organization.

**Response:**
```json
{
  "results": [
    {
      "_id": "507f1f77bcf86cd799439011",
      "url": "https://example.com",
      "mode": "all",
      "created_at": 1728651234,
      "summary": {
        "accessibility_score": 72.5,
        "pages_scanned": 45,
        ...
      }
    }
  ],
  "count": 10
}
```

## How It Works

### 1. Page Discovery Phase

The crawler discovers pages using multiple strategies:

1. **Sitemap.xml Parsing**: Fetches and parses `/sitemap.xml` (including sitemap indexes)
2. **HTML Link Extraction**: Crawls pages and extracts `<a>` tags
3. **robots.txt Respect**: Honors disallowed paths from `/robots.txt`
4. **Smart Filtering**: Automatically excludes:
   - Non-HTML resources (images, PDFs, CSS, JS)
   - API endpoints (e.g., `/api/`)
   - Download links (e.g., `/download/`)
   - Logout/print URLs
   - Duplicate URLs (normalized)

### 2. Scanning Phase

Once pages are discovered:

1. Pages are scanned in parallel batches (default: 3 at a time)
2. Each page undergoes:
   - **WCAG Scan**: axe-core accessibility audit
   - **Security Scan**: Headers, SSL/TLS analysis
   - **Interaction Test**: Keyboard navigation, form detection
3. Individual results are collected

### 3. Aggregation Phase

Results are aggregated to provide site-wide insights:

- **WCAG Aggregation**:
  - Groups violations by rule ID
  - Tracks which pages are affected
  - Counts violation instances
  - Calculates impact distribution
  - Identifies top issues affecting most pages

- **Security Aggregation**:
  - Takes primary security scan (headers are usually domain-level)
  - Notes any variations across pages
  - Provides SSL Labs grade

- **Scoring**:
  - Accessibility score (0-100) based on violations
  - Deducts points for critical/serious/moderate/minor issues

## Usage Patterns

### Pattern 1: Pre-Launch Audit

Scan your entire website before launch to catch accessibility and security issues:

```bash
# Comprehensive scan with maximum coverage
curl -X POST "http://localhost:8000/api/ui/scan-site" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://staging.yoursite.com",
    "max_pages": 100,
    "max_depth": 4,
    "scan_mode": "all",
    "parallel_scans": 5
  }'
```

### Pattern 2: Accessibility-Only Quick Scan

Focus on accessibility for faster scans:

```bash
curl -X POST "http://localhost:8000/api/ui/scan-site" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://yoursite.com",
    "max_pages": 30,
    "scan_mode": "accessibility",
    "parallel_scans": 5
  }'
```

### Pattern 3: JavaScript-Heavy Site

For single-page applications or JS-heavy sites:

```bash
curl -X POST "http://localhost:8000/api/ui/scan-site" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://yoursite.com",
    "max_pages": 20,
    "max_depth": 2,
    "use_selenium_crawler": true,
    "parallel_scans": 2
  }'
```

**Note**: Selenium crawler is slower but can discover pages rendered by JavaScript.

### Pattern 4: Preview Before Scanning

Check which pages will be scanned without running the full scan:

```bash
# Step 1: Preview pages
curl -X POST "http://localhost:8000/api/ui/crawl-only" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://yoursite.com",
    "max_pages": 50
  }'

# Step 2: Review the URLs, then run full scan
curl -X POST "http://localhost:8000/api/ui/scan-site" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://yoursite.com",
    "max_pages": 50
  }'
```

## Interpreting Results

### Accessibility Score

- **90-100**: Excellent - Few or no issues detected
- **70-89**: Good - Some issues, but manageable
- **50-69**: Fair - Multiple issues requiring attention
- **Below 50**: Poor - Significant accessibility problems

### Violation Severity

- **Critical**: Must fix - Severe barriers for users with disabilities
- **Serious**: High priority - Significant usability problems
- **Moderate**: Medium priority - Impacts some users
- **Minor**: Low priority - Best practice improvements

### Top Issues

The `top_issues` array shows the 10 most widespread problems, sorted by:
1. Severity (critical > serious > moderate > minor)
2. Number of pages affected

**Example:**
```json
{
  "id": "image-alt",
  "description": "Images must have alternate text",
  "impact": "critical",
  "pages_affected": 25,
  "total_instances": 38
}
```

This means 25 out of your pages have images without alt text, with 38 total instances.

## Performance Tips

### Optimize Scan Speed

1. **Reduce max_pages**: Start with 20-30 pages for quick scans
2. **Increase parallel_scans**: Use 5-10 for faster completion (monitor resource usage)
3. **Skip security scans**: Use `scan_mode: "accessibility"` for faster results
4. **Lower max_depth**: Use depth 2 for shallow sites

### Optimize Accuracy

1. **Use Selenium crawler**: For JavaScript-heavy sites
2. **Increase max_pages**: Scan more pages for comprehensive coverage
3. **Use max_depth 3-4**: Discover all pages in complex site structures

### Resource Considerations

- Each page scan launches a headless Chrome instance
- Parallel scans consume more memory and CPU
- SSL Labs analysis may take minutes on first run
- Recommended max_pages: 50-100 for most sites

## Troubleshooting

### Issue: No pages discovered

**Possible causes:**
- Site blocks crawlers (check robots.txt)
- No sitemap.xml exists
- Starting URL is incorrect
- JavaScript-rendered navigation

**Solutions:**
- Verify the URL is correct
- Use `use_selenium_crawler: true`
- Check robots.txt allows crawling
- Try `/crawl-only` endpoint to debug

### Issue: Scan takes too long

**Solutions:**
- Reduce `max_pages` to 20-30
- Increase `parallel_scans` to 5-10
- Use `scan_mode: "accessibility"` only
- Lower `max_depth` to 2

### Issue: Some pages fail to scan

**Possible causes:**
- Pages require authentication
- Pages have JavaScript errors
- Pages time out loading
- Network issues

**Solutions:**
- Check `page_results[].errors` for details
- Pages with errors are skipped gracefully
- Aggregated results still provided for successful scans

## Best Practices

1. **Start Small**: Begin with 20 pages to test configuration
2. **Preview First**: Use `/crawl-only` to verify page discovery
3. **Schedule Regular Scans**: Run weekly/monthly for regression testing
4. **Focus on Critical Issues**: Prioritize critical and serious violations
5. **Track Progress**: Use `/site/history` to monitor improvements over time
6. **Combine with Manual Testing**: Automated scans don't catch everything
7. **Review Top Issues**: Fix issues affecting multiple pages first
8. **Respect Rate Limits**: Don't scan more than once per hour per site

## Integration Examples

### Python

```python
import requests

response = requests.post(
    'http://localhost:8000/api/ui/scan-site',
    headers={'Authorization': 'Bearer YOUR_TOKEN'},
    json={
        'url': 'https://example.com',
        'max_pages': 50,
        'scan_mode': 'all'
    }
)

result = response.json()
print(f"Accessibility Score: {result['summary']['accessibility_score']}")
print(f"Pages Scanned: {result['summary']['pages_scanned']}")
print(f"Critical Issues: {result['summary']['accessibility_summary']['critical_issues']}")
```

### JavaScript/Node.js

```javascript
const response = await fetch('http://localhost:8000/api/ui/scan-site', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer YOUR_TOKEN',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    url: 'https://example.com',
    max_pages: 50,
    scan_mode: 'all'
  })
});

const result = await response.json();
console.log(`Accessibility Score: ${result.summary.accessibility_score}`);
console.log(`Pages Scanned: ${result.summary.pages_scanned}`);
```

## FAQ

**Q: Can I scan sites behind authentication?**  
A: Not currently. The scanner cannot provide credentials for authenticated pages.

**Q: How often should I run whole-site scans?**  
A: Weekly for active development, monthly for stable sites.

**Q: What's the difference between single-page and whole-site scanning?**  
A: Single-page scans one URL deeply. Whole-site discovers and scans multiple pages, providing aggregated insights.

**Q: Can I export results?**  
A: Yes, use the existing `/api/ui/export/pdf` or `/api/ui/export/excel` endpoints with the scan results.

**Q: Do scans affect my live site?**  
A: Scans only read pages (like a normal visitor). They don't submit forms or modify data.

**Q: How much does a scan cost (API calls)?**  
A: External APIs (SSL Labs, SecurityHeaders) may have rate limits. Gemini API calls are made for recommendations (same as single-page scans).

**Q: Can I scan competitor sites?**  
A: Technically yes, but respect robots.txt and rate limits. Use for competitive analysis ethically.

## Support

For issues, feature requests, or questions:
- Check the logs for detailed error messages
- Review the `/crawl-only` results to debug discovery issues
- Reduce `max_pages` if encountering timeouts
- Contact support with scan ID and error details

