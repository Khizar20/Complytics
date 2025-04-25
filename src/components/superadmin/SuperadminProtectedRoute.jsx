import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

export default function SuperadminProtectedRoute({ children }) {
  const { authToken, isLoading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isLoading && !authToken) {
      navigate('/superadmin/login');
    }
  }, [authToken, isLoading, navigate]);

  if (isLoading) {
    return <div>Loading...</div>;
  }

  return authToken ? children : null;
}