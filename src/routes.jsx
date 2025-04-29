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

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
  },
  {
    path: '/login',
    element: <LoginForm />,
  },
  {
    path: '/dashboard',
    element: (
      <AdminProtectedRoute>
        <AdminDashboard />
      </AdminProtectedRoute>
    ),
  },
  {
    path: '/team-dashboard',
    element: (
      <TeamMemberProtectedRoute>
        <UserDashboard />
      </TeamMemberProtectedRoute>
    ),
  },
  {
    path: '/superadmin/login',
    element: <SuperadminLogin />,
  },
  {
    path: '/superadmin/dashboard',
    element: (
      <SuperadminProtectedRoute>
        <SuperadminDashboard />
      </SuperadminProtectedRoute>
    ),
  },
]);

export function AppRouter() {
  return (
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  );
}