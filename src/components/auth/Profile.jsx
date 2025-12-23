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
      className="min-h-screen"
    >
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Profile summary card */}
          <div className="lg:col-span-1 bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl p-6 space-y-6 relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/10 rounded-full blur-2xl -mr-16 -mt-16"></div>
            <div className="relative z-10">
              <div className="flex items-center space-x-4 mb-6">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-600 to-blue-500 flex items-center justify-center shadow-lg">
                  <FaUser className="h-8 w-8 text-white" />
                </div>
                <div className="max-w-[20rem]">
                  <p className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-1">Signed in as</p>
                  <h2 className="text-lg font-bold text-gray-900 truncate max-w-[20rem]">
                    {user?.name || 'Complytics Member'}
                  </h2>
                  <p className="text-sm text-gray-600 truncate max-w-[20rem] font-medium">{user?.email}</p>
                </div>
              </div>

              <div className="rounded-xl bg-gradient-to-br from-gray-50 to-white p-5 border-2 border-gray-100 space-y-4 shadow-sm">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-semibold text-gray-600">Role</span>
                  <span className="px-3 py-1.5 text-xs rounded-full font-bold bg-blue-100 text-blue-800 border-2 border-blue-500 capitalize">
                    {user?.role || 'member'}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-semibold text-gray-600">Account Status</span>
                  <span className="px-3 py-1.5 text-xs rounded-full font-bold bg-green-100 text-green-800 border-2 border-green-500">Active</span>
                </div>
              </div>

              <div className="rounded-2xl bg-gradient-to-br from-blue-50/80 to-white border-2 border-blue-100 p-5 space-y-4 mt-6">
                <p className="text-sm font-bold text-blue-600">Security Tips</p>
                <ul className="space-y-3 text-sm text-gray-600">
                  <li className="flex items-start space-x-3">
                    <span className="mt-1.5 h-2 w-2 rounded-full bg-blue-600 flex-shrink-0"></span>
                    <span className="font-medium">Use at least 12 characters mixing letters, numbers, and symbols.</span>
                  </li>
                  <li className="flex items-start space-x-3">
                    <span className="mt-1.5 h-2 w-2 rounded-full bg-blue-600 flex-shrink-0"></span>
                    <span className="font-medium">Avoid reusing passwords across different services.</span>
                  </li>
                  <li className="flex items-start space-x-3">
                    <span className="mt-1.5 h-2 w-2 rounded-full bg-blue-600 flex-shrink-0"></span>
                    <span className="font-medium">Update credentials every 90 days as part of compliance best practices.</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>

          {/* Password form */}
          <div className="lg:col-span-2 bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl p-8">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-8 gap-4">
              <div>
                <p className="text-xs uppercase tracking-widest text-gray-500 font-semibold mb-2">Account</p>
                <h2 className="text-2xl font-bold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent mb-2">Update Password</h2>
                <p className="text-sm text-gray-600 font-medium">Secure your workspace account with a strong password.</p>
              </div>
              <div className="hidden md:block">
                <div className="px-4 py-2 rounded-xl bg-blue-100 text-blue-700 text-xs font-bold tracking-wide border-2 border-blue-200">
                  Last updated • {user?.password_updated_at ? new Date(user.password_updated_at).toLocaleDateString() : 'N/A'}
                </div>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-5">
                <div>
                  <label className="block text-sm font-bold text-gray-700 mb-2">
                    Current Password
                  </label>
                  <div className="relative">
                    <input
                      type={showCurrentPassword ? "text" : "password"}
                      name="current_password"
                      value={formData.current_password}
                      onChange={handleInputChange}
                      className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all font-medium"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                      className="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-blue-600 transition-colors"
                    >
                      {showCurrentPassword ? <FaEyeSlash className="h-5 w-5" /> : <FaEye className="h-5 w-5" />}
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-bold text-gray-700 mb-2">
                    New Password
                  </label>
                  <div className="relative">
                    <input
                      type={showNewPassword ? "text" : "password"}
                      name="new_password"
                      value={formData.new_password}
                      onChange={handleInputChange}
                      className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all font-medium"
                      required
                      minLength={8}
                    />
                    <button
                      type="button"
                      onClick={() => setShowNewPassword(!showNewPassword)}
                      className="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-blue-600 transition-colors"
                    >
                      {showNewPassword ? <FaEyeSlash className="h-5 w-5" /> : <FaEye className="h-5 w-5" />}
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-bold text-gray-700 mb-2">
                    Confirm New Password
                  </label>
                  <div className="relative">
                    <input
                      type={showConfirmPassword ? "text" : "password"}
                      name="confirm_password"
                      value={formData.confirm_password}
                      onChange={handleInputChange}
                      className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all font-medium"
                      required
                      minLength={8}
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-blue-600 transition-colors"
                    >
                      {showConfirmPassword ? <FaEyeSlash className="h-5 w-5" /> : <FaEye className="h-5 w-5" />}
                    </button>
                  </div>
                </div>
              </div>

              {error && (
                <div className="p-4 bg-gradient-to-r from-red-50 to-red-100 border-l-4 border-red-500 text-red-700 rounded-xl font-semibold shadow-lg">
                  {error}
                </div>
              )}

              <Button
                type="submit"
                className="w-full bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-700 hover:to-blue-600 text-white font-semibold shadow-lg shadow-blue-500/30 rounded-xl py-6 text-lg transition-all hover:scale-105"
                disabled={isLoading}
              >
                {isLoading ? 'Updating...' : 'Update Password'}
              </Button>
            </form>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default Profile; 