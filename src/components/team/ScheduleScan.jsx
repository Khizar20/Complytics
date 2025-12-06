import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { FaCalendarAlt, FaClock, FaList, FaTrash, FaSpinner, FaGlobe, FaCheckCircle, FaExclamationCircle } from 'react-icons/fa';
import { useAuth } from '../../context/AuthContext';
import { buildApiUrl } from '@/lib/api';

const ScheduleScan = () => {
  const { authToken } = useAuth();
  const apiBase = buildApiUrl('/api');
  const [runAt, setRunAt] = useState(''); // HTML datetime-local value (local time)
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [schedules, setSchedules] = useState([]);
  const [scanNowLoading, setScanNowLoading] = useState(false);
  const [showScanNowModal, setShowScanNowModal] = useState(false);
  const [modalUrl, setModalUrl] = useState('');
  const [modalError, setModalError] = useState(null);
  const [modalSubmitting, setModalSubmitting] = useState(false);
  const [showSuccessPopup, setShowSuccessPopup] = useState(false);
  
  // New state for URL selection
  const [usePreviousUrl, setUsePreviousUrl] = useState(true);
  const [scheduleUrl, setScheduleUrl] = useState('');
  const [previousUrl, setPreviousUrl] = useState('');

  const fetchSchedules = async () => {
    try {
      const resp = await fetch(`${apiBase}/ui/schedules`, {
        headers: {
          'Authorization': `Bearer ${authToken}`,
        }
      });
      if (!resp.ok) throw new Error(await resp.text() || 'Failed to load schedules');
      const data = await resp.json();
      const items = Array.isArray(data.schedules) ? data.schedules : [];
      const nowTs = Math.floor(Date.now() / 1000);
      // Hide past schedules from the list
      setSchedules(items.filter((s) => (s?.scheduled_for || 0) >= nowTs));
    } catch (e) {
      // Non-blocking
    }
  };

  useEffect(() => {
    if (authToken) fetchSchedules();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authToken]);

  // Load previous URL from localStorage on mount
  useEffect(() => {
    try {
      const lastResult = localStorage.getItem('uiTesting:lastResult');
      if (lastResult) {
        const parsed = JSON.parse(lastResult);
        if (parsed.url) {
          setPreviousUrl(parsed.url);
          setScheduleUrl(parsed.url); // Set as default if using previous URL
        }
      }
    } catch (e) {
      // Ignore localStorage errors
    }
  }, []);

  const toIsoUtc = (localValue) => {
    // localValue like '2025-10-01T14:30'
    if (!localValue) return '';
    const dt = new Date(localValue);
    return dt.toISOString();
  };

  const minDateTimeLocal = () => {
    // Return current local datetime in input-compatible format YYYY-MM-DDTHH:MM
    const now = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    const yyyy = now.getFullYear();
    const mm = pad(now.getMonth() + 1);
    const dd = pad(now.getDate());
    const hh = pad(now.getHours());
    const mi = pad(now.getMinutes());
    return `${yyyy}-${mm}-${dd}T${hh}:${mi}`;
  };

  const handleSchedule = async () => {
    if (!runAt) {
      setError('Please select a date and time');
      return;
    }
    
    // Validate URL if not using previous URL
    if (!usePreviousUrl) {
      const normalized = normalizeUrl(scheduleUrl);
      if (!normalized) {
        setError('Please enter a valid URL (e.g., https://example.com)');
        return;
      }
    }
    
    // Prevent scheduling in the past on the client as well
    try {
      const selected = new Date(runAt).getTime();
      const now = Date.now();
      if (!isFinite(selected) || selected <= now) {
        setError('Please select a future date and time');
        return;
      }
    } catch {
      // ignore, backend validates too
    }
    setError(null);
    setSuccess(null);
    setLoading(true);
    try {
      const run_at_iso = toIsoUtc(runAt);
      const requestBody = { run_at_iso };
      
      // Include URL if not using previous URL
      if (!usePreviousUrl && scheduleUrl) {
        const normalized = normalizeUrl(scheduleUrl);
        if (normalized) {
          requestBody.url = normalized;
        }
      }
      
      const resp = await fetch(`${apiBase}/ui/schedule`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`,
        },
        body: JSON.stringify(requestBody),
      });
      if (!resp.ok) throw new Error(await resp.text() || 'Failed to schedule scan');
      await resp.json();
      setSuccess('Compliance scan scheduled successfully. You will receive an email with website testing and Azure compliance results after it completes.');
      setRunAt('');
      if (!usePreviousUrl) {
        setScheduleUrl('');
      }
      fetchSchedules();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleScanNow = async () => {
    setError(null);
    setSuccess(null);
    setScanNowLoading(true);
    try {
      const resp = await fetch(`${apiBase}/ui/scan-now`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
        },
      });
      if (!resp.ok) {
        const t = await resp.text();
        // If no previous site, guide user to UI Testing page
        if (t && t.toLowerCase().includes('no previous website')) {
          // open modal to capture URL and run scan immediately
          setShowScanNowModal(true);
          return;
        }
        throw new Error(t || 'Scan failed');
      }
      await resp.json();
      setSuccess('Whole-site scan completed. Dashboard will reflect the latest results.');
      setShowSuccessPopup(true);
      setTimeout(() => setShowSuccessPopup(false), 2500);
      // Refresh schedules and dashboard widgets will auto-refresh via polling
      fetchSchedules();
    } catch (e) {
      setError(e.message);
    } finally {
      setScanNowLoading(false);
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

  const submitScanNowWithUrl = async () => {
    const normalized = normalizeUrl(modalUrl);
    if (!normalized) {
      setModalError('Please enter a valid URL (e.g., https://example.com)');
      return;
    }
    setModalError(null);
    setModalSubmitting(true);
    try {
      const resp = await fetch(`${apiBase}/ui/scan-site`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`,
        },
        body: JSON.stringify({ 
          url: normalized, 
          scan_mode: 'all',
          max_pages: 50,
          max_depth: 3,
          parallel_scans: 3,
          use_selenium_crawler: false
        }),
      });
      if (!resp.ok) {
        const t = await resp.text();
        throw new Error(t || 'Scan failed');
      }
      await resp.json();
      setShowScanNowModal(false);
      setModalUrl('');
      setSuccess('Whole-site scan completed. Dashboard will reflect the latest results.');
      setShowSuccessPopup(true);
      setTimeout(() => setShowSuccessPopup(false), 2500);
      fetchSchedules();
    } catch (e) {
      setModalError(e.message);
    } finally {
      setModalSubmitting(false);
    }
  };

  const handleCancel = async (id) => {
    try {
      const resp = await fetch(`${apiBase}/ui/schedules/${id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${authToken}`,
        },
      });
      if (!resp.ok) throw new Error(await resp.text() || 'Failed to cancel');
      await resp.json();
      fetchSchedules();
    } catch (e) {
      // surface lightly
      setError(e.message);
    }
  };

  const formatUtc = (ts) => {
    try {
      return new Date((ts || 0) * 1000).toUTCString();
    } catch {
      return '';
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="space-y-8"
    >
      {/* Header Section */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-foreground mb-2">Schedule Compliance Scan</h2>
          <p className="text-muted-foreground">Schedule automated whole-site scans for your website and Azure compliance analysis</p>
        </div>
      </div>

      {/* Schedule Form Card */}
      <div className="bg-card rounded-xl shadow-lg border border-border overflow-hidden">
        {/* Card Header */}
        <div className="bg-gradient-to-r from-primary/10 to-primary/5 px-6 py-5 border-b border-border">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-primary/10 rounded-lg">
              <FaCalendarAlt className="text-xl text-primary" />
            </div>
            <div>
              <h3 className="text-xl font-semibold text-foreground">Schedule a One-Time Compliance Scan</h3>
              <p className="text-sm text-muted-foreground mt-0.5">Runs comprehensive website testing and Azure compliance analysis on the selected date/time</p>
            </div>
          </div>
        </div>

        {/* Card Body */}
        <div className="p-6 space-y-6">
          {/* Info about Azure compliance */}
          <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
            <p className="text-sm text-blue-700 dark:text-blue-300">
              <strong>Note:</strong> Scheduled scans automatically include Azure compliance analysis if Azure settings have been fetched. 
              The email notification will include both website testing results and Azure compliance check results.
            </p>
          </div>
          {/* Alert Messages */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-start space-x-3 p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800"
            >
              <FaExclamationCircle className="text-red-600 dark:text-red-400 mt-0.5 flex-shrink-0" />
              <p className="text-sm text-red-700 dark:text-red-300 flex-1">{error}</p>
            </motion.div>
          )}
          {success && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-start space-x-3 p-4 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800"
            >
              <FaCheckCircle className="text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
              <p className="text-sm text-green-700 dark:text-green-300 flex-1">{success}</p>
            </motion.div>
          )}

          {/* URL Selection Section */}
          <div className="space-y-4">
            <div className="flex items-center space-x-3">
              <input
                type="checkbox"
                id="usePreviousUrl"
                checked={usePreviousUrl}
                onChange={(e) => {
                  setUsePreviousUrl(e.target.checked);
                  if (e.target.checked && previousUrl) {
                    setScheduleUrl(previousUrl);
                  } else if (!e.target.checked) {
                    setScheduleUrl('');
                  }
                }}
                className="w-4 h-4 rounded border-border text-primary focus:ring-2 focus:ring-primary/20 cursor-pointer"
              />
              <label htmlFor="usePreviousUrl" className="text-sm font-medium text-foreground cursor-pointer">
                Use previously scanned website
              </label>
            </div>
            
            {usePreviousUrl ? (
              previousUrl ? (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg"
                >
                  <div className="flex items-start space-x-2">
                    <FaGlobe className="text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold text-blue-600 dark:text-blue-400 mb-1 uppercase tracking-wide">Previous Website</p>
                      <p className="text-sm text-blue-800 dark:text-blue-200 break-all font-mono">{previousUrl}</p>
                    </div>
                  </div>
                </motion.div>
              ) : (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg"
                >
                  <div className="flex items-start space-x-2">
                    <FaExclamationCircle className="text-yellow-600 dark:text-yellow-400 mt-0.5 flex-shrink-0" />
                    <p className="text-sm text-yellow-700 dark:text-yellow-300 flex-1">
                      No previous website found. Please uncheck the option above and enter a URL manually.
                    </p>
                  </div>
                </motion.div>
              )
            ) : (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="space-y-2"
              >
                <label className="block text-sm font-semibold text-foreground">
                  Website URL
                </label>
                <div className="relative">
                  <FaGlobe className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground text-sm" />
                  <input
                    type="text"
                    value={scheduleUrl}
                    onChange={(e) => setScheduleUrl(e.target.value)}
                    placeholder="https://example.com"
                    className="w-full pl-10 pr-4 py-3 border border-border rounded-lg bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
                  />
                </div>
              </motion.div>
            )}
          </div>

          {/* Date/Time and Actions */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 pt-4 border-t border-border">
            <div className="lg:col-span-2 space-y-2">
              <label className="block text-sm font-semibold text-foreground">
                Date & Time
              </label>
              <div className="relative">
                <FaClock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground text-sm" />
                <input
                  type="datetime-local"
                  value={runAt}
                  onChange={(e) => setRunAt(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 border border-border rounded-lg bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
                  min={minDateTimeLocal()}
                />
              </div>
            </div>
            <div className="flex flex-col gap-3">
              <button
                disabled={loading}
                onClick={handleSchedule}
                className="w-full px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 font-medium transition-all shadow-sm hover:shadow-md"
              >
                {loading ? (
                  <>
                    <FaSpinner className="animate-spin" />
                    <span>Scheduling...</span>
                  </>
                ) : (
                  <>
                    <FaClock />
                    <span>Schedule Scan</span>
                  </>
                )}
              </button>
              <button
                disabled={scanNowLoading}
                onClick={handleScanNow}
                className="w-full px-6 py-3 border-2 border-border rounded-lg hover:bg-secondary/50 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 font-medium transition-all"
              >
                {scanNowLoading ? (
                  <>
                    <FaSpinner className="animate-spin" />
                    <span>Scanning…</span>
                  </>
                ) : (
                  <>
                    <FaGlobe />
                    <span>Scan Now</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Scheduled Scans List Card */}
      <div className="bg-card rounded-xl shadow-lg border border-border overflow-hidden">
        {/* Card Header */}
        <div className="bg-gradient-to-r from-primary/10 to-primary/5 px-6 py-5 border-b border-border">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-primary/10 rounded-lg">
                <FaList className="text-xl text-primary" />
              </div>
              <div>
                <h3 className="text-xl font-semibold text-foreground">Scheduled Scans</h3>
                <p className="text-sm text-muted-foreground mt-0.5">Manage your upcoming scans</p>
              </div>
            </div>
            {schedules.length > 0 && (
              <div className="px-3 py-1 bg-primary/10 rounded-full">
                <span className="text-sm font-semibold text-primary">{schedules.length}</span>
              </div>
            )}
          </div>
        </div>

        {/* Card Body */}
        <div className="p-6">
          {schedules.length === 0 ? (
            <div className="text-center py-12">
              <FaList className="text-4xl text-muted-foreground/30 mx-auto mb-4" />
              <p className="text-muted-foreground font-medium">No scheduled scans</p>
              <p className="text-sm text-muted-foreground mt-1">Schedule your first scan above to get started</p>
            </div>
          ) : (
            <div className="space-y-3">
              {schedules.map((s, index) => (
                <motion.div
                  key={s._id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="flex items-center justify-between p-4 border border-border rounded-lg hover:border-primary/30 hover:shadow-sm transition-all bg-background/50"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-3 mb-2">
                      <div className="p-1.5 bg-primary/10 rounded">
                        <FaClock className="text-primary text-xs" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-semibold text-foreground truncate">
                          {formatUtc(s.scheduled_for)}
                        </div>
                        <div className="flex items-center space-x-2 mt-1">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                            s.status === 'scheduled' 
                              ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                              : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300'
                          }`}>
                            {s.status}
                          </span>
                        </div>
                      </div>
                    </div>
                    {s.url && (
                      <div className="ml-8 mt-2 flex items-start space-x-2">
                        <FaGlobe className="text-muted-foreground text-xs mt-0.5 flex-shrink-0" />
                        <p className="text-xs text-muted-foreground break-all font-mono">{s.url}</p>
                      </div>
                    )}
                  </div>
                  {s.status === 'scheduled' && (
                    <button
                      onClick={() => handleCancel(s._id)}
                      className="ml-4 px-4 py-2 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center gap-2 transition-colors font-medium text-sm"
                    >
                      <FaTrash className="text-xs" />
                      <span>Cancel</span>
                    </button>
                  )}
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </div>
      {/* Scan Now Modal */}
      {showScanNowModal && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
          onClick={() => {
            if (!modalSubmitting) {
              setShowScanNowModal(false);
              setModalUrl('');
              setModalError(null);
            }
          }}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-md bg-card rounded-xl shadow-2xl border border-border overflow-hidden"
          >
            {/* Modal Header */}
            <div className="bg-gradient-to-r from-primary/10 to-primary/5 px-6 py-4 border-b border-border">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-primary/10 rounded-lg">
                  <FaGlobe className="text-xl text-primary" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-foreground">Enter Website URL</h3>
                  <p className="text-xs text-muted-foreground mt-0.5">No previous website found</p>
                </div>
              </div>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-4">
              <p className="text-sm text-muted-foreground">
                Provide your site URL to run a comprehensive whole-site scan now.
              </p>
              
              {modalError && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex items-start space-x-2 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800"
                >
                  <FaExclamationCircle className="text-red-600 dark:text-red-400 mt-0.5 flex-shrink-0" />
                  <p className="text-sm text-red-700 dark:text-red-300 flex-1">{modalError}</p>
                </motion.div>
              )}
              
              <div className="space-y-2">
                <label className="block text-sm font-semibold text-foreground">
                  Website URL
                </label>
                <div className="relative">
                  <FaGlobe className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground text-sm" />
                  <input
                    value={modalUrl}
                    onChange={(e) => setModalUrl(e.target.value)}
                    placeholder="https://example.com"
                    className="w-full pl-10 pr-4 py-3 border border-border rounded-lg bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
                    onKeyPress={(e) => {
                      if (e.key === 'Enter' && !modalSubmitting && modalUrl.trim()) {
                        submitScanNowWithUrl();
                      }
                    }}
                  />
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 bg-muted/30 border-t border-border flex items-center justify-end gap-3">
              <button
                onClick={() => {
                  setShowScanNowModal(false);
                  setModalUrl('');
                  setModalError(null);
                }}
                disabled={modalSubmitting}
                className="px-4 py-2 border border-border rounded-lg hover:bg-secondary disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
              >
                Cancel
              </button>
              <button
                onClick={submitScanNowWithUrl}
                disabled={modalSubmitting || !modalUrl.trim()}
                className="px-6 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-all shadow-sm hover:shadow-md font-medium"
              >
                {modalSubmitting ? (
                  <>
                    <FaSpinner className="animate-spin" />
                    <span>Scanning…</span>
                  </>
                ) : (
                  <>
                    <FaGlobe />
                    <span>Scan Now</span>
                  </>
                )}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}

      {/* Success Popup */}
      {showSuccessPopup && (
        <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 20, scale: 0.95 }}
          className="fixed bottom-6 right-6 z-50 px-6 py-4 bg-green-600 text-white rounded-lg shadow-xl flex items-center space-x-3 max-w-md"
        >
          <FaCheckCircle className="text-xl flex-shrink-0" />
          <p className="font-medium">Whole-site scan completed successfully.</p>
        </motion.div>
      )}
    </motion.div>
  );
};

export default ScheduleScan;


