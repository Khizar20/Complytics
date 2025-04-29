import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

const TeamMemberProtectedRoute = ({ children }) => {
  const { isAuthenticated, user } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Check if user is a team member
  if (!user || !['it_team', 'compliance_team', 'management_team'].includes(user.role)) {
    return <Navigate to="/login" replace />;
  }

  return children;
};

export default TeamMemberProtectedRoute; 