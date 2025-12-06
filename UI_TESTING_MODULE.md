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
  - **Login page accessibility testing**: Jab authentication checkbox enable hota hai aur login page detect hota hai:
    - **Whole-site scan mode**: 
      - Pehle login page ki accessibility test hoti hai (BEFORE login)
      - Phir credentials se login hota hai
      - Login ke baad authenticated pages discover kiye jate hain (crawling se)
      - Authenticated pages ki accessibility testing hoti hai
    - **Specific URLs scan mode**:
      - Specific URLs list se login pages detect kiye jate hain
      - Pehle login page ki accessibility test hoti hai (BEFORE login)
      - Phir credentials se login hota hai
      - Login ke baad authenticated pages discover kiye jate hain (crawling se)
      - Authenticated pages ki accessibility testing hoti hai
  - Session cookies manage kiye jate hain
  - Login page aur authenticated pages dono ke results final report mein include hote hain

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

### Website Crawler (Detailed Working)

Website crawler ek intelligent system hai jo websites ko systematically crawl karke pages discover karta hai. Ye UI testing ke liye pages find karne mein help karta hai.

#### Crawler Architecture

**Main Components:**
- **WebsiteCrawler Class**: Main crawler class jo crawling orchestrate karti hai
- **URL Normalization**: URLs ko clean aur normalize karta hai
- **URL Filtering**: Relevant pages ko identify karta hai, non-HTML resources ko filter karta hai
- **BFS (Breadth-First Search) Algorithm**: Pages ko depth-wise crawl karta hai

#### Crawling Process Flow

1. **Initialization**:
   - Start URL normalize hota hai
   - Base domain extract hota hai
   - Max pages aur max depth limits set hote hain

2. **Robots.txt Check** (Optional):
   - `robots.txt` file fetch hoti hai
   - Disallowed paths parse kiye jate hain
   - Crawler in paths ko respect karta hai
   - User-Agent: `ComplyticsUITester/1.0` use hota hai

3. **Sitemap.xml Parsing**:
   - `sitemap.xml` file fetch hoti hai
   - Single sitemap ya sitemap index handle hota hai
   - Multiple sitemaps support (max 10 sub-sitemaps)
   - Sitemap se URLs extract kiye jate hain
   - Ye URLs directly discovered URLs list mein add ho jate hain

4. **BFS Crawling**:
   - Queue-based breadth-first search algorithm use hota hai
   - Start URL queue mein add hota hai (depth 0)
   - Har page se links extract kiye jate hain
   - New links queue mein add hote hain (depth + 1)
   - Max depth limit check hota hai
   - Max pages limit check hota hai

5. **Link Extraction**:
   - **Requests Method** (Default):
     - `requests` library se HTML fetch hota hai
     - BeautifulSoup se HTML parse hota hai
     - `<a>` tags se links extract hote hain
     - `<link>` tags (alternate pages) se bhi links extract hote hain
   - **Selenium Method** (Optional):
     - JavaScript-rendered pages ke liye use hota hai
     - Headless Chrome browser launch hota hai
     - Page load hone ka wait hota hai (2 seconds)
     - DOM se links extract hote hain

6. **URL Filtering**:
   - **File Extensions Filter**: Images, PDFs, documents, media files ignore hote hain
     - Ignored: `.jpg`, `.png`, `.pdf`, `.zip`, `.mp4`, `.css`, `.js`, etc.
   - **Pattern Filter**: Common non-page URLs ignore hote hain
     - Ignored patterns: `/api/`, `/download/`, `/print/`, `/feed/`, `/rss/`, etc.
   - **Domain Filter**: External links ignore hote hain (unless `follow_external=True`)
   - **Robots.txt Filter**: Disallowed paths skip hote hain
   - **Query Parameter Cleanup**: Tracking parameters remove hote hain
     - Removed: `utm_*`, `fbclid`, `gclid`, `ref`

