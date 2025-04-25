// src/context/AuthContext.jsx
import { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [authToken, setAuthToken] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('superadminToken');
    setAuthToken(token);
    setIsLoading(false);
  }, []);

  const login = (token) => {
    localStorage.setItem('superadminToken', token);
    setAuthToken(token);
  };

  const logout = () => {
    localStorage.removeItem('superadminToken');
    setAuthToken(null);
  };

  return (
    <AuthContext.Provider value={{ 
      authToken, 
      isLoading, 
      login, 
      logout 
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}