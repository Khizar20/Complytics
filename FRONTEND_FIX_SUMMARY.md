# Frontend Display Fix for Whole-Site Scanning Results

## Problem

The frontend was showing all zeros (0 pages scanned, 0 violations, etc.) even though the backend logs showed a successful scan of 50 pages with 115 violations found. This was because the frontend was looking for the wrong property names in the backend response.

## Root Cause

**Backend Response Structure:**
```json
{
  "summary": {
    "pages_scanned": 50,           // ❌ Frontend was looking for "total_pages"
    "pages_discovered": 50,
    "accessibility_score": 0
  },
  "crawl_result": {
    "urls": [...],
    "stats": {
      "from_sitemap": 48,           // ❌ Frontend was looking for "crawl_result.from_sitemap"
      "from_crawl": 2               // ❌ Frontend was looking for "crawl_result.from_crawling"
    }
  },
  "wcag_aggregate": {
    "total_violations": 115,
    "unique_rules_violated": 11,
    "pages_with_issues": 49,
    "impact_counts": {
      "critical": 28,
      "serious": 26,
      "moderate": 35,
      "minor": 26
    }
  },
  "duration_seconds": 341.48        // ❌ Frontend was looking for "scan_duration"
}
```

**Frontend was expecting:**
- `summary.total_pages` → **Should be** `summary.pages_scanned`
- `summary.scan_duration` → **Should be** `duration_seconds`
- `crawl_result.from_sitemap` → **Should be** `crawl_result.stats.from_sitemap`
- `crawl_result.from_crawling` → **Should be** `crawl_result.stats.from_crawl`

## Solution

### 1. Fixed Site Scan Summary Banner

**Before:**
```jsx
Scanned {result?.summary?.total_pages || 0} pages across the website
{result?.summary?.scan_duration && ` in ${result.summary.scan_duration}`}

{result?.crawl_result?.from_sitemap || 0} from sitemap • 
{result?.crawl_result?.from_crawling || 0} from crawling
```

**After:**
```jsx
Scanned {result?.summary?.pages_scanned || 0} pages across the website
{result?.duration_seconds && ` in ${(result.duration_seconds / 60).toFixed(1)} minutes`}
Discovered {result?.summary?.pages_discovered || 0} pages total

{result?.crawl_result?.stats?.from_sitemap || 0} from sitemap • 
{result?.crawl_result?.stats?.from_crawl || 0} from crawling
```

### 2. Fixed Severity Counts for Site Scans

**Before:** The frontend was counting violations from the `all_violations` array, which didn't match the aggregated counts shown in backend logs.

**After:** For site scans, use the pre-computed `impact_counts` from `wcag_aggregate`:

```jsx
const getA11ySeverityCounts = () => {
  // For site scans, use aggregated impact counts
  if (isSiteScan && result?.wcag_aggregate?.impact_counts) {
    const impactCounts = result.wcag_aggregate.impact_counts;
    return {
      critical: impactCounts.critical || 0,
      serious: impactCounts.serious || 0,
      moderate: impactCounts.moderate || 0,
      minor: impactCounts.minor || 0,
      unknown: 0
    };
  }
  
  // For single-page scans, count from violations array
  const counts = { critical: 0, serious: 0, moderate: 0, minor: 0, unknown: 0 };
  const viols = isSiteScan 
    ? (result?.wcag_aggregate?.all_violations || [])
    : (result?.wcag_results?.violations || []);
  (viols || []).forEach((v) => {
    const impact = (v?.impact || '').toLowerCase();
    if (impact === 'critical') counts.critical += 1;
    else if (impact === 'serious') counts.serious += 1;
    else if (impact === 'moderate') counts.moderate += 1;
    else if (impact === 'minor') counts.minor += 1;
    else counts.unknown += 1;
  });
  return counts;
};
```

### 3. Fixed Total Violations Display

**Before:** Always showed `violations.length`

**After:** For site scans, show the aggregated total and additional stats:

```jsx
<h3 className="text-2xl font-bold">
  {isSiteScan 
    ? (result?.wcag_aggregate?.total_violations || 0)
    : violations.length}
</h3>

{isSiteScan && (
  <div className="mt-3 text-xs text-muted-foreground">
    Unique issues: {result?.wcag_aggregate?.unique_rules_violated || 0} • 
    Pages affected: {result?.wcag_aggregate?.pages_with_issues || 0}
  </div>
)}
```

### 4. Fixed Accessibility Score

**Before:** Was computing score from violations

**After:** For site scans, use the pre-computed score from backend:

```jsx
const a11yScore = isSiteScan
  ? (result?.summary?.accessibility_score || 0)
  : (result ? (violations.length > 0 ? computeAccessibilityScore() : 100) : 0);
```

---

## What You'll See Now

Based on your terminal output showing:
- **50 pages scanned**
- **115 total violations**
- **28 critical, 26 serious, 35 moderate, 26 minor**
- **11 unique issues**
- **49 pages with issues**
- **Duration: 341.48s (5.7 minutes)**

The frontend will now display:

### Site Summary Banner:
```
Whole-Site Scan Complete
Scanned 50 pages across the website in 5.7 minutes
Discovered 50 pages total

48 from sitemap • 2 from crawling
```

### Accessibility Score Card:
```
Accessibility Score
0

Crit 28 • Serious 26 • Moderate 35 • Minor 26
```

### WCAG Violations Card:
```
WCAG Violations
115

Unique issues: 11 • Pages affected: 49
```

---

## Testing the Fix

1. **Refresh the frontend** (hard refresh with Ctrl+F5 to clear cache)

2. **The cached result should now display correctly** with:
   - ✅ 50 pages scanned (not 0)
   - ✅ 5.7 minutes duration (not blank)
   - ✅ 48 from sitemap, 2 from crawling (not 0 • 0)
   - ✅ 115 total violations (not 0)
   - ✅ 28 critical, 26 serious, etc. (not all zeros)
   - ✅ Accessibility score: 0 (correct based on violations)

3. **Or run a new scan** to see the results populate in real-time

---

## Property Mapping Reference

For future reference, here's the complete mapping:

| Frontend Expected | Backend Actual | Location |
|------------------|----------------|----------|
| `summary.total_pages` | `summary.pages_scanned` | Site summary banner |
| `summary.scan_duration` | `duration_seconds` | Site summary banner |
| `crawl_result.from_sitemap` | `crawl_result.stats.from_sitemap` | Discovery stats |
| `crawl_result.from_crawling` | `crawl_result.stats.from_crawl` | Discovery stats |
| `wcag_aggregate.impact_counts` | ✅ Already correct | Severity counts |
| `wcag_aggregate.total_violations` | ✅ Already correct | Total violations |
| `wcag_aggregate.unique_rules_violated` | ✅ Already correct | Unique issues |
| `wcag_aggregate.pages_with_issues` | ✅ Already correct | Pages affected |
| `summary.accessibility_score` | ✅ Already correct | Accessibility score |

---

## Summary

All property name mismatches have been fixed. The frontend now correctly reads and displays:
- ✅ Number of pages scanned
- ✅ Scan duration in minutes
- ✅ Discovery stats (sitemap vs crawling)
- ✅ Total violations across all pages
- ✅ Unique issues and pages affected
- ✅ Severity breakdown (critical, serious, moderate, minor)
- ✅ Site-wide accessibility score

**The results from your 50-page scan will now display correctly!** 🎉

