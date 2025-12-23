import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { FaCalendarAlt, FaClock, FaList, FaTrash, FaSpinner, FaGlobe, FaCheckCircle, FaExclamationCircle, FaInfoCircle } from 'react-icons/fa';
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
      className="space-y-10 p-8"
    >
      {/* Header Section */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-4xl md:text-5xl font-bold text-black mb-3">Schedule Compliance Scan</h2>
          <p className="text-lg text-gray-600">Schedule automated whole-site scans for your website and Azure compliance analysis</p>
        </div>
      </div>

      {/* Schedule Form Card */}
      <motion.div 
        whileHover={{ scale: 1.01 }}
        className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl hover:shadow-2xl transition-all duration-300 relative overflow-hidden group"
      >
        {/* Decorative blur elements */}
        <div className="absolute top-0 right-0 w-48 h-48 bg-blue-500/10 rounded-full blur-3xl -mr-24 -mt-24 animate-pulse-slow"></div>
        
        {/* Card Header */}
        <div className="bg-gradient-to-r from-blue-600/10 via-blue-500/5 to-transparent px-8 py-6 border-b border-blue-200 relative z-10">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-gradient-to-br from-blue-600 to-blue-500 rounded-xl shadow-lg">
              <FaCalendarAlt className="text-2xl text-white" />
            </div>
            <div>
              <h3 className="text-2xl font-bold text-gray-900">Schedule a One-Time Compliance Scan</h3>
              <p className="text-sm text-gray-600 mt-1">Runs comprehensive website testing and Azure compliance analysis on the selected date/time</p>
            </div>
          </div>
        </div>

        {/* Card Body */}
        <div className="p-8 space-y-6 relative z-10">
          {/* Info about Azure compliance */}
          <div className="p-5 bg-gradient-to-r from-blue-50/80 to-indigo-50/80 backdrop-blur-sm border-2 border-blue-200 rounded-xl shadow-sm">
            <p className="text-sm text-blue-800 font-medium flex items-start space-x-2">
              <FaInfoCircle className="text-blue-600 mt-0.5 flex-shrink-0" />
              <span>
                <strong>Note:</strong> Scheduled scans automatically include Azure compliance analysis if Azure settings have been fetched. 
                The email notification will include both website testing results and Azure compliance check results.
              </span>
            </p>
          </div>
          {/* Alert Messages */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-start space-x-3 p-5 rounded-xl bg-red-50/90 backdrop-blur-sm border-2 border-red-300 shadow-sm"
            >
              <FaExclamationCircle className="text-red-600 mt-0.5 flex-shrink-0 text-xl" />
              <p className="text-sm text-red-800 font-medium flex-1">{error}</p>
            </motion.div>
          )}
          {success && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-start space-x-3 p-5 rounded-xl bg-green-50/90 backdrop-blur-sm border-2 border-green-300 shadow-sm"
            >
              <FaCheckCircle className="text-green-600 mt-0.5 flex-shrink-0 text-xl" />
              <p className="text-sm text-green-800 font-medium flex-1">{success}</p>
            </motion.div>
          )}

          {/* URL Selection Section */}
          <div className="space-y-5">
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
                className="w-5 h-5 rounded border-2 border-gray-300 text-blue-600 focus:ring-2 focus:ring-blue-500/50 cursor-pointer"
              />
              <label htmlFor="usePreviousUrl" className="text-sm font-semibold text-gray-900 cursor-pointer">
                Use previously scanned website
              </label>
            </div>
            
            {usePreviousUrl ? (
              previousUrl ? (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="p-5 bg-gradient-to-r from-blue-50/80 to-indigo-50/80 backdrop-blur-sm border-2 border-blue-300 rounded-xl shadow-sm"
                >
                  <div className="flex items-start space-x-3">
                    <div className="p-2 bg-blue-600 rounded-lg">
                      <FaGlobe className="text-white text-sm" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-bold text-blue-700 mb-2 uppercase tracking-wide">Previous Website</p>
                      <p className="text-sm text-blue-900 break-all font-mono font-medium">{previousUrl}</p>
                    </div>
                  </div>
                </motion.div>
              ) : (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="p-5 bg-yellow-50/90 backdrop-blur-sm border-2 border-yellow-300 rounded-xl shadow-sm"
                >
                  <div className="flex items-start space-x-3">
                    <FaExclamationCircle className="text-yellow-600 mt-0.5 flex-shrink-0 text-xl" />
                    <p className="text-sm text-yellow-800 font-medium flex-1">
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
                <label className="block text-sm font-bold text-gray-900">
                  Website URL
                </label>
                <div className="relative">
                  <FaGlobe className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400 text-lg" />
                  <input
                    type="text"
                    value={scheduleUrl}
                    onChange={(e) => setScheduleUrl(e.target.value)}
                    placeholder="https://example.com"
                    className="w-full pl-12 pr-4 py-3.5 border-2 border-gray-300 rounded-xl bg-white focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all shadow-sm"
                  />
                </div>
              </motion.div>
            )}
          </div>

          {/* Date/Time and Actions */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 pt-6 border-t-2 border-blue-200">
            <div className="lg:col-span-2 space-y-2">
              <label className="block text-sm font-bold text-gray-900">
                Date & Time
              </label>
              <div className="relative">
                <FaClock className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400 text-lg" />
                <input
                  type="datetime-local"
                  value={runAt}
                  onChange={(e) => setRunAt(e.target.value)}
                  className="w-full pl-12 pr-4 py-3.5 border-2 border-gray-300 rounded-xl bg-white focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all shadow-sm"
                  min={minDateTimeLocal()}
                />
              </div>
            </div>
            <div className="flex flex-col gap-3">
              <button
                disabled={loading}
                onClick={handleSchedule}
                className="w-full px-6 py-3.5 bg-gradient-to-r from-blue-600 to-blue-500 text-white rounded-xl hover:from-blue-700 hover:to-blue-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 font-semibold transition-all shadow-lg hover:shadow-xl"
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
                className="w-full px-6 py-3.5 border-2 border-gray-300 rounded-xl hover:bg-gray-50 hover:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 font-semibold transition-all shadow-sm hover:shadow-md text-gray-900"
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
      </motion.div>

      {/* Scheduled Scans List Card */}
      <motion.div 
        whileHover={{ scale: 1.01 }}
        className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl hover:shadow-2xl transition-all duration-300 relative overflow-hidden group"
      >
        {/* Decorative blur elements */}
        <div className="absolute top-0 right-0 w-48 h-48 bg-purple-500/10 rounded-full blur-3xl -mr-24 -mt-24 animate-pulse-slow"></div>
        
        {/* Card Header */}
        <div className="bg-gradient-to-r from-purple-600/10 via-purple-500/5 to-transparent px-8 py-6 border-b border-purple-200 relative z-10">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="p-3 bg-gradient-to-br from-purple-600 to-purple-500 rounded-xl shadow-lg">
                <FaList className="text-2xl text-white" />
              </div>
              <div>
                <h3 className="text-2xl font-bold text-gray-900">Scheduled Scans</h3>
                <p className="text-sm text-gray-600 mt-1">Manage your upcoming scans</p>
              </div>
            </div>
            {schedules.length > 0 && (
              <div className="px-4 py-2 bg-gradient-to-r from-purple-600 to-purple-500 rounded-full shadow-md">
                <span className="text-sm font-bold text-white">{schedules.length}</span>
              </div>
            )}
          </div>
        </div>

        {/* Card Body */}
        <div className="p-8 relative z-10">
          {schedules.length === 0 ? (
            <div className="text-center py-16">
              <div className="mx-auto w-20 h-20 bg-purple-100/50 rounded-full flex items-center justify-center mb-4">
                <FaList className="text-4xl text-purple-600" />
              </div>
              <p className="text-gray-900 font-bold text-lg mb-2">No scheduled scans</p>
              <p className="text-sm text-gray-600">Schedule your first scan above to get started</p>
            </div>
          ) : (
            <div className="space-y-4">
              {schedules.map((s, index) => (
                <motion.div
                  key={s._id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                  whileHover={{ scale: 1.02, y: -3 }}
                  className="flex items-center justify-between p-5 border-2 border-gray-200 rounded-xl hover:border-purple-300 hover:shadow-lg transition-all bg-white/80 backdrop-blur-sm"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-4 mb-3">
                      <div className="p-2 bg-gradient-to-br from-purple-600 to-purple-500 rounded-lg shadow-md">
                        <FaClock className="text-white text-sm" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-base font-bold text-gray-900 truncate">
                          {formatUtc(s.scheduled_for)}
                        </div>
                        <div className="flex items-center space-x-2 mt-2">
                          <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-bold ${
                            s.status === 'scheduled' 
                              ? 'bg-blue-100 text-blue-800 border-2 border-blue-300'
                              : 'bg-gray-100 text-gray-800 border-2 border-gray-300'
                          }`}>
                            {s.status}
                          </span>
                        </div>
                      </div>
                    </div>
                    {s.url && (
                      <div className="ml-12 mt-3 flex items-start space-x-2">
                        <FaGlobe className="text-purple-600 text-sm mt-0.5 flex-shrink-0" />
                        <p className="text-xs text-gray-700 break-all font-mono font-medium">{s.url}</p>
                      </div>
                    )}
                  </div>
                  {s.status === 'scheduled' && (
                    <button
                      onClick={() => handleCancel(s._id)}
                      className="ml-4 px-5 py-2.5 text-white bg-gradient-to-r from-red-600 to-red-500 border-2 border-red-300 rounded-xl hover:from-red-700 hover:to-red-600 flex items-center gap-2 transition-all font-semibold text-sm shadow-md hover:shadow-lg"
                    >
                      <FaTrash className="text-sm" />
                      <span>Cancel</span>
                    </button>
                  )}
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </motion.div>
      {/* Scan Now Modal */}
      {showScanNowModal && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-md p-4"
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
            className="w-full max-w-md bg-white/90 backdrop-blur-md rounded-2xl shadow-2xl border-2 border-blue-200 overflow-hidden relative"
          >
            {/* Decorative blur */}
            <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/20 rounded-full blur-2xl -mr-16 -mt-16"></div>
            
            {/* Modal Header */}
            <div className="bg-gradient-to-r from-blue-600/10 via-blue-500/5 to-transparent px-6 py-5 border-b-2 border-blue-200 relative z-10">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-gradient-to-br from-blue-600 to-blue-500 rounded-lg shadow-md">
                  <FaGlobe className="text-xl text-white" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-gray-900">Enter Website URL</h3>
                  <p className="text-xs text-gray-600 mt-0.5">No previous website found</p>
                </div>
              </div>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-5 relative z-10">
              <p className="text-sm text-gray-700 font-medium">
                Provide your site URL to run a comprehensive whole-site scan now.
              </p>
              
              {modalError && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex items-start space-x-2 p-4 rounded-xl bg-red-50/90 backdrop-blur-sm border-2 border-red-300"
                >
                  <FaExclamationCircle className="text-red-600 mt-0.5 flex-shrink-0 text-xl" />
                  <p className="text-sm text-red-800 font-medium flex-1">{modalError}</p>
                </motion.div>
              )}
              
              <div className="space-y-2">
                <label className="block text-sm font-bold text-gray-900">
                  Website URL
                </label>
                <div className="relative">
                  <FaGlobe className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400 text-lg" />
                  <input
                    value={modalUrl}
                    onChange={(e) => setModalUrl(e.target.value)}
                    placeholder="https://example.com"
                    className="w-full pl-12 pr-4 py-3.5 border-2 border-gray-300 rounded-xl bg-white focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all shadow-sm"
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
            <div className="px-6 py-5 bg-gray-50/80 backdrop-blur-sm border-t-2 border-blue-200 flex items-center justify-end gap-3 relative z-10">
              <button
                onClick={() => {
                  setShowScanNowModal(false);
                  setModalUrl('');
                  setModalError(null);
                }}
                disabled={modalSubmitting}
                className="px-5 py-2.5 border-2 border-gray-300 rounded-xl hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-semibold text-gray-900 shadow-sm"
              >
                Cancel
              </button>
              <button
                onClick={submitScanNowWithUrl}
                disabled={modalSubmitting || !modalUrl.trim()}
                className="px-6 py-2.5 bg-gradient-to-r from-blue-600 to-blue-500 text-white rounded-xl hover:from-blue-700 hover:to-blue-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-all shadow-lg hover:shadow-xl font-semibold"
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
          className="fixed bottom-6 right-6 z-50 px-6 py-4 bg-gradient-to-r from-green-600 to-green-500 text-white rounded-xl shadow-2xl flex items-center space-x-3 max-w-md border-2 border-green-300"
        >
          <FaCheckCircle className="text-2xl flex-shrink-0" />
          <p className="font-bold">Whole-site scan completed successfully.</p>
        </motion.div>
      )}
    </motion.div>
  );
};

export default ScheduleScan;


