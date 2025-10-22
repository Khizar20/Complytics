# AI Recommendations System Improvements

## Overview
Enhanced the AI recommendations system to provide more actionable, human-friendly guidance tailored to the scan mode and actual results.

## Changes Made

### 1. **Mode-Specific Prompting**

#### **Accessibility-Only Mode**
**Before:**
```
"You are an accessibility auditor. Only analyze accessibility.
WCAG Summary (top 12): [violations]
Generate clear, actionable recommendations..."
```

**After:**
```
"You are an accessibility expert analyzing a whole-site WCAG audit.

## Site-Wide Accessibility Results:
- Total violations: 127
- Unique issues: 8
- Pages with issues: 32
- Critical: 3 | Serious: 12 | Moderate: 50 | Minor: 17

## Top Issues:
[Detailed violation data with pages_affected and total_instances]

## Your Task:
For EACH violation, provide:
1. Issue Title - Clear, non-technical description
2. Impact - Why this matters for users with disabilities
3. How to Fix - Step-by-step implementation guide
4. Affected Pages - How many pages have this issue
5. Priority - When to fix this
```

**Benefits:**
- ✅ Uses actual site-wide statistics
- ✅ Shows pages affected for each issue
- ✅ Provides implementation guidance structure
- ✅ No Security Agent mentioned
- ✅ No Navigation Agent mentioned

#### **Security-Only Mode**
- Only security audit context
- No accessibility or navigation agents mentioned
- Focus on missing headers and SSL configuration

#### **Combined Mode**
- TWO clear sections: ACCESSIBILITY and SECURITY
- Each with appropriate context and guidance
- No redundant agent mentions

### 2. **Enhanced Data Passing**

**Updated `routes/ui_testing.py`:**
```python
# Before
ai_input = {
    "wcag_results": {
        "violations": violations_summary,
        "total_violations": count,
        "impact_counts": counts
    }
}

# After
ai_input = {
    "wcag_results": {
        "violations": violations_summary,
        "total_violations": count,
        "unique_rules_violated": unique_count,
        "pages_with_issues": pages_count,
        "total_pages_scanned": total,
        "impact_counts": counts
    }
}
```

**Benefits:**
- AI now has complete site-wide statistics
- Can mention how many pages are affected
- Can provide better prioritization guidance

### 3. **Increased Token Limits**

**Before:**
- `UI_AI_MAX_TOKENS`: 1024
- `max_output_tokens`: 2048

**After:**
- `UI_AI_MAX_TOKENS`: 2048
- `max_output_tokens`: 4096

**Benefits:**
- More detailed recommendations possible
- Can cover more violations comprehensively
- Better step-by-step guidance

### 4. **Structured Output Format**

**Recommended Format for AI:**
```markdown
### [Critical] Issue Title (23 pages affected)
**Impact:** This prevents screen reader users from...

**How to Fix:**
1. Identify all form inputs without labels
2. Add <label> elements with for="input-id"
3. Ensure label text is descriptive
4. Test with screen reader

**Priority:** Fix immediately before launch
```

**Benefits:**
- Clear severity indication
- Shows impact on real users
- Step-by-step implementation
- Pages affected mentioned
- Priority guidance

### 5. **Detailed Violation Data**

For each violation, the AI now receives:
```python
{
    "rule": "label",
    "description": "Ensures every form element has a label",
    "impact": "critical",
    "pages_affected": 23,  # NEW
    "total_instances": 45,  # NEW
    "help": "Add label elements..."  # NEW
}
```

**Benefits:**
- AI knows which issues are widespread
- Can prioritize fixes affecting most pages
- Can reference official guidance

## Example Output Comparison

### **Before (With Issues):**
```
Okay, team, let's get this website audit done.

Accessibility Agent:
[Critical] Form elements missing labels — Add <label> elements...

Security Agent:
No security issues detected.

Navigation Agent:
No URL provided, so no navigation issues can be assessed.

Reviewer:
Executive Summary
The website has several accessibility issues...
```

**Problems:**
- ❌ Mentions Security Agent (not relevant for accessibility-only)
- ❌ Mentions Navigation Agent (not used)
- ❌ Redundant sections
- ❌ No pages affected information
- ❌ Generic "how to fix" guidance

