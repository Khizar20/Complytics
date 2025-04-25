import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import App from './App';
import { AuthProvider } from './context/AuthContext';
import SuperadminLogin from './components/superadmin/SuperadminLogin';
import SuperadminDashboard from './components/superadmin/SuperadminDashboard';
import SuperadminProtectedRoute from './components/superadmin/SuperadminProtectedRoute';

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
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