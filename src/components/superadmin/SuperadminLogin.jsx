// src/components/superadmin/SuperadminLogin.jsx
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Button } from '@/components/ui/button';
import { FaLock, FaUserShield, FaSpinner } from 'react-icons/fa';
import { buildApiUrl } from '@/lib/api';

export default function SuperadminLogin() {
  const [email, setEmail] = useState('superadmin@complytics.com');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { login, isAuthenticated, user, isLoading: authLoading } = useAuth();
  const navigate = useNavigate();

  // Redirect if superadmin is already authenticated
  useEffect(() => {
    // Wait for auth context to finish loading
    if (authLoading) {
      return;
    }

    // Check if user is already authenticated and is a superadmin
    if (isAuthenticated && user && user.role === 'superadmin') {
      navigate('/superadmin/dashboard', { replace: true });
    }
  }, [isAuthenticated, user, authLoading, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('username', email);
      formData.append('password', password);

      const response = await fetch(buildApiUrl('/auth/login'), {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Login failed - Invalid credentials');
      }

      const data = await response.json();
      
      // Store the token immediately
      localStorage.setItem('authToken', data.access_token);
      
      // Now try to login with the token
      await login(data.access_token);
      
      // Check if the user is a superadmin
      const userData = JSON.parse(localStorage.getItem('userData'));
      if (userData && userData.role === 'superadmin') {
        navigate('/superadmin/dashboard');
      } else {
        throw new Error('Unauthorized access - Superadmin access required');
      }
    } catch (err) {
      setError(err.message);
      console.error('Login error:', err);
      // Clear any stored tokens on error
      localStorage.removeItem('authToken');
      localStorage.removeItem('userData');
    } finally {
      setIsLoading(false);
    }
  };

  // Show loading state while checking authentication
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4 bg-blue-50/30">
        <div className="text-center">
          <FaUserShield className="animate-pulse h-10 w-10 text-blue-600 mx-auto mb-4" />
          <p className="text-gray-600 font-medium">Checking authentication...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-blue-50/30 via-blue-50/20 to-blue-50/30">
      {/* Background decorative elements */}
      <div className="absolute top-0 left-0 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl"></div>
      <div className="absolute bottom-0 right-0 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl"></div>
      
      <div className="max-w-md w-full mx-auto relative z-10">
        <div className="bg-white border-2 border-black rounded-2xl shadow-2xl p-8 md:p-10">
          <div className="text-center mb-8">
            <div className="w-20 h-20 bg-gradient-to-br from-blue-600 via-blue-500 to-blue-700 rounded-full flex items-center justify-center mx-auto mb-6 shadow-lg">
              <FaUserShield className="h-10 w-10 text-white" />
            </div>
            <h2 className="text-3xl font-bold text-black mb-2">Superadmin Login</h2>
            <p className="text-gray-600 text-base">
              Access the superadmin dashboard
            </p>
          </div>

          {error && (
            <div className="mb-6 p-4 bg-red-50 border-2 border-red-500 text-red-700 rounded-lg font-medium">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="email" className="block text-sm font-bold text-black mb-2">
                Email Address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                  <FaUserShield className="h-5 w-5 text-blue-600" />
                </div>
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="block w-full pl-12 pr-4 py-3 border-2 border-black rounded-lg bg-white text-black placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-blue-600 transition-all font-medium"
                  placeholder="superadmin@complytics.com"
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-bold text-black mb-2">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                  <FaLock className="h-5 w-5 text-blue-600" />
                </div>
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="block w-full pl-12 pr-4 py-3 border-2 border-black rounded-lg bg-white text-black placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-blue-600 transition-all font-medium"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <div>
              <Button
                type="submit"
                className="w-full flex justify-center py-4 px-4 rounded-lg shadow-lg text-base font-bold text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-600 transition-all duration-300 transform hover:scale-[1.02]"
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <FaSpinner className="animate-spin mr-2" />
                    Signing in...
                  </>
                ) : (
                  'Sign in'
                )}
              </Button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}