import React, { useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { FaDesktop, FaFilePdf, FaFileExcel, FaSpinner } from 'react-icons/fa';
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

  const apiBase = 'http://localhost:8000/api';

  const runScan = async () => {
    if (!url) {
      setError('Please enter a URL');
      return;
    }
    setError(null);
    setLoading(true);
    setResult(null);
    setProgress(0);
    setShowProgress(true);
    // Increment progress smoothly up to 90% while waiting
    if (progressTimerRef.current) clearInterval(progressTimerRef.current);
    progressTimerRef.current = setInterval(() => {
      setProgress((p) => (p < 90 ? Math.min(90, p + Math.floor(5 + Math.random() * 7)) : p));
    }, 500);
    try {
      const resp = await fetch(`${apiBase}/ui/scan`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`,
        },
        body: JSON.stringify({ url, mode }),
      });
      if (!resp.ok) {
        const t = await resp.text();
        throw new Error(t || 'Scan failed');
      }
      const data = await resp.json();
      setResult(data);
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
      }, 800);
    }
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

      {result && (
        <div className="space-y-6">
          {(mode === 'all' || mode === 'accessibility') && (
            <div className="p-6 bg-card rounded-xl shadow-lg border border-border">
              <h3 className="text-lg font-semibold mb-4">Accessibility (WCAG)</h3>
              {violations.length > 0 ? (
                <div className="overflow-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left border-b">
                        <th className="py-2 pr-4">Rule</th>
                        <th className="py-2 pr-4">Impact</th>
                        <th className="py-2 pr-4">Description</th>
                        <th className="py-2">Targets</th>
                      </tr>
                    </thead>
                    <tbody>
                      {violations.map((v, i) => (
                        <tr key={i} className="border-b last:border-0">
                          <td className="py-2 pr-4">{v.id}</td>
                          <td className="py-2 pr-4 capitalize">{v.impact}</td>
                          <td className="py-2 pr-4">{v.description}</td>
                          <td className="py-2 text-xs text-muted-foreground">{(v.nodes || []).map(n => (n.target || []).join(' ')).join(', ')}</td>
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
                <h3 className="text-lg font-semibold mb-4">SecurityHeaders</h3>
                <pre className="text-xs whitespace-pre-wrap">{JSON.stringify(result.security_results?.securityheaders || {}, null, 2)}</pre>
              </div>
              <div className="p-6 bg-card rounded-xl shadow-lg border border-border">
                <h3 className="text-lg font-semibold mb-4">SSL Labs</h3>
                <pre className="text-xs whitespace-pre-wrap">{JSON.stringify(result.security_results?.ssllabs || {}, null, 2)}</pre>
              </div>
            </div>
          )}

          <div className="p-6 bg-card rounded-xl shadow-lg border border-border">
            <h3 className="text-lg font-semibold mb-4">AI Recommendations</h3>
            <div className="prose prose-sm max-w-none dark:prose-invert">
              <div dangerouslySetInnerHTML={{ __html: (result.recommendations || '').replace(/\n/g, '<br/>') }} />
            </div>
          </div>

          <div className="p-6 bg-card rounded-xl shadow-lg border border-border">
            <h3 className="text-lg font-semibold mb-4">Structured Findings</h3>
            <pre className="text-xs whitespace-pre-wrap">{JSON.stringify(result.findings || {}, null, 2)}</pre>
          </div>
        </div>
      )}
    </motion.div>
  );
};

export default UiTesting;


