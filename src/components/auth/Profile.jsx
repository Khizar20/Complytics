import React, { useState } from 'react';
import { useToast } from '@/components/ui/toast';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../ui/button';
import { FaUser, FaLock, FaEye, FaEyeSlash } from 'react-icons/fa';
import { motion } from 'framer-motion';
import { API_URL } from '../../config';

const Profile = () => {
  const { user, authToken } = useAuth();
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [formData, setFormData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });

  const [deletionReason, setDeletionReason] = useState('');
  const [deletionRequest, setDeletionRequest] = useState(null);

  React.useEffect(() => {
    const fetchDeletionRequest = async () => {
      try {
        if (!authToken) return;
        const res = await fetch(`${API_URL}/admin/account-deletion-request`, {
          headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (res.ok) {
          const data = await res.json();
          setDeletionRequest(data);
        }
      } catch (e) {
        console.error('Failed to fetch deletion request', e);
      }
    };
    fetchDeletionRequest();
  }, [authToken]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!authToken) {
      setError('Authentication token not found. Please log in again.');
      return;
    }

    // Validate password match
    if (formData.new_password !== formData.confirm_password) {
      setError('New passwords do not match');
      return;
    }

    // Validate password length
    if (formData.new_password.length < 8) {
      setError('New password must be at least 8 characters long');
      return;
    }

    try {
      setIsLoading(true);
      console.log('Sending password update request...');
      console.log('Request URL:', `${API_URL}/auth/profile`);
      console.log('Request headers:', {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authToken}`
      });
      console.log('Request body:', {
        current_password: formData.current_password,
        new_password: formData.new_password,
        confirm_password: formData.confirm_password
      });

      const response = await fetch(`${API_URL}/auth/profile`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({
          current_password: formData.current_password,
          new_password: formData.new_password,
          confirm_password: formData.confirm_password
        })
      });

      console.log('Response status:', response.status);
      const data = await response.json();
      console.log('Response data:', data);

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to update password');
      }

      toast({ title: 'Password updated', variant: 'success' });
      setFormData({
        current_password: '',
        new_password: '',
        confirm_password: ''
      });
    } catch (err) {
      console.error('Error updating password:', err);
      setError(err.message);
      toast({ title: 'Failed to update password', description: err.message, variant: 'error' });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      className="max-w-6xl mx-auto p-6 space-y-6"
    >
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Profile summary card */}
        <div className="lg:col-span-1 bg-white/80 dark:bg-gray-800/70 backdrop-blur rounded-2xl border border-border/40 shadow-xl p-6 space-y-6">
          <div className="flex items-center space-x-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-primary/20 via-primary/10 to-transparent flex items-center justify-center">
              <FaUser className="h-7 w-7 text-primary" />
            </div>
            <div className="max-w-[20rem]">
              <p className="text-xs uppercase tracking-wider text-muted-foreground">Signed in as</p>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white truncate max-w-[20rem]">
                {user?.name || 'Complytics Member'}
              </h2>
              <p className="text-sm text-muted-foreground truncate max-w-[20rem]">{user?.email}</p>
            </div>
          </div>

          <div className="rounded-xl bg-muted/40 dark:bg-gray-900/40 p-4 border border-border/30 space-y-3">
            <div className="flex justify-between text-sm text-muted-foreground">
              <span>Role</span>
              <span className="text-gray-900 dark:text-gray-100 font-medium capitalize">
                {user?.role || 'member'}
              </span>
            </div>
            <div className="flex justify-between text-sm text-muted-foreground">
              <span>Account Status</span>
              <span className="text-green-600 dark:text-green-400 font-medium">Active</span>
            </div>
          </div>

          <div className="rounded-2xl bg-gradient-to-br from-primary/5 via-blue-50 dark:via-gray-900 to-transparent border border-primary/10 p-5 space-y-4">
            <p className="text-sm font-semibold text-primary">Security Tips</p>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li className="flex items-start space-x-2">
                <span className="mt-1 h-1.5 w-1.5 rounded-full bg-primary"></span>
                <span>Use at least 12 characters mixing letters, numbers, and symbols.</span>
              </li>
              <li className="flex items-start space-x-2">
                <span className="mt-1 h-1.5 w-1.5 rounded-full bg-primary"></span>
                <span>Avoid reusing passwords across different services.</span>
              </li>
              <li className="flex items-start space-x-2">
                <span className="mt-1 h-1.5 w-1.5 rounded-full bg-primary"></span>
                <span>Update credentials every 90 days as part of compliance best practices.</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Password form */}
        <div className="lg:col-span-2 bg-white dark:bg-gray-800 rounded-2xl shadow-xl border border-border/40 p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <p className="text-xs uppercase tracking-widest text-muted-foreground">Account</p>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Update Password</h2>
              <p className="text-sm text-muted-foreground">Secure your workspace account with a strong password.</p>
            </div>
            <div className="hidden md:block">
              <div className="px-4 py-2 rounded-full bg-primary/10 text-primary text-xs font-semibold tracking-wide">
                Last updated • {user?.password_updated_at ? new Date(user.password_updated_at).toLocaleDateString() : 'N/A'}
              </div>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Current Password
              </label>
              <div className="relative">
                <input
                  type={showCurrentPassword ? "text" : "password"}
                  name="current_password"
                  value={formData.current_password}
                  onChange={handleInputChange}
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-primary/50 dark:bg-gray-700 dark:text-white"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 dark:text-gray-400"
                >
                  {showCurrentPassword ? <FaEyeSlash /> : <FaEye />}
                </button>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                New Password
              </label>
              <div className="relative">
                <input
                  type={showNewPassword ? "text" : "password"}
                  name="new_password"
                  value={formData.new_password}
                  onChange={handleInputChange}
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-primary/50 dark:bg-gray-700 dark:text-white"
                  required
                  minLength={8}
                />
                <button
                  type="button"
                  onClick={() => setShowNewPassword(!showNewPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 dark:text-gray-400"
                >
                  {showNewPassword ? <FaEyeSlash /> : <FaEye />}
                </button>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Confirm New Password
              </label>
              <div className="relative">
                <input
                  type={showConfirmPassword ? "text" : "password"}
                  name="confirm_password"
                  value={formData.confirm_password}
                  onChange={handleInputChange}
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-primary/50 dark:bg-gray-700 dark:text-white"
                  required
                  minLength={8}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 dark:text-gray-400"
                >
                  {showConfirmPassword ? <FaEyeSlash /> : <FaEye />}
                </button>
              </div>
            </div>
          </div>

          {error && (
            <div className="p-3 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded-md">
              {error}
            </div>
          )}

          {/* Inline success container removed; toast is used */}

          <Button
            type="submit"
            className="w-full"
            disabled={isLoading}
          >
            {isLoading ? 'Updating...' : 'Update Password'}
          </Button>
          </form>

          {/* Account deletion UI moved to Admin Dashboard (Request Account Deletion menu) */}
        </div>
      </div>
    </motion.div>
  );
};

export default Profile; 