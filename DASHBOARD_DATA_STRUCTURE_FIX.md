# Dashboard Data Structure Fix

## Problem
The dashboard was showing **incorrect results** (all zeros) even though the UI Testing scan found real issues:
- **Expected:** 115 violations, 11 unique issues, accessibility score 5.0
- **Displayed:** 0 violations, 0 issues, accessibility score 100

## Root Cause
The dashboard code was reading data in the **single-page scan format** (`wcag_results`), but whole-site scans use a **different structure** (`wcag_aggregate`).

### Data Structure Comparison

**Single-Page Scan Structure:**
```javascript
{
  result: {
    wcag_results: {
      violations: [...],  // Array of violations
      passes: [...]
    },
    security_results: {
      securityheaders: {...},
      ssllabs: {...}
    }
  }
}
```

**Whole-Site Scan Structure:**
```javascript
{
  result: {
    summary: {
      accessibility_score: 5.0,
      pages_scanned: 50,
      ...
    },
    wcag_aggregate: {
      total_violations: 115,              // Total count across all pages
      unique_rules_violated: 11,          // Number of unique violation types
      pages_with_issues: 49,              // Pages that have issues
      impact_counts: {                    // Pre-calculated counts
        critical: 23,
        serious: 21,
        moderate: 22,
        minor: 21
      },
      violations_summary: [...]           // Array of unique violations with page counts
    },
    security_aggregate: {
      primary_scan: {                     // Domain-level security scan
        securityheaders: {...},
        ssllabs: {...}
      }
    },
    page_results: [...]                   // Individual page results
  }
}
```

## Solution Applied

Updated `src/components/team/UserDashboard.jsx` to handle both data structures:

### 1. **Violations Reading** (Line 329)
```javascript
// ✅ Now checks both structures
const violations = result?.wcag_aggregate?.violations_summary || result?.wcag_results?.violations || [];
```

### 2. **Total Violations Count** (Lines 332-339)
```javascript
const getTotalViolationsCount = () => {
  // For whole-site scans, use the total_violations count
  if (result?.wcag_aggregate?.total_violations !== undefined) {
    return result.wcag_aggregate.total_violations;  // Returns 115 ✅
  }
  // For single-page scans, use violations array length
  return violations.length;
};
```

### 3. **Severity Counts** (Lines 341-363)
```javascript
const getA11ySeverityCounts = () => {
  // ✅ For whole-site scans, use pre-calculated impact_counts
  if (result?.wcag_aggregate?.impact_counts) {
    return {
      critical: result.wcag_aggregate.impact_counts.critical || 0,  // 23
      serious: result.wcag_aggregate.impact_counts.serious || 0,    // 21
      moderate: result.wcag_aggregate.impact_counts.moderate || 0,  // 22
      minor: result.wcag_aggregate.impact_counts.minor || 0,        // 21
      unknown: 0
    };
  }
  
  // For single-page scans, count from violations array
  const counts = { critical: 0, serious: 0, moderate: 0, minor: 0, unknown: 0 };
  (violations || []).forEach((v) => {
    const impact = (v?.impact || '').toLowerCase();
    if (impact === 'critical') counts.critical += 1;
    // ... etc
  });
  return counts;
};
```

### 4. **Accessibility Score** (Lines 365-376)
```javascript
const computeAccessibilityScore = () => {
  // ✅ For whole-site scans, use pre-calculated score
  if (result?.summary?.accessibility_score !== undefined) {
    return result.summary.accessibility_score;  // Returns 5.0 ✅
  }
  
  // For single-page scans, calculate from severity counts
  const c = getA11ySeverityCounts();
  const deduction = c.critical * 25 + c.serious * 15 + c.moderate * 8 + c.minor * 3 + c.unknown * 5;
  const score = Math.max(0, Math.min(100, 100 - deduction));
  return score;
};
```

### 5. **Security Data Reading** (Lines 377-393)
```javascript
const getSecuritySummaries = () => {
  // ✅ Handle whole-site structure (security_aggregate.primary_scan) and single-page structure (security_results)
  const securityData = result?.security_aggregate?.primary_scan || result?.security_results || {};
  
  const sh = securityData?.securityheaders || {};
  const ssl = securityData?.ssllabs || {};
  // ... rest of logic
};
```

### 6. **Enhanced Violations Card** (Lines 447-464)
Now shows additional context for whole-site scans:
```javascript
<h3 className="text-2xl font-bold">{getTotalViolationsCount()}</h3>

{result?.wcag_aggregate?.unique_rules_violated && (
  <div className="mt-2 text-xs text-muted-foreground">
    {result.wcag_aggregate.unique_rules_violated} unique issues across {result.wcag_aggregate.pages_with_issues || 0} pages
  </div>
)}
```

**Output Example:**
```
WCAG Violations
115
11 unique issues across 49 pages
```

## What the Dashboard Shows Now ✅

Based on your scan results (115 violations, 11 unique issues, score 5.0):

### Accessibility Cards
1. **Accessibility Score:** `5.0` (not 100)
2. **WCAG Violations:** `115` (not 0)
   - Subtitle: "11 unique issues across 49 pages"
3. **Severity Breakdown:**
   - Critical: 23
   - Serious: 21
   - Moderate: 22
   - Minor: 21

### Charts
- **WCAG Severity Distribution Chart:** Shows the correct bar heights
- **Security Headers Coverage:** (if security scan was run)

## Testing
1. Refresh the dashboard page
2. The latest whole-site scan results should now display correctly
3. Both single-page and whole-site scan results are now supported

## Backward Compatibility ✅
The fix maintains backward compatibility with single-page scans by checking for both data structures:
- If `wcag_aggregate` exists → use whole-site structure
- Otherwise → fall back to single-page structure (`wcag_results`)