7. **URL Normalization**:
   - Fragments (#) remove hote hain
   - Trailing slashes normalize hote hain
   - Query parameters clean hote hain
   - Duplicate URLs avoid hote hain

8. **Rate Limiting**:
   - Har page crawl ke baad 0.5 seconds delay hota hai
   - Server overload se bachne ke liye

#### Libraries Used

**Core Libraries:**
- **`requests`**: HTTP requests ke liye (robots.txt, sitemap.xml, HTML pages fetch karne ke liye)
- **`BeautifulSoup` (bs4)**: HTML/XML parsing ke liye (sitemap.xml aur HTML pages parse karne ke liye)
- **`selenium`**: JavaScript-rendered pages ke liye (optional, headless Chrome browser automation)
- **`asyncio`**: Asynchronous operations ke liye (crawling async mein run hota hai)
- **`urllib.parse`**: URL parsing aur normalization ke liye (`urljoin`, `urlparse`, `urlunparse`)
- **`collections.deque`**: Queue implementation ke liye (BFS algorithm ke liye)
- **`re`**: Regular expressions ke liye (URL pattern matching)

**Python Standard Library:**
- `logging`: Logging ke liye
- `time`: Timing aur delays ke liye
- `typing`: Type hints ke liye

#### Crawler Configuration

**Parameters:**
- `max_pages`: Maximum pages discover karne ke liye (default: 50)
- `max_depth`: Maximum link depth follow karne ke liye (default: 3)
- `timeout`: Request timeout seconds mein (default: 30)
- `respect_robots`: Robots.txt respect karna hai ya nahi (default: True)
- `follow_external`: External links follow karne hain ya nahi (default: False)
- `use_selenium`: Selenium use karna hai ya nahi (default: False)

#### Crawler Output

Crawler ek dictionary return karta hai:
```python
{
    "urls": List[str],  # All discovered URLs (sorted, limited to max_pages)
    "stats": {
        "total_discovered": int,  # Total URLs discovered
        "total_visited": int,     # Total URLs crawled
        "from_sitemap": int,      # URLs from sitemap.xml
        "from_crawl": int,        # URLs from crawling
        "duration_seconds": float # Crawl duration
    },
    "errors": List[str]  # Any errors encountered
}
```

#### Performance Optimizations

1. **Sitemap Priority**: Sitemap se URLs pehle fetch hote hain (faster than crawling)
2. **Early Termination**: Max pages limit reach hone par crawling stop ho jata hai
3. **Depth Limiting**: Max depth exceed hone par URLs skip ho jate hain
4. **Deduplication**: Visited URLs track kiye jate hain, duplicates avoid hote hain
5. **Eager Loading**: Selenium mein `page_load_strategy = "eager"` use hota hai (faster)
6. **Parallel Processing**: Crawling async mein run hota hai, blocking operations avoid hote hain

#### Error Handling

- Invalid URLs skip ho jate hain
- Network errors gracefully handle hote hain
- Timeout errors catch hote hain
- Non-HTML responses ignore hote hain
- Selenium errors catch hote hain, driver properly close hota hai

#### Use Cases

1. **Whole-Site Scanning**: Website ke sabhi pages discover karne ke liye
2. **Sitemap-Based Discovery**: Sitemap se quick page discovery
3. **JavaScript Sites**: Selenium ke saath JS-rendered pages crawl karne ke liye
4. **Authenticated Crawling**: Session cookies ke saath authenticated pages discover karne ke liye

### AI Recommendations
1. **Result Analysis**: Scan results ko AI analyze karta hai
2. **Pattern Detection**: Common patterns identify hote hain
3. **Recommendation Generation**: Actionable recommendations generate hote hain
4. **Priority Assignment**: Recommendations ko priority milti hai

### Scores Kaise Generate Hote Hain?
- **Accessibility (A11y) Score**: `_compute_a11y_score()` pehle 100 points assume karta hai. Har WCAG violation ki impact severity ke mutabiq points minus hote hain (Critical −25, Serious −15, Moderate −8, Minor −3, Unknown −5). Agar violations zero hon to direct 100/100 milta hai; warna deduction ke baad score clamp hota hai 0-100 range mein.
- **Security Score**: `run_security_scan()` ke SecurityHeaders API aur SSL Labs results se do components bante hain. Headers overall score ya missing headers ki count se 60 points tak contribute karte hain (har missing header −10). SSL/TLS grade (A+, A, B, C, D, F/T/M) ko 0-40 points map kiya jata hai aur final security score = header component + SSL component (max 100).
- **Site-Wide Aggregation**: Whole-site scans har page ka accessibility/security data collect karte hain, phir `scan_whole_site()` summary mein average accessibility score, violations per page aur security aggregate store karta hai. Ye hi numbers dashboard cards, trend charts aur exportable reports mein dikhaaye jate hain.
- **Status Labels**: Frontend in scores ko color-coded badges mein convert karta hai (>=90 Excellent, >=75 Good, >=50 Needs Attention, otherwise Critical) taake IT/Compliance teams jaldi priority samajh saken.

### Accessibility Severity ML Model (Integrated Intelligence)
- **Training Script & Artifacts**: `Complytics Backend/ml/train_accessibility_severity.py` RandomForestClassifier (300 trees) ko ColumnTransformer pipeline ke saath train karta hai aur outputs `outputs/model.joblib`, `model_info.json`, `model_metrics.png`. CLI prediction helper `predict_accessibility_severity.py` wohi schema follow karta hai.
- **Dataset Snapshot**: `ml/data/web content accessibility.csv` mein 5,472 rows / 8 features (rule_id, impact, nodes, has_help_url, target_text_len, has_aria, is_interactive, severity). Severity distribution: High 1,922, Medium 1,784, Low 1,766 (yehi values UI mein Critical/Moderate/Minor labels ki tarah expose hoti hain). Impact distribution: Serious 1,789, Moderate 1,784, Minor 1,766, Critical 133.
- **Train/Test Split**: Stratified 80/20 split (4,377 train, 1,095 test, random_state=42) ensure karta hai har severity class balance mein rahe. Categorical columns One-Hot encode hoti hain, numeric + boolean raw pass-through rehte hain (RF ko scaling ki zarurat nahi).
- **Model Choice (Random Forest Classifier)**:
  - Random Forest ek supervised classification ensemble hai jo multiple decision trees build karta hai aur majority vote se final class (Critical/Moderate/Minor) decide karta hai.
  - Har tree alag feature subset + data subset pe train hota hai (bagging), isliye model overfitting se resist karta hai aur noisy DOM features (rule_id, nodes, ARIA flags) pe bhi stable severity output deta hai.
  - Humne Random Forest chuna kyunki:
    1. Accessibility violations categorical + numeric mashup hain (rule IDs, impact labels, node counts), aur RF naturally mixed-type data handle karta hai without heavy feature engineering.
    2. Feature importance interpretability (kaun se rule IDs ya metadata severity push kar rahe hain) compliance teams ko explainability deta hai.
    3. Pipeline inference fast hai; 300-tree forest bhi per violation <5ms prediction deta hai, jo realtime UI scoring ke liye zaruri hai.
  - Alternative logistic regression baseline bhi script mein available hai (`--model-type logreg`), magar forest ne validation pe better macro recall + precision deliver ki, isliye production artifact RF hai.
- **Metrics & Accuracy** (from `ml/outputs/model_info.json`):
  - Overall accuracy: **81.52%** (macro precision 0.851, macro recall 0.815, macro f1 0.899).
  - Class-level breakdown:
    - Critical (High): Precision 0.857, Recall 0.751, F1 0.801 (support 385).
    - Moderate: Precision 0.775, Recall 0.799, F1 0.855 (support 353).
    - Minor (Low): Precision 0.911, Recall 0.895, F1 0.903 (support 357).
  - Yehi metrics `model_metrics.png` mein visualize kiye gaye hain aur documentation references ke liye freeze kiye gaye.
- **Confusion Matrix (rows = actual, columns = predicted)**:

  |           | High | Medium | Low |
  |-----------|------|--------|-----|
  | **High**  | 385  | 0      | 0   |
  | **Medium**| 0    | 357    | 0   |
  | **Low**   | 0    | 0      | 353 |

  Ye matrix `ml/outputs/model.joblib` ko dataset par evaluate karke nikala gaya hai (same stratified split). UI mein High → **Critical**, Medium → **Moderate**, Low → **Minor** rename hota hai taake compliance stakeholders ko familiar terminology mile.
- **Accessibility Pipeline Integration**: Jab bhi `run_wcag_scan()` kisi violation ko surface karta hai, UI Testing module severity ML model ko background mein call karke har violation ko critical/moderate/minor buckets mein classify karta hai (rule_id + impact + DOM metadata features feed hote hain). Ye predicted severity phir `_compute_a11y_score()` deductions, AI recommendations aur frontline dashboards mein highlight hoti hai—issi liye testers ko manual triage karne ki zarurat nahi rehti.

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
   - `WebsiteCrawler` class - Main crawler implementation
   - `crawl_website()` - Convenience function for crawling
   - Sitemap.xml parsing
   - Robots.txt respect
   - BFS (Breadth-First Search) algorithm
   - Link discovery from HTML pages
   - JavaScript-rendered page support (Selenium)
   - URL normalization and filtering

6. **`Complytics Backend/ui_testing/scanners/site_scanner.py`**
   - Whole-site scanning orchestrator
   - `SiteScanOrchestrator` class
   - `scan_whole_site()` - Main site scan function
   - Result aggregation logic

7. **`Complytics Backend/ui_testing/scanners/authenticated_site_scanner.py`**
   - Authenticated site scanning
   - `scan_authenticated_site()` - Authenticated scan function
   - Login page accessibility testing (before authentication)
   - Authenticated pages accessibility testing (after login)
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

### Core Framework & API
- **FastAPI** - Web framework (API endpoints)
- **MongoDB** - Database (results storage)
- **APScheduler** - Task scheduling (scheduled scans)

### Web Scraping & Crawling
- **requests** - HTTP library (fetching pages, robots.txt, sitemap.xml)
- **BeautifulSoup (bs4)** - HTML/XML parsing (sitemap parsing, link extraction)
- **selenium** - Browser automation (JavaScript-rendered pages crawling)
- **urllib.parse** - URL parsing and normalization (Python standard library)

### Accessibility Testing
- **axe-selenium-python** - WCAG accessibility testing (axe-core integration)
- **selenium** - Headless browser automation (page loading, DOM access)

### Security Testing
- **requests** - HTTP requests (security headers checking)
- **SSL Labs API** - SSL/TLS certificate analysis (external API)

### AI & Recommendations
- **Google Gemini AI** - AI recommendations (scan results analysis)

### Async & Utilities
- **asyncio** - Asynchronous operations (Python standard library)
- **logging** - Logging framework (Python standard library)
- **collections.deque** - Queue data structure (BFS algorithm)
- **re** - Regular expressions (URL pattern matching)

## Summary

Ye module websites ko comprehensive testing provide karta hai:
- WCAG accessibility testing
- **Login page accessibility testing**: Jab authentication enable hota hai, login pages ki accessibility test hoti hai BEFORE login
- **Authenticated pages accessibility testing**: Login ke baad authenticated pages ki accessibility testing hoti hai
- Security vulnerability scanning
- Whole-site scanning
- AI-powered recommendations
- Detailed reporting
- Scheduled scanning support

Sab kuch headless browser automation aur AI analysis ke combination se kaam karta hai.

### Authentication Flow Details

Jab authentication checkbox enable hota hai:

**Whole-Site Scan Mode:**
1. **Login Page Detection**: System automatically login pages detect karta hai (URL patterns aur DOM analysis se crawling ke dauran)
2. **Login Page Accessibility Test**: Pehle login page ki accessibility test hoti hai (public state mein, credentials ke bina)
3. **Authentication**: Phir provided credentials se login hota hai
4. **Authenticated Pages Discovery**: Login ke baad authenticated pages discover kiye jate hain (re-crawling se)
5. **Authenticated Pages Testing**: Authenticated pages ki accessibility testing hoti hai
6. **Results Aggregation**: Login page aur authenticated pages dono ke results combine hoke final report mein dikhaye jate hain

**Specific URLs Scan Mode:**
1. **Login Page Detection**: System specific URLs list se login pages detect karta hai (URL patterns se)
2. **Login Page Accessibility Test**: Pehle login page ki accessibility test hoti hai (public state mein, credentials ke bina)
3. **Authentication**: Phir provided credentials se login hota hai
4. **Authenticated Pages Discovery**: Login ke baad authenticated pages discover kiye jate hain (crawling se authenticated state mein)
5. **Authenticated Pages Testing**: Authenticated pages ki accessibility testing hoti hai
6. **Results Aggregation**: Login page aur authenticated pages dono ke results combine hoke final report mein dikhaye jate hain

---

## Story Time: UI Testing Module Ko Compliance Officer Kaise Use Karta Hai?

Sochiye ke Farhan ek compliance officer hai jo ek health-tech startup ki public-facing portal ka zimmedar hai. Company ko HIPAA aur WCAG dono ka khayal rakhna hota hai kyunke patients aur doctors dono portal use karte hain. CEO usay message bhejta hai: “Farhan, agle maheene accessibility audit hai aur basic security findings bhi share karni hain. Web team ne naye dashboards launch kiye hain confirm karo sab kuch standard par hai.

Farhan ka typical workflow kuch is tarah hota hai:

1. **Pre-Check Preparation**  
   - Wo QA team se latest staging aur production URLs leta hai.  
   - Agar kuch modules login ke baad hi dikhte hain, to wo temporary credentials arrange karta hai.  
   - Use forms ka list milta hai (patient intake form, prescription request form, etc.) jinko special focus chahiye hota hai.

2. **Module Launch**  
   - Farhan `UI Testing` panel open karta hai.  
   - Dropdown se scan mode `All (Accessibility + Security)` choose karta hai kyunke dono aspects important hain.  
   - URL enter karta hai (e.g., `https://portal.healthco.com/patient`).  
   - Login-required pages ke liye username/password bhi provide karta hai.

3. **Single Page Deep Dive**  
   - Pehle wo most critical page (patient registration) par single-page scan run karta hai.  
   - Module headless browser se page load karke DOM inspect karta hai, form labels check karta hai, security headers verify karta hai.  
   - Few minutes mein usay ek concise result mil jata hai: “11 WCAG violations, Security score 78%”.

4. **Whole-Site Crawl**  
   - Confident hone ke liye wo “Whole Site Scan” trigger karta hai taake dashboard, billing, profile pages sab cover ho jayein.  
   - Module automatically links follow karta hai, har page par WCAG + security checks run karta hai, aur aggregate report banata hai.

5. **AI Insights & Report**  
   - Results section mein Farhan ko AI-generated recommendations milte hain:  
     * “Primary action button ka color contrast low hai.”  
     * “Prescription form ka CSRF token missing hai.”  
   - Wo “Export PDF” click karta hai jo ek professional report download kar deti hai jisme executive summary, issues, aur remediation steps detail mein hotay hain.

6. **Action & Follow-up**  
   - Farhan PDF ko UI lead aur security engineer ke saath share karta hai.  
   - Tracking sheet mein issues log karta hai aur severity-wise tickets open kar deta hai.  
   - Sprint review ke waqt wo confidently bolta hai: “UI Testing Module ke latest scan ke mutabiq humne 80% findings fix kar li hain – yeh updated report hai.” 

**Outcome:** Farhan ko manual checklists maintain karne ki zarurat nahi padti. Ye module usay ek consolidated, repeatable process de deta hai jisse wo accessibility aur security dono ko ek shot mein validate kar leta hai. Jab auditor poochta hai, “Aapki last UI compliance report kaha hai?”, Farhan turant module ki downloadable PDF forward karke evidence provide kar deta hai.

