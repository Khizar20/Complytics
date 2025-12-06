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
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="text-center">
          <FaSpinner className="animate-spin h-8 w-8 text-primary mx-auto mb-4" />
          <p className="text-muted-foreground">Checking authentication...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="max-w-md w-full mx-auto p-8 bg-card rounded-xl shadow-lg">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
            <FaUser className="h-8 w-8 text-primary" />
          </div>
          <h2 className="text-2xl font-bold text-foreground">Welcome Back</h2>
          <p className="text-muted-foreground mt-2">
            Sign in to your Complytics account
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-destructive/10 text-destructive rounded-lg">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-foreground mb-1">
              Email Address
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <FaUser className="h-5 w-5 text-muted-foreground" />
              </div>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="block w-full pl-10 pr-3 py-3 border border-border rounded-lg bg-background focus:ring-primary focus:border-primary"
                placeholder="your@email.com"
              />
            </div>
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-foreground mb-1">
              Password
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <FaLock className="h-5 w-5 text-muted-foreground" />
              </div>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="block w-full pl-10 pr-3 py-3 border border-border rounded-lg bg-background focus:ring-primary focus:border-primary"
                placeholder="••••••••"
              />
            </div>
          </div>

          <div className="flex items-center justify-between">
            <div className="text-sm">
              <Link
                to="/forgot-password"
                className="font-medium text-primary hover:text-primary/80"
              >
                Forgot password?
              </Link>
            </div>
          </div>

          <div>
            <Button
              type="submit"
              className="w-full flex justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
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

        <div className="mt-6">
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-border" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-card text-muted-foreground">
                Don't have an account?
              </span>
            </div>
          </div>

          <div className="mt-6">
            <button
              onClick={scrollToCTA}
              className="w-full flex justify-center py-2 px-4 border border-border rounded-md shadow-sm text-sm font-medium text-foreground bg-background hover:bg-secondary focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
            >
              Request access
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginForm;