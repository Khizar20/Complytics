import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  FaCloud, 
  FaRobot, 
  FaDesktop, 
  FaCalendarAlt,
  FaChartLine,
  FaFileAlt,
  FaSignOutAlt,
  FaBars,
  FaTimes,
  FaUser
} from 'react-icons/fa';
import Profile from '../auth/Profile';

const UserDashboard = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [userData, setUserData] = useState(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [activeTab, setActiveTab] = useState('dashboard');

  useEffect(() => {
    const fetchUserData = async () => {
      try {
        const response = await fetch('http://localhost:8000/team/user-data', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        });
        
        if (!response.ok) {
          throw new Error('Failed to fetch user data');
        }
        
        const data = await response.json();
        setUserData(data);
      } catch (error) {
        console.error('Error fetching user data:', error);
      }
    };

    fetchUserData();
  }, []);

  const sidebarItems = [
    { id: 'dashboard', icon: <FaChartLine />, label: 'Dashboard' },
    { id: 'profile', icon: <FaUser />, label: 'Profile' },
    { id: 'azure', icon: <FaCloud />, label: 'Connect to Azure' },
    { id: 'chatbot', icon: <FaRobot />, label: 'Compliance Chatbot' },
    { id: 'testing', icon: <FaDesktop />, label: 'UI Testing' },
    { id: 'scan', icon: <FaCalendarAlt />, label: 'Schedule Compliance Scan' },
  ];

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  if (!userData) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
          className="h-12 w-12 border-t-2 border-b-2 border-primary rounded-full"
        />
      </div>
    );
  }

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="space-y-6"
          >
            <h2 className="text-2xl font-bold text-foreground">
              {userData.role === 'IT_TEAM' ? 'IT Team Dashboard' :
               userData.role === 'COMPLIANCE_TEAM' ? 'Compliance Team Dashboard' :
               'Management Team Dashboard'}
            </h2>
            
            <motion.div
              whileHover={{ scale: 1.02 }}
              className="p-6 bg-card rounded-xl shadow-lg hover:shadow-xl transition-shadow"
            >
              <h3 className="text-lg font-semibold mb-2">System Status</h3>
              <p className="text-muted-foreground">Monitor system health and performance</p>
            </motion.div>
            <motion.div
              whileHover={{ scale: 1.02 }}
              className="p-6 bg-card rounded-xl shadow-lg hover:shadow-xl transition-shadow"
            >
              <h3 className="text-lg font-semibold mb-2">Recent Activities</h3>
              <p className="text-muted-foreground">View recent system activities</p>
            </motion.div>
            <motion.div
              whileHover={{ scale: 1.02 }}
              className="p-6 bg-card rounded-xl shadow-lg hover:shadow-xl transition-shadow"
            >
              <h3 className="text-lg font-semibold mb-2">Notifications</h3>
              <p className="text-muted-foreground">Check your notifications</p>
            </motion.div>
          </motion.div>
        );
      case 'profile':
        return <Profile />;
      case 'azure':
        return (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="space-y-6"
          >
            <h2 className="text-2xl font-bold text-foreground">Azure Connection</h2>
            <div className="p-6 bg-card rounded-xl shadow-lg">
              <p className="text-muted-foreground">Azure connection settings and status</p>
            </div>
          </motion.div>
        );
      case 'chatbot':
        return (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="space-y-6"
          >
            <h2 className="text-2xl font-bold text-foreground">Compliance Chatbot</h2>
            <div className="p-6 bg-card rounded-xl shadow-lg">
              <p className="text-muted-foreground">Chatbot interface for compliance queries</p>
            </div>
          </motion.div>
        );
      case 'testing':
        return (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="space-y-6"
          >
            <h2 className="text-2xl font-bold text-foreground">UI Testing</h2>
            <div className="p-6 bg-card rounded-xl shadow-lg">
              <p className="text-muted-foreground">UI testing tools and reports</p>
            </div>
          </motion.div>
        );
      case 'scan':
        return (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="space-y-6"
          >
            <h2 className="text-2xl font-bold text-foreground">Schedule Compliance Scan</h2>
            <div className="p-6 bg-card rounded-xl shadow-lg">
              <p className="text-muted-foreground">Schedule and manage compliance scans</p>
            </div>
          </motion.div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Mobile Sidebar Toggle */}
      <div className="lg:hidden fixed top-4 left-4 z-50">
        <button
          onClick={() => setIsSidebarOpen(!isSidebarOpen)}
          className="p-2 rounded-lg bg-card shadow-lg"
        >
          {isSidebarOpen ? <FaTimes /> : <FaBars />}
        </button>
      </div>

      {/* Sidebar */}
      <motion.div
        initial={{ x: -300 }}
        animate={{ x: isSidebarOpen ? 0 : -300 }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className="fixed top-0 left-0 h-full w-64 bg-card shadow-lg z-40 lg:translate-x-0"
      >
        <div className="h-full flex flex-col">
          <div className="p-6 border-b border-border">
            <h1 className="text-xl font-bold text-foreground">Complytics</h1>
            <p className="text-sm text-muted-foreground">{userData.email}</p>
          </div>

          <nav className="flex-1 p-4 space-y-2">
            {sidebarItems.map((item) => (
              <motion.button
                key={item.id}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center space-x-3 p-3 rounded-lg transition-colors ${
                  activeTab === item.id
                    ? 'bg-primary text-primary-foreground'
                    : 'hover:bg-secondary'
                }`}
              >
                <span className="text-lg">{item.icon}</span>
                <span>{item.label}</span>
              </motion.button>
            ))}
          </nav>

          <div className="p-4 border-t border-border">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleLogout}
              className="w-full flex items-center space-x-3 p-3 rounded-lg text-destructive hover:bg-destructive/10"
            >
              <FaSignOutAlt />
              <span>Logout</span>
            </motion.button>
          </div>
        </div>
      </motion.div>

      {/* Main Content */}
      <div className={`lg:ml-64 transition-all duration-300 ${isSidebarOpen ? 'ml-64' : 'ml-0'}`}>
        <div className="p-6">
          {renderContent()}
        </div>
      </div>
    </div>
  );
};

export default UserDashboard; 