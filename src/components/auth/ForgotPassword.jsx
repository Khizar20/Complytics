import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../ui/button';
import { FaEnvelope, FaSpinner } from 'react-icons/fa';

const ForgotPassword = () => {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/auth/forgot-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      const data = await response.json();

      if (response.ok) {
        setSuccess("If an account exists with this email address, you will receive a password reset email shortly. Please check your inbox and spam folder.");
        setEmail('');
      } else {
        setError(data.detail || 'Failed to process request');
      }
    } catch (err) {
      setError('An error occurred. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="max-w-md w-full mx-auto p-8 bg-card rounded-xl shadow-lg">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
            <FaEnvelope className="h-8 w-8 text-primary" />
          </div>
          <h2 className="text-2xl font-bold text-foreground">Forgot Password</h2>
          <p className="text-muted-foreground mt-2">
            Enter your email address and we'll send you your credentials
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-destructive/10 text-destructive rounded-lg">
            {error}
          </div>
        )}

        {success && (
          <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded relative mb-4">
            <p className="text-sm">{success}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-foreground mb-1">
              Email Address
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <FaEnvelope className="h-5 w-5 text-muted-foreground" />
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

          <div className="flex flex-col space-y-4">
            <Button
              type="submit"
              className="w-full flex justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <FaSpinner className="animate-spin mr-2" />
                  Sending...
                </>
              ) : (
                'Send Credentials'
              )}
            </Button>

            <Button
              type="button"
              variant="outline"
              className="w-full"
              onClick={() => navigate('/login')}
            >
              Back to Login
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ForgotPassword; 