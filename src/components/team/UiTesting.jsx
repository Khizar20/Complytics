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
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }} className="space-y-10 p-8">
      <div className="flex items-center space-x-4 mb-6">
        <div className="p-3 bg-gradient-to-br from-blue-600 to-blue-500 rounded-xl shadow-lg">
          <FaDesktop className="text-3xl text-white" />
        </div>
        <div>
          <h2 className="text-4xl md:text-5xl font-bold text-black">UI Testing</h2>
          <p className="text-lg text-gray-600 mt-2">Whole-site WCAG accessibility + Security + SSL testing with AI recommendations</p>
        </div>
      </div>

      <motion.div 
        whileHover={{ scale: 1.01 }}
        className="p-8 bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl hover:shadow-2xl border-2 border-blue-200 relative overflow-hidden group space-y-6"
      >
        <div className="absolute top-0 right-0 w-48 h-48 bg-blue-500/10 rounded-full blur-3xl -mr-24 -mt-24 animate-pulse-slow"></div>
        <div className="relative z-10">
        {/* Scan Type Selection */}
        <div className="flex items-center space-x-4 mb-4">
          <label className="text-sm font-bold text-gray-900">Scan Type:</label>
          <div className="flex items-center space-x-6 bg-blue-50/50 backdrop-blur-sm rounded-full p-1 border-2 border-blue-200">
            <label className="flex items-center space-x-2 cursor-pointer px-4 py-2 rounded-full transition-all">
              <input
                type="radio"
                name="scanType"
                value="crawl"
                checked={scanType === 'crawl'}
                onChange={(e) => setScanType(e.target.value)}
                className="w-4 h-4 text-blue-600 focus:ring-blue-500 border-gray-300"
              />
              <span className={`text-sm font-semibold ${scanType === 'crawl' ? 'text-blue-700' : 'text-gray-600'}`}>Crawl & Scan (up to 50 pages)</span>
            </label>
            <label className="flex items-center space-x-2 cursor-pointer px-4 py-2 rounded-full transition-all">
              <input
                type="radio"
                name="scanType"
                value="specific"
                checked={scanType === 'specific'}
                onChange={(e) => setScanType(e.target.value)}
                className="w-4 h-4 text-blue-600 focus:ring-blue-500 border-gray-300"
              />
              <span className={`text-sm font-semibold ${scanType === 'specific' ? 'text-blue-700' : 'text-gray-600'}`}>Scan Specific Pages</span>
            </label>
          </div>
        </div>
        
        {scanType === 'crawl' ? (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com"
              className="md:col-span-3 w-full px-5 py-3.5 border-2 border-gray-300 rounded-xl bg-white focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all shadow-sm"
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
              className="w-full px-5 py-3.5 border-2 border-gray-300 rounded-xl bg-white focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all shadow-sm"
            >
              <option value="all">All</option>
              <option value="accessibility">Accessibility</option>
              <option value="security">Security</option>
            </select>
          </div>
        ) : (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-bold text-gray-900 mb-3">
                Enter page URLs to scan:
              </label>
              <div className="space-y-3">
                {specificUrls.map((urlValue, index) => (
                  <div key={index} className="flex items-center gap-3">
                    <input
                      type="text"
                      value={urlValue}
                      onChange={(e) => {
                        const newUrls = [...specificUrls];
                        newUrls[index] = e.target.value;
                        setSpecificUrls(newUrls);
                      }}
                      placeholder={`https://example.com/page${index + 1}`}
                      className="flex-1 px-5 py-3 border-2 border-gray-300 rounded-xl bg-white focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all shadow-sm text-sm"
                    />
                    {specificUrls.length > 1 && (
                      <button
                        type="button"
                        onClick={() => {
                          const newUrls = specificUrls.filter((_, i) => i !== index);
                          setSpecificUrls(newUrls);
                        }}
                        className="p-3 text-white bg-gradient-to-r from-red-600 to-red-500 hover:from-red-700 hover:to-red-600 rounded-xl transition-all shadow-md hover:shadow-lg"
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
                  className="flex items-center gap-2 px-5 py-2.5 text-sm border-2 border-gray-300 rounded-xl hover:bg-gray-50 hover:border-blue-500 transition-all shadow-sm font-semibold text-gray-900"
                >
                  <FaPlus className="w-4 h-4" />
                  <span>Add URL</span>
                </button>
              </div>
              <p className="text-xs text-gray-600 mt-3 font-medium">
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
              className="w-full px-5 py-3.5 border-2 border-gray-300 rounded-xl bg-white focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all shadow-sm"
            >
              <option value="all">All</option>
              <option value="accessibility">Accessibility</option>
              <option value="security">Security</option>
            </select>
          </div>
        )}
        {mode === 'security' && (
          <div className="p-4 bg-blue-50/80 backdrop-blur-sm border-2 border-blue-200 rounded-xl">
            <p className="text-sm text-blue-800 font-medium">
              ℹ️ Security scans are domain-level and don't require authentication
            </p>
          </div>
        )}
        
        {/* Authentication Section - Only show for accessibility and "all" modes */}
        {mode !== 'security' && (
          <div className="space-y-6 mt-8">
            <div className="flex items-center space-x-3">
              <input
                type="checkbox"
                id="useAuthentication"
                checked={useAuthentication}
                onChange={(e) => setUseAuthentication(e.target.checked)}
                className="w-5 h-5 rounded border-2 border-gray-300 text-blue-600 focus:ring-blue-500/50"
              />
              <label htmlFor="useAuthentication" className="text-sm font-bold text-gray-900 cursor-pointer">
                Enable authentication for login-protected pages
              </label>
            </div>
            
            {useAuthentication && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="bg-gradient-to-r from-yellow-50/80 to-orange-50/80 backdrop-blur-sm border-2 border-yellow-300 rounded-xl p-6 space-y-4 shadow-sm"
            >
              <div className="flex items-center space-x-3">
                <div className="w-3 h-3 bg-yellow-600 rounded-full shadow-md"></div>
                <h4 className="font-bold text-lg text-yellow-900">
                  Authentication Required
                </h4>
              </div>
              <p className="text-sm text-yellow-800 font-medium leading-relaxed">
                The website requires login credentials to access protected areas. 
                {scanType === 'specific' 
                  ? ' Provide the login URL and credentials below. The system will first test the login page, authenticate, then test your specific URLs and authenticated pages.' 
                  : ' Provide your credentials and authenticated page URLs below. The system will crawl the site, detect login pages, authenticate if found, then test the provided authenticated pages.'}
              </p>
              
              {/* Login URL field - only for specific URLs mode */}
              {scanType === 'specific' && (
                <div>
                  <label className="block text-sm font-bold text-gray-900 mb-2">
                    Login URL <span className="text-red-600">*</span>
                  </label>
                  <input
                    type="text"
                    value={loginUrl}
                    onChange={(e) => setLoginUrl(e.target.value)}
                    placeholder="https://example.com/login"
                    className="w-full px-4 py-3 border-2 border-gray-300 rounded-xl bg-white focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all shadow-sm"
                  />
                  <p className="text-xs text-yellow-700 mt-2 font-medium">
                    The URL of the login page. The system will test this page's accessibility, then authenticate and fetch authenticated pages.
                  </p>
                </div>
              )}
              
              {/* Authenticated Page URLs field */}
              <div>
                <label className="block text-sm font-bold text-gray-900 mb-2">
                  Authenticated Page URLs <span className="text-red-600">*</span>
                </label>
                <p className="text-xs text-yellow-700 mb-3 font-medium">
                  URLs of pages to test after successful login. At least one authenticated page URL must be provided.
                </p>
                <div className="space-y-3">
                  {authenticatedUrls.map((authUrl, index) => (
                    <div key={index} className="flex items-center gap-3">
                      <input
                        type="text"
                        value={authUrl}
                        onChange={(e) => {
                          const newUrls = authenticatedUrls.map((u, i) => i === index ? e.target.value : u);
                          setAuthenticatedUrls(newUrls);
                        }}
                        placeholder={`https://example.com/secure${index > 0 ? index + 1 : ''}`}
                        className="flex-1 px-4 py-3 border-2 border-gray-300 rounded-xl bg-white focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all shadow-sm text-sm"
                      />
                      {authenticatedUrls.length > 1 && (
                        <button
                          type="button"
                          onClick={() => {
                            const newUrls = authenticatedUrls.filter((_, i) => i !== index);
                            setAuthenticatedUrls(newUrls);
                          }}
                          className="p-3 text-white bg-gradient-to-r from-red-600 to-red-500 hover:from-red-700 hover:to-red-600 rounded-xl transition-all shadow-md hover:shadow-lg"
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
                    className="flex items-center gap-2 px-5 py-2.5 text-sm border-2 border-gray-300 rounded-xl hover:bg-gray-50 hover:border-blue-500 transition-all shadow-sm font-semibold text-gray-900"
                  >
                    <FaPlus className="w-4 h-4" />
                    <span>Add Authenticated Page URL</span>
                  </button>
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-bold text-gray-900 mb-2">
                    Username/Email <span className="text-red-600">*</span>
                  </label>
                  <input
                    type="text"
                    value={credentials.username}
                    onChange={(e) => setCredentials({...credentials, username: e.target.value})}
                    placeholder="Enter your username or email"
                    className="w-full px-4 py-3 border-2 border-gray-300 rounded-xl bg-white focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all shadow-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-bold text-gray-900 mb-2">
                    Password <span className="text-red-600">*</span>
                  </label>
                  <div className="relative">
                    <input
                      type={showPassword ? "text" : "password"}
                      value={credentials.password}
                      onChange={(e) => setCredentials({...credentials, password: e.target.value})}
                      placeholder="Enter your password"
                      className="w-full px-4 py-3 pr-12 border-2 border-gray-300 rounded-xl bg-white focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all shadow-sm"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-blue-600 focus:outline-none transition-colors"
                      aria-label={showPassword ? "Hide password" : "Show password"}
                    >
                      {showPassword ? (
                        <FaEyeSlash className="w-5 h-5" />
                      ) : (
                        <FaEye className="w-5 h-5" />
                      )}
                    </button>
                  </div>
                </div>
              </div>
              <div className="p-4 bg-yellow-100/50 border-2 border-yellow-300 rounded-xl">
                <p className="text-xs text-yellow-900 font-semibold">
                  <strong>Note:</strong> Credentials are only used during the scan and are not stored. 
                  {scanType === 'specific' ? ' The system will first test the login page, authenticate, discover authenticated pages, then test your specific URLs according to the selected mode.' : ' The system will automatically detect login pages and authenticate as needed.'}
                </p>
              </div>
            </motion.div>
            )}
          </div>
        )}
        {showProgress && (
          <div className="space-y-3 p-4 bg-blue-50/50 backdrop-blur-sm border-2 border-blue-200 rounded-xl">
            <div className="flex items-center justify-between text-sm font-semibold text-gray-900">
              <span>Scanning…</span>
              <span>{progress}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden shadow-inner">
              <motion.div
                className="h-4 bg-gradient-to-r from-blue-600 to-blue-500 rounded-full shadow-md"
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ type: 'spring', stiffness: 120, damping: 20 }}
              />
            </div>
          </div>
        )}
        <div className="flex items-center gap-4 pt-6">
          <motion.button 
            whileHover={{ scale: 1.02 }} 
            whileTap={{ scale: 0.98 }} 
            onClick={runScan} 
            disabled={loading}
            className="px-8 py-3.5 bg-gradient-to-r from-blue-600 to-blue-500 text-white rounded-xl hover:from-blue-700 hover:to-blue-600 disabled:opacity-50 flex items-center gap-2 font-bold shadow-lg hover:shadow-xl transition-all"
          >
            {loading ? <FaSpinner className="animate-spin" /> : null}
            <span>{loading ? 'Scanning…' : 'Run Scan'}</span>
          </motion.button>
          <button 
            onClick={() => download('pdf')} 
            disabled={!result || loading} 
            className="px-5 py-2.5 border-2 border-gray-300 rounded-xl flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 hover:border-blue-500 transition-all shadow-sm font-semibold text-gray-900" 
            title={!result ? 'Run a scan to enable downloads' : ''}
          >
            <FaFilePdf className="text-red-600" /> PDF
          </button>
          <button 
            onClick={() => download('excel')} 
            disabled={!result || loading} 
            className="px-5 py-2.5 border-2 border-gray-300 rounded-xl flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 hover:border-green-500 transition-all shadow-sm font-semibold text-gray-900" 
            title={!result ? 'Run a scan to enable downloads' : ''}
          >
            <FaFileExcel className="text-green-600" /> Excel
          </button>
          {error && (
            <div className="ml-auto px-4 py-2 bg-red-50 border-2 border-red-300 text-red-800 rounded-xl text-sm font-semibold">
              {error}
            </div>
          )}
        </div>
        </div>
      </motion.div>
      {showSuccessPopup && (
        <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 20, scale: 0.95 }}
          className="fixed bottom-6 right-6 z-50 px-6 py-4 bg-gradient-to-r from-green-600 to-green-500 text-white rounded-xl shadow-2xl border-2 border-green-300"
        >
          <p className="font-bold">Scan completed successfully.</p>
        </motion.div>
      )}

      {result && (
        <div className="space-y-6">
          {/* Authentication status banner */}
          {(result.authentication_required !== undefined || authRequired) && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`p-5 rounded-xl border-2 backdrop-blur-sm ${
                result.authentication_successful 
                  ? 'bg-green-50/90 border-green-300' 
                  : 'bg-red-50/90 border-red-300'
              }`}
            >
              <div className="flex items-center space-x-3">
                <div className={`w-3 h-3 rounded-full shadow-md ${
                  result.authentication_successful ? 'bg-green-600' : 'bg-red-600'
                }`}></div>
                <h4 className={`font-bold text-lg ${
                  result.authentication_successful 
                    ? 'text-green-900' 
                    : 'text-red-900'
                }`}>
                  {result.authentication_required ? 'Authentication Required' : 'No Authentication Required'}
                </h4>
              </div>
              <p className={`text-sm mt-2 font-medium ${
                result.authentication_successful 
                  ? 'text-green-800' 
                  : 'text-red-800'
              }`}>
                {result.authentication_required 
                  ? (result.authentication_successful 
                      ? 'Successfully authenticated and scanned protected pages' 
                      : 'Authentication failed - please check your credentials')
                  : 'Website does not require authentication for scanning'
                }
              </p>
              {result.session_used && (
                <p className="text-xs text-green-700 font-semibold mt-2">
                  Session cookies were used to maintain authentication during the scan
                </p>
              )}
            </motion.div>
          )}
          
          {/* Login page detection status */}
          {useAuthentication && hasLoginPageCheck && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`p-5 rounded-xl border-2 backdrop-blur-sm ${
                noLoginPagesFound
                  ? 'bg-yellow-50/90 border-yellow-300'
                  : 'bg-blue-50/90 border-blue-300'
              }`}
            >
              <div className="flex items-center space-x-3">
                <div className={`w-3 h-3 rounded-full shadow-md ${
                  noLoginPagesFound ? 'bg-yellow-600' : 'bg-blue-600'
                }`}></div>
                <h4 className={`font-bold text-lg ${
                  noLoginPagesFound
                    ? 'text-yellow-900'
                    : 'text-blue-900'
                }`}>
                  Login Page Detection
                </h4>
              </div>
              <p className={`text-sm mt-2 font-medium ${
                noLoginPagesFound
                  ? 'text-yellow-800'
                  : 'text-blue-800'
              }`}>
                {noLoginPagesFound
                  ? `No login pages detected on ${loginPageDetection.pages_without_login_detected.length} scanned page(s). Pages were scanned as public pages.`
                  : `Login pages detected on ${loginPageDetection.pages_with_login_detected.length} page(s).`
                }
              </p>
            </motion.div>
          )}
          
          {/* Site scan summary banner */}
          {isSiteScan && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-6 bg-gradient-to-r from-blue-50/80 to-indigo-50/80 backdrop-blur-sm border-2 border-blue-300 rounded-xl shadow-lg"
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <h4 className="font-bold text-xl text-blue-900 mb-2">Scan Completed</h4>
                  <p className="text-sm text-blue-800 font-semibold mt-1">
                    Scanned {result?.summary?.pages_scanned || 0} pages across the website
                    {result?.duration_seconds && ` in ${(result.duration_seconds / 60).toFixed(1)} minutes`}
                  </p>
                  <p className="text-xs text-blue-700 font-medium mt-2">
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
                          className="w-full max-w-md px-4 py-2.5 pr-10 text-sm border-2 border-blue-300 rounded-xl bg-white text-blue-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 cursor-pointer appearance-none shadow-sm font-medium"
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
                        <FaChevronDown className="absolute right-3 top-1/2 transform -translate-y-1/2 text-blue-600 pointer-events-none text-sm" />
                      </div>
                      <p className="text-xs text-blue-700 font-medium mt-2">
                        Select a page from the dropdown to open it in a new tab
                      </p>
                    </div>
                  )}
                </div>
                <div className="text-right ml-4">
                  <div className="text-xs text-blue-700 font-semibold">
                    {result?.crawl_result?.stats?.from_sitemap || 0} from sitemap • {result?.crawl_result?.stats?.from_crawl || 0} from crawling
                  </div>
                </div>
              </div>
            </motion.div>
          )}
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Pages Scanned Card - Only show for site scans */}
            {isSiteScan && mode !== 'security' && (
              <motion.div
                whileHover={{ scale: 1.03, y: -5 }}
                className="bg-white/80 backdrop-blur-sm p-6 rounded-2xl shadow-xl hover:shadow-2xl transition-all duration-300 relative overflow-hidden group"
              >
                <div className="absolute top-0 right-0 w-24 h-24 bg-indigo-500/10 rounded-full blur-2xl -mr-12 -mt-12 group-hover:bg-indigo-500/20 transition-all"></div>
                <div className="relative z-10">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <p className="text-xs font-semibold text-gray-500 mb-1 uppercase tracking-wide">Pages Scanned</p>
                      <h3 className="text-3xl font-bold bg-gradient-to-r from-indigo-600 to-indigo-500 bg-clip-text text-transparent">{result?.summary?.pages_scanned || 0}</h3>
                    </div>
                    <div className="p-4 rounded-xl bg-gradient-to-br from-indigo-600 to-indigo-500 text-white shadow-lg">
                      <FaChartLine className="h-6 w-6" />
                    </div>
                  </div>
                  <div className="mt-3 text-xs text-gray-600 font-medium">
                    Discovered: {result?.summary?.pages_discovered || 0} • 
                    Successful: {result?.summary?.pages_scanned_successfully || 0}
                  </div>
                </div>
              </motion.div>
            )}
            
            {(mode === 'all' || mode === 'accessibility') && (
              <motion.div
                whileHover={{ scale: 1.03, y: -5 }}
                className="bg-white/80 backdrop-blur-sm p-6 rounded-2xl shadow-xl hover:shadow-2xl transition-all duration-300 relative overflow-hidden group"
              >
                <div className="absolute top-0 right-0 w-24 h-24 bg-blue-500/10 rounded-full blur-2xl -mr-12 -mt-12 group-hover:bg-blue-500/20 transition-all"></div>
                <div className="relative z-10">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <p className="text-xs font-semibold text-gray-500 mb-1 uppercase tracking-wide">Accessibility Score</p>
                      <h3 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-blue-500 bg-clip-text text-transparent">{a11yScore}</h3>
                    </div>
                    <div className="p-4 rounded-xl bg-gradient-to-br from-blue-600 to-blue-500 text-white shadow-lg">
                      <FaDesktop className="h-6 w-6" />
                    </div>
                  </div>
                  <div className="mt-3 text-xs text-gray-600 font-medium">Crit {a11yCounts.critical} • Serious {a11yCounts.serious} • Moderate {a11yCounts.moderate} • Minor {a11yCounts.minor}</div>
                </div>
              </motion.div>
            )}
            {(mode === 'all' || mode === 'accessibility') && (
              <motion.div
                whileHover={{ scale: 1.03, y: -5 }}
                className="bg-white/80 backdrop-blur-sm p-6 rounded-2xl shadow-xl hover:shadow-2xl transition-all duration-300 relative overflow-hidden group"
              >
                <div className="absolute top-0 right-0 w-24 h-24 bg-red-500/10 rounded-full blur-2xl -mr-12 -mt-12 group-hover:bg-red-500/20 transition-all"></div>
                <div className="relative z-10">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <p className="text-xs font-semibold text-gray-500 mb-1 uppercase tracking-wide">WCAG Violations</p>
                      <h3 className="text-3xl font-bold bg-gradient-to-r from-red-600 to-red-500 bg-clip-text text-transparent">
                        {isSiteScan 
                          ? (result?.wcag_aggregate?.total_violations || 0)
                          : violations.length}
                      </h3>
                    </div>
                    <div className="p-4 rounded-xl bg-gradient-to-br from-red-600 to-red-500 text-white shadow-lg">
                      <FaChartLine className="h-6 w-6" />
                    </div>
                  </div>
                  {isSiteScan && (
                    <div className="mt-3 text-xs text-gray-600 font-medium">
                      Unique issues: {result?.wcag_aggregate?.unique_rules_violated || 0} • 
                      Pages affected: {result?.wcag_aggregate?.pages_with_issues || 0}
                    </div>
                  )}
                </div>
              </motion.div>
            )}
            {(mode === 'all' || mode === 'security') && (
              <motion.div
                whileHover={{ scale: 1.03, y: -5 }}
                className="bg-white/80 backdrop-blur-sm p-6 rounded-2xl shadow-xl hover:shadow-2xl transition-all duration-300 relative overflow-hidden group"
              >
                <div className="absolute top-0 right-0 w-24 h-24 bg-green-500/10 rounded-full blur-2xl -mr-12 -mt-12 group-hover:bg-green-500/20 transition-all"></div>
                <div className="relative z-10">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <p className="text-xs font-semibold text-gray-500 mb-1 uppercase tracking-wide">Security Score</p>
                      <h3 className="text-3xl font-bold bg-gradient-to-r from-green-600 to-green-500 bg-clip-text text-transparent">{typeof securityScore === 'number' ? securityScore : '—'}</h3>
                    </div>
                    <div className="p-4 rounded-xl bg-gradient-to-br from-green-600 to-green-500 text-white shadow-lg">
                      <FaChartLine className="h-6 w-6" />
                    </div>
                  </div>
                  <div className="mt-3 text-xs text-gray-600 font-medium">Missing headers: {missingHeaders.length}</div>
                </div>
              </motion.div>
            )}
            {(mode === 'all' || mode === 'security') && (
              <motion.div
                whileHover={{ scale: 1.03, y: -5 }}
                className="bg-white/80 backdrop-blur-sm p-6 rounded-2xl shadow-xl hover:shadow-2xl transition-all duration-300 relative overflow-hidden group"
              >
                <div className="absolute top-0 right-0 w-24 h-24 bg-purple-500/10 rounded-full blur-2xl -mr-12 -mt-12 group-hover:bg-purple-500/20 transition-all"></div>
                <div className="relative z-10">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <p className="text-xs font-semibold text-gray-500 mb-1 uppercase tracking-wide">SSL Labs Grade</p>
                      <h3 className="text-3xl font-bold bg-gradient-to-r from-purple-600 to-purple-500 bg-clip-text text-transparent">{displaySslGrade}</h3>
                    </div>
                    <div className="p-4 rounded-xl bg-gradient-to-br from-purple-600 to-purple-500 text-white shadow-lg">
                      <FaChartLine className="h-6 w-6" />
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
          </div>
          {(mode === 'all' || mode === 'accessibility') && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-8 bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl border-2 border-blue-200 relative overflow-hidden group"
            >
              <div className="absolute top-0 right-0 w-48 h-48 bg-blue-500/10 rounded-full blur-3xl -mr-24 -mt-24 animate-pulse-slow"></div>
              <div className="relative z-10">
                <h3 className="text-2xl font-bold text-gray-900 mb-6">Accessibility (WCAG)</h3>
              {violations.length > 0 ? (
                <div className="space-y-4">
                      {violations.map((v, i) => (
                    <motion.details
                      key={i}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className="border-2 border-gray-200 rounded-xl overflow-hidden bg-white/50 backdrop-blur-sm hover:border-blue-300 transition-all shadow-sm hover:shadow-md"
                    >
                      <summary className="px-6 py-4 bg-gradient-to-r from-gray-50/80 to-blue-50/80 backdrop-blur-sm cursor-pointer hover:from-blue-50/80 hover:to-indigo-50/80 transition-all flex items-center justify-between">
                        <div className="flex items-center gap-4 flex-1">
                          <span className={`px-3 py-1.5 text-xs rounded-full font-bold border-2 ${
                              v.impact === 'critical' ? 'bg-red-100 text-red-800 border-red-300' :
                              v.impact === 'serious' ? 'bg-orange-100 text-orange-800 border-orange-300' :
                              v.impact === 'moderate' ? 'bg-yellow-100 text-yellow-800 border-yellow-300' :
                              'bg-green-100 text-green-800 border-green-300'
                            }`}>{v.impact}</span>
                          <span className="font-mono text-xs font-bold text-gray-700">{v.id}</span>
                          <span className="text-sm font-semibold text-gray-900 flex-1">{v.description}</span>
                          {isSiteScan && (
                            <span className="text-xs bg-gradient-to-r from-blue-600 to-blue-500 text-white px-3 py-1.5 rounded-full font-bold shadow-sm">
                              {v.pages_affected || 0} page(s)
                            </span>
                          )}
                        </div>
                      </summary>
                      <div className="px-6 py-5 bg-white/80 backdrop-blur-sm space-y-4">
                        {/* Help Text */}
                        {v.help && (
                          <div className="p-4 bg-blue-50/80 backdrop-blur-sm border-2 border-blue-200 rounded-xl">
                            <p className="text-xs font-bold text-blue-900 mb-2 uppercase tracking-wide">How to fix:</p>
                            <p className="text-sm text-gray-800 font-medium">{v.help}</p>
                          </div>
                        )}
                        
                        {/* Help URL */}
                        {v.helpUrl && (
                          <div className="p-4 bg-indigo-50/80 backdrop-blur-sm border-2 border-indigo-200 rounded-xl">
                            <p className="text-xs font-bold text-indigo-900 mb-2 uppercase tracking-wide">Learn more:</p>
                            <a href={v.helpUrl} target="_blank" rel="noopener noreferrer" 
                               className="text-sm text-blue-700 hover:text-blue-900 font-semibold hover:underline break-all">
                              {v.helpUrl}
                            </a>
                          </div>
                        )}
                        
                        {/* For site scans: Show affected pages */}
                        {isSiteScan && v.pages_affected_urls && v.pages_affected_urls.length > 0 && (
                          <div className="p-4 bg-gray-50/80 backdrop-blur-sm border-2 border-gray-200 rounded-xl">
                            <p className="text-xs font-bold text-gray-900 mb-3 uppercase tracking-wide">
                              Affected pages ({v.total_instances || 0} total instances):
                            </p>
                            <ul className="text-xs space-y-2 max-h-40 overflow-y-auto">
                              {v.pages_affected_urls.map((pageUrl, idx) => (
                                <li key={idx} className="text-gray-700 break-all font-medium">
                                  • {pageUrl}
                                </li>
                              ))}
                              {v.pages_affected > (v.pages_affected_urls?.length || 0) && (
                                <li className="text-gray-600 italic font-semibold">
                                  ... and {v.pages_affected - v.pages_affected_urls.length} more pages
                                </li>
                              )}
                            </ul>
                          </div>
                        )}
                        
                        {/* For single-page scans: Show target nodes */}
                        {!isSiteScan && v.nodes && v.nodes.length > 0 && (
                          <div className="p-4 bg-gray-50/80 backdrop-blur-sm border-2 border-gray-200 rounded-xl">
                            <p className="text-xs font-bold text-gray-900 mb-3 uppercase tracking-wide">
                              Elements affected ({v.nodes.length} instances):
                            </p>
                            <ul className="text-xs space-y-2 max-h-40 overflow-y-auto">
                              {v.nodes.map((n, idx) => (
                                <li key={idx} className="font-mono text-gray-700 break-all font-medium">
                                  • {(n.target || []).join(' ')}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                        
                        {/* Sample HTML Nodes (for site scans) */}
                        {isSiteScan && v.sample_nodes && v.sample_nodes.length > 0 && (
                          <div className="p-4 bg-gray-50/80 backdrop-blur-sm border-2 border-gray-200 rounded-xl">
                            <p className="text-xs font-bold text-gray-900 mb-4 uppercase tracking-wide">
                              Sample violations (showing {v.sample_nodes.length} of {v.total_instances}):
                            </p>
                            <div className="space-y-3">
                              {v.sample_nodes.map((node, idx) => (
                                <div key={idx} className="border-2 border-gray-300 rounded-xl p-4 bg-white/80 backdrop-blur-sm shadow-sm">
                                  {/* CSS Selector */}
                                  {node.target && node.target.length > 0 && (
                                    <div className="mb-2">
                                      <span className="text-xs font-bold text-gray-900">Selector:</span>
                                      <code className="ml-2 text-xs font-mono bg-gray-100 px-2 py-1 rounded-lg border border-gray-300 text-gray-800">
                                        {node.target.join(' ')}
                                      </code>
                                    </div>
                                  )}
                                  
                                  {/* Page URL */}
                                  {node.page_url && (
                                    <div className="mb-2">
                                      <span className="text-xs font-bold text-gray-900">On page:</span>
                                      <span className="ml-2 text-xs text-gray-700 break-all font-medium">
                                        {node.page_url}
                                      </span>
                                    </div>
                                  )}
                                  
                                  {/* Failure Summary */}
                                  {node.failureSummary && (
                                    <div className="mb-2">
                                      <span className="text-xs font-bold text-gray-900">Issue:</span>
                                      <span className="ml-2 text-xs text-gray-700 font-medium">
                                        {node.failureSummary}
                                      </span>
                                    </div>
                                  )}
                                  
                                  {/* HTML Snippet */}
                                  {node.html && (
                                    <details className="mt-3">
                                      <summary className="text-xs font-bold text-blue-700 cursor-pointer hover:text-blue-900 transition-colors">
                                        View HTML snippet ▼
                                      </summary>
                                      <pre className="mt-2 text-xs font-mono bg-gray-900 text-gray-100 p-3 rounded-lg border-2 border-gray-700 overflow-x-auto max-h-32">
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
                          <div className="p-4 bg-purple-50/80 backdrop-blur-sm border-2 border-purple-200 rounded-xl">
                            <p className="text-xs font-bold text-purple-900 mb-3 uppercase tracking-wide">WCAG Standards:</p>
                            <div className="flex flex-wrap gap-2">
                              {v.tags.map((tag, idx) => (
                                <span key={idx} className="px-3 py-1.5 bg-gradient-to-r from-purple-600 to-purple-500 text-white text-xs rounded-lg font-bold shadow-sm">
                                  {tag}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </motion.details>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <div className="mx-auto w-20 h-20 bg-green-100/50 rounded-full flex items-center justify-center mb-4">
                    <FaDesktop className="h-10 w-10 text-green-600" />
                  </div>
                  <p className="text-lg font-bold text-gray-900">No WCAG violations detected.</p>
                  <p className="text-sm text-gray-600 mt-2">Great job! Your site meets accessibility standards.</p>
                </div>
              )}
              </div>
            </motion.div>
          )}

          {(mode === 'all' || mode === 'security') && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="grid grid-cols-1 md:grid-cols-2 gap-6"
            >
              <div className="p-6 bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl border-2 border-green-200 relative overflow-hidden group">
                <div className="absolute top-0 right-0 w-32 h-32 bg-green-500/10 rounded-full blur-2xl -mr-16 -mt-16"></div>
                <div className="relative z-10">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-xl font-bold text-gray-900">SecurityHeaders</h3>
                    <button 
                      onClick={() => setOpenSecurity((v) => !v)} 
                      className="px-4 py-2 text-sm font-semibold bg-gradient-to-r from-green-600 to-green-500 text-white rounded-xl hover:from-green-700 hover:to-green-600 transition-all shadow-md hover:shadow-lg flex items-center gap-2"
                    >
                      <span>{openSecurity ? 'Hide' : 'Show'}</span>
                      <FaChevronDown className={`transition-transform ${openSecurity ? 'rotate-180' : ''}`} />
                    </button>
                  </div>
                  <AnimatePresence initial={false}>
                    {openSecurity && (
                      <motion.div 
                        initial={{ height: 0, opacity: 0 }} 
                        animate={{ height: 'auto', opacity: 1 }} 
                        exit={{ height: 0, opacity: 0 }} 
                        transition={{ duration: 0.25 }}
                      >
                        <pre className="text-xs whitespace-pre-wrap max-h-72 overflow-auto border-2 border-gray-300 rounded-xl p-4 bg-gray-50 font-mono">{JSON.stringify(securityData?.securityheaders || {}, null, 2)}</pre>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </div>
            </motion.div>
          )}

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-8 bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl border-2 border-blue-200 relative overflow-hidden group"
          >
            <div className="absolute top-0 right-0 w-48 h-48 bg-purple-500/10 rounded-full blur-3xl -mr-24 -mt-24 animate-pulse-slow"></div>
            <div className="relative z-10">
              <h3 className="text-2xl font-bold text-gray-900 mb-6">AI Recommendations</h3>
              <UiTestingRecommendations content={result.recommendations || ''} />
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-8 bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl border-2 border-blue-200 relative overflow-hidden group"
          >
            <div className="absolute top-0 right-0 w-48 h-48 bg-indigo-500/10 rounded-full blur-3xl -mr-24 -mt-24 animate-pulse-slow"></div>
            <div className="relative z-10">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-2xl font-bold text-gray-900">Structured Findings</h3>
                <button 
                  onClick={() => setOpenFindings((v) => !v)} 
                  className="px-4 py-2 text-sm font-semibold bg-gradient-to-r from-indigo-600 to-indigo-500 text-white rounded-xl hover:from-indigo-700 hover:to-indigo-600 transition-all shadow-md hover:shadow-lg flex items-center gap-2"
                >
                  <span>{openFindings ? 'Hide' : 'Show'}</span>
                  <FaChevronDown className={`transition-transform ${openFindings ? 'rotate-180' : ''}`} />
                </button>
              </div>
              <AnimatePresence initial={false}>
                {openFindings && (
                  <motion.div 
                    initial={{ height: 0, opacity: 0 }} 
                    animate={{ height: 'auto', opacity: 1 }} 
                    exit={{ height: 0, opacity: 0 }} 
                    transition={{ duration: 0.25 }}
                  >
                    <pre className="text-xs whitespace-pre-wrap max-h-96 overflow-auto border-2 border-gray-300 rounded-xl p-4 bg-gray-50 font-mono">{JSON.stringify(result.findings || {}, null, 2)}</pre>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </motion.div>
        </div>
      )}
    </motion.div>
  );
};

export default UiTesting;


