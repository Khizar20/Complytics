import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  FaCloud, 
  FaRobot, 
  FaDesktop, 
  FaCalendarAlt,
  FaChartLine,
  FaFileAlt,
  FaSignOutAlt,
  FaBars,
  FaTimes,
  FaUser,
  FaShieldAlt,
  FaCog,
  FaQuestionCircle,
  FaClock,
  FaChartBar,
  FaGlobe,
  FaCheckCircle,
  FaServer,
  FaExclamationTriangle,
  FaCheck,
  FaBell,
  FaHistory,
  FaTasks,
  FaInfo,
  FaEye,
  FaListAlt,
  FaEyeSlash,
  FaKey,
  FaBuilding,
  FaIdCard,
  FaSave,
  FaSpinner,
  FaLock,
  FaUsers,
  FaClipboardList,
  FaChevronLeft,
  FaChevronRight,
  FaSearch,
  FaBook,
  FaInbox
} from 'react-icons/fa';
import { FaFilePdf, FaFileWord, FaFileCsv, FaDownload } from 'react-icons/fa';
import Profile from '../auth/Profile';
import ComplianceChat from './ComplianceChat';
import UiTesting from './UiTesting';
import ScheduleScan from './ScheduleScan';
import AzureComplianceChecker from './AzureComplianceChecker';
import AzureComplianceLatestResult from './AzureComplianceLatestResult';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';
import autoTable from 'jspdf-autotable';
import { Document as DocxDocument, Packer, Paragraph, HeadingLevel, TextRun, ImageRun, Table, TableRow, TableCell, WidthType } from 'docx';
import { buildApiUrl } from '@/lib/api';

const ChatbotAnalytics = () => {
  const { authToken } = useAuth();
  const [analytics, setAnalytics] = useState({
    totalQueries: 0,
    averageResponseTime: 0,
    mostCommonTopics: [],
    successRate: 0
  });
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        if (!authToken) {
          throw new Error('No authentication token found');
        }

        const response = await fetch(buildApiUrl('/api/compliance/analytics'), {
          headers: {
            'Authorization': `Bearer ${authToken}`
          }
        });

        if (!response.ok) {
          throw new Error('Failed to fetch analytics');
        }

        const data = await response.json();
        setAnalytics(data);
        setError(null);
      } catch (error) {
        console.error('Error fetching chatbot analytics:', error);
        setError(error.message);
        // Set default values in case of error
        setAnalytics({
          totalQueries: 0,
          averageResponseTime: 0,
          mostCommonTopics: [],
          successRate: 0
        });
      }
    };

    fetchAnalytics();
  }, [authToken]);

  if (error) {
    return (
      <div className="p-4 bg-destructive/10 rounded-xl">
        <p className="text-destructive text-sm">Failed to load analytics: {error}</p>
      </div>
    );
  }

  const topicPairs = Array.isArray(analytics.topicCounts)
    ? analytics.topicCounts
    : (analytics.mostCommonTopics || []).slice(0, 5).map((t) => ({ name: t, count: 1 }));
  const hasTimeseries = Array.isArray(analytics.queriesOverTime);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <motion.div whileHover={{ scale: 1.02 }} className="p-3 bg-card rounded-xl shadow-lg">
          <div className="flex items-center space-x-3">
            <FaQuestionCircle className="text-2xl text-primary" />
            <div>
              <h4 className="text-sm font-medium text-muted-foreground">Total Queries</h4>
              <p className="text-2xl font-bold">{analytics.totalQueries}</p>
            </div>
          </div>
        </motion.div>

        <motion.div whileHover={{ scale: 1.02 }} className="p-3 bg-card rounded-xl shadow-lg">
          <div className="flex items-center space-x-3">
            <FaClock className="text-2xl text-primary" />
            <div>
              <h4 className="text-sm font-medium text-muted-foreground">Avg Response Time</h4>
              <p className="text-2xl font-bold">{analytics.averageResponseTime}s</p>
            </div>
          </div>
        </motion.div>

        <motion.div whileHover={{ scale: 1.02 }} className="p-3 bg-card rounded-xl shadow-lg">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-sm font-medium text-muted-foreground">Success Rate</h4>
              <p className="text-xs text-muted-foreground">Resolved queries</p>
            </div>
            <RadialSuccess value={analytics.successRate || 0} size={88} />
          </div>
        </motion.div>
      </div>
      {/* Removed Topic Distribution and Queries Over Time as requested */}
    </div>
  );
};

