import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../ui/button';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  FaUserPlus, 
  FaUsers, 
  FaEnvelope, 
  FaUserTie, 
  FaSpinner,
  FaCheckCircle,
  FaTimesCircle,
  FaEdit,
  FaTrash,
  FaUserSlash,
  FaSignOutAlt,
  FaChartLine,
  FaUser
} from 'react-icons/fa';
import Profile from './Profile';

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

const AdminDashboard = () => {
  const { authToken, logout } = useAuth();
  const navigate = useNavigate();
  const [teamMembers, setTeamMembers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showAddMemberForm, setShowAddMemberForm] = useState(false);
  const [newMember, setNewMember] = useState({
    firstName: '',
    lastName: '',
    email: '',
    role: 'compliance_team'
  });
  const [selectedMembers, setSelectedMembers] = useState([]);
  const [editingMember, setEditingMember] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [activeTab, setActiveTab] = useState('dashboard');

  useEffect(() => {
    if (!authToken) {
      navigate('/login');
    } else {
      fetchTeamMembers();
    }
  }, [authToken, navigate]);

  const fetchTeamMembers = async () => {
    try {
      const response = await fetch('http://localhost:8000/admin/team-members', {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch team members');
      }

      const data = await response.json();
      setTeamMembers(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddMember = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    try {
      const response = await fetch('http://localhost:8000/admin/create-team-member', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          first_name: newMember.firstName,
          last_name: newMember.lastName,
          email: newMember.email,
          role: newMember.role
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to add team member');
      }

      setSuccess('Team member added successfully! Credentials have been sent to their email.');
      setShowAddMemberForm(false);
      setNewMember({
        firstName: '',
        lastName: '',
        email: '',
        role: 'compliance_team'
      });
      fetchTeamMembers();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDeleteMember = async (memberId) => {
    try {
      const response = await fetch(`http://localhost:8000/admin/team-members/${memberId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to delete team member');
      }

      setSuccess('Team member deleted successfully');
      fetchTeamMembers();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleBulkDelete = async () => {
    if (selectedMembers.length === 0) {
      setError('Please select team members to delete');
      return;
    }

    try {
      const response = await fetch('http://localhost:8000/admin/team-members/bulk-delete', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          member_ids: selectedMembers
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to delete team members');
      }

      setSuccess(`Successfully deleted ${selectedMembers.length} team members`);
      setSelectedMembers([]);
      fetchTeamMembers();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleEditMember = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    try {
      const response = await fetch(`http://localhost:8000/admin/team-members/${editingMember.id}`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          first_name: editingMember.firstName,
          last_name: editingMember.lastName,
          role: editingMember.role,
          is_active: editingMember.isActive
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to update team member');
      }

      setSuccess('Team member updated successfully');
      setEditingMember(null);
      fetchTeamMembers();
    } catch (err) {
      setError(err.message);
    }
  };

  const toggleMemberSelection = (memberId) => {
    setSelectedMembers(prev => 
      prev.includes(memberId) 
        ? prev.filter(id => id !== memberId)
        : [...prev, memberId]
    );
  };

  const sidebarItems = [
    { id: 'dashboard', icon: <FaChartLine />, label: 'Dashboard' },
    { id: 'profile', icon: <FaUser />, label: 'Profile' },
    // ... other sidebar items ...
  ];

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5 }}
            className="min-h-screen bg-background"
          >
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
              {/* Header */}
              <motion.div 
                initial={{ y: -20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ duration: 0.5 }}
                className="flex justify-between items-center mb-8"
              >
                <div>
                  <h1 className="text-3xl md:text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-purple-600">
                    Organization Dashboard
                  </h1>
                  <p className="mt-2 text-muted-foreground">
                    Manage your team and organization settings
                  </p>
                </div>
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => {
                    logout();
                    navigate('/login');
                  }}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-red-500 to-red-600 text-white shadow-lg hover:shadow-xl transition-all duration-300 hover:from-red-600 hover:to-red-700"
                >
                  <FaSignOutAlt className="h-4 w-4" />
                  <span>Logout</span>
                </motion.button>
              </motion.div>

              {/* Stats cards */}
              <motion.div 
                className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8"
                initial="hidden"
                animate="show"
                variants={containerVariants}
              >
                <motion.div 
                  variants={itemVariants}
                  className="glass-card p-6 rounded-lg border-l-4 border-primary"
                  whileHover={cardHoverVariants.hover}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">Total Team Members</p>
                      <h3 className="text-2xl font-bold">{teamMembers.length}</h3>
                    </div>
                    <div className="p-3 rounded-full bg-primary/10 text-primary">
                      <FaUsers className="h-6 w-6" />
                    </div>
                  </div>
                </motion.div>

                <motion.div 
                  variants={itemVariants}
                  className="glass-card p-6 rounded-lg border-l-4 border-green-500"
                  whileHover={cardHoverVariants.hover}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">Active Members</p>
                      <h3 className="text-2xl font-bold">
                        {teamMembers.filter(member => member.is_active).length}
                      </h3>
                    </div>
                    <div className="p-3 rounded-full bg-green-500/10 text-green-500">
                      <FaUserTie className="h-6 w-6" />
                    </div>
                  </div>
                </motion.div>

                <motion.div 
                  variants={itemVariants}
                  className="glass-card p-6 rounded-lg border-l-4 border-blue-500"
                  whileHover={cardHoverVariants.hover}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">Inactive Team Members</p>
                      <h3 className="text-2xl font-bold">
                        {teamMembers.filter(member => !member.is_active).length}
                      </h3>
                    </div>
                    <div className="p-3 rounded-full bg-blue-500/10 text-blue-500">
                      <FaUserSlash className="h-6 w-6" />
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

              {/* Team Members Section */}
              <div className="glass-card p-6 rounded-lg">
                <div className="flex justify-between items-center mb-6">
                  <h2 className="text-xl font-semibold">Team Members</h2>
                  <div className="flex gap-4">
                    {selectedMembers.length > 0 && (
                      <Button 
                        variant="destructive"
                        onClick={handleBulkDelete}
                        className="flex items-center gap-2"
                      >
                        <FaTrash />
                        Delete Selected ({selectedMembers.length})
                      </Button>
                    )}
                    <Button 
                      onClick={() => setShowAddMemberForm(true)}
                      className="flex items-center gap-2"
                    >
                      <FaUserPlus />
                      Add Team Member
                    </Button>
                  </div>
                </div>

                {/* Add Member Form */}
                <AnimatePresence>
                  {showAddMemberForm && (
                    <motion.div
                      initial={{ opacity: 0, y: -20 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -20 }}
                      className="mb-6 p-6 bg-secondary/50 rounded-lg"
                    >
                      <h3 className="text-lg font-medium mb-4">Add New Team Member</h3>
                      <form onSubmit={handleAddMember} className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div>
                            <label className="block text-sm font-medium mb-1">First Name</label>
                            <input
                              type="text"
                              value={newMember.firstName}
                              onChange={(e) => setNewMember({...newMember, firstName: e.target.value})}
                              className="w-full px-4 py-2 border border-border rounded-md focus:ring-2 focus:ring-primary/50 focus:outline-none"
                              required
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-medium mb-1">Last Name</label>
                            <input
                              type="text"
                              value={newMember.lastName}
                              onChange={(e) => setNewMember({...newMember, lastName: e.target.value})}
                              className="w-full px-4 py-2 border border-border rounded-md focus:ring-2 focus:ring-primary/50 focus:outline-none"
                              required
                            />
                          </div>
                        </div>
                        <div>
                          <label className="block text-sm font-medium mb-1">Email</label>
                          <input
                            type="email"
                            value={newMember.email}
                            onChange={(e) => setNewMember({...newMember, email: e.target.value})}
                            className="w-full px-4 py-2 border border-border rounded-md focus:ring-2 focus:ring-primary/50 focus:outline-none"
                            required
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium mb-1">Role</label>
                          <select
                            value={newMember.role}
                            onChange={(e) => setNewMember({...newMember, role: e.target.value})}
                            className="w-full px-4 py-2 border border-border rounded-md focus:ring-2 focus:ring-primary/50 focus:outline-none"
                          >
                            <option value="compliance_team">Compliance Team</option>
                            <option value="it_team">IT Team</option>
                            <option value="management_team">Management Team</option>
                          </select>
                        </div>
                        <div className="flex justify-end gap-4">
                          <Button
                            type="button"
                            variant="outline"
                            onClick={() => setShowAddMemberForm(false)}
                          >
                            Cancel
                          </Button>
                          <Button type="submit">
                            Add Member
                          </Button>
                        </div>
                      </form>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Edit Member Form */}
                <AnimatePresence>
                  {editingMember && (
                    <motion.div
                      initial={{ opacity: 0, y: -20 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -20 }}
                      className="mb-6 p-6 bg-secondary/50 rounded-lg"
                    >
                      <h3 className="text-lg font-medium mb-4">Edit Team Member</h3>
                      <form onSubmit={handleEditMember} className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div>
                            <label className="block text-sm font-medium mb-1">First Name</label>
                            <input
                              type="text"
                              value={editingMember.firstName}
                              onChange={(e) => setEditingMember({...editingMember, firstName: e.target.value})}
                              className="w-full px-4 py-2 border border-border rounded-md focus:ring-2 focus:ring-primary/50 focus:outline-none"
                              required
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-medium mb-1">Last Name</label>
                            <input
                              type="text"
                              value={editingMember.lastName}
                              onChange={(e) => setEditingMember({...editingMember, lastName: e.target.value})}
                              className="w-full px-4 py-2 border border-border rounded-md focus:ring-2 focus:ring-primary/50 focus:outline-none"
                              required
                            />
                          </div>
                        </div>
                        <div>
                          <label className="block text-sm font-medium mb-1">Role</label>
                          <select
                            value={editingMember.role}
                            onChange={(e) => setEditingMember({...editingMember, role: e.target.value})}
                            className="w-full px-4 py-2 border border-border rounded-md focus:ring-2 focus:ring-primary/50 focus:outline-none"
                          >
                            <option value="compliance_team">Compliance Team</option>
                            <option value="it_team">IT Team</option>
                            <option value="management_team">Management Team</option>
                          </select>
                        </div>
                        <div className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            id="isActive"
                            checked={editingMember.isActive}
                            onChange={(e) => setEditingMember({...editingMember, isActive: e.target.checked})}
                            className="h-4 w-4 text-primary focus:ring-primary/50 border-border rounded"
                          />
                          <label htmlFor="isActive" className="text-sm font-medium">
                            Active Member
                          </label>
                        </div>
                        <div className="flex justify-end gap-4">
                          <Button
                            type="button"
                            variant="outline"
                            onClick={() => setEditingMember(null)}
                          >
                            Cancel
                          </Button>
                          <Button type="submit">
                            Save Changes
                          </Button>
                        </div>
                      </form>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Team Members List */}
                {isLoading ? (
                  <div className="flex justify-center py-8">
                    <FaSpinner className="animate-spin h-8 w-8 text-primary" />
                  </div>
                ) : teamMembers.length === 0 ? (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="text-center py-8"
                  >
                    <div className="mx-auto flex items-center justify-center w-16 h-16 bg-muted rounded-full mb-4">
                      <FaUsers className="h-8 w-8 text-muted-foreground" />
                    </div>
                    <h3 className="text-lg font-medium">No team members yet</h3>
                    <p className="text-muted-foreground mt-2">
                      Start by adding your first team member
                    </p>
                  </motion.div>
                ) : (
                  <motion.div
                    initial="hidden"
                    animate="show"
                    variants={containerVariants}
                    className="grid gap-4"
                  >
                    {teamMembers.map((member) => (
                      <motion.div
                        key={member._id}
                        variants={itemVariants}
                        whileHover={cardHoverVariants.hover}
                        className="glass-card p-4 rounded-lg border border-border/50"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-4">
                            <input
                              type="checkbox"
                              checked={selectedMembers.includes(member._id)}
                              onChange={() => toggleMemberSelection(member._id)}
                              className="h-4 w-4 text-primary focus:ring-primary/50 border-border rounded"
                            />
                            <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center text-primary">
                              <FaUserTie className="h-5 w-5" />
                            </div>
                            <div>
                              <h3 className="font-medium">
                                {member.first_name} {member.last_name}
                              </h3>
                              <p className="text-sm text-muted-foreground">
                                {member.email}
                              </p>
                            </div>
                          </div>
                          <div className="flex items-center space-x-4">
                            <div className="flex items-center space-x-2">
                              <span className={`px-2 py-1 text-xs rounded-full ${
                                member.is_active 
                                  ? 'bg-green-100 text-green-800' 
                                  : 'bg-yellow-100 text-yellow-800'
                              }`}>
                                {member.is_active ? 'Active' : 'Inactive'}
                              </span>
                              <span className="px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-800">
                                {member.role === 'compliance_team' ? 'Compliance Team' :
                                 member.role === 'it_team' ? 'IT Team' :
                                 member.role === 'management_team' ? 'Management Team' : member.role}
                              </span>
                            </div>
                            <div className="flex items-center space-x-2">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setEditingMember({
                                  id: member._id,
                                  firstName: member.first_name,
                                  lastName: member.last_name,
                                  role: member.role,
                                  isActive: member.is_active
                                })}
                              >
                                <FaEdit className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleDeleteMember(member._id)}
                              >
                                <FaTrash className="h-4 w-4 text-destructive" />
                              </Button>
                            </div>
                          </div>
                        </div>
                      </motion.div>
                    ))}
                  </motion.div>
                )}
              </div>
            </div>
          </motion.div>
        );
      case 'profile':
        return <Profile />;
      // ... other cases ...
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
          <h2 className="text-xl font-bold text-primary mb-6">Admin Panel</h2>
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
        </div>
      </motion.div>

      {/* Main Content */}
      <div className="flex-1">
        {renderContent()}
      </div>
    </div>
  );
};

export default AdminDashboard; 