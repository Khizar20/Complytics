// src/context/AuthContext.jsx
import { createContext, useContext, useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [authToken, setAuthToken] = useState(null);
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const initializeAuth = async () => {
      const token = localStorage.getItem('authToken');
      const userData = localStorage.getItem('userData');
      
      if (token && userData) {
        try {
          // Verify token is still valid
          const response = await fetch('http://localhost:8000/auth/me', {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          });

          if (response.ok) {
            setAuthToken(token);
            setUser(JSON.parse(userData));
          } else {
            // Token is invalid, clear everything
            localStorage.removeItem('authToken');
            localStorage.removeItem('userData');
            setAuthToken(null);
            setUser(null);
            if (location.pathname !== '/login') {
              navigate('/login');
            }
          }
        } catch (error) {
          console.error('Error verifying token:', error);
          localStorage.removeItem('authToken');
          localStorage.removeItem('userData');
          setAuthToken(null);
          setUser(null);
          if (location.pathname !== '/login') {
            navigate('/login');
          }
        }
      }
      setIsLoading(false);
    };

    initializeAuth();
  }, [navigate, location]);

  const fetchUserData = async (token) => {
    try {
      const response = await fetch('http://localhost:8000/auth/me', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch user data');
      }

      const userData = await response.json();
      localStorage.setItem('userData', JSON.stringify(userData));
      setUser(userData);
      return userData;
    } catch (error) {
      console.error('Error fetching user data:', error);
      throw error;
    }
  };

  const login = async (token) => {
    try {
      // Store token first
      localStorage.setItem('authToken', token);
      setAuthToken(token);

      // Then fetch user data
      await fetchUserData(token);
    } catch (error) {
      console.error('Error during login:', error);
      // Clear everything on error
      localStorage.removeItem('authToken');
      localStorage.removeItem('userData');
      setAuthToken(null);
      setUser(null);
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem('authToken');
    localStorage.removeItem('userData');
    setAuthToken(null);
    setUser(null);
    navigate('/login');
  };

  const fetchWithRetry = async (url, options = {}) => {
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          ...options.headers,
          'Authorization': `Bearer ${authToken}`
        }
      });

      if (response.status === 401) {
        // If unauthorized, clear everything and redirect to login
        logout();
        throw new Error('Session expired. Please login again.');
      }

      return response;
    } catch (error) {
      console.error('Error in fetchWithRetry:', error);
      throw error;
    }
  };

  const isAuthenticated = !!authToken;

  return (
    <AuthContext.Provider value={{ 
      authToken, 
      user,
      isLoading, 
      isAuthenticated,
      login, 
      logout,
      fetchWithRetry
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}