### **After (Improved):**
```markdown
# Accessibility Audit Recommendations

## Executive Summary
This website has 127 accessibility violations across 32 pages, with 3 critical issues requiring immediate attention.

---

## Critical Issues

### Missing Form Labels (23 pages affected)
**Impact:** Screen reader users cannot identify what information to enter in form fields. This violates WCAG 2.1 Level A and prevents users with disabilities from completing forms.

**How to Fix:**
1. Locate all `<input>`, `<select>`, and `<textarea>` elements in your forms
2. Add a `<label>` element before or after each form control
3. Set the label's `for` attribute to match the input's `id`:
   ```html
   <label for="email">Email Address:</label>
   <input type="email" id="email" name="email">
   ```
4. For icon-only buttons, use `aria-label`:
   ```html
   <button aria-label="Submit form">
     <i class="icon-submit"></i>
   </button>
   ```
5. Test with NVDA or JAWS screen reader

**Priority:** Fix immediately - This is a WCAG Level A violation blocking form submission for disabled users.

---

### Invalid ARIA Attributes (5 pages affected)
**Impact:** Screen readers may ignore or misinterpret elements, causing confusion for users with disabilities.

**How to Fix:**
1. Review ARIA attributes on each element
2. Check against the ARIA in HTML specification
3. Common mistakes to fix:
   - Don't use `aria-label` on `<div>` without a role
   - Remove `aria-hidden="true"` from interactive elements
   - Use `role="button"` before adding button ARIA attributes
4. Validate with axe DevTools browser extension

**Priority:** Fix within 1 week - Serious usability impact for assistive technology users.

---

## Serious Issues

### Links Without Discernible Text (21 pages affected)
**Impact:** Screen reader users hear "link" without knowing the destination, making navigation impossible.

**How to Fix:**
1. Find all links with only icons or images
2. Add descriptive text:
   ```html
   <!-- Bad -->
   <a href="/home"><i class="icon-home"></i></a>
   
   <!-- Good -->
   <a href="/home">
     <i class="icon-home" aria-hidden="true"></i>
     <span class="sr-only">Home Page</span>
   </a>
   
   <!-- Or -->
   <a href="/home" aria-label="Home Page">
     <i class="icon-home"></i>
   </a>
   ```
3. Ensure link text describes the destination

**Priority:** Fix within 2 weeks - Major navigation barrier.

---

[Additional issues continue with same format...]

## Implementation Roadmap

**Week 1 (Critical):**
- Fix all form labels (23 pages)
- Fix invalid ARIA attributes (5 pages)

**Week 2-3 (Serious):**
- Add link text (21 pages)
- Add page titles (2 pages)
- Add lang attribute (2 pages)

**Week 4+ (Moderate):**
- Fix heading order
- Add H1 to pages
- Improve landmark structure

## Testing Recommendations

1. **Automated:** Run axe DevTools on each fixed page
2. **Manual:** Test with NVDA screen reader
3. **Keyboard:** Tab through all forms without mouse
4. **Validation:** Use WAVE browser extension for quick checks
```

**Improvements:**
- ✅ No irrelevant agent mentions
- ✅ Uses actual violation data (23 pages, 5 pages, etc.)
- ✅ Human-friendly implementation steps
- ✅ Code examples included
- ✅ Clear prioritization with timeline
- ✅ Testing recommendations
- ✅ Explains WHY each issue matters

## Technical Implementation

### Files Modified:
1. `ui_testing/ai/recommendations.py` - Enhanced prompting
2. `routes/ui_testing.py` - Complete data passing

### Key Functions Updated:
- `generate_recommendations()` - Mode-specific prompting
- Accessibility mode prompt - Site-wide context
- Combined mode prompt - Two-section structure
- Retry logic - Compact site-wide summaries

### Configuration Changes:
- `_UI_MAX_TOKENS`: 1024 → 2048
- `max_output_tokens`: 2048 → 4096

## Benefits Summary

### For Accessibility-Only Scans:
✅ No Security/Navigation Agent mentions
✅ Uses site-wide statistics (pages affected)
✅ Implementation-focused guidance
✅ Prioritization based on severity and spread
✅ Code examples for common fixes

### For Security-Only Scans:
✅ No Accessibility/Navigation Agent mentions
✅ Focus on missing headers and SSL
✅ Implementation guidance

### For Combined Scans:
✅ Clear two-section structure
✅ Both accessibility and security covered
✅ No redundant agent mentions
✅ Comprehensive recommendations

## Testing

### Before Testing:
Run an accessibility-only scan:
```bash
POST /api/ui/scan-site
{
  "url": "https://example.com",
  "scan_mode": "accessibility",
  "max_pages": 50
}
```

### Expected Results:
- ✅ No Security Agent mentioned
- ✅ Pages affected shown (e.g., "23 pages")
- ✅ Step-by-step implementation guidance
- ✅ Severity-based organization
- ✅ Priority recommendations
- ✅ Testing guidance

## Future Enhancements

1. **Code Snippets**: Include framework-specific examples (React, Vue, Angular)
2. **Before/After**: Show visual comparisons
3. **Testing Scripts**: Generate automated test code
4. **Compliance Mapping**: Map to WCAG 2.1 success criteria
5. **Remediation Cost**: Estimate developer hours needed
6. **Impact Analysis**: Show user statistics affected

---

**Implementation Date:** October 2025
**Version:** 2.1
**Status:** ✅ Ready for Production

