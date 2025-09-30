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
  FaUser,
  FaShieldAlt,
  FaCog,
  FaQuestionCircle,
  FaClock,
  FaChartBar,
  FaCheckCircle,
  FaServer,
  FaExclamationTriangle,
  FaCheck,
  FaBell,
  FaHistory,
  FaTasks,
  FaInfo,
  FaEye,
  FaEyeSlash,
  FaKey,
  FaBuilding,
  FaIdCard,
  FaSave,
  FaSpinner,
  FaLock,
  FaUsers,
  FaGlobe,
  FaClipboardList
} from 'react-icons/fa';
import Profile from '../auth/Profile';
import ComplianceChat from './ComplianceChat';
import UiTesting from './UiTesting';

const ChatbotAnalytics = () => {
  const { authToken } = useAuth();
  const [analytics, setAnalytics] = useState({
    totalQueries: 0,
    averageResponseTime: 0,
    mostCommonTopics: [],
    successRate: 0
  });
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        if (!authToken) {
          throw new Error('No authentication token found');
        }

        const response = await fetch('http://localhost:8000/api/compliance/analytics', {
          headers: {
            'Authorization': `Bearer ${authToken}`
          }
        });

        if (!response.ok) {
          throw new Error('Failed to fetch analytics');
        }

        const data = await response.json();
        setAnalytics(data);
        setError(null);
      } catch (error) {
        console.error('Error fetching chatbot analytics:', error);
        setError(error.message);
        // Set default values in case of error
        setAnalytics({
          totalQueries: 0,
          averageResponseTime: 0,
          mostCommonTopics: [],
          successRate: 0
        });
      }
    };

    fetchAnalytics();
  }, [authToken]);

  if (error) {
    return (
      <div className="p-4 bg-destructive/10 rounded-xl">
        <p className="text-destructive text-sm">Failed to load analytics: {error}</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <motion.div
        whileHover={{ scale: 1.02 }}
        className="p-4 bg-card rounded-xl shadow-lg"
      >
        <div className="flex items-center space-x-3">
          <FaQuestionCircle className="text-2xl text-primary" />
          <div>
            <h4 className="text-sm font-medium text-muted-foreground">Total Queries</h4>
            <p className="text-2xl font-bold">{analytics.totalQueries}</p>
          </div>
        </div>
      </motion.div>

      <motion.div
        whileHover={{ scale: 1.02 }}
        className="p-4 bg-card rounded-xl shadow-lg"
      >
        <div className="flex items-center space-x-3">
          <FaClock className="text-2xl text-primary" />
          <div>
            <h4 className="text-sm font-medium text-muted-foreground">Avg Response Time</h4>
            <p className="text-2xl font-bold">{analytics.averageResponseTime}s</p>
          </div>
        </div>
      </motion.div>

      <motion.div
        whileHover={{ scale: 1.02 }}
        className="p-4 bg-card rounded-xl shadow-lg"
      >
        <div className="flex items-center space-x-3">
          <FaChartBar className="text-2xl text-primary" />
          <div>
            <h4 className="text-sm font-medium text-muted-foreground">Success Rate</h4>
            <p className="text-2xl font-bold">{analytics.successRate}%</p>
          </div>
        </div>
      </motion.div>

      <motion.div
        whileHover={{ scale: 1.02 }}
        className="p-4 bg-card rounded-xl shadow-lg"
      >
        <div className="flex items-center space-x-3">
          <FaCheckCircle className="text-2xl text-primary" />
          <div>
            <h4 className="text-sm font-medium text-muted-foreground">Top Topics</h4>
            <p className="text-sm font-medium">
              {analytics.mostCommonTopics?.slice(0, 2).join(', ') || 'No topics yet'}
            </p>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

const SystemStatus = () => {
  const [status, setStatus] = useState({
    systemHealth: 'healthy',
    lastScan: '2024-03-20 14:30',
    activeUsers: 12,
    complianceScore: 85
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <FaServer className="text-primary" />
          <span className="font-medium">System Health</span>
        </div>
        <span className={`px-2 py-1 rounded-full text-xs ${
          status.systemHealth === 'healthy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
        }`}>
          {status.systemHealth === 'healthy' ? 'Healthy' : 'Needs Attention'}
        </span>
      </div>
      
      <div className="space-y-2">
        <div className="flex justify-between items-center">
          <span className="text-sm text-muted-foreground">Last Compliance Scan</span>
          <span className="text-sm font-medium">{status.lastScan}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-muted-foreground">Active Users</span>
          <span className="text-sm font-medium">{status.activeUsers}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-muted-foreground">Compliance Score</span>
          <span className="text-sm font-medium">{status.complianceScore}%</span>
        </div>
      </div>
    </div>
  );
};

const RecentActivities = () => {
  const [activities, setActivities] = useState([
    { type: 'scan', message: 'Compliance scan completed', time: '2 hours ago' },
    { type: 'chat', message: 'New compliance query resolved', time: '3 hours ago' },
    { type: 'update', message: 'System update completed', time: '5 hours ago' }
  ]);

  return (
    <div className="space-y-4">
      <div className="flex items-center space-x-2 mb-2">
        <FaHistory className="text-primary" />
        <span className="font-medium">Recent Activities</span>
      </div>
      
      <div className="space-y-3">
        {activities.map((activity, index) => (
          <div key={index} className="flex items-start space-x-3">
            <div className={`mt-1 w-2 h-2 rounded-full ${
              activity.type === 'scan' ? 'bg-blue-500' :
              activity.type === 'chat' ? 'bg-green-500' :
              'bg-purple-500'
            }`} />
            <div className="flex-1">
              <p className="text-sm">{activity.message}</p>
              <p className="text-xs text-muted-foreground">{activity.time}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const Notifications = () => {
  const [notifications, setNotifications] = useState([
    { type: 'warning', message: 'Compliance scan due in 2 days', time: '1 hour ago' },
    { type: 'info', message: 'New compliance guidelines available', time: '3 hours ago' },
    { type: 'success', message: 'System backup completed', time: '5 hours ago' }
  ]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <FaBell className="text-primary" />
          <span className="font-medium">Notifications</span>
        </div>
        <span className="text-xs text-muted-foreground">{notifications.length} new</span>
      </div>
      
      <div className="space-y-3">
        {notifications.map((notification, index) => (
          <div key={index} className="flex items-start space-x-3 p-2 rounded-lg hover:bg-secondary/50">
            <div className={`mt-1 ${
              notification.type === 'warning' ? 'text-yellow-500' :
              notification.type === 'info' ? 'text-blue-500' :
              'text-green-500'
            }`}>
              {notification.type === 'warning' ? <FaExclamationTriangle /> :
               notification.type === 'info' ? <FaInfo /> :
               <FaCheck />}
            </div>
            <div className="flex-1">
              <p className="text-sm">{notification.message}</p>
              <p className="text-xs text-muted-foreground">{notification.time}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const AzureConnectionMiniCard = () => {
  const { authToken } = useAuth();
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        setLoading(true);
        const response = await fetch('http://localhost:8000/api/azure/status', {
          headers: {
            'Authorization': `Bearer ${authToken}`
          }
        });
        if (response.ok) {
          const data = await response.json();
          setConnected(!!data.connected);
        } else {
          setConnected(false);
        }
      } catch (e) {
        setConnected(false);
      } finally {
        setLoading(false);
      }
    };
    if (authToken) {
      fetchStatus();
    }
  }, [authToken]);

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      className="p-4 bg-card rounded-xl shadow-lg flex items-center justify-between"
    >
      <div className="flex items-center space-x-3">
        <FaCloud className={connected ? 'text-green-600' : 'text-gray-500'} />
        <div>
          <div className="text-sm font-semibold">Azure AD</div>
          <div className="text-xs text-muted-foreground">
            {loading ? 'Checking connection…' : (connected ? 'Connected' : 'Not connected')}
          </div>
        </div>
      </div>
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${connected ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400' : 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400'}`}>
        {loading ? '…' : (connected ? 'Connected' : 'Not Connected')}
      </span>
    </motion.div>
  );
};

const AzureADConfiguration = () => {
  const { authToken } = useAuth();
  const [isConnected, setIsConnected] = useState(false);
  const [configData, setConfigData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchStatusAndConfig = async () => {
      try {
        setLoading(true);
        // First check connection status
        const statusResponse = await fetch('http://localhost:8000/api/azure/status', {
          headers: {
            'Authorization': `Bearer ${authToken}`
          }
        });
        
        if (statusResponse.ok) {
          const statusData = await statusResponse.json();
          setIsConnected(!!statusData.connected);
          
          if (statusData.connected) {
            // Fetch Azure AD configuration
            const configResponse = await fetch('http://localhost:8000/api/azure/config', {
              headers: {
                'Authorization': `Bearer ${authToken}`
              }
            });
            
            if (configResponse.ok) {
              const data = await configResponse.json();
              setConfigData(data);
            } else {
              setError('Failed to fetch Azure AD configuration');
            }
          }
        } else {
          setIsConnected(false);
        }
      } catch (e) {
        setError('Failed to check Azure AD status');
        setIsConnected(false);
      } finally {
        setLoading(false);
      }
    };
    
    if (authToken) {
      fetchStatusAndConfig();
    }
  }, [authToken]);

  const handleConnectClick = () => {
    // Dispatch event to switch to Azure tab
    window.dispatchEvent(new CustomEvent('setActiveTab', { detail: 'azure' }));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <FaSpinner className="animate-spin text-2xl text-primary" />
      </div>
    );
  }

  if (!isConnected) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="space-y-6"
      >
        <div className="flex items-center space-x-4 mb-6">
          <div className="p-3 bg-blue-100 dark:bg-blue-900/20 rounded-lg">
            <FaCloud className="text-2xl text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-foreground">Azure AD Configuration</h2>
            <p className="text-muted-foreground">View your Azure Active Directory settings</p>
          </div>
        </div>

        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-8 bg-card rounded-xl shadow-lg border border-border text-center"
        >
          <div className="flex flex-col items-center space-y-4">
            <FaCloud className="text-4xl text-muted-foreground" />
            <div>
              <h3 className="text-lg font-semibold mb-2">Not Connected to Azure AD</h3>
              <p className="text-muted-foreground mb-6">
                You need to connect to Azure AD first to view configuration settings.
              </p>
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={handleConnectClick}
                className="px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
              >
                Connect to Azure AD
              </motion.button>
            </div>
          </div>
        </motion.div>
      </motion.div>
    );
  }

  if (error) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="space-y-6"
      >
        <div className="flex items-center space-x-4 mb-6">
          <div className="p-3 bg-blue-100 dark:bg-blue-900/20 rounded-lg">
            <FaCloud className="text-2xl text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-foreground">Azure AD Configuration</h2>
            <p className="text-muted-foreground">View your Azure Active Directory settings</p>
          </div>
        </div>

        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-6 bg-destructive/10 border border-destructive/20 rounded-xl"
        >
          <div className="flex items-center space-x-2">
            <FaExclamationTriangle className="text-destructive" />
            <span className="text-destructive">{error}</span>
          </div>
        </motion.div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="space-y-6"
    >
      <div className="flex items-center space-x-4 mb-6">
        <div className="p-3 bg-blue-100 dark:bg-blue-900/20 rounded-lg">
          <FaCloud className="text-2xl text-blue-600 dark:text-blue-400" />
        </div>
        <div>
          <h2 className="text-2xl font-bold text-foreground">Azure AD Configuration</h2>
          <p className="text-muted-foreground">Current Azure Active Directory settings</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Conditional Access Policies */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-6 bg-card rounded-xl shadow-lg border border-border"
        >
          <div className="flex items-center space-x-3 mb-4">
            <FaShieldAlt className="text-xl text-primary" />
            <h3 className="text-lg font-semibold">Conditional Access Policies</h3>
          </div>
          <div className="space-y-3">
            {configData?.conditional_access_policies?.error ? (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <div className="text-sm text-destructive">{configData.conditional_access_policies.error}</div>
              </div>
            ) : configData?.conditional_access_policies?.value?.length > 0 ? (
              configData.conditional_access_policies.value.slice(0, 3).map((policy, index) => (
                <div key={index} className="p-3 bg-secondary/50 rounded-lg">
                  <div className="font-medium text-sm">{policy.displayName}</div>
                  <div className="text-xs text-muted-foreground">
                    State: {policy.state}
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted-foreground">No conditional access policies found</p>
            )}
          </div>
        </motion.div>

        {/* Authentication Methods */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-6 bg-card rounded-xl shadow-lg border border-border"
        >
          <div className="flex items-center space-x-3 mb-4">
            <FaKey className="text-xl text-primary" />
            <h3 className="text-lg font-semibold">Authentication Methods</h3>
          </div>
          <div className="space-y-3">
            {configData?.authentication_methods_policy?.error ? (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <div className="text-sm text-destructive">{configData.authentication_methods_policy.error}</div>
              </div>
            ) : configData?.authentication_methods_policy?.authenticationMethodConfigurations ? (
              configData.authentication_methods_policy.authenticationMethodConfigurations
                .filter(method => method.state === 'enabled')
                .map((method, index) => (
                  <div key={index} className="p-3 bg-secondary/50 rounded-lg">
                    <div className="font-medium text-sm">{method.id}</div>
                    <div className="text-xs text-muted-foreground">
                      State: {method.state}
                    </div>
                  </div>
                ))
            ) : (
              <p className="text-sm text-muted-foreground">No authentication methods found</p>
            )}
          </div>
        </motion.div>

        {/* Users Overview */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-6 bg-card rounded-xl shadow-lg border border-border"
        >
          <div className="flex items-center space-x-3 mb-4">
            <FaUser className="text-xl text-primary" />
            <h3 className="text-lg font-semibold">Users Overview</h3>
          </div>
          <div className="space-y-3">
            {configData?.users?.error ? (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <div className="text-sm text-destructive">{configData.users.error}</div>
              </div>
            ) : configData?.users?.value?.length > 0 ? (
              <div>
                <div className="text-2xl font-bold text-primary">
                  {configData.users.value.length}
                </div>
                <div className="text-sm text-muted-foreground">Total users (showing first 10)</div>
                <div className="mt-3 space-y-2">
                  {configData.users.value.slice(0, 3).map((user, index) => (
                    <div key={index} className="p-2 bg-secondary/50 rounded text-sm">
                      <div className="font-medium">{user.displayName || user.userPrincipalName}</div>
                      <div className="text-xs text-muted-foreground">
                        {user.accountEnabled ? 'Active' : 'Disabled'}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No users found</p>
            )}
          </div>
        </motion.div>

        {/* Applications */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-6 bg-card rounded-xl shadow-lg border border-border"
        >
          <div className="flex items-center space-x-3 mb-4">
            <FaDesktop className="text-xl text-primary" />
            <h3 className="text-lg font-semibold">Applications</h3>
          </div>
          <div className="space-y-3">
            {configData?.applications?.error ? (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <div className="text-sm text-destructive">{configData.applications.error}</div>
              </div>
            ) : configData?.applications?.value?.length > 0 ? (
              <div>
                <div className="text-2xl font-bold text-primary">
                  {configData.applications.value.length}
                </div>
                <div className="text-sm text-muted-foreground">Registered applications (showing first 10)</div>
                <div className="mt-3 space-y-2">
                  {configData.applications.value.slice(0, 3).map((app, index) => (
                    <div key={index} className="p-2 bg-secondary/50 rounded text-sm">
                      <div className="font-medium">{app.displayName}</div>
                      <div className="text-xs text-muted-foreground">
                        Created: {new Date(app.createdDateTime).toLocaleDateString()}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No applications found</p>
            )}
          </div>
        </motion.div>

        {/* Groups */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-6 bg-card rounded-xl shadow-lg border border-border"
        >
          <div className="flex items-center space-x-3 mb-4">
            <FaUsers className="text-xl text-primary" />
            <h3 className="text-lg font-semibold">Groups</h3>
          </div>
          <div className="space-y-3">
            {configData?.groups?.error ? (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <div className="text-sm text-destructive">{configData.groups.error}</div>
              </div>
            ) : configData?.groups?.value?.length > 0 ? (
              <div>
                <div className="text-2xl font-bold text-primary">
                  {configData.groups.value.length}
                </div>
                <div className="text-sm text-muted-foreground">Total groups (showing first 10)</div>
                <div className="mt-3 space-y-2">
                  {configData.groups.value.slice(0, 3).map((group, index) => (
                    <div key={index} className="p-2 bg-secondary/50 rounded text-sm">
                      <div className="font-medium">{group.displayName}</div>
                      {group.description && (
                        <div className="text-xs text-muted-foreground">{group.description}</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No groups found</p>
            )}
          </div>
        </motion.div>

        {/* Directory Settings */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-6 bg-card rounded-xl shadow-lg border border-border"
        >
          <div className="flex items-center space-x-3 mb-4">
            <FaLock className="text-xl text-primary" />
            <h3 className="text-lg font-semibold">Organization Settings</h3>
          </div>
          <div className="space-y-3">
            {configData?.organization?.error ? (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <div className="text-sm text-destructive">{configData.organization.error}</div>
              </div>
            ) : configData?.organization?.value?.length > 0 ? (
              <div className="space-y-2">
                {configData.organization.value.slice(0, 3).map((org, index) => (
                  <div key={index} className="p-2 bg-secondary/50 rounded text-sm">
                    <div className="font-medium">{org.displayName || org.id}</div>
                    <div className="text-xs text-muted-foreground">
                      Domain: {org.verifiedDomains?.[0]?.name || 'N/A'}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No organization settings found</p>
            )}
          </div>
        </motion.div>

        {/* Authorization Policy */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-6 bg-card rounded-xl shadow-lg border border-border"
        >
          <div className="flex items-center space-x-3 mb-4">
            <FaShieldAlt className="text-xl text-primary" />
            <h3 className="text-lg font-semibold">Authorization Policy</h3>
          </div>
          <div className="space-y-3">
            {configData?.authorization_policy?.error ? (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <div className="text-sm text-destructive">{configData.authorization_policy.error}</div>
              </div>
            ) : configData?.authorization_policy?.value?.length > 0 ? (
              <div className="space-y-2">
                {configData.authorization_policy.value.slice(0, 3).map((policy, index) => (
                  <div key={index} className="p-2 bg-secondary/50 rounded text-sm">
                    <div className="font-medium">{policy.displayName || policy.id}</div>
                    <div className="text-xs text-muted-foreground">
                      Type: {policy.templateId || 'N/A'}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No authorization policies found</p>
            )}
          </div>
        </motion.div>

        {/* Cross Tenant Access Policy */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-6 bg-card rounded-xl shadow-lg border border-border"
        >
          <div className="flex items-center space-x-3 mb-4">
            <FaGlobe className="text-xl text-primary" />
            <h3 className="text-lg font-semibold">Cross Tenant Access</h3>
          </div>
          <div className="space-y-3">
            {configData?.cross_tenant_access_policy?.error ? (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <div className="text-sm text-destructive">{configData.cross_tenant_access_policy.error}</div>
              </div>
            ) : configData?.cross_tenant_access_policy?.value?.length > 0 ? (
              <div className="space-y-2">
                {configData.cross_tenant_access_policy.value.slice(0, 3).map((policy, index) => (
                  <div key={index} className="p-2 bg-secondary/50 rounded text-sm">
                    <div className="font-medium">{policy.displayName || policy.id}</div>
                    <div className="text-xs text-muted-foreground">
                      Type: {policy.templateId || 'N/A'}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No cross tenant access policies found</p>
            )}
          </div>
        </motion.div>

        {/* Cross Tenant Access Default */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-6 bg-card rounded-xl shadow-lg border border-border"
        >
          <div className="flex items-center space-x-3 mb-4">
            <FaGlobe className="text-xl text-primary" />
            <h3 className="text-lg font-semibold">Cross Tenant Default</h3>
          </div>
          <div className="space-y-3">
            {configData?.cross_tenant_access_default?.error ? (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <div className="text-sm text-destructive">{configData.cross_tenant_access_default.error}</div>
              </div>
            ) : configData?.cross_tenant_access_default ? (
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Inbound MFA Trusted</span>
                  <span className="font-medium">
                    {configData.cross_tenant_access_default?.inboundTrust?.isMfaAccepted === true ? 'Yes' :
                      configData.cross_tenant_access_default?.inboundTrust?.isMfaAccepted === false ? 'No' : 'N/A'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Outbound Settings</span>
                  <span className="font-medium">{Object.keys(configData.cross_tenant_access_default || {}).length > 0 ? 'Configured' : 'N/A'}</span>
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No default policy data</p>
            )}
          </div>
        </motion.div>

        {/* Cross Tenant Partners */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-6 bg-card rounded-xl shadow-lg border border-border"
        >
          <div className="flex items-center space-x-3 mb-4">
            <FaGlobe className="text-xl text-primary" />
            <h3 className="text-lg font-semibold">Cross Tenant Partners</h3>
          </div>
          <div className="space-y-3">
            {configData?.cross_tenant_access_partners?.error ? (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <div className="text-sm text-destructive">{configData.cross_tenant_access_partners.error}</div>
              </div>
            ) : configData?.cross_tenant_access_partners?.value?.length > 0 ? (
              <div>
                <div className="text-2xl font-bold text-primary">
                  {configData.cross_tenant_access_partners.value.length}
                </div>
                <div className="text-sm text-muted-foreground">Configured partners</div>
                <div className="mt-3 space-y-2">
                  {configData.cross_tenant_access_partners.value.slice(0, 3).map((p, i) => (
                    <div key={i} className="p-2 bg-secondary/50 rounded text-sm">
                      <div className="font-medium">{p.tenantId || p.id}</div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No partners configured</p>
            )}
          </div>
        </motion.div>

        {/* Audit Logs */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-6 bg-card rounded-xl shadow-lg border border-border"
        >
          <div className="flex items-center space-x-3 mb-4">
            <FaClipboardList className="text-xl text-primary" />
            <h3 className="text-lg font-semibold">Audit Logs</h3>
          </div>
          <div className="space-y-3">
            {configData?.audit_logs?.error ? (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <div className="text-sm text-destructive">{configData.audit_logs.error}</div>
              </div>
            ) : configData?.audit_logs?.value?.length > 0 ? (
              <div>
                <div className="text-2xl font-bold text-primary">
                  {configData.audit_logs.value.length}
                </div>
                <div className="text-sm text-muted-foreground">Recent audit events (showing first 10)</div>
                <div className="mt-3 space-y-2">
                  {configData.audit_logs.value.slice(0, 3).map((log, index) => (
                    <div key={index} className="p-2 bg-secondary/50 rounded text-sm">
                      <div className="font-medium">{log.activityDisplayName || 'Unknown Activity'}</div>
                      <div className="text-xs text-muted-foreground">
                        {new Date(log.activityDateTime).toLocaleDateString()}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No audit logs found</p>
            )}
          </div>
        </motion.div>

        {/* Risky Users (Identity Protection) */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-6 bg-card rounded-xl shadow-lg border border-border"
        >
          <div className="flex items-center space-x-3 mb-4">
            <FaShieldAlt className="text-xl text-primary" />
            <h3 className="text-lg font-semibold">Risky Users</h3>
          </div>
          <div className="space-y-3">
            {configData?.identity_protection_risky_users?.error ? (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <div className="text-sm text-destructive">{configData.identity_protection_risky_users.error}</div>
              </div>
            ) : configData?.identity_protection_risky_users?.value?.length >= 0 ? (
              <div>
                <div className="text-2xl font-bold text-primary">
                  {configData.identity_protection_risky_users.value?.length || 0}
                </div>
                <div className="text-sm text-muted-foreground">Risky users (first 10)</div>
                <div className="mt-3 space-y-2">
                  {(configData.identity_protection_risky_users.value || []).slice(0, 3).map((u, i) => (
                    <div key={i} className="p-2 bg-secondary/50 rounded text-sm">
                      <div className="font-medium">{u.userPrincipalName || u.id}</div>
                      {u.riskLevel && (
                        <div className="text-xs text-muted-foreground">Risk: {u.riskLevel}</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No risky users found</p>
            )}
          </div>
        </motion.div>

        {/* Directory Roles */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-6 bg-card rounded-xl shadow-lg border border-border"
        >
          <div className="flex items-center space-x-3 mb-4">
            <FaShieldAlt className="text-xl text-primary" />
            <h3 className="text-lg font-semibold">Directory Roles</h3>
          </div>
          <div className="space-y-3">
            {configData?.directory_roles?.error ? (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <div className="text-sm text-destructive">{configData.directory_roles.error}</div>
              </div>
            ) : configData?.directory_roles?.value?.length > 0 ? (
              <div className="space-y-2">
                {configData.directory_roles.value.slice(0, 3).map((role, idx) => {
                  const memberCount = (configData.directory_role_members &&
                    configData.directory_role_members[role.id] &&
                    (configData.directory_role_members[role.id].value || []).length) || 0;
                  return (
                    <div key={idx} className="p-2 bg-secondary/50 rounded text-sm">
                      <div className="font-medium">{role.displayName || role.templateId || role.id}</div>
                      <div className="text-xs text-muted-foreground">Members: {memberCount}</div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No directory roles found</p>
            )}
          </div>
        </motion.div>

        {/* Group Settings */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-6 bg-card rounded-xl shadow-lg border border-border"
        >
          <div className="flex items-center space-x-3 mb-4">
            <FaUsers className="text-xl text-primary" />
            <h3 className="text-lg font-semibold">Group Settings</h3>
          </div>
          <div className="space-y-3">
            {configData?.group_settings?.error ? (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <div className="text-sm text-destructive">{configData.group_settings.error}</div>
              </div>
            ) : configData?.group_settings?.value?.length > 0 ? (
              <div className="space-y-2 text-sm">
                {(() => {
                  const list = configData.group_settings.value || [];
                  let enableVal = null;
                  for (const s of list) {
                    if (Array.isArray(s.values)) {
                      const v = s.values.find(x => x.name === 'EnableGroupCreation');
                      if (v) { enableVal = v.value; break; }
                    }
                  }
                  return (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Self-service group creation</span>
                      <span className="font-medium">{enableVal !== null ? String(enableVal) : 'Unknown'}</span>
                    </div>
                  );
                })()}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No group settings found</p>
            )}
          </div>
        </motion.div>

        {/* Directory Settings */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-6 bg-card rounded-xl shadow-lg border border-border"
        >
          <div className="flex items-center space-x-3 mb-4">
            <FaCog className="text-xl text-primary" />
            <h3 className="text-lg font-semibold">Directory Settings</h3>
          </div>
          <div className="space-y-3">
            {configData?.settings?.error ? (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <div className="text-sm text-destructive">{configData.settings.error}</div>
              </div>
            ) : configData?.settings?.value?.length >= 0 ? (
              <div>
                <div className="text-2xl font-bold text-primary">{configData.settings.value?.length || 0}</div>
                <div className="text-sm text-muted-foreground">Directory settings objects</div>
                <div className="mt-3 space-y-2 text-xs">
                  {(configData.settings.value || []).slice(0, 2).map((s, i) => (
                    <div key={i} className="p-2 bg-secondary/50 rounded">
                      <div className="font-medium">{s.displayName || s.id}</div>
                      {Array.isArray(s.values) && s.values.length > 0 && (
                        <div className="text-muted-foreground">{s.values[0].name}: {String(s.values[0].value)}</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No directory settings found</p>
            )}
          </div>
        </motion.div>

        {/* Certificate-based Auth Configuration */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-6 bg-card rounded-xl shadow-lg border border-border"
        >
          <div className="flex items-center space-x-3 mb-4">
            <FaLock className="text-xl text-primary" />
            <h3 className="text-lg font-semibold">Certificate-based Auth</h3>
          </div>
          <div className="space-y-3">
            {configData?.certificate_based_auth_configuration?.error ? (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <div className="text-sm text-destructive">{configData.certificate_based_auth_configuration.error}</div>
              </div>
            ) : configData?.certificate_based_auth_configuration?.value?.length >= 0 ? (
              <div>
                <div className="text-2xl font-bold text-primary">{configData.certificate_based_auth_configuration.value?.length || 0}</div>
                <div className="text-sm text-muted-foreground">Certificate auth configurations</div>
                {(configData.certificate_based_auth_configuration.value || []).slice(0, 1).map((c, i) => (
                  <div key={i} className="mt-3 p-2 bg-secondary/50 rounded text-xs">
                    <div className="font-medium">{c.id || 'Config'}</div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No certificate-based auth configuration found</p>
            )}
          </div>
        </motion.div>

        {/* Lifecycle Workflows */}
        <motion.div
          whileHover={{ scale: 1.01 }}
          className="p-6 bg-card rounded-xl shadow-lg border border-border"
        >
          <div className="flex items-center space-x-3 mb-4">
            <FaClipboardList className="text-xl text-primary" />
            <h3 className="text-lg font-semibold">Lifecycle Workflows</h3>
          </div>
          <div className="space-y-3">
            {configData?.lifecycle_workflows?.error ? (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <div className="text-sm text-destructive">{configData.lifecycle_workflows.error}</div>
              </div>
            ) : configData?.lifecycle_workflows?.value?.length >= 0 ? (
              <div>
                <div className="text-2xl font-bold text-primary">{configData.lifecycle_workflows.value?.length || 0}</div>
                <div className="text-sm text-muted-foreground">Lifecycle workflows</div>
                <div className="mt-3 space-y-2">
                  {(configData.lifecycle_workflows.value || []).slice(0, 3).map((w, i) => (
                    <div key={i} className="p-2 bg-secondary/50 rounded text-sm">
                      <div className="font-medium">{w.displayName || w.id}</div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No lifecycle workflows found</p>
            )}
          </div>
        </motion.div>
      </div>

      {/* ISO 27017 Compliance Section */}
      {configData?.compliance_check && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="mt-8"
        >
          <div className="flex items-center space-x-4 mb-6">
            <div className="p-3 bg-green-100 dark:bg-green-900/20 rounded-lg">
              <FaShieldAlt className="text-2xl text-green-600 dark:text-green-400" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-foreground">ISO 27017 Compliance Assessment</h2>
              <p className="text-muted-foreground">Azure AD security compliance against ISO 27017 standards</p>
            </div>
          </div>

          {/* Compliance Score Overview */}
          <motion.div
            whileHover={{ scale: 1.01 }}
            className="p-6 bg-card rounded-xl shadow-lg border border-border mb-6"
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Compliance Overview</h3>
              <div className="text-right">
                <div className="text-3xl font-bold text-primary">
                  {configData.compliance_check.summary?.compliance_score || 0}%
                </div>
                <div className="text-sm text-muted-foreground">Compliance Score</div>
              </div>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 bg-green-100 dark:bg-green-900/20 rounded-lg">
                <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                  {configData.compliance_check.summary?.compliant_count || 0}
                </div>
                <div className="text-sm text-green-700 dark:text-green-300">Compliant</div>
              </div>
              <div className="p-4 bg-red-100 dark:bg-red-900/20 rounded-lg">
                <div className="text-2xl font-bold text-red-600 dark:text-red-400">
                  {configData.compliance_check.summary?.non_compliant_count || 0}
                </div>
                <div className="text-sm text-red-700 dark:text-red-300">Non-Compliant</div>
              </div>
              <div className="p-4 bg-gray-100 dark:bg-gray-900/20 rounded-lg">
                <div className="text-2xl font-bold text-gray-600 dark:text-gray-400">
                  {configData.compliance_check.summary?.not_applicable_count || 0}
                </div>
                <div className="text-sm text-gray-700 dark:text-gray-300">Not Applicable</div>
              </div>
            </div>
          </motion.div>

          {/* Non-Compliant Rules - Recommendations */}
          {configData.compliance_check.non_compliant?.length > 0 && (
            <motion.div
              whileHover={{ scale: 1.01 }}
              className="p-6 bg-card rounded-xl shadow-lg border border-border mb-6"
            >
              <div className="flex items-center space-x-3 mb-4">
                <FaExclamationTriangle className="text-xl text-red-500" />
                <h3 className="text-lg font-semibold">Security Recommendations</h3>
              </div>
              <div className="space-y-4">
                {configData.compliance_check.non_compliant.map((rule, index) => (
                  <div key={index} className="p-4 bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800 rounded-lg">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <h4 className="font-semibold text-red-800 dark:text-red-200">{rule.title}</h4>
                        <p className="text-sm text-red-700 dark:text-red-300 mt-1">{rule.description}</p>
                      </div>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        rule.severity === 'high' ? 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400' :
                        rule.severity === 'medium' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400' :
                        'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400'
                      }`}>
                        {rule.severity?.toUpperCase()}
                      </span>
                    </div>
                    <div className="mt-3 p-3 bg-white dark:bg-gray-800 rounded border">
                      <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Recommended Action:</div>
                      <p className="text-sm text-gray-600 dark:text-gray-400">{rule.remediation}</p>
                    </div>
                    <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                      <span className="font-medium">Control ID:</span> {rule.control_id} | 
                      <span className="font-medium ml-2">Current Value:</span> {String(rule.current_value || 'N/A')} | 
                      <span className="font-medium ml-2">Expected:</span> {String(rule.expected_value || 'N/A')}
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          {/* Compliant Rules */}
          {configData.compliance_check.compliant?.length > 0 && (
            <motion.div
              whileHover={{ scale: 1.01 }}
              className="p-6 bg-card rounded-xl shadow-lg border border-border mb-6"
            >
              <div className="flex items-center space-x-3 mb-4">
                <FaCheckCircle className="text-xl text-green-500" />
                <h3 className="text-lg font-semibold">Compliant Controls</h3>
              </div>
              <div className="space-y-3">
                {configData.compliance_check.compliant.map((rule, index) => (
                  <div key={index} className="p-3 bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-800 rounded-lg">
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="font-medium text-green-800 dark:text-green-200">{rule.title}</h4>
                        <p className="text-xs text-green-600 dark:text-green-400 mt-1">{rule.control_id}</p>
                      </div>
                      <FaCheckCircle className="text-green-500" />
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          {/* Compliance Checklist */}
          <motion.div
            whileHover={{ scale: 1.01 }}
            className="p-6 bg-card rounded-xl shadow-lg border border-border"
          >
            <div className="flex items-center space-x-3 mb-4">
              <FaClipboardList className="text-xl text-primary" />
              <h3 className="text-lg font-semibold">Compliance Checklist</h3>
            </div>
            <div className="space-y-3">
              {configData.compliance_check.non_compliant?.map((rule, index) => (
                <div key={index} className="flex items-center space-x-3 p-3 bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800 rounded-lg">
                  <input 
                    type="checkbox" 
                    className="w-4 h-4 text-red-600 bg-gray-100 border-gray-300 rounded focus:ring-red-500 dark:focus:ring-red-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
                    disabled
                  />
                  <div className="flex-1">
                    <label className="text-sm font-medium text-red-800 dark:text-red-200">
                      {rule.title}
                    </label>
                    <p className="text-xs text-red-600 dark:text-red-400 mt-1">
                      {rule.remediation}
                    </p>
                  </div>
                  <span className="text-xs text-red-600 dark:text-red-400 font-medium">
                    {rule.severity?.toUpperCase()}
                  </span>
                </div>
              ))}
              {configData.compliance_check.compliant?.map((rule, index) => (
                <div key={`compliant-${index}`} className="flex items-center space-x-3 p-3 bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-800 rounded-lg">
                  <input 
                    type="checkbox" 
                    checked
                    readOnly
                    className="w-4 h-4 text-green-600 bg-gray-100 border-gray-300 rounded focus:ring-green-500 dark:focus:ring-green-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
                  />
                  <div className="flex-1">
                    <label className="text-sm font-medium text-green-800 dark:text-green-200">
                      {rule.title}
                    </label>
                    <p className="text-xs text-green-600 dark:text-green-400 mt-1">
                      ✓ Compliant
                    </p>
                  </div>
                  <FaCheckCircle className="text-green-500" />
                </div>
              ))}
            </div>
          </motion.div>
        </motion.div>
      )}
    </motion.div>
  );
};

const AzureADConnection = () => {
  const { authToken } = useAuth();
  const [formData, setFormData] = useState({
    clientId: '',
    clientSecret: '',
    tenantId: ''
  });
  const [showSecret, setShowSecret] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [statusLoading, setStatusLoading] = useState(true);
  const [showDisconnectModal, setShowDisconnectModal] = useState(false);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        setStatusLoading(true);
        const response = await fetch('http://localhost:8000/api/azure/status', {
          headers: {
            'Authorization': `Bearer ${authToken}`
          }
        });
        if (response.ok) {
          const data = await response.json();
          setIsConnected(!!data.connected);
        }
      } catch (e) {
        // ignore
      } finally {
        setStatusLoading(false);
      }
    };
    if (authToken) {
      fetchStatus();
    }
  }, [authToken]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    // Clear error when user starts typing
    if (error) setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await fetch('http://localhost:8000/api/azure/connect', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify(formData)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to connect to Azure AD');
      }

      const data = await response.json();
      setSuccess('Successfully connected to Azure AD!');
      setIsConnected(true);
      
      // Clear form after successful connection
      setFormData({
        clientId: '',
        clientSecret: '',
        tenantId: ''
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDisconnect = () => {
    setShowDisconnectModal(true);
  };

  const confirmDisconnect = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/azure/disconnect', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });

      if (response.ok) {
        setIsConnected(false);
        setSuccess('Successfully disconnected from Azure AD');
      }
    } catch (err) {
      setError('Failed to disconnect from Azure AD');
    } finally {
      setIsLoading(false);
      setShowDisconnectModal(false);
    }
  };

  const cancelDisconnect = () => setShowDisconnectModal(false);

  return (
    <>
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="space-y-6"
    >
      <div className="flex items-center space-x-4 mb-6">
        <div className="p-3 bg-blue-100 dark:bg-blue-900/20 rounded-lg">
          <FaCloud className="text-2xl text-blue-600 dark:text-blue-400" />
        </div>
        <div>
          <h2 className="text-2xl font-bold text-foreground">Connect to Azure AD</h2>
          <p className="text-muted-foreground">Configure your Azure Active Directory integration</p>
        </div>
      </div>

      <div className={`${isConnected ? 'grid grid-cols-1 gap-6' : 'grid grid-cols-1 lg:grid-cols-3 gap-6'}`}>
        {/* Connection Form - hidden when connected */}
        {!isConnected && (
          <div className="lg:col-span-2">
            <motion.div
              whileHover={{ scale: 1.01 }}
              className="p-6 bg-card rounded-xl shadow-lg border border-border"
            >
              <div className="flex items-center space-x-3 mb-6">
                <FaKey className="text-xl text-primary" />
                <h3 className="text-lg font-semibold">Azure AD Configuration</h3>
              </div>

              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mb-4 p-4 bg-destructive/10 border border-destructive/20 rounded-lg"
                >
                  <div className="flex items-center space-x-2">
                    <FaExclamationTriangle className="text-destructive" />
                    <span className="text-destructive text-sm">{error}</span>
                  </div>
                </motion.div>
              )}

              {success && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mb-4 p-4 bg-green-100 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg"
                >
                  <div className="flex items-center space-x-2">
                    <FaCheckCircle className="text-green-600 dark:text-green-400" />
                    <span className="text-green-700 dark:text-green-300 text-sm">{success}</span>
                  </div>
                </motion.div>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                {/* Client ID */}
                <div className="space-y-2">
                  <label className="flex items-center space-x-2 text-sm font-medium">
                    <FaIdCard className="text-primary" />
                    <span>Azure Client ID</span>
                  </label>
                  <input
                    type="text"
                    name="clientId"
                    value={formData.clientId}
                    onChange={handleInputChange}
                    placeholder="Enter your Azure Client ID"
                    className="w-full px-4 py-3 border border-border rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary bg-background transition-colors"
                    required
                  />
                  <p className="text-xs text-muted-foreground">
                    The Application (client) ID from your Azure AD app registration
                  </p>
                </div>

                {/* Tenant ID */}
                <div className="space-y-2">
                  <label className="flex items-center space-x-2 text-sm font-medium">
                    <FaBuilding className="text-primary" />
                    <span>Azure Tenant ID</span>
                  </label>
                  <input
                    type="text"
                    name="tenantId"
                    value={formData.tenantId}
                    onChange={handleInputChange}
                    placeholder="Enter your Azure Tenant ID"
                    className="w-full px-4 py-3 border border-border rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary bg-background transition-colors"
                    required
                  />
                  <p className="text-xs text-muted-foreground">
                    The Directory (tenant) ID from your Azure AD
                  </p>
                </div>

                {/* Client Secret */}
                <div className="space-y-2">
                  <label className="flex items-center space-x-2 text-sm font-medium">
                    <FaKey className="text-primary" />
                    <span>Azure Client Secret</span>
                  </label>
                  <div className="relative">
                    <input
                      type={showSecret ? "text" : "password"}
                      name="clientSecret"
                      value={formData.clientSecret}
                      onChange={handleInputChange}
                      placeholder="Enter your Azure Client Secret"
                      className="w-full px-4 py-3 pr-12 border border-border rounded-lg focus:ring-2 focus:ring-primary/20 focus:border-primary bg-background transition-colors"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowSecret(!showSecret)}
                      className="absolute right-3 top-1/2 transform -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                    >
                      {showSecret ? <FaEyeSlash /> : <FaEye />}
                    </button>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    The client secret from your Azure AD app registration
                  </p>
                </div>

                {/* Submit Button */}
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  type="submit"
                  disabled={isLoading}
                  className="w-full flex items-center justify-center space-x-2 px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                >
                  {isLoading ? (
                    <>
                      <FaSpinner className="animate-spin" />
                      <span>Connecting...</span>
                    </>
                  ) : (
                    <>
                      <FaSave />
                      <span>Connect to Azure AD</span>
                    </>
                  )}
                </motion.button>
              </form>
            </motion.div>
          </div>
        )}

        {/* Connection Status & Info */}
        <div className="space-y-6">
          {/* Connection Status */}
          <motion.div
            whileHover={{ scale: 1.01 }}
            className="p-6 bg-card rounded-xl shadow-lg border border-border"
          >
            <div className="flex items-center space-x-3 mb-4">
              <FaShieldAlt className="text-xl text-primary" />
              <h3 className="text-lg font-semibold">Connection Status</h3>
            </div>
            
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Status</span>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  isConnected 
                    ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400' 
                    : 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400'
                }`}>
                  {statusLoading ? 'Checking…' : (isConnected ? 'Connected' : 'Not Connected')}
                </span>
              </div>
              
              {isConnected && (
                <motion.button
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={handleDisconnect}
                  disabled={isLoading}
                  className="w-full px-4 py-2 border border-destructive text-destructive rounded-lg hover:bg-destructive/10 disabled:opacity-50 transition-colors"
                >
                  Disconnect
                </motion.button>
              )}
            </div>
          </motion.div>

          {/* Help Information */}
          <motion.div
            whileHover={{ scale: 1.01 }}
            className="p-6 bg-card rounded-xl shadow-lg border border-border"
          >
            <div className="flex items-center space-x-3 mb-4">
              <FaQuestionCircle className="text-xl text-primary" />
              <h3 className="text-lg font-semibold">How to Get Credentials</h3>
            </div>
            
            <div className="space-y-3 text-sm text-muted-foreground">
              <div className="space-y-2">
                <h4 className="font-medium text-foreground">1. Azure Portal</h4>
                <p>Go to Azure Portal → Azure Active Directory → App registrations</p>
              </div>
              
              <div className="space-y-2">
                <h4 className="font-medium text-foreground">2. Create App</h4>
                <p>Create a new app registration or use an existing one</p>
              </div>
              
              <div className="space-y-2">
                <h4 className="font-medium text-foreground">3. Get Credentials</h4>
                <p>Copy the Application ID, Tenant ID, and create a client secret</p>
              </div>
              
              <div className="space-y-2">
                <h4 className="font-medium text-foreground">4. Permissions</h4>
                <p>Ensure the app has necessary permissions for compliance scanning</p>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </motion.div>
    {showDisconnectModal && (
      <div className="fixed inset-0 z-50 flex items-center justify-center">
        <div className="absolute inset-0 bg-black/50" onClick={cancelDisconnect} />
        <div className="relative z-10 w-full max-w-md p-6 bg-card rounded-xl shadow-xl border border-border">
          <div className="flex items-center space-x-3 mb-4">
            <FaExclamationTriangle className="text-destructive" />
            <h3 className="text-lg font-semibold">Disconnect Azure AD</h3>
          </div>
          <p className="text-sm text-muted-foreground mb-6">Are you sure you want to disconnect your Azure Active Directory integration? This will disable Azure-related features until reconnected.</p>
          <div className="flex justify-end space-x-3">
            <button
              onClick={cancelDisconnect}
              className="px-4 py-2 rounded-lg border border-border hover:bg-secondary"
            >
              Cancel
            </button>
            <button
              onClick={confirmDisconnect}
              disabled={isLoading}
              className="px-4 py-2 rounded-lg bg-destructive text-white hover:bg-red-600 disabled:opacity-50"
            >
              {isLoading ? 'Disconnecting…' : 'Disconnect'}
            </button>
          </div>
        </div>
      </div>
    )}
    </>
  );
};

const UserDashboard = () => {
  const { user, authToken, logout } = useAuth();
  const navigate = useNavigate();
  const [userData, setUserData] = useState(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [error, setError] = useState(null);

  // Add event listener for setActiveTab event
  useEffect(() => {
    const handleSetActiveTab = (event) => {
      setActiveTab(event.detail);
    };

    window.addEventListener('setActiveTab', handleSetActiveTab);

    return () => {
      window.removeEventListener('setActiveTab', handleSetActiveTab);
    };
  }, []);

  useEffect(() => {
    const fetchUserData = async () => {
      try {
        if (!authToken) {
          throw new Error('No authentication token found');
        }

        const response = await fetch('http://localhost:8000/team/user-data', {
          headers: {
            'Authorization': `Bearer ${authToken}`
          }
        });
        
        if (response.status === 401) {
          logout();
          throw new Error('Session expired. Please login again.');
        }
        
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || 'Failed to fetch user data');
        }
        
        const data = await response.json();
        setUserData(data);
        setError(null);
      } catch (error) {
        console.error('Error fetching user data:', error);
        setError(error.message);
        if (error.message.includes('Session expired')) {
          navigate('/login');
        }
      }
    };

    fetchUserData();
  }, [authToken, logout, navigate]);

  const getSidebarItems = () => {
    const commonItems = [
      { id: 'dashboard', icon: <FaChartLine />, label: 'Dashboard' },
    ];

    const roleSpecificItems = {
      'it_team': [
        { id: 'azure', icon: <FaCloud />, label: 'Connect to Azure' },
        { id: 'azure-config', icon: <FaCog />, label: 'Azure AD Config' },
        { id: 'chatbot', icon: <FaRobot />, label: 'Compliance Chatbot' },
      ],
      'management_team': [],
      'compliance_team': [
        { id: 'chatbot', icon: <FaRobot />, label: 'Compliance Chatbot' },
        { id: 'testing', icon: <FaDesktop />, label: 'UI Testing' },
        { id: 'scan', icon: <FaCalendarAlt />, label: 'Schedule Scan' },
      ],
    };

    // Add profile at the end
    const allItems = [...commonItems, ...(roleSpecificItems[userData?.role] || [])];
    allItems.push({ id: 'profile', icon: <FaUser />, label: 'Profile' });

    return allItems;
  };

  const handleLogout = () => {
    logout();
  };

  if (!userData) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        {error ? (
          <div className="text-center">
            <div className="text-destructive text-lg mb-4">{error}</div>
            <button
              onClick={() => navigate('/login')}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90"
            >
              Return to Login
            </button>
          </div>
        ) : (
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
          className="h-12 w-12 border-t-2 border-b-2 border-primary rounded-full"
        />
        )}
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
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-bold text-foreground">
                {userData.role === 'it_team' ? 'IT Team Dashboard' :
                 userData.role === 'compliance_team' ? 'Compliance Team Dashboard' :
                 'Management Team Dashboard'}
              </h2>
              <div className="flex items-center space-x-2">
                <FaShieldAlt className="text-primary" />
                <span className="text-sm text-muted-foreground capitalize">
                  {userData.role.replace('_', ' ')}
                </span>
              </div>
            </div>
            
            <div className="mb-6">
              <h3 className="text-lg font-semibold mb-4">Chatbot Analytics</h3>
              <div className="w-full">
                <ChatbotAnalytics />
              </div>
            </div>

            <div className="mb-6">
              <h3 className="text-lg font-semibold mb-4">Integrations</h3>
              <div className="grid grid-cols-1">
                <AzureConnectionMiniCard />
              </div>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              <motion.div
                whileHover={{ scale: 1.02 }}
                className="p-6 bg-card rounded-xl shadow-lg hover:shadow-xl transition-shadow"
              >
                <h3 className="text-lg font-semibold mb-4">System Status</h3>
                <SystemStatus />
              </motion.div>
              
              <motion.div
                whileHover={{ scale: 1.02 }}
                className="p-6 bg-card rounded-xl shadow-lg hover:shadow-xl transition-shadow"
              >
                <h3 className="text-lg font-semibold mb-4">Recent Activities</h3>
                <RecentActivities />
              </motion.div>
              
              <motion.div
                whileHover={{ scale: 1.02 }}
                className="p-6 bg-card rounded-xl shadow-lg hover:shadow-xl transition-shadow"
              >
                <h3 className="text-lg font-semibold mb-4">Notifications</h3>
                <Notifications />
              </motion.div>
            </div>
          </motion.div>
        );
      case 'profile':
        return <Profile />;
      case 'azure':
        return <AzureADConnection />;
      case 'azure-config':
        return <AzureADConfiguration />;
      case 'chatbot':
        return <ComplianceChat />;
      case 'testing':
        return <UiTesting />;
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
              <div className="flex items-center space-x-4 mb-4">
                <FaCalendarAlt className="text-2xl text-primary" />
                <div>
                  <h3 className="text-lg font-semibold">Scan Management</h3>
              <p className="text-muted-foreground">Schedule and manage compliance scans</p>
                </div>
              </div>
              <div className="space-y-4">
                <button className="w-full px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90">
                  Schedule New Scan
                </button>
                <button className="w-full px-4 py-2 border border-border rounded-lg hover:bg-secondary">
                  View Scan History
                </button>
              </div>
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
          {/* Logo Section */}
          <div className="p-4 border-b border-border bg-card">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 rounded-md bg-primary flex items-center justify-center">
                <span className="text-white font-bold text-lg">C</span>
              </div>
              <span className="font-bold text-lg">Complytics</span>
            </div>
          </div>

          <nav className="flex-1 p-4 space-y-2">
            {getSidebarItems().map((item) => (
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