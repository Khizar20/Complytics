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
  FaCog,
  FaTrash
} from 'react-icons/fa';
import { motion, AnimatePresence } from 'framer-motion';
import { useToast } from '@/components/ui/toast';
import { Button } from '@/components/ui/button';
import { useAuth } from '../../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { buildApiUrl } from "@/lib/api";

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
  <motion.div className="bg-white/80 backdrop-blur-sm p-6 rounded-2xl shadow-lg space-y-4" variants={itemVariants}>
    <div className="flex items-center space-x-4">
      <div className="h-12 w-12 bg-gradient-to-br from-gray-200 to-gray-300 rounded-xl animate-pulse"></div>
      <div className="flex-1 space-y-2">
        <div className="h-4 bg-gradient-to-r from-gray-200 to-gray-300 rounded w-3/4 animate-pulse"></div>
        <div className="h-3 bg-gradient-to-r from-gray-200 to-gray-300 rounded w-1/2 animate-pulse"></div>
      </div>
    </div>
    <div className="space-y-2">
      <div className="h-3 bg-gradient-to-r from-gray-200 to-gray-300 rounded w-full animate-pulse"></div>
      <div className="h-3 bg-gradient-to-r from-gray-200 to-gray-300 rounded w-5/6 animate-pulse"></div>
    </div>
    <div className="h-10 bg-gradient-to-r from-gray-200 to-gray-300 rounded-xl w-24 animate-pulse"></div>
  </motion.div>
);

const OrganizationSkeleton = () => (
  <motion.div className="bg-white/80 backdrop-blur-sm p-6 rounded-2xl shadow-lg space-y-4" variants={itemVariants}>
    <div className="flex items-center space-x-4">
      <div className="h-12 w-12 bg-gradient-to-br from-gray-200 to-gray-300 rounded-xl animate-pulse"></div>
      <div className="flex-1 space-y-2">
        <div className="h-4 bg-gradient-to-r from-gray-200 to-gray-300 rounded w-full animate-pulse"></div>
        <div className="h-3 bg-gradient-to-r from-gray-200 to-gray-300 rounded w-3/4 animate-pulse"></div>
      </div>
    </div>
  </motion.div>
);

const UserSkeleton = () => (
  <motion.div className="bg-white/80 backdrop-blur-sm p-6 rounded-2xl shadow-lg space-y-4" variants={itemVariants}>
    <div className="flex items-center space-x-4">
      <div className="h-12 w-12 bg-gradient-to-br from-gray-200 to-gray-300 rounded-xl animate-pulse"></div>
      <div className="flex-1 space-y-2">
        <div className="h-4 bg-gradient-to-r from-gray-200 to-gray-300 rounded w-3/4 animate-pulse"></div>
        <div className="h-3 bg-gradient-to-r from-gray-200 to-gray-300 rounded w-1/2 animate-pulse"></div>
      </div>
    </div>
    <div className="space-y-2">
      <div className="h-3 bg-gradient-to-r from-gray-200 to-gray-300 rounded w-full animate-pulse"></div>
      <div className="h-3 bg-gradient-to-r from-gray-200 to-gray-300 rounded w-5/6 animate-pulse"></div>
    </div>
  </motion.div>
);

