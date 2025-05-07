import { useEffect, useState } from 'react';
import { 
  FaCheckCircle, 
  FaTimesCircle, 
  FaSpinner, 
  FaUserPlus,
  FaUserCheck,
  FaBuilding,
  FaEnvelope,
  FaUserTie,
  FaUsers,
  FaGlobe,
  FaSignOutAlt,
  FaHome,
  FaChartLine,
  FaCog
} from 'react-icons/fa';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { useAuth } from '../../context/AuthContext';
import { useNavigate } from 'react-router-dom';

// Animation variants
const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1
    }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5 } }
};

const cardHoverVariants = {
  hover: { 
    y: -5,
    boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.1)",
    transition: { duration: 0.3 }
  }
};

// Skeleton loader components
const RequestSkeleton = () => (
  <motion.div className="glass-card p-6 rounded-lg space-y-4" variants={itemVariants}>
    <div className="flex items-center space-x-4">
      <div className="h-12 w-12 bg-muted rounded-full animate-pulse"></div>
      <div className="flex-1 space-y-2">
        <div className="h-4 bg-muted rounded w-3/4 animate-pulse"></div>
        <div className="h-3 bg-muted rounded w-1/2 animate-pulse"></div>
      </div>
    </div>
    <div className="space-y-2">
      <div className="h-3 bg-muted rounded w-full animate-pulse"></div>
      <div className="h-3 bg-muted rounded w-5/6 animate-pulse"></div>
    </div>
    <div className="h-10 bg-muted rounded-md w-24 animate-pulse"></div>
  </motion.div>
);

const OrganizationSkeleton = () => (
  <motion.div className="glass-card p-6 rounded-lg space-y-4" variants={itemVariants}>
    <div className="flex items-center space-x-4">
      <div className="h-12 w-12 bg-muted rounded-full animate-pulse"></div>
      <div className="flex-1 space-y-2">
        <div className="h-4 bg-muted rounded w-full animate-pulse"></div>
        <div className="h-3 bg-muted rounded w-3/4 animate-pulse"></div>
      </div>
    </div>
  </motion.div>
);

const UserSkeleton = () => (
  <motion.div className="glass-card p-6 rounded-lg space-y-4" variants={itemVariants}>
    <div className="flex items-center space-x-4">
      <div className="h-12 w-12 bg-muted rounded-full animate-pulse"></div>
      <div className="flex-1 space-y-2">
        <div className="h-4 bg-muted rounded w-3/4 animate-pulse"></div>
        <div className="h-3 bg-muted rounded w-1/2 animate-pulse"></div>
      </div>
    </div>
    <div className="space-y-2">
      <div className="h-3 bg-muted rounded w-full animate-pulse"></div>
      <div className="h-3 bg-muted rounded w-5/6 animate-pulse"></div>
    </div>
  </motion.div>
);