const SeverityBarChart = ({ counts }) => {
  const items = [
    { key: 'critical', label: 'Critical', value: counts.critical || 0, color: 'bg-red-500' },
    { key: 'serious', label: 'Serious', value: counts.serious || 0, color: 'bg-orange-500' },
    { key: 'moderate', label: 'Moderate', value: counts.moderate || 0, color: 'bg-yellow-500' },
    { key: 'minor', label: 'Minor', value: counts.minor || 0, color: 'bg-green-500' },
  ];
  const maxVal = Math.max(1, ...items.map(i => i.value));
  return (
    <div className="space-y-3">
      {items.map((i) => (
        <div key={i.key} className="space-y-1">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">{i.label}</span>
            <span className="font-medium">{i.value}</span>
          </div>
          <div className="h-3 w-full bg-secondary rounded">
            <div className={`h-3 rounded ${i.color}`} style={{ width: `${(i.value / maxVal) * 100}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
};

const HeadersDonutChart = ({ presentCount, missingCount }) => {
  const total = Math.max(0, (presentCount || 0) + (missingCount || 0));
  const radius = 30;
  const circumference = 2 * Math.PI * radius;
  const missingRatio = total > 0 ? missingCount / total : 0;
  const missingLength = missingRatio * circumference;
  const remainingLength = circumference - missingLength;
  return (
    <div className="flex items-center gap-4">
      <svg width="110" height="110" viewBox="0 0 110 110">
        <g transform="translate(55,55)">
          <circle r={radius} fill="none" stroke="var(--border)" strokeWidth="12" />
          <g transform="rotate(-90)">
            <circle r={radius} fill="none" stroke="rgb(239,68,68)" strokeWidth="12" strokeLinecap="round" strokeDasharray={`${missingLength} ${remainingLength}`} />
          </g>
          <text x="0" y="-2" textAnchor="middle" className="fill-foreground font-bold" style={{ fontSize: 16 }}>{total}</text>
          <text x="0" y="12" textAnchor="middle" className="fill-muted-foreground" style={{ fontSize: 10 }}>Headers</text>
        </g>
      </svg>
      <div className="space-y-1 text-sm">
        <div className="flex items-center gap-2"><span className="inline-block w-3 h-3 rounded-full bg-red-500" /> Missing: <span className="font-medium">{missingCount}</span></div>
        <div className="flex items-center gap-2"><span className="inline-block w-3 h-3 rounded-full bg-gray-300" /> Present: <span className="font-medium">{presentCount}</span></div>
      </div>
    </div>
  );
};

const RadialSuccess = ({ value = 0, size = 64 }) => {
  const clamped = Math.max(0, Math.min(100, value));
  const radius = Math.max(16, (size / 2) - 10);
  const strokeWidth = Math.max(6, Math.round(size / 12));
  const circumference = 2 * Math.PI * radius;
  const filled = (clamped / 100) * circumference;
  const remaining = circumference - filled;
  const color = clamped >= 80 ? 'rgb(34,197,94)' : clamped >= 50 ? 'rgb(234,179,8)' : 'rgb(239,68,68)';
  const view = `${size} ${size}`;
  const half = size / 2;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${view}`}>
      <g transform={`translate(${half},${half})`}>
        <circle r={radius} fill="none" stroke="var(--border)" strokeWidth={strokeWidth} />
        <g transform="rotate(-90)">
          <circle r={radius} fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeDasharray={`${filled} ${remaining}`} />
        </g>
        <text x="0" y="5" textAnchor="middle" className="fill-foreground font-bold" style={{ fontSize: Math.max(12, Math.round(size / 7)) }}>{clamped}%</text>
      </g>
    </svg>
  );
};

const Sparkline = ({ data = [] }) => {
  const width = 440;
  const height = 100;
  const padding = 8;
  const n = data.length;
  if (n === 0) {
    return <div className="text-sm text-muted-foreground">No data</div>;
  }
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = Math.max(1, max - min);
  const pts = data.map((v, i) => {
    const x = padding + (i * (width - padding * 2)) / Math.max(1, n - 1);
    const y = height - padding - ((v - min) / range) * (height - padding * 2);
    return `${x},${y}`;
  }).join(' ');
  return (
    <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`}>
      <polyline fill="none" stroke="rgb(59,130,246)" strokeWidth="2" points={pts} />
      {data.map((v, i) => {
        const x = padding + (i * (width - padding * 2)) / Math.max(1, n - 1);
        const y = height - padding - ((v - min) / range) * (height - padding * 2);
        return <circle key={i} cx={x} cy={y} r="2" fill="rgb(59,130,246)" />;
      })}
    </svg>
  );
};

const TopicsBars = ({ data = [] }) => {
  const items = data.slice(0, 6);
  const maxVal = Math.max(1, ...items.map(i => i.count || 0));
  return (
    <div className="space-y-3">
      {items.length === 0 ? (
        <div className="text-sm text-muted-foreground">No topics yet</div>
      ) : (
        items.map((t, idx) => (
          <div key={idx} className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground truncate max-w-[70%]">{t.name}</span>
              <span className="font-medium">{t.count || 1}</span>
            </div>
            <div className="h-3 w-full bg-secondary rounded">
              <div className="h-3 rounded bg-primary" style={{ width: `${((t.count || 1) / maxVal) * 100}%` }} />
            </div>
          </div>
        ))
      )}
    </div>
  );
};

const UiTestingSummaryCards = () => {
  const { authToken } = useAuth();
  const [result, setResult] = useState(null);
  const [meta, setMeta] = useState({ url: '', mode: 'all', ts: null });

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      // Try backend first for org-wide whole-site scan results
      try {
        const resp = await fetch(buildApiUrl('/api/ui/site/latest'), {
          headers: authToken ? { 'Authorization': `Bearer ${authToken}` } : {}
        });
        if (resp.ok) {
          const data = await resp.json();
          // Check if it's a valid scan result (not just a message)
          if (data?.result && !cancelled) {
            setResult(data.result);
            setMeta({ url: data.url || '', mode: data.mode || 'all', ts: data.created_at || null });
            return;
          } else if (data?.message && !cancelled) {
            // No site scans found, clear the result
            setResult(null);
            setMeta({ url: '', mode: 'all', ts: null });
            return;
          }
        }
      } catch (e) {
        console.error('Failed to fetch latest site scan:', e);
      }
      // Fallback to localStorage for backward compatibility
      try {
        const last = localStorage.getItem('uiTesting:lastResult');
        if (last && !cancelled) {
          const parsed = JSON.parse(last);
          setResult(parsed?.result || null);
          setMeta({ url: parsed?.url || '', mode: parsed?.mode || 'all', ts: parsed?.ts || null });
        }
      } catch (e) {}
    };
    load();
    const id = setInterval(load, 60000); // refresh every 60s to reflect scheduled scans
    const onVisible = () => {
      if (document.visibilityState === 'visible') load();
    };
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      cancelled = true;
      clearInterval(id);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, [authToken]);

  // Handle both whole-site scan structure (wcag_aggregate) and single-page structure (wcag_results)
  const violations = result?.wcag_aggregate?.violations_summary || result?.wcag_results?.violations || [];
  
  // Get total violations count (for display)
  const getTotalViolationsCount = () => {
    // For whole-site scans, use the total_violations count
    if (result?.wcag_aggregate?.total_violations !== undefined) {
      return result.wcag_aggregate.total_violations;
    }
    // For single-page scans, use violations array length
    return violations.length;
  };
  
  const getA11ySeverityCounts = () => {
    // For whole-site scans, use the pre-calculated impact_counts
    if (result?.wcag_aggregate?.impact_counts) {
      return {
        critical: result.wcag_aggregate.impact_counts.critical || 0,
        serious: result.wcag_aggregate.impact_counts.serious || 0,
        moderate: result.wcag_aggregate.impact_counts.moderate || 0,
        minor: result.wcag_aggregate.impact_counts.minor || 0,
        unknown: 0
      };
    }
    
    // For single-page scans, count from violations
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
    // For whole-site scans, use the pre-calculated score
    if (result?.summary?.accessibility_score !== undefined) {
      return result.summary.accessibility_score;
    }
    
    // For single-page scans, calculate from severity counts
    const c = getA11ySeverityCounts();
    const deduction = c.critical * 25 + c.serious * 15 + c.moderate * 8 + c.minor * 3 + c.unknown * 5;
    const score = Math.max(0, Math.min(100, 100 - deduction));
    return score;
  };
  const getSecuritySummaries = () => {
    // Handle both whole-site scan structure (security_aggregate.primary_scan) and single-page structure (security_results)
    const securityData = result?.security_aggregate?.primary_scan || result?.security_results || {};
    
    const sh = securityData?.securityheaders || {};
    const ssl = securityData?.ssllabs || {};
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
    return { securityScore, sslGrade, missingHeaders, presentHeaders };
  };
  const a11yCounts = result ? getA11ySeverityCounts() : { critical: 0, serious: 0, moderate: 0, minor: 0, unknown: 0 };
  const a11yScore = result ? computeAccessibilityScore() : 0;
  const { securityScore, sslGrade, missingHeaders, presentHeaders } = result ? getSecuritySummaries() : { securityScore: undefined, sslGrade: '', missingHeaders: [], presentHeaders: [] };

  // Format timestamp (handles both Unix timestamp and ISO string)
  const formatTimestamp = (ts) => {
    if (!ts) return '';
    try {
      // If it's a Unix timestamp (number), convert to milliseconds
      const date = typeof ts === 'number' ? new Date(ts * 1000) : new Date(ts);
      return date.toLocaleString('en-US', { 
        month: 'short', 
        day: 'numeric', 
        year: 'numeric',
        hour: '2-digit', 
        minute: '2-digit' 
      });
    } catch {
      return '';
    }
  };

  // Format duration in seconds to human-readable format
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

  return (
    <div className="mb-6">
      <h3 className="text-lg font-semibold mb-2">Latest UI Testing Results</h3>
      <div className="text-xs text-muted-foreground mb-3">
        {meta.url ? (
          <>
            <span className="font-medium">Website:</span> {meta.url}
            {meta.ts && <span className="ml-3"><span className="font-medium">Scanned:</span> {formatTimestamp(meta.ts)}</span>}
            <span className="ml-3"><span className="font-medium">Mode:</span> {meta.mode.charAt(0).toUpperCase() + meta.mode.slice(1)}</span>
          </>
        ) : (
          'No whole-site scans available. Run a scan from the UI Testing page.'
        )}
      </div>
      {result ? (
        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {(meta.mode === 'all' || meta.mode === 'accessibility') && (
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
          {(meta.mode === 'all' || meta.mode === 'accessibility') && (
            <div className="glass-card p-6 rounded-lg border-l-4 border-red-500">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">WCAG Violations</p>
                  <h3 className="text-2xl font-bold">{getTotalViolationsCount()}</h3>
                </div>
                <div className="p-3 rounded-full bg-red-500/10 text-red-500">
                  <FaChartLine className="h-6 w-6" />
                </div>
              </div>
              {result?.wcag_aggregate?.unique_rules_violated && (
                <div className="mt-2 text-xs text-muted-foreground">
                  {result.wcag_aggregate.unique_rules_violated} unique issues across {result.wcag_aggregate.pages_with_issues || 0} pages
                </div>
              )}
            </div>
          )}
          
          {/* Pages Scanned Card - Always shown for whole-site scans */}
          <div className="glass-card p-6 rounded-lg border-l-4 border-orange-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Pages Scanned</p>
                <h3 className="text-2xl font-bold">{result?.summary?.pages_scanned || result?.wcag_aggregate?.total_pages_scanned || 0}</h3>
              </div>
              <div className="p-3 rounded-full bg-orange-500/10 text-orange-500">
                <FaGlobe className="h-6 w-6" />
              </div>
            </div>
            <div className="mt-3 text-xs text-muted-foreground">
              {result?.summary?.pages_discovered && (
                <span>{result.summary.pages_discovered} pages discovered</span>
              )}
            </div>
          </div>

          {/* Scan Duration Card - Always shown for whole-site scans */}
          <div className="glass-card p-6 rounded-lg border-l-4 border-cyan-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Scan Duration</p>
                <h3 className="text-2xl font-bold">{formatDuration(result?.duration_seconds || 0)}</h3>
              </div>
              <div className="p-3 rounded-full bg-cyan-500/10 text-cyan-500">
                <FaClock className="h-6 w-6" />
              </div>
            </div>
            <div className="mt-3 text-xs text-muted-foreground">
              {result?.duration_seconds && (
                <span>{result.duration_seconds}s total</span>
              )}
            </div>
          </div>

          {(meta.mode === 'all' || meta.mode === 'security') && (
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
          {(meta.mode === 'all' || meta.mode === 'security') && (
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
      ) : (
        <div className="p-6 bg-secondary/50 rounded-lg border text-center">
          <div className="text-sm text-muted-foreground mb-2">No whole-site scan results available</div>
          <div className="text-xs text-muted-foreground">Visit the UI Testing page to run your first whole-site scan and see results here.</div>
        </div>
      )}

      {result && (
        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="p-6 bg-card rounded-xl shadow-lg border border-border">
            <h4 className="text-base font-semibold mb-3">WCAG Severity Distribution</h4>
            <SeverityBarChart counts={a11yCounts} />
          </div>
          <div className="p-6 bg-card rounded-xl shadow-lg border border-border">
            <h4 className="text-base font-semibold mb-3">Security Headers Coverage</h4>
            <HeadersDonutChart presentCount={presentHeaders.length} missingCount={missingHeaders.length} />
            {missingHeaders.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {missingHeaders.map((h) => (
                  <span key={h} className="px-2 py-1 text-xs rounded-full bg-red-100 text-red-800 border border-red-200">{h}</span>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

const SystemStatus = () => {
  const [status, setStatus] = useState({
    systemHealth: 'healthy',
    lastScan: '2024-03-20 14:30',
    activeUsers: 12,
    complianceScore: 85
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <FaServer className="text-primary" />
          <span className="font-medium">System Health</span>
        </div>
        <span className={`px-2 py-1 rounded-full text-xs ${
          status.systemHealth === 'healthy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
        }`}>
          {status.systemHealth === 'healthy' ? 'Healthy' : 'Needs Attention'}
        </span>
      </div>
      
      <div className="space-y-2">
        <div className="flex justify-between items-center">
          <span className="text-sm text-muted-foreground">Last Compliance Scan</span>
          <span className="text-sm font-medium">{status.lastScan}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-muted-foreground">Active Users</span>
          <span className="text-sm font-medium">{status.activeUsers}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-muted-foreground">Compliance Score</span>
          <span className="text-sm font-medium">{status.complianceScore}%</span>
        </div>
      </div>
    </div>
  );
};

const RecentActivities = () => {
  const [activities, setActivities] = useState([
    { type: 'scan', message: 'Compliance scan completed', time: '2 hours ago' },
    { type: 'chat', message: 'New compliance query resolved', time: '3 hours ago' },
    { type: 'update', message: 'System update completed', time: '5 hours ago' }
  ]);

  return (
    <div className="space-y-4">
      <div className="flex items-center space-x-2 mb-2">
        <FaHistory className="text-primary" />
        <span className="font-medium">Recent Activities</span>
      </div>
      
      <div className="space-y-3">
        {activities.map((activity, index) => (
          <div key={index} className="flex items-start space-x-3">
            <div className={`mt-1 w-2 h-2 rounded-full ${
              activity.type === 'scan' ? 'bg-blue-500' :
              activity.type === 'chat' ? 'bg-green-500' :
              'bg-purple-500'
            }`} />
            <div className="flex-1">
              <p className="text-sm">{activity.message}</p>
              <p className="text-xs text-muted-foreground">{activity.time}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const Notifications = () => {
  const [notifications, setNotifications] = useState([
    { type: 'warning', message: 'Compliance scan due in 2 days', time: '1 hour ago' },
    { type: 'info', message: 'New compliance guidelines available', time: '3 hours ago' },
    { type: 'success', message: 'System backup completed', time: '5 hours ago' }
  ]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <FaBell className="text-primary" />
          <span className="font-medium">Notifications</span>
        </div>
        <span className="text-xs text-muted-foreground">{notifications.length} new</span>
      </div>
      
      <div className="space-y-3">
        {notifications.map((notification, index) => (
          <div key={index} className="flex items-start space-x-3 p-2 rounded-lg hover:bg-secondary/50">
            <div className={`mt-1 ${
              notification.type === 'warning' ? 'text-yellow-500' :
              notification.type === 'info' ? 'text-blue-500' :
              'text-green-500'
            }`}>
              {notification.type === 'warning' ? <FaExclamationTriangle /> :
               notification.type === 'info' ? <FaInfo /> :
               <FaCheck />}
            </div>
            <div className="flex-1">
              <p className="text-sm">{notification.message}</p>
              <p className="text-xs text-muted-foreground">{notification.time}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const AzureConnectionMiniCard = () => {
  const { authToken } = useAuth();
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        setLoading(true);
        const response = await fetch(buildApiUrl('/api/azure/status'), {
          headers: {
            'Authorization': `Bearer ${authToken}`
          }
        });
        if (response.ok) {
          const data = await response.json();
          setConnected(!!data.connected);
        } else {
          setConnected(false);
        }
      } catch (e) {
        setConnected(false);
      } finally {
        setLoading(false);
      }
    };
    if (authToken) {
      fetchStatus();
    }
  }, [authToken]);

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      className="p-4 bg-card rounded-xl shadow-lg flex items-center justify-between"
    >
      <div className="flex items-center space-x-3">
        <FaCloud className={connected ? 'text-green-600' : 'text-gray-500'} />
        <div>
          <div className="text-sm font-semibold">Azure AD</div>
          <div className="text-xs text-muted-foreground">
            {loading ? 'Checking connection…' : (connected ? 'Connected' : 'Not connected')}
          </div>
        </div>
      </div>
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${connected ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400' : 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400'}`}>
        {loading ? '…' : (connected ? 'Connected' : 'Not Connected')}
      </span>
    </motion.div>
  );
};

const AzureADConfiguration = () => {
  const { authToken } = useAuth();
  const [isConnected, setIsConnected] = useState(false);
  const [configData, setConfigData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadingMessage, setLoadingMessage] = useState('Checking connection status...');
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [error, setError] = useState(null);

  // Progress messages for different stages of fetching
  const progressMessages = [
    { message: 'Checking connection status...', progress: 5 },
    { message: 'Verifying Azure AD credentials...', progress: 10 },
    { message: 'Fetching Conditional Access Policies...', progress: 15 },
    { message: 'Fetching Authentication Methods...', progress: 25 },
    { message: 'Fetching User Information...', progress: 35 },
    { message: 'Fetching Organization Settings...', progress: 45 },
    { message: 'Fetching Authorization Policies...', progress: 55 },
    { message: 'Fetching Application Registrations...', progress: 65 },
    { message: 'Fetching Groups and Directory Roles...', progress: 75 },
    { message: 'Fetching Security Settings...', progress: 85 },
    { message: 'Analyzing Compliance Status...', progress: 95 },
    { message: 'Finalizing configuration data...', progress: 100 }
  ];

  useEffect(() => {
    let progressInterval = null;
    let isMounted = true;
    
    const fetchStatusAndConfig = async () => {
      try {
        if (!isMounted) return;
        
        setLoading(true);
        setLoadingProgress(0);
        setError(null);
        
        // Simulate progress while fetching
        let currentMessageIndex = 0;
        progressInterval = setInterval(() => {
          if (!isMounted) {
            if (progressInterval) {
              clearInterval(progressInterval);
            }
            return;
          }
          
          if (currentMessageIndex < progressMessages.length - 1) {
            currentMessageIndex++;
            setLoadingMessage(progressMessages[currentMessageIndex].message);
            setLoadingProgress(progressMessages[currentMessageIndex].progress);
          } else {
            if (progressInterval) {
              clearInterval(progressInterval);
              progressInterval = null;
            }
          }
        }, 800); // Update message every 800ms
        
        // First check connection status
        setLoadingMessage(progressMessages[0].message);
        setLoadingProgress(progressMessages[0].progress);
        
        const statusResponse = await fetch(buildApiUrl('/api/azure/status'), {
          headers: {
            'Authorization': `Bearer ${authToken}`
          }
        });
        
        if (!isMounted) return;
        
        if (statusResponse.ok) {
          const statusData = await statusResponse.json();
          setIsConnected(!!statusData.connected);
          
          if (statusData.connected) {
            // Update message for config fetch
            setLoadingMessage('Fetching Azure AD configuration...');
            setLoadingProgress(20);
            
            // Fetch Azure AD configuration
            const configResponse = await fetch(buildApiUrl('/api/azure/config'), {
              headers: {
                'Authorization': `Bearer ${authToken}`
              }
            });
            
            if (!isMounted) return;
            
            if (configResponse.ok) {
              const data = await configResponse.json();
              setConfigData(data);
              setLoadingMessage('Configuration loaded successfully!');
              setLoadingProgress(100);
              // Small delay to show completion message
              await new Promise(resolve => setTimeout(resolve, 500));
            } else {
              if (progressInterval) {
                clearInterval(progressInterval);
                progressInterval = null;
              }
              setError('Failed to fetch Azure AD configuration');
            }
          } else {
            if (progressInterval) {
              clearInterval(progressInterval);
              progressInterval = null;
            }
          }
        } else {
          if (progressInterval) {
            clearInterval(progressInterval);
            progressInterval = null;
          }
          setIsConnected(false);
        }
        
        if (progressInterval) {
          clearInterval(progressInterval);
          progressInterval = null;
        }
      } catch (e) {
        if (!isMounted) return;
        
        if (progressInterval) {
          clearInterval(progressInterval);
          progressInterval = null;
        }
        setError('Failed to check Azure AD status');
        setIsConnected(false);
      } finally {
        if (isMounted) {
          setLoading(false);
          setLoadingProgress(100);
        }
      }
    };
    
    if (authToken) {
      fetchStatusAndConfig();
    }
    
    // Cleanup function
    return () => {
      isMounted = false;
      if (progressInterval) {
        clearInterval(progressInterval);
      }
    };
  }, [authToken]);

  const handleConnectClick = () => {
    // Dispatch event to switch to Azure tab
    window.dispatchEvent(new CustomEvent('setActiveTab', { detail: 'azure' }));
  };

  if (loading) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="space-y-6"
      >
        <div className="flex items-center space-x-4 mb-6">
          <div className="p-3 bg-blue-100 dark:bg-blue-900/20 rounded-lg">
            <FaCloud className="text-2xl text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-foreground">Azure AD Configuration</h2>
            <p className="text-muted-foreground">Loading your Azure Active Directory settings</p>
          </div>
        </div>

        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3 }}
          className="p-8 bg-card rounded-xl shadow-lg border border-border"
        >
          <div className="flex flex-col items-center justify-center space-y-6">
            {/* Animated Spinner */}
            <div className="relative">
              <div className="w-20 h-20 border-4 border-primary/20 rounded-full"></div>
              <div className="absolute top-0 left-0 w-20 h-20 border-4 border-transparent border-t-primary rounded-full animate-spin"></div>
              <FaCloud className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-2xl text-primary" />
            </div>

            {/* Loading Message */}
            <div className="text-center space-y-2">
              <motion.p
                key={loadingMessage}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
                className="text-lg font-semibold text-foreground"
              >
                {loadingMessage}
              </motion.p>
              <p className="text-sm text-muted-foreground">
                This may take a few moments...
              </p>
            </div>

            {/* Progress Bar */}
            <div className="w-full max-w-md space-y-2">
              <div className="flex justify-between text-xs text-muted-foreground mb-1">
                <span>Progress</span>
                <span>{loadingProgress}%</span>
              </div>
              <div className="w-full bg-secondary rounded-full h-2.5 overflow-hidden">
                <motion.div
                  className="h-full bg-gradient-to-r from-blue-500 to-blue-600 rounded-full"
                  initial={{ width: '0%' }}
                  animate={{ width: `${loadingProgress}%` }}
                  transition={{ duration: 0.5, ease: 'easeOut' }}
                />
              </div>
            </div>

            {/* Loading Steps Indicator */}
            <div className="w-full max-w-md space-y-2">
              <div className="flex items-center justify-center space-x-2 text-xs text-muted-foreground">
                <FaSpinner className="animate-spin text-primary" />
                <span>Fetching settings from Microsoft Graph API</span>
              </div>
            </div>
          </div>
        </motion.div>
      </motion.div>
    );
  }

  if (!isConnected) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="space-y-6"
      >
        <div className="flex items-center space-x-4 mb-6">
          <div className="p-3 bg-blue-100 dark:bg-blue-900/20 rounded-lg">
            <FaCloud className="text-2xl text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-foreground">Azure AD Configuration</h2>
            <p className="text-muted-foreground">View your Azure Active Directory settings</p>
          </div>
        </div>

        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-8 bg-card rounded-xl shadow-lg border border-border text-center"
        >
          <div className="flex flex-col items-center space-y-4">
            <FaCloud className="text-4xl text-muted-foreground" />
            <div>
              <h3 className="text-lg font-semibold mb-2">Not Connected to Azure AD</h3>
              <p className="text-muted-foreground mb-6">
                You need to connect to Azure AD first to view configuration settings.
              </p>
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={handleConnectClick}
                className="px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
              >
                Connect to Azure AD
              </motion.button>
            </div>
          </div>
        </motion.div>
      </motion.div>
    );
  }

  if (error) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="space-y-6"
      >
        <div className="flex items-center space-x-4 mb-6">
          <div className="p-3 bg-blue-100 dark:bg-blue-900/20 rounded-lg">
            <FaCloud className="text-2xl text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-foreground">Azure AD Configuration</h2>
            <p className="text-muted-foreground">View your Azure Active Directory settings</p>
          </div>
        </div>

        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-6 bg-destructive/10 border border-destructive/20 rounded-xl"
        >
          <div className="flex items-center space-x-2">
            <FaExclamationTriangle className="text-destructive" />
            <span className="text-destructive">{error}</span>
          </div>
        </motion.div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="space-y-6"
    >
      <div className="flex items-center space-x-4 mb-6">
        <div className="p-3 bg-blue-100 dark:bg-blue-900/20 rounded-lg">
          <FaCloud className="text-2xl text-blue-600 dark:text-blue-400" />
        </div>
        <div>
          <h2 className="text-2xl font-bold text-foreground">Azure AD Configuration</h2>
          <p className="text-muted-foreground">Current Azure Active Directory settings</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Conditional Access Policies */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-6 bg-card rounded-xl shadow-lg border border-border"
        >
          <div className="flex items-center space-x-3 mb-4">
            <FaShieldAlt className="text-xl text-primary" />
            <h3 className="text-lg font-semibold">Conditional Access Policies</h3>
          </div>
          <div className="space-y-3">
            {configData?.conditional_access_policies?.error ? (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <div className="text-sm text-destructive">{configData.conditional_access_policies.error}</div>
              </div>
            ) : configData?.conditional_access_policies?.value?.length > 0 ? (
              configData.conditional_access_policies.value.slice(0, 3).map((policy, index) => (
                <div key={index} className="p-3 bg-secondary/50 rounded-lg">
                  <div className="font-medium text-sm">{policy.displayName}</div>
                  <div className="text-xs text-muted-foreground">
                    State: {policy.state}
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted-foreground">No conditional access policies found</p>
            )}
          </div>
        </motion.div>

        {/* Authentication Methods */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-6 bg-card rounded-xl shadow-lg border border-border"
        >
          <div className="flex items-center space-x-3 mb-4">
            <FaKey className="text-xl text-primary" />
            <h3 className="text-lg font-semibold">Authentication Methods</h3>
          </div>
          <div className="space-y-3">
            {configData?.authentication_methods_policy?.error ? (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <div className="text-sm text-destructive">{configData.authentication_methods_policy.error}</div>
              </div>
            ) : configData?.authentication_methods_policy?.authenticationMethodConfigurations ? (
              configData.authentication_methods_policy.authenticationMethodConfigurations
                .filter(method => method.state === 'enabled')
                .map((method, index) => (
                  <div key={index} className="p-3 bg-secondary/50 rounded-lg">
                    <div className="font-medium text-sm">{method.id}</div>
                    <div className="text-xs text-muted-foreground">
                      State: {method.state}
                    </div>
                  </div>
                ))
            ) : (
              <p className="text-sm text-muted-foreground">No authentication methods found</p>
            )}
          </div>
        </motion.div>

        {/* Users Overview */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-6 bg-card rounded-xl shadow-lg border border-border"
        >
          <div className="flex items-center space-x-3 mb-4">
            <FaUser className="text-xl text-primary" />
            <h3 className="text-lg font-semibold">Users Overview</h3>
          </div>
          <div className="space-y-3">
            {configData?.users?.error ? (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <div className="text-sm text-destructive">{configData.users.error}</div>
              </div>
            ) : configData?.users?.value?.length > 0 ? (
              <div>
                <div className="text-2xl font-bold text-primary">
                  {configData.users.value.length}
                </div>
                <div className="text-sm text-muted-foreground">Total users (showing first 10)</div>
                <div className="mt-3 space-y-2">
                  {configData.users.value.slice(0, 3).map((user, index) => (
                    <div key={index} className="p-2 bg-secondary/50 rounded text-sm">
                      <div className="font-medium">{user.displayName || user.userPrincipalName}</div>
                      <div className="text-xs text-muted-foreground">
                        {user.accountEnabled ? 'Active' : 'Disabled'}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No users found</p>
            )}
          </div>
        </motion.div>

        {/* Applications */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-6 bg-card rounded-xl shadow-lg border border-border"
        >
          <div className="flex items-center space-x-3 mb-4">
            <FaDesktop className="text-xl text-primary" />
            <h3 className="text-lg font-semibold">Applications</h3>
          </div>
          <div className="space-y-3">
            {configData?.applications?.error ? (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <div className="text-sm text-destructive">{configData.applications.error}</div>
              </div>
            ) : configData?.applications?.value?.length > 0 ? (
              <div>
                <div className="text-2xl font-bold text-primary">
                  {configData.applications.value.length}
                </div>
                <div className="text-sm text-muted-foreground">Registered applications (showing first 10)</div>
                <div className="mt-3 space-y-2">
                  {configData.applications.value.slice(0, 3).map((app, index) => (
                    <div key={index} className="p-2 bg-secondary/50 rounded text-sm">
                      <div className="font-medium">{app.displayName}</div>
                      <div className="text-xs text-muted-foreground">
                        Created: {new Date(app.createdDateTime).toLocaleDateString()}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No applications found</p>
            )}
          </div>
        </motion.div>

        {/* Groups */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-6 bg-card rounded-xl shadow-lg border border-border"
        >
          <div className="flex items-center space-x-3 mb-4">
            <FaUsers className="text-xl text-primary" />
            <h3 className="text-lg font-semibold">Groups</h3>
          </div>
          <div className="space-y-3">
            {configData?.groups?.error ? (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <div className="text-sm text-destructive">{configData.groups.error}</div>
              </div>
            ) : configData?.groups?.value?.length > 0 ? (
              <div>
                <div className="text-2xl font-bold text-primary">
                  {configData.groups.value.length}
                </div>
                <div className="text-sm text-muted-foreground">Total groups (showing first 10)</div>
                <div className="mt-3 space-y-2">
                  {configData.groups.value.slice(0, 3).map((group, index) => (
                    <div key={index} className="p-2 bg-secondary/50 rounded text-sm">
                      <div className="font-medium">{group.displayName}</div>
                      {group.description && (
                        <div className="text-xs text-muted-foreground">{group.description}</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No groups found</p>
            )}
          </div>
        </motion.div>

        {/* Directory Settings */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-6 bg-card rounded-xl shadow-lg border border-border"
        >
          <div className="flex items-center space-x-3 mb-4">
            <FaLock className="text-xl text-primary" />
            <h3 className="text-lg font-semibold">Organization Settings</h3>
          </div>
          <div className="space-y-3">
            {configData?.organization?.error ? (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <div className="text-sm text-destructive">{configData.organization.error}</div>
              </div>
            ) : configData?.organization?.value?.length > 0 ? (
              <div className="space-y-2">
                {configData.organization.value.slice(0, 3).map((org, index) => (
                  <div key={index} className="p-2 bg-secondary/50 rounded text-sm">
                    <div className="font-medium">{org.displayName || org.id}</div>
                    <div className="text-xs text-muted-foreground">
                      Domain: {org.verifiedDomains?.[0]?.name || 'N/A'}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No organization settings found</p>
            )}
          </div>
        </motion.div>

        {/* Authorization Policy */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-6 bg-card rounded-xl shadow-lg border border-border"
        >
          <div className="flex items-center space-x-3 mb-4">
            <FaShieldAlt className="text-xl text-primary" />
            <h3 className="text-lg font-semibold">Authorization Policy</h3>
          </div>
          <div className="space-y-3">
            {configData?.authorization_policy?.error ? (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <div className="text-sm text-destructive">{configData.authorization_policy.error}</div>
              </div>
            ) : configData?.authorization_policy?.value?.length > 0 ? (
              <div className="space-y-2">
                {configData.authorization_policy.value.slice(0, 3).map((policy, index) => (
                  <div key={index} className="p-2 bg-secondary/50 rounded text-sm">
                    <div className="font-medium">{policy.displayName || policy.id}</div>
                    <div className="text-xs text-muted-foreground">
                      Type: {policy.templateId || 'N/A'}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No authorization policies found</p>
            )}
          </div>
        </motion.div>

        {/* Cross Tenant Access Policy */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-6 bg-card rounded-xl shadow-lg border border-border"
        >
          <div className="flex items-center space-x-3 mb-4">
            <FaGlobe className="text-xl text-primary" />
            <h3 className="text-lg font-semibold">Cross Tenant Access</h3>
          </div>
          <div className="space-y-3">
            {configData?.cross_tenant_access_policy?.error ? (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <div className="text-sm text-destructive">{configData.cross_tenant_access_policy.error}</div>
              </div>
            ) : configData?.cross_tenant_access_policy?.value?.length > 0 ? (
              <div className="space-y-2">
                {configData.cross_tenant_access_policy.value.slice(0, 3).map((policy, index) => (
                  <div key={index} className="p-2 bg-secondary/50 rounded text-sm">
                    <div className="font-medium">{policy.displayName || policy.id}</div>
                    <div className="text-xs text-muted-foreground">
                      Type: {policy.templateId || 'N/A'}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No cross tenant access policies found</p>
            )}
          </div>
        </motion.div>

        {/* Cross Tenant Access Default */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-6 bg-card rounded-xl shadow-lg border border-border"
        >
          <div className="flex items-center space-x-3 mb-4">
            <FaGlobe className="text-xl text-primary" />
            <h3 className="text-lg font-semibold">Cross Tenant Default</h3>
          </div>
          <div className="space-y-3">
            {configData?.cross_tenant_access_default?.error ? (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <div className="text-sm text-destructive">{configData.cross_tenant_access_default.error}</div>
              </div>
            ) : configData?.cross_tenant_access_default ? (
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Inbound MFA Trusted</span>
                  <span className="font-medium">
                    {configData.cross_tenant_access_default?.inboundTrust?.isMfaAccepted === true ? 'Yes' :
                      configData.cross_tenant_access_default?.inboundTrust?.isMfaAccepted === false ? 'No' : 'N/A'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Outbound Settings</span>
                  <span className="font-medium">{Object.keys(configData.cross_tenant_access_default || {}).length > 0 ? 'Configured' : 'N/A'}</span>
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No default policy data</p>
            )}
          </div>
        </motion.div>

        {/* Cross Tenant Partners */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-6 bg-card rounded-xl shadow-lg border border-border"
        >
          <div className="flex items-center space-x-3 mb-4">
            <FaGlobe className="text-xl text-primary" />
            <h3 className="text-lg font-semibold">Cross Tenant Partners</h3>
          </div>
          <div className="space-y-3">
            {configData?.cross_tenant_access_partners?.error ? (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <div className="text-sm text-destructive">{configData.cross_tenant_access_partners.error}</div>
              </div>
            ) : configData?.cross_tenant_access_partners?.value?.length > 0 ? (
              <div>
                <div className="text-2xl font-bold text-primary">
                  {configData.cross_tenant_access_partners.value.length}
                </div>
                <div className="text-sm text-muted-foreground">Configured partners</div>
                <div className="mt-3 space-y-2">
                  {configData.cross_tenant_access_partners.value.slice(0, 3).map((p, i) => (
                    <div key={i} className="p-2 bg-secondary/50 rounded text-sm">
                      <div className="font-medium">{p.tenantId || p.id}</div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No partners configured</p>
            )}
          </div>
        </motion.div>

        {/* Audit Logs */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-6 bg-card rounded-xl shadow-lg border border-border"
        >
          <div className="flex items-center space-x-3 mb-4">
            <FaClipboardList className="text-xl text-primary" />
            <h3 className="text-lg font-semibold">Audit Logs</h3>
          </div>
          <div className="space-y-3">
            {configData?.audit_logs?.error ? (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <div className="text-sm text-destructive">{configData.audit_logs.error}</div>
              </div>
            ) : configData?.audit_logs?.value?.length > 0 ? (
              <div>
                <div className="text-2xl font-bold text-primary">
                  {configData.audit_logs.value.length}
                </div>
                <div className="text-sm text-muted-foreground">Recent audit events (showing first 10)</div>
                <div className="mt-3 space-y-2">
                  {configData.audit_logs.value.slice(0, 3).map((log, index) => (
                    <div key={index} className="p-2 bg-secondary/50 rounded text-sm">
                      <div className="font-medium">{log.activityDisplayName || 'Unknown Activity'}</div>
                      <div className="text-xs text-muted-foreground">
                        {new Date(log.activityDateTime).toLocaleDateString()}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No audit logs found</p>
            )}
          </div>
        </motion.div>

        {/* Risky Users (Identity Protection) */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-6 bg-card rounded-xl shadow-lg border border-border"
        >
          <div className="flex items-center space-x-3 mb-4">
            <FaShieldAlt className="text-xl text-primary" />
            <h3 className="text-lg font-semibold">Risky Users</h3>
          </div>
          <div className="space-y-3">
            {configData?.identity_protection_risky_users?.error ? (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <div className="text-sm text-destructive">{configData.identity_protection_risky_users.error}</div>
              </div>
            ) : configData?.identity_protection_risky_users?.value?.length >= 0 ? (
              <div>
                <div className="text-2xl font-bold text-primary">
                  {configData.identity_protection_risky_users.value?.length || 0}
                </div>
                <div className="text-sm text-muted-foreground">Risky users (first 10)</div>
                <div className="mt-3 space-y-2">
                  {(configData.identity_protection_risky_users.value || []).slice(0, 3).map((u, i) => (
                    <div key={i} className="p-2 bg-secondary/50 rounded text-sm">
                      <div className="font-medium">{u.userPrincipalName || u.id}</div>
                      {u.riskLevel && (
                        <div className="text-xs text-muted-foreground">Risk: {u.riskLevel}</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No risky users found</p>
            )}
          </div>
        </motion.div>

        {/* Directory Roles */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-6 bg-card rounded-xl shadow-lg border border-border"
        >
          <div className="flex items-center space-x-3 mb-4">
            <FaShieldAlt className="text-xl text-primary" />
            <h3 className="text-lg font-semibold">Directory Roles</h3>
          </div>
          <div className="space-y-3">
            {configData?.directory_roles?.error ? (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <div className="text-sm text-destructive">{configData.directory_roles.error}</div>
              </div>
            ) : configData?.directory_roles?.value?.length > 0 ? (
              <div className="space-y-2">
                {configData.directory_roles.value.slice(0, 3).map((role, idx) => {
                  const memberCount = (configData.directory_role_members &&
                    configData.directory_role_members[role.id] &&
                    (configData.directory_role_members[role.id].value || []).length) || 0;
                  return (
                    <div key={idx} className="p-2 bg-secondary/50 rounded text-sm">
                      <div className="font-medium">{role.displayName || role.templateId || role.id}</div>
                      <div className="text-xs text-muted-foreground">Members: {memberCount}</div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No directory roles found</p>
            )}
          </div>
        </motion.div>

        {/* Group Settings */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-6 bg-card rounded-xl shadow-lg border border-border"
        >
          <div className="flex items-center space-x-3 mb-4">
            <FaUsers className="text-xl text-primary" />
            <h3 className="text-lg font-semibold">Group Settings</h3>
          </div>
          <div className="space-y-3">
            {configData?.group_settings?.error ? (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <div className="text-sm text-destructive">{configData.group_settings.error}</div>
              </div>
            ) : configData?.group_settings?.value?.length > 0 ? (
              <div className="space-y-2 text-sm">
                {(() => {
                  const list = configData.group_settings.value || [];
                  let enableVal = null;
                  for (const s of list) {
                    if (Array.isArray(s.values)) {
                      const v = s.values.find(x => x.name === 'EnableGroupCreation');
                      if (v) { enableVal = v.value; break; }
                    }
                  }
                  return (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Self-service group creation</span>
                      <span className="font-medium">{enableVal !== null ? String(enableVal) : 'Unknown'}</span>
                    </div>
                  );
                })()}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No group settings found</p>
            )}
          </div>
        </motion.div>

        {/* Directory Settings */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-6 bg-card rounded-xl shadow-lg border border-border"
        >
          <div className="flex items-center space-x-3 mb-4">
            <FaCog className="text-xl text-primary" />
            <h3 className="text-lg font-semibold">Directory Settings</h3>
          </div>
          <div className="space-y-3">
            {configData?.settings?.error ? (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <div className="text-sm text-destructive">{configData.settings.error}</div>
              </div>
            ) : configData?.settings?.value?.length >= 0 ? (
              <div>
                <div className="text-2xl font-bold text-primary">{configData.settings.value?.length || 0}</div>
                <div className="text-sm text-muted-foreground">Directory settings objects</div>
                <div className="mt-3 space-y-2 text-xs">
                  {(configData.settings.value || []).slice(0, 2).map((s, i) => (
                    <div key={i} className="p-2 bg-secondary/50 rounded">
                      <div className="font-medium">{s.displayName || s.id}</div>
                      {Array.isArray(s.values) && s.values.length > 0 && (
                        <div className="text-muted-foreground">{s.values[0].name}: {String(s.values[0].value)}</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No directory settings found</p>
            )}
          </div>
        </motion.div>

        {/* Certificate-based Auth Configuration */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-6 bg-card rounded-xl shadow-lg border border-border"
        >
          <div className="flex items-center space-x-3 mb-4">
            <FaLock className="text-xl text-primary" />
            <h3 className="text-lg font-semibold">Certificate-based Auth</h3>
          </div>
          <div className="space-y-3">
            {configData?.certificate_based_auth_configuration?.error ? (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <div className="text-sm text-destructive">{configData.certificate_based_auth_configuration.error}</div>
              </div>
            ) : configData?.certificate_based_auth_configuration?.value?.length >= 0 ? (
              <div>
                <div className="text-2xl font-bold text-primary">{configData.certificate_based_auth_configuration.value?.length || 0}</div>
                <div className="text-sm text-muted-foreground">Certificate auth configurations</div>
                {(configData.certificate_based_auth_configuration.value || []).slice(0, 1).map((c, i) => (
                  <div key={i} className="mt-3 p-2 bg-secondary/50 rounded text-xs">
                    <div className="font-medium">{c.id || 'Config'}</div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No certificate-based auth configuration found</p>
            )}
          </div>
        </motion.div>

        {/* Lifecycle Workflows */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-6 bg-card rounded-xl shadow-lg border border-border"
        >
          <div className="flex items-center space-x-3 mb-4">
            <FaClipboardList className="text-xl text-primary" />
            <h3 className="text-lg font-semibold">Lifecycle Workflows</h3>
          </div>
          <div className="space-y-3">
            {configData?.lifecycle_workflows?.error ? (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <div className="text-sm text-destructive">{configData.lifecycle_workflows.error}</div>
              </div>
            ) : configData?.lifecycle_workflows?.value?.length >= 0 ? (
              <div>
                <div className="text-2xl font-bold text-primary">{configData.lifecycle_workflows.value?.length || 0}</div>
                <div className="text-sm text-muted-foreground">Lifecycle workflows</div>
                <div className="mt-3 space-y-2">
                  {(configData.lifecycle_workflows.value || []).slice(0, 3).map((w, i) => (
                    <div key={i} className="p-2 bg-secondary/50 rounded text-sm">
                      <div className="font-medium">{w.displayName || w.id}</div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No lifecycle workflows found</p>
            )}
          </div>
        </motion.div>
      </div>


    </motion.div>
  );
};

// Azure AD Change Logs Component
const AzureADChangeLogs = () => {
  const { authToken } = useAuth();
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    date: '',
    userEmail: '',
    changeType: '',
    statusFilter: ''
  });
  const [totalLogs, setTotalLogs] = useState(0);
  const [currentPage, setCurrentPage] = useState(0);
  const logsPerPage = 20;

  useEffect(() => {
    fetchLogs();
  }, [authToken, filters, currentPage]);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params = new URLSearchParams({
        limit: logsPerPage.toString(),
        skip: (currentPage * logsPerPage).toString()
      });
      
      if (filters.date) {
        // Set start_date to the beginning of the selected date (00:00:00)
        // Use the date string directly to avoid timezone conversion issues
        params.append('start_date', filters.date);
        // Send the same date as end_date - backend will add 1 day to it
        // This ensures we get logs only for the selected date
        params.append('end_date', filters.date);
      }
      if (filters.userEmail) params.append('user_email', filters.userEmail);
      if (filters.changeType) params.append('change_type', filters.changeType);
      if (filters.statusFilter) params.append('status_filter', filters.statusFilter);
      
      const response = await fetch(buildApiUrl(`/api/azure/logs?${params}`), {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch logs');
      }
      
      const data = await response.json();
      setLogs(data.logs || []);
      setTotalLogs(data.total || 0);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (field, value) => {
    setFilters(prev => ({ ...prev, [field]: value }));
    setCurrentPage(0); // Reset to first page when filters change
  };

  const handleExport = async (format) => {
    try {
      const params = new URLSearchParams();
      if (filters.date) {
        // Send the same date for both start and end - backend will add 1 day to end_date
        params.append('start_date', filters.date);
        params.append('end_date', filters.date);
      }
      if (filters.userEmail) params.append('user_email', filters.userEmail);
      if (filters.changeType) params.append('change_type', filters.changeType);
      if (filters.statusFilter) params.append('status_filter', filters.statusFilter);
      
      const url = buildApiUrl(`/api/azure/logs/export/${format}?${params}`);
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });
      
      if (!response.ok) {
        throw new Error(`Failed to export ${format.toUpperCase()}`);
      }
      
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = `azure_config_logs_${new Date().toISOString().split('T')[0]}.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(downloadUrl);
    } catch (err) {
      setError(err.message);
    }
  };

  const formatTimestamp = (timestamp) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleString();
    } catch {
      return timestamp;
    }
  };

  const getStatusBadge = (status) => {
    const isSuccess = status === 'success';
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
        isSuccess 
          ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400'
          : 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400'
      }`}>
        {status?.toUpperCase() || 'UNKNOWN'}
      </span>
    );
  };

  const totalPages = Math.ceil(totalLogs / logsPerPage);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-4">
          <div className="p-3 bg-purple-100 dark:bg-purple-900/20 rounded-lg">
            <FaClipboardList className="text-2xl text-purple-600 dark:text-purple-400" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-foreground">Change Logs</h2>
            <p className="text-muted-foreground">View and manage Azure AD configuration change history</p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => handleExport('csv')}
            className="px-4 py-2 bg-secondary text-foreground rounded-lg hover:bg-secondary/80 transition-colors flex items-center space-x-2"
          >
            <FaFileAlt />
            <span>Export CSV</span>
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => handleExport('pdf')}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors flex items-center space-x-2"
          >
            <FaFilePdf />
            <span>Export PDF</span>
          </motion.button>
        </div>
      </div>

      {/* Filters */}
      <motion.div
        whileHover={{ scale: 1.01 }}
        className="p-6 bg-card rounded-xl shadow-lg border border-border mb-6"
      >
        <h3 className="text-lg font-semibold mb-4">Filters</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Date Filter */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">Date</label>
            <input
              type="date"
              value={filters.date}
              onChange={(e) => handleFilterChange('date', e.target.value)}
              className="w-full px-4 py-2.5 border border-border rounded-lg focus:ring-2 focus:ring-primary/30 focus:border-primary bg-background transition-all duration-200 shadow-sm hover:shadow-md"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">User Email</label>
            <input
              type="text"
              value={filters.userEmail}
              onChange={(e) => handleFilterChange('userEmail', e.target.value)}
              placeholder="Filter by user email"
              className="w-full px-4 py-2.5 border border-border rounded-lg focus:ring-2 focus:ring-primary/30 focus:border-primary bg-background transition-all duration-200 shadow-sm hover:shadow-md"
            />
          </div>
          <div className="space-y-2 relative">
            <label className="text-sm font-medium text-foreground">Change Type</label>
            <div className="relative">
              <select
                value={filters.changeType}
                onChange={(e) => handleFilterChange('changeType', e.target.value)}
                className="w-full px-4 py-2.5 border border-border rounded-lg focus:ring-2 focus:ring-primary/30 focus:border-primary bg-background appearance-none cursor-pointer transition-all duration-200 shadow-sm hover:shadow-md pr-10"
                style={{
                  backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3E%3Cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3E%3C/svg%3E")`,
                  backgroundPosition: 'right 0.5rem center',
                  backgroundRepeat: 'no-repeat',
                  backgroundSize: '1.5em 1.5em'
                }}
              >
                <option value="">All Types</option>
                <option value="config_fetch">Config Fetch</option>
                <option value="connection">Connection</option>
              </select>
            </div>
          </div>
          <div className="space-y-2 relative">
            <label className="text-sm font-medium text-foreground">Status</label>
            <div className="relative">
              <select
                value={filters.statusFilter}
                onChange={(e) => handleFilterChange('statusFilter', e.target.value)}
                className="w-full px-4 py-2.5 border border-border rounded-lg focus:ring-2 focus:ring-primary/30 focus:border-primary bg-background appearance-none cursor-pointer transition-all duration-200 shadow-sm hover:shadow-md pr-10"
                style={{
                  backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3E%3Cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3E%3C/svg%3E")`,
                  backgroundPosition: 'right 0.5rem center',
                  backgroundRepeat: 'no-repeat',
                  backgroundSize: '1.5em 1.5em'
                }}
              >
                <option value="">All Statuses</option>
                <option value="success">Success</option>
                <option value="failed">Failed</option>
              </select>
            </div>
          </div>
        </div>
        <div className="mt-4 flex justify-end">
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => {
              setFilters({
                date: '',
                userEmail: '',
                changeType: '',
                statusFilter: ''
              });
              setCurrentPage(0);
            }}
            className="px-6 py-2 border border-border rounded-lg hover:bg-secondary transition-all duration-200 shadow-sm hover:shadow-md"
          >
            Clear Filters
          </motion.button>
        </div>
      </motion.div>

      {/* Logs Table */}
      <motion.div
        whileHover={{ scale: 1.01 }}
        className="p-6 bg-card rounded-xl shadow-lg border border-border"
      >
        {loading ? (
          <div className="flex items-center justify-center p-8">
            <FaSpinner className="animate-spin text-2xl text-primary" />
          </div>
        ) : error ? (
          <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-lg">
            <div className="flex items-center space-x-2">
              <FaExclamationTriangle className="text-destructive" />
              <span className="text-destructive">{error}</span>
            </div>
          </div>
        ) : logs.length === 0 ? (
          <div className="text-center p-8 text-muted-foreground">
            <FaClipboardList className="text-4xl mx-auto mb-4 opacity-50" />
            <p>No logs found matching your filters</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left p-3 text-sm font-semibold">Timestamp</th>
                    <th className="text-left p-3 text-sm font-semibold">User</th>
                    <th className="text-left p-3 text-sm font-semibold">Change Type</th>
                    <th className="text-left p-3 text-sm font-semibold">Details</th>
                    <th className="text-left p-3 text-sm font-semibold">Status</th>
                    <th className="text-left p-3 text-sm font-semibold">Error</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log, index) => {
                    // Extract connection details for connection type logs
                    const isConnection = log.change_type === 'connection';
                    const details = log.details || {};
                    const connectionDetails = isConnection ? (
                      <div className="space-y-1">
                        {details.tenant_id && (
                          <div className="text-xs">
                            <span className="font-medium">Tenant ID: </span>
                            <span className="text-muted-foreground">{details.tenant_id}</span>
                          </div>
                        )}
                        {details.action && (
                          <div className="text-xs">
                            <span className="font-medium">Action: </span>
                            <span className="text-muted-foreground capitalize">{details.action.replace('_', ' ')}</span>
                          </div>
                        )}
                        {details.connection_time && (
                          <div className="text-xs">
                            <span className="font-medium">Connection Time: </span>
                            <span className="text-muted-foreground">{formatTimestamp(details.connection_time)}</span>
                          </div>
                        )}
                        {details.disconnection_time && (
                          <div className="text-xs">
                            <span className="font-medium">Disconnection Time: </span>
                            <span className="text-muted-foreground">{formatTimestamp(details.disconnection_time)}</span>
                          </div>
                        )}
                      </div>
                    ) : (
                      <span className="text-muted-foreground text-xs">—</span>
                    );

                    return (
                      <motion.tr
                        key={log._id || index}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.05 }}
                        className="border-b border-border hover:bg-secondary/50 transition-colors"
                      >
                        <td className="p-3 text-sm">{formatTimestamp(log.timestamp)}</td>
                        <td className="p-3 text-sm">{log.user_email || 'N/A'}</td>
                        <td className="p-3 text-sm">
                          <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900/20 text-blue-800 dark:text-blue-400 rounded text-xs">
                            {log.change_type || 'N/A'}
                          </span>
                        </td>
                        <td className="p-3 text-sm">{connectionDetails}</td>
                        <td className="p-3">{getStatusBadge(log.status)}</td>
                        <td className="p-3 text-sm text-muted-foreground">
                          {log.error_message ? (
                            <span className="text-red-600 dark:text-red-400" title={log.error_message}>
                              {log.error_message.length > 50 ? `${log.error_message.substring(0, 50)}...` : log.error_message}
                            </span>
                          ) : (
                            <span className="text-green-600 dark:text-green-400">—</span>
                          )}
                        </td>
                      </motion.tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            
            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-4 pt-4 border-t border-border">
                <div className="text-sm text-muted-foreground">
                  Showing {currentPage * logsPerPage + 1} to {Math.min((currentPage + 1) * logsPerPage, totalLogs)} of {totalLogs} logs
                </div>
                <div className="flex items-center space-x-2">
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => setCurrentPage(prev => Math.max(0, prev - 1))}
                    disabled={currentPage === 0}
                    className="px-4 py-2 border border-border rounded-lg hover:bg-secondary disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Previous
                  </motion.button>
                  <span className="px-4 py-2 text-sm">
                    Page {currentPage + 1} of {totalPages}
                  </span>
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => setCurrentPage(prev => Math.min(totalPages - 1, prev + 1))}
                    disabled={currentPage >= totalPages - 1}
                    className="px-4 py-2 border border-border rounded-lg hover:bg-secondary disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Next
                  </motion.button>
                </div>
              </div>
            )}
          </>
        )}
      </motion.div>
    </motion.div>
  );
};

const AzureADConnection = () => {
  const { authToken } = useAuth();
  const [formData, setFormData] = useState({
    clientId: '',
    clientSecret: '',
    tenantId: ''
  });
  const [showSecret, setShowSecret] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [statusLoading, setStatusLoading] = useState(true);
  const [showDisconnectModal, setShowDisconnectModal] = useState(false);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        setStatusLoading(true);
        const response = await fetch(buildApiUrl('/api/azure/status'), {
          headers: {
            'Authorization': `Bearer ${authToken}`
          }
        });
        if (response.ok) {
          const data = await response.json();
          setIsConnected(!!data.connected);
        }
      } catch (e) {
        // ignore
      } finally {
        setStatusLoading(false);
      }
    };
    if (authToken) {
      fetchStatus();
    }
  }, [authToken]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    // Clear error when user starts typing
    if (error) setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await fetch(buildApiUrl('/api/azure/connect'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify(formData)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to connect to Azure AD');
      }

      const data = await response.json();
      setSuccess('Successfully connected to Azure AD!');
      setIsConnected(true);
      
      // Clear form after successful connection
      setFormData({
        clientId: '',
        clientSecret: '',
        tenantId: ''
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDisconnect = () => {
    setShowDisconnectModal(true);
  };

  const confirmDisconnect = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(buildApiUrl('/api/azure/disconnect'), {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });

      if (response.ok) {
        setIsConnected(false);
        setSuccess('Successfully disconnected from Azure AD');
      }
    } catch (err) {
      setError('Failed to disconnect from Azure AD');
    } finally {
      setIsLoading(false);
      setShowDisconnectModal(false);
    }
  };

  const cancelDisconnect = () => setShowDisconnectModal(false);

  return (
    <>
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="space-y-6"
    >
      <div className="flex items-center space-x-4 mb-6">
        <div className="p-3 bg-blue-100 dark:bg-blue-900/20 rounded-lg">
          <FaCloud className="text-2xl text-blue-600 dark:text-blue-400" />
        </div>
        <div>
          <h2 className="text-2xl font-bold text-foreground">Connect to Azure AD</h2>
          <p className="text-muted-foreground">Configure your Azure Active Directory integration</p>
        </div>
      </div>

      <div className={`${isConnected ? 'grid grid-cols-1 gap-6' : 'grid grid-cols-1 lg:grid-cols-3 gap-6'}`}>
        {/* Connection Form - hidden when connected */}
        {!isConnected && (
          <div className="lg:col-span-2">
            <motion.div
              whileHover={{ scale: 1.01 }}
              className="p-6 bg-card rounded-xl shadow-lg border border-border"
            >
              <div className="flex items-center space-x-3 mb-6">
                <FaKey className="text-xl text-primary" />
                <h3 className="text-lg font-semibold">Azure AD Configuration</h3>
              </div>

              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mb-4 p-4 bg-destructive/10 border border-destructive/20 rounded-lg"
                >
                  <div className="flex items-center space-x-2">
                    <FaExclamationTriangle className="text-destructive" />
                    <span className="text-destructive text-sm">{error}</span>
                  </div>
                </motion.div>
              )}

              {success && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mb-4 p-4 bg-green-100 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg"
                >
                  <div className="flex items-center space-x-2">
                    <FaCheckCircle className="text-green-600 dark:text-green-400" />
                    <span className="text-green-700 dark:text-green-300 text-sm">{success}</span>
                  </div>
                </motion.div>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                {/* Client ID */}
                <div className="space-y-2">
                  <label className="flex items-center space-x-2 text-sm font-medium">
                    <FaIdCard className="text-primary" />
                    <span>Azure Client ID</span>
                  </label>
                  <input
                    type="text"
                    name="clientId"
                    value={formData.clientId}
                    onChange={handleInputChange}
                    placeholder="Enter your Azure Client ID"
                    className="w-full px-4 py-3 border border-border rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary bg-background transition-colors"
                    required
                  />
                  <p className="text-xs text-muted-foreground">
                    The Application (client) ID from your Azure AD app registration
                  </p>
                </div>

                {/* Tenant ID */}
                <div className="space-y-2">
                  <label className="flex items-center space-x-2 text-sm font-medium">
                    <FaBuilding className="text-primary" />
                    <span>Azure Tenant ID</span>
                  </label>
                  <input
                    type="text"
                    name="tenantId"
                    value={formData.tenantId}
                    onChange={handleInputChange}
                    placeholder="Enter your Azure Tenant ID"
                    className="w-full px-4 py-3 border border-border rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary bg-background transition-colors"
                    required
                  />
                  <p className="text-xs text-muted-foreground">
                    The Directory (tenant) ID from your Azure AD
                  </p>
                </div>

                {/* Client Secret */}
                <div className="space-y-2">
                  <label className="flex items-center space-x-2 text-sm font-medium">
                    <FaKey className="text-primary" />
                    <span>Azure Client Secret</span>
                  </label>
                  <div className="relative">
                    <input
                      type={showSecret ? "text" : "password"}
                      name="clientSecret"
                      value={formData.clientSecret}
                      onChange={handleInputChange}
                      placeholder="Enter your Azure Client Secret"
                      className="w-full px-4 py-3 pr-12 border border-border rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary bg-background transition-colors"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowSecret(!showSecret)}
                      className="absolute right-3 top-1/2 transform -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                    >
                      {showSecret ? <FaEyeSlash /> : <FaEye />}
                    </button>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    The client secret from your Azure AD app registration
                  </p>
                </div>

                {/* Submit Button */}
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  type="submit"
                  disabled={isLoading}
                  className="w-full flex items-center justify-center space-x-2 px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                >
                  {isLoading ? (
                    <>
                      <FaSpinner className="animate-spin" />
                      <span>Connecting...</span>
                    </>
                  ) : (
                    <>
                      <FaSave />
                      <span>Connect to Azure AD</span>
                    </>
                  )}
                </motion.button>
              </form>
            </motion.div>
          </div>
        )}

        {/* Connection Status & Info */}
        <div className="space-y-6">
          {/* Connection Status */}
          <motion.div
            whileHover={{ scale: 1.01 }}
            className="p-6 bg-card rounded-xl shadow-lg border border-border"
          >
            <div className="flex items-center space-x-3 mb-4">
              <FaShieldAlt className="text-xl text-primary" />
              <h3 className="text-lg font-semibold">Connection Status</h3>
            </div>
            
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Status</span>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  isConnected 
                    ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400' 
                    : 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400'
                }`}>
                  {statusLoading ? 'Checking…' : (isConnected ? 'Connected' : 'Not Connected')}
                </span>
              </div>
              
              {isConnected && (
                <motion.button
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={handleDisconnect}
                  disabled={isLoading}
                  className="w-full px-4 py-2 border border-destructive text-destructive rounded-lg hover:bg-destructive/10 disabled:opacity-50 transition-colors"
                >
                  Disconnect
                </motion.button>
              )}
            </div>
          </motion.div>

          {/* Help Information */}
          <motion.div
            whileHover={{ scale: 1.01 }}
            className="p-6 bg-card rounded-xl shadow-lg border border-border"
          >
            <div className="flex items-center space-x-3 mb-4">
              <FaQuestionCircle className="text-xl text-primary" />
              <h3 className="text-lg font-semibold">How to Get Credentials</h3>
            </div>
            
            <div className="space-y-3 text-sm text-muted-foreground">
              <div className="space-y-2">
                <h4 className="font-medium text-foreground">1. Azure Portal</h4>
                <p>Go to Azure Portal → Azure Active Directory → App registrations</p>
              </div>
              
              <div className="space-y-2">
                <h4 className="font-medium text-foreground">2. Create App</h4>
                <p>Create a new app registration or use an existing one</p>
              </div>
              
              <div className="space-y-2">
                <h4 className="font-medium text-foreground">3. Get Credentials</h4>
                <p>Copy the Application ID, Tenant ID, and create a client secret</p>
              </div>
              
              <div className="space-y-2">
                <h4 className="font-medium text-foreground">4. Permissions</h4>
                <p>Ensure the app has necessary permissions for compliance scanning</p>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </motion.div>
    {showDisconnectModal && (
      <div className="fixed inset-0 z-50 flex items-center justify-center">
        <div className="absolute inset-0 bg-black/50" onClick={cancelDisconnect} />
        <div className="relative z-10 w-full max-w-md p-6 bg-card rounded-xl shadow-xl border border-border">
          <div className="flex items-center space-x-3 mb-4">
            <FaExclamationTriangle className="text-destructive" />
            <h3 className="text-lg font-semibold">Disconnect Azure AD</h3>
          </div>
          <p className="text-sm text-muted-foreground mb-6">Are you sure you want to disconnect your Azure Active Directory integration? This will disable Azure-related features until reconnected.</p>
          <div className="flex justify-end space-x-3">
            <button
              onClick={cancelDisconnect}
              className="px-4 py-2 rounded-lg border border-border hover:bg-secondary"
            >
              Cancel
            </button>
            <button
              onClick={confirmDisconnect}
              disabled={isLoading}
              className="px-4 py-2 rounded-lg bg-destructive text-white hover:bg-red-600 disabled:opacity-50"
            >
              {isLoading ? 'Disconnecting…' : 'Disconnect'}
            </button>
          </div>
        </div>
      </div>
    )}
    </>
  );
};

const AzureComplianceReportsList = () => {
  const { authToken } = useAuth();
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const reportsPerPage = 5;

  // Fetch reports
  useEffect(() => {
    const fetchReports = async () => {
      try {
        setLoading(true);
        const headers = authToken ? { 'Authorization': `Bearer ${authToken}` } : {};
        const response = await fetch(buildApiUrl('/api/azure-checker/results'), { headers });
        
        if (!response.ok) {
          throw new Error('Failed to fetch reports');
        }
        
        const data = await response.json();
        if (data.status === 'success' && data.results) {
          setReports(data.results);
        } else {
          setReports([]);
        }
        setError(null);
      } catch (err) {
        console.error('Error fetching Azure compliance reports:', err);
        setError(err.message);
        setReports([]);
      } finally {
        setLoading(false);
      }
    };

    if (authToken) {
      fetchReports();
    }
  }, [authToken]);
  
  // Calculate total pages for pagination reset check
  const totalPagesForReset = Math.ceil(reports.length / reportsPerPage);
  
  // Reset to page 1 if current page is out of bounds
  useEffect(() => {
    if (currentPage > totalPagesForReset && totalPagesForReset > 0) {
      setCurrentPage(1);
    }
  }, [currentPage, totalPagesForReset]);

  const handleDownloadReport = async (resultId) => {
    try {
      const headers = authToken ? { 'Authorization': `Bearer ${authToken}` } : {};
      const reportResp = await fetch(buildApiUrl(`/api/azure-checker/generate-report/${resultId}`), {
        headers,
        method: 'GET'
      });
      
      if (!reportResp.ok) {
        throw new Error('Failed to generate report');
      }
      
      // Download the PDF
      const blob = await reportResp.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const report = reports.find(r => r._id === resultId || r.id === resultId);
      const dateStr = report?.created_at 
        ? new Date(report.created_at).toISOString().split('T')[0]
        : new Date().toISOString().split('T')[0];
      a.download = `Azure_Compliance_Report_${dateStr}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Error downloading report:', error);
      alert(`Error downloading report: ${error.message}`);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown';
    try {
      const date = new Date(dateString);
      return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return 'Unknown';
    }
  };

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'compliant':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'partial':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'non-compliant':
        return 'text-red-600 bg-red-50 border-red-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  if (loading) {
    return (
      <div className="mb-6 p-4 bg-card rounded-lg border">
        <div className="flex items-center justify-center py-4">
          <FaSpinner className="animate-spin text-primary mr-2" />
          <span className="text-muted-foreground">Loading Azure compliance reports...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mb-6 p-4 bg-card rounded-lg border border-destructive">
        <p className="text-destructive">Error loading reports: {error}</p>
      </div>
    );
  }

  if (reports.length === 0) {
    return (
      <div className="mb-6 p-4 bg-card rounded-lg border">
        <h4 className="text-sm font-semibold mb-2 text-muted-foreground">Azure Compliance Reports</h4>
        <p className="text-sm text-muted-foreground">No Azure compliance reports available. Analyze a document in the Azure Compliance Checker to generate reports.</p>
      </div>
    );
  }

  // Calculate pagination (moved after hooks)
  const totalPages = Math.ceil(reports.length / reportsPerPage);
  const startIndex = (currentPage - 1) * reportsPerPage;
  const endIndex = startIndex + reportsPerPage;
  const currentReports = reports.slice(startIndex, endIndex);

  const handlePreviousPage = () => {
    if (currentPage > 1) {
      setCurrentPage(currentPage - 1);
    }
  };

  const handleNextPage = () => {
    if (currentPage < totalPages) {
      setCurrentPage(currentPage + 1);
    }
  };

  const handlePageClick = (page) => {
    setCurrentPage(page);
  };

  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-foreground">Azure Compliance Reports</h4>
        <span className="text-xs text-muted-foreground">
          Showing {startIndex + 1}-{Math.min(endIndex, reports.length)} of {reports.length}
        </span>
      </div>
      <div className="space-y-2">
        {currentReports.map((report) => (
          <div
            key={report._id || report.id}
            className="flex items-center justify-between p-3 bg-card rounded-lg border hover:shadow-md transition-shadow"
          >
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <FaCloud className="text-blue-500" />
                <span className="font-medium text-sm truncate">{report.document_name || 'Unknown Document'}</span>
              </div>
              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                <span>Score: {report.score || report.overall_score || 0}/100</span>
                <span className={`px-2 py-0.5 rounded-full border text-xs font-medium ${getStatusColor(report.overall_status)}`}>
                  {report.overall_status || 'Unknown'}
                </span>
                <span>{formatDate(report.created_at || report.analyzed_at)}</span>
              </div>
            </div>
            <button
              onClick={() => handleDownloadReport(report._id || report.id)}
              className="ml-4 inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-colors text-sm"
            >
              <FaFilePdf />
              <span>Download</span>
            </button>
          </div>
        ))}
      </div>
      
      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-4">
          <button
            onClick={handlePreviousPage}
            disabled={currentPage === 1}
            className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm transition-colors ${
              currentPage === 1
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            <FaChevronLeft />
            <span>Previous</span>
          </button>
          
          <div className="flex items-center gap-1">
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => {
              // Show first page, last page, current page, and pages around current
              if (
                page === 1 ||
                page === totalPages ||
                (page >= currentPage - 1 && page <= currentPage + 1)
              ) {
                return (
                  <button
                    key={page}
                    onClick={() => handlePageClick(page)}
                    className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                      currentPage === page
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                    }`}
                  >
                    {page}
                  </button>
                );
              } else if (page === currentPage - 2 || page === currentPage + 2) {
                return <span key={page} className="px-2 text-gray-400">...</span>;
              }
              return null;
            })}
          </div>
          
          <button
            onClick={handleNextPage}
            disabled={currentPage === totalPages}
            className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm transition-colors ${
              currentPage === totalPages
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            <span>Next</span>
            <FaChevronRight />
          </button>
        </div>
      )}
    </div>
  );
};

const ComplianceLogs = () => {
  const { authToken } = useAuth();
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [summary, setSummary] = useState({
    today: { analyses: 0, uploads: 0, config_fetches: 0, checklists: 0, total: 0 },
    this_week: { analyses: 0, uploads: 0, config_fetches: 0, checklists: 0, total: 0 }
  });
  const [totalLogs, setTotalLogs] = useState(0);
  const [filters, setFilters] = useState({
    startDate: '',
    endDate: '',
    activityType: '',
    status: ''
  });
  const [currentPage, setCurrentPage] = useState(1);
  const logsPerPage = 20;

  useEffect(() => {
    fetchLogs();
  }, [authToken, filters, currentPage]);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params = new URLSearchParams({
        limit: logsPerPage.toString(),
        skip: ((currentPage - 1) * logsPerPage).toString()
      });
      
      if (filters.startDate) params.append('start_date', filters.startDate);
      if (filters.endDate) params.append('end_date', filters.endDate);
      if (filters.activityType) params.append('activity_type', filters.activityType);
      if (filters.status) params.append('status', filters.status);
      
      const response = await fetch(buildApiUrl(`/api/compliance/compliance-logs?${params}`), {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch logs');
      }
      
      const data = await response.json();
      setLogs(data.logs || []);
      setSummary(data.summary || summary);
      setTotalLogs(data.total || 0);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (field, value) => {
    setFilters(prev => ({ ...prev, [field]: value }));
    setCurrentPage(1);
  };

  const formatTimestamp = (timestamp) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return timestamp;
    }
  };

  const getStatusBadge = (status) => {
    const statusConfig = {
      success: { bg: 'bg-green-100 dark:bg-green-900/20', text: 'text-green-800 dark:text-green-400', icon: <FaCheckCircle /> },
      warning: { bg: 'bg-yellow-100 dark:bg-yellow-900/20', text: 'text-yellow-800 dark:text-yellow-400', icon: <FaExclamationTriangle /> },
      failed: { bg: 'bg-red-100 dark:bg-red-900/20', text: 'text-red-800 dark:text-red-400', icon: <FaExclamationTriangle /> }
    };
    const config = statusConfig[status] || statusConfig.success;
    return (
      <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${config.bg} ${config.text}`}>
        {config.icon}
        {status?.toUpperCase() || 'SUCCESS'}
      </span>
    );
  };

  const getActivityIcon = (icon) => {
    return <span className="text-2xl">{icon || '📋'}</span>;
  };

  const fetchAllLogsForExport = async () => {
    try {
      const params = new URLSearchParams({
        limit: '10000', // Large limit to get all logs
        skip: '0'
      });
      
      if (filters.startDate) params.append('start_date', filters.startDate);
      if (filters.endDate) params.append('end_date', filters.endDate);
      if (filters.activityType) params.append('activity_type', filters.activityType);
      if (filters.status) params.append('status', filters.status);
      
      const response = await fetch(buildApiUrl(`/api/compliance/compliance-logs?${params}`), {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch logs');
      }
      
      const data = await response.json();
      return data.logs || [];
    } catch (err) {
      console.error('Error fetching logs for export:', err);
      return [];
    }
  };

  const exportToCSV = async () => {
    try {
      const allLogs = await fetchAllLogsForExport();
      
      // CSV Headers
      const headers = ['Timestamp', 'Activity Type', 'Description', 'Status', 'Details'];
      
      // CSV Rows
      const rows = allLogs.map(log => {
        const timestamp = formatTimestamp(log.timestamp);
        const activityType = log.activity_label || log.activity_type || 'Unknown';
        const description = log.description || '';
        const status = log.status || 'unknown';
        const details = log.details ? JSON.stringify(log.details).replace(/"/g, '""') : '';
        
        return [
          `"${timestamp}"`,
          `"${activityType}"`,
          `"${description.replace(/"/g, '""')}"`,
          `"${status}"`,
          `"${details}"`
        ].join(',');
      });
      
      // Combine headers and rows
      const csvContent = [headers.join(','), ...rows].join('\n');
      
      // Create blob and download
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);
      link.setAttribute('href', url);
      link.setAttribute('download', `compliance_activity_logs_${new Date().toISOString().split('T')[0]}.csv`);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      console.error('Error exporting to CSV:', err);
      alert('Failed to export CSV. Please try again.');
    }
  };

  const exportToPDF = async () => {
    try {
      const allLogs = await fetchAllLogsForExport();
      
      const doc = new jsPDF('l', 'mm', 'a4'); // Landscape orientation
      
      // Add title
      doc.setFontSize(20);
      doc.setTextColor(40, 40, 40);
      doc.setFont('helvetica', 'bold');
      doc.text('Compliance Team Activity Logs Report', 14, 20);
      
      // Add subtitle with date range
      doc.setFontSize(12);
      doc.setTextColor(100, 100, 100);
      doc.setFont('helvetica', 'normal');
      const dateRange = filters.startDate && filters.endDate 
        ? `${filters.startDate} to ${filters.endDate}`
        : 'All Time';
      doc.text(`Report Period: ${dateRange}`, 14, 28);
      doc.text(`Generated: ${new Date().toLocaleString()}`, 14, 33);
      
      // Add summary section
      doc.setFontSize(14);
      doc.setTextColor(40, 40, 40);
      doc.setFont('helvetica', 'bold');
      doc.text('Summary', 14, 43);
      
      doc.setFontSize(10);
      doc.setTextColor(60, 60, 60);
      doc.setFont('helvetica', 'normal');
      doc.text(`Total Activities: ${allLogs.length}`, 14, 50);
      doc.text(`Today's Analyses: ${summary.today.analyses}`, 14, 55);
      doc.text(`Today's Uploads: ${summary.today.uploads}`, 14, 60);
      doc.text(`This Week Total: ${summary.this_week.total}`, 14, 65);
      
      // Helper function to format details in a readable way
      const formatDetails = (details) => {
        if (!details) return 'N/A';
        try {
          // Extract key information instead of showing raw JSON
          const parts = [];
          if (details.score !== undefined) parts.push(`Score: ${details.score}`);
          if (details.frameworks && Array.isArray(details.frameworks)) {
            parts.push(`Frameworks: ${details.frameworks.join(', ')}`);
          }
          if (details.filename) parts.push(`File: ${details.filename}`);
          if (details.doc_type) parts.push(`Type: ${details.doc_type}`);
          if (details.file_type) parts.push(`Format: ${details.file_type}`);
          
          // If we have extracted info, use it; otherwise format JSON compactly
          if (parts.length > 0) {
            return parts.join(' | ');
          }
          
          // For other details, show a compact version
          const jsonStr = JSON.stringify(details);
          if (jsonStr.length > 60) {
            return jsonStr.substring(0, 57) + '...';
          }
          return jsonStr;
        } catch {
          return String(details).substring(0, 60);
        }
      };
      
      // Prepare table data
      const tableData = allLogs.map(log => [
        formatTimestamp(log.timestamp),
        log.activity_label || log.activity_type || 'Unknown',
        (log.description || '').substring(0, 45) + (log.description?.length > 45 ? '...' : ''),
        log.status || 'unknown',
        formatDetails(log.details)
      ]);
      
      // Add table with proper column widths
      autoTable(doc, {
        head: [['Timestamp', 'Activity Type', 'Description', 'Status', 'Details']],
        body: tableData,
        startY: 72,
        columnStyles: {
          0: { cellWidth: 35, fontSize: 7 }, // Timestamp
          1: { cellWidth: 40, fontSize: 8 }, // Activity Type
          2: { cellWidth: 50, fontSize: 7 }, // Description
          3: { cellWidth: 25, fontSize: 8 }, // Status
          4: { cellWidth: 80, fontSize: 7, overflow: 'linebreak' } // Details - wider with linebreak
        },
        styles: {
          font: 'helvetica',
          fontSize: 8,
          cellPadding: 2,
          overflow: 'linebreak',
          cellWidth: 'wrap'
        },
        headStyles: {
          fillColor: [59, 130, 246],
          textColor: 255,
          fontStyle: 'bold',
          font: 'helvetica',
        },
        alternateRowStyles: {
          fillColor: [245, 247, 250],
        },
        margin: { top: 72, left: 14, right: 14 },
        tableWidth: 'auto',
      });
      
      // Add footer
      const pageCount = doc.internal.getNumberOfPages();
      for (let i = 1; i <= pageCount; i++) {
        doc.setPage(i);
        doc.setFontSize(8);
        doc.setTextColor(150, 150, 150);
        doc.setFont('helvetica', 'normal');
        doc.text(
          `Page ${i} of ${pageCount} - Complytics Activity Logs`,
          doc.internal.pageSize.getWidth() / 2,
          doc.internal.pageSize.getHeight() - 10,
          { align: 'center' }
        );
      }
      
      // Save PDF
      doc.save(`compliance_activity_logs_${new Date().toISOString().split('T')[0]}.pdf`);
    } catch (err) {
      console.error('Error exporting to PDF:', err);
      alert('Failed to export PDF. Please try again.');
    }
  };

  const totalPages = Math.ceil(totalLogs / logsPerPage);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-4">
          <motion.div
            whileHover={{ scale: 1.1, rotate: 5 }}
            className="p-3 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl shadow-lg"
          >
            <FaClipboardList className="text-2xl text-white" />
          </motion.div>
          <div>
            <h2 className="text-3xl font-bold text-foreground">My Activity Logs</h2>
            <p className="text-muted-foreground">Track your compliance activities and analyses</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={exportToCSV}
            className="flex items-center gap-2 px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg shadow-md transition-colors"
            title="Export to CSV"
          >
            <FaFileCsv />
            <span className="hidden sm:inline">Export CSV</span>
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={exportToPDF}
            className="flex items-center gap-2 px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg shadow-md transition-colors"
            title="Export to PDF"
          >
            <FaFilePdf />
            <span className="hidden sm:inline">Export PDF</span>
          </motion.button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          whileHover={{ scale: 1.02, y: -2 }}
          className="p-5 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl shadow-lg text-white"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium opacity-90">Today's Analyses</span>
            <FaCloud className="text-xl opacity-80" />
          </div>
          <p className="text-3xl font-bold">{summary.today.analyses}</p>
          <p className="text-xs opacity-75 mt-1">This week: {summary.this_week.analyses}</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          whileHover={{ scale: 1.02, y: -2 }}
          className="p-5 bg-gradient-to-br from-green-500 to-green-600 rounded-xl shadow-lg text-white"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium opacity-90">Today's Uploads</span>
            <FaFileAlt className="text-xl opacity-80" />
          </div>
          <p className="text-3xl font-bold">{summary.today.uploads}</p>
          <p className="text-xs opacity-75 mt-1">This week: {summary.this_week.uploads}</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          whileHover={{ scale: 1.02, y: -2 }}
          className="p-5 bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl shadow-lg text-white"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium opacity-90">Today's Checklists</span>
            <FaListAlt className="text-xl opacity-80" />
          </div>
          <p className="text-3xl font-bold">{summary.today.checklists || 0}</p>
          <p className="text-xs opacity-75 mt-1">This week: {summary.this_week.checklists || 0}</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          whileHover={{ scale: 1.02, y: -2 }}
          className="p-5 bg-gradient-to-br from-orange-500 to-orange-600 rounded-xl shadow-lg text-white"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium opacity-90">Total Activities</span>
            <FaChartBar className="text-xl opacity-80" />
          </div>
          <p className="text-3xl font-bold">{summary.today.total}</p>
          <p className="text-xs opacity-75 mt-1">This week: {summary.this_week.total}</p>
        </motion.div>
      </div>

      {/* Filters */}
      <div className="bg-card rounded-lg border border-border p-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium mb-2">Start Date</label>
            <input
              type="date"
              value={filters.startDate}
              onChange={(e) => handleFilterChange('startDate', e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-border bg-background"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">End Date</label>
            <input
              type="date"
              value={filters.endDate}
              onChange={(e) => handleFilterChange('endDate', e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-border bg-background"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Activity Type</label>
            <select
              value={filters.activityType}
              onChange={(e) => handleFilterChange('activityType', e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-border bg-background"
            >
              <option value="">All Activities</option>
              <option value="azure_analysis">Azure Analysis</option>
              <option value="document_upload">Document Upload</option>
              <option value="azure_config_fetch">Azure Config Fetch</option>
              <option value="checklist_generation">Checklist Generation</option>
              <option value="ui_testing">UI Testing</option>
              <option value="schedule_scan">Schedule Scan</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Status</label>
            <select
              value={filters.status}
              onChange={(e) => handleFilterChange('status', e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-border bg-background"
            >
              <option value="">All Status</option>
              <option value="success">Success</option>
              <option value="warning">Warning</option>
              <option value="failed">Failed</option>
            </select>
          </div>
        </div>
      </div>

      {/* Logs Table */}
      {loading ? (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      ) : error ? (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <p className="text-red-800 dark:text-red-400">{error}</p>
        </div>
      ) : logs.length === 0 ? (
        <div className="bg-card rounded-lg border border-border p-12 text-center">
          <FaInbox className="text-4xl text-muted-foreground mx-auto mb-4" />
          <p className="text-muted-foreground">No activity logs found</p>
        </div>
      ) : (
        <>
          <div className="bg-card rounded-lg border border-border overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-secondary">
                  <tr>
                    <th className="p-3 text-left text-sm font-semibold">Activity</th>
                    <th className="p-3 text-left text-sm font-semibold">Description</th>
                    <th className="p-3 text-left text-sm font-semibold">Status</th>
                    <th className="p-3 text-left text-sm font-semibold">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log, index) => (
                    <motion.tr
                      key={log.id || index}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.05 }}
                      className="border-b border-border hover:bg-secondary/50 transition-colors"
                    >
                      <td className="p-3">
                        <div className="flex items-center gap-3">
                          {getActivityIcon(log.icon)}
                          <span className="font-medium text-sm">{log.activity_label}</span>
                        </div>
                      </td>
                      <td className="p-3 text-sm text-muted-foreground">
                        <div>
                          <p>{log.description}</p>
                          {log.details && (
                            <div className="mt-1 text-xs space-y-1">
                              {log.details.score && (
                                <span className="inline-block px-2 py-0.5 bg-blue-100 dark:bg-blue-900/20 text-blue-800 dark:text-blue-400 rounded mr-2">
                                  Score: {log.details.score}/100
                                </span>
                              )}
                              {log.details.frameworks && log.details.frameworks.length > 0 && (
                                <span className="inline-block px-2 py-0.5 bg-purple-100 dark:bg-purple-900/20 text-purple-800 dark:text-purple-400 rounded">
                                  {log.details.frameworks.join(', ')}
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                      </td>
                      <td className="p-3">{getStatusBadge(log.status)}</td>
                      <td className="p-3 text-sm text-muted-foreground">
                        {formatTimestamp(log.timestamp)}
                      </td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          
          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                Showing {((currentPage - 1) * logsPerPage) + 1} to {Math.min(currentPage * logsPerPage, totalLogs)} of {totalLogs} logs
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                  disabled={currentPage === 1}
                  className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                    currentPage === 1
                      ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                >
                  <FaChevronLeft />
                  <span>Previous</span>
                </button>
                <span className="px-3 py-1.5 text-sm">
                  Page {currentPage} of {totalPages}
                </span>
                <button
                  onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                  disabled={currentPage === totalPages}
                  className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                    currentPage === totalPages
                      ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                >
                  <span>Next</span>
                  <FaChevronRight />
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </motion.div>
  );
};

const ManagementLogs = () => {
  const { authToken } = useAuth();
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [summary, setSummary] = useState({
    today: { scans: 0, analyses: 0, reports: 0, uploads: 0, checklists: 0 },
    this_week: { scans: 0, analyses: 0, reports: 0, uploads: 0, checklists: 0 }
  });
  const [totalLogs, setTotalLogs] = useState(0);
  const [filters, setFilters] = useState({
    startDate: '',
    endDate: '',
    activityType: '',
    teamMember: '',
    status: ''
  });
  const [currentPage, setCurrentPage] = useState(1);
  const logsPerPage = 20;

  useEffect(() => {
    fetchLogs();
  }, [authToken, filters, currentPage]);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params = new URLSearchParams({
        limit: logsPerPage.toString(),
        skip: ((currentPage - 1) * logsPerPage).toString()
      });
      
      if (filters.startDate) params.append('start_date', filters.startDate);
      if (filters.endDate) params.append('end_date', filters.endDate);
      if (filters.activityType) params.append('activity_type', filters.activityType);
      if (filters.teamMember) params.append('team_member', filters.teamMember);
      if (filters.status) params.append('status', filters.status);
      
      const response = await fetch(buildApiUrl(`/api/compliance/management-logs?${params}`), {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch logs');
      }
      
      const data = await response.json();
      setLogs(data.logs || []);
      setSummary(data.summary || summary);
      setTotalLogs(data.total || 0);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (field, value) => {
    setFilters(prev => ({ ...prev, [field]: value }));
    setCurrentPage(1);
  };

  const formatTimestamp = (timestamp) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return timestamp;
    }
  };

  const getStatusBadge = (status) => {
    const statusConfig = {
      success: { bg: 'bg-green-100 dark:bg-green-900/20', text: 'text-green-800 dark:text-green-400', icon: <FaCheckCircle /> },
      warning: { bg: 'bg-yellow-100 dark:bg-yellow-900/20', text: 'text-yellow-800 dark:text-yellow-400', icon: <FaExclamationTriangle /> },
      failed: { bg: 'bg-red-100 dark:bg-red-900/20', text: 'text-red-800 dark:text-red-400', icon: <FaExclamationTriangle /> }
    };
    const config = statusConfig[status] || statusConfig.success;
    return (
      <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${config.bg} ${config.text}`}>
        {config.icon}
        {status?.toUpperCase() || 'SUCCESS'}
      </span>
    );
  };

  const getActivityIcon = (icon) => {
    return <span className="text-2xl">{icon || '📋'}</span>;
  };

  const getRoleBadge = (role) => {
    const roleConfig = {
      compliance_team: { bg: 'bg-blue-100 dark:bg-blue-900/20', text: 'text-blue-800 dark:text-blue-400' },
      it_team: { bg: 'bg-purple-100 dark:bg-purple-900/20', text: 'text-purple-800 dark:text-purple-400' }
    };
    const config = roleConfig[role] || { bg: 'bg-gray-100 dark:bg-gray-900/20', text: 'text-gray-800 dark:text-gray-400' };
    return (
      <span className={`px-2 py-0.5 rounded text-xs font-medium ${config.bg} ${config.text}`}>
        {role?.replace('_', ' ').toUpperCase() || 'UNKNOWN'}
      </span>
    );
  };

  const fetchAllLogsForExport = async () => {
    try {
      const params = new URLSearchParams({
        limit: '10000', // Large limit to get all logs
        skip: '0'
      });
      
      if (filters.startDate) params.append('start_date', filters.startDate);
      if (filters.endDate) params.append('end_date', filters.endDate);
      if (filters.activityType) params.append('activity_type', filters.activityType);
      if (filters.teamMember) params.append('team_member', filters.teamMember);
      if (filters.status) params.append('status', filters.status);
      
      const response = await fetch(buildApiUrl(`/api/compliance/management-logs?${params}`), {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch logs');
      }
      
      const data = await response.json();
      return data.logs || [];
    } catch (err) {
      console.error('Error fetching logs for export:', err);
      return [];
    }
  };

  const exportToCSV = async () => {
    try {
      const allLogs = await fetchAllLogsForExport();
      
      // CSV Headers
      const headers = ['Timestamp', 'Activity Type', 'Description', 'User Email', 'User Role', 'Status', 'Details'];
      
      // CSV Rows
      const rows = allLogs.map(log => {
        const timestamp = formatTimestamp(log.timestamp);
        const activityType = log.activity_label || log.activity_type || 'Unknown';
        const description = log.description || '';
        const userEmail = log.user_email || 'Unknown';
        const userRole = log.user_role || 'Unknown';
        const status = log.status || 'unknown';
        const details = log.details ? JSON.stringify(log.details).replace(/"/g, '""') : '';
        
        return [
          `"${timestamp}"`,
          `"${activityType}"`,
          `"${description.replace(/"/g, '""')}"`,
          `"${userEmail}"`,
          `"${userRole}"`,
          `"${status}"`,
          `"${details}"`
        ].join(',');
      });
      
      // Combine headers and rows
      const csvContent = [headers.join(','), ...rows].join('\n');
      
      // Create blob and download
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);
      link.setAttribute('href', url);
      link.setAttribute('download', `management_activity_logs_${new Date().toISOString().split('T')[0]}.csv`);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      console.error('Error exporting to CSV:', err);
      alert('Failed to export CSV. Please try again.');
    }
  };

  const exportToPDF = async () => {
    try {
      const allLogs = await fetchAllLogsForExport();
      
      const doc = new jsPDF('l', 'mm', 'a4'); // Landscape orientation
      
      // Add title
      doc.setFontSize(20);
      doc.setTextColor(40, 40, 40);
      doc.setFont('helvetica', 'bold');
      doc.text('Management Team Activity Logs Report', 14, 20);
      
      // Add subtitle with date range
      doc.setFontSize(12);
      doc.setTextColor(100, 100, 100);
      doc.setFont('helvetica', 'normal');
      const dateRange = filters.startDate && filters.endDate 
        ? `${filters.startDate} to ${filters.endDate}`
        : 'All Time';
      doc.text(`Report Period: ${dateRange}`, 14, 28);
      doc.text(`Generated: ${new Date().toLocaleString()}`, 14, 33);
      
      // Add summary section
      doc.setFontSize(14);
      doc.setTextColor(40, 40, 40);
      doc.setFont('helvetica', 'bold');
      doc.text('Summary', 14, 43);
      
      doc.setFontSize(10);
      doc.setTextColor(60, 60, 60);
      doc.setFont('helvetica', 'normal');
      doc.text(`Total Activities: ${allLogs.length}`, 14, 50);
      doc.text(`Today's Scans: ${summary.today.scans}`, 14, 55);
      doc.text(`Today's Analyses: ${summary.today.analyses}`, 14, 60);
      doc.text(`Today's Uploads: ${summary.today.uploads}`, 14, 65);
      doc.text(`This Week Total: ${summary.this_week.scans + summary.this_week.analyses + summary.this_week.uploads}`, 14, 70);
      
      // Helper function to format details in a readable way
      const formatDetails = (details) => {
        if (!details) return 'N/A';
        try {
          // Extract key information instead of showing raw JSON
          const parts = [];
          if (details.score !== undefined) parts.push(`Score: ${details.score}`);
          if (details.frameworks && Array.isArray(details.frameworks)) {
            parts.push(`Frameworks: ${details.frameworks.join(', ')}`);
          }
          if (details.filename) parts.push(`File: ${details.filename}`);
          if (details.doc_type) parts.push(`Type: ${details.doc_type}`);
          if (details.file_type) parts.push(`Format: ${details.file_type}`);
          if (details.url) parts.push(`URL: ${details.url}`);
          if (details.scan_type) parts.push(`Scan: ${details.scan_type}`);
          
          // If we have extracted info, use it; otherwise format JSON compactly
          if (parts.length > 0) {
            return parts.join(' | ');
          }
          
          // For other details, show a compact version
          const jsonStr = JSON.stringify(details);
          if (jsonStr.length > 50) {
            return jsonStr.substring(0, 47) + '...';
          }
          return jsonStr;
        } catch {
          return String(details).substring(0, 50);
        }
      };
      
      // Prepare table data
      const tableData = allLogs.map(log => [
        formatTimestamp(log.timestamp),
        log.activity_label || log.activity_type || 'Unknown',
        (log.description || '').substring(0, 35) + (log.description?.length > 35 ? '...' : ''),
        (log.user_email || 'Unknown').substring(0, 25) + ((log.user_email || '').length > 25 ? '...' : ''),
        log.user_role ? log.user_role.replace('_', ' ') : 'Unknown',
        log.status || 'unknown',
        formatDetails(log.details)
      ]);
      
      // Add table with proper column widths
      autoTable(doc, {
        head: [['Timestamp', 'Activity Type', 'Description', 'User Email', 'User Role', 'Status', 'Details']],
        body: tableData,
        startY: 77,
        columnStyles: {
          0: { cellWidth: 30, fontSize: 6 }, // Timestamp
          1: { cellWidth: 35, fontSize: 7 }, // Activity Type
          2: { cellWidth: 40, fontSize: 6 }, // Description
          3: { cellWidth: 35, fontSize: 6 }, // User Email
          4: { cellWidth: 25, fontSize: 7 }, // User Role
          5: { cellWidth: 20, fontSize: 7 }, // Status
          6: { cellWidth: 70, fontSize: 6, overflow: 'linebreak' } // Details - wider with linebreak
        },
        styles: {
          font: 'helvetica',
          fontSize: 7,
          cellPadding: 2,
          overflow: 'linebreak',
          cellWidth: 'wrap'
        },
        headStyles: {
          fillColor: [147, 51, 234], // Purple color for management
          textColor: 255,
          fontStyle: 'bold',
          font: 'helvetica',
        },
        alternateRowStyles: {
          fillColor: [245, 247, 250],
        },
        margin: { top: 77, left: 14, right: 14 },
        tableWidth: 'auto',
      });
      
      // Add footer
      const pageCount = doc.internal.getNumberOfPages();
      for (let i = 1; i <= pageCount; i++) {
        doc.setPage(i);
        doc.setFontSize(8);
        doc.setTextColor(150, 150, 150);
        doc.setFont('helvetica', 'normal');
        doc.text(
          `Page ${i} of ${pageCount} - Complytics Management Activity Logs`,
          doc.internal.pageSize.getWidth() / 2,
          doc.internal.pageSize.getHeight() - 10,
          { align: 'center' }
        );
      }
      
      // Save PDF
      doc.save(`management_activity_logs_${new Date().toISOString().split('T')[0]}.pdf`);
    } catch (err) {
      console.error('Error exporting to PDF:', err);
      alert('Failed to export PDF. Please try again.');
    }
  };

  const totalPages = Math.ceil(totalLogs / logsPerPage);
  const startIndex = (currentPage - 1) * logsPerPage;
  const endIndex = Math.min(startIndex + logsPerPage, totalLogs);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-4">
          <motion.div
            whileHover={{ scale: 1.1, rotate: 5 }}
            className="p-3 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl shadow-lg"
          >
            <FaClipboardList className="text-2xl text-white" />
          </motion.div>
          <div>
            <h2 className="text-3xl font-bold text-foreground">Activity Logs</h2>
            <p className="text-muted-foreground">Monitor compliance and IT team activities across your organization</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={exportToCSV}
            className="flex items-center gap-2 px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg shadow-md transition-colors"
            title="Export to CSV"
          >
            <FaFileCsv />
            <span className="hidden sm:inline">Export CSV</span>
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={exportToPDF}
            className="flex items-center gap-2 px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg shadow-md transition-colors"
            title="Export to PDF"
          >
            <FaFilePdf />
            <span className="hidden sm:inline">Export PDF</span>
          </motion.button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          whileHover={{ scale: 1.02, y: -2 }}
          className="p-5 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl shadow-lg text-white"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium opacity-90">Today's Scans</span>
            <FaDesktop className="text-xl opacity-80" />
          </div>
          <p className="text-3xl font-bold">{summary.today.scans}</p>
          <p className="text-xs opacity-75 mt-1">This week: {summary.this_week.scans}</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          whileHover={{ scale: 1.02, y: -2 }}
          className="p-5 bg-gradient-to-br from-green-500 to-green-600 rounded-xl shadow-lg text-white"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium opacity-90">Today's Analyses</span>
            <FaCloud className="text-xl opacity-80" />
          </div>
          <p className="text-3xl font-bold">{summary.today.analyses}</p>
          <p className="text-xs opacity-75 mt-1">This week: {summary.this_week.analyses}</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          whileHover={{ scale: 1.02, y: -2 }}
          className="p-5 bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl shadow-lg text-white"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium opacity-90">Today's Uploads</span>
            <FaFileAlt className="text-xl opacity-80" />
          </div>
          <p className="text-3xl font-bold">{summary.today.uploads}</p>
          <p className="text-xs opacity-75 mt-1">This week: {summary.this_week.uploads}</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          whileHover={{ scale: 1.02, y: -2 }}
          className="p-5 bg-gradient-to-br from-orange-500 to-orange-600 rounded-xl shadow-lg text-white"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium opacity-90">Total Activities</span>
            <FaChartBar className="text-xl opacity-80" />
          </div>
          <p className="text-3xl font-bold">{summary.today.scans + summary.today.analyses + summary.today.uploads}</p>
          <p className="text-xs opacity-75 mt-1">This week: {summary.this_week.scans + summary.this_week.analyses + summary.this_week.uploads}</p>
        </motion.div>
      </div>

      {/* Filters */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="p-6 bg-card rounded-xl shadow-lg border border-border"
      >
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <FaSearch className="text-primary" />
          Filters
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">Start Date</label>
            <input
              type="date"
              value={filters.startDate}
              onChange={(e) => handleFilterChange('startDate', e.target.value)}
              className="w-full px-4 py-2.5 border border-border rounded-lg focus:ring-2 focus:ring-primary/30 focus:border-primary bg-background transition-all duration-200"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">End Date</label>
            <input
              type="date"
              value={filters.endDate}
              onChange={(e) => handleFilterChange('endDate', e.target.value)}
              className="w-full px-4 py-2.5 border border-border rounded-lg focus:ring-2 focus:ring-primary/30 focus:border-primary bg-background transition-all duration-200"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">Activity Type</label>
            <select
              value={filters.activityType}
              onChange={(e) => handleFilterChange('activityType', e.target.value)}
              className="w-full px-4 py-2.5 border border-border rounded-lg focus:ring-2 focus:ring-primary/30 focus:border-primary bg-background appearance-none cursor-pointer transition-all duration-200"
            >
              <option value="">All Activities</option>
              <option value="azure_analysis">Azure Analysis</option>
              <option value="ui_scan">UI Scan</option>
              <option value="document_upload">Document Upload</option>
              <option value="checklist_generation">Checklist Generation</option>
            </select>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">Status</label>
            <select
              value={filters.status}
              onChange={(e) => handleFilterChange('status', e.target.value)}
              className="w-full px-4 py-2.5 border border-border rounded-lg focus:ring-2 focus:ring-primary/30 focus:border-primary bg-background appearance-none cursor-pointer transition-all duration-200"
            >
              <option value="">All Statuses</option>
              <option value="success">Success</option>
              <option value="warning">Warning</option>
              <option value="failed">Failed</option>
            </select>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">Team Member</label>
            <input
              type="email"
              value={filters.teamMember}
              onChange={(e) => handleFilterChange('teamMember', e.target.value)}
              placeholder="Filter by email address"
              className="w-full px-4 py-2.5 border border-border rounded-lg focus:ring-2 focus:ring-primary/30 focus:border-primary bg-background transition-all duration-200"
            />
          </div>
        </div>
        <div className="mt-4 flex justify-end">
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => {
              setFilters({
                startDate: '',
                endDate: '',
                activityType: '',
                teamMember: '',
                status: ''
              });
              setCurrentPage(1);
            }}
            className="px-6 py-2 border border-border rounded-lg hover:bg-secondary transition-all duration-200"
          >
            Clear Filters
          </motion.button>
        </div>
      </motion.div>

      {/* Logs Timeline */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
        className="p-6 bg-card rounded-xl shadow-lg border border-border"
      >
        {loading ? (
          <div className="flex items-center justify-center p-12">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
            >
              <FaSpinner className="text-4xl text-primary" />
            </motion.div>
          </div>
        ) : error ? (
          <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-lg">
            <div className="flex items-center space-x-2">
              <FaExclamationTriangle className="text-destructive" />
              <span className="text-destructive">{error}</span>
            </div>
          </div>
        ) : logs.length === 0 ? (
          <div className="text-center p-12 text-muted-foreground">
            <motion.div
              animate={{ scale: [1, 1.1, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
            >
              <FaClipboardList className="text-6xl mx-auto mb-4 opacity-30" />
            </motion.div>
            <p className="text-lg font-medium">No activity logs found</p>
            <p className="text-sm mt-2">Activity logs will appear here as team members perform actions</p>
          </div>
        ) : (
          <>
            <div className="space-y-4">
              {logs.map((log, index) => (
                <motion.div
                  key={log.id || index}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05 }}
                  whileHover={{ scale: 1.01, x: 4 }}
                  className="p-4 bg-background rounded-lg border border-border hover:shadow-md transition-all duration-200"
                >
                  <div className="flex items-start gap-4">
                    <div className="flex-shrink-0 mt-1">
                      {getActivityIcon(log.icon)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-4 mb-2">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-semibold text-foreground">{log.activity_label}</span>
                            {getStatusBadge(log.status)}
                          </div>
                          <p className="text-sm text-muted-foreground mb-2">{log.description}</p>
                          <div className="flex items-center gap-3 text-xs text-muted-foreground flex-wrap">
                            <span className="flex items-center gap-1">
                              <FaUser className="text-primary" />
                              {log.user_email}
                            </span>
                            {getRoleBadge(log.user_role)}
                            <span className="flex items-center gap-1">
                              <FaClock className="text-primary" />
                              {formatTimestamp(log.timestamp)}
                            </span>
                          </div>
                        </div>
                      </div>
                      {log.details && (
                        <div className="mt-3 p-3 bg-secondary/50 rounded-lg border border-border">
                          <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
                            {Object.entries(log.details).map(([key, value]) => (
                              <div key={key}>
                                <span className="font-medium text-foreground">{key.replace('_', ' ').toUpperCase()}:</span>{' '}
                                <span className="text-muted-foreground">{String(value)}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
            
            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-6 pt-6 border-t border-border">
                <div className="text-sm text-muted-foreground">
                  Showing {startIndex + 1} to {endIndex} of {totalLogs} logs
                </div>
                <div className="flex items-center space-x-2">
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                    disabled={currentPage === 1}
                    className="px-4 py-2 border border-border rounded-lg hover:bg-secondary disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                  >
                    <FaChevronLeft />
                  </motion.button>
                  <span className="px-4 py-2 text-sm">
                    Page {currentPage} of {totalPages}
                  </span>
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                    disabled={currentPage >= totalPages}
                    className="px-4 py-2 border border-border rounded-lg hover:bg-secondary disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                  >
                    <FaChevronRight />
                  </motion.button>
                </div>
              </div>
            )}
          </>
        )}
      </motion.div>
    </motion.div>
  );
};

const UserDashboard = () => {
  const { user, authToken, logout } = useAuth();
  const navigate = useNavigate();
  const [userData, setUserData] = useState(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [error, setError] = useState(null);
  const reportRef = useRef(null);

  // Add event listener for setActiveTab event
  useEffect(() => {
    const handleSetActiveTab = (event) => {
      setActiveTab(event.detail);
    };

    window.addEventListener('setActiveTab', handleSetActiveTab);

    return () => {
      window.removeEventListener('setActiveTab', handleSetActiveTab);
    };
  }, []);

  useEffect(() => {
    const fetchUserData = async () => {
      try {
        if (!authToken) {
          throw new Error('No authentication token found');
        }

        const response = await fetch(buildApiUrl('/team/user-data'), {
          headers: {
            'Authorization': `Bearer ${authToken}`
          }
        });
        
        if (response.status === 401) {
          logout();
          throw new Error('Session expired. Please login again.');
        }
        
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || 'Failed to fetch user data');
        }
        
        const data = await response.json();
        setUserData(data);
        setError(null);
      } catch (error) {
        console.error('Error fetching user data:', error);
        setError(error.message);
        if (error.message.includes('Session expired')) {
          navigate('/login');
        }
      }
    };

    fetchUserData();
  }, [authToken, logout, navigate]);

  const getSidebarItems = () => {
    const commonItems = [
      { id: 'dashboard', icon: <FaChartLine />, label: 'Dashboard' },
    ];

    const roleSpecificItems = {
      'it_team': [
        { id: 'azure', icon: <FaCloud />, label: 'Connect to Azure' },
        { id: 'azure-config', icon: <FaCog />, label: 'Azure AD Config' },
        { id: 'logs', icon: <FaClipboardList />, label: 'Logs' },
        { id: 'chatbot', icon: <FaRobot />, label: 'Compliance Chatbot' },
      ],
      'management_team': [
        { id: 'logs', icon: <FaClipboardList />, label: 'Activity Logs' },
      ],
      'compliance_team': [
        { id: 'chatbot', icon: <FaRobot />, label: 'Compliance Chatbot' },
        { id: 'testing', icon: <FaDesktop />, label: 'UI Testing' },
        { id: 'scan', icon: <FaCalendarAlt />, label: 'Schedule Scan' },
        { id: 'azure-checker', icon: <FaCloud />, label: 'Azure Compliance Checker' },
        { id: 'logs', icon: <FaClipboardList />, label: 'Activity Logs' },
      ],
    };

    // Add profile at the end
    const allItems = [...commonItems, ...(roleSpecificItems[userData?.role] || [])];
    allItems.push({ id: 'profile', icon: <FaUser />, label: 'Profile' });

    return allItems;
  };

  const handleLogout = () => {
    logout();
  };

  if (!userData) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        {error ? (
          <div className="text-center">
            <div className="text-destructive text-lg mb-4">{error}</div>
            <button
              onClick={() => navigate('/login')}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90"
            >
              Return to Login
            </button>
          </div>
        ) : (
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
          className="h-12 w-12 border-t-2 border-b-2 border-primary rounded-full"
        />
        )}
      </div>
    );
  }

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="space-y-6"
          >
            {/* Report Content - everything inside will be captured in export */}
            <div ref={reportRef} className="space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold text-foreground">
                  {userData.role === 'it_team' ? 'IT Team Dashboard' :
                   userData.role === 'compliance_team' ? 'Compliance Team Dashboard' :
                   'Management Team Dashboard'}
                </h2>
                <div className="flex items-center space-x-2">
                  <FaShieldAlt className="text-primary" />
                  <span className="text-sm text-muted-foreground capitalize">
                    {userData.role.replace('_', ' ')}
                  </span>
                </div>
              </div>

              <div className="mb-6">
                <h3 className="text-lg font-semibold mb-4">Chatbot Analytics</h3>
                <div className="w-full">
                  <ChatbotAnalytics />
                </div>
              </div>

              {/* UI Testing summary cards (consistent for all roles) */}
              <UiTestingSummaryCards />

              {/* Azure Compliance Checker Latest Result */}
              {(userData.role === 'compliance_team' || userData.role === 'management_team' || userData.role === 'it_team') && (
                <div className="mb-6">
                  <h3 className="text-lg font-semibold mb-4">Latest Azure Compliance Analysis</h3>
                  <AzureComplianceLatestResult />
                </div>
              )}

              <div className="mb-6">
                <h3 className="text-lg font-semibold mb-4">Integrations</h3>
                <div className="grid grid-cols-1">
                  <AzureConnectionMiniCard />
                </div>
              </div>
            </div>

            {/* Reports - actions placed at end of dashboard */}
            <div className="mt-8">
              <h3 className="text-lg font-semibold mb-3">Reports</h3>
              
              {/* Azure Compliance Reports List - Only for compliance_team and management_team, NOT for it_team */}
              {(userData?.role === 'compliance_team' || userData?.role === 'management_team') && <AzureComplianceReportsList />}
              
              <div className="flex items-center justify-start gap-3 flex-wrap no-export">
                <button
                  onClick={async () => {
                  // Fetch structured data
                  const headers = authToken ? { 'Authorization': `Bearer ${authToken}` } : {};
                  
                  // Fetch all data including Azure compliance (if compliance_team, management_team, or it_team)
                  const fetchPromises = [
                    fetch(buildApiUrl('/api/compliance/analytics'), { headers }),
                    fetch(buildApiUrl('/api/ui/site/latest'), { headers })
                  ];
                  
                  // Add Azure compliance fetch for compliance_team, management_team, and it_team
                  if (userData?.role === 'compliance_team' || userData?.role === 'management_team' || userData?.role === 'it_team') {
                    fetchPromises.push(fetch(buildApiUrl('/api/azure-checker/latest-result'), { headers }));
                  }
                  
                  const [analyticsResp, uiResp, azureResp] = await Promise.all(fetchPromises);
                  const analytics = analyticsResp.ok ? await analyticsResp.json() : {};
                  const uiLatest = uiResp.ok ? await uiResp.json() : {};
                  const ui = uiLatest?.result || {};
                  
                  // Get Azure compliance data
                  let azureData = null;
                  if ((userData?.role === 'compliance_team' || userData?.role === 'management_team' || userData?.role === 'it_team') && azureResp && azureResp.ok) {
                    const azureLatest = await azureResp.json();
                    if (azureLatest.status === 'success' && azureLatest.result) {
                      azureData = azureLatest.result;
                    }
                  }
                  
                  // Helper function to parse markdown recommendations with better structure
                  const parseMarkdownRecommendations = (text) => {
                    if (!text) return [];
                    const lines = text.split('\n');
                    const recommendations = [];
                    let currentRec = null;
                    let inCodeBlock = false;
                    let codeBlockContent = [];
                    let codeBlockLanguage = '';
                    
                    lines.forEach((line, idx) => {
                      const trimmed = line.trim();
                      
                      // Check for code block start/end
                      if (trimmed.startsWith('```')) {
                        if (inCodeBlock) {
                          // End of code block
                          if (currentRec) {
                            currentRec.items.push({
                              type: 'code',
                              language: codeBlockLanguage,
                              content: codeBlockContent.join('\n')
                            });
                          }
                          codeBlockContent = [];
                          codeBlockLanguage = '';
                          inCodeBlock = false;
                        } else {
                          // Start of code block
                          inCodeBlock = true;
                          codeBlockLanguage = trimmed.replace(/```/, '').trim();
                        }
                        return;
                      }
                      
                      if (inCodeBlock) {
                        codeBlockContent.push(line);
                        return;
                      }
                      
                      // Check for recommendation header [Critical], [Major], [Minor], etc.
                      if (trimmed.match(/^\[(Critical|Major|Minor|Low|Info)\]/)) {
                        if (currentRec) recommendations.push(currentRec);
                        const severity = trimmed.match(/^\[(Critical|Major|Minor|Low|Info)\]/)?.[1] || 'Info';
                        const title = trimmed.replace(/^\[(Critical|Major|Minor|Low|Info)\]\s*/, '');
                        currentRec = {
                          title: title,
                          severity: severity,
                          items: []
                        };
                      }
                      // Check for section headers (Impact, How to Fix, Verification)
                      else if (trimmed.match(/^(Impact|How to Fix|Verification):/i)) {
                        if (currentRec) {
                          const sectionType = trimmed.match(/^(Impact|How to Fix|Verification):/i)?.[1]?.toLowerCase() || '';
                          currentRec.items.push({
                            type: 'section',
                            sectionType: sectionType,
                            content: trimmed.replace(/^(Impact|How to Fix|Verification):\s*/i, '')
                          });
                        }
                      }
                      // Check for separators (---)
                      else if (trimmed === '---' || trimmed === '***') {
                        if (currentRec) {
                          recommendations.push(currentRec);
                          currentRec = null;
                        }
                      }
                      // Check for bullet points (- or *)
                      else if (trimmed.match(/^[-*•]\s+/)) {
                        if (!currentRec) {
                          currentRec = { title: 'Recommendation', severity: 'Info', items: [] };
                        }
                        const content = trimmed.replace(/^[-*•]\s+/, '');
                        // Check if it's a bold item (starts with **)
                        if (content.startsWith('**') && content.endsWith('**')) {
                          currentRec.items.push({
                            type: 'bold',
                            content: content.replace(/\*\*/g, '')
                          });
                        } else {
                          currentRec.items.push({
                            type: 'text',
                            content: content
                          });
                        }
                      }
                      // Check for numbered lists
                      else if (trimmed.match(/^\d+\.\s+/)) {
                        if (!currentRec) {
                          currentRec = { title: 'Recommendation', severity: 'Info', items: [] };
                        }
                        currentRec.items.push({
                          type: 'text',
                          content: trimmed.replace(/^\d+\.\s+/, '')
                        });
                      }
                      // Regular text
                      else if (trimmed && currentRec) {
                        // Check if previous item was a section, append to it
                        if (currentRec.items.length > 0 && currentRec.items[currentRec.items.length - 1].type === 'section') {
                          currentRec.items[currentRec.items.length - 1].content += ' ' + trimmed;
                        } else {
                          currentRec.items.push({
                            type: 'text',
                            content: trimmed
                          });
                        }
                      }
                    });
                    
                    if (currentRec) recommendations.push(currentRec);
                    return recommendations.length > 0 ? recommendations : [{ title: 'Recommendations', severity: 'Info', items: [{ type: 'text', content: text }] }];
                  };

                  // Handle both whole-site scan structure (wcag_aggregate) and single-page structure (wcag_results)
                  const isWholeSiteScan = ui?.wcag_aggregate && ui?.summary;
                  
                  // Get violations data
                  const violations = isWholeSiteScan 
                    ? (ui?.wcag_aggregate?.violations_summary || [])
                    : (ui?.wcag_results?.violations || []);
                  
                  // Get violation counts
                  let counts = { critical: 0, serious: 0, moderate: 0, minor: 0, unknown: 0 };
                  if (isWholeSiteScan) {
                    // Use pre-calculated impact counts from whole-site scan
                    counts = ui?.wcag_aggregate?.impact_counts || counts;
                  } else {
                    // Count violations for single-page scan
                    violations.forEach(v => {
                      const imp = String(v?.impact || '').toLowerCase();
                      if (imp === 'critical') counts.critical += 1;
                      else if (imp === 'serious') counts.serious += 1;
                      else if (imp === 'moderate') counts.moderate += 1;
                      else if (imp === 'minor') counts.minor += 1;
                      else counts.unknown += 1;
                    });
                  }
                  
                  // Get security data (handle both whole-site and single-page formats)
                  const securityData = isWholeSiteScan 
                    ? (ui?.security_aggregate?.primary_scan || {})
                    : (ui?.security_results || {});
                  
                  const sh = securityData?.securityheaders || {};
                  const missingHeaders = Array.isArray(sh?.missing) ? sh.missing : [];
                  const presentHeaders = Array.isArray(sh?.present) ? sh.present : [];
                  const ssl = securityData?.ssllabs || {};
                  const endpoints = Array.isArray(ssl?.endpoints) ? ssl.endpoints : [];
                  const sslGrade = (endpoints[0]?.grade || ssl?.grade || '') || '—';
                  const securityScore = typeof sh?.score === 'number' ? sh.score : Math.max(0, 100 - missingHeaders.length * 15);
                  
                  // Get findings and recommendations
                  const nonCompliant = (Array.isArray(ui?.findings?.security) || Array.isArray(ui?.findings?.accessibility))
                    ? [ ...(ui.findings.security || []), ...(ui.findings.accessibility || []) ]
                    : [];
                  const aiRecs = String(ui?.recommendations || '').trim();
                  
                  // Get whole-site scan metrics if available
                  const pagesScanned = ui?.summary?.pages_scanned || 0;
                  const accessibilityScore = ui?.summary?.accessibility_score || 0;
                  const totalViolations = isWholeSiteScan ? (ui?.wcag_aggregate?.total_violations || 0) : violations.length;

                  // Build PDF with headings and tables
                  const pdf = new jsPDF('p', 'mm', 'a4');
                  const pageWidth = pdf.internal.pageSize.getWidth();
                  const pageHeight = pdf.internal.pageSize.getHeight();
                  let y = 18;

                  // Helper function to draw section divider
                  const drawSectionDivider = (yPos) => {
                    pdf.setDrawColor(100, 100, 100);
                    pdf.setLineWidth(0.3);
                    // Draw a decorative line with some spacing
                    pdf.line(14, yPos, pageWidth - 14, yPos);
                    // Add a subtle shadow effect
                    pdf.setDrawColor(220, 220, 220);
                    pdf.setLineWidth(0.2);
                    pdf.line(14, yPos + 0.3, pageWidth - 14, yPos + 0.3);
                    pdf.setDrawColor(100, 100, 100);
                  };

                  // Helper function to add page numbers
                  const addPageNumber = () => {
                    const pageCount = pdf.internal.getNumberOfPages();
                    for (let i = 1; i <= pageCount; i++) {
                      pdf.setPage(i);
                      pdf.setFontSize(8);
                      pdf.setTextColor(150, 150, 150);
                      pdf.text(
                        `Page ${i} of ${pageCount}`,
                        pageWidth / 2,
                        pageHeight - 10,
                        { align: 'center' }
                      );
                      pdf.setTextColor(0, 0, 0);
                    }
                  };

                  // Enhanced Title Section with background
                  pdf.setFillColor(66, 139, 202);
                  pdf.roundedRect(14, y - 5, pageWidth - 28, 25, 3, 3, 'F');
                  
                  pdf.setTextColor(255, 255, 255);
                  pdf.setFontSize(20);
                  pdf.setFont(undefined, 'bold');
                  pdf.text('Complytics Dashboard Report', pageWidth / 2, y + 3, { align: 'center' });
                  
                  pdf.setFontSize(10);
                  pdf.setFont(undefined, 'normal');
                  pdf.text(new Date().toLocaleString(), pageWidth / 2, y + 10, { align: 'center' });
                  
                  pdf.setTextColor(0, 0, 0);
                  y += 25;
                  
                  // Add decorative line after title
                  drawSectionDivider(y);
                  y += 8;

                  // Chatbot Analytics Section
                  pdf.setFontSize(16);
                  pdf.setFont(undefined, 'bold');
                  pdf.setTextColor(66, 139, 202);
                  pdf.text('Chatbot Analytics', 14, y);
                  y += 6;
                  
                  // Add underline accent
                  pdf.setDrawColor(66, 139, 202);
                  pdf.setLineWidth(2);
                  pdf.line(14, y - 2, 70, y - 2);
                  pdf.setTextColor(0, 0, 0);
                  y += 2;
                  autoTable(pdf, {
                    startY: y,
                    head: [['Metric', 'Value']],
                    body: [
                      ['Total Queries', String(analytics.totalQueries ?? 0)],
                      ['Avg Response Time (s)', String(analytics.averageResponseTime ?? 0)],
                      ['Success Rate (%)', String(analytics.successRate ?? 0)]
                    ],
                    styles: { 
                      fontSize: 9, 
                      cellWidth: 'wrap',
                      overflow: 'linebreak',
                      cellPadding: 3
                    },
                    columnStyles: {
                      0: { cellWidth: 100, halign: 'left' },
                      1: { cellWidth: 60, halign: 'right' }
                    },
                    headStyles: {
                      fillColor: [66, 139, 202],
                      textColor: 255,
                      fontSize: 10,
                      fontStyle: 'bold'
                    },
                    theme: 'striped',
                    margin: { left: 14, right: 14 }
                  });
                  y = (pdf.lastAutoTable && pdf.lastAutoTable.finalY ? pdf.lastAutoTable.finalY : y) + 8;
                  
                  // Section divider
                  drawSectionDivider(y);
                  y += 10;

                  // UI Testing Summary Section
                  pdf.setFontSize(16);
                  pdf.setFont(undefined, 'bold');
                  pdf.setTextColor(66, 139, 202);
                  pdf.text(isWholeSiteScan ? 'Whole-Site Scan Summary' : 'UI Testing Summary', 14, y);
                  y += 6;
                  
                  // Add underline accent
                  pdf.setDrawColor(66, 139, 202);
                  pdf.setLineWidth(2);
                  pdf.line(14, y - 2, 90, y - 2);
                  pdf.setTextColor(0, 0, 0);
                  y += 2;
                  
                  // Add whole-site scan metrics if available
                  if (isWholeSiteScan) {
                    autoTable(pdf, {
                      startY: y,
                      head: [['Scan Metric', 'Value']],
                      body: [
                        ['Pages Scanned', String(pagesScanned)],
                        ['Accessibility Score', String(accessibilityScore)],
                        ['Total Violations', String(totalViolations)],
                        ['Unique Issues', String(ui?.wcag_aggregate?.unique_rules_violated || 0)],
                        ['Pages with Issues', String(ui?.wcag_aggregate?.pages_with_issues || 0)]
                      ],
                      styles: { 
                        fontSize: 9, 
                        cellWidth: 'wrap',
                        overflow: 'linebreak',
                        cellPadding: 3
                      },
                      columnStyles: {
                        0: { cellWidth: 100, halign: 'left' },
                        1: { cellWidth: 60, halign: 'right' }
                      },
                      headStyles: {
                        fillColor: [66, 139, 202],
                        textColor: 255,
                        fontSize: 10,
                        fontStyle: 'bold'
                      },
                      theme: 'striped',
                      margin: { left: 14, right: 14 }
                    });
                    y = (pdf.lastAutoTable && pdf.lastAutoTable.finalY ? pdf.lastAutoTable.finalY : y) + 8;
                  }
                  
                  autoTable(pdf, {
                    startY: y,
                    head: [['Severity', 'Count']],
                    body: [
                      ['Critical', String(counts.critical)],
                      ['Serious', String(counts.serious)],
                      ['Moderate', String(counts.moderate)],
                      ['Minor', String(counts.minor)]
                    ],
                    styles: { 
                      fontSize: 9, 
                      cellWidth: 'wrap',
                      overflow: 'linebreak',
                      cellPadding: 3
                    },
                    columnStyles: {
                      0: { cellWidth: 100, halign: 'left' },
                      1: { cellWidth: 60, halign: 'right' }
                    },
                    headStyles: {
                      fillColor: [66, 139, 202],
                      textColor: 255,
                      fontSize: 10,
                      fontStyle: 'bold'
                    },
                    theme: 'striped',
                    margin: { left: 14, right: 14 }
                  });
                  y = (pdf.lastAutoTable && pdf.lastAutoTable.finalY ? pdf.lastAutoTable.finalY : y) + 6;

                  autoTable(pdf, {
                    startY: y,
                    head: [['Security Metric', 'Value']],
                    body: [
                      ['Security Score', String(securityScore)],
                      ['SSL Labs Grade', String(sslGrade)],
                      ['Headers Present', String(presentHeaders.length)],
                      ['Headers Missing', String(missingHeaders.length)]
                    ],
                    styles: { 
                      fontSize: 9, 
                      cellWidth: 'wrap',
                      overflow: 'linebreak',
                      cellPadding: 3
                    },
                    columnStyles: {
                      0: { cellWidth: 100, halign: 'left' },
                      1: { cellWidth: 60, halign: 'right' }
                    },
                    headStyles: {
                      fillColor: [66, 139, 202],
                      textColor: 255,
                      fontSize: 10,
                      fontStyle: 'bold'
                    },
                    theme: 'striped',
                    margin: { left: 14, right: 14 }
                  });
                  y = (pdf.lastAutoTable && pdf.lastAutoTable.finalY ? pdf.lastAutoTable.finalY : y) + 8;
                  
                  // Section divider
                  drawSectionDivider(y);
                  y += 10;

                  // Recommendations Section
                  pdf.setFontSize(16);
                  pdf.setFont(undefined, 'bold');
                  pdf.setTextColor(66, 139, 202);
                  pdf.text('Recommendations', 14, y);
                  y += 6;
                  
                  // Add underline accent
                  pdf.setDrawColor(66, 139, 202);
                  pdf.setLineWidth(2);
                  pdf.line(14, y - 2, 60, y - 2);
                  pdf.setTextColor(0, 0, 0);
                  y += 2;
                  const recRows = (nonCompliant || []).slice(0, 30).map((r) => [
                    String(r.title || '—'),
                    String(r.severity || '—').toUpperCase(),
                    String(r.remediation || r.fix || '—')
                  ]);
                  if (recRows.length > 0) {
                    autoTable(pdf, {
                      startY: y,
                      head: [['Title', 'Severity', 'Action']],
                      body: recRows,
                      styles: { 
                        fontSize: 8, 
                        cellWidth: 'wrap',
                        overflow: 'linebreak',
                        cellPadding: 3
                      },
                      columnStyles: { 
                        0: { cellWidth: 60, halign: 'left' },  // Title column
                        1: { cellWidth: 20, halign: 'center' }, // Severity column
                        2: { cellWidth: 60, halign: 'left' }    // Action column
                      },
                      headStyles: {
                        fillColor: [66, 139, 202],
                        textColor: 255,
                        fontSize: 9,
                        fontStyle: 'bold'
                      },
                      bodyStyles: {
                        fontSize: 8,
                        cellPadding: 2
                      },
                      theme: 'striped',
                      tableWidth: 'wrap',
                      margin: { left: 14, right: 14 }
                    });
                    y = (pdf.lastAutoTable && pdf.lastAutoTable.finalY ? pdf.lastAutoTable.finalY : y) + 6;
                  }
                  
                  // Section divider
                  if (aiRecs) {
                    drawSectionDivider(y);
                    y += 10;
                  }
                  
                  // AI Recommendations with better formatting
                  if (aiRecs) {
                    if (y > pdf.internal.pageSize.getHeight() - 30) { pdf.addPage(); y = 20; }
                    
                    pdf.setFontSize(16);
                    pdf.setFont(undefined, 'bold');
                    pdf.setTextColor(66, 139, 202);
                    pdf.text('AI Recommendations', 14, y);
                    y += 6;
                    
                    // Add underline accent
                    pdf.setDrawColor(66, 139, 202);
                    pdf.setLineWidth(2);
                    pdf.line(14, y - 2, 75, y - 2);
                    pdf.setTextColor(0, 0, 0);
                    y += 4;
                    
                    const parsedRecs = parseMarkdownRecommendations(aiRecs);
                    parsedRecs.forEach((rec, idx) => {
                      if (y > pdf.internal.pageSize.getHeight() - 50) { pdf.addPage(); y = 20; }
                      
                      // Recommendation header with severity badge
                      const severityColors = {
                        'Critical': [220, 38, 38],  // Red
                        'Major': [245, 158, 11],     // Orange
                        'Minor': [234, 179, 8],      // Yellow
                        'Low': [59, 130, 246],        // Blue
                        'Info': [107, 114, 128]       // Gray
                      };
                      const severityColor = severityColors[rec.severity] || [107, 114, 128];
                      
                      // Draw severity badge background
                      pdf.setFillColor(...severityColor);
                      pdf.roundedRect(14, y - 3, 20, 6, 2, 2, 'F');
                      pdf.setTextColor(255, 255, 255);
                      pdf.setFontSize(8);
                      pdf.setFont(undefined, 'bold');
                      pdf.text((rec.severity || 'Info').toUpperCase(), 16, y + 1);
                      
                      // Recommendation title
                      pdf.setTextColor(0, 0, 0);
                      pdf.setFontSize(11);
                      pdf.setFont(undefined, 'bold');
                      const titleX = 38;
                      const titleLines = pdf.splitTextToSize(rec.title, pageWidth - titleX - 14);
                      titleLines.forEach((line, lineIdx) => {
                        if (y > pdf.internal.pageSize.getHeight() - 20) { pdf.addPage(); y = 20; }
                        pdf.text(line, titleX, y + (lineIdx * 4));
                      });
                      y += Math.max(6, titleLines.length * 4) + 4;
                      
                      // Items with proper formatting
                      pdf.setFontSize(9);
                      pdf.setFont(undefined, 'normal');
                      
                      rec.items.forEach((item) => {
                        if (y > pdf.internal.pageSize.getHeight() - 20) { pdf.addPage(); y = 20; }
                        
                        if (item.type === 'section') {
                          // Section header (Impact, How to Fix, Verification)
                          y += 2;
                    pdf.setFontSize(10);
                          pdf.setFont(undefined, 'bold');
                          const sectionTitle = item.sectionType.charAt(0).toUpperCase() + item.sectionType.slice(1) + ':';
                          pdf.text(sectionTitle, 18, y);
                          y += 5;
                          
                          // Section content
                          pdf.setFontSize(9);
                          pdf.setFont(undefined, 'normal');
                          const contentLines = pdf.splitTextToSize(item.content, pageWidth - 32);
                          contentLines.forEach((line) => {
                            if (y > pdf.internal.pageSize.getHeight() - 20) { pdf.addPage(); y = 20; }
                            pdf.text(line, 22, y);
                            y += 4;
                          });
                          y += 2;
                        }
                        else if (item.type === 'code') {
                          // Code block with background
                          y += 3;
                          const codeLines = item.content.split('\n');
                          const codeHeight = codeLines.length * 4 + 4;
                          
                          if (y + codeHeight > pdf.internal.pageSize.getHeight() - 20) { 
                            pdf.addPage(); 
                            y = 20; 
                          }
                          
                          // Draw code block background
                          pdf.setFillColor(245, 247, 250);
                          pdf.roundedRect(18, y - 2, pageWidth - 36, codeHeight, 2, 2, 'F');
                          
                          // Draw border
                          pdf.setDrawColor(200, 200, 200);
                          pdf.setLineWidth(0.5);
                          pdf.roundedRect(18, y - 2, pageWidth - 36, codeHeight, 2, 2, 'S');
                          
                          // Code language label (if specified)
                          if (item.language) {
                            pdf.setFontSize(7);
                            pdf.setFont(undefined, 'italic');
                            pdf.setTextColor(100, 100, 100);
                            pdf.text(item.language, 20, y + 1);
                            pdf.setTextColor(0, 0, 0);
                            y += 4;
                          }
                          
                          // Code content
                          pdf.setFontSize(8);
                          pdf.setFont('courier', 'normal');
                          codeLines.forEach((codeLine) => {
                            if (y > pdf.internal.pageSize.getHeight() - 20) { 
                              pdf.addPage(); 
                              y = 20;
                              pdf.setFillColor(245, 247, 250);
                              pdf.roundedRect(18, y - 2, pageWidth - 36, codeHeight, 2, 2, 'F');
                            }
                            // Handle long code lines
                            const maxCodeWidth = pageWidth - 40;
                            const codeLineParts = pdf.splitTextToSize(codeLine, maxCodeWidth);
                            codeLineParts.forEach((part) => {
                              if (y > pdf.internal.pageSize.getHeight() - 20) { 
                                pdf.addPage(); 
                                y = 20;
                              }
                              pdf.text(part, 22, y);
                              y += 4;
                            });
                          });
                          
                          pdf.setFont('helvetica', 'normal');
                          y += 3;
                        }
                        else if (item.type === 'bold') {
                          // Bold text
                          pdf.setFont(undefined, 'bold');
                          const boldLines = pdf.splitTextToSize(item.content, pageWidth - 32);
                          boldLines.forEach((line) => {
                            if (y > pdf.internal.pageSize.getHeight() - 20) { pdf.addPage(); y = 20; }
                            pdf.text(line, 22, y);
                            y += 4;
                          });
                          pdf.setFont(undefined, 'normal');
                        }
                        else {
                          // Regular text with bullet
                          const textContent = item.content || String(item);
                          const lines = pdf.splitTextToSize(`• ${textContent}`, pageWidth - 32);
                    lines.forEach((line) => {
                            if (y > pdf.internal.pageSize.getHeight() - 20) { pdf.addPage(); y = 20; }
                            pdf.text(line, 22, y);
                            y += 4;
                          });
                        }
                      });
                      
                      // Add separator between recommendations
                      if (idx < parsedRecs.length - 1) {
                        y += 4;
                        pdf.setDrawColor(200, 200, 200);
                        pdf.setLineWidth(0.5);
                        pdf.line(14, y, pageWidth - 14, y);
                        y += 6;
                      }
                    });
                    
                    // Section divider after AI Recommendations
                    drawSectionDivider(y);
                    y += 10;
                  }
                  
                  // Azure Compliance Analysis Section
                  if (azureData && (userData?.role === 'compliance_team' || userData?.role === 'management_team' || userData?.role === 'it_team')) {
                    if (y > pdf.internal.pageSize.getHeight() - 40) { pdf.addPage(); y = 20; }
                    
                    pdf.setFontSize(16);
                    pdf.setFont(undefined, 'bold');
                    pdf.setTextColor(66, 139, 202);
                    pdf.text('Azure Compliance Analysis', 14, y);
                    y += 6;
                    
                    // Add underline accent
                    pdf.setDrawColor(66, 139, 202);
                    pdf.setLineWidth(2);
                    pdf.line(14, y - 2, 95, y - 2);
                    pdf.setTextColor(0, 0, 0);
                    y += 4;
                    
                    // Document info
                    autoTable(pdf, {
                      startY: y,
                      head: [['Metric', 'Value']],
                      body: [
                        ['Document Name', azureData.document_name || 'N/A'],
                        ['Overall Score', `${azureData.overall_score || azureData.score || 0}/100`],
                        ['Overall Status', azureData.overall_status || 'Unknown'],
                        ['Frameworks Analyzed', String(azureData.frameworks_analyzed || 0)],
                        ['Analysis Date', azureData.analyzed_at ? new Date(azureData.analyzed_at).toLocaleDateString() : 'N/A']
                      ],
                      styles: { 
                        fontSize: 9, 
                        cellWidth: 'wrap',
                        overflow: 'linebreak',
                        cellPadding: 3
                      },
                      columnStyles: {
                        0: { cellWidth: 100, halign: 'left' },
                        1: { cellWidth: 60, halign: 'left' }
                      },
                      headStyles: {
                        fillColor: [66, 139, 202],
                        textColor: 255,
                        fontSize: 10,
                        fontStyle: 'bold'
                      },
                      theme: 'striped',
                      margin: { left: 14, right: 14 }
                    });
                    y = (pdf.lastAutoTable && pdf.lastAutoTable.finalY ? pdf.lastAutoTable.finalY : y) + 8;
                    
                    // Framework Scores
                    if (azureData.framework_scores && Object.keys(azureData.framework_scores).length > 0) {
                      pdf.setFontSize(13);
                      pdf.setFont(undefined, 'bold');
                      pdf.setTextColor(50, 50, 50);
                      pdf.text('Framework Compliance Scores', 14, y);
                      y += 6;
                      pdf.setTextColor(0, 0, 0);
                      
                      const frameworkData = [['Framework', 'Score', 'Status']];
                      Object.entries(azureData.framework_scores).forEach(([framework, score]) => {
                        const status = score >= 80 ? 'Compliant' : score >= 60 ? 'Partial' : 'Non-Compliant';
                        const frameworkName = {
                          'gdpr': 'GDPR',
                          'iso27001': 'ISO 27001',
                          'iso27017': 'ISO 27017',
                          'iso27018': 'ISO 27018',
                          'azure': 'Azure Best Practices'
                        }[framework] || framework.toUpperCase();
                        frameworkData.push([frameworkName, `${score}/100`, status]);
                      });
                      
                      autoTable(pdf, {
                        startY: y,
                        head: frameworkData.slice(0, 1),
                        body: frameworkData.slice(1),
                        styles: { 
                          fontSize: 9, 
                          cellWidth: 'wrap',
                          overflow: 'linebreak',
                          cellPadding: 3
                        },
                        columnStyles: {
                          0: { cellWidth: 60, halign: 'left' },
                          1: { cellWidth: 30, halign: 'center' },
                          2: { cellWidth: 30, halign: 'center' }
                        },
                        headStyles: {
                          fillColor: [66, 139, 202],
                          textColor: 255,
                          fontSize: 10,
                          fontStyle: 'bold'
                        },
                        theme: 'striped',
                        margin: { left: 14, right: 14 }
                      });
                      y = (pdf.lastAutoTable && pdf.lastAutoTable.finalY ? pdf.lastAutoTable.finalY : y) + 8;
                    }
                    
                    // Summary
                    if (azureData.summary) {
                      pdf.setFontSize(13);
                      pdf.setFont(undefined, 'bold');
                      pdf.setTextColor(50, 50, 50);
                      pdf.text('Executive Summary', 14, y);
                      y += 6;
                      pdf.setTextColor(0, 0, 0);
                      pdf.setFontSize(10);
                      pdf.setFont(undefined, 'normal');
                      const summaryLines = pdf.splitTextToSize(azureData.summary, pageWidth - 28);
                      summaryLines.forEach((line) => {
                      if (y > pdf.internal.pageSize.getHeight() - 20) { pdf.addPage(); y = 20; }
                      pdf.text(line, 14, y);
                      y += 5;
                    });
                      y += 4;
                    }
                    
                    // Framework-specific recommendations
                    if (azureData.frameworks && Object.keys(azureData.frameworks).length > 0) {
                      pdf.setFontSize(13);
                      pdf.setFont(undefined, 'bold');
                      pdf.setTextColor(50, 50, 50);
                      pdf.text('Framework-Specific Recommendations', 14, y);
                      y += 6;
                      pdf.setTextColor(0, 0, 0);
                      
                      const frameworkEntries = Object.entries(azureData.frameworks);
                      frameworkEntries.forEach(([frameworkName, frameworkData], frameworkIdx) => {
                        if (y > pdf.internal.pageSize.getHeight() - 40) { pdf.addPage(); y = 20; }
                        
                        // Add divider before each framework (except the first one)
                        if (frameworkIdx > 0) {
                          y += 4;
                          drawSectionDivider(y);
                          y += 8;
                        }
                        
                        const frameworkDisplayName = {
                          'gdpr': 'GDPR',
                          'iso27001': 'ISO 27001',
                          'iso27017': 'ISO 27017',
                          'iso27018': 'ISO 27018',
                          'azure': 'Azure Best Practices'
                        }[frameworkName] || frameworkName.toUpperCase();
                        
                        // Framework header with background
                        pdf.setFillColor(240, 248, 255);
                        pdf.roundedRect(14, y - 2, pageWidth - 28, 8, 2, 2, 'F');
                        
                        pdf.setFontSize(12);
                        pdf.setFont(undefined, 'bold');
                        pdf.setTextColor(66, 139, 202);
                        pdf.text(frameworkDisplayName, 18, y + 3);
                        pdf.setTextColor(0, 0, 0);
                        y += 10;
                        
                        pdf.setFontSize(9);
                        pdf.setFont(undefined, 'normal');
                        
                        // Recommendation
                        if (frameworkData.recommendation) {
                          pdf.setFont(undefined, 'bold');
                          pdf.text('Recommendation:', 14, y);
                          y += 5;
                          pdf.setFont(undefined, 'normal');
                          const recLines = pdf.splitTextToSize(frameworkData.recommendation, pageWidth - 28);
                          recLines.forEach((line) => {
                            if (y > pdf.internal.pageSize.getHeight() - 20) { pdf.addPage(); y = 20; }
                            pdf.text(line, 18, y);
                            y += 4;
                          });
                          y += 2;
                        }
                        
                        // Gaps
                        if (frameworkData.gaps && frameworkData.gaps.length > 0) {
                          pdf.setFont(undefined, 'bold');
                          pdf.text('Gaps Identified:', 14, y);
                          y += 5;
                          pdf.setFont(undefined, 'normal');
                          frameworkData.gaps.forEach((gap) => {
                            if (y > pdf.internal.pageSize.getHeight() - 20) { pdf.addPage(); y = 20; }
                            const gapLines = pdf.splitTextToSize(`• ${gap}`, pageWidth - 28);
                            gapLines.forEach((line) => {
                              if (y > pdf.internal.pageSize.getHeight() - 20) { pdf.addPage(); y = 20; }
                              pdf.text(line, 18, y);
                              y += 4;
                            });
                          });
                          y += 2;
                        }
                        
                        // Priority Actions
                        if (frameworkData.priority_actions && frameworkData.priority_actions.length > 0) {
                          pdf.setFont(undefined, 'bold');
                          pdf.text('Priority Actions:', 14, y);
                          y += 5;
                          pdf.setFont(undefined, 'normal');
                          frameworkData.priority_actions.forEach((action, idx) => {
                            if (y > pdf.internal.pageSize.getHeight() - 20) { pdf.addPage(); y = 20; }
                            const actionLines = pdf.splitTextToSize(`${idx + 1}. ${action}`, pageWidth - 28);
                            actionLines.forEach((line) => {
                              if (y > pdf.internal.pageSize.getHeight() - 20) { pdf.addPage(); y = 20; }
                              pdf.text(line, 18, y);
                              y += 4;
                            });
                          });
                          y += 2;
                        }
                        
                        // Add spacing after each framework
                        y += 4;
                      });
                    }
                  }

                  // Visual summary (append as image pages)
                  const node = reportRef.current;
                  if (node) {
                    const canvas = await html2canvas(node, {
                      scale: 2,
                      useCORS: true,
                      backgroundColor: '#ffffff',
                      ignoreElements: (el) => el.classList?.contains('no-export')
                    });
                    const imgData = canvas.toDataURL('image/png');
                    const pageHeight = pdf.internal.pageSize.getHeight();
                    const imgWidth = pageWidth;
                    const imgHeight = (canvas.height * imgWidth) / canvas.width;
                    let heightLeft = imgHeight;
                    let position = 0;
                    pdf.addPage();
                    pdf.setFontSize(12);
                    pdf.text('Visual Summary', 14, 16);
                    pdf.addImage(imgData, 'PNG', 0, 20, imgWidth, Math.min(imgHeight, pageHeight - 24));
                    heightLeft -= (pageHeight - 24);
                    while (heightLeft > 0) {
                      pdf.addPage();
                      position = 20 - (imgHeight - heightLeft);
                      pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
                      heightLeft -= pageHeight;
                    }
                  }

                  // Add page numbers to all pages
                  addPageNumber();

                    pdf.save('Complytics-Dashboard-Report.pdf');
                  }}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90"
                >
                  <FaFilePdf />
                  <span>Download Full Report (PDF)</span>
                </button>
                
                <button
                  onClick={async () => {
                  // Fetch structured data
                  const headers = authToken ? { 'Authorization': `Bearer ${authToken}` } : {};
                        
                  // Fetch all data including Azure compliance (if compliance_team, management_team, or it_team)
                  const fetchPromises = [
                    fetch(buildApiUrl('/api/compliance/analytics'), { headers }),
                    fetch(buildApiUrl('/api/ui/site/latest'), { headers })
                  ];
                  
                  // Add Azure compliance fetch for compliance_team, management_team, and it_team
                  if (userData?.role === 'compliance_team' || userData?.role === 'management_team' || userData?.role === 'it_team') {
                    fetchPromises.push(fetch(buildApiUrl('/api/azure-checker/latest-result'), { headers }));
                  }
                  
                  const [analyticsResp, uiResp, azureResp] = await Promise.all(fetchPromises);
                  const analytics = analyticsResp.ok ? await analyticsResp.json() : {};
                  const uiLatest = uiResp.ok ? await uiResp.json() : {};
                  const ui = uiLatest?.result || {};
                  
                  // Get Azure compliance data
                  let azureData = null;
                  if ((userData?.role === 'compliance_team' || userData?.role === 'management_team' || userData?.role === 'it_team') && azureResp && azureResp.ok) {
                    const azureLatest = await azureResp.json();
                    if (azureLatest.status === 'success' && azureLatest.result) {
                      azureData = azureLatest.result;
                    }
                  }
                  
                  // Helper function to parse markdown recommendations with better structure
                  const parseMarkdownRecommendations = (text) => {
                    if (!text) return [];
                    const lines = text.split('\n');
                    const recommendations = [];
                    let currentRec = null;
                    let inCodeBlock = false;
                    let codeBlockContent = [];
                    let codeBlockLanguage = '';
                    
                    lines.forEach((line, idx) => {
                      const trimmed = line.trim();
                      
                      // Check for code block start/end
                      if (trimmed.startsWith('```')) {
                        if (inCodeBlock) {
                          // End of code block
                          if (currentRec) {
                            currentRec.items.push({
                              type: 'code',
                              language: codeBlockLanguage,
                              content: codeBlockContent.join('\n')
                            });
                          }
                          codeBlockContent = [];
                          codeBlockLanguage = '';
                          inCodeBlock = false;
                        } else {
                          // Start of code block
                          inCodeBlock = true;
                          codeBlockLanguage = trimmed.replace(/```/, '').trim();
                        }
                        return;
                      }
                      
                      if (inCodeBlock) {
                        codeBlockContent.push(line);
                        return;
                      }
                      
                      // Check for recommendation header [Critical], [Major], [Minor], etc.
                      if (trimmed.match(/^\[(Critical|Major|Minor|Low|Info)\]/)) {
                        if (currentRec) recommendations.push(currentRec);
                        const severity = trimmed.match(/^\[(Critical|Major|Minor|Low|Info)\]/)?.[1] || 'Info';
                        const title = trimmed.replace(/^\[(Critical|Major|Minor|Low|Info)\]\s*/, '');
                        currentRec = {
                          title: title,
                          severity: severity,
                          items: []
                        };
                      }
                      // Check for section headers (Impact, How to Fix, Verification)
                      else if (trimmed.match(/^(Impact|How to Fix|Verification):/i)) {
                        if (currentRec) {
                          const sectionType = trimmed.match(/^(Impact|How to Fix|Verification):/i)?.[1]?.toLowerCase() || '';
                          currentRec.items.push({
                            type: 'section',
                            sectionType: sectionType,
                            content: trimmed.replace(/^(Impact|How to Fix|Verification):\s*/i, '')
                          });
                        }
                      }
                      // Check for separators (---)
                      else if (trimmed === '---' || trimmed === '***') {
                        if (currentRec) {
                          recommendations.push(currentRec);
                          currentRec = null;
                        }
                      }
                      // Check for bullet points (- or *)
                      else if (trimmed.match(/^[-*•]\s+/)) {
                        if (!currentRec) {
                          currentRec = { title: 'Recommendation', severity: 'Info', items: [] };
                        }
                        const content = trimmed.replace(/^[-*•]\s+/, '');
                        // Check if it's a bold item (starts with **)
                        if (content.startsWith('**') && content.endsWith('**')) {
                          currentRec.items.push({
                            type: 'bold',
                            content: content.replace(/\*\*/g, '')
                          });
                        } else {
                          currentRec.items.push({
                            type: 'text',
                            content: content
                          });
                        }
                      }
                      // Check for numbered lists
                      else if (trimmed.match(/^\d+\.\s+/)) {
                        if (!currentRec) {
                          currentRec = { title: 'Recommendation', severity: 'Info', items: [] };
                        }
                        currentRec.items.push({
                          type: 'text',
                          content: trimmed.replace(/^\d+\.\s+/, '')
                        });
                      }
                      // Regular text
                      else if (trimmed && currentRec) {
                        // Check if previous item was a section, append to it
                        if (currentRec.items.length > 0 && currentRec.items[currentRec.items.length - 1].type === 'section') {
                          currentRec.items[currentRec.items.length - 1].content += ' ' + trimmed;
                        } else {
                          currentRec.items.push({
                            type: 'text',
                            content: trimmed
                          });
                        }
                      }
                    });
                    
                    if (currentRec) recommendations.push(currentRec);
                    return recommendations.length > 0 ? recommendations : [{ title: 'Recommendations', severity: 'Info', items: [{ type: 'text', content: text }] }];
                  };

                  // Handle both whole-site scan structure (wcag_aggregate) and single-page structure (wcag_results)
                  const isWholeSiteScan = ui?.wcag_aggregate && ui?.summary;
                  
                  // Get violations data
                  const violations = isWholeSiteScan 
                    ? (ui?.wcag_aggregate?.violations_summary || [])
                    : (ui?.wcag_results?.violations || []);
                  
                  // Get violation counts
                  let counts = { critical: 0, serious: 0, moderate: 0, minor: 0, unknown: 0 };
                  if (isWholeSiteScan) {
                    // Use pre-calculated impact counts from whole-site scan
                    counts = ui?.wcag_aggregate?.impact_counts || counts;
                  } else {
                    // Count violations for single-page scan
                    violations.forEach(v => {
                      const imp = String(v?.impact || '').toLowerCase();
                      if (imp === 'critical') counts.critical += 1;
                      else if (imp === 'serious') counts.serious += 1;
                      else if (imp === 'moderate') counts.moderate += 1;
                      else if (imp === 'minor') counts.minor += 1;
                      else counts.unknown += 1;
                    });
                  }
                  
                  // Get security data (handle both whole-site and single-page formats)
                  const securityData = isWholeSiteScan 
                    ? (ui?.security_aggregate?.primary_scan || {})
                    : (ui?.security_results || {});
                  
                  const sh = securityData?.securityheaders || {};
                  const missingHeaders = Array.isArray(sh?.missing) ? sh.missing : [];
                  const presentHeaders = Array.isArray(sh?.present) ? sh.present : [];
                  const ssl = securityData?.ssllabs || {};
                  const endpoints = Array.isArray(ssl?.endpoints) ? ssl.endpoints : [];
                  const sslGrade = (endpoints[0]?.grade || ssl?.grade || '') || '—';
                  const securityScore = typeof sh?.score === 'number' ? sh.score : Math.max(0, 100 - missingHeaders.length * 15);
                  
                  // Get findings and recommendations
                  const nonCompliant = (Array.isArray(ui?.findings?.security) || Array.isArray(ui?.findings?.accessibility))
                    ? [ ...(ui.findings.security || []), ...(ui.findings.accessibility || []) ]
                    : [];
                  const aiRecs = String(ui?.recommendations || '').trim();
                  
                  // Get whole-site scan metrics if available
                  const pagesScanned = ui?.summary?.pages_scanned || 0;
                  const accessibilityScore = ui?.summary?.accessibility_score || 0;
                  const totalViolations = isWholeSiteScan ? (ui?.wcag_aggregate?.total_violations || 0) : violations.length;

                  // Capture visualization image
                  const node = reportRef.current;
                  let imageRun = null;
                  if (node) {
                    const canvas = await html2canvas(node, {
                      scale: 2,
                      useCORS: true,
                      backgroundColor: '#ffffff',
                      ignoreElements: (el) => el.classList?.contains('no-export')
                    });
                    const dataUrl = canvas.toDataURL('image/png');
                    const imageBuffer = await (await fetch(dataUrl)).arrayBuffer();
                    imageRun = new ImageRun({ data: imageBuffer, transformation: { width: 600, height: Math.round(600 * (canvas.height / canvas.width)) } });
                  }

                  // Helpers for docx tables
                  const makeHeader = (cells) => new TableRow({ children: cells.map((c) => new TableCell({ children: [new Paragraph({ text: c, bold: true })], width: { size: Math.round(100 / cells.length), type: WidthType.PERCENTAGE } })) });
                  const makeRow = (cells) => new TableRow({ children: cells.map((c) => new TableCell({ children: [new Paragraph(String(c))], width: { size: Math.round(100 / cells.length), type: WidthType.PERCENTAGE } })) });

                  const analyticsTable = new Table({ rows: [
                    makeHeader(['Metric', 'Value']),
                    makeRow(['Total Queries', analytics.totalQueries ?? 0]),
                    makeRow(['Avg Response Time (s)', analytics.averageResponseTime ?? 0]),
                    makeRow(['Success Rate (%)', analytics.successRate ?? 0])
                  ] });
                  const severityTable = new Table({ rows: [
                    makeHeader(['Severity', 'Count']),
                    makeRow(['Critical', counts.critical]),
                    makeRow(['Serious', counts.serious]),
                    makeRow(['Moderate', counts.moderate]),
                    makeRow(['Minor', counts.minor])
                  ] });
                  const securityTable = new Table({ rows: [
                    makeHeader(['Security Metric', 'Value']),
                    makeRow(['Security Score', securityScore]),
                    makeRow(['SSL Labs Grade', sslGrade]),
                    makeRow(['Headers Present', presentHeaders.length]),
                    makeRow(['Headers Missing', missingHeaders.length])
                  ] });

                  const recRows = (nonCompliant || []).slice(0, 30).map((r) => makeRow([
                    String(r.title || '—'),
                    String(r.severity || '—').toUpperCase(),
                    String(r.remediation || r.fix || '—')
                  ]));
                  const recsTable = new Table({ rows: [ makeHeader(['Title', 'Severity', 'Action']), ...recRows ] });

                  // Build document children array
                  const docChildren = [
                          new Paragraph({ text: 'Complytics Dashboard Report', heading: HeadingLevel.TITLE }),
                          new Paragraph({ children: [new TextRun({ text: new Date().toLocaleString(), italics: true })] }),
                          new Paragraph({ text: 'Chatbot Analytics', heading: HeadingLevel.HEADING_1 }),
                          analyticsTable,
                          new Paragraph({ text: 'UI Testing Summary', heading: HeadingLevel.HEADING_1 }),
                          severityTable,
                          securityTable,
                          new Paragraph({ text: 'Recommendations', heading: HeadingLevel.HEADING_1 }),
                    ...(recRows.length > 0 ? [recsTable] : [new Paragraph('No specific recommendations available')])
                  ];
                  
                  // Add formatted AI Recommendations
                  if (aiRecs) {
                    const parsedRecs = parseMarkdownRecommendations(aiRecs);
                    docChildren.push(new Paragraph({ text: 'AI Recommendations', heading: HeadingLevel.HEADING_2 }));
                    parsedRecs.forEach((rec) => {
                      // Add recommendation title with severity
                      const titleText = rec.severity ? `[${rec.severity.toUpperCase()}] ${rec.title}` : rec.title;
                      docChildren.push(new Paragraph({ text: titleText, heading: HeadingLevel.HEADING_3 }));
                      
                      rec.items.forEach((item) => {
                        if (typeof item === 'string') {
                          // Legacy format - just text
                          docChildren.push(new Paragraph({ 
                            text: item,
                            bullet: { level: 0 }
                          }));
                        } else if (item.type === 'section') {
                          // Section header (Impact, How to Fix, Verification)
                          const sectionTitle = item.sectionType.charAt(0).toUpperCase() + item.sectionType.slice(1) + ':';
                          docChildren.push(new Paragraph({ 
                            text: sectionTitle,
                            heading: HeadingLevel.HEADING_4
                          }));
                          docChildren.push(new Paragraph({ text: item.content }));
                        } else if (item.type === 'code') {
                          // Code block
                          docChildren.push(new Paragraph({ 
                            text: item.language ? `Code (${item.language}):` : 'Code:',
                            heading: HeadingLevel.HEADING_4
                          }));
                          docChildren.push(new Paragraph({ 
                            text: item.content,
                            style: 'Code'
                          }));
                        } else if (item.type === 'bold') {
                          docChildren.push(new Paragraph({ 
                            children: [new TextRun({ text: item.content, bold: true })],
                            bullet: { level: 0 }
                          }));
                        } else if (item.type === 'text') {
                          docChildren.push(new Paragraph({ 
                            text: item.content,
                            bullet: { level: 0 }
                          }));
                        }
                      });
                    });
                  }
                  
                  // Add Azure Compliance Analysis Section
                  if (azureData && (userData?.role === 'compliance_team' || userData?.role === 'management_team' || userData?.role === 'it_team')) {
                    docChildren.push(new Paragraph({ text: 'Azure Compliance Analysis', heading: HeadingLevel.HEADING_1 }));
                    
                    // Document info table
                    const azureInfoTable = new Table({ rows: [
                      makeHeader(['Metric', 'Value']),
                      makeRow(['Document Name', azureData.document_name || 'N/A']),
                      makeRow(['Overall Score', `${azureData.overall_score || azureData.score || 0}/100`]),
                      makeRow(['Overall Status', azureData.overall_status || 'Unknown']),
                      makeRow(['Frameworks Analyzed', String(azureData.frameworks_analyzed || 0)]),
                      makeRow(['Analysis Date', azureData.analyzed_at ? new Date(azureData.analyzed_at).toLocaleDateString() : 'N/A'])
                    ] });
                    docChildren.push(azureInfoTable);
                    
                    // Framework Scores Table
                    if (azureData.framework_scores && Object.keys(azureData.framework_scores).length > 0) {
                      docChildren.push(new Paragraph({ text: 'Framework Compliance Scores', heading: HeadingLevel.HEADING_2 }));
                      const frameworkRows = [makeHeader(['Framework', 'Score', 'Status'])];
                      Object.entries(azureData.framework_scores).forEach(([framework, score]) => {
                        const status = score >= 80 ? 'Compliant' : score >= 60 ? 'Partial' : 'Non-Compliant';
                        const frameworkName = {
                          'gdpr': 'GDPR',
                          'iso27001': 'ISO 27001',
                          'iso27017': 'ISO 27017',
                          'iso27018': 'ISO 27018',
                          'azure': 'Azure Best Practices'
                        }[framework] || framework.toUpperCase();
                        frameworkRows.push(makeRow([frameworkName, `${score}/100`, status]));
                      });
                      docChildren.push(new Table({ rows: frameworkRows }));
                    }
                    
                    // Executive Summary
                    if (azureData.summary) {
                      docChildren.push(new Paragraph({ text: 'Executive Summary', heading: HeadingLevel.HEADING_2 }));
                      docChildren.push(new Paragraph(azureData.summary));
                    }
                    
                    // Framework-specific recommendations
                    if (azureData.frameworks && Object.keys(azureData.frameworks).length > 0) {
                      docChildren.push(new Paragraph({ text: 'Framework-Specific Recommendations', heading: HeadingLevel.HEADING_2 }));
                      
                      Object.entries(azureData.frameworks).forEach(([frameworkName, frameworkData]) => {
                        const frameworkDisplayName = {
                          'gdpr': 'GDPR',
                          'iso27001': 'ISO 27001',
                          'iso27017': 'ISO 27017',
                          'iso27018': 'ISO 27018',
                          'azure': 'Azure Best Practices'
                        }[frameworkName] || frameworkName.toUpperCase();
                        
                        docChildren.push(new Paragraph({ text: frameworkDisplayName, heading: HeadingLevel.HEADING_3 }));
                        
                        // Recommendation
                        if (frameworkData.recommendation) {
                          docChildren.push(new Paragraph({ 
                            children: [new TextRun({ text: 'Recommendation: ', bold: true }), new TextRun(frameworkData.recommendation)]
                          }));
                        }
                        
                        // Gaps
                        if (frameworkData.gaps && frameworkData.gaps.length > 0) {
                          docChildren.push(new Paragraph({ 
                            children: [new TextRun({ text: 'Gaps Identified:', bold: true })]
                          }));
                          frameworkData.gaps.forEach((gap) => {
                            docChildren.push(new Paragraph({ 
                              text: gap,
                              bullet: { level: 0 }
                            }));
                          });
                        }
                        
                        // Priority Actions
                        if (frameworkData.priority_actions && frameworkData.priority_actions.length > 0) {
                          docChildren.push(new Paragraph({ 
                            children: [new TextRun({ text: 'Priority Actions:', bold: true })]
                          }));
                          frameworkData.priority_actions.forEach((action, idx) => {
                            docChildren.push(new Paragraph(`${idx + 1}. ${action}`));
                          });
                        }
                      });
                    }
                  }
                  
                  // Add visual summary if available
                  if (imageRun) {
                    docChildren.push(new Paragraph({ text: 'Visual Summary', heading: HeadingLevel.HEADING_1 }));
                    docChildren.push(new Paragraph({ children: [imageRun] }));
                  }

                  const doc = new DocxDocument({
                    sections: [
                      {
                        properties: {},
                        children: docChildren
                      }
                    ]
                  });
                  const blob = await Packer.toBlob(doc);
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = 'Complytics-Dashboard-Report.docx';
                  document.body.appendChild(a);
                  a.click();
                  a.remove();
                    URL.revokeObjectURL(url);
                  }}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-border hover:bg-secondary"
                >
                  <FaFileWord />
                  <span>Download Full Report (Word)</span>
                </button>
              </div>
            </div>
          </motion.div>
        );
      case 'profile':
        return <Profile />;
      case 'azure':
        return <AzureADConnection />;
      case 'azure-config':
        return <AzureADConfiguration />;
      case 'logs':
        // Show different logs component based on role
        if (userData?.role === 'management_team') {
          return <ManagementLogs />;
        } else if (userData?.role === 'compliance_team') {
          return <ComplianceLogs />;
        } else {
          return <AzureADChangeLogs />;
        }
      case 'chatbot':
        return <ComplianceChat />;
      case 'testing':
        return <UiTesting />;
      case 'scan':
        return <ScheduleScan />;
      case 'azure-checker':
        return <AzureComplianceChecker />;
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Mobile Sidebar Toggle */}
      <div className="lg:hidden fixed top-4 left-4 z-50">
        <button
          onClick={() => setIsSidebarOpen(!isSidebarOpen)}
          className="p-2 rounded-lg bg-card shadow-lg"
        >
          {isSidebarOpen ? <FaTimes /> : <FaBars />}
        </button>
      </div>

      {/* Sidebar */}
      <motion.div
        initial={{ x: -300 }}
        animate={{ x: isSidebarOpen ? 0 : -300 }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className="fixed top-0 left-0 h-full w-64 bg-card shadow-lg z-40 lg:translate-x-0"
      >
        <div className="h-full flex flex-col">
          {/* Logo Section */}
          <div className="p-4 border-b border-border bg-card">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 rounded-md bg-primary flex items-center justify-center">
                <span className="text-white font-bold text-lg">C</span>
              </div>
              <span className="font-bold text-lg">Complytics</span>
            </div>
          </div>

          <nav className="flex-1 p-4 space-y-2">
            {getSidebarItems().map((item) => (
              <motion.button
                key={item.id}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center justify-start space-x-3 p-3 rounded-lg transition-colors text-left ${
                  activeTab === item.id
                    ? 'bg-primary text-primary-foreground'
                    : 'hover:bg-secondary'
                }`}
              >
                <span className="text-lg">{item.icon}</span>
                <span className="text-left">{item.label}</span>
              </motion.button>
            ))}
          </nav>

          <div className="p-4 border-t border-border">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleLogout}
              className="w-full flex items-center justify-start space-x-3 p-3 rounded-lg text-destructive hover:bg-destructive/10 text-left"
            >
              <FaSignOutAlt />
              <span className="text-left">Logout</span>
            </motion.button>
          </div>
        </div>
      </motion.div>

      {/* Main Content */}
      <div className={`lg:ml-64 transition-all duration-300 ${isSidebarOpen ? 'ml-64' : 'ml-0'}`}>
        <div className="p-6">
          {renderContent()}
        </div>
      </div>
    </div>
  );
};

export default UserDashboard; 