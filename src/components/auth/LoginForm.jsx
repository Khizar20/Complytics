// src/components/auth/LoginForm.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { FaUser, FaLock, FaSpinner } from 'react-icons/fa';
import { Button } from '../ui/button';
import { useAuth } from '../../context/AuthContext';
import { buildApiUrl } from '@/lib/api';

const LoginForm = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const { login, isAuthenticated, user, isLoading: authLoading } = useAuth();

  // Redirect if user is already authenticated
  useEffect(() => {
    // Wait for auth context to finish loading
    if (authLoading) {
      return;
    }

    // Check if user is already authenticated
    if (isAuthenticated && user) {
      // Redirect based on user role
      if (user.role === 'superadmin') {
        navigate('/superadmin/dashboard', { replace: true });
      } else if (user.role === 'admin') {
        navigate('/dashboard', { replace: true });
      } else if (['it_team', 'compliance_team', 'management_team'].includes(user.role)) {
        navigate('/team-dashboard', { replace: true });
      }
    }
  }, [isAuthenticated, user, authLoading, navigate]);

  useEffect(() => {
    // Clean up any legacy remembered email
    const savedEmail = localStorage.getItem('rememberedEmail');
    if (savedEmail) {
      localStorage.removeItem('rememberedEmail');
    }
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const formData = new FormData();
      formData.append('username', email);
      formData.append('password', password);

      const response = await fetch(buildApiUrl('/auth/login'), {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Login failed - Invalid credentials');
      }

      const data = await response.json();
      
      // Login will now handle fetching user data and storing it
      await login(data.access_token);

      // Get the stored user data
      const userData = JSON.parse(localStorage.getItem('userData'));
      
      if (!userData) {
        throw new Error('No user data found in localStorage');
      }
      
      if (!userData.role) {
        console.error('User data missing role:', userData);
        throw new Error('User data is missing role information');
      }

      // Redirect based on user role
      if (userData.role === 'superadmin') {
        // If superadmin tries to login here, redirect to superadmin login
        navigate('/superadmin/login');
        throw new Error('Superadmin users must login through the superadmin portal');
      } else if (userData.role === 'admin') {
        navigate('/dashboard');
      } else if (['it_team', 'compliance_team', 'management_team'].includes(userData.role)) {
        navigate('/team-dashboard');
      } else {
        throw new Error('Unauthorized access - Invalid role');
      }
    } catch (err) {
      setError(err.message || 'Login failed. Please try again.');
      setIsLoading(false);
    }
  };

  const scrollToCTA = (e) => {
    e.preventDefault();
    navigate('/');
    // Use setTimeout to ensure the navigation is complete before scrolling
    setTimeout(() => {
      const ctaSection = document.getElementById('contact');
      if (ctaSection) {
        ctaSection.scrollIntoView({ behavior: 'smooth' });
      }
    }, 100);
  };

  // Show loading state while checking authentication
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4 bg-blue-50/30">
        <div className="text-center">
          <FaSpinner className="animate-spin h-10 w-10 text-blue-600 mx-auto mb-4" />
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
            <div className="flex items-center justify-center mb-6">
              <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-blue-600 via-blue-500 to-blue-700 flex items-center justify-center shadow-lg transform rotate-[-2deg] mr-3">
                <span className="text-white font-bold text-xl">C</span>
              </div>
              <span className="font-bold text-2xl text-black">Complytics</span>
          </div>
            <h2 className="text-3xl font-bold text-black mb-2">Welcome Back</h2>
            <p className="text-gray-600 text-base">
            Sign in to your Complytics account
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
                  <FaUser className="h-5 w-5 text-blue-600" />
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
                placeholder="your@email.com"
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

          <div className="flex items-center justify-between">
            <div className="text-sm">
              <Link
                to="/forgot-password"
                  className="font-bold text-blue-600 hover:text-blue-700 transition-colors"
              >
                Forgot password?
              </Link>
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

          <div className="mt-8">
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t-2 border-black" />
            </div>
            <div className="relative flex justify-center text-sm">
                <span className="px-3 bg-white text-gray-600 font-medium">
                Don't have an account?
              </span>
            </div>
          </div>

          <div className="mt-6">
            <button
              onClick={scrollToCTA}
                className="w-full flex justify-center py-3 px-4 border-2 border-black rounded-lg shadow-lg text-base font-bold text-black bg-white hover:bg-black hover:text-white focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-600 transition-all duration-300"
            >
              Request access
            </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginForm;