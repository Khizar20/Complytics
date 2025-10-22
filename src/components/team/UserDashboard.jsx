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
  FaEyeSlash,
  FaKey,
  FaBuilding,
  FaIdCard,
  FaSave,
  FaSpinner,
  FaLock,
  FaUsers,
  FaClipboardList
} from 'react-icons/fa';
import { FaFilePdf, FaFileWord } from 'react-icons/fa';
import Profile from '../auth/Profile';
import ComplianceChat from './ComplianceChat';
import UiTesting from './UiTesting';
import ScheduleScan from './ScheduleScan';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';
import autoTable from 'jspdf-autotable';
import { Document as DocxDocument, Packer, Paragraph, HeadingLevel, TextRun, ImageRun, Table, TableRow, TableCell, WidthType } from 'docx';

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

        const response = await fetch('http://localhost:8000/api/compliance/analytics', {
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
        const resp = await fetch('http://localhost:8000/api/ui/site/latest', {
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
      const missing = missingHeaders.length;
      securityScore = Math.max(0, 100 - missing * 15);
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
        const response = await fetch('http://localhost:8000/api/azure/status', {
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
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchStatusAndConfig = async () => {
      try {
        setLoading(true);
        // First check connection status
        const statusResponse = await fetch('http://localhost:8000/api/azure/status', {
          headers: {
            'Authorization': `Bearer ${authToken}`
          }
        });
        
        if (statusResponse.ok) {
          const statusData = await statusResponse.json();
          setIsConnected(!!statusData.connected);
          
          if (statusData.connected) {
            // Fetch Azure AD configuration
            const configResponse = await fetch('http://localhost:8000/api/azure/config', {
              headers: {
                'Authorization': `Bearer ${authToken}`
              }
            });
            
            if (configResponse.ok) {
              const data = await configResponse.json();
              setConfigData(data);
            } else {
              setError('Failed to fetch Azure AD configuration');
            }
          }
        } else {
          setIsConnected(false);
        }
      } catch (e) {
        setError('Failed to check Azure AD status');
        setIsConnected(false);
      } finally {
        setLoading(false);
      }
    };
    
    if (authToken) {
      fetchStatusAndConfig();
    }
  }, [authToken]);

  const handleConnectClick = () => {
    // Dispatch event to switch to Azure tab
    window.dispatchEvent(new CustomEvent('setActiveTab', { detail: 'azure' }));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <FaSpinner className="animate-spin text-2xl text-primary" />
      </div>
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

      {/* ISO 27017 Compliance Section */}
      {configData?.compliance_check && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="mt-8"
        >
          <div className="flex items-center space-x-4 mb-6">
            <div className="p-3 bg-green-100 dark:bg-green-900/20 rounded-lg">
              <FaShieldAlt className="text-2xl text-green-600 dark:text-green-400" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-foreground">ISO 27017 Compliance Assessment</h2>
              <p className="text-muted-foreground">Azure AD security compliance against ISO 27017 standards</p>
            </div>
          </div>

          {/* Compliance Score Overview */}
          <motion.div
            whileHover={{ scale: 1.01 }}
            className="p-6 bg-card rounded-xl shadow-lg border border-border mb-6"
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Compliance Overview</h3>
              <div className="text-right">
                <div className="text-3xl font-bold text-primary">
                  {configData.compliance_check.summary?.compliance_score || 0}%
                </div>
                <div className="text-sm text-muted-foreground">Compliance Score</div>
              </div>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 bg-green-100 dark:bg-green-900/20 rounded-lg">
                <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                  {configData.compliance_check.summary?.compliant_count || 0}
                </div>
                <div className="text-sm text-green-700 dark:text-green-300">Compliant</div>
              </div>
              <div className="p-4 bg-red-100 dark:bg-red-900/20 rounded-lg">
                <div className="text-2xl font-bold text-red-600 dark:text-red-400">
                  {configData.compliance_check.summary?.non_compliant_count || 0}
                </div>
                <div className="text-sm text-red-700 dark:text-red-300">Non-Compliant</div>
              </div>
              <div className="p-4 bg-gray-100 dark:bg-gray-900/20 rounded-lg">
                <div className="text-2xl font-bold text-gray-600 dark:text-gray-400">
                  {configData.compliance_check.summary?.not_applicable_count || 0}
                </div>
                <div className="text-sm text-gray-700 dark:text-gray-300">Not Applicable</div>
              </div>
            </div>
          </motion.div>

          {/* Non-Compliant Rules - Recommendations */}
          {configData.compliance_check.non_compliant?.length > 0 && (
            <motion.div
              whileHover={{ scale: 1.01 }}
              className="p-6 bg-card rounded-xl shadow-lg border border-border mb-6"
            >
              <div className="flex items-center space-x-3 mb-4">
                <FaExclamationTriangle className="text-xl text-red-500" />
                <h3 className="text-lg font-semibold">Security Recommendations</h3>
              </div>
              <div className="space-y-4">
                {configData.compliance_check.non_compliant.map((rule, index) => (
                  <div key={index} className="p-4 bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800 rounded-lg">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <h4 className="font-semibold text-red-800 dark:text-red-200">{rule.title}</h4>
                        <p className="text-sm text-red-700 dark:text-red-300 mt-1">{rule.description}</p>
                      </div>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        rule.severity === 'high' ? 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400' :
                        rule.severity === 'medium' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400' :
                        'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400'
                      }`}>
                        {rule.severity?.toUpperCase()}
                      </span>
                    </div>
                    <div className="mt-3 p-3 bg-white dark:bg-gray-800 rounded border">
                      <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Recommended Action:</div>
                      <p className="text-sm text-gray-600 dark:text-gray-400">{rule.remediation}</p>
                    </div>
                    <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                      <span className="font-medium">Control ID:</span> {rule.control_id} | 
                      <span className="font-medium ml-2">Current Value:</span> {String(rule.current_value || 'N/A')} | 
                      <span className="font-medium ml-2">Expected:</span> {String(rule.expected_value || 'N/A')}
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          {/* Compliant Rules */}
          {configData.compliance_check.compliant?.length > 0 && (
            <motion.div
              whileHover={{ scale: 1.01 }}
              className="p-6 bg-card rounded-xl shadow-lg border border-border mb-6"
            >
              <div className="flex items-center space-x-3 mb-4">
                <FaCheckCircle className="text-xl text-green-500" />
                <h3 className="text-lg font-semibold">Compliant Controls</h3>
              </div>
              <div className="space-y-3">
                {configData.compliance_check.compliant.map((rule, index) => (
                  <div key={index} className="p-3 bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-800 rounded-lg">
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="font-medium text-green-800 dark:text-green-200">{rule.title}</h4>
                        <p className="text-xs text-green-600 dark:text-green-400 mt-1">{rule.control_id}</p>
                      </div>
                      <FaCheckCircle className="text-green-500" />
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          {/* Compliance Checklist */}
          <motion.div
            whileHover={{ scale: 1.01 }}
            className="p-6 bg-card rounded-xl shadow-lg border border-border"
          >
            <div className="flex items-center space-x-3 mb-4">
              <FaClipboardList className="text-xl text-primary" />
              <h3 className="text-lg font-semibold">Compliance Checklist</h3>
            </div>
            <div className="space-y-3">
              {configData.compliance_check.non_compliant?.map((rule, index) => (
                <div key={index} className="flex items-center space-x-3 p-3 bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800 rounded-lg">
                  <input 
                    type="checkbox" 
                    className="w-4 h-4 text-red-600 bg-gray-100 border-gray-300 rounded focus:ring-red-500 dark:focus:ring-red-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
                    disabled
                  />
                  <div className="flex-1">
                    <label className="text-sm font-medium text-red-800 dark:text-red-200">
                      {rule.title}
                    </label>
                    <p className="text-xs text-red-600 dark:text-red-400 mt-1">
                      {rule.remediation}
                    </p>
                  </div>
                  <span className="text-xs text-red-600 dark:text-red-400 font-medium">
                    {rule.severity?.toUpperCase()}
                  </span>
                </div>
              ))}
              {configData.compliance_check.compliant?.map((rule, index) => (
                <div key={`compliant-${index}`} className="flex items-center space-x-3 p-3 bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-800 rounded-lg">
                  <input 
                    type="checkbox" 
                    checked
                    readOnly
                    className="w-4 h-4 text-green-600 bg-gray-100 border-gray-300 rounded focus:ring-green-500 dark:focus:ring-green-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
                  />
                  <div className="flex-1">
                    <label className="text-sm font-medium text-green-800 dark:text-green-200">
                      {rule.title}
                    </label>
                    <p className="text-xs text-green-600 dark:text-green-400 mt-1">
                      ✓ Compliant
                    </p>
                  </div>
                  <FaCheckCircle className="text-green-500" />
                </div>
              ))}
            </div>
          </motion.div>
        </motion.div>
      )}
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
        const response = await fetch('http://localhost:8000/api/azure/status', {
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
      const response = await fetch('http://localhost:8000/api/azure/connect', {
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
      const response = await fetch('http://localhost:8000/api/azure/disconnect', {
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

        const response = await fetch('http://localhost:8000/team/user-data', {
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
        { id: 'chatbot', icon: <FaRobot />, label: 'Compliance Chatbot' },
      ],
      'management_team': [],
      'compliance_team': [
        { id: 'chatbot', icon: <FaRobot />, label: 'Compliance Chatbot' },
        { id: 'testing', icon: <FaDesktop />, label: 'UI Testing' },
        { id: 'scan', icon: <FaCalendarAlt />, label: 'Schedule Scan' },
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
              <div className="flex items-center justify-start gap-3 no-export">
                <button
                  onClick={async () => {
                  // Fetch structured data
                  const headers = authToken ? { 'Authorization': `Bearer ${authToken}` } : {};
                  const [analyticsResp, uiResp] = await Promise.all([
                    fetch('http://localhost:8000/api/compliance/analytics', { headers }),
                    fetch('http://localhost:8000/api/ui/site/latest', { headers })
                  ]);
                  const analytics = analyticsResp.ok ? await analyticsResp.json() : {};
                  const uiLatest = uiResp.ok ? await uiResp.json() : {};
                  const ui = uiLatest?.result || {};

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
                  let y = 18;

                  // Title + Date
                  pdf.setFontSize(18);
                  pdf.text('Complytics Dashboard Report', 14, y);
                  y += 8;
                  pdf.setFontSize(10);
                  pdf.text(new Date().toLocaleString(), 14, y);
                  y += 10;

                  // Chatbot Analytics
                  pdf.setFontSize(14);
                  pdf.text('Chatbot Analytics', 14, y);
                  y += 4;
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
                      0: { cellWidth: 80, halign: 'left' },
                      1: { cellWidth: 40, halign: 'right' }
                    },
                    theme: 'striped',
                    margin: { left: 14, right: 14 }
                  });
                  y = (pdf.lastAutoTable && pdf.lastAutoTable.finalY ? pdf.lastAutoTable.finalY : y) + 8;

                  // UI Testing Summary
                  pdf.setFontSize(14);
                  pdf.text(isWholeSiteScan ? 'Whole-Site Scan Summary' : 'UI Testing Summary', 14, y);
                  y += 4;
                  
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
                        0: { cellWidth: 80, halign: 'left' },
                        1: { cellWidth: 40, halign: 'right' }
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
                      0: { cellWidth: 80, halign: 'left' },
                      1: { cellWidth: 40, halign: 'right' }
                    },
                    theme: 'striped',
                    margin: { left: 14, right: 14 }
                  });
                  y = (pdf.lastAutoTable && pdf.lastAutoTable.finalY ? pdf.lastAutoTable.finalY : y) + 4;

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
                      0: { cellWidth: 80, halign: 'left' },
                      1: { cellWidth: 40, halign: 'right' }
                    },
                    theme: 'grid',
                    margin: { left: 14, right: 14 }
                  });
                  y = (pdf.lastAutoTable && pdf.lastAutoTable.finalY ? pdf.lastAutoTable.finalY : y) + 8;

                  // Recommendations
                  pdf.setFontSize(14);
                  pdf.text('Recommendations', 14, y);
                  y += 4;
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
                  if (aiRecs) {
                    pdf.setFontSize(12);
                    pdf.text('AI Recommendations', 14, y);
                    y += 6;
                    pdf.setFontSize(10);
                    const lines = pdf.splitTextToSize(aiRecs, pageWidth - 28);
                    lines.forEach((line) => {
                      if (y > pdf.internal.pageSize.getHeight() - 20) { pdf.addPage(); y = 20; }
                      pdf.text(line, 14, y);
                      y += 5;
                    });
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

                    pdf.save('Complytics-Dashboard-Report.pdf');
                  }}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90"
                >
                  <FaFilePdf />
                  <span>Download PDF</span>
                </button>
                <button
                  onClick={async () => {
                  // Fetch structured data
                  const headers = authToken ? { 'Authorization': `Bearer ${authToken}` } : {};
                  const [analyticsResp, uiResp] = await Promise.all([
                    fetch('http://localhost:8000/api/compliance/analytics', { headers }),
                    fetch('http://localhost:8000/api/ui/site/latest', { headers })
                  ]);
                  const analytics = analyticsResp.ok ? await analyticsResp.json() : {};
                  const uiLatest = uiResp.ok ? await uiResp.json() : {};
                  const ui = uiLatest?.result || {};

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

                  const doc = new DocxDocument({
                    sections: [
                      {
                        properties: {},
                        children: [
                          new Paragraph({ text: 'Complytics Dashboard Report', heading: HeadingLevel.TITLE }),
                          new Paragraph({ children: [new TextRun({ text: new Date().toLocaleString(), italics: true })] }),
                          new Paragraph({ text: 'Chatbot Analytics', heading: HeadingLevel.HEADING_1 }),
                          analyticsTable,
                          new Paragraph({ text: 'UI Testing Summary', heading: HeadingLevel.HEADING_1 }),
                          severityTable,
                          securityTable,
                          new Paragraph({ text: 'Recommendations', heading: HeadingLevel.HEADING_1 }),
                          ...(recRows.length > 0 ? [recsTable] : [new Paragraph('No specific recommendations available')]),
                          ...(aiRecs ? [new Paragraph({ text: 'AI Recommendations', heading: HeadingLevel.HEADING_2 }), new Paragraph(aiRecs)] : []),
                          ...(imageRun ? [new Paragraph({ text: 'Visual Summary', heading: HeadingLevel.HEADING_1 }), new Paragraph({ children: [imageRun] })] : [])
                        ]
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
                  <span>Download Word</span>
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
      case 'chatbot':
        return <ComplianceChat />;
      case 'testing':
        return <UiTesting />;
      case 'scan':
        return <ScheduleScan />;
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
                className={`w-full flex items-center space-x-3 p-3 rounded-lg transition-colors ${
                  activeTab === item.id
                    ? 'bg-primary text-primary-foreground'
                    : 'hover:bg-secondary'
                }`}
              >
                <span className="text-lg">{item.icon}</span>
                <span>{item.label}</span>
              </motion.button>
            ))}
          </nav>

          <div className="p-4 border-t border-border">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleLogout}
              className="w-full flex items-center space-x-3 p-3 rounded-lg text-destructive hover:bg-destructive/10"
            >
              <FaSignOutAlt />
              <span>Logout</span>
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