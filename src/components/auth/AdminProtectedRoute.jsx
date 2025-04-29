import { useEffect } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

export default function AdminProtectedRoute({ children }) {
  const { isAuthenticated, user, isLoading } = useAuth();

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    console.log('Not authenticated, redirecting to login');
    return <Navigate to="/login" replace />;
  }

  // Check if user is an admin
  if (!user) {
    console.error('No user data available');
    return <Navigate to="/login" replace />;
  }

  console.log('Checking user role:', user.role); // Debug log
  
  if (user.role !== 'admin') {
    console.error('Unauthorized access attempt. User role:', user.role);
    return <Navigate to="/login" replace />;
  }

  return children;
} 