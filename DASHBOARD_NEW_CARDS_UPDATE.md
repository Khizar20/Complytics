# Dashboard New Cards Update

## Added Two New Cards

### 1. **Pages Scanned Card** 🗺️
- **Color:** Orange border (`border-orange-500`)
- **Icon:** Globe icon (`FaGlobe`)
- **Data Source:** `result.summary.pages_scanned` or `result.wcag_aggregate.total_pages_scanned`
- **Subtitle:** Shows "X pages discovered" from `result.summary.pages_discovered`

**Example Display:**
```
Pages Scanned
50
50 pages discovered
```

### 2. **Scan Duration Card** ⏱️
- **Color:** Cyan border (`border-cyan-500`)
- **Icon:** Clock icon (`FaClock`)
- **Data Source:** `result.duration_seconds`
- **Format:** Human-readable (e.g., "2m 10s" or "129s")
- **Subtitle:** Shows raw seconds (e.g., "129.76s total")

**Example Display:**
```
Scan Duration
2m 10s
129.76s total
```

## Layout Changes

### Grid Layout Updated
- **Before:** `lg:grid-cols-4` (4 columns max)
- **After:** `lg:grid-cols-3 xl:grid-cols-6` (3 columns on large screens, 6 on extra large)

### Card Order (for accessibility mode):
1. **Accessibility Score** (Blue)
2. **WCAG Violations** (Red)
3. **Pages Scanned** (Orange) - **NEW**
4. **Scan Duration** (Cyan) - **NEW**

### Card Order (for all mode):
1. **Accessibility Score** (Blue)
2. **WCAG Violations** (Red)
3. **Pages Scanned** (Orange) - **NEW**
4. **Scan Duration** (Cyan) - **NEW**
5. **Security Score** (Green)
6. **SSL Labs Grade** (Purple)

## Technical Implementation

### New Function: `formatDuration`
```javascript
const formatDuration = (seconds) => {
  if (!seconds || seconds === 0) return '0s';
  
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.floor(seconds % 60);
  
  if (minutes > 0) {
    return `${minutes}m ${remainingSeconds}s`;
  } else {
    return `${remainingSeconds}s`;
  }
};
```

**Examples:**
- `129.76` → `"2m 10s"`
- `45` → `"45s"`
- `0` → `"0s"`

### New Import
```javascript
import { FaGlobe } from 'react-icons/fa';
```

### Data Sources
Both cards read from the whole-site scan result structure:

```javascript
// Pages Scanned
result?.summary?.pages_scanned || result?.wcag_aggregate?.total_pages_scanned || 0

// Scan Duration
result?.duration_seconds || 0
```

## What Users See Now

Based on your contour-software.com scan (50 pages, 129.76 seconds):

### Pages Scanned Card
```
Pages Scanned
50
50 pages discovered
```

### Scan Duration Card
```
Scan Duration
2m 10s
129.76s total
```

## Responsive Design

- **Mobile:** 1 column (stacked)
- **Medium:** 2 columns
- **Large:** 3 columns
- **Extra Large:** 6 columns (all cards in one row)

The cards will automatically wrap to new rows on smaller screens while maintaining proper spacing and readability.

## Backward Compatibility

- Cards only show for whole-site scans (which have `duration_seconds` and `pages_scanned` data)
- Single-page scans will show 0 for these values
- No breaking changes to existing functionality
