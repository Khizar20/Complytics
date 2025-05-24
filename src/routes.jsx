import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import App from './App';
import { AuthProvider } from './context/AuthContext';
import SuperadminLogin from './components/superadmin/SuperadminLogin';
import SuperadminDashboard from './components/superadmin/SuperadminDashboard';
import SuperadminProtectedRoute from './components/superadmin/SuperadminProtectedRoute';
import LoginForm from './components/auth/LoginForm';
import AdminDashboard from './components/auth/AdminDashboard';
import AdminProtectedRoute from './components/auth/AdminProtectedRoute';
import UserDashboard from './components/team/UserDashboard';
import TeamMemberProtectedRoute from './components/team/TeamMemberProtectedRoute';
import ForgotPassword from './components/auth/ForgotPassword';

// Create a wrapper component that includes AuthProvider
const withAuth = (Component) => {
  return (
    <AuthProvider>
      {Component}
    </AuthProvider>
  );
};

const router = createBrowserRouter([
  {
    path: '/',
    element: withAuth(<App />),
  },
  {
    path: '/login',
    element: withAuth(<LoginForm />),
  },
  {
    path: '/forgot-password',
    element: withAuth(<ForgotPassword />),
  },
  {
    path: '/dashboard',
    element: withAuth(
      <AdminProtectedRoute>
        <AdminDashboard />
      </AdminProtectedRoute>
    ),
  },
  {
    path: '/team-dashboard',
    element: withAuth(
      <TeamMemberProtectedRoute>
        <UserDashboard />
      </TeamMemberProtectedRoute>
    ),
  },
  {
    path: '/superadmin/login',
    element: withAuth(<SuperadminLogin />),
  },
  {
    path: '/superadmin/dashboard',
    element: withAuth(
      <SuperadminProtectedRoute>
        <SuperadminDashboard />
      </SuperadminProtectedRoute>
    ),
  },
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}