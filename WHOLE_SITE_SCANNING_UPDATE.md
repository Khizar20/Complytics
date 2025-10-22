# Whole-Site Scanning Update

## Problem Identified

The frontend UI testing component (`UiTesting.jsx`) was calling the **single-page scan endpoint** (`/api/ui/scan`) instead of the **whole-site scan endpoint** (`/api/ui/scan-site`), which meant:

- ❌ Only scanning the single URL provided
- ❌ Not crawling other pages on the website
- ❌ Not showing the comprehensive logging we added to `crawler.py` and `site_scanner.py`
- ❌ Not utilizing the sitemap.xml parsing or link discovery features

## Solution Implemented

### 1. **Frontend Changes** (`src/components/team/UiTesting.jsx`)

#### Changed API Endpoint
```javascript
// OLD: Single-page scan
const resp = await fetch(`${apiBase}/ui/scan`, {
  body: JSON.stringify({ url: normalized, mode, force: true })
});

// NEW: Whole-site scan
const resp = await fetch(`${apiBase}/ui/scan-site`, {
  body: JSON.stringify({ 
    url: normalized, 
    scan_mode: mode,
    max_pages: 50,        // Scan up to 50 pages
    max_depth: 3,         // Follow links up to 3 levels deep
    parallel_scans: 3,    // Scan 3 pages concurrently for speed
    use_selenium_crawler: false  // Use fast requests-based crawling
  })
});
```

#### Updated Response Handling
The whole-site scan returns a different response structure:

**Old (Single Page):**
```json
{
  "wcag_results": {...},
  "security_results": {...},
  "a11y_score": 85,
  "recommendations": "..."
}
```

**New (Whole Site):**
```json
{
  "summary": {
    "total_pages": 45,
    "accessibility_score": 72.5,
    "critical_issues": 3,
    "serious_issues": 12,
    "scan_duration": "2.1 minutes"
  },
  "crawl_result": {
    "urls_discovered": 45,
    "from_sitemap": 38,
    "from_crawling": 7,
    "crawl_duration": "12.4s"
  },
  "page_results": [...],      // Individual page results
  "wcag_aggregate": {...},    // Combined WCAG findings
  "security_aggregate": {...} // Combined security findings
}
```

#### Added Scan Type Detection
```javascript
// Check if this is a whole-site scan result or single-page scan result
const isSiteScan = result && result.summary && result.page_results;

// Extract data based on scan type
const violations = isSiteScan 
  ? (result?.wcag_aggregate?.all_violations || [])
  : (result?.wcag_results?.violations || []);

const a11yScore = isSiteScan
  ? (result?.summary?.accessibility_score || 0)
  : (result ? (violations.length > 0 ? computeAccessibilityScore() : 100) : 0);
```

#### Added Site Scan Summary Banner
When a whole-site scan completes, a blue banner displays:
```
Whole-Site Scan Complete
Scanned 45 pages across the website in 2.1 minutes
38 from sitemap • 7 from crawling
```

#### Updated UI Description
Changed from:
```
"WCAG + Security headers + SSL Labs + AI recommendations"
```

To:
```
"Whole-site WCAG accessibility + Security + SSL testing with AI recommendations"
```

### 2. **Backend Changes** (`Complytics Backend/routes/ui_testing.py`)

#### Fixed Endpoint Paths
The whole-site scanning endpoints were missing the `/ui/` prefix:

```python
# Before: /api/scan-site
@router.post("/scan-site")

# After: /api/ui/scan-site
@router.post("/ui/scan-site")
```

Updated all whole-site endpoints:
- ✅ `/api/ui/scan-site` - Main whole-site scanning
- ✅ `/api/ui/crawl-only` - Preview crawling without scanning
- ✅ `/api/ui/site/latest` - Get latest whole-site scan
- ✅ `/api/ui/site/history` - Get scan history

#### Added Logger
```python
import logging
logger = logging.getLogger("routes.ui_testing")
```

This ensures that logs from the route handler are properly captured alongside the detailed logging from `crawler.py` and `site_scanner.py`.

---

## How It Works Now

### User Flow

1. **User enters a URL** (e.g., `https://contour-software.com`)
2. **Selects scan mode**:
   - `all` - Full accessibility + security scan
   - `accessibility` - Only WCAG testing
   - `security` - Only security headers/SSL
3. **Clicks "Run Scan"**

### Backend Process

