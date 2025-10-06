import React, { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import FormattedResponse from '@/components/ui/FormattedResponse';
import { FaDesktop, FaFilePdf, FaFileExcel, FaSpinner, FaChevronDown, FaChartLine } from 'react-icons/fa';
import { useAuth } from '../../context/AuthContext';

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
  const [openSSL, setOpenSSL] = useState(false);
  const [openFindings, setOpenFindings] = useState(false);
  const [showSuccessPopup, setShowSuccessPopup] = useState(false);

  const apiBase = 'http://localhost:8000/api';

  const runScan = async () => {
    const normalized = normalizeUrl(url);
    if (!normalized) {
      setError('Please enter a valid URL (e.g., https://example.com)');
      return;
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
      const resp = await fetch(`${apiBase}/ui/scan`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`,
        },
        body: JSON.stringify({ url: normalized, mode, force: true }),
      });
      if (!resp.ok) {
        const t = await resp.text();
        throw new Error(t || 'Scan failed');
      }
      const data = await resp.json();
      setResult(data);
      setShowSuccessPopup(true);
      setTimeout(() => setShowSuccessPopup(false), 2500);
      try {
        localStorage.setItem('uiTesting:lastResult', JSON.stringify({ url: normalized, mode, result: data, ts: Date.now() }));
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

  const getA11ySeverityCounts = () => {
    const counts = { critical: 0, serious: 0, moderate: 0, minor: 0, unknown: 0 };
    (violations || []).forEach((v) => {
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
    const sh = result?.security_results?.securityheaders || {};
    const ssl = result?.security_results?.ssllabs || {};
    const live = result?.security_results?.live_headers || {};
    const endpoints = Array.isArray(ssl?.endpoints) ? ssl.endpoints : [];
    const sslGrade = (endpoints[0]?.grade || ssl?.grade || '') || '';
    const missingHeaders = Array.isArray(sh?.missing) ? sh.missing : [];
    const presentHeaders = Array.isArray(sh?.present) ? sh.present : [];
    let securityScore = typeof sh?.score === 'number' ? sh.score : undefined;
    if (securityScore === undefined) {
      const missing = missingHeaders.length;
      securityScore = Math.max(0, 100 - missing * 15);
    }
    return { securityScore, sslGrade, missingHeaders, presentHeaders, live };
  };

  const download = async (type) => {
    try {
      const endpoint = type === 'pdf' ? 'pdf' : 'excel';
      const resp = await fetch(`${apiBase}/ui/export/${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`,
        },
        body: JSON.stringify({ url, mode }),
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

  const violations = result?.wcag_results?.violations || [];
  const a11yCounts = (result ? getA11ySeverityCounts() : { critical: 0, serious: 0, moderate: 0, minor: 0, unknown: 0 });
  const a11yScore = result ? (violations.length > 0 ? computeAccessibilityScore() : 100) : 0;
  const { securityScore, sslGrade, missingHeaders } = result ? getSecuritySummaries() : { securityScore: undefined, sslGrade: '', missingHeaders: [] };

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }} className="space-y-6">
      <div className="flex items-center space-x-4">
        <FaDesktop className="text-2xl text-primary" />
        <div>
          <h2 className="text-2xl font-bold text-foreground">UI Testing</h2>
          <p className="text-muted-foreground">WCAG + Security headers + SSL Labs + AI recommendations</p>
        </div>
      </div>

      <div className="p-6 bg-card rounded-xl shadow-lg border border-border space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com"
            className="md:col-span-3 w-full px-4 py-3 border border-border rounded-lg bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary"
            aria-invalid={!!error}
          />
          <select value={mode} onChange={(e) => setMode(e.target.value)} className="w-full px-4 py-3 border border-border rounded-lg bg-background">
            <option value="all">All</option>
            <option value="accessibility">Accessibility</option>
            <option value="security">Security</option>
          </select>
        </div>
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
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
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
                    <h3 className="text-2xl font-bold">{violations.length}</h3>
                  </div>
                  <div className="p-3 rounded-full bg-red-500/10 text-red-500">
                    <FaChartLine className="h-6 w-6" />
                  </div>
                </div>
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
                    <h3 className="text-2xl font-bold">{sslGrade || '—'}</h3>
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
                <div className="w-full max-h-96 overflow-auto rounded border border-border/60">
                  <table className="min-w-full text-sm">
                    <thead className="bg-secondary sticky top-0 z-10">
                      <tr className="text-left border-b">
                        <th className="py-2 px-3">Rule</th>
                        <th className="py-2 px-3">Impact</th>
                        <th className="py-2 px-3">Description</th>
                        <th className="py-2 px-3">Targets</th>
                      </tr>
                    </thead>
                    <tbody>
                      {violations.map((v, i) => (
                        <tr key={i} className="border-b last:border-0 align-top">
                          <td className="py-2 px-3 font-mono text-xs whitespace-nowrap">{v.id}</td>
                          <td className="py-2 px-3 capitalize">
                            <span className={`px-2 py-1 text-xs rounded-full ${
                              v.impact === 'critical' ? 'bg-red-100 text-red-800' :
                              v.impact === 'serious' ? 'bg-orange-100 text-orange-800' :
                              v.impact === 'moderate' ? 'bg-yellow-100 text-yellow-800' :
                              'bg-green-100 text-green-800'
                            }`}>{v.impact}</span>
                          </td>
                          <td className="py-2 px-3">{v.description}</td>
                          <td className="py-2 px-3 text-xs text-muted-foreground break-words whitespace-pre-wrap max-w-[520px]">
                            {(v.nodes || []).map((n, idx) => (
                              <div key={idx} className="mb-1 last:mb-0">
                                {(n.target || []).join(' ')}
                              </div>
                            ))}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
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
                      <pre className="text-xs whitespace-pre-wrap max-h-72 overflow-auto border rounded p-3 bg-background">{JSON.stringify(result.security_results?.securityheaders || {}, null, 2)}</pre>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
              <div className="p-6 bg-card rounded-xl shadow-lg border border-border">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-lg font-semibold">SSL Labs</h3>
                  <button onClick={() => setOpenSSL((v) => !v)} className="text-sm flex items-center gap-1">
                    <span>{openSSL ? 'Hide' : 'Show'}</span>
                    <FaChevronDown className={`transition-transform ${openSSL ? 'rotate-180' : ''}`} />
                  </button>
                </div>
                <AnimatePresence initial={false}>
                  {openSSL && (
                    <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.25 }}>
                      <pre className="text-xs whitespace-pre-wrap max-h-72 overflow-auto border rounded p-3 bg-background">{JSON.stringify(result.security_results?.ssllabs || {}, null, 2)}</pre>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>
          )}

          <div className="p-6 bg-card rounded-xl shadow-lg border border-border">
            <h3 className="text-lg font-semibold mb-4">AI Recommendations</h3>
            <FormattedResponse content={result.recommendations || ''} />
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


