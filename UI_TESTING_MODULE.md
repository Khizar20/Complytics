# UI Testing Module - Roman Urdu Documentation

## Module Ka Naam
**UI Testing Module** - Ye module websites ko accessibility (WCAG) aur security ke liye test karta hai. Ye whole-site scanning bhi support karta hai.

## Module Ka Kaam Kya Hai?

Ye module:
- Websites ko WCAG accessibility guidelines ke against test karta hai
- Security vulnerabilities check karta hai (SSL, headers, etc.)
- Whole-site scanning karta hai (multiple pages)
- Interactive testing karta hai (forms, buttons, etc.)
- AI-powered recommendations provide karta hai
- Detailed reports generate karta hai

## Flow Kaise Kaam Karta Hai?

### 1. URL Input
- User website ka URL enter karta hai
- System URL ko normalize karta hai
- Scan mode select karta hai:
  - **All** - Accessibility + Security
  - **Accessibility** - Sirf WCAG testing
  - **Security** - Sirf security testing

### 2. Authentication (Optional)
- Agar website authentication require karti hai:
  - Username/password provide kiye ja sakte hain
  - Session cookies manage kiye jate hain
  - Authenticated scans run hote hain

### 3. Single Page Scan
- **WCAG Scan**:
  - Page load hota hai headless browser mein
  - DOM analyze hota hai
  - WCAG violations detect hote hain
  - Accessibility issues identify hote hain
  
- **Security Scan**:
  - SSL certificate check hota hai
  - Security headers check hote hain
  - Vulnerabilities detect hote hain
  
- **Interactive Test**:
  - Forms test hote hain
  - Buttons test hote hain
  - Navigation test hoti hai

### 4. Whole-Site Scan (Optional)
- Website crawl hoti hai
- Multiple pages discover hote hain
- Har page par scan run hota hai
- Results aggregate hote hain
- Site-wide report generate hota hai

### 5. AI Recommendations
- Scan results ko AI (Gemini) analyze karta hai
- Findings identify hote hain
- Recommendations generate hote hain
- Priority-based suggestions milte hain

### 6. Results Display
- Results frontend par display hote hain
- Violations list show hoti hai
- Security scores display hote hain
- Recommendations show hote hain
- Export options available hain (PDF, Excel)

## Technical Working

### WCAG Scanner
1. **Headless Browser**: Puppeteer/Playwright use karke page load hota hai
2. **DOM Analysis**: Page ka DOM analyze hota hai
3. **Rule Checking**: WCAG rules check hote hain
4. **Violation Detection**: Violations identify hote hain
5. **Impact Assessment**: Har violation ka impact assess hota hai

### Security Scanner
1. **SSL Check**: SSL certificate validate hota hai
2. **Header Analysis**: Security headers check hote hain
3. **Vulnerability Scan**: Common vulnerabilities detect hote hain
4. **Score Calculation**: Security score calculate hota hai

### Site Scanner
1. **Crawling**: Website crawl hoti hai
2. **Page Discovery**: Links follow kiye jate hain
3. **Parallel Scanning**: Multiple pages parallel scan hote hain
4. **Aggregation**: Results aggregate hote hain
5. **Reporting**: Comprehensive report generate hota hai

### AI Recommendations
1. **Result Analysis**: Scan results ko AI analyze karta hai
2. **Pattern Detection**: Common patterns identify hote hain
3. **Recommendation Generation**: Actionable recommendations generate hote hain
4. **Priority Assignment**: Recommendations ko priority milti hai

## Files Jahan Code Present Hai

### Backend Files (Python)

1. **`Complytics Backend/routes/ui_testing.py`**
   - Main API routes file
   - `/api/ui/scan` endpoint - Single page scan
   - `/api/ui/scan-site` endpoint - Whole-site scan
   - `/api/ui/scan-now` endpoint - Quick scan
   - Schedule scan endpoints
   - Result caching logic

2. **`Complytics Backend/ui_testing/scanners/wcag.py`**
   - WCAG scanning functions
   - `run_wcag_scan()` - Main WCAG scan function
   - `get_dom_snapshot()` - DOM snapshot function
   - Violation detection logic

3. **`Complytics Backend/ui_testing/scanners/security.py`**
   - Security scanning functions
   - `run_security_scan()` - Main security scan function
   - SSL certificate checking
   - Security headers checking
   - Vulnerability detection