#### Phase 1: Crawling (with detailed logging)
```
============================================================
Starting BFS crawl (max_pages=50, max_depth=3)
============================================================

Fetching robots.txt from https://contour-software.com/robots.txt
✓ Loaded robots.txt: found 5 disallowed paths

Fetching sitemap from https://contour-software.com/sitemap.xml
  Found sitemap index with 3 sitemaps
  Fetching sub-sitemap 1/3: https://contour-software.com/sitemap-posts.xml
    ✓ Found 150 URLs in sub-sitemap
✓ Found 175 total URLs in sitemap(s)

🔍 Crawling [1/50] (2.0%)
   URL: https://contour-software.com
   Depth: 0/3
   Queue size: 0
   ✓ Discovered 12 new URLs (total: 13)

🔍 Crawling [2/50] (4.0%)
   URL: https://contour-software.com/about
   Depth: 1/3
   Queue size: 11
   ✓ Discovered 3 new URLs (total: 16)
```

#### Phase 2: Scanning (with detailed logging)
```
**********************************************************************
🌐 WHOLE-SITE SCAN INITIATED
**********************************************************************
Target URL: https://contour-software.com
Max Pages: 50
Max Depth: 3
Scan Mode: all
**********************************************************************

📡 PHASE 1/4: CRAWLING WEBSITE
✅ CRAWLING COMPLETE
   Pages discovered: 45
   From sitemap: 38
   From crawling: 7
   Duration: 12.4s

🔬 PHASE 2/4: SCANNING PAGES

######################################################################
🚀 STARTING BATCH SCANNING
######################################################################
Total pages: 45
Parallel scans: 3
Batches: 15
Scan mode: all
######################################################################

┌────────────────────────────────────────────────────────────────────┐
│ BATCH 1/15 - Scanning 3 page(s) in parallel...                    │
└────────────────────────────────────────────────────────────────────┘

======================================================================
📊 SCANNING PAGE [1/45] (2.2%)
======================================================================
URL: https://contour-software.com
Mode: all
  🔍 Running WCAG accessibility scan...
  ✓ WCAG scan complete: 12 violations found
  🔒 Running security scan...
  ✓ Security scan complete: Grade A
  ⌨️  Running interaction test...
  ✓ Interaction test complete
✅ Page scan completed successfully

[... more pages ...]

📊 PHASE 3/4: AGGREGATING RESULTS
   ✓ WCAG aggregation complete
     - Total violations: 127
     - Unique issues: 8
     - Pages with issues: 32
   ✓ Security aggregation complete

📋 PHASE 4/4: GENERATING SUMMARY
   ✓ Summary generated
     - Accessibility Score: 72.5/100
     - Critical Issues: 3
     - Serious Issues: 12

**********************************************************************
🎉 WHOLE-SITE SCAN COMPLETE
**********************************************************************
Duration: 124.5s (2.1 minutes)
Pages Scanned: 45/45
Accessibility Score: 72.5/100
**********************************************************************
```

#### Phase 3: Frontend Display
The UI shows:
- 📊 **Site-wide summary banner** - Number of pages, duration, discovery stats
- 📈 **Aggregated scores** - Accessibility score across all pages
- 📋 **Combined violations** - All WCAG issues found site-wide
- 🔒 **Security findings** - Aggregated security headers and SSL info
- 🤖 **AI recommendations** - Comprehensive guidance for the entire site

---

## What You'll See Now

### Terminal/Console Logs
When you run a scan, you'll see **comprehensive logging** like:

```
INFO:scanner.crawler:Fetching robots.txt from https://contour-software.com/robots.txt
INFO:scanner.crawler:✓ Loaded robots.txt: found 5 disallowed paths
INFO:scanner.crawler:Fetching sitemap from https://contour-software.com/sitemap.xml
INFO:scanner.crawler:  Found sitemap index with 3 sitemaps
INFO:scanner.crawler:🔍 Crawling [1/50] (2.0%)
INFO:scanner.crawler:   URL: https://contour-software.com
INFO:scanner.crawler:   ✓ Discovered 12 new URLs (total: 13)
INFO:scanner.site:📊 SCANNING PAGE [1/45] (2.2%)
INFO:scanner.site:URL: https://contour-software.com
INFO:scanner.site:  🔍 Running WCAG accessibility scan...
INFO:scanner.wcag:Launching headless Chrome for WCAG scan
INFO:scanner.wcag:✓ WCAG scan complete: 12 violations found
INFO:scanner.site:  🔒 Running security scan...
INFO:scanner.site:  ✓ Security scan complete: Grade A
INFO:scanner.site:✅ Page scan completed successfully
```

