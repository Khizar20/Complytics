import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { FaCalendarAlt, FaClock, FaList, FaTrash } from 'react-icons/fa';
import { useAuth } from '../../context/AuthContext';

const ScheduleScan = () => {
  const { authToken } = useAuth();
  const apiBase = 'http://localhost:8000/api';
  const [runAt, setRunAt] = useState(''); // HTML datetime-local value (local time)
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [schedules, setSchedules] = useState([]);

  const fetchSchedules = async () => {
    try {
      const resp = await fetch(`${apiBase}/ui/schedules`, {
        headers: {
          'Authorization': `Bearer ${authToken}`,
        }
      });
      if (!resp.ok) throw new Error(await resp.text() || 'Failed to load schedules');
      const data = await resp.json();
      setSchedules(Array.isArray(data.schedules) ? data.schedules : []);
    } catch (e) {
      // Non-blocking
    }
  };

  useEffect(() => {
    if (authToken) fetchSchedules();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authToken]);

  const toIsoUtc = (localValue) => {
    // localValue like '2025-10-01T14:30'
    if (!localValue) return '';
    const dt = new Date(localValue);
    return dt.toISOString();
  };

  const handleSchedule = async () => {
    if (!runAt) {
      setError('Please select a date and time');
      return;
    }
    setError(null);
    setSuccess(null);
    setLoading(true);
    try {
      const run_at_iso = toIsoUtc(runAt);
      const resp = await fetch(`${apiBase}/ui/schedule`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`,
        },
        body: JSON.stringify({ run_at_iso }),
      });
      if (!resp.ok) throw new Error(await resp.text() || 'Failed to schedule scan');
      await resp.json();
      setSuccess('Scan scheduled successfully. You will receive an email after it completes.');
      setRunAt('');
      fetchSchedules();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
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
            <h3 className="text-lg font-semibold">Schedule a One-Time Scan</h3>
            <p className="text-muted-foreground">Runs on the selected date/time (uses last scanned URL)</p>
          </div>
        </div>

        {error && (
          <div className="mb-3 p-3 rounded bg-red-50 text-red-700 text-sm">{error}</div>
        )}
        {success && (
          <div className="mb-3 p-3 rounded bg-green-50 text-green-700 text-sm">{success}</div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
          <div className="md:col-span-2">
            <label className="block text-sm mb-1">Date & Time</label>
            <input
              type="datetime-local"
              value={runAt}
              onChange={(e) => setRunAt(e.target.value)}
              className="w-full p-2 border border-border rounded"
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
          </div>
        </div>
      </div>

      <div className="p-6 bg-card rounded-xl shadow-lg">
        <div className="flex items-center space-x-4 mb-4">
          <FaList className="text-2xl text-primary" />
          <div>
            <h3 className="text-lg font-semibold">Scheduled Scans</h3>
            <p className="text-muted-foreground">Upcoming and past one-time schedules</p>
          </div>
        </div>

        <div className="space-y-3">
          {schedules.length === 0 && (
            <div className="text-sm text-muted-foreground">No schedules.</div>
          )}
          {schedules.map((s) => (
            <div key={s._id} className="flex items-center justify-between p-3 border border-border rounded-lg">
              <div>
                <div className="text-sm font-medium">{formatUtc(s.scheduled_for)}</div>
                <div className="text-xs text-muted-foreground">Status: {s.status}</div>
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
    </motion.div>
  );
};

export default ScheduleScan;