4. **`Complytics Backend/ui_testing/scanners/interaction.py`**
   - Interactive testing functions
   - `run_interactive_test()` - Interactive test function
   - Form testing
   - Button testing
   - Navigation testing

5. **`Complytics Backend/ui_testing/scanners/crawler.py`**
   - Website crawling functions
   - `crawl_website()` - Main crawl function
   - Link discovery
   - Page discovery

6. **`Complytics Backend/ui_testing/scanners/site_scanner.py`**
   - Whole-site scanning orchestrator
   - `SiteScanOrchestrator` class
   - `scan_whole_site()` - Main site scan function
   - Result aggregation logic

7. **`Complytics Backend/ui_testing/scanners/authenticated_site_scanner.py`**
   - Authenticated site scanning
   - `scan_authenticated_site()` - Authenticated scan function
   - Session management

8. **`Complytics Backend/ui_testing/scanners/auth_handler.py`**
   - Authentication handling
   - Login functions
   - Cookie management

9. **`Complytics Backend/ui_testing/ai/recommendations.py`**
   - AI recommendation functions
   - `generate_findings_and_recommendations()` - Main recommendation function
   - Gemini AI integration

10. **`Complytics Backend/ui_testing/ai/agents.py`**
    - AI agent functions
    - Analysis agents

11. **`Complytics Backend/ui_testing/crawl_cache.py`**
    - Crawl caching functions
    - Cache management
    - Database persistence

### Frontend Files (React/JSX)

1. **`src/components/team/UiTesting.jsx`**
   - Main UI component
   - URL input interface
   - Scan mode selection
   - Authentication form
   - Results display
   - Progress indicators
   - Export functionality

2. **`src/components/ui/FormattedResponse.jsx`**
   - Response formatting
   - Violation display
   - Security score display

3. **`src/lib/api.js`**
   - API utility functions

### Database Collections

1. **`ui_testing_results`** - Single page scan results
2. **`ui_testing_site_results`** - Whole-site scan results
3. **`crawl_cache`** - Crawl cache storage

## Key Functions

### Main Functions in `ui_testing.py`:
- `scan()` - Single page scan
- `scan_site()` - Whole-site scan
- `scan_now()` - Quick scan
- `schedule_scan()` - Schedule scan
- `_execute_scheduled_scan()` - Execute scheduled scan

### Main Functions in `wcag.py`:
- `run_wcag_scan()` - WCAG scan execution
- `get_dom_snapshot()` - DOM snapshot

### Main Functions in `security.py`:
- `run_security_scan()` - Security scan execution

### Main Functions in `site_scanner.py`:
- `scan_whole_site()` - Whole-site scan
- `SiteScanOrchestrator` class - Scan orchestration

### Main Functions in `recommendations.py`:
- `generate_findings_and_recommendations()` - AI recommendations

## API Endpoints

- `POST /api/ui/scan` - Single page scan
- `POST /api/ui/scan-site` - Whole-site scan
- `POST /api/ui/scan-now` - Quick scan
- `POST /api/ui/schedule` - Schedule scan
- `GET /api/ui/schedules` - List schedules
- `DELETE /api/ui/schedule/{id}` - Cancel schedule

## Scan Modes

1. **All** - Accessibility + Security scanning
2. **Accessibility** - Sirf WCAG testing
3. **Security** - Sirf security testing

## WCAG Violations

Common violations jo detect hote hain:
- Missing alt text
- Color contrast issues
- Keyboard navigation problems
- Form label issues
- ARIA attributes missing
- Heading structure issues

## Security Checks

Security checks jo perform hote hain:
- SSL certificate validation
- Security headers (HSTS, CSP, etc.)
- Cookie security
- XSS vulnerabilities
- CSRF protection
- Clickjacking protection

## Dependencies

- **FastAPI** - Web framework
- **Playwright/Puppeteer** - Headless browser
- **Google Gemini AI** - AI recommendations
- **MongoDB** - Database
- **APScheduler** - Task scheduling

## Summary

Ye module websites ko comprehensive testing provide karta hai:
- WCAG accessibility testing
- Security vulnerability scanning
- Whole-site scanning
- AI-powered recommendations
- Detailed reporting
- Scheduled scanning support

Sab kuch headless browser automation aur AI analysis ke combination se kaam karta hai.

