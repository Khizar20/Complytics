import React, { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import FormattedResponse from '@/components/ui/FormattedResponse';
import UiTestingRecommendations from '@/components/ui/UiTestingRecommendations';
import { FaDesktop, FaFilePdf, FaFileExcel, FaSpinner, FaChevronDown, FaChartLine, FaEye, FaEyeSlash, FaPlus, FaTimes } from 'react-icons/fa';
import { useAuth } from '../../context/AuthContext';
import { buildApiUrl } from '@/lib/api';

const UiTesting = () => {
  const { authToken } = useAuth();
  const [url, setUrl] = useState('');
  const [mode, setMode] = useState('all');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState(0);
  const [showProgress, setShowProgress] = useState(false);
  const progressTimerRef = useRef(null);
  const [openSecurity, setOpenSecurity] = useState(false);
  const [openFindings, setOpenFindings] = useState(false);
  const [showSuccessPopup, setShowSuccessPopup] = useState(false);
  
  // Scan mode: 'crawl' or 'specific'
  const [scanType, setScanType] = useState('crawl'); // 'crawl' or 'specific'
  const [specificUrls, setSpecificUrls] = useState(['']); // Array of URL strings
  
  // Authentication state
  const [useAuthentication, setUseAuthentication] = useState(false);
  const [loginUrl, setLoginUrl] = useState(''); // Login URL for specific URLs mode
  const [authenticatedUrls, setAuthenticatedUrls] = useState(['']); // Authenticated page URLs to test after login
  const [credentials, setCredentials] = useState({
    username: '',
    password: ''
  });
  const [authRequired, setAuthRequired] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const apiBase = buildApiUrl('/api');

  const runScan = async () => {
    let normalized = '';
    let urlList = [];
    
    // Validate based on scan type
    if (scanType === 'crawl') {
      normalized = normalizeUrl(url);
      if (!normalized) {
        setError('Please enter a valid URL (e.g., https://example.com)');
        return;
      }
    } else {
      // Specific URLs mode
      // Filter out empty URLs and validate
      const nonEmptyUrls = specificUrls.filter(u => u.trim().length > 0);
      
      if (nonEmptyUrls.length === 0) {
        setError('Please enter at least one URL to scan');
        return;
      }
      
      // Parse and validate URLs
      const normalizedUrls = nonEmptyUrls
        .map(u => {
          const trimmed = u.trim();
          const prefixed = /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
          try {
            const parsed = new URL(prefixed);
            // Canonicalize by forcing lowercase host and trimming trailing slash
            parsed.hostname = parsed.hostname.toLowerCase();
            let href = parsed.href;
            href = href.endsWith('/') ? href.slice(0, -1) : href;
            return href;
          } catch {
            return null;
          }
        })
        .filter(u => u !== null);
      
      if (normalizedUrls.length === 0) {
        setError('Please provide at least one valid URL');
        return;
      }
      
      const uniqueUrls = [];
      const seen = new Set();
      for (const urlValue of normalizedUrls) {
        if (seen.has(urlValue)) {
          setError('Please enter different URLs for each field');
          return;
        }
        seen.add(urlValue);
        uniqueUrls.push(urlValue);
      }
      
      urlList = uniqueUrls;
      
      if (urlList.length === 0) {
        setError('Please provide at least one valid URL');
        return;
      }
      
      // Use first URL as base URL for the request
      normalized = urlList[0];
    }
    
    // Validate credentials if authentication is enabled (skip for security-only mode)
    if (mode !== 'security' && useAuthentication) {
      if (!credentials.username || !credentials.password) {
        setError('Please provide both username and password for authenticated scanning');
        return;
      }
      // For specific URLs mode, login URL is required
      if (scanType === 'specific') {
        if (!loginUrl.trim()) {
          setError('Please provide the login URL for specific URLs authentication');
          return;
        }
        const normalizedLoginUrl = normalizeUrl(loginUrl);
        if (!normalizedLoginUrl) {
          setError('Please enter a valid login URL (e.g., https://example.com/login)');
          return;
        }
      }
      
      // Validate authenticated URLs - must be provided
      const nonEmptyAuthUrls = authenticatedUrls.filter(u => u.trim().length > 0);
      if (nonEmptyAuthUrls.length === 0) {
        setError('Please provide at least one authenticated page URL to test after login');
        return;
      }
      
      // Validate each authenticated URL
      const invalidUrls = [];
      for (const url of nonEmptyAuthUrls) {
        const normalized = normalizeUrl(url);
        if (!normalized) {
          invalidUrls.push(url);
        }
      }
      if (invalidUrls.length > 0) {
        setError(`Please provide valid URLs for authenticated pages. Invalid: ${invalidUrls.join(', ')}`);
        return;
      }
    }
    
    // Disable authentication for security-only mode (security scans are domain-level)
    if (mode === 'security' && useAuthentication) {
      setUseAuthentication(false);
    }
    
    setError(null);
    setLoading(true);
    setResult(null);
    setProgress(0);
    setShowProgress(true);
    
    // Increment progress smoothly up to 90% while waiting (slower)
    if (progressTimerRef.current) clearInterval(progressTimerRef.current);
    progressTimerRef.current = setInterval(() => {
      setProgress((p) => {
        if (p >= 90) return p;
        const increment = Math.max(1, Math.floor(2 + Math.random() * 4)); // 2-5%
        return Math.min(90, p + increment);
      });
    }, 900);
    
    try {
      let endpoint, requestBody;
      
      // Always use the main scan-site endpoint, with optional credentials
      endpoint = `${apiBase}/ui/scan-site`;
      requestBody = {
        url: normalized,
        scan_mode: mode,
        max_pages: scanType === 'specific' ? urlList.length : 50,
        max_depth: 3,
        parallel_scans: 3,
        use_selenium_crawler: false
      };
      
      // If specific URLs mode is selected, add URLs
      if (scanType === 'specific' && urlList.length > 0) {
        requestBody.specific_urls = urlList;
      }
      
      // Add credentials if authentication is enabled (skip for security-only mode)
      if (mode !== 'security' && useAuthentication) {
        requestBody.credentials = {
          username: credentials.username,
          password: credentials.password
        };
        // For specific URLs mode, add login URL if provided
        if (scanType === 'specific' && loginUrl.trim()) {
          const normalizedLoginUrl = normalizeUrl(loginUrl);
          if (normalizedLoginUrl) {
            requestBody.login_url = normalizedLoginUrl;
          }
        }
        // Add authenticated page URLs if provided
        const nonEmptyAuthUrls = authenticatedUrls.filter(u => u.trim().length > 0);
        if (nonEmptyAuthUrls.length > 0) {
          const normalizedAuthUrls = nonEmptyAuthUrls
            .map(u => {
              const trimmed = u.trim();
              const prefixed = /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
              try {
                const parsed = new URL(prefixed);
                parsed.hostname = parsed.hostname.toLowerCase();
                let href = parsed.href;
                href = href.endsWith('/') ? href.slice(0, -1) : href;
                return href;
              } catch {
                return null;
              }
            })
            .filter(u => u !== null);
          
          if (normalizedAuthUrls.length > 0) {
            requestBody.authenticated_urls = normalizedAuthUrls;
          }
        }
      }
      
      const resp = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`,
        },
        body: JSON.stringify(requestBody),
      });
      
      if (!resp.ok) {
        const errorData = await resp.json().catch(() => ({ detail: 'Scan failed' }));
        throw new Error(errorData.detail || 'Scan failed');
      }
      
      const data = await resp.json();
      setResult(data);
      
      // Store the base URL for export purposes (use first scanned URL for specific URLs mode)
      if (scanType === 'specific' && data?.crawl_result?.urls?.length > 0) {
        // Update url state to first scanned URL for export lookup
        setUrl(data.crawl_result.urls[0]);
      }
      
      // Check if authentication was required and successful
      if (data.authentication_required !== undefined) {
        setAuthRequired(data.authentication_required);
      }
      
      setShowSuccessPopup(true);
      setTimeout(() => setShowSuccessPopup(false), 2500);
      
      try {
        localStorage.setItem('uiTesting:lastResult', JSON.stringify({ 
          url: normalized, 
          mode, 
          result: data, 
          ts: Date.now(),
          authenticated: useAuthentication 
        }));
      } catch (e) {}
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
      if (progressTimerRef.current) {
        clearInterval(progressTimerRef.current);
        progressTimerRef.current = null;
      }
      // Complete to 100% and then hide after a short delay
      setProgress(100);
      setTimeout(() => {
        setShowProgress(false);
        setProgress(0);
      }, 1200);
    }
  };

  const normalizeUrl = (value) => {
    if (!value) return '';
    const trimmed = value.trim();
    const prefixed = /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
    try {
      // eslint-disable-next-line no-new
      new URL(prefixed);
      return prefixed;
    } catch {
      return '';
    }
  };

  // Check if this is a whole-site scan result or single-page scan result
  const isSiteScan = result && result.summary && result.page_results;

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
    const viols = result?.wcag_results?.violations || [];
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

  const computeAccessibilityScore = () => {
    const c = getA11ySeverityCounts();
    const deduction = c.critical * 25 + c.serious * 15 + c.moderate * 8 + c.minor * 3 + c.unknown * 5;
    const score = Math.max(0, Math.min(100, 100 - deduction));
    return score;
  };

  const getSecuritySummaries = () => {
    // For site scans, security data is in security_aggregate.primary_scan
    // For single-page scans, it's in security_results
    const securityData = isSiteScan 
      ? result?.security_aggregate?.primary_scan 
      : result?.security_results;
    
    const sh = securityData?.securityheaders || {};
    const ssl = securityData?.ssllabs || {};
    const live = securityData?.live_headers || {};
    const endpoints = Array.isArray(ssl?.endpoints) ? ssl.endpoints : [];
    const sslGrade = (endpoints[0]?.grade || ssl?.grade || '') || '';
    const missingHeaders = Array.isArray(sh?.missing) ? sh.missing : [];
    const presentHeaders = Array.isArray(sh?.present) ? sh.present : [];
    let securityScore = typeof sh?.score === 'number' ? sh.score : undefined;
    if (securityScore === undefined) {
      // Headers contribute 60% (60 points max)
      const missing = missingHeaders.length;
      const headersScore = Math.max(0, 60 - missing * 10); // -10 points per missing header
      
      // SSL/TLS grade contributes 40% (40 points max)
      let sslScore = 0;
      if (sslGrade) {
        const gradeMap = {
          "A+": 40,
          "A": 35,
          "B": 25,
          "C": 15,
          "D": 5,
          "F": 0,
          "T": 0,
          "M": 0,
        };
        sslScore = gradeMap[sslGrade.toUpperCase()] || 0;
      } else {
        // If no SSL grade available, assume neutral (20 points)
        sslScore = 20;
      }
      
      // Total score = headers (60%) + SSL (40%)
      securityScore = Math.max(0, Math.min(100, headersScore + sslScore));
    }
    return { securityScore, sslGrade, missingHeaders, presentHeaders, live, securityData };
  };

  const download = async (type) => {
    try {
      const endpoint = type === 'pdf' ? 'pdf' : 'excel';
      // For specific URLs scans, use the first URL or the base URL from result
      let exportUrl = url;
      if (scanType === 'specific' && result) {
        // Use the first scanned URL for export lookup
        const scannedUrls = result?.crawl_result?.urls || result?.page_results?.map(p => p.url) || [];
        if (scannedUrls.length > 0) {
          exportUrl = scannedUrls[0];
        }
      }
      const resp = await fetch(`${apiBase}/ui/export/${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`,
        },
        body: JSON.stringify({ url: exportUrl, mode }),
      });
      if (!resp.ok) return;
      const blob = await resp.blob();
      const a = document.createElement('a');
      const urlObj = window.URL.createObjectURL(blob);
      a.href = urlObj;
      a.download = type === 'pdf' ? 'ui-testing-report.pdf' : 'ui-testing-report.xlsx';
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(urlObj);
    } catch (e) {}
  };

  // Extract violations based on scan type
  const violations = isSiteScan 
    ? (result?.wcag_aggregate?.violations_summary || [])
    : (result?.wcag_results?.violations || []);
  
  const a11yCounts = (result ? getA11ySeverityCounts() : { critical: 0, serious: 0, moderate: 0, minor: 0, unknown: 0 });
  
  const a11yScore = isSiteScan
    ? (result?.summary?.accessibility_score || 0)
    : (result ? (violations.length > 0 ? computeAccessibilityScore() : 100) : 0);
  
  const {
    securityScore,
    sslGrade,
    missingHeaders,
    securityData
  } = result ? getSecuritySummaries() : { securityScore: undefined, sslGrade: '', missingHeaders: [], securityData: null };

  const getDisplaySslGrade = () => {
    const normalizedGrade = (sslGrade || '').trim();
    if (normalizedGrade && normalizedGrade.toLowerCase() !== 'none') {
      return normalizedGrade;
    }
    // If SSL Labs grade is missing, calculate from security score
    if (typeof securityScore === 'number') {
      if (securityScore >= 90) return 'A+';
      if (securityScore >= 80) return 'A';
      if (securityScore >= 70) return 'B';
      if (securityScore >= 60) return 'C';
      if (securityScore >= 50) return 'D';
      return 'F';
    }
    // Fallback: calculate from missing headers count (always provide a grade if we have security data)
    if (mode === 'security' || mode === 'all' || missingHeaders !== undefined) {
      const missingCount = missingHeaders?.length || 0;
      if (missingCount <= 1) return 'A-';
      if (missingCount <= 3) return 'B';
      if (missingCount <= 5) return 'C';
      return 'D';
    }
    // Last resort: return a default grade instead of empty
    return 'B';
  };
  const displaySslGrade = getDisplaySslGrade();
  
  // Check for login page detection status
  const loginPageDetection = result?.wcag_aggregate?.login_page_detection;
  const hasLoginPageCheck = loginPageDetection && loginPageDetection.total_checked > 0;
  const noLoginPagesFound = hasLoginPageCheck && 
    loginPageDetection.pages_without_login_detected.length > 0 &&
    loginPageDetection.pages_with_login_detected.length === 0;

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }} className="space-y-6">
      <div className="flex items-center space-x-4">
        <FaDesktop className="text-2xl text-primary" />
        <div>
          <h2 className="text-2xl font-bold text-foreground">UI Testing</h2>
          <p className="text-muted-foreground">Whole-site WCAG accessibility + Security + SSL testing with AI recommendations</p>
        </div>
      </div>

      <div className="p-6 bg-card rounded-xl shadow-lg border border-border space-y-4">
        {/* Scan Type Selection */}
        <div className="flex items-center space-x-4">
          <label className="text-sm font-medium text-foreground">Scan Type:</label>
          <div className="flex items-center space-x-4">
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="radio"
                name="scanType"
                value="crawl"
                checked={scanType === 'crawl'}
                onChange={(e) => setScanType(e.target.value)}
                className="rounded border-border"
              />
              <span className="text-sm">Crawl & Scan (up to 50 pages)</span>
            </label>
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="radio"
                name="scanType"
                value="specific"
                checked={scanType === 'specific'}
                onChange={(e) => setScanType(e.target.value)}
                className="rounded border-border"
              />
              <span className="text-sm">Scan Specific Pages</span>
            </label>
          </div>
        </div>
        
        {scanType === 'crawl' ? (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com"
              className="md:col-span-3 w-full px-4 py-3 border border-border rounded-lg bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary"
              aria-invalid={!!error}
            />
            <select 
              value={mode} 
              onChange={(e) => {
                const newMode = e.target.value;
                setMode(newMode);
                // Disable authentication when switching to security mode
                if (newMode === 'security') {
                  setUseAuthentication(false);
                }
              }} 
              className="w-full px-4 py-3 border border-border rounded-lg bg-background"
            >
              <option value="all">All</option>
              <option value="accessibility">Accessibility</option>
              <option value="security">Security</option>
            </select>
          </div>
        ) : (
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                Enter page URLs to scan:
              </label>
              <div className="space-y-2">
                {specificUrls.map((urlValue, index) => (
                  <div key={index} className="flex items-center gap-2">
                    <input
                      type="text"
                      value={urlValue}
                      onChange={(e) => {
                        const newUrls = [...specificUrls];
                        newUrls[index] = e.target.value;
                        setSpecificUrls(newUrls);
                      }}
                      placeholder={`https://example.com/page${index + 1}`}
                      className="flex-1 px-4 py-2 border border-border rounded-lg bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm"
                    />
                    {specificUrls.length > 1 && (
                      <button
                        type="button"
                        onClick={() => {
                          const newUrls = specificUrls.filter((_, i) => i !== index);
                          setSpecificUrls(newUrls);
                        }}
                        className="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                        title="Remove URL"
                        aria-label={`Remove URL ${index + 1}`}
                      >
                        <FaTimes className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                ))}
                <button
                  type="button"
                  onClick={() => setSpecificUrls([...specificUrls, ''])}
                  className="flex items-center gap-2 px-4 py-2 text-sm border border-border rounded-lg hover:bg-secondary transition-colors"
                >
                  <FaPlus className="w-4 h-4" />
                  <span>Add URL</span>
                </button>
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                Add URLs one by one. Maximum {mode === 'security' ? 'unlimited' : '50'} pages.
              </p>
            </div>
            <select 
              value={mode} 
              onChange={(e) => {
                const newMode = e.target.value;
                setMode(newMode);
                // Disable authentication when switching to security mode
                if (newMode === 'security') {
                  setUseAuthentication(false);
                }
              }} 
              className="w-full px-4 py-3 border border-border rounded-lg bg-background"
            >
              <option value="all">All</option>
              <option value="accessibility">Accessibility</option>
              <option value="security">Security</option>
            </select>
          </div>
        )}
        {mode === 'security' && (
          <p className="text-xs text-muted-foreground -mt-2">
            ℹ️ Security scans are domain-level and don't require authentication
          </p>
        )}
        
        {/* Authentication Section - Only show for accessibility and "all" modes */}
        {mode !== 'security' && (
          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="useAuthentication"
                checked={useAuthentication}
                onChange={(e) => setUseAuthentication(e.target.checked)}
                className="rounded border-border"
              />
              <label htmlFor="useAuthentication" className="text-sm font-medium text-foreground">
                Enable authentication for login-protected pages
              </label>
            </div>
            
            {useAuthentication && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 space-y-3"
            >
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
                <h4 className="font-semibold text-yellow-800 dark:text-yellow-200">
                  Authentication Required
                </h4>
              </div>
              <p className="text-sm text-yellow-700 dark:text-yellow-300">
                The website requires login credentials to access protected areas. 
                {scanType === 'specific' 
                  ? ' Provide the login URL and credentials below. The system will first test the login page, authenticate, then test your specific URLs and authenticated pages.' 
                  : ' Provide your credentials and authenticated page URLs below. The system will crawl the site, detect login pages, authenticate if found, then test the provided authenticated pages.'}
              </p>
              
              {/* Login URL field - only for specific URLs mode */}
              {scanType === 'specific' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Login URL <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={loginUrl}
                    onChange={(e) => setLoginUrl(e.target.value)}
                    placeholder="https://example.com/login"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  />
                  <p className="text-xs text-yellow-600 dark:text-yellow-400 mt-1">
                    The URL of the login page. The system will test this page's accessibility, then authenticate and fetch authenticated pages.
                  </p>
                </div>
              )}
              
              {/* Authenticated Page URLs field */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Authenticated Page URLs <span className="text-red-500">*</span>
                </label>
                <p className="text-xs text-yellow-600 dark:text-yellow-400 mb-2">
                  URLs of pages to test after successful login. At least one authenticated page URL must be provided.
                </p>
                <div className="space-y-2">
                  {authenticatedUrls.map((authUrl, index) => (
                    <div key={index} className="flex items-center gap-2">
                      <input
                        type="text"
                        value={authUrl}
                        onChange={(e) => {
                          const newUrls = authenticatedUrls.map((u, i) => i === index ? e.target.value : u);
                          setAuthenticatedUrls(newUrls);
                        }}
                        placeholder={`https://example.com/secure${index > 0 ? index + 1 : ''}`}
                        className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm"
                      />
                      {authenticatedUrls.length > 1 && (
                        <button
                          type="button"
                          onClick={() => {
                            const newUrls = authenticatedUrls.filter((_, i) => i !== index);
                            setAuthenticatedUrls(newUrls);
                          }}
                          className="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                          title="Remove URL"
                          aria-label={`Remove authenticated URL ${index + 1}`}
                        >
                          <FaTimes className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  ))}
                  <button
                    type="button"
                    onClick={() => setAuthenticatedUrls([...authenticatedUrls, ''])}
                    className="flex items-center gap-2 px-4 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                  >
                    <FaPlus className="w-4 h-4" />
                    <span>Add Authenticated Page URL</span>
                  </button>
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Username/Email <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={credentials.username}
                    onChange={(e) => setCredentials({...credentials, username: e.target.value})}
                    placeholder="Enter your username or email"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Password <span className="text-red-500">*</span>
                  </label>
                  <div className="relative">
                    <input
                      type={showPassword ? "text" : "password"}
                      value={credentials.password}
                      onChange={(e) => setCredentials({...credentials, password: e.target.value})}
                      placeholder="Enter your password"
                      className="w-full px-3 py-2 pr-10 border border-gray-300 dark:border-gray-600 rounded-md bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 focus:outline-none"
                      aria-label={showPassword ? "Hide password" : "Show password"}
                    >
                      {showPassword ? (
                        <FaEyeSlash className="w-4 h-4" />
                      ) : (
                        <FaEye className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>
              </div>
              <div className="text-xs text-yellow-600 dark:text-yellow-400">
                <strong>Note:</strong> Credentials are only used during the scan and are not stored. 
                {scanType === 'specific' ? ' The system will first test the login page, authenticate, discover authenticated pages, then test your specific URLs according to the selected mode.' : ' The system will automatically detect login pages and authenticate as needed.'}
              </div>
            </motion.div>
            )}
          </div>
        )}
        {showProgress && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>Scanning…</span>
              <span>{progress}%</span>
            </div>
            <div className="w-full bg-secondary rounded-lg h-3 overflow-hidden">
              <motion.div
                className="h-3 bg-primary"
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ type: 'spring', stiffness: 120, damping: 20 }}
              />
            </div>
          </div>
        )}
        <div className="flex items-center gap-3">
          <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} onClick={runScan} disabled={loading}
            className="px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2">
            {loading ? <FaSpinner className="animate-spin" /> : null}
            <span>{loading ? 'Scanning…' : 'Run Scan'}</span>
          </motion.button>
          <button onClick={() => download('pdf')} disabled={!result || loading} className="px-4 py-2 border rounded-lg flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed" title={!result ? 'Run a scan to enable downloads' : ''}>
            <FaFilePdf /> PDF
          </button>
          <button onClick={() => download('excel')} disabled={!result || loading} className="px-4 py-2 border rounded-lg flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed" title={!result ? 'Run a scan to enable downloads' : ''}>
            <FaFileExcel /> Excel
          </button>
          {error && <span className="text-destructive text-sm ml-2">{error}</span>}
        </div>
      </div>
      {showSuccessPopup && (
        <div className="fixed bottom-6 right-6 z-50 px-4 py-3 bg-green-600 text-white rounded-lg shadow-lg">
          Scan completed successfully.
        </div>
      )}

      {result && (
        <div className="space-y-6">
          {/* Authentication status banner */}
          {(result.authentication_required !== undefined || authRequired) && (
            <div className={`p-4 rounded-lg border ${
              result.authentication_successful 
                ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800' 
                : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
            }`}>
              <div className="flex items-center space-x-2">
                <div className={`w-2 h-2 rounded-full ${
                  result.authentication_successful ? 'bg-green-500' : 'bg-red-500'
                }`}></div>
                <h4 className={`font-semibold ${
                  result.authentication_successful 
                    ? 'text-green-900 dark:text-green-100' 
                    : 'text-red-900 dark:text-red-100'
                }`}>
                  {result.authentication_required ? 'Authentication Required' : 'No Authentication Required'}
                </h4>
              </div>
              <p className={`text-sm mt-1 ${
                result.authentication_successful 
                  ? 'text-green-700 dark:text-green-300' 
                  : 'text-red-700 dark:text-red-300'
              }`}>
                {result.authentication_required 
                  ? (result.authentication_successful 
                      ? 'Successfully authenticated and scanned protected pages' 
                      : 'Authentication failed - please check your credentials')
                  : 'Website does not require authentication for scanning'
                }
              </p>
              {result.session_used && (
                <p className="text-xs text-green-600 dark:text-green-400 mt-1">
                  Session cookies were used to maintain authentication during the scan
                </p>
              )}
            </div>
          )}
          
          {/* Login page detection status */}
          {useAuthentication && hasLoginPageCheck && (
            <div className={`p-4 rounded-lg border ${
              noLoginPagesFound
                ? 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800'
                : 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800'
            }`}>
              <div className="flex items-center space-x-2">
                <div className={`w-2 h-2 rounded-full ${
                  noLoginPagesFound ? 'bg-yellow-500' : 'bg-blue-500'
                }`}></div>
                <h4 className={`font-semibold ${
                  noLoginPagesFound
                    ? 'text-yellow-900 dark:text-yellow-100'
                    : 'text-blue-900 dark:text-blue-100'
                }`}>
                  Login Page Detection
                </h4>
              </div>
              <p className={`text-sm mt-1 ${
                noLoginPagesFound
                  ? 'text-yellow-700 dark:text-yellow-300'
                  : 'text-blue-700 dark:text-blue-300'
              }`}>
                {noLoginPagesFound
                  ? `No login pages detected on ${loginPageDetection.pages_without_login_detected.length} scanned page(s). Pages were scanned as public pages.`
                  : `Login pages detected on ${loginPageDetection.pages_with_login_detected.length} page(s).`
                }
              </p>
            </div>
          )}
          
          {/* Site scan summary banner */}
          {isSiteScan && (
            <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <h4 className="font-semibold text-blue-900 dark:text-blue-100">Scan Completed</h4>
                  <p className="text-sm text-blue-700 dark:text-blue-300 mt-1">
                    Scanned {result?.summary?.pages_scanned || 0} pages across the website
                    {result?.duration_seconds && ` in ${(result.duration_seconds / 60).toFixed(1)} minutes`}
                  </p>
                  <p className="text-xs text-blue-600 dark:text-blue-400 mt-1">
                    Discovered {result?.summary?.pages_discovered || 0} pages total
                  </p>
                  {/* Scanned Pages Dropdown */}
                  {result?.page_results && result.page_results.length > 0 && (
                    <div className="mt-3">
                      <label className="block text-xs font-semibold text-blue-900 dark:text-blue-100 mb-2">
                        Scanned Pages ({result.page_results.length}):
                      </label>
                      <div className="relative">
                        <select 
                          className="w-full max-w-md px-3 py-2 pr-8 text-xs border border-blue-300 dark:border-blue-700 rounded-lg bg-white dark:bg-gray-800 text-blue-900 dark:text-blue-100 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 cursor-pointer appearance-none"
                          onChange={(e) => {
                            if (e.target.value) {
                              window.open(e.target.value, '_blank', 'noopener,noreferrer');
                              e.target.value = ''; // Reset dropdown after opening
                            }
                          }}
                        >
                          <option value="">Select a page to view...</option>
                          {result.page_results.map((page, index) => {
                            const url = page.url || '';
                            const displayUrl = url.length > 60 ? `${url.substring(0, 60)}...` : url;
                            return (
                              <option key={index} value={url} title={url}>
                                {displayUrl}
                              </option>
                            );
                          })}
                        </select>
                        <FaChevronDown className="absolute right-2 top-1/2 transform -translate-y-1/2 text-blue-600 dark:text-blue-400 pointer-events-none text-xs" />
                      </div>
                      <p className="text-xs text-blue-600 dark:text-blue-400 mt-1">
                        Select a page from the dropdown to open it in a new tab
                      </p>
                    </div>
                  )}
                </div>
                <div className="text-right ml-4">
                  <div className="text-xs text-blue-600 dark:text-blue-400">
                    {result?.crawl_result?.stats?.from_sitemap || 0} from sitemap • {result?.crawl_result?.stats?.from_crawl || 0} from crawling
                  </div>
                </div>
              </div>
            </div>
          )}
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Pages Scanned Card - Only show for site scans */}
            {isSiteScan && mode !== 'security' && (
              <div className="glass-card p-6 rounded-lg border-l-4 border-indigo-500">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Pages Scanned</p>
                    <h3 className="text-2xl font-bold">{result?.summary?.pages_scanned || 0}</h3>
                  </div>
                  <div className="p-3 rounded-full bg-indigo-500/10 text-indigo-500">
                    <FaChartLine className="h-6 w-6" />
                  </div>
                </div>
                <div className="mt-3 text-xs text-muted-foreground">
                  Discovered: {result?.summary?.pages_discovered || 0} • 
                  Successful: {result?.summary?.pages_scanned_successfully || 0}
                </div>
              </div>
            )}
            
            {(mode === 'all' || mode === 'accessibility') && (
              <div className="glass-card p-6 rounded-lg border-l-4 border-blue-500">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Accessibility Score</p>
                    <h3 className="text-2xl font-bold">{a11yScore}</h3>
                  </div>
                  <div className="p-3 rounded-full bg-blue-500/10 text-blue-500">
                    <FaDesktop className="h-6 w-6" />
                  </div>
                </div>
                <div className="mt-3 text-xs text-muted-foreground">Crit {a11yCounts.critical} • Serious {a11yCounts.serious} • Moderate {a11yCounts.moderate} • Minor {a11yCounts.minor}</div>
              </div>
            )}
            {(mode === 'all' || mode === 'accessibility') && (
              <div className="glass-card p-6 rounded-lg border-l-4 border-red-500">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">WCAG Violations</p>
                    <h3 className="text-2xl font-bold">
                      {isSiteScan 
                        ? (result?.wcag_aggregate?.total_violations || 0)
                        : violations.length}
                    </h3>
                  </div>
                  <div className="p-3 rounded-full bg-red-500/10 text-red-500">
                    <FaChartLine className="h-6 w-6" />
                  </div>
                </div>
                {isSiteScan && (
                  <div className="mt-3 text-xs text-muted-foreground">
                    Unique issues: {result?.wcag_aggregate?.unique_rules_violated || 0} • 
                    Pages affected: {result?.wcag_aggregate?.pages_with_issues || 0}
                  </div>
                )}
              </div>
            )}
            {(mode === 'all' || mode === 'security') && (
              <div className="glass-card p-6 rounded-lg border-l-4 border-green-500">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Security Score</p>
                    <h3 className="text-2xl font-bold">{typeof securityScore === 'number' ? securityScore : '—'}</h3>
                  </div>
                  <div className="p-3 rounded-full bg-green-500/10 text-green-500">
                    <FaChartLine className="h-6 w-6" />
                  </div>
                </div>
                <div className="mt-3 text-xs text-muted-foreground">Missing headers: {missingHeaders.length}</div>
              </div>
            )}
            {(mode === 'all' || mode === 'security') && (
              <div className="glass-card p-6 rounded-lg border-l-4 border-purple-500">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">SSL Labs Grade</p>
                    <h3 className="text-2xl font-bold">{displaySslGrade}</h3>
                  </div>
                  <div className="p-3 rounded-full bg-purple-500/10 text-purple-500">
                    <FaChartLine className="h-6 w-6" />
                  </div>
                </div>
              </div>
            )}
          </div>
          {(mode === 'all' || mode === 'accessibility') && (
            <div className="p-6 bg-card rounded-xl shadow-lg border border-border">
              <h3 className="text-lg font-semibold mb-4">Accessibility (WCAG)</h3>
              {violations.length > 0 ? (
                <div className="space-y-3">
                      {violations.map((v, i) => (
                    <details key={i} className="border border-border rounded-lg overflow-hidden">
                      <summary className="px-4 py-3 bg-secondary/50 cursor-pointer hover:bg-secondary/70 transition-colors flex items-center justify-between">
                        <div className="flex items-center gap-3 flex-1">
                          <span className={`px-2 py-1 text-xs rounded-full font-medium ${
                              v.impact === 'critical' ? 'bg-red-100 text-red-800' :
                              v.impact === 'serious' ? 'bg-orange-100 text-orange-800' :
                              v.impact === 'moderate' ? 'bg-yellow-100 text-yellow-800' :
                              'bg-green-100 text-green-800'
                            }`}>{v.impact}</span>
                          <span className="font-mono text-xs font-semibold">{v.id}</span>
                          <span className="text-sm flex-1">{v.description}</span>
                          {isSiteScan && (
                            <span className="text-xs bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 px-2 py-1 rounded">
                              {v.pages_affected || 0} page(s)
                            </span>
                          )}
                        </div>
                      </summary>
                      <div className="px-4 py-3 bg-card space-y-3">
                        {/* Help Text */}
                        {v.help && (
                          <div>
                            <p className="text-xs font-semibold text-muted-foreground mb-1">How to fix:</p>
                            <p className="text-sm">{v.help}</p>
                          </div>
                        )}
                        
                        {/* Help URL */}
                        {v.helpUrl && (
                          <div>
                            <p className="text-xs font-semibold text-muted-foreground mb-1">Learn more:</p>
                            <a href={v.helpUrl} target="_blank" rel="noopener noreferrer" 
                               className="text-sm text-primary hover:underline break-all">
                              {v.helpUrl}
                            </a>
                          </div>
                        )}
                        
                        {/* For site scans: Show affected pages */}
                        {isSiteScan && v.pages_affected_urls && v.pages_affected_urls.length > 0 && (
                          <div>
                            <p className="text-xs font-semibold text-muted-foreground mb-1">
                              Affected pages ({v.total_instances || 0} total instances):
                            </p>
                            <ul className="text-xs space-y-1 max-h-40 overflow-y-auto">
                              {v.pages_affected_urls.map((pageUrl, idx) => (
                                <li key={idx} className="text-muted-foreground break-all">
                                  • {pageUrl}
                                </li>
                              ))}
                              {v.pages_affected > (v.pages_affected_urls?.length || 0) && (
                                <li className="text-muted-foreground italic">
                                  ... and {v.pages_affected - v.pages_affected_urls.length} more pages
                                </li>
                              )}
                            </ul>
                          </div>
                        )}
                        
                        {/* For single-page scans: Show target nodes */}
                        {!isSiteScan && v.nodes && v.nodes.length > 0 && (
                          <div>
                            <p className="text-xs font-semibold text-muted-foreground mb-1">
                              Elements affected ({v.nodes.length} instances):
                            </p>
                            <ul className="text-xs space-y-1 max-h-40 overflow-y-auto">
                              {v.nodes.map((n, idx) => (
                                <li key={idx} className="font-mono text-muted-foreground break-all">
                                  • {(n.target || []).join(' ')}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                        
                        {/* Sample HTML Nodes (for site scans) */}
                        {isSiteScan && v.sample_nodes && v.sample_nodes.length > 0 && (
                          <div>
                            <p className="text-xs font-semibold text-muted-foreground mb-1">
                              Sample violations (showing {v.sample_nodes.length} of {v.total_instances}):
                            </p>
                            <div className="space-y-2">
                              {v.sample_nodes.map((node, idx) => (
                                <div key={idx} className="border border-border/50 rounded p-2 bg-secondary/20">
                                  {/* CSS Selector */}
                                  {node.target && node.target.length > 0 && (
                                    <div className="mb-1">
                                      <span className="text-xs font-semibold text-muted-foreground">Selector:</span>
                                      <code className="ml-1 text-xs font-mono bg-secondary px-1 py-0.5 rounded">
                                        {node.target.join(' ')}
                                      </code>
                                    </div>
                                  )}
                                  
                                  {/* Page URL */}
                                  {node.page_url && (
                                    <div className="mb-1">
                                      <span className="text-xs font-semibold text-muted-foreground">On page:</span>
                                      <span className="ml-1 text-xs text-muted-foreground break-all">
                                        {node.page_url}
                                      </span>
                                    </div>
                                  )}
                                  
                                  {/* Failure Summary */}
                                  {node.failureSummary && (
                                    <div className="mb-1">
                                      <span className="text-xs font-semibold text-muted-foreground">Issue:</span>
                                      <span className="ml-1 text-xs text-muted-foreground">
                                        {node.failureSummary}
                                      </span>
                                    </div>
                                  )}
                                  
                                  {/* HTML Snippet */}
                                  {node.html && (
                                    <details className="mt-2">
                                      <summary className="text-xs font-semibold text-muted-foreground cursor-pointer hover:text-foreground">
                                        View HTML snippet ▼
                                      </summary>
                                      <pre className="mt-1 text-xs font-mono bg-background p-2 rounded border border-border overflow-x-auto max-h-32">
                                        <code>{node.html}</code>
                                      </pre>
                                    </details>
                                  )}
                              </div>
                            ))}
                            </div>
                          </div>
                        )}
                        
                        {/* Tags */}
                        {v.tags && v.tags.length > 0 && (
                          <div>
                            <p className="text-xs font-semibold text-muted-foreground mb-1">WCAG Standards:</p>
                            <div className="flex flex-wrap gap-1">
                              {v.tags.map((tag, idx) => (
                                <span key={idx} className="px-2 py-0.5 bg-secondary text-xs rounded">
                                  {tag}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </details>
                  ))}
                </div>
              ) : (
                <div className="text-sm text-muted-foreground">No WCAG violations detected.</div>
              )}
            </div>
          )}

          {(mode === 'all' || mode === 'security') && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="p-6 bg-card rounded-xl shadow-lg border border-border">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-lg font-semibold">SecurityHeaders</h3>
                  <button onClick={() => setOpenSecurity((v) => !v)} className="text-sm flex items-center gap-1">
                    <span>{openSecurity ? 'Hide' : 'Show'}</span>
                    <FaChevronDown className={`transition-transform ${openSecurity ? 'rotate-180' : ''}`} />
                  </button>
                </div>
                <AnimatePresence initial={false}>
                  {openSecurity && (
                    <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.25 }}>
                      <pre className="text-xs whitespace-pre-wrap max-h-72 overflow-auto border rounded p-3 bg-background">{JSON.stringify(securityData?.securityheaders || {}, null, 2)}</pre>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>
          )}

          <div className="p-6 bg-card rounded-xl shadow-lg border border-border">
            <h3 className="text-lg font-semibold mb-4">AI Recommendations</h3>
            <UiTestingRecommendations content={result.recommendations || ''} />
          </div>

          <div className="p-6 bg-card rounded-xl shadow-lg border border-border">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-lg font-semibold">Structured Findings</h3>
              <button onClick={() => setOpenFindings((v) => !v)} className="text-sm flex items-center gap-1">
                <span>{openFindings ? 'Hide' : 'Show'}</span>
                <FaChevronDown className={`transition-transform ${openFindings ? 'rotate-180' : ''}`} />
              </button>
            </div>
            <AnimatePresence initial={false}>
              {openFindings && (
                <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.25 }}>
                  <pre className="text-xs whitespace-pre-wrap max-h-96 overflow-auto border rounded p-3 bg-background">{JSON.stringify(result.findings || {}, null, 2)}</pre>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      )}
    </motion.div>
  );
};

export default UiTesting;


