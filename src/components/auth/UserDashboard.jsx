import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../ui/button';
import { motion } from 'framer-motion';
import { FaChartLine, FaUser, FaSignOutAlt } from 'react-icons/fa';
import Profile from './Profile';

const UserDashboard = () => {
  const { authToken, logout, user } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('dashboard');

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
        className="w-64 bg-white dark:bg-gray-800 shadow-lg"
      >
        <div className="p-4">
          <h2 className="text-xl font-bold text-primary mb-6">User Panel</h2>
          <nav className="space-y-2">
            {sidebarItems.map((item) => (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors ${
                  activeTab === item.id
                    ? 'bg-primary text-white'
                    : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                }`}
              >
                {item.icon}
                <span>{item.label}</span>
              </button>
            ))}
          </nav>
          <div className="mt-8">
            <button
              onClick={() => {
                logout();
                navigate('/login');
              }}
              className="w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-red-600 hover:bg-red-50 transition-colors"
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
        className="flex-1 overflow-auto"
      >
        {renderContent()}
      </motion.div>
    </div>
  );
};

export default UserDashboard; 