const SuperadminDashboard = () => {
  const { authToken, logout, fetchWithRetry } = useAuth();
  const navigate = useNavigate();
  const [requests, setRequests] = useState([]);
  const [organizations, setOrganizations] = useState([]);
  const [activeUsers, setActiveUsers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [orgsLoading, setOrgsLoading] = useState(true);
  const [usersLoading, setUsersLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [activeTab, setActiveTab] = useState('registrations');
  const [approvingId, setApprovingId] = useState(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  useEffect(() => {
    if (!authToken) {
      navigate('/superadmin/login');
    }
  }, [authToken, navigate]);

  // Fetch pending registrations
  useEffect(() => {
    const fetchRequests = async () => {
      try {
        const response = await fetchWithRetry('http://localhost:8000/registration/pending-registrations');

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to fetch requests');
        }
        const data = await response.json();
        setRequests(data);
      } catch (err) {
        console.error('Error fetching requests:', err);
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    };

    if (authToken) {
      fetchRequests();
    }
  }, [authToken, fetchWithRetry]);

  // Fetch active organizations
  useEffect(() => {
    const fetchOrganizations = async () => {
      try {
        const response = await fetchWithRetry('http://localhost:8000/superadmin/organizations/active');

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to fetch organizations');
        }
        const data = await response.json();
        setOrganizations(data);
      } catch (err) {
        console.error('Error fetching organizations:', err);
        setError(err.message);
      } finally {
        setOrgsLoading(false);
      }
    };

    if (authToken) {
      fetchOrganizations();
    }
  }, [authToken, fetchWithRetry]);

  // Fetch active users
  useEffect(() => {
    const fetchActiveUsers = async () => {
      try {
        const response = await fetchWithRetry('http://localhost:8000/superadmin/active-users');

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to fetch active users');
        }
        const data = await response.json();
        setActiveUsers(data);
      } catch (err) {
        console.error('Error fetching active users:', err);
        setError(err.message);
      } finally {
        setUsersLoading(false);
      }
    };

    if (authToken) {
      fetchActiveUsers();
    }
  }, [authToken, fetchWithRetry]);

  const handleApprove = async (requestId) => {
    try {
      setApprovingId(requestId);
      setError('');
      setSuccess('');

      const response = await fetchWithRetry(`http://localhost:8000/registration/approve-registration/${requestId}`, {
        method: 'POST'
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to approve request');
      }

      setSuccess('Request approved successfully');
      // Refresh the requests list
      const updatedResponse = await fetchWithRetry('http://localhost:8000/registration/pending-registrations');
      if (updatedResponse.ok) {
        const updatedData = await updatedResponse.json();
        setRequests(updatedData);
      }
    } catch (err) {
      console.error('Error approving request:', err);
      setError(err.message);
    } finally {
      setApprovingId(null);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/superadmin/login');
  };

  const handleHome = () => {
    navigate('/');
  };

  const sidebarItems = [
    { id: 'home', icon: <FaHome />, label: 'Home', onClick: handleHome },
    { id: 'registrations', icon: <FaUserPlus />, label: 'Registrations', onClick: () => setActiveTab('registrations') },
    { id: 'organizations', icon: <FaBuilding />, label: 'Organizations', onClick: () => setActiveTab('organizations') },
    { id: 'users', icon: <FaUsers />, label: 'Users', onClick: () => setActiveTab('users') },
    { id: 'settings', icon: <FaCog />, label: 'Settings', onClick: () => setActiveTab('settings') },
  ];

  return (
    <div className="flex min-h-screen bg-background">
      {/* Sidebar */}
    <motion.div 
        initial={{ x: -100, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.5 }}
        className={`fixed top-0 left-0 h-full bg-card shadow-lg z-50 transition-all duration-300 ${
          isSidebarOpen ? 'w-64' : 'w-20'
        }`}
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="p-4 border-b border-border">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 rounded-md bg-primary flex items-center justify-center">
                <span className="text-white font-bold text-lg">C</span>
              </div>
              {isSidebarOpen && <span className="font-bold text-lg">Complytics</span>}
            </div>
          </div>

          {/* Navigation Items */}
          <nav className="flex-1 p-4 space-y-2">
            {sidebarItems.map((item) => (
              <motion.button
                key={item.id}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={item.onClick}
                className={`w-full flex items-center space-x-3 p-3 rounded-lg transition-colors ${
                  activeTab === item.id
                    ? 'bg-primary text-primary-foreground'
                    : 'hover:bg-secondary'
                }`}
              >
                <span className="text-lg">{item.icon}</span>
                {isSidebarOpen && <span>{item.label}</span>}
              </motion.button>
            ))}
          </nav>

          {/* Logout Button */}
          <div className="p-4 border-t border-border">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleLogout}
              className="w-full flex items-center space-x-3 p-3 rounded-lg text-destructive hover:bg-destructive/10"
            >
              <FaSignOutAlt />
              {isSidebarOpen && <span>Logout</span>}
            </motion.button>
          </div>
        </div>
      </motion.div>

      {/* Main Content */}
      <div className={`flex-1 transition-all duration-300 ${isSidebarOpen ? 'ml-64' : 'ml-20'}`}>
        <div className="p-8">
        {/* Header */}
        <motion.div 
          initial={{ y: -20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.5 }}
          className="flex justify-between items-center mb-8"
        >
          <div>
            <h1 className="text-3xl md:text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-purple-600">
              Superadmin Dashboard
            </h1>
            <p className="mt-2 text-muted-foreground">
              Manage organizations and user registrations
            </p>
          </div>
            <Button
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              variant="outline"
              className="lg:hidden"
            >
              {isSidebarOpen ? 'Close Sidebar' : 'Open Sidebar'}
            </Button>
        </motion.div>

        {/* Stats cards */}
        <motion.div 
          className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8"
          initial="hidden"
          animate="show"
          variants={containerVariants}
        >
          {/* Pending Requests Card */}
          <motion.div 
            variants={itemVariants}
            className="glass-card p-6 rounded-lg border-l-4 border-primary"
            whileHover={{ scale: 1.02 }}
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Pending Requests</p>
                <h3 className="text-2xl font-bold">{requests.length}</h3>
              </div>
              <div className="p-3 rounded-full bg-primary/10 text-primary">
                <FaUserPlus className="h-6 w-6" />
              </div>
            </div>
          </motion.div>

          {/* Active Organizations Card */}
          <motion.div 
            variants={itemVariants}
            className="glass-card p-6 rounded-lg border-l-4 border-green-500"
            whileHover={{ scale: 1.02 }}
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Active Organizations</p>
                <h3 className="text-2xl font-bold">{organizations.length}</h3>
              </div>
              <div className="p-3 rounded-full bg-green-500/10 text-green-500">
                <FaBuilding className="h-6 w-6" />
              </div>
            </div>
          </motion.div>

          {/* Active Users Card */}
          <motion.div 
            variants={itemVariants}
            className="glass-card p-6 rounded-lg border-l-4 border-blue-500"
            whileHover={{ scale: 1.02 }}
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Active Users</p>
                <h3 className="text-2xl font-bold">{activeUsers.length}</h3>
              </div>
              <div className="p-3 rounded-full bg-blue-500/10 text-blue-500">
                <FaUsers className="h-6 w-6" />
              </div>
            </div>
          </motion.div>
        </motion.div>

        {/* Messages */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="glass-card bg-destructive/10 text-destructive p-4 mb-6 rounded-lg flex items-center"
            >
              <FaTimesCircle className="mr-2" />
              {error}
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {success && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="glass-card bg-green-500/10 text-green-500 p-4 mb-6 rounded-lg flex items-center"
            >
              <FaCheckCircle className="mr-2" />
              {success}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Tabs */}
        <div className="flex border-b border-border mb-6">
          <button
            className={`px-4 py-2 font-medium ${activeTab === 'registrations' ? 'text-primary border-b-2 border-primary' : 'text-muted-foreground'}`}
            onClick={() => setActiveTab('registrations')}
          >
            Pending Registrations
          </button>
          <button
            className={`px-4 py-2 font-medium ${activeTab === 'organizations' ? 'text-primary border-b-2 border-primary' : 'text-muted-foreground'}`}
            onClick={() => setActiveTab('organizations')}
          >
            Active Organizations
          </button>
          <button
            className={`px-4 py-2 font-medium ${activeTab === 'users' ? 'text-primary border-b-2 border-primary' : 'text-muted-foreground'}`}
            onClick={() => setActiveTab('users')}
          >
            Active Users
          </button>
        </div>

        {/* Content based on active tab */}
        {activeTab === 'registrations' ? (
          /* Pending Registrations Tab */
          isLoading ? (
            <motion.div className="grid gap-6" initial="hidden" animate="show" variants={containerVariants}>
              {[1, 2, 3].map((i) => <RequestSkeleton key={i} />)}
            </motion.div>
          ) : requests.length === 0 ? (
            <motion.div variants={itemVariants} className="glass-card p-8 text-center rounded-xl">
              <div className="mx-auto flex items-center justify-center w-16 h-16 bg-muted rounded-full mb-4">
                <FaUserTie className="h-8 w-8 text-muted-foreground" />
              </div>
              <h3 className="text-lg font-medium">No pending requests</h3>
              <p className="text-muted-foreground mt-2">All registration requests have been processed</p>
            </motion.div>
          ) : (
            <motion.div initial="hidden" animate="show" variants={containerVariants} className="grid gap-6">
              <AnimatePresence>
                {requests.map((request) => (
                  <motion.div
                    key={request._id}
                    variants={itemVariants}
                    whileHover={cardHoverVariants.hover}
                    className="glass-card p-6 rounded-lg border border-border/50"
                  >
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                      <div className="flex items-start space-x-4">
                        <div className="flex-shrink-0">
                          <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center text-primary">
                            <FaUserTie className="h-5 w-5" />
                          </div>
                        </div>
                        <div>
                          <h3 className="font-medium text-lg">
                            {request.user_data?.organization_name || 'No organization name'}
                          </h3>
                          <div className="flex items-center text-sm text-muted-foreground mt-1">
                            <FaEnvelope className="mr-2" />
                            {request.user_data?.email || 'No email'}
                          </div>
                          <div className="flex items-center text-sm text-muted-foreground mt-1">
                            <FaUserTie className="mr-2" />
                            {request.user_data?.first_name} {request.user_data?.last_name}
                          </div>
                        </div>
                      </div>

                      <div className="space-y-2">
                        <div className="flex items-center text-sm">
                          <span className="font-medium">Submitted:</span>
                          <span className="ml-1">
                            {request.created_at ? 
                              new Date(request.created_at).toLocaleDateString() : 
                              'Unknown date'}
                          </span>
                        </div>
                        <div className="flex items-center text-sm">
                          <span className="font-medium">Domain:</span>
                          <span className="ml-1">
                            {request.user_data?.organization_domain || 'No domain'}
                          </span>
                        </div>
                      </div>

                      <div className="flex justify-end items-center space-x-2">
                        <Button 
                          variant="default" 
                          size="sm" 
                          onClick={() => handleApprove(request._id)}
                          className="flex items-center gap-2"
                          disabled={approvingId === request._id}
                        >
                          {approvingId === request._id ? (
                            <FaSpinner className="animate-spin" />
                          ) : (
                            <FaCheckCircle />
                          )}
                          Approve
                        </Button>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </motion.div>
          )
        ) : activeTab === 'organizations' ? (
          /* Active Organizations Tab */
          orgsLoading ? (
            <motion.div className="grid gap-6" initial="hidden" animate="show" variants={containerVariants}>
              {[1, 2, 3].map((i) => <OrganizationSkeleton key={i} />)}
            </motion.div>
          ) : organizations.length === 0 ? (
            <motion.div variants={itemVariants} className="glass-card p-8 text-center rounded-xl">
              <div className="mx-auto flex items-center justify-center w-16 h-16 bg-muted rounded-full mb-4">
                <FaBuilding className="h-8 w-8 text-muted-foreground" />
              </div>
              <h3 className="text-lg font-medium">No active organizations</h3>
              <p className="text-muted-foreground mt-2">Approved organizations will appear here</p>
            </motion.div>
          ) : (
            <motion.div initial="hidden" animate="show" variants={containerVariants} className="grid gap-6">
              {organizations.map((org) => (
                <motion.div
                  key={org._id}
                  variants={itemVariants}
                  whileHover={cardHoverVariants.hover}
                  className="glass-card p-6 rounded-lg border border-border/50"
                >
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="flex items-start space-x-4">
                      <div className="flex-shrink-0">
                        <div className="h-12 w-12 rounded-full bg-blue-500/10 flex items-center justify-center text-blue-500">
                          <FaBuilding className="h-5 w-5" />
                        </div>
                      </div>
                      <div>
                        <h3 className="font-medium text-lg">{org.name}</h3>
                        <div className="flex items-center text-sm text-muted-foreground mt-1">
                          <FaGlobe className="mr-2" />
                          {org.domain}
                        </div>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center text-sm">
                        <span className="font-medium">Status:</span>
                        <span className={`ml-2 px-2 py-1 text-xs rounded-full ${org.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                          {org.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </div>
                      <div className="flex items-center text-sm">
                        <span className="font-medium">Created:</span>
                        <span className="ml-1">
                          {new Date(org.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>

                    <div className="flex justify-end items-center space-x-2">
                      <Button variant="outline" size="sm">
                        View Details
                      </Button>
                    </div>
                  </div>
                </motion.div>
              ))}
            </motion.div>
          )
        ) : (
          /* Active Users Tab */
          usersLoading ? (
            <motion.div className="grid gap-6" initial="hidden" animate="show" variants={containerVariants}>
              {[1, 2, 3].map((i) => <UserSkeleton key={i} />)}
            </motion.div>
          ) : activeUsers.length === 0 ? (
            <motion.div variants={itemVariants} className="glass-card p-8 text-center rounded-xl">
              <div className="mx-auto flex items-center justify-center w-16 h-16 bg-muted rounded-full mb-4">
                <FaUserCheck className="h-8 w-8 text-muted-foreground" />
              </div>
              <h3 className="text-lg font-medium">No active users</h3>
              <p className="text-muted-foreground mt-2">All users are currently inactive</p>
            </motion.div>
          ) : (
            <motion.div initial="hidden" animate="show" variants={containerVariants} className="grid gap-6">
              {activeUsers.map((user) => (
                <motion.div
                  key={user._id}
                  variants={itemVariants}
                  whileHover={cardHoverVariants.hover}
                  className="glass-card p-6 rounded-lg border border-border/50"
                >
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                    <div className="flex items-start space-x-4">
                      <div className="flex-shrink-0">
                        <div className="h-12 w-12 rounded-full bg-blue-500/10 flex items-center justify-center text-blue-500">
                          <FaUserCheck className="h-5 w-5" />
                        </div>
                      </div>
                      <div>
                        <h3 className="font-medium text-lg">
                          {user.first_name} {user.last_name}
                        </h3>
                        <div className="flex items-center text-sm text-muted-foreground mt-1">
                          <FaEnvelope className="mr-2" />
                          {user.email}
                        </div>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center text-sm">
                        <span className="font-medium">Role:</span>
                        <span className="ml-1 capitalize">{user.role}</span>
                      </div>
                      <div className="flex items-center text-sm">
                        <span className="font-medium">Status:</span>
                        <span className={`ml-2 px-2 py-1 text-xs rounded-full ${
                          user.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                        }`}>
                          {user.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center text-sm">
                        <span className="font-medium">Organization:</span>
                        <span className="ml-1">
                          {user.organization_id || 'Not assigned'}
                        </span>
                      </div>
                      <div className="flex items-center text-sm">
                        <span className="font-medium">Joined:</span>
                        <span className="ml-1">
                          {new Date(user.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>

                    <div className="flex justify-end items-center space-x-2">
                      <Button variant="outline" size="sm">
                        View Details
                      </Button>
                    </div>
                  </div>
                </motion.div>
              ))}
            </motion.div>
          )
        )}
      </div>
      </div>
    </div>
  );
};

export default SuperadminDashboard;