const SuperadminDashboard = () => {
  const { authToken, logout, fetchWithRetry } = useAuth();
  const { toast } = useToast();
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
  const [deletionRequests, setDeletionRequests] = useState([]);
  const [approvingId, setApprovingId] = useState(null);
  const [rejectingId, setRejectingId] = useState(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [showApproveDialog, setShowApproveDialog] = useState(false);
  const [showRejectDialog, setShowRejectDialog] = useState(false);
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [uploadingFramework, setUploadingFramework] = useState(false);
  const [frameworkUploadSuccess, setFrameworkUploadSuccess] = useState('');
  const [frameworkUploadError, setFrameworkUploadError] = useState('');
  const [frameworks, setFrameworks] = useState([]);
  const [frameworksLoading, setFrameworksLoading] = useState(true);
  const [showApproveDeletionDialog, setShowApproveDeletionDialog] = useState(false);
  const [showRejectDeletionDialog, setShowRejectDeletionDialog] = useState(false);
  const [showDeleteUserDialog, setShowDeleteUserDialog] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [deletingUserId, setDeletingUserId] = useState(null);

  useEffect(() => {
    if (!authToken) {
      navigate('/superadmin/login');
    }
  }, [authToken, navigate]);

  // Fetch pending registrations
  useEffect(() => {
    const fetchRequests = async () => {
      try {
        const response = await fetchWithRetry(buildApiUrl('/registration/pending-registrations'));

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

  // Fetch deletion requests
  useEffect(() => {
    const fetchDeletionRequests = async () => {
      try {
        const response = await fetchWithRetry(buildApiUrl('/superadmin/deletion-requests'));
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to fetch deletion requests');
        }
        const data = await response.json();
        setDeletionRequests(data);
      } catch (err) {
        console.error('Error fetching deletion requests:', err);
        setError(err.message);
      }
    };
    if (authToken) fetchDeletionRequests();
  }, [authToken, fetchWithRetry]);

  // Fetch active organizations
  useEffect(() => {
    const fetchOrganizations = async () => {
      try {
        const response = await fetchWithRetry(buildApiUrl('/superadmin/organizations/active'));

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
        const response = await fetchWithRetry(buildApiUrl('/superadmin/active-users'));

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

  // Helper function to get organization name by ID
  const getOrganizationName = (organizationId) => {
    if (!organizationId) return 'Not assigned';
    const org = organizations.find(org => org.id === organizationId || org._id === organizationId);
    return org ? org.name : organizationId; // Fallback to ID if not found
  };

  // Fetch framework documents
  useEffect(() => {
    const fetchFrameworks = async () => {
      try {
        const response = await fetchWithRetry(buildApiUrl('/api/compliance/framework-documents'));

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to fetch framework documents');
        }
        const data = await response.json();
        setFrameworks(data);
      } catch (err) {
        console.error('Error fetching framework documents:', err);
        setError(err.message);
      } finally {
        setFrameworksLoading(false);
      }
    };

    if (authToken) {
      fetchFrameworks();
    }
  }, [authToken, fetchWithRetry]);

  const handleApprove = async (requestId) => {
    try {
      setApprovingId(requestId);
      setError('');
      setSuccess('');

      const response = await fetchWithRetry(buildApiUrl(`/registration/approve-registration/${requestId}`), {
        method: 'POST'
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to approve request');
      }

      toast({ title: 'Registration approved', variant: 'success' });
      // Refresh the requests list
      const updatedResponse = await fetchWithRetry(buildApiUrl('/registration/pending-registrations'));
      if (updatedResponse.ok) {
        const updatedData = await updatedResponse.json();
        setRequests(updatedData);
      }
    } catch (err) {
      console.error('Error approving request:', err);
      toast({ title: 'Failed to approve request', description: err.message, variant: 'error' });
    } finally {
      setApprovingId(null);
      setShowApproveDialog(false);
      setSelectedRequest(null);
    }
  };

  const handleReject = async (requestId) => {
    try {
      setRejectingId(requestId);
      setError('');
      setSuccess('');

      const response = await fetchWithRetry(buildApiUrl(`/registration/reject-registration/${requestId}`), {
        method: 'POST'
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to reject request');
      }

      toast({ title: 'Registration rejected', variant: 'success' });
      // Refresh the requests list
      const updatedResponse = await fetchWithRetry(buildApiUrl('/registration/pending-registrations'));
      if (updatedResponse.ok) {
        const updatedData = await updatedResponse.json();
        setRequests(updatedData);
      }
    } catch (err) {
      console.error('Error rejecting request:', err);
      toast({ title: 'Failed to reject request', description: err.message, variant: 'error' });
    } finally {
      setRejectingId(null);
      setShowRejectDialog(false);
      setSelectedRequest(null);
    }
  };

  // Delete user handler
  const handleDeleteUser = async () => {
    if (!selectedUser) return;
    
    try {
      setDeletingUserId(selectedUser._id);
      setError('');
      setSuccess('');

      const response = await fetchWithRetry(
        buildApiUrl(`/superadmin/users/${selectedUser._id}`),
        {
          method: 'DELETE'
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to delete user');
      }

      const result = await response.json();
      
      toast({ 
        title: 'User deleted successfully', 
        description: result.message,
        variant: 'success' 
      });
      
      // Refresh the users list
      const updatedResponse = await fetchWithRetry(buildApiUrl('/superadmin/active-users'));
      if (updatedResponse.ok) {
        const updatedData = await updatedResponse.json();
        setActiveUsers(updatedData);
      }
      
      // Refresh organizations list if organization was deleted
      if (result.deleted_organization_id) {
        const orgsResponse = await fetchWithRetry(buildApiUrl('/superadmin/organizations/active'));
        if (orgsResponse.ok) {
          const orgsData = await orgsResponse.json();
          setOrganizations(orgsData);
        }
      }
    } catch (err) {
      console.error('Error deleting user:', err);
      toast({ 
        title: 'Failed to delete user', 
        description: err.message, 
        variant: 'error' 
      });
    } finally {
      setDeletingUserId(null);
      setShowDeleteUserDialog(false);
      setSelectedUser(null);
    }
  };

  // Deletion requests handlers
  const handleApproveDeletion = async (requestId) => {
    try {
      setApprovingId(requestId);
      const r = await fetchWithRetry(buildApiUrl(`/superadmin/deletion-requests/${requestId}/approve`), { method: 'POST' });
      if (!r.ok) {
        const e = await r.json();
        throw new Error(e.detail || 'Failed to approve deletion');
      }
      toast({ title: 'Deletion approved', variant: 'success' });
      const refresh = await fetchWithRetry(buildApiUrl('/superadmin/deletion-requests'));
      if (refresh.ok) setDeletionRequests(await refresh.json());
    } catch (err) {
      toast({ title: 'Failed to approve deletion', description: err.message, variant: 'error' });
    } finally {
      setApprovingId(null);
      setShowApproveDeletionDialog(false);
      setSelectedRequest(null);
    }
  };

  const handleRejectDeletion = async (requestId) => {
    try {
      setRejectingId(requestId);
      const r = await fetchWithRetry(buildApiUrl(`/superadmin/deletion-requests/${requestId}/reject`), { method: 'POST' });
      if (!r.ok) {
        const e = await r.json();
        throw new Error(e.detail || 'Failed to reject deletion');
      }
      toast({ title: 'Deletion rejected', variant: 'success' });
      const refresh = await fetchWithRetry(buildApiUrl('/superadmin/deletion-requests'));
      if (refresh.ok) setDeletionRequests(await refresh.json());
    } catch (err) {
      toast({ title: 'Failed to reject deletion', description: err.message, variant: 'error' });
    } finally {
      setRejectingId(null);
      setShowRejectDeletionDialog(false);
      setSelectedRequest(null);
    }
  };

  const openApproveDialog = (request) => {
    setSelectedRequest(request);
    setShowApproveDialog(true);
  };

  const openRejectDialog = (request) => {
    setSelectedRequest(request);
    setShowRejectDialog(true);
  };

  const handleLogout = () => {
    logout();
    navigate('/superadmin/login');
  };

  const handleHome = () => {
    navigate('/');
  };

  const handleFrameworkUpload = async (event) => {
    const files = Array.from(event.target.files);
    if (files.length === 0) return;

    // Check file types
    const validTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
    const invalidFiles = files.filter(file => !validTypes.includes(file.type));
    
    if (invalidFiles.length > 0) {
      setFrameworkUploadError('Please upload only PDF or DOCX files');
      return;
    }

    setUploadingFramework(true);
    setFrameworkUploadError('');
    setFrameworkUploadSuccess('');

    let successCount = 0;
    let errorCount = 0;

    for (const file of files) {
      const formData = new FormData();
      formData.append('file', file);

      try {
        const response = await fetchWithRetry(buildApiUrl('/api/compliance/upload-framework'), {
          method: 'POST',
          body: formData
        });

        if (!response.ok) {
          const errorData = await response.json();
          if (response.status === 400 && errorData.detail.includes('duplicate')) {
            errorCount++;
            console.error(`Error uploading ${file.name}: ${errorData.detail}`);
          } else {
            throw new Error(errorData.detail || `Failed to upload ${file.name}`);
          }
          continue;
        }

        const data = await response.json();
        successCount++;
      } catch (error) {
        console.error(`Error uploading ${file.name}:`, error);
        errorCount++;
      }
    }

    if (successCount > 0) {
      setFrameworkUploadSuccess(`Successfully uploaded ${successCount} document${successCount > 1 ? 's' : ''}`);
    }
    if (errorCount > 0) {
      setFrameworkUploadError(`Failed to upload ${errorCount} document${errorCount > 1 ? 's' : ''}`);
    }

    setUploadingFramework(false);
  };

  const sidebarItems = [
    { id: 'home', icon: <FaHome />, label: 'Home', onClick: handleHome },
    { id: 'registrations', icon: <FaUserPlus />, label: 'Registrations', onClick: () => setActiveTab('registrations') },
    { id: 'organizations', icon: <FaBuilding />, label: 'Organizations', onClick: () => setActiveTab('organizations') },
    { id: 'users', icon: <FaUsers />, label: 'Users', onClick: () => setActiveTab('users') },
    { id: 'deletions', icon: <FaTimesCircle />, label: 'Deletion Requests', onClick: () => setActiveTab('deletions') },
    { id: 'frameworks', icon: <FaCog />, label: 'Frameworks', onClick: () => setActiveTab('frameworks') },
  ];

  return (
    <>
      <div className="flex min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50/50">
        {/* Sidebar */}
        <motion.div 
          initial={{ x: -100, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={{ duration: 0.5 }}
          className={`fixed top-0 left-0 h-full bg-gradient-to-b from-gray-900 via-black to-gray-900 backdrop-blur-xl shadow-2xl z-50 transition-all duration-300 ${
            isSidebarOpen ? 'w-64' : 'w-20'
          }`}
        >
          <div className="flex flex-col h-full">
            {/* Logo */}
            <div className="p-6 border-b border-gray-700">
              <div className="flex items-center space-x-3">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-gray-700 via-gray-600 to-gray-800 flex items-center justify-center shadow-lg transform rotate-[-2deg]">
                  <span className="text-white font-bold text-xl">C</span>
                </div>
                {isSidebarOpen && <span className="font-bold text-xl text-white">Complytics</span>}
              </div>
            </div>

            {/* Navigation Items */}
            <nav className="flex-1 p-4 space-y-2">
              {sidebarItems.map((item) => (
                <motion.button
                  key={item.id}
                  whileHover={{ scale: 1.02, x: 4 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={item.onClick}
                  className={`w-full flex items-center space-x-3 p-3 rounded-xl transition-all duration-300 font-semibold ${
                    activeTab === item.id
                      ? 'bg-gradient-to-r from-gray-700 to-gray-600 text-white shadow-lg shadow-gray-700/50'
                      : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                  }`}
                >
                  <span className="text-lg">{item.icon}</span>
                  {isSidebarOpen && <span>{item.label}</span>}
                </motion.button>
              ))}
            </nav>

            {/* Logout Button */}
            <div className="p-4 border-t border-gray-700">
              <motion.button
                whileHover={{ scale: 1.02, x: 4 }}
                whileTap={{ scale: 0.98 }}
                onClick={handleLogout}
                className="w-full flex items-center space-x-3 p-3 rounded-xl text-red-400 hover:bg-red-900/30 hover:text-red-300 transition-all duration-300 font-semibold"
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
            className="flex justify-between items-start mb-10"
          >
            <div>
              <h1 className="text-5xl md:text-6xl font-bold bg-gradient-to-r from-blue-600 via-blue-500 to-blue-700 bg-clip-text text-transparent mb-3">
                Superadmin Dashboard
              </h1>
              <p className="text-gray-600 text-lg font-medium">
                Manage organizations and user registrations
              </p>
            </div>
              <Button
                onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                variant="outline"
                className="lg:hidden border-2 border-gray-300 hover:bg-blue-600 hover:text-white hover:border-blue-600"
              >
                {isSidebarOpen ? 'Close Sidebar' : 'Open Sidebar'}
              </Button>
          </motion.div>

          {/* Stats cards */}
          <motion.div 
            className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8"
            initial="hidden"
            animate="show"
            variants={containerVariants}
          >
            {/* Pending Requests Card */}
            <motion.div 
              variants={itemVariants}
              className="bg-gradient-to-br from-white to-blue-50/50 p-8 rounded-2xl shadow-xl hover:shadow-2xl transition-all duration-300 relative overflow-hidden group"
              whileHover={{ scale: 1.03, y: -5 }}
            >
              <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/10 rounded-full blur-2xl -mr-16 -mt-16 group-hover:bg-blue-500/20 transition-all"></div>
              <div className="relative z-10 flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold text-gray-500 mb-2 uppercase tracking-wide">Pending Requests</p>
                  <h3 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-blue-500 bg-clip-text text-transparent">{requests.length}</h3>
                </div>
                <div className="p-5 rounded-2xl bg-gradient-to-br from-blue-600 to-blue-500 text-white shadow-lg shadow-blue-500/30 group-hover:scale-110 transition-transform">
                  <FaUserPlus className="h-7 w-7" />
                </div>
              </div>
            </motion.div>

            {/* Active Organizations Card */}
            <motion.div 
              variants={itemVariants}
              className="bg-gradient-to-br from-white to-green-50/50 p-8 rounded-2xl shadow-xl hover:shadow-2xl transition-all duration-300 relative overflow-hidden group"
              whileHover={{ scale: 1.03, y: -5 }}
            >
              <div className="absolute top-0 right-0 w-32 h-32 bg-green-500/10 rounded-full blur-2xl -mr-16 -mt-16 group-hover:bg-green-500/20 transition-all"></div>
              <div className="relative z-10 flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold text-gray-500 mb-2 uppercase tracking-wide">Active Organizations</p>
                  <h3 className="text-4xl font-bold bg-gradient-to-r from-green-600 to-green-500 bg-clip-text text-transparent">{organizations.length}</h3>
                </div>
                <div className="p-5 rounded-2xl bg-gradient-to-br from-green-600 to-green-500 text-white shadow-lg shadow-green-500/30 group-hover:scale-110 transition-transform">
                  <FaBuilding className="h-7 w-7" />
                </div>
              </div>
            </motion.div>

            {/* Active Users Card */}
            <motion.div 
              variants={itemVariants}
              className="bg-gradient-to-br from-white to-purple-50/50 p-8 rounded-2xl shadow-xl hover:shadow-2xl transition-all duration-300 relative overflow-hidden group"
              whileHover={{ scale: 1.03, y: -5 }}
            >
              <div className="absolute top-0 right-0 w-32 h-32 bg-purple-500/10 rounded-full blur-2xl -mr-16 -mt-16 group-hover:bg-purple-500/20 transition-all"></div>
              <div className="relative z-10 flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold text-gray-500 mb-2 uppercase tracking-wide">Active Users</p>
                  <h3 className="text-4xl font-bold bg-gradient-to-r from-purple-600 to-purple-500 bg-clip-text text-transparent">{activeUsers.length}</h3>
                </div>
                <div className="p-5 rounded-2xl bg-gradient-to-br from-purple-600 to-purple-500 text-white shadow-lg shadow-purple-500/30 group-hover:scale-110 transition-transform">
                  <FaUsers className="h-7 w-7" />
                </div>
              </div>
            </motion.div>

            {/* Framework Documents Card */}
            <motion.div 
              variants={itemVariants}
              className="bg-gradient-to-br from-white to-orange-50/50 p-8 rounded-2xl shadow-xl hover:shadow-2xl transition-all duration-300 relative overflow-hidden group"
              whileHover={{ scale: 1.03, y: -5 }}
            >
              <div className="absolute top-0 right-0 w-32 h-32 bg-orange-500/10 rounded-full blur-2xl -mr-16 -mt-16 group-hover:bg-orange-500/20 transition-all"></div>
              <div className="relative z-10 flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold text-gray-500 mb-2 uppercase tracking-wide">Framework Documents</p>
                  <h3 className="text-4xl font-bold bg-gradient-to-r from-orange-600 to-orange-500 bg-clip-text text-transparent">{frameworks.length}</h3>
                </div>
                <div className="p-5 rounded-2xl bg-gradient-to-br from-orange-600 to-orange-500 text-white shadow-lg shadow-orange-500/30 group-hover:scale-110 transition-transform">
                  <FaCog className="h-7 w-7" />
                </div>
              </div>
            </motion.div>
          </motion.div>

          {/* Inline success/error containers removed; toast notifications are used instead */}

          {/* Tabs */}
          <div className="flex flex-wrap gap-3 mb-8 bg-white/60 backdrop-blur-sm p-2 rounded-2xl shadow-lg">
            <button
              className={`px-6 py-3 font-bold rounded-xl transition-all duration-300 ${
                activeTab === 'registrations' 
                  ? 'bg-gradient-to-r from-blue-600 to-blue-500 text-white shadow-lg shadow-blue-500/30' 
                  : 'text-gray-600 hover:bg-blue-50 hover:text-blue-600'
              }`}
              onClick={() => setActiveTab('registrations')}
            >
              Pending Registrations
            </button>
            <button
              className={`px-6 py-3 font-bold rounded-xl transition-all duration-300 ${
                activeTab === 'organizations' 
                  ? 'bg-gradient-to-r from-blue-600 to-blue-500 text-white shadow-lg shadow-blue-500/30' 
                  : 'text-gray-600 hover:bg-blue-50 hover:text-blue-600'
              }`}
              onClick={() => setActiveTab('organizations')}
            >
              Active Organizations
            </button>
            <button
              className={`px-6 py-3 font-bold rounded-xl transition-all duration-300 ${
                activeTab === 'users' 
                  ? 'bg-gradient-to-r from-blue-600 to-blue-500 text-white shadow-lg shadow-blue-500/30' 
                  : 'text-gray-600 hover:bg-blue-50 hover:text-blue-600'
              }`}
              onClick={() => setActiveTab('users')}
            >
              Active Users
            </button>
            <button
              className={`px-6 py-3 font-bold rounded-xl transition-all duration-300 ${
                activeTab === 'deletions' 
                  ? 'bg-gradient-to-r from-blue-600 to-blue-500 text-white shadow-lg shadow-blue-500/30' 
                  : 'text-gray-600 hover:bg-blue-50 hover:text-blue-600'
              }`}
              onClick={() => setActiveTab('deletions')}
            >
              Deletion Requests
            </button>
            <button
              className={`px-6 py-3 font-bold rounded-xl transition-all duration-300 ${
                activeTab === 'frameworks' 
                  ? 'bg-gradient-to-r from-blue-600 to-blue-500 text-white shadow-lg shadow-blue-500/30' 
                  : 'text-gray-600 hover:bg-blue-50 hover:text-blue-600'
              }`}
              onClick={() => setActiveTab('frameworks')}
            >
              Frameworks
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
              <motion.div variants={itemVariants} className="bg-white/80 backdrop-blur-sm p-12 text-center rounded-2xl shadow-xl">
                <div className="mx-auto flex items-center justify-center w-20 h-20 bg-gradient-to-br from-blue-100 to-blue-200 rounded-2xl mb-6 shadow-lg">
                  <FaUserTie className="h-10 w-10 text-blue-600" />
                </div>
                <h3 className="text-2xl font-bold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent">No pending requests</h3>
                <p className="text-gray-600 mt-3 text-lg">All registration requests have been processed</p>
              </motion.div>
            ) : (
              <motion.div initial="hidden" animate="show" variants={containerVariants} className="grid gap-6">
                <AnimatePresence>
                  {requests.map((request) => (
                    <motion.div
                      key={request._id}
                      variants={itemVariants}
                      whileHover={{ y: -5, scale: 1.01 }}
                      className="bg-white/80 backdrop-blur-sm p-6 rounded-2xl shadow-lg hover:shadow-2xl transition-all duration-300 group relative overflow-hidden"
                    >
                      <div className="absolute inset-0 bg-gradient-to-r from-blue-500/0 via-blue-500/0 to-blue-500/0 group-hover:from-blue-500/5 group-hover:via-blue-500/5 group-hover:to-blue-500/5 transition-all duration-300"></div>
                      <div className="relative z-10">
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div className="flex items-start space-x-4">
                          <div className="flex-shrink-0">
                            <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center text-primary">
                              <FaUserTie className="h-5 w-5" />
                            </div>
                          </div>
                          <div>
                            <h3 className="font-bold text-lg text-black">
                              {request.user_data?.organization_name || 'No organization name'}
                            </h3>
                            <div className="flex items-center text-sm text-gray-600 mt-1">
                              <FaEnvelope className="mr-2" />
                              {request.user_data?.email || 'No email'}
                            </div>
                            <div className="flex items-center text-sm text-gray-600 mt-1">
                              <FaUserTie className="mr-2" />
                              {request.user_data?.first_name} {request.user_data?.last_name}
                            </div>
                          </div>
                        </div>

                        <div className="space-y-2">
                          <div className="flex items-center text-sm">
                            <span className="font-bold text-black">Submitted:</span>
                            <span className="ml-1 text-gray-700">
                              {request.created_at ? 
                                new Date(request.created_at).toLocaleDateString() : 
                                'Unknown date'}
                            </span>
                          </div>
                          <div className="flex items-center text-sm">
                            <span className="font-bold text-black">Domain:</span>
                            <span className="ml-1 text-gray-700">
                              {request.user_data?.organization_domain || 'No domain'}
                            </span>
                          </div>
                        </div>

                        <div className="flex justify-end items-center space-x-2">
                          <Button 
                            variant="default" 
                            size="sm" 
                            onClick={() => openApproveDialog(request)}
                            className="flex items-center gap-2 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-700 hover:to-blue-600 text-white font-semibold shadow-lg shadow-blue-500/30 rounded-xl px-5 py-2.5 transition-all hover:scale-105"
                            disabled={approvingId === request._id}
                          >
                            {approvingId === request._id ? (
                              <FaSpinner className="animate-spin" />
                            ) : (
                              <FaCheckCircle />
                            )}
                            Approve
                          </Button>
                          <Button 
                            variant="destructive" 
                            size="sm" 
                            onClick={() => openRejectDialog(request)}
                            className="flex items-center gap-2 bg-gradient-to-r from-red-600 to-red-500 hover:from-red-700 hover:to-red-600 text-white font-semibold shadow-lg shadow-red-500/30 rounded-xl px-5 py-2.5 transition-all hover:scale-105"
                            disabled={rejectingId === request._id}
                          >
                            {rejectingId === request._id ? (
                              <FaSpinner className="animate-spin" />
                            ) : (
                              <FaTimesCircle />
                            )}
                            Reject
                          </Button>
                        </div>
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
              <motion.div variants={itemVariants} className="bg-white/80 backdrop-blur-sm p-12 text-center rounded-2xl shadow-xl">
                <div className="mx-auto flex items-center justify-center w-20 h-20 bg-gradient-to-br from-green-100 to-green-200 rounded-2xl mb-6 shadow-lg">
                  <FaBuilding className="h-10 w-10 text-green-600" />
                </div>
                <h3 className="text-2xl font-bold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent">No active organizations</h3>
                <p className="text-gray-600 mt-3 text-lg">Approved organizations will appear here</p>
              </motion.div>
            ) : (
              <motion.div initial="hidden" animate="show" variants={containerVariants} className="grid gap-6">
                {organizations.map((org) => (
                  <motion.div
                    key={org._id}
                    variants={itemVariants}
                    whileHover={{ y: -5, scale: 1.01 }}
                    className="bg-white/80 backdrop-blur-sm p-6 rounded-2xl shadow-lg hover:shadow-2xl transition-all duration-300 group relative overflow-hidden"
                  >
                    <div className="absolute inset-0 bg-gradient-to-r from-green-500/0 via-green-500/0 to-green-500/0 group-hover:from-green-500/5 group-hover:via-green-500/5 group-hover:to-green-500/5 transition-all duration-300"></div>
                    <div className="relative z-10">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                      <div className="flex items-start space-x-4">
                        <div className="flex-shrink-0">
                          <div className="h-12 w-12 rounded-full bg-blue-500/10 flex items-center justify-center text-blue-500">
                            <FaBuilding className="h-5 w-5" />
                          </div>
                        </div>
                        <div>
                          <h3 className="font-bold text-lg text-black">{org.name}</h3>
                          <div className="flex items-center text-sm text-gray-600 mt-1">
                            <FaGlobe className="mr-2" />
                            {org.domain}
                          </div>
                        </div>
                      </div>

                      <div className="space-y-2">
                          <div className="flex items-center text-sm">
                            <span className="font-bold text-black">Status:</span>
                            <span className={`ml-2 px-3 py-1 text-xs rounded-full font-semibold ${org.is_active ? 'bg-green-100 text-green-800 border-2 border-green-500' : 'bg-red-100 text-red-800 border-2 border-red-500'}`}>
                              {org.is_active ? 'Active' : 'Inactive'}
                            </span>
                          </div>
                          <div className="flex items-center text-sm">
                            <span className="font-bold text-black">Created:</span>
                            <span className="ml-1 text-gray-700">
                              {new Date(org.created_at).toLocaleDateString()}
                            </span>
                          </div>
                      </div>
                    </div>
                    </div>
                  </motion.div>
                ))}
              </motion.div>
            )
          ) : activeTab === 'users' ? (
            /* Active Users Tab */
            usersLoading ? (
              <motion.div className="grid gap-6" initial="hidden" animate="show" variants={containerVariants}>
                {[1, 2, 3].map((i) => <UserSkeleton key={i} />)}
              </motion.div>
            ) : activeUsers.length === 0 ? (
              <motion.div variants={itemVariants} className="bg-white/80 backdrop-blur-sm p-12 text-center rounded-2xl shadow-xl">
                <div className="mx-auto flex items-center justify-center w-20 h-20 bg-gradient-to-br from-purple-100 to-purple-200 rounded-2xl mb-6 shadow-lg">
                  <FaUserCheck className="h-10 w-10 text-purple-600" />
                </div>
                <h3 className="text-2xl font-bold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent">No active users</h3>
                <p className="text-gray-600 mt-3 text-lg">All users are currently inactive</p>
              </motion.div>
            ) : (
              <motion.div initial="hidden" animate="show" variants={containerVariants} className="grid gap-6">
                {activeUsers.map((user) => (
                  <motion.div
                    key={user._id}
                    variants={itemVariants}
                    whileHover={{ y: -5, scale: 1.01 }}
                    className="bg-white/80 backdrop-blur-sm p-6 rounded-2xl shadow-lg hover:shadow-2xl transition-all duration-300 group relative overflow-hidden"
                  >
                    <div className="absolute inset-0 bg-gradient-to-r from-purple-500/0 via-purple-500/0 to-purple-500/0 group-hover:from-purple-500/5 group-hover:via-purple-500/5 group-hover:to-purple-500/5 transition-all duration-300"></div>
                    <div className="relative z-10">
                    <div className="flex flex-col gap-4">
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div className="flex items-start space-x-4">
                          <div className="flex-shrink-0">
                            <div className="h-12 w-12 rounded-full bg-blue-500/10 flex items-center justify-center text-blue-500">
                              <FaUserCheck className="h-5 w-5" />
                            </div>
                          </div>
                          <div>
                            <h3 className="font-bold text-lg text-black">
                              {user.first_name} {user.last_name}
                            </h3>
                            <div className="flex items-center text-sm text-gray-600 mt-1">
                              <FaEnvelope className="mr-2" />
                              {user.email}
                            </div>
                          </div>
                        </div>

                        <div className="space-y-2">
                          <div className="flex items-center text-sm">
                            <span className="font-bold text-black">Role:</span>
                            <span className="ml-1 capitalize text-gray-700">{user.role}</span>
                          </div>
                          <div className="flex items-center text-sm">
                            <span className="font-bold text-black">Status:</span>
                            <span className={`ml-2 px-3 py-1 text-xs rounded-full font-semibold ${
                              user.is_active ? 'bg-green-100 text-green-800 border-2 border-green-500' : 'bg-red-100 text-red-800 border-2 border-red-500'
                            }`}>
                              {user.is_active ? 'Active' : 'Inactive'}
                            </span>
                          </div>
                        </div>

                        <div className="space-y-2">
                          <div className="flex items-center text-sm">
                            <span className="font-bold text-black">Organization:</span>
                            <span className="ml-1 text-gray-700">
                              {getOrganizationName(user.organization_id)}
                            </span>
                          </div>
                          <div className="flex items-center text-sm">
                            <span className="font-bold text-black">Joined:</span>
                            <span className="ml-1 text-gray-700">
                              {new Date(user.created_at).toLocaleDateString()}
                            </span>
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex justify-end pt-2 border-t-2 border-black">
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => {
                            setSelectedUser(user);
                            setShowDeleteUserDialog(true);
                          }}
                          disabled={deletingUserId === user._id}
                          className="flex items-center gap-2 bg-gradient-to-r from-red-600 to-red-500 hover:from-red-700 hover:to-red-600 text-white font-semibold shadow-lg shadow-red-500/30 rounded-xl px-5 py-2.5 transition-all hover:scale-105"
                        >
                          {deletingUserId === user._id ? (
                            <>
                              <FaSpinner className="animate-spin" />
                              Deleting...
                            </>
                          ) : (
                            <>
                              <FaTrash />
                              Delete User
                            </>
                          )}
                        </Button>
                      </div>
                    </div>
                    </div>
                  </motion.div>
                ))}
              </motion.div>
            )
          ) : activeTab === 'deletions' ? (
            <motion.div initial="hidden" animate="show" variants={containerVariants} className="grid gap-6">
              {deletionRequests.length === 0 ? (
                <motion.div variants={itemVariants} className="bg-white/80 backdrop-blur-sm p-12 text-center rounded-2xl shadow-xl">
                  <div className="mx-auto flex items-center justify-center w-20 h-20 bg-gradient-to-br from-red-100 to-red-200 rounded-2xl mb-6 shadow-lg">
                    <FaTimesCircle className="h-10 w-10 text-red-600" />
                  </div>
                  <h3 className="text-2xl font-bold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent">No deletion requests</h3>
                  <p className="text-gray-600 mt-3 text-lg">New requests will appear here</p>
                </motion.div>
              ) : (
                deletionRequests.map((req) => (
                  <motion.div key={req._id} variants={itemVariants} whileHover={{ y: -5, scale: 1.01 }} className="bg-white/80 backdrop-blur-sm p-6 rounded-2xl shadow-lg hover:shadow-2xl transition-all duration-300 group relative overflow-hidden">
                    <div className="absolute inset-0 bg-gradient-to-r from-red-500/0 via-red-500/0 to-red-500/0 group-hover:from-red-500/5 group-hover:via-red-500/5 group-hover:to-red-500/5 transition-all duration-300"></div>
                    <div className="relative z-10">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                      <div>
                        <h3 className="font-bold text-lg text-black">Requester</h3>
                        <div className="text-sm text-gray-600">User ID: {req.requester_user_id}</div>
                        <div className="text-sm text-gray-600">Org ID: {req.organization_id || 'N/A'}</div>
                      </div>
                      <div>
                        <div className="text-sm"><span className="font-bold text-black">Status:</span> <span className="text-gray-700">{req.status}</span></div>
                        <div className="text-sm"><span className="font-bold text-black">Reason:</span> <span className="text-gray-700">{req.reason || 'None'}</span></div>
                        <div className="text-sm"><span className="font-bold text-black">Requested:</span> <span className="text-gray-700">{req.created_at ? new Date(req.created_at).toLocaleString() : ''}</span></div>
                      </div>
                      <div className="flex items-center justify-end gap-2">
                        {req.status === 'pending' && (
                          <>
                            <Button 
                              variant="default" 
                              size="sm"
                              onClick={() => { setSelectedRequest(req); setShowApproveDeletionDialog(true); }}
                              className="flex items-center gap-2 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-700 hover:to-blue-600 text-white font-semibold shadow-lg shadow-blue-500/30 rounded-xl px-5 py-2.5 transition-all hover:scale-105"
                              disabled={approvingId === req._id}
                            >
                              {approvingId === req._id ? <FaSpinner className="animate-spin" /> : null}
                              Approve
                            </Button>
                            <Button 
                              variant="destructive" 
                              size="sm"
                              onClick={() => { setSelectedRequest(req); setShowRejectDeletionDialog(true); }}
                              className="flex items-center gap-2 bg-gradient-to-r from-red-600 to-red-500 hover:from-red-700 hover:to-red-600 text-white font-semibold shadow-lg shadow-red-500/30 rounded-xl px-5 py-2.5 transition-all hover:scale-105"
                              disabled={rejectingId === req._id}
                            >
                              {rejectingId === req._id ? <FaSpinner className="animate-spin" /> : null}
                              Reject
                            </Button>
                          </>
                        )}
                      </div>
                    </div>
                    </div>
                  </motion.div>
                ))
              )}
            </motion.div>
          ) : (
            /* Frameworks Tab */
            <motion.div initial="hidden" animate="show" variants={containerVariants} className="space-y-6">
              <div className="bg-white/80 backdrop-blur-sm p-8 rounded-2xl shadow-xl">
                <h2 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-blue-500 bg-clip-text text-transparent mb-4">Framework Document Management</h2>
                <p className="text-gray-600 mb-6 text-lg">
                  Upload new compliance framework documents to be processed and indexed by the RAG system.
                </p>

                <div className="space-y-4">
                  <div className="flex items-center space-x-4">
                    <input
                      type="file"
                      accept=".pdf,.docx"
                      onChange={handleFrameworkUpload}
                      className="hidden"
                      id="framework-upload"
                      disabled={uploadingFramework}
                      multiple
                    />
                    <label
                      htmlFor="framework-upload"
                      className={`flex items-center space-x-2 px-6 py-3 rounded-xl cursor-pointer font-semibold shadow-lg transition-all duration-300 ${
                        uploadingFramework
                          ? 'bg-gray-300 cursor-not-allowed text-gray-600'
                          : 'bg-gradient-to-r from-blue-600 to-blue-500 text-white hover:from-blue-700 hover:to-blue-600 hover:scale-105 shadow-blue-500/30'
                      }`}
                    >
                      {uploadingFramework ? (
                        <FaSpinner className="animate-spin" />
                      ) : (
                        <FaCog />
                      )}
                      <span>{uploadingFramework ? 'Uploading...' : 'Upload Framework Documents'}</span>
                    </label>
                  </div>

                  {frameworkUploadSuccess && (
                    <div className="p-4 bg-gradient-to-r from-green-50 to-green-100 border-l-4 border-green-500 text-green-700 rounded-xl font-semibold shadow-lg">
                      {frameworkUploadSuccess}
                    </div>
                  )}

                  {frameworkUploadError && (
                    <div className="p-4 bg-gradient-to-r from-red-50 to-red-100 border-l-4 border-red-500 text-red-700 rounded-xl font-semibold shadow-lg">
                      {frameworkUploadError}
                    </div>
                  )}
                </div>
              </div>

              {frameworksLoading ? (
                <motion.div className="grid gap-6" initial="hidden" animate="show" variants={containerVariants}>
                  {[1, 2, 3].map((i) => (
                    <motion.div key={i} className="glass-card p-6 rounded-lg space-y-4" variants={itemVariants}>
                      <div className="flex items-center space-x-4">
                        <div className="h-12 w-12 bg-muted rounded-full animate-pulse"></div>
                        <div className="flex-1 space-y-2">
                          <div className="h-4 bg-muted rounded w-3/4 animate-pulse"></div>
                          <div className="h-3 bg-muted rounded w-1/2 animate-pulse"></div>
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </motion.div>
              ) : frameworks.length === 0 ? (
                <motion.div variants={itemVariants} className="bg-white/80 backdrop-blur-sm p-12 text-center rounded-2xl shadow-xl">
                  <div className="mx-auto flex items-center justify-center w-20 h-20 bg-gradient-to-br from-orange-100 to-orange-200 rounded-2xl mb-6 shadow-lg">
                    <FaCog className="h-10 w-10 text-orange-600" />
                  </div>
                  <h3 className="text-2xl font-bold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent">No framework documents</h3>
                  <p className="text-gray-600 mt-3 text-lg">Upload framework documents to get started</p>
                </motion.div>
              ) : (
                <div className="grid gap-6">
                  {frameworks.map((framework) => (
                    <motion.div
                      key={framework.id}
                      variants={itemVariants}
                      whileHover={{ y: -5, scale: 1.01 }}
                      className="bg-white/80 backdrop-blur-sm p-6 rounded-2xl shadow-lg hover:shadow-2xl transition-all duration-300 group relative overflow-hidden"
                    >
                      <div className="absolute inset-0 bg-gradient-to-r from-orange-500/0 via-orange-500/0 to-orange-500/0 group-hover:from-orange-500/5 group-hover:via-orange-500/5 group-hover:to-orange-500/5 transition-all duration-300"></div>
                      <div className="relative z-10">
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div className="flex items-start space-x-4">
                          <div className="flex-shrink-0">
                            <div className="h-12 w-12 rounded-full bg-purple-500/10 flex items-center justify-center text-purple-500">
                              <FaCog className="h-5 w-5" />
                            </div>
                          </div>
                          <div>
                            <h3 className="font-bold text-lg text-black">{framework.filename}</h3>
                            <div className="flex items-center text-sm text-gray-600 mt-1">
                              <span className="capitalize">{framework.file_type}</span>
                            </div>
                          </div>
                        </div>

                        <div className="space-y-2">
                          <div className="flex items-center text-sm">
                            <span className="font-bold text-black">Status:</span>
                            <span className={`ml-2 px-3 py-1 text-xs rounded-full font-semibold ${
                              framework.status === 'processed' ? 'bg-green-100 text-green-800 border-2 border-green-500' : 'bg-yellow-100 text-yellow-800 border-2 border-yellow-500'
                            }`}>
                              {framework.status}
                            </span>
                          </div>
                          <div className="flex items-center text-sm">
                            <span className="font-bold text-black">Uploaded:</span>
                            <span className="ml-1 text-gray-700">
                              {new Date(framework.upload_date).toLocaleDateString()}
                            </span>
                          </div>
                        </div>

                        <div className="space-y-2">
                          <div className="flex items-center text-sm">
                            <span className="font-bold text-black">Segments:</span>
                            <span className="ml-1 text-gray-700">{framework.segments_count}</span>
                          </div>
                          <div className="flex items-center text-sm">
                            <span className="font-bold text-black">Embeddings:</span>
                            <span className="ml-1 text-gray-700">{framework.embeddings_count}</span>
                          </div>
                          <div className="flex items-center text-sm">
                            <span className="font-bold text-black">Index Vectors:</span>
                            <span className="ml-1 text-gray-700">{framework.index_vectors}</span>
                          </div>
                        </div>
                      </div>
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </motion.div>
          )}
        </div>
        </div>
      </div>

      <AlertDialog open={showApproveDialog} onOpenChange={setShowApproveDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirm Approval</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to approve the registration request for {selectedRequest?.user_data?.organization_name}?
              This will create a new organization and admin account.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={() => handleApprove(selectedRequest?._id)} className="flex items-center gap-2">
              {approvingId === selectedRequest?._id ? <FaSpinner className="animate-spin" /> : null}
              Approve
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={showRejectDialog} onOpenChange={setShowRejectDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirm Rejection</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to reject the registration request for {selectedRequest?.user_data?.organization_name}?
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={() => handleReject(selectedRequest?._id)} className="flex items-center gap-2">
              {rejectingId === selectedRequest?._id ? <FaSpinner className="animate-spin" /> : null}
              Reject
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Deletion requests confirm dialogs */}
      <AlertDialog open={showApproveDeletionDialog} onOpenChange={setShowApproveDeletionDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Approve Deletion Request</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete the admin account and related data for the requester. Continue?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={() => handleApproveDeletion(selectedRequest?._id)} className="flex items-center gap-2">
              {approvingId === selectedRequest?._id ? <FaSpinner className="animate-spin" /> : null}
              Approve
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={showRejectDeletionDialog} onOpenChange={setShowRejectDeletionDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Reject Deletion Request</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to reject this account deletion request?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={() => handleRejectDeletion(selectedRequest?._id)} className="flex items-center gap-2">
              {rejectingId === selectedRequest?._id ? <FaSpinner className="animate-spin" /> : null}
              Reject
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Delete User Confirmation Dialog */}
      <AlertDialog open={showDeleteUserDialog} onOpenChange={setShowDeleteUserDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete User</AlertDialogTitle>
            <AlertDialogDescription>
              <div className="space-y-2">
                <p>
                  Are you sure you want to delete <strong>{selectedUser?.first_name} {selectedUser?.last_name}</strong> ({selectedUser?.email})?
                </p>
                {selectedUser?.organization_id && (
                  <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-md">
                    <p className="text-sm font-semibold text-red-800 mb-1">⚠️ Warning: This will also delete:</p>
                    <ul className="text-sm text-red-700 list-disc list-inside space-y-1">
                      <li>The entire organization and all its data</li>
                      <li>All users in this organization</li>
                      <li>All compliance chat history</li>
                      <li>All UI testing results</li>
                      <li>All Azure connections and logs</li>
                    </ul>
                    <p className="text-sm font-semibold text-red-800 mt-2">This action cannot be undone!</p>
                  </div>
                )}
                {!selectedUser?.organization_id && (
                  <p className="text-sm text-muted-foreground">
                    This will delete the user and all their personal data. This action cannot be undone.
                  </p>
                )}
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction 
              onClick={handleDeleteUser} 
              className="flex items-center gap-2 bg-red-600 hover:bg-red-700"
            >
              {deletingUserId === selectedUser?._id ? (
                <>
                  <FaSpinner className="animate-spin" />
                  Deleting...
                </>
              ) : (
                <>
                  <FaTrash />
                  Delete User
                </>
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
};

export default SuperadminDashboard;