### UI Display
- Blue banner: "Whole-Site Scan Complete - Scanned 45 pages"
- Discovery stats: "38 from sitemap • 7 from crawling"
- Site-wide accessibility score
- All violations across all pages
- Aggregated security findings

---

## Configuration Options

You can customize the scan behavior by modifying the request parameters in `UiTesting.jsx`:

```javascript
body: JSON.stringify({ 
  url: normalized, 
  scan_mode: mode,           // "all", "accessibility", or "security"
  max_pages: 50,             // Maximum pages to scan (increase for larger sites)
  max_depth: 3,              // Maximum link depth (increase to discover more pages)
  parallel_scans: 3,         // Concurrent scans (increase for faster scanning)
  use_selenium_crawler: false // Use Selenium for JS-heavy sites (slower but more thorough)
})
```

### Recommended Settings

**Small sites (< 20 pages):**
```javascript
max_pages: 20,
max_depth: 3,
parallel_scans: 5
```

**Medium sites (20-100 pages):**
```javascript
max_pages: 50,
max_depth: 3,
parallel_scans: 3
```

**Large sites (100+ pages):**
```javascript
max_pages: 100,
max_depth: 2,
parallel_scans: 5
```

**JavaScript-heavy sites:**
```javascript
use_selenium_crawler: true  // Slower but handles dynamic content
```

---

## Benefits

### ✅ What You Get Now

1. **Comprehensive Coverage**
   - Automatically discovers all pages via sitemap.xml
   - Follows links to find additional pages
   - Scans up to 50 pages by default

2. **Intelligent Crawling**
   - Respects robots.txt
   - Avoids duplicate URLs
   - Filters out non-HTML resources (images, PDFs, etc.)
   - Stays within the same domain

3. **Parallel Processing**
   - Scans multiple pages concurrently for speed
   - Configurable parallelism based on your needs

4. **Detailed Logging**
   - See exactly what pages are being discovered
   - Track scanning progress in real-time
   - View detailed WCAG/security scan results per page

5. **Aggregated Results**
   - Site-wide accessibility score
   - All violations across all pages
   - Combined security findings
   - Executive summary with key metrics

6. **Flexible Scan Modes**
   - `all` - Full accessibility + security
   - `accessibility` - WCAG only (faster)
   - `security` - Security headers/SSL only

---

## Testing

To verify the whole-site scanning is working:

1. **Start the backend** (if not already running)
   ```bash
   cd "Complytics Backend"
   python app.py
   ```

2. **Open the frontend** and navigate to UI Testing

3. **Enter a URL** (e.g., `https://contour-software.com`)

4. **Select a scan mode** (e.g., "All")

5. **Click "Run Scan"**

6. **Watch the backend terminal** - You should see:
   - Robots.txt fetching
   - Sitemap.xml parsing
   - BFS crawling with progress percentages
   - Page scanning with [X/Y] counters
   - WCAG/security scan logs for each page
   - Aggregation logs
   - Final summary

7. **Check the frontend** - You should see:
   - Blue "Whole-Site Scan Complete" banner
   - Number of pages scanned
   - Discovery stats (sitemap vs crawling)
   - Site-wide accessibility score
   - Aggregated violations and security findings

---

## Troubleshooting

### Issue: Not seeing crawl logs

**Check:**
- Backend terminal should show logs starting with `INFO:scanner.crawler:`
- If missing, verify the backend restarted after the changes

### Issue: Only seeing 1 page scanned

**Check:**
- Frontend should be calling `/api/ui/scan-site`, not `/api/ui/scan`
- Check browser Network tab to verify the correct endpoint

### Issue: Scan is very slow

**Solutions:**
- Increase `parallel_scans` (e.g., 5 or 7)
- Decrease `max_pages` to scan fewer pages
- Use `accessibility` or `security` mode instead of `all`

### Issue: Not discovering enough pages

**Solutions:**
- Increase `max_depth` (e.g., 4 or 5)
- Increase `max_pages` (e.g., 100)
- Set `use_selenium_crawler: true` for JS-heavy sites

---

## Summary

The UI testing now performs **whole-website scanning** by:

1. ✅ Calling the correct whole-site endpoint (`/api/ui/scan-site`)
2. ✅ Crawling the entire website (sitemap.xml + link following)
3. ✅ Scanning all discovered pages in parallel
4. ✅ Showing detailed logs in the terminal
5. ✅ Displaying aggregated results in the UI
6. ✅ Supporting all scan modes (all, accessibility, security)

**Your logs will now show every page being crawled and scanned!** 🎉

