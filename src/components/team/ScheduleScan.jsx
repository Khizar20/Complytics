import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { FaCalendarAlt, FaClock, FaList, FaTrash, FaSpinner } from 'react-icons/fa';
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
      setSuccess('Whole-site scan scheduled successfully. You will receive an email after it completes.');
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
      className="space-y-6"
    >
      <h2 className="text-2xl font-bold text-foreground">Schedule Compliance Scan</h2>

      <div className="p-6 bg-card rounded-xl shadow-lg">
        <div className="flex items-center space-x-4 mb-4">
          <FaCalendarAlt className="text-2xl text-primary" />
          <div>
            <h3 className="text-lg font-semibold">Schedule a One-Time Whole-Site Scan</h3>
            <p className="text-muted-foreground">Runs comprehensive website testing on the selected date/time</p>
          </div>
        </div>

        {error && (
          <div className="mb-3 p-3 rounded bg-red-50 text-red-700 text-sm">{error}</div>
        )}
        {success && (
          <div className="mb-3 p-3 rounded bg-green-50 text-green-700 text-sm">{success}</div>
        )}

        {/* URL Selection Section */}
        <div className="mb-4 space-y-3">
          <div className="flex items-center space-x-2">
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
              className="rounded border-border"
            />
            <label htmlFor="usePreviousUrl" className="text-sm font-medium text-foreground">
              Use previously scanned website
            </label>
          </div>
          
          {usePreviousUrl ? (
            previousUrl ? (
              <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                <p className="text-xs text-blue-600 dark:text-blue-400 mb-1 font-medium">Previous Website:</p>
                <p className="text-sm text-blue-800 dark:text-blue-200 break-all">{previousUrl}</p>
              </div>
            ) : (
              <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                <p className="text-sm text-yellow-700 dark:text-yellow-300">
                  No previous website found. Please uncheck the option above and enter a URL manually.
                </p>
              </div>
            )
          ) : (
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">
                Website URL
              </label>
              <input
                type="text"
                value={scheduleUrl}
                onChange={(e) => setScheduleUrl(e.target.value)}
                placeholder="https://example.com"
                className="w-full px-3 py-2 border border-border rounded-md bg-background focus:ring-2 focus:ring-primary/20 focus:border-primary"
              />
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
          <div className="md:col-span-2">
            <label className="block text-sm mb-1">Date & Time</label>
            <input
              type="datetime-local"
              value={runAt}
              onChange={(e) => setRunAt(e.target.value)}
              className="w-full p-2 border border-border rounded"
            min={minDateTimeLocal()}
            />
          </div>
          <div>
            <button
              disabled={loading}
              onClick={handleSchedule}
              className="w-full px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 flex items-center justify-center gap-2"
            >
              <FaClock /> {loading ? 'Scheduling...' : 'Schedule Scan'}
            </button>
          <button
            disabled={scanNowLoading}
            onClick={handleScanNow}
            className="mt-2 w-full px-4 py-2 border border-border rounded-lg hover:bg-secondary flex items-center justify-center gap-2"
          >
            {scanNowLoading ? (<><FaSpinner className="animate-spin" /> Scanning…</>) : 'Scan Now (Whole-Site)'}
          </button>
          </div>
        </div>
      </div>

      <div className="p-6 bg-card rounded-xl shadow-lg">
        <div className="flex items-center space-x-4 mb-4">
          <FaList className="text-2xl text-primary" />
          <div>
            <h3 className="text-lg font-semibold">Scheduled Scans</h3>
            <p className="text-muted-foreground">Upcoming schedules</p>
          </div>
        </div>

        <div className="space-y-3">
          {schedules.length === 0 && (
            <div className="text-sm text-muted-foreground">No schedules.</div>
          )}
          {schedules.map((s) => (
            <div key={s._id} className="flex items-center justify-between p-3 border border-border rounded-lg">
              <div className="flex-1">
                <div className="text-sm font-medium">{formatUtc(s.scheduled_for)}</div>
                <div className="text-xs text-muted-foreground">Status: {s.status}</div>
                {s.url && (
                  <div className="text-xs text-muted-foreground mt-1 break-all">
                    URL: {s.url}
                  </div>
                )}
              </div>
              {s.status === 'scheduled' && (
                <button
                  onClick={() => handleCancel(s._id)}
                  className="px-3 py-2 border border-border rounded hover:bg-secondary flex items-center gap-2"
                >
                  <FaTrash /> Cancel
                </button>
              )}
            </div>
          ))}
        </div>
      </div>
      {showScanNowModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-md p-6 bg-card rounded-xl shadow-xl border border-border">
            <h3 className="text-lg font-semibold mb-2">Enter Website URL</h3>
            <p className="text-sm text-muted-foreground mb-4">No previous website found. Provide your site URL to run a comprehensive whole-site scan now.</p>
            {modalError && (
              <div className="mb-3 p-3 rounded bg-red-50 text-red-700 text-sm">{modalError}</div>
            )}
            <input
              value={modalUrl}
              onChange={(e) => setModalUrl(e.target.value)}
              placeholder="https://example.com"
              className="w-full px-3 py-2 border border-border rounded mb-4"
            />
            <div className="flex items-center justify-end gap-2">
              <button onClick={() => { setShowScanNowModal(false); setModalUrl(''); setModalError(null); }} className="px-3 py-2 border border-border rounded">Cancel</button>
              <button onClick={submitScanNowWithUrl} disabled={modalSubmitting} className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90 flex items-center gap-2">
                {modalSubmitting ? (<><FaSpinner className="animate-spin" /> Scanning…</>) : 'Scan Now (Whole-Site)'}
              </button>
            </div>
          </div>
        </div>
      )}
      {showSuccessPopup && (
        <div className="fixed bottom-6 right-6 z-50 px-4 py-3 bg-green-600 text-white rounded-lg shadow-lg">
          Whole-site scan completed successfully.
        </div>
      )}
    </motion.div>
  );
};

export default ScheduleScan;


