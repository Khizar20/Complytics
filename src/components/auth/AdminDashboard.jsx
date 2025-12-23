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
  FaUser,
  FaHome
} from 'react-icons/fa';
import Profile from './Profile';
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
import { useToast } from "@/components/ui/toast";
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

const AdminDashboard = () => {
  const { authToken, logout, fetchWithRetry } = useAuth();
  const { toast } = useToast();
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
  const [deletionReason, setDeletionReason] = useState('');
  const [deletionRequest, setDeletionRequest] = useState(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [showBulkDeleteDialog, setShowBulkDeleteDialog] = useState(false);
  const [memberToDelete, setMemberToDelete] = useState(null);
  const [isAddingMember, setIsAddingMember] = useState(false);
  const [isEditingMember, setIsEditingMember] = useState(false);
  const [isRequestingDeletion, setIsRequestingDeletion] = useState(false);
  const [showRequestDeletionDialog, setShowRequestDeletionDialog] = useState(false);

  useEffect(() => {
    if (!authToken) {
      navigate('/login');
    } else {
      fetchTeamMembers();
    }
  }, [authToken, navigate]);

  useEffect(() => {
    const fetchDeletionRequest = async () => {
      try {
        if (!authToken) return;
        const res = await fetch(buildApiUrl('/admin/account-deletion-request'), {
          headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (res.ok) {
          const data = await res.json();
          setDeletionRequest(data);
        }
      } catch (e) {
        console.error('Failed to fetch deletion request', e);
      }
    };
    fetchDeletionRequest();
  }, [authToken]);

  const fetchTeamMembers = async () => {
    try {
      const response = await fetch(buildApiUrl('/admin/team-members'), {
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
      setIsAddingMember(true);
      const response = await fetch(buildApiUrl('/admin/create-team-member'), {
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

      const created = await response.json();
      toast({ title: 'Team member added', description: 'Credentials have been sent to their email.', variant: 'success' });
      setShowAddMemberForm(false);
      setNewMember({
        firstName: '',
        lastName: '',
        email: '',
        role: 'compliance_team'
      });
      // Optimistically update the list so it appears instantly
      setTeamMembers(prev => [
        {
          _id: created?._id || created?.id,
          first_name: created?.first_name ?? newMember.firstName,
          last_name: created?.last_name ?? newMember.lastName,
          email: created?.email ?? newMember.email,
          role: created?.role ?? newMember.role,
          is_active: typeof created?.is_active === 'boolean' ? created.is_active : true
        },
        ...prev
      ]);
      // Also re-fetch to ensure full sync with server state
      fetchTeamMembers();
    } catch (err) {
      toast({ title: 'Failed to add team member', description: err.message, variant: 'error' });
    } finally {
      setIsAddingMember(false);
    }
  };

  const handleDeleteMember = async (memberId) => {
    try {
      setIsDeleting(true);
      const response = await fetch(buildApiUrl(`/admin/team-members/${memberId}`), {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to delete team member');
      }

      toast({ title: 'Team member deleted', variant: 'success' });
      fetchTeamMembers();
    } catch (err) {
      toast({ title: 'Failed to delete member', description: err.message, variant: 'error' });
    } finally {
      setIsDeleting(false);
      setShowDeleteDialog(false);
      setMemberToDelete(null);
    }
  };

  const handleBulkDelete = async () => {
    if (selectedMembers.length === 0) {
      setError('Please select team members to delete');
      return;
    }

    try {
      setIsDeleting(true);
      const response = await fetch(buildApiUrl('/admin/team-members/bulk-delete'), {
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

      toast({ title: 'Deleted team members', description: `Removed ${selectedMembers.length} member(s)`, variant: 'success' });
      setSelectedMembers([]);
      fetchTeamMembers();
    } catch (err) {
      toast({ title: 'Failed to delete members', description: err.message, variant: 'error' });
    } finally {
      setIsDeleting(false);
      setShowBulkDeleteDialog(false);
    }
  };

  const handleEditMember = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    try {
      setIsEditingMember(true);
      const response = await fetch(buildApiUrl(`/admin/team-members/${editingMember.id}`), {
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

      toast({ title: 'Team member updated', variant: 'success' });
      setEditingMember(null);
      fetchTeamMembers();
    } catch (err) {
      toast({ title: 'Failed to update member', description: err.message, variant: 'error' });
    } finally {
      setIsEditingMember(false);
    }
  };

  const toggleMemberSelection = (memberId) => {
    setSelectedMembers(prev => 
      prev.includes(memberId) 
        ? prev.filter(id => id !== memberId)
        : [...prev, memberId]
    );
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleHome = () => {
    navigate('/');
  };

  const sidebarItems = [
    { id: 'dashboard', icon: <FaHome />, label: 'Dashboard', onClick: () => setActiveTab('dashboard') },
    { id: 'profile', icon: <FaUser />, label: 'Profile', onClick: () => setActiveTab('profile') },
    { id: 'delete-account', icon: <FaUserSlash />, label: 'Request Account Deletion', onClick: () => setActiveTab('delete-account') }
  ];

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5 }}
            className="min-h-screen"
          >
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
              {/* Header */}
              <motion.div 
                initial={{ y: -20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ duration: 0.5 }}
                className="flex justify-between items-start mb-10"
              >
                <div>
                  <h1 className="text-4xl md:text-5xl font-bold mb-4">
                    <span className="text-blue-600">Organization</span>{' '}
                    <span className="text-black">Dashboard</span>
                  </h1>
                  <p className="text-gray-600 text-lg font-medium">
                    Manage your team and organization settings
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
                className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-10"
                initial="hidden"
                animate="show"
                variants={containerVariants}
              >
                <motion.div 
                  variants={itemVariants}
                  className="bg-gradient-to-br from-white to-blue-50/50 p-5 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 relative overflow-hidden group border-2 border-blue-500/30 hover:border-blue-500/60"
                  whileHover={{ scale: 1.02, y: -3 }}
                >
                  <div className="absolute top-0 right-0 w-24 h-24 bg-blue-500/10 rounded-full blur-2xl -mr-12 -mt-12 group-hover:bg-blue-500/20 transition-all"></div>
                  <div className="relative z-10 flex items-center justify-between">
                    <div>
                      <p className="text-xs font-semibold text-gray-500 mb-1 uppercase tracking-wide">Total Team Members</p>
                      <h3 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-blue-500 bg-clip-text text-transparent">{teamMembers.length}</h3>
                    </div>
                    <div className="p-3 rounded-xl bg-gradient-to-br from-blue-600 to-blue-500 text-white shadow-md shadow-blue-500/30 group-hover:scale-105 transition-transform">
                      <FaUsers className="h-5 w-5" />
                    </div>
                  </div>
                </motion.div>

                <motion.div 
                  variants={itemVariants}
                  className="bg-gradient-to-br from-white to-green-50/50 p-5 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 relative overflow-hidden group border-2 border-green-500/30 hover:border-green-500/60"
                  whileHover={{ scale: 1.02, y: -3 }}
                >
                  <div className="absolute top-0 right-0 w-24 h-24 bg-green-500/10 rounded-full blur-2xl -mr-12 -mt-12 group-hover:bg-green-500/20 transition-all"></div>
                  <div className="relative z-10 flex items-center justify-between">
                    <div>
                      <p className="text-xs font-semibold text-gray-500 mb-1 uppercase tracking-wide">Active Members</p>
                      <h3 className="text-2xl font-bold bg-gradient-to-r from-green-600 to-green-500 bg-clip-text text-transparent">
                        {teamMembers.filter(member => member.is_active).length}
                      </h3>
                    </div>
                    <div className="p-3 rounded-xl bg-gradient-to-br from-green-600 to-green-500 text-white shadow-md shadow-green-500/30 group-hover:scale-105 transition-transform">
                      <FaUserTie className="h-5 w-5" />
                    </div>
                  </div>
                </motion.div>

                <motion.div 
                  variants={itemVariants}
                  className="bg-gradient-to-br from-white to-purple-50/50 p-5 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 relative overflow-hidden group border-2 border-purple-500/30 hover:border-purple-500/60"
                  whileHover={{ scale: 1.02, y: -3 }}
                >
                  <div className="absolute top-0 right-0 w-24 h-24 bg-purple-500/10 rounded-full blur-2xl -mr-12 -mt-12 group-hover:bg-purple-500/20 transition-all"></div>
                  <div className="relative z-10 flex items-center justify-between">
                    <div>
                      <p className="text-xs font-semibold text-gray-500 mb-1 uppercase tracking-wide">Inactive Members</p>
                      <h3 className="text-2xl font-bold bg-gradient-to-r from-purple-600 to-purple-500 bg-clip-text text-transparent">
                        {teamMembers.filter(member => !member.is_active).length}
                      </h3>
                    </div>
                    <div className="p-3 rounded-xl bg-gradient-to-br from-purple-600 to-purple-500 text-white shadow-md shadow-purple-500/30 group-hover:scale-105 transition-transform">
                      <FaUserSlash className="h-5 w-5" />
                    </div>
                  </div>
                </motion.div>
              </motion.div>

              {/* Messages */}
              {/* Inline success/error containers removed; toast notifications are used instead */}

              {/* Team Members Section */}
              <div className="bg-white/80 backdrop-blur-sm p-8 rounded-2xl shadow-xl">
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8 gap-4">
                  <h2 className="text-2xl font-bold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent">Team Members</h2>
                  <div className="flex flex-wrap gap-3">
                    {selectedMembers.length > 0 && (
                      <Button 
                        variant="destructive"
                        onClick={openBulkDeleteDialog}
                        className="flex items-center gap-2 bg-gradient-to-r from-red-600 to-red-500 hover:from-red-700 hover:to-red-600 text-white font-semibold shadow-lg shadow-red-500/30 rounded-xl px-5 py-2.5 transition-all hover:scale-105"
                      >
                        <FaTrash />
                        Delete Selected ({selectedMembers.length})
                      </Button>
                    )}
                    <Button 
                      onClick={() => setShowAddMemberForm(true)}
                      className="flex items-center gap-2 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-700 hover:to-blue-600 text-white font-semibold shadow-lg shadow-blue-500/30 rounded-xl px-5 py-2.5 transition-all hover:scale-105"
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
                      className="mb-8 p-8 bg-gradient-to-br from-blue-50/50 to-white rounded-2xl shadow-lg border border-blue-100"
                    >
                      <h3 className="text-xl font-bold text-gray-900 mb-6">Add New Team Member</h3>
                      <form onSubmit={handleAddMember} className="space-y-5">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                          <div>
                            <label className="block text-sm font-bold text-gray-700 mb-2">First Name</label>
                            <input
                              type="text"
                              value={newMember.firstName}
                              onChange={(e) => setNewMember({...newMember, firstName: e.target.value})}
                              className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all font-medium"
                              required
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-bold text-gray-700 mb-2">Last Name</label>
                            <input
                              type="text"
                              value={newMember.lastName}
                              onChange={(e) => setNewMember({...newMember, lastName: e.target.value})}
                              className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all font-medium"
                              required
                            />
                          </div>
                        </div>
                        <div>
                          <label className="block text-sm font-bold text-gray-700 mb-2">Email</label>
                          <input
                            type="email"
                            value={newMember.email}
                            onChange={(e) => setNewMember({...newMember, email: e.target.value})}
                            className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all font-medium"
                            required
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-bold text-gray-700 mb-2">Role</label>
                          <select
                            value={newMember.role}
                            onChange={(e) => setNewMember({...newMember, role: e.target.value})}
                            className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all font-medium bg-white"
                          >
                            <option value="compliance_team">Compliance Team</option>
                            <option value="it_team">IT Team</option>
                            <option value="management_team">Management Team</option>
                          </select>
                        </div>
                        <div className="flex justify-end gap-4 pt-4">
                          <Button
                            type="button"
                            variant="outline"
                            onClick={() => setShowAddMemberForm(false)}
                            className="border-2 border-gray-300 hover:bg-gray-50 rounded-xl px-6 py-2.5 font-semibold"
                          >
                            Cancel
                          </Button>
                          <Button 
                            type="submit" 
                            disabled={isAddingMember}
                            className="bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-700 hover:to-blue-600 text-white font-semibold shadow-lg shadow-blue-500/30 rounded-xl px-6 py-2.5 transition-all hover:scale-105"
                          >
                            {isAddingMember ? (
                              <span className="flex items-center gap-2"><FaSpinner className="animate-spin" /> Adding...</span>
                            ) : 'Add Member'}
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
                      className="mb-8 p-8 bg-gradient-to-br from-green-50/50 to-white rounded-2xl shadow-lg border border-green-100"
                    >
                      <h3 className="text-xl font-bold text-gray-900 mb-6">Edit Team Member</h3>
                      <form onSubmit={handleEditMember} className="space-y-5">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                          <div>
                            <label className="block text-sm font-bold text-gray-700 mb-2">First Name</label>
                            <input
                              type="text"
                              value={editingMember.firstName}
                              onChange={(e) => setEditingMember({...editingMember, firstName: e.target.value})}
                              className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all font-medium"
                              required
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-bold text-gray-700 mb-2">Last Name</label>
                            <input
                              type="text"
                              value={editingMember.lastName}
                              onChange={(e) => setEditingMember({...editingMember, lastName: e.target.value})}
                              className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all font-medium"
                              required
                            />
                          </div>
                        </div>
                        <div>
                          <label className="block text-sm font-bold text-gray-700 mb-2">Role</label>
                          <select
                            value={editingMember.role}
                            onChange={(e) => setEditingMember({...editingMember, role: e.target.value})}
                            className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all font-medium bg-white"
                          >
                            <option value="compliance_team">Compliance Team</option>
                            <option value="it_team">IT Team</option>
                            <option value="management_team">Management Team</option>
                          </select>
                        </div>
                        <div className="flex items-center gap-3 p-4 bg-gray-50 rounded-xl">
                          <input
                            type="checkbox"
                            id="isActive"
                            checked={editingMember.isActive}
                            onChange={(e) => setEditingMember({...editingMember, isActive: e.target.checked})}
                            className="h-5 w-5 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                          />
                          <label htmlFor="isActive" className="text-sm font-bold text-gray-700">
                            Active Member
                          </label>
                        </div>
                        <div className="flex justify-end gap-4 pt-4">
                          <Button
                            type="button"
                            variant="outline"
                            onClick={() => setEditingMember(null)}
                            className="border-2 border-gray-300 hover:bg-gray-50 rounded-xl px-6 py-2.5 font-semibold"
                          >
                            Cancel
                          </Button>
                          <Button 
                            type="submit" 
                            disabled={isEditingMember}
                            className="bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-700 hover:to-blue-600 text-white font-semibold shadow-lg shadow-blue-500/30 rounded-xl px-6 py-2.5 transition-all hover:scale-105"
                          >
                            {isEditingMember ? (
                              <span className="flex items-center gap-2"><FaSpinner className="animate-spin" /> Saving...</span>
                            ) : 'Save Changes'}
                          </Button>
                        </div>
                      </form>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Team Members List */}
                {isLoading ? (
                  <div className="flex justify-center py-12">
                    <FaSpinner className="animate-spin h-10 w-10 text-blue-600" />
                  </div>
                ) : teamMembers.length === 0 ? (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="text-center py-16"
                  >
                    <div className="mx-auto flex items-center justify-center w-20 h-20 bg-gradient-to-br from-blue-100 to-blue-200 rounded-2xl mb-6 shadow-lg">
                      <FaUsers className="h-10 w-10 text-blue-600" />
                    </div>
                    <h3 className="text-2xl font-bold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent">No team members yet</h3>
                    <p className="text-gray-600 mt-3 text-lg">
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
                        whileHover={{ y: -5, scale: 1.01 }}
                        className="bg-white/80 backdrop-blur-sm p-6 rounded-2xl shadow-lg hover:shadow-2xl transition-all duration-300 group relative overflow-hidden"
                      >
                        <div className="absolute inset-0 bg-gradient-to-r from-blue-500/0 via-blue-500/0 to-blue-500/0 group-hover:from-blue-500/5 group-hover:via-blue-500/5 group-hover:to-blue-500/5 transition-all duration-300"></div>
                        <div className="relative z-10">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-4">
                            <input
                              type="checkbox"
                              checked={selectedMembers.includes(member._id)}
                              onChange={() => toggleMemberSelection(member._id)}
                              className="h-5 w-5 text-blue-600 focus:ring-blue-500 border-gray-300 rounded cursor-pointer"
                            />
                            <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-blue-600 to-blue-500 flex items-center justify-center text-white shadow-lg">
                              <FaUserTie className="h-6 w-6" />
                            </div>
                            <div>
                              <h3 className="font-bold text-lg text-gray-900">
                                {member.first_name} {member.last_name}
                              </h3>
                              <p className="text-sm text-gray-600 font-medium">
                                {member.email}
                              </p>
                            </div>
                          </div>
                          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className={`px-3 py-1.5 text-xs rounded-full font-semibold border-2 ${
                                member.is_active 
                                  ? 'bg-green-100 text-green-800 border-green-500' 
                                  : 'bg-yellow-100 text-yellow-800 border-yellow-500'
                              }`}>
                                {member.is_active ? 'Active' : 'Inactive'}
                              </span>
                              <span className="px-3 py-1.5 text-xs rounded-full font-semibold bg-blue-100 text-blue-800 border-2 border-blue-500">
                                {member.role === 'compliance_team' ? 'Compliance Team' :
                                 member.role === 'it_team' ? 'IT Team' :
                                 member.role === 'management_team' ? 'Management Team' : member.role}
                              </span>
                            </div>
                            <div className="flex items-center gap-2">
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
                                className="hover:bg-blue-50 rounded-xl p-2.5"
                              >
                                <FaEdit className="h-5 w-5 text-blue-600" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => openDeleteDialog(member)}
                                className="hover:bg-red-50 rounded-xl p-2.5"
                              >
                                <FaTrash className="h-5 w-5 text-red-600" />
                              </Button>
                            </div>
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
      case 'delete-account':
        return (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5 }}
            className="min-h-screen"
          >
            <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
              <div className="bg-white/80 backdrop-blur-sm p-8 rounded-2xl shadow-xl relative overflow-hidden group">
                <div className="absolute top-0 right-0 w-40 h-40 bg-red-500/10 rounded-full blur-3xl -mr-20 -mt-20"></div>
                <div className="relative z-10">
                  <div className="flex items-center gap-4 mb-6">
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-red-600 to-red-500 flex items-center justify-center shadow-lg">
                      <FaUserSlash className="h-6 w-6 text-white" />
                    </div>
                    <div>
                      <h2 className="text-2xl font-bold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent">Request Account Deletion</h2>
                      <p className="text-sm text-gray-600 font-medium mt-1">Submit a request to permanently delete your account</p>
                    </div>
                  </div>

                  {deletionRequest?.status === 'pending' ? (
                    <div className="p-5 bg-gradient-to-r from-yellow-50 to-yellow-100 border-l-4 border-yellow-500 text-yellow-800 rounded-xl mb-6 font-semibold shadow-lg flex items-start gap-3">
                      <div className="mt-0.5">
                        <FaSpinner className="animate-spin h-5 w-5" />
                      </div>
                      <div>
                        <p className="font-bold mb-1">Request Pending</p>
                        <p className="text-sm font-medium">Your deletion request is pending superadmin review.</p>
                      </div>
                    </div>
                  ) : deletionRequest?.status === 'rejected' ? (
                    <div className="p-5 bg-gradient-to-r from-red-50 to-red-100 border-l-4 border-red-500 text-red-800 rounded-xl mb-6 font-semibold shadow-lg flex items-start gap-3">
                      <div className="mt-0.5">
                        <FaTimesCircle className="h-5 w-5" />
                      </div>
                      <div>
                        <p className="font-bold mb-1">Request Rejected</p>
                        <p className="text-sm font-medium">Your previous deletion request was rejected. You may submit a new request.</p>
                      </div>
                    </div>
                  ) : (
                    <div className="p-5 bg-gradient-to-r from-blue-50 to-blue-100 border-l-4 border-blue-500 rounded-xl mb-6 shadow-lg">
                      <p className="text-sm font-semibold text-blue-800 mb-2">⚠️ Important Notice</p>
                      <ul className="text-sm text-blue-700 space-y-1 list-disc list-inside">
                        <li>This action will permanently delete your account and all associated data</li>
                        <li>All team members under your organization will also be affected</li>
                        <li>This action cannot be undone</li>
                      </ul>
                    </div>
                  )}

                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-bold text-gray-700 mb-3">Reason for Deletion (optional)</label>
                      <textarea
                        value={deletionReason}
                        onChange={(e) => setDeletionReason(e.target.value)}
                        className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-red-500 focus:border-red-500 transition-all font-medium resize-none"
                        rows={6}
                        placeholder="Please provide a reason for account deletion (optional)..."
                      />
                    </div>

                    <Button
                      className="w-full bg-gradient-to-r from-red-600 to-red-500 hover:from-red-700 hover:to-red-600 text-white font-semibold shadow-lg shadow-red-500/30 rounded-xl py-6 text-lg transition-all hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                      disabled={isRequestingDeletion || deletionRequest?.status === 'pending'}
                      onClick={() => setShowRequestDeletionDialog(true)}
                    >
                      {deletionRequest?.status === 'pending' ? (
                        <span className="flex items-center justify-center gap-2">
                          <FaSpinner className="animate-spin" />
                          Request Pending
                        </span>
                      ) : isRequestingDeletion ? (
                        <span className="flex items-center justify-center gap-2">
                          <FaSpinner className="animate-spin" />
                          Submitting...
                        </span>
                      ) : (
                        <span className="flex items-center justify-center gap-2">
                          <FaUserSlash />
                          Submit Deletion Request
                        </span>
                      )}
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        );
      default:
        return null;
    }
  };

  const openDeleteDialog = (member) => {
    setMemberToDelete(member);
    setShowDeleteDialog(true);
  };

  const openBulkDeleteDialog = () => {
    if (selectedMembers.length === 0) {
      setError('Please select team members to delete');
      return;
    }
    setShowBulkDeleteDialog(true);
  };

  return (
    <>
      <div className="flex min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-50/50">
        {/* Sidebar */}
        <motion.div
          initial={{ x: -100, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={{ duration: 0.5 }}
          className={`fixed top-0 left-0 h-screen bg-gradient-to-b from-gray-900 via-black to-gray-900 backdrop-blur-xl shadow-2xl z-[100] transition-all duration-300 ${
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
                  className={`w-full flex items-center justify-start text-left space-x-3 p-3 rounded-xl transition-all duration-300 font-semibold ${
                    activeTab === item.id
                      ? 'bg-gradient-to-r from-gray-700 to-gray-600 text-white shadow-lg shadow-gray-700/50'
                      : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                  }`}
                >
                  <span className="text-lg">{item.icon}</span>
                  {isSidebarOpen && <span className="text-left">{item.label}</span>}
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
          {renderContent()}
        </div>
      </div>

      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirm Deletion</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete {memberToDelete?.first_name} {memberToDelete?.last_name}?
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction 
              onClick={() => handleDeleteMember(memberToDelete?._id)}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? (
                <FaSpinner className="animate-spin mr-2" />
              ) : (
                <FaTrash className="mr-2" />
              )}
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={showBulkDeleteDialog} onOpenChange={setShowBulkDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirm Bulk Deletion</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete {selectedMembers.length} selected team members?
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction 
              onClick={handleBulkDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? (
                <FaSpinner className="animate-spin mr-2" />
              ) : (
                <FaTrash className="mr-2" />
              )}
              Delete All
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Confirm admin account deletion request */}
      <AlertDialog open={showRequestDeletionDialog} onOpenChange={setShowRequestDeletionDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirm Account Deletion Request</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to send an account deletion request to the superadmin? You will be signed out once approved.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction 
              onClick={async () => {
                setError('');
                setSuccess('');
                setIsRequestingDeletion(true);
                try {
                  const res = await fetch(buildApiUrl('/admin/request-account-deletion'), {
                    method: 'POST',
                    headers: {
                      'Content-Type': 'application/json',
                      'Authorization': `Bearer ${authToken}`
                    },
                    body: JSON.stringify({ reason: deletionReason })
                  });
                  const data = await res.json();
                  if (!res.ok) {
                    throw new Error(data.detail || 'Failed to request account deletion');
                  }
                  setDeletionRequest(data);
                  setSuccess('Deletion request submitted. The superadmin will review it.');
                  setDeletionReason('');
                } catch (e) {
                  setError(e.message);
                } finally {
                  setIsRequestingDeletion(false);
                  setShowRequestDeletionDialog(false);
                }
              }}
            >
              {isRequestingDeletion ? <FaSpinner className="animate-spin" /> : 'Confirm'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
};

export default AdminDashboard; 