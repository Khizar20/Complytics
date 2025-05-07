import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../ui/button';
import { motion } from 'framer-motion';
import { FaChartLine, FaUser, FaSignOutAlt } from 'react-icons/fa';
import Profile from './Profile';

const UserDashboard = () => {
  const { authToken, logout, user, isLoading } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('dashboard');

  useEffect(() => {
    // Only redirect if we're sure we're not loading and there's no token
    if (!isLoading && !authToken) {
      navigate('/login');
    }
  }, [authToken, isLoading, navigate]);

  // Don't render anything while loading
  if (isLoading) {
    return null;
  }

  const sidebarItems = [
    { id: 'dashboard', icon: <FaChartLine />, label: 'Dashboard' },
    { id: 'profile', icon: <FaUser />, label: 'Profile' },
  ];

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return (
          <div className="p-8">
            <h1 className="text-2xl font-bold mb-4">User Dashboard</h1>
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
              <h2 className="text-xl font-semibold mb-4">Welcome, {user?.first_name}!</h2>
              <p className="text-gray-600 dark:text-gray-300">
                This is your user dashboard. You can manage your profile and view your information here.
              </p>
            </div>
          </div>
        );
      case 'profile':
        return <Profile />;
      default:
        return null;
    }
  };

  return (
    <div className="flex min-h-screen bg-background">
      {/* Sidebar */}
      <motion.div
        initial={{ x: -100, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ duration: 0.5 }}
        className="fixed top-0 left-0 w-64 h-screen bg-card shadow-xl z-[100] transition-all duration-300"
      >
        <div className="flex flex-col h-full bg-card">
          {/* Logo */}
          <div className="p-4 border-b border-border bg-card">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 rounded-md bg-primary flex items-center justify-center">
                <span className="text-white font-bold text-lg">C</span>
              </div>
              <span className="font-bold text-lg text-foreground">Complytics</span>
            </div>
          </div>

          {/* Navigation Items */}
          <nav className="flex-1 p-4 space-y-2 bg-card">
            {sidebarItems.map((item) => (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors ${
                  activeTab === item.id
                    ? 'bg-primary text-primary-foreground'
                    : 'text-foreground hover:bg-secondary'
                }`}
              >
                {item.icon}
                <span>{item.label}</span>
              </button>
            ))}
          </nav>

          {/* Logout Button */}
          <div className="p-4 border-t border-border">
            <button
              onClick={logout}
              className="w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-destructive hover:bg-destructive/10 transition-colors"
            >
              <FaSignOutAlt />
              <span>Logout</span>
            </button>
          </div>
        </div>
      </motion.div>

      {/* Main Content */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
        className="flex-1 overflow-auto ml-64"
      >
        {renderContent()}
      </motion.div>
    </div>
  );
};

export default UserDashboard; 