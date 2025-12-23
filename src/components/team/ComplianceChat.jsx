import React, { useState, useEffect, useRef } from 'react';
import { 
  Box, 
  TextField, 
  Button, 
  Paper, 
  Typography, 
  CircularProgress, 
  IconButton,
  Avatar,
  Divider,
  useTheme,
  alpha,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Drawer,
  useMediaQuery,
  Menu,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Select,
  FormControl,
  InputLabel,
  Tooltip,
  Chip,
  Fade,
  Zoom
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import RefreshIcon from '@mui/icons-material/Refresh';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import PersonIcon from '@mui/icons-material/Person';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import DeleteIcon from '@mui/icons-material/Delete';
import MenuIcon from '@mui/icons-material/Menu';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import PolicyIcon from '@mui/icons-material/Policy';
import DescriptionIcon from '@mui/icons-material/Description';
import ThumbUpIcon from '@mui/icons-material/ThumbUp';
import ThumbDownIcon from '@mui/icons-material/ThumbDown';
import ThumbUpOffAltIcon from '@mui/icons-material/ThumbUpOffAlt';
import ThumbDownOffAltIcon from '@mui/icons-material/ThumbDownOffAlt';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import SecurityIcon from '@mui/icons-material/Security';
import { useAuth } from '../../context/AuthContext';
import { motion, AnimatePresence } from 'framer-motion';
import { buildApiUrl } from '@/lib/api';
import { useNavigate } from 'react-router-dom';
import FormattedResponse from '@/components/ui/FormattedResponse';
import ComplianceChatFormattedResponse from '@/components/ui/ComplianceChatFormattedResponse';


// Typing effect component
const TypewriterText = ({ text, onComplete }) => {
  const [displayedText, setDisplayedText] = useState('');
  const [currentIndex, setCurrentIndex] = useState(0);
  const theme = useTheme();

  // Add check for undefined text
  if (!text) {
    return null;
  }

  useEffect(() => {
    if (currentIndex < text.length) {
      let delay = 5;
      
      if (['.', '!', '?', '\n'].includes(text[currentIndex])) {
        delay = 15;
      } 
      else if ([' ', 'e', 't', 'a', 'o', 'i'].includes(text[currentIndex].toLowerCase())) {
        delay = 2;
      }
      
      delay += Math.random() * 3;

      const chunkSize = 3;
      if (currentIndex + chunkSize < text.length) {
        const timeout = setTimeout(() => {
          setDisplayedText(prev => prev + text.slice(currentIndex, currentIndex + chunkSize));
          setCurrentIndex(prev => prev + chunkSize);
        }, delay);
        return () => clearTimeout(timeout);
      } else {
        const timeout = setTimeout(() => {
          setDisplayedText(prev => prev + text[currentIndex]);
          setCurrentIndex(prev => prev + 1);
        }, delay);
        return () => clearTimeout(timeout);
      }
    } else {
      onComplete?.();
    }
  }, [currentIndex, text, onComplete]);

  return (
    <Box sx={{ width: '100%' }}>
      {currentIndex < text.length ? (
        <Box sx={{ 
          whiteSpace: 'pre-wrap',
          fontFamily: 'DM Sans, sans-serif',
          lineHeight: 1.6
        }}>
          <ComplianceChatFormattedResponse content={displayedText} />
          <motion.span
            animate={{ opacity: [1, 0] }}
            transition={{ duration: 0.4, repeat: Infinity }}
            style={{ marginLeft: 2 }}
          >
            |
          </motion.span>
        </Box>
      ) : (
        <ComplianceChatFormattedResponse content={text} />
      )}
    </Box>
  );
};

const ComplianceChat = () => {
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [isTyping, setIsTyping] = useState(false);
  const [sessionHistory, setSessionHistory] = useState([]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true); // Desktop sidebar state
  const [allChatHistory, setAllChatHistory] = useState([]);
  const messagesEndRef = useRef(null);
  const { authToken, fetchWithRetry } = useAuth();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);
  const [analysisDialogOpen, setAnalysisDialogOpen] = useState(false);
  const [generationDialogOpen, setGenerationDialogOpen] = useState(false);
  const [selectedFramework, setSelectedFramework] = useState('');
  const [selectedFormat, setSelectedFormat] = useState('docx');
  const [analysisResult, setAnalysisResult] = useState(null);
  const [generatedPolicy, setGeneratedPolicy] = useState(null);
  const [documentType, setDocumentType] = useState('privacy');
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [messageFeedback, setMessageFeedback] = useState({}); // Track feedback for each message
  const [pendingAttachment, setPendingAttachment] = useState(null); // File attached to next send
  
  const DRAWER_WIDTH = 320;

  const frameworks = [
    'GDPR',
    'CCPA',
    'HIPAA',
    'ISO 27001',
    'SOC 2',
    'NIST',
    'PCI DSS'
  ];

  const formats = ['docx', 'pdf', 'txt'];

  useEffect(() => {
    const loadInitialData = async () => {
      if (authToken) {
        try {
          // Load all chat history first
          await loadAllChatHistory();
          
          // Create new session only if no session exists
          if (!sessionId) {
            const newSessionId = Date.now().toString();
            setSessionId(newSessionId);
          }
        } catch (error) {
          console.error('Error loading initial data:', error);
        }
      }
    };
    
    loadInitialData();
  }, [authToken]);

  const loadSessionHistory = async (currentSessionId) => {
    try {
      const response = await fetchWithRetry(buildApiUrl(`/api/compliance/history?session_id=${currentSessionId}`));
      const data = await response.json();
      
      if (!data.history || !Array.isArray(data.history) || data.history.length === 0) {
        setSessionHistory([]);
        setMessages([]);
        return;
      }
      
      // The backend already filters for the current session, so we can use the data directly
      setSessionHistory(data.history);
      
      // Format messages for display
      const formattedMessages = [];
      data.history.forEach(item => {
        if (item.query) {
          formattedMessages.push({
            type: 'user',
            content: item.query,
            timestamp: new Date(item.timestamp)
          });
        }
        if (item.response) {
          formattedMessages.push({
            type: 'response',
            content: item.response,
            experts: item.experts_consulted,
            timestamp: new Date(item.timestamp),
            isTyping: false
          });
        }
      });
      
      // Sort messages by timestamp
      formattedMessages.sort((a, b) => a.timestamp - b.timestamp);
      setMessages(formattedMessages);
      
      // Scroll to bottom after loading messages
      setTimeout(scrollToBottom, 100);
      
      // Debug log
      console.log('Loaded session history:', {
        sessionId: currentSessionId,
        messageCount: formattedMessages.length
      });
    } catch (error) {
      console.error('Error loading session history:', error);
      setSessionHistory([]);
      setMessages([]);
    }
  };

  const loadAllChatHistory = async () => {
    try {
      const response = await fetchWithRetry(buildApiUrl('/api/compliance/all-history'));
      const data = await response.json();
      
      if (!data.history || !Array.isArray(data.history)) {
        console.error('Invalid history data received:', data);
        setAllChatHistory([]);
        return;
      }

      // Process and validate each session
      const validSessions = data.history
        .filter(session => 
          session && 
          session.session_id && 
          Array.isArray(session.messages) && 
          session.messages.length > 0
        )
        .map(session => ({
          ...session,
          timestamp: new Date(session.timestamp),
          messages: session.messages.map(msg => ({
            ...msg,
            timestamp: new Date(msg.timestamp)
          }))
        }));

      // Remove any duplicate sessions
      const uniqueSessions = validSessions.reduce((acc, current) => {
        const existingIndex = acc.findIndex(session => session.session_id === current.session_id);
        if (existingIndex >= 0) {
          // If session exists, keep the one with more recent timestamp
          if (current.timestamp > acc[existingIndex].timestamp) {
            acc[existingIndex] = current;
          }
        } else {
          acc.push(current);
        }
        return acc;
      }, []);

      // Sort by timestamp (most recent first)
      const sortedHistory = uniqueSessions.sort((a, b) => b.timestamp - a.timestamp);
      
      setAllChatHistory(sortedHistory);
      
      // Debug log
      console.log('Loaded chat history:', {
        totalSessions: sortedHistory.length,
        currentSessionId: sessionId,
        sessions: sortedHistory.map(s => ({
          id: s.session_id,
          messageCount: s.messages.length,
          timestamp: s.timestamp
        }))
      });
    } catch (error) {
      console.error('Error loading chat history:', error);
      setAllChatHistory([]);
    }
  };

  const handleLoadPreviousSession = async (sessionToLoad) => {
    if (!sessionToLoad?.session_id || !Array.isArray(sessionToLoad.messages)) {
      console.error('Invalid session data:', sessionToLoad);
      return;
    }
    
    // Set the session ID to the previous session's ID
    setSessionId(sessionToLoad.session_id);
    setLoading(true);
    try {
      // Format the existing messages from the session
      const formattedMessages = [];
      const validMessages = sessionToLoad.messages.filter(item => item && (item.query || item.response));
      
      validMessages.forEach(item => {
        if (item.query) {
          formattedMessages.push({
            type: 'user',
            content: item.query,
            timestamp: new Date(item.timestamp)
          });
        }
        if (item.response) {
          formattedMessages.push({
            type: 'response',
            content: item.response,
            experts: item.experts_consulted,
            timestamp: new Date(item.timestamp),
            isTyping: false
          });
        }
      });
      
      // Sort messages by timestamp
      formattedMessages.sort((a, b) => a.timestamp - b.timestamp);
      
      // Update states
      setMessages(formattedMessages);
      setSessionHistory(validMessages);
      
      // Scroll to bottom
      setTimeout(scrollToBottom, 100);
      
      // Debug log
      console.log('Loaded previous session:', {
        sessionId: sessionToLoad.session_id,
        messageCount: formattedMessages.length,
        messages: formattedMessages
      });
    } catch (error) {
      console.error('Error loading previous session:', error);
      setMessages([]);
      setSessionHistory([]);
    } finally {
      setLoading(false);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if ((!input.trim()) || !authToken) return;

    const userMessage = {
      type: 'user',
      content: input,
      timestamp: new Date(),
      attachments: pendingAttachment ? [pendingAttachment] : []
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setPendingAttachment(null);
    setLoading(true);
    setIsTyping(true);

    try {
      const response = await fetchWithRetry(buildApiUrl('/api/compliance/chat'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          query: input,
          session_id: sessionId // Using the current sessionId, whether it's a new or existing session
        })
      });
      
      const data = await response.json();

      const botMessage = {
        type: 'response',
        content: data.response,
        experts: data.experts_consulted,
        timestamp: new Date(),
        isTyping: true,
        originalQuery: input // Store the original query for feedback
      };

      setMessages(prev => [...prev, botMessage]);
      
      // Update session history
      const newHistoryItem = {
        query: input,
        response: data.response,
        experts_consulted: data.experts_consulted,
        timestamp: new Date(),
        session_id: sessionId
      };
      
      setSessionHistory(prev => [...prev, newHistoryItem]);

      // Update all chat history to reflect the new message in the current session
      setAllChatHistory(prev => {
        const updatedHistory = [...prev];
        const sessionIndex = updatedHistory.findIndex(session => session.session_id === sessionId);
        
        if (sessionIndex !== -1) {
          // Update existing session
          updatedHistory[sessionIndex] = {
            ...updatedHistory[sessionIndex],
            messages: [...updatedHistory[sessionIndex].messages, newHistoryItem],
            timestamp: new Date() // Update session timestamp
          };
        } else {
          // Only create new session if it doesn't exist (should not happen normally)
          console.warn('Session not found in history:', sessionId);
          updatedHistory.unshift({
            session_id: sessionId,
            messages: [newHistoryItem],
            timestamp: new Date()
          });
        }
        
        // Sort sessions by timestamp (most recent first)
        updatedHistory.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
        
        return updatedHistory;
      });

      // Debug log
      console.log('Message sent:', {
        sessionId,
        messageCount: messages.length + 2,
        allChatHistoryCount: allChatHistory.length
      });
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages(prev => [...prev, {
        type: 'error',
        content: 'Sorry, there was an error processing your request.',
        timestamp: new Date()
      }]);
    } finally {
      setLoading(false);
      setIsTyping(false);
    }
  };

  const handleReset = async () => {
    if (!authToken) return;
    try {
      await fetchWithRetry(buildApiUrl('/api/compliance/reset'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          session_id: sessionId
        })
      });
      
      // Create new session
      const newSessionId = Date.now().toString();
      setSessionId(newSessionId);
      setMessages([]);
      setSessionHistory([]);
      
      // Reload chat history
      await loadAllChatHistory();
    } catch (error) {
      console.error('Error resetting chat:', error);
    }
  };

  const handleTypingComplete = (index) => {
    setMessages(prev => prev.map((msg, i) => 
      i === index ? { ...msg, isTyping: false } : msg
    ));
    setIsTyping(false);
  };

  // Add feedback handling functions
  const handleFeedback = async (messageIndex, isHelpful, originalQuery) => {
    try {
      await fetchWithRetry(buildApiUrl('/api/compliance/feedback'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          query: originalQuery,
          was_helpful: isHelpful,
          session_id: sessionId
        })
      });
      
      // Update local feedback state
      setMessageFeedback(prev => ({
        ...prev,
        [messageIndex]: isHelpful
      }));
      
      console.log('Feedback submitted:', { messageIndex, isHelpful, query: originalQuery });
    } catch (error) {
      console.error('Error submitting feedback:', error);
    }
  };

  const getFeedbackButtons = (messageIndex, originalQuery) => {
    const currentFeedback = messageFeedback[messageIndex];
    
    return (
      <Box sx={{ 
        display: 'flex', 
        gap: 1.5, 
        mt: 2, 
        pt: 2,
        borderTop: `1.5px solid ${alpha(theme.palette.divider, 0.12)}`,
        justifyContent: 'flex-start',
        opacity: 0.8,
        '&:hover': { opacity: 1 },
        transition: 'opacity 0.3s ease'
      }}>
        <Tooltip title={currentFeedback === true ? "You found this helpful" : "Mark as helpful"} arrow placement="top">
          <IconButton 
            size="small"
            onClick={() => handleFeedback(messageIndex, true, originalQuery)}
            disabled={currentFeedback !== undefined}
            sx={{ 
              color: currentFeedback === true ? theme.palette.success.main : theme.palette.text.secondary,
              bgcolor: currentFeedback === true 
                ? `linear-gradient(135deg, ${alpha(theme.palette.success.main, 0.15)} 0%, ${alpha(theme.palette.success.main, 0.1)} 100%)`
                : alpha(theme.palette.action.hover, 0.05),
              border: `1.5px solid ${currentFeedback === true ? theme.palette.success.main : alpha(theme.palette.divider, 0.2)}`,
              borderRadius: 2,
              px: 1.5,
              py: 0.8,
              '&:hover': { 
                bgcolor: currentFeedback === true 
                  ? `linear-gradient(135deg, ${alpha(theme.palette.success.main, 0.25)} 0%, ${alpha(theme.palette.success.main, 0.18)} 100%)`
                  : alpha(theme.palette.success.main, 0.1),
                borderColor: currentFeedback === true ? theme.palette.success.main : theme.palette.success.main,
                transform: 'translateY(-2px)',
                boxShadow: `0 4px 12px ${alpha(theme.palette.success.main, 0.2)}`
              },
              '&:disabled': {
                opacity: currentFeedback === true ? 1 : 0.6
              },
              transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
            }}
          >
            {currentFeedback === true ? <ThumbUpIcon fontSize="small" sx={{ fontSize: 18 }} /> : <ThumbUpOffAltIcon fontSize="small" sx={{ fontSize: 18 }} />}
          </IconButton>
        </Tooltip>
        <Tooltip title={currentFeedback === false ? "You marked this as not helpful" : "Mark as not helpful"} arrow placement="top">
          <IconButton 
            size="small"
            onClick={() => handleFeedback(messageIndex, false, originalQuery)}
            disabled={currentFeedback !== undefined}
            sx={{ 
              color: currentFeedback === false ? theme.palette.error.main : theme.palette.text.secondary,
              bgcolor: currentFeedback === false 
                ? `linear-gradient(135deg, ${alpha(theme.palette.error.main, 0.15)} 0%, ${alpha(theme.palette.error.main, 0.1)} 100%)`
                : alpha(theme.palette.action.hover, 0.05),
              border: `1.5px solid ${currentFeedback === false ? theme.palette.error.main : alpha(theme.palette.divider, 0.2)}`,
              borderRadius: 2,
              px: 1.5,
              py: 0.8,
              '&:hover': { 
                bgcolor: currentFeedback === false 
                  ? `linear-gradient(135deg, ${alpha(theme.palette.error.main, 0.25)} 0%, ${alpha(theme.palette.error.main, 0.18)} 100%)`
                  : alpha(theme.palette.error.main, 0.1),
                borderColor: currentFeedback === false ? theme.palette.error.main : theme.palette.error.main,
                transform: 'translateY(-2px)',
                boxShadow: `0 4px 12px ${alpha(theme.palette.error.main, 0.2)}`
              },
              '&:disabled': {
                opacity: currentFeedback === false ? 1 : 0.6
              },
              transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
            }}
          >
            {currentFeedback === false ? <ThumbDownIcon fontSize="small" sx={{ fontSize: 18 }} /> : <ThumbDownOffAltIcon fontSize="small" sx={{ fontSize: 18 }} />}
          </IconButton>
        </Tooltip>
      </Box>
    );
  };

  // Add a function to handle returning to dashboard
  const handleBackToDashboard = () => {
    // Instead of using navigate, we'll update the parent component's state
    if (window.location.pathname === '/team-dashboard') {
      // If we're already in the dashboard, just update the activeTab
      window.dispatchEvent(new CustomEvent('setActiveTab', { detail: 'dashboard' }));
    } else {
      // If we're somehow not in the dashboard, navigate there
      navigate('/team-dashboard');
    }
  };

  // Handle file downloads
  const handleDownload = async (url, filename) => {
    try {
      const response = await fetchWithRetry(url);
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename || 'document';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
    } catch (error) {
      console.error('Error downloading file:', error);
      // Fallback to opening in new tab
      window.open(url, '_blank');
    }
  };

  // Add click handler for download links in messages
  useEffect(() => {
    const handleLinkClick = (event) => {
      const target = event.target;
      if (target.tagName === 'A') {
        const hrefAttr = target.getAttribute('href') || target.href;
        if (hrefAttr && hrefAttr.includes('/api/compliance/download/')) {
        event.preventDefault();
        const filename = hrefAttr.split('/').pop();
        const fullUrl = buildApiUrl(hrefAttr);
        handleDownload(fullUrl, filename);
        }
      }
    };

    document.addEventListener('click', handleLinkClick);
    return () => {
      document.removeEventListener('click', handleLinkClick);
    };
  }, []);

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Check file type
    const validTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
    if (!validTypes.includes(file.type)) {
      alert('Please upload a PDF or DOCX file');
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('session_id', sessionId);
    if (input && input.trim()) {
      formData.append('query', input.trim());
    }

    try {
      const response = await fetch(buildApiUrl('/api/compliance/upload-document'), {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('authToken')}`
        },
        body: formData
      });

      const data = await response.json();

      if (!response.ok) {
        // Handle document type rejection
        if (data.detail && data.detail.type === 'INVALID_DOCUMENT_TYPE') {
          // Display user-friendly error in chat
          const errorMessage = {
            type: 'response',
            content: data.detail.message || 'This document type is not supported.',
            timestamp: new Date(),
            isTyping: false
          };
          setMessages(prev => [...prev, errorMessage]);
          scrollToBottom();
          return;
        }
        
        // Handle PDF extraction failure
        if (data.detail && data.detail.type === 'PDF_EXTRACTION_FAILED') {
          // Display user-friendly error in chat with suggestions
          let errorContent = `**${data.detail.title || 'PDF Extraction Failed'}**\n\n${data.detail.message || 'Unable to extract text from the PDF document.'}`;
          
          if (data.detail.suggestions && Array.isArray(data.detail.suggestions)) {
            errorContent += '\n\n**Suggestions:**\n';
            data.detail.suggestions.forEach((suggestion, index) => {
              errorContent += `${index + 1}. ${suggestion}\n`;
            });
          }
          
          const errorMessage = {
            type: 'response',
            content: errorContent,
            timestamp: new Date(),
            isTyping: false
          };
          setMessages(prev => [...prev, errorMessage]);
          scrollToBottom();
          return;
        }
        
        throw new Error(data.detail?.message || data.detail?.title || 'Upload failed');
      }

      // Store pending attachment to be sent with the next user message
      if (data && data.attachment) {
        setPendingAttachment(data.attachment);
      }
    } catch (error) {
      console.error('Error uploading document:', error);
      alert(error.message || 'Error uploading document. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const handlePrivacyPolicyAnalysis = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Check file type
    const validTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
    if (!validTypes.includes(file.type)) {
      alert('Please upload a PDF or DOCX file');
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('framework', selectedFramework);

    try {
      const response = await fetchWithRetry(buildApiUrl('/api/compliance/analyze-privacy-policy'), {
        method: 'POST',
        body: formData
      });

      const data = await response.json();
      setAnalysisResult(data.analysis);
      
      // Add system message about analysis
      const systemMessage = {
        type: 'response',
        content: `Privacy policy analysis against ${selectedFramework} completed. Here are the findings:\n\n${data.analysis}`,
        timestamp: new Date(),
        isTyping: false
      };

      setMessages(prev => [...prev, systemMessage]);
      scrollToBottom();
    } catch (error) {
      console.error('Error analyzing privacy policy:', error);
      alert('Error analyzing privacy policy. Please try again.');
    } finally {
      setUploading(false);
      setAnalysisDialogOpen(false);
    }
  };

  const handleGenerateDocument = async () => {
    setUploading(true);
    const formData = new FormData();
    formData.append('framework', selectedFramework);
    formData.append('format', selectedFormat);

    try {
      const endpoint = documentType === 'privacy' 
        ? buildApiUrl('/api/compliance/generate-privacy-policy')
        : buildApiUrl('/api/compliance/generate-terms');

      const response = await fetchWithRetry(endpoint, {
        method: 'POST',
        body: formData
      });

      const data = await response.json();
      setGeneratedPolicy(data.policy || data.terms);
      setDownloadUrl(data.download_url);
      
      // Add system message about generation
      const systemMessage = {
        type: 'response',
        content: `Generated ${documentType === 'privacy' ? 'privacy policy' : 'terms and conditions'} for ${selectedFramework}:\n\n${data.policy || data.terms}`,
        timestamp: new Date(),
        isTyping: false
      };

      setMessages(prev => [...prev, systemMessage]);
      scrollToBottom();
    } catch (error) {
      console.error(`Error generating ${documentType === 'privacy' ? 'privacy policy' : 'terms and conditions'}:`, error);
      alert(`Error generating ${documentType === 'privacy' ? 'privacy policy' : 'terms and conditions'}. Please try again.`);
    } finally {
      setUploading(false);
      setGenerationDialogOpen(false);
    }
  };

  const ChatSidebar = () => (
    <Box sx={{ position: 'relative' }}>
      <Drawer
        variant={isMobile ? "temporary" : "persistent"}
        open={isMobile ? drawerOpen : sidebarOpen}
        onClose={() => isMobile ? setDrawerOpen(false) : setSidebarOpen(false)}
        sx={{
          width: DRAWER_WIDTH,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: DRAWER_WIDTH,
            position: 'relative',
            height: '100vh',
            top: 0,
            boxSizing: 'border-box',
            background: `linear-gradient(180deg, #1e40af 0%, #1e3a8a 50%, #1e3a8a 100%)`,
            backdropFilter: 'blur(20px)',
            border: 'none',
            borderRight: `1px solid ${alpha('#ffffff', 0.1)}`,
            boxShadow: `inset -1px 0 0 ${alpha('#ffffff', 0.05)}, 4px 0 20px ${alpha('#000000', 0.2)}`,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          },
        }}
      >
      <Box sx={{ 
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        overflow: 'hidden'
      }}>
        <Box sx={{ 
          px: 2,
          py: 2.2,
          height: '80.44px',
          flexShrink: 0,
          borderBottom: `1px solid ${alpha('#ffffff', 0.15)}`,
          background: `linear-gradient(135deg, ${alpha('#3b82f6', 0.3)} 0%, ${alpha('#2563eb', 0.2)} 100%)`,
          display: 'flex',
          flexDirection: 'row',
          gap: 1.5,
          alignItems: 'center',
          boxSizing: 'border-box'
        }}>
          <Tooltip title="Back to Dashboard" arrow>
            <IconButton
              onClick={handleBackToDashboard}
              sx={{ 
                border: `1px solid ${alpha('#ffffff', 0.3)}`,
                color: '#ffffff',
                '&:hover': {
                  borderColor: '#ffffff',
                  bgcolor: alpha('#ffffff', 0.15),
                  color: '#ffffff'
                }
              }}
            >
              <ArrowBackIcon />
            </IconButton>
          </Tooltip>
          <Button
            fullWidth
            variant="contained"
            startIcon={<RefreshIcon />}
            onClick={handleReset}
            sx={{ 
              background: `linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)`,
              color: 'white',
              fontFamily: 'Montserrat, sans-serif',
              fontWeight: 600,
              textTransform: 'none',
              py: 1,
              boxShadow: `0 4px 12px ${alpha('#3b82f6', 0.4)}`,
              '&:hover': {
                background: `linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)`,
                boxShadow: `0 6px 16px ${alpha('#3b82f6', 0.5)}`,
                transform: 'translateY(-1px)'
              },
              transition: 'all 0.3s ease'
            }}
          >
            New Chat
          </Button>
        </Box>
        <Box sx={{ 
          flex: 1,
          minHeight: 0,
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column'
        }}>
          <List sx={{ 
            overflowY: 'auto', 
            overflowX: 'hidden',
            flex: 1,
            minHeight: 0,
            p: 2,
            '&::-webkit-scrollbar': {
              width: '6px',
            },
            '&::-webkit-scrollbar-track': {
              background: 'transparent',
            },
            '&::-webkit-scrollbar-thumb': {
              background: alpha('#ffffff', 0.3),
              borderRadius: '3px',
              '&:hover': {
                background: alpha('#ffffff', 0.5),
              }
            },
          }}>
        <Typography
          variant="overline"
          sx={{
            color: alpha('#ffffff', 0.7),
            fontWeight: 700,
            pl: 2,
            fontFamily: 'Montserrat, sans-serif',
            letterSpacing: 1.2,
            fontSize: '0.7rem'
          }}
        >
          Current Session
        </Typography>
        {sessionHistory.length > 0 && (() => {
          const firstQuery = sessionHistory.find(msg => msg?.query && typeof msg.query === 'string');
          return firstQuery && (
            <ListItem
              sx={{
                borderRadius: 2,
                mb: 0.5,
                mt: 1,
                background: `linear-gradient(135deg, ${alpha('#ffffff', 0.15)} 0%, ${alpha('#ffffff', 0.1)} 100%)`,
                border: `1px solid ${alpha('#ffffff', 0.2)}`,
                '&:hover': {
                  background: `linear-gradient(135deg, ${alpha('#ffffff', 0.25)} 0%, ${alpha('#ffffff', 0.18)} 100%)`,
                  transform: 'translateX(4px)',
                  boxShadow: `0 4px 12px ${alpha('#000000', 0.2)}`
                },
                transition: 'all 0.3s ease',
                cursor: 'pointer'
              }}
            >
              <ListItemIcon sx={{ minWidth: 36 }}>
                <SmartToyIcon fontSize="small" sx={{ color: '#ffffff' }} />
              </ListItemIcon>
              <ListItemText
                primary={firstQuery.query.substring(0, 30) + (firstQuery.query.length > 30 ? '...' : '')}
                secondary={new Date(firstQuery.timestamp).toLocaleTimeString()}
                primaryTypographyProps={{
                  noWrap: true,
                  fontSize: '0.875rem',
                  fontFamily: 'DM Sans, sans-serif',
                  fontWeight: 600,
                  color: '#ffffff'
                }}
                secondaryTypographyProps={{
                  fontSize: '0.7rem',
                  fontFamily: 'DM Sans, sans-serif',
                  color: alpha('#ffffff', 0.7)
                }}
              />
            </ListItem>
          );
        })()}

        {allChatHistory.length > 0 && (
          <>
            <Typography
              variant="overline"
              sx={{
                color: alpha('#ffffff', 0.7),
                fontWeight: 700,
                pl: 2,
                mt: 3,
                mb: 2,
                fontFamily: 'Montserrat, sans-serif',
                display: 'block',
                letterSpacing: 1.2,
                fontSize: '0.7rem'
              }}
            >
              Previous Chats
            </Typography>
            {allChatHistory
              .filter(session => session.session_id !== sessionId) // Only show sessions that aren't the current one
              .map((session) => {
                // Find the first query message in the session
                const firstQuery = session.messages.find(msg => msg?.query && typeof msg.query === 'string');
                
                return firstQuery && (
                  <Box 
                    key={session.session_id} 
                    sx={{ 
                      mb: 2,
                      cursor: 'pointer',
                      borderRadius: 2,
                      overflow: 'hidden',
                      background: alpha('#ffffff', 0.15),
                      border: `1px solid ${alpha('#ffffff', 0.2)}`,
                      '&:hover': {
                        background: alpha('#ffffff', 0.25),
                        borderColor: alpha('#ffffff', 0.4),
                        transform: 'translateX(4px)',
                        boxShadow: `0 4px 12px ${alpha('#000000', 0.2)}`
                      },
                      transition: 'all 0.3s ease'
                    }}
                    onClick={() => handleLoadPreviousSession(session)}
                  >
                    <Typography
                      variant="caption"
                      sx={{
                        color: alpha('#ffffff', 0.7),
                        pl: 2,
                        pt: 1,
                        fontFamily: 'DM Sans, sans-serif',
                        display: 'block',
                        mb: 0.5,
                        fontSize: '0.7rem',
                        fontWeight: 500
                      }}
                    >
                      {new Date(session.timestamp).toLocaleDateString()}
                    </Typography>
                    <ListItem
                      sx={{
                        borderRadius: 1,
                        mb: 0.5,
                        pt: 0
                      }}
                    >
                      <ListItemIcon sx={{ minWidth: 36 }}>
                        <SmartToyIcon fontSize="small" sx={{ color: '#ffffff' }} />
                      </ListItemIcon>
                      <ListItemText
                        primary={firstQuery.query.substring(0, 30) + (firstQuery.query.length > 30 ? '...' : '')}
                        secondary={new Date(firstQuery.timestamp).toLocaleTimeString()}
                        primaryTypographyProps={{
                          noWrap: true,
                          fontSize: '0.875rem',
                          color: '#ffffff',
                          fontFamily: 'DM Sans, sans-serif',
                          fontWeight: 500
                        }}
                        secondaryTypographyProps={{
                          fontSize: '0.7rem',
                          fontFamily: 'DM Sans, sans-serif',
                          color: alpha('#ffffff', 0.7)
                        }}
                      />
                    </ListItem>
                  </Box>
                );
              })}
          </>
        )}
          </List>
        </Box>
      </Box>
    </Drawer>
    
    {/* Sidebar Collapse Button - Only on Desktop */}
    {!isMobile && (
      <IconButton
        onClick={() => setSidebarOpen(!sidebarOpen)}
        sx={{
          position: 'fixed',
          left: sidebarOpen ? DRAWER_WIDTH - 20 : 0,
          top: '50%',
          transform: 'translateY(-50%)',
          zIndex: 10000,
          background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.primary.dark} 100%)`,
          color: 'white',
          width: 40,
          height: 40,
          boxShadow: `0 4px 12px ${alpha(theme.palette.primary.main, 0.4)}`,
          border: `2px solid ${alpha('#ffffff', 0.2)}`,
          '&:hover': {
            background: `linear-gradient(135deg, ${theme.palette.primary.dark} 0%, ${theme.palette.primary.main} 100%)`,
            boxShadow: `0 6px 16px ${alpha(theme.palette.primary.main, 0.6)}`,
            transform: 'translateY(-50%) scale(1.1)',
          },
          transition: 'all 0.3s ease',
        }}
      >
        {sidebarOpen ? <ChevronLeftIcon /> : <ChevronRightIcon />}
      </IconButton>
    )}
  </Box>
  );

  const renderInputArea = () => (
    <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'flex-end' }}>
      <input
        type="file"
        accept=".pdf,.docx"
        style={{ display: 'none' }}
        ref={fileInputRef}
        onChange={handleFileUpload}
      />
      <Tooltip title="Upload document (PDF/DOCX)" arrow placement="top">
        <IconButton
          onClick={() => fileInputRef.current?.click()}
          disabled={loading || isTyping || uploading}
          sx={{
            background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.12)} 0%, ${alpha(theme.palette.secondary.main, 0.1)} 100%)`,
            border: `2px solid ${alpha(theme.palette.primary.main, 0.25)}`,
            width: 52,
            height: 52,
            borderRadius: 3,
            boxShadow: `0 2px 8px ${alpha(theme.palette.primary.main, 0.15)}`,
            '&:hover': {
              background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.2)} 0%, ${alpha(theme.palette.secondary.main, 0.18)} 100%)`,
              borderColor: theme.palette.primary.main,
              transform: 'translateY(-3px) scale(1.05)',
              boxShadow: `0 8px 20px ${alpha(theme.palette.primary.main, 0.35)}`
            },
            '&:active': {
              transform: 'translateY(-1px) scale(1.02)'
            },
            '&:disabled': {
              opacity: 0.5,
              transform: 'none'
            },
            transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
          }}
        >
          {uploading ? (
            <CircularProgress size={26} sx={{ color: theme.palette.primary.main }} />
          ) : (
            <UploadFileIcon sx={{ color: theme.palette.primary.main, fontSize: 24 }} />
          )}
        </IconButton>
      </Tooltip>
      <Box sx={{ flex: 1 }}>
        {pendingAttachment && (
          <Fade in={true}>
            <Box sx={{ mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
              <Chip
                label={`${pendingAttachment.filename} (${pendingAttachment.doc_type || 'document'})`}
                onDelete={() => setPendingAttachment(null)}
                color="primary"
                variant="outlined"
                icon={<DescriptionIcon />}
                sx={{
                  fontFamily: 'DM Sans, sans-serif',
                  borderRadius: 2,
                  background: alpha(theme.palette.primary.main, 0.05),
                  borderColor: alpha(theme.palette.primary.main, 0.3),
                  '& .MuiChip-deleteIcon': {
                    color: theme.palette.primary.main,
                    '&:hover': {
                      color: theme.palette.error.main
                    }
                  }
                }}
              />
            </Box>
          </Fade>
        )}
        <TextField
        fullWidth
        variant="outlined"
        placeholder="Ask me anything about compliance, frameworks, or security standards..."
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
        disabled={loading || isTyping || uploading}
        multiline
        maxRows={4}
        size="small"
        sx={{
          '& .MuiOutlinedInput-root': {
            background: `linear-gradient(135deg, ${alpha(theme.palette.background.default, 0.6)} 0%, ${alpha(theme.palette.background.paper, 0.6)} 100%)`,
            backdropFilter: 'blur(12px)',
            borderRadius: 4,
            fontSize: '0.95rem',
            fontFamily: 'DM Sans, sans-serif',
            padding: '14px 18px',
            border: `2px solid ${alpha(theme.palette.primary.main, 0.15)}`,
            transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
            boxShadow: `0 2px 8px ${alpha(theme.palette.divider, 0.1)}`,
            '&:hover': {
              background: `linear-gradient(135deg, ${alpha(theme.palette.background.default, 0.8)} 0%, ${alpha(theme.palette.background.paper, 0.8)} 100%)`,
              borderColor: alpha(theme.palette.primary.main, 0.3),
              boxShadow: `0 4px 12px ${alpha(theme.palette.primary.main, 0.15)}`
            },
            '&.Mui-focused': {
              background: `linear-gradient(135deg, ${alpha(theme.palette.background.default, 0.95)} 0%, ${alpha(theme.palette.background.paper, 0.95)} 100%)`,
              borderColor: theme.palette.primary.main,
              boxShadow: `0 0 0 4px ${alpha(theme.palette.primary.main, 0.15)}, 0 6px 16px ${alpha(theme.palette.primary.main, 0.2)}`
            },
            '& fieldset': {
              border: 'none',
            },
          },
        }}
        />
      </Box>
      <Button
        variant="contained"
        onClick={handleSend}
        disabled={loading || isTyping || !input.trim() || uploading}
        sx={{ 
          px: 5,
          minWidth: '130px',
          height: '52px',
          borderRadius: 4,
          textTransform: 'none',
          fontFamily: 'DM Sans, sans-serif',
          fontWeight: 700,
          fontSize: '1rem',
          letterSpacing: '0.02em',
          background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.primary.dark} 100%)`,
          boxShadow: `0 6px 20px ${alpha(theme.palette.primary.main, 0.4)}, inset 0 1px 0 ${alpha('#ffffff', 0.2)}`,
          border: `1px solid ${alpha('#ffffff', 0.1)}`,
          '&:hover': {
            background: `linear-gradient(135deg, ${theme.palette.primary.dark} 0%, ${theme.palette.primary.main} 100%)`,
            boxShadow: `0 8px 28px ${alpha(theme.palette.primary.main, 0.5)}, inset 0 1px 0 ${alpha('#ffffff', 0.25)}`,
            transform: 'translateY(-3px) scale(1.02)'
          },
          '&:active': {
            transform: 'translateY(-1px) scale(0.98)'
          },
          '&:disabled': {
            background: `linear-gradient(135deg, ${alpha(theme.palette.action.disabled, 0.15)} 0%, ${alpha(theme.palette.action.disabled, 0.1)} 100%)`,
            color: theme.palette.action.disabled,
            boxShadow: 'none',
            border: `1px solid ${alpha(theme.palette.action.disabled, 0.2)}`
          },
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
        }}
        endIcon={loading ? <CircularProgress size={22} color="inherit" sx={{ color: 'white' }} /> : <SendIcon sx={{ fontSize: 20 }} />}
      >
        {loading ? 'Sending...' : 'Send'}
      </Button>
    </Box>
  );

  const renderDialogs = () => (
    <>
      <Dialog open={analysisDialogOpen} onClose={() => setAnalysisDialogOpen(false)}>
        <DialogTitle>Analyze Privacy Policy</DialogTitle>
        <DialogContent>
          <FormControl fullWidth sx={{ mt: 2 }}>
            <InputLabel>Select Framework</InputLabel>
            <Select
              value={selectedFramework}
              onChange={(e) => setSelectedFramework(e.target.value)}
              label="Select Framework"
            >
              {frameworks.map((framework) => (
                <MenuItem key={framework} value={framework}>
                  {framework}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Box sx={{ mt: 2 }}>
            <input
              type="file"
              accept=".pdf,.docx"
              onChange={handlePrivacyPolicyAnalysis}
              style={{ display: 'none' }}
              id="privacy-policy-analysis"
            />
            <label htmlFor="privacy-policy-analysis">
              <Button
                variant="contained"
                component="span"
                fullWidth
                disabled={!selectedFramework}
              >
                Upload Privacy Policy
              </Button>
            </label>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAnalysisDialogOpen(false)}>Cancel</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={generationDialogOpen} onClose={() => setGenerationDialogOpen(false)}>
        <DialogTitle>Generate Document</DialogTitle>
        <DialogContent>
          <FormControl fullWidth sx={{ mt: 2 }}>
            <InputLabel>Document Type</InputLabel>
            <Select
              value={documentType}
              onChange={(e) => setDocumentType(e.target.value)}
              label="Document Type"
            >
              <MenuItem value="privacy">Privacy Policy</MenuItem>
              <MenuItem value="terms">Terms & Conditions</MenuItem>
            </Select>
          </FormControl>
          <FormControl fullWidth sx={{ mt: 2 }}>
            <InputLabel>Select Framework</InputLabel>
            <Select
              value={selectedFramework}
              onChange={(e) => setSelectedFramework(e.target.value)}
              label="Select Framework"
            >
              {frameworks.map((framework) => (
                <MenuItem key={framework} value={framework}>
                  {framework}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl fullWidth sx={{ mt: 2 }}>
            <InputLabel>Select Format</InputLabel>
            <Select
              value={selectedFormat}
              onChange={(e) => setSelectedFormat(e.target.value)}
              label="Select Format"
            >
              {formats.map((format) => (
                <MenuItem key={format} value={format}>
                  {format.toUpperCase()}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setGenerationDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleGenerateDocument}
            variant="contained"
            disabled={!selectedFramework}
          >
            Generate
          </Button>
        </DialogActions>
      </Dialog>

      {downloadUrl && (
        <Dialog open={!!downloadUrl} onClose={() => setDownloadUrl(null)}>
          <DialogTitle>Document Generated</DialogTitle>
          <DialogContent>
            <Typography>
              Your document has been generated successfully. Click the button below to download it.
            </Typography>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDownloadUrl(null)}>Close</Button>
            <Button
              variant="contained"
              onClick={() => window.open(downloadUrl, '_blank')}
            >
              Download
            </Button>
          </DialogActions>
        </Dialog>
      )}
    </>
  );

  return (
    <Box 
      component={motion.div}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      sx={{ 
        height: '100vh',
        width: '100vw',
        display: 'flex',
        position: 'fixed',
        top: 0,
        left: 0,
        background: `linear-gradient(135deg, ${alpha(theme.palette.background.default, 0.98)} 0%, ${alpha(theme.palette.background.paper, 0.98)} 100%)`,
        zIndex: 9999,
      }}
    >
      <ChatSidebar />
      
      <Box 
        sx={{ 
          flex: 1,
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          position: 'relative',
          overflow: 'hidden',
          transition: 'all 0.3s ease',
          width: isMobile ? '100%' : (sidebarOpen ? `calc(100% - ${DRAWER_WIDTH}px)` : '100%'),
          marginLeft: isMobile ? 0 : (sidebarOpen ? 0 : `-${DRAWER_WIDTH}px`)
        }}
      >
        {/* Modern Header with Enhanced Gradient */}
        <Box
          component={motion.div}
          initial={{ y: -20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.2 }}
          sx={{
            width: '100%',
            px: 3,
            py: 2.5,
            minHeight: '85px',
            background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.primary.dark} 50%, ${alpha('#000000', 0.85)} 100%)`,
            boxShadow: `0 8px 32px ${alpha(theme.palette.primary.main, 0.3)}, inset 0 1px 0 ${alpha('#ffffff', 0.1)}`,
            display: 'flex',
            alignItems: 'center',
            gap: 2.5,
            zIndex: 1,
            position: 'relative',
            boxSizing: 'border-box',
            overflow: 'hidden',
            '&::before': {
              content: '""',
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: `radial-gradient(circle at 20% 50%, ${alpha('#ffffff', 0.15)} 0%, transparent 60%),
                          radial-gradient(circle at 80% 20%, ${alpha('#000000', 0.2)} 0%, transparent 50%)`,
              pointerEvents: 'none',
              animation: 'pulse 4s ease-in-out infinite'
            },
            '@keyframes pulse': {
              '0%, 100%': { opacity: 1 },
              '50%': { opacity: 0.8 }
            }
          }}
        >
          {isMobile && (
            <IconButton 
              onClick={() => setDrawerOpen(true)} 
              sx={{ 
                color: 'white', 
                zIndex: 1,
                background: alpha('#ffffff', 0.1),
                backdropFilter: 'blur(10px)',
                border: `1px solid ${alpha('#ffffff', 0.2)}`,
                '&:hover': {
                  background: alpha('#ffffff', 0.2),
                  transform: 'scale(1.1)'
                },
                transition: 'all 0.3s ease'
              }}
            >
              <MenuIcon />
            </IconButton>
          )}
          <motion.div
            animate={{ 
              rotate: [0, 5, -5, 0],
              scale: [1, 1.05, 1]
            }}
            transition={{ 
              duration: 3,
              repeat: Infinity,
              repeatType: "reverse"
            }}
            style={{ zIndex: 1 }}
          >
            <img
              src="/images/law.png"
              alt="Compliance Assistant"
              style={{
                width: '28px',
                height: '28px',
                objectFit: 'contain',
                filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.2))'
              }}
            />
          </motion.div>
          <Box sx={{ zIndex: 1, flex: 1 }}>
            <Typography 
              variant="h5" 
              sx={{ 
                fontWeight: 800,
                fontFamily: 'Montserrat, sans-serif',
                fontSize: '1.35rem',
                color: 'white',
                letterSpacing: '-0.03em',
                lineHeight: 1.2,
                textShadow: '0 2px 8px rgba(0,0,0,0.2)',
                mb: 0.3
              }}
            >
              Compliance Assistant
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.8 }}>
              <SecurityIcon sx={{ fontSize: 14, color: alpha('#ffffff', 0.95), filter: 'drop-shadow(0 1px 2px rgba(0,0,0,0.2))' }} />
              <Typography 
                variant="body2" 
                sx={{ 
                  opacity: 0.95,
                  fontFamily: 'DM Sans, sans-serif',
                  fontSize: '0.8rem',
                  color: 'white',
                  lineHeight: 1.4,
                  fontWeight: 500,
                  textShadow: '0 1px 4px rgba(0,0,0,0.15)'
                }}
              >
                Your intelligent compliance & security expert
              </Typography>
            </Box>
          </Box>
          <Tooltip title="Clear conversation" arrow placement="bottom">
            <IconButton 
              onClick={handleReset} 
              sx={{ 
                color: 'white',
                background: `linear-gradient(135deg, ${alpha('#ffffff', 0.15)} 0%, ${alpha('#ffffff', 0.1)} 100%)`,
                backdropFilter: 'blur(12px)',
                border: `1.5px solid ${alpha('#ffffff', 0.25)}`,
                width: 42,
                height: 42,
                '&:hover': {
                  background: `linear-gradient(135deg, ${alpha('#ffffff', 0.25)} 0%, ${alpha('#ffffff', 0.15)} 100%)`,
                  transform: 'rotate(180deg) scale(1.1)',
                  borderColor: alpha('#ffffff', 0.4),
                  boxShadow: `0 4px 16px ${alpha('#000000', 0.2)}`
                },
                transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
                zIndex: 1
              }}
            >
              <DeleteIcon sx={{ fontSize: 20 }} />
            </IconButton>
          </Tooltip>
        </Box>

        {/* Chat Messages with Enhanced Design */}
        <Box 
          sx={{ 
            flex: 1,
            width: '100%',
            overflow: 'auto',
            display: 'flex',
            flexDirection: 'column',
            p: 4,
            background: `radial-gradient(ellipse at top, ${alpha(theme.palette.primary.main, 0.03)} 0%, transparent 60%),
                        radial-gradient(ellipse at bottom right, ${alpha(theme.palette.secondary.main, 0.02)} 0%, transparent 50%)`,
            position: 'relative',
            '&::before': {
              content: '""',
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundImage: `radial-gradient(circle at 2px 2px, ${alpha(theme.palette.divider, 0.03)} 1px, transparent 0)`,
              backgroundSize: '40px 40px',
              pointerEvents: 'none',
              opacity: 0.5
            },
            '&::-webkit-scrollbar': {
              width: '10px',
            },
            '&::-webkit-scrollbar-track': {
              background: alpha(theme.palette.background.paper, 0.4),
              borderRadius: '5px',
              border: `1px solid ${alpha(theme.palette.divider, 0.1)}`
            },
            '&::-webkit-scrollbar-thumb': {
              background: `linear-gradient(180deg, ${alpha(theme.palette.primary.main, 0.4)} 0%, ${alpha(theme.palette.primary.dark, 0.3)} 100%)`,
              borderRadius: '5px',
              border: `1px solid ${alpha(theme.palette.primary.main, 0.1)}`,
              '&:hover': {
                background: `linear-gradient(180deg, ${alpha(theme.palette.primary.main, 0.6)} 0%, ${alpha(theme.palette.primary.dark, 0.5)} 100%)`,
              }
            },
          }}
        >
          <AnimatePresence mode="popLayout">
            {messages.length === 0 ? (
              <Box
                component={motion.div}
                key="empty-state"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                transition={{ duration: 0.5 }}
                sx={{ 
                  flex: 1,
                  width: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  textAlign: 'center',
                  color: theme.palette.text.secondary,
                }}
              >
                <motion.div
                  animate={{ 
                    y: [0, -20, 0],
                    rotate: [0, 8, -8, 0],
                    scale: [1, 1.05, 1]
                  }}
                  transition={{ 
                    duration: 4,
                    repeat: Infinity,
                    repeatType: "reverse",
                    ease: "easeInOut"
                  }}
                  style={{ marginBottom: '24px' }}
                >
                  <img
                    src="/images/law.png"
                    alt="Compliance Assistant"
                    style={{
                      width: '56px',
                      height: '56px',
                      objectFit: 'contain',
                      opacity: 0.9,
                      zIndex: 1,
                      filter: 'drop-shadow(0 3px 6px rgba(0,0,0,0.1))'
                    }}
                  />
                </motion.div>
                <Typography 
                  variant="h4"
                  sx={{ 
                    mb: 2.5,
                    fontFamily: 'Montserrat, sans-serif',
                    fontWeight: 800,
                    background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.secondary.main} 100%)`,
                    backgroundClip: 'text',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    letterSpacing: '-0.03em',
                    fontSize: { xs: '1.75rem', md: '2.25rem' },
                    textShadow: `0 2px 8px ${alpha(theme.palette.primary.main, 0.1)}`
                  }}
                >
                  Welcome to Compliance Assistant
                </Typography>
                <Typography
                  variant="h6"
                  sx={{ 
                    maxWidth: '650px',
                    fontFamily: 'DM Sans, sans-serif',
                    color: theme.palette.text.secondary,
                    lineHeight: 1.7,
                    mb: 4,
                    fontSize: { xs: '1rem', md: '1.15rem' },
                    fontWeight: 500,
                    px: 2
                  }}
                >
                  Your intelligent expert for compliance frameworks, security controls, and regulatory requirements
                </Typography>
                <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', justifyContent: 'center', mt: 3 }}>
                  {['GDPR', 'HIPAA', 'ISO 27001', 'SOC 2'].map((framework, idx) => (
                    <motion.div
                      key={framework}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.3 + idx * 0.1 }}
                    >
                      <Chip
                        label={framework}
                        sx={{
                          background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.12)} 0%, ${alpha(theme.palette.secondary.main, 0.08)} 100%)`,
                          color: theme.palette.primary.main,
                          fontWeight: 700,
                          fontSize: '0.9rem',
                          px: 2,
                          py: 2.5,
                          height: 'auto',
                          border: `1.5px solid ${alpha(theme.palette.primary.main, 0.25)}`,
                          boxShadow: `0 4px 12px ${alpha(theme.palette.primary.main, 0.1)}`,
                          fontFamily: 'DM Sans, sans-serif',
                          cursor: 'pointer',
                          '&:hover': {
                            background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.2)} 0%, ${alpha(theme.palette.secondary.main, 0.15)} 100%)`,
                            transform: 'translateY(-3px) scale(1.05)',
                            boxShadow: `0 8px 20px ${alpha(theme.palette.primary.main, 0.25)}`,
                            borderColor: theme.palette.primary.main
                          },
                          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
                        }}
                        onClick={() => {
                          setInput(`Tell me about ${framework} compliance requirements`);
                        }}
                      />
                    </motion.div>
                  ))}
                </Box>
              </Box>
            ) : (
              messages.map((message, index) => (
                <Zoom in={true} key={`${message.type}-${index}`} style={{ transitionDelay: `${index * 50}ms` }}>
                  <Box
                    component={motion.div}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    transition={{ duration: 0.4 }}
                    sx={{
                      width: '100%',
                      display: 'flex',
                      flexDirection: message.type === 'user' ? 'row-reverse' : 'row',
                      gap: 2,
                      mb: 3,
                    }}
                  >
                    <Avatar 
                      sx={{ 
                        background: message.type === 'user' 
                          ? `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.primary.dark} 100%)`
                          : `linear-gradient(135deg, ${theme.palette.secondary.main} 0%, ${theme.palette.secondary.dark} 100%)`,
                        width: 44,
                        height: 44,
                        boxShadow: message.type === 'user'
                          ? `0 6px 20px ${alpha(theme.palette.primary.main, 0.4)}, inset 0 1px 0 ${alpha('#ffffff', 0.2)}`
                          : `0 6px 20px ${alpha(theme.palette.secondary.main, 0.4)}, inset 0 1px 0 ${alpha('#ffffff', 0.2)}`,
                        border: `2.5px solid ${alpha('#ffffff', 0.2)}`,
                        transition: 'all 0.3s ease',
                        '&:hover': {
                          transform: 'scale(1.1) rotate(5deg)',
                          boxShadow: message.type === 'user'
                            ? `0 8px 24px ${alpha(theme.palette.primary.main, 0.5)}, inset 0 1px 0 ${alpha('#ffffff', 0.3)}`
                            : `0 8px 24px ${alpha(theme.palette.secondary.main, 0.5)}, inset 0 1px 0 ${alpha('#ffffff', 0.3)}`
                        }
                      }}
                    >
                      {message.type === 'user' ? <PersonIcon sx={{ fontSize: 22 }} /> : <SmartToyIcon sx={{ fontSize: 22 }} />}
                    </Avatar>
                    <Box 
                      sx={{ 
                        maxWidth: '75%',
                        minWidth: '200px',
                        position: 'relative'
                      }}
                    >
                      <Paper
                        elevation={0}
                        sx={{
                          p: 3,
                          background: message.type === 'user' 
                            ? `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.primary.dark} 100%)`
                            : `linear-gradient(135deg, ${alpha(theme.palette.background.paper, 0.95)} 0%, ${alpha(theme.palette.background.default, 0.95)} 100%)`,
                          backdropFilter: 'blur(12px)',
                          color: message.type === 'user' ? 'white' : 'text.primary',
                          borderRadius: 4,
                          border: message.type === 'user' 
                            ? `1.5px solid ${alpha('#ffffff', 0.2)}`
                            : `1.5px solid ${alpha(theme.palette.primary.main, 0.15)}`,
                          boxShadow: message.type === 'user'
                            ? `0 10px 32px ${alpha(theme.palette.primary.main, 0.35)}, inset 0 1px 0 ${alpha('#ffffff', 0.1)}`
                            : `0 10px 32px ${alpha(theme.palette.divider, 0.15)}, inset 0 1px 0 ${alpha('#ffffff', 0.5)}`,
                          position: 'relative',
                          overflow: 'hidden',
                          transition: 'all 0.3s ease',
                          '&:hover': {
                            transform: 'translateY(-2px)',
                            boxShadow: message.type === 'user'
                              ? `0 12px 40px ${alpha(theme.palette.primary.main, 0.4)}, inset 0 1px 0 ${alpha('#ffffff', 0.15)}`
                              : `0 12px 40px ${alpha(theme.palette.divider, 0.2)}, inset 0 1px 0 ${alpha('#ffffff', 0.6)}`
                          },
                          '&::before': message.type !== 'user' ? {
                            content: '""',
                            position: 'absolute',
                            top: 0,
                            left: 0,
                            width: '5px',
                            height: '100%',
                            background: `linear-gradient(180deg, ${theme.palette.primary.main} 0%, ${theme.palette.secondary.main} 100%)`,
                            borderRadius: '4px 0 0 4px',
                            boxShadow: `2px 0 8px ${alpha(theme.palette.primary.main, 0.3)}`
                          } : {},
                          '&::after': message.type === 'user' ? {
                            content: '""',
                            position: 'absolute',
                            top: 0,
                            left: 0,
                            right: 0,
                            bottom: 0,
                            background: `radial-gradient(circle at top right, ${alpha('#ffffff', 0.1)} 0%, transparent 70%)`,
                            pointerEvents: 'none'
                          } : {}
                        }}
                      >
                        {message.type === 'response' && message.isTyping ? (
                          <TypewriterText 
                            text={message.content} 
                            onComplete={() => handleTypingComplete(index)}
                          />
                        ) : (
                          <ComplianceChatFormattedResponse 
                            content={message.content} 
                            textColor={message.type === 'user' ? 'white' : undefined}
                          />
                        )}
                {message.attachments && message.attachments.length > 0 && (
                  <Box sx={{ mt: 2, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    {message.attachments.map((att, i) => (
                      <Chip
                        key={i}
                        label={`${att.filename}${att.doc_type ? ` • ${att.doc_type}` : ''}`}
                        variant="outlined"
                        size="small"
                        icon={<DescriptionIcon />}
                        onClick={() => {
                          // optionally open a sidebar or just ignore
                        }}
                        sx={{
                          borderColor: message.type === 'user' ? alpha('#ffffff', 0.3) : alpha(theme.palette.primary.main, 0.3),
                          color: message.type === 'user' ? 'white' : theme.palette.text.primary,
                          '& .MuiChip-icon': {
                            color: message.type === 'user' ? 'white' : theme.palette.primary.main
                          }
                        }}
                      />
                    ))}
                  </Box>
                )}
                {message.experts && !message.isTyping && (
                          <Box sx={{ 
                            mt: 2.5, 
                            pt: 2, 
                            borderTop: `1.5px solid ${alpha(theme.palette.divider, 0.15)}`,
                            display: 'flex',
                            alignItems: 'center',
                            gap: 1.5,
                            flexWrap: 'wrap'
                          }}>
                            <Box sx={{ 
                              display: 'flex', 
                              alignItems: 'center', 
                              gap: 0.8,
                              background: alpha(theme.palette.primary.main, 0.08),
                              px: 1.5,
                              py: 0.8,
                              borderRadius: 2,
                              border: `1px solid ${alpha(theme.palette.primary.main, 0.15)}`
                            }}>
                              <AutoAwesomeIcon sx={{ fontSize: 16, color: theme.palette.primary.main, opacity: 0.9 }} />
                              <Typography 
                                variant="caption"
                                sx={{ 
                                  color: theme.palette.text.secondary,
                                  fontFamily: 'DM Sans, sans-serif',
                                  fontSize: '0.75rem',
                                  fontWeight: 600,
                                  letterSpacing: '0.02em'
                                }}
                              >
                                Experts Consulted:
                              </Typography>
                            </Box>
                            <Box sx={{ display: 'flex', gap: 0.8, flexWrap: 'wrap' }}>
                              {message.experts.map((expert, idx) => (
                                <Chip
                                  key={idx}
                                  label={expert}
                                  size="small"
                                  sx={{
                                    background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.12)} 0%, ${alpha(theme.palette.secondary.main, 0.08)} 100%)`,
                                    color: theme.palette.primary.main,
                                    border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`,
                                    fontSize: '0.7rem',
                                    fontWeight: 600,
                                    height: '24px',
                                    fontFamily: 'DM Sans, sans-serif',
                                    '&:hover': {
                                      background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.18)} 0%, ${alpha(theme.palette.secondary.main, 0.12)} 100%)`,
                                      transform: 'translateY(-1px)',
                                      boxShadow: `0 2px 8px ${alpha(theme.palette.primary.main, 0.2)}`
                                    },
                                    transition: 'all 0.2s ease'
                                  }}
                                />
                              ))}
                            </Box>
                          </Box>
                        )}
                        {/* Add feedback buttons for bot responses */}
                        {message.type === 'response' && !message.isTyping && message.originalQuery && (
                          <Box sx={{ mt: 1.5 }}>
                            {getFeedbackButtons(index, message.originalQuery)}
                          </Box>
                        )}
                      </Paper>
                      <Typography 
                        variant="caption" 
                        sx={{ 
                          display: 'block',
                          mt: 1.5,
                          ml: message.type === 'user' ? 0 : 1,
                          mr: message.type === 'user' ? 1 : 0,
                          color: theme.palette.text.secondary,
                          textAlign: message.type === 'user' ? 'right' : 'left',
                          fontFamily: 'DM Sans, sans-serif',
                          fontSize: '0.7rem',
                          fontWeight: 500,
                          opacity: 0.7,
                          letterSpacing: '0.02em'
                        }}
                      >
                        {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </Typography>
                    </Box>
                  </Box>
                </Zoom>
              ))
            )}
          </AnimatePresence>
          <div ref={messagesEndRef} />
        </Box>

        {/* Enhanced Input Area */}
        <Box
          component={motion.div}
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          sx={{ 
            width: '100%',
            p: 3.5,
            background: `linear-gradient(180deg, transparent 0%, ${alpha(theme.palette.background.paper, 0.85)} 15%, ${alpha(theme.palette.background.paper, 0.98)} 100%)`,
            backdropFilter: 'blur(16px)',
            borderTop: `1.5px solid ${alpha(theme.palette.divider, 0.15)}`,
            boxShadow: `0 -8px 32px ${alpha(theme.palette.divider, 0.12)}, inset 0 1px 0 ${alpha('#ffffff', 0.5)}`,
            position: 'relative',
            '&::before': {
              content: '""',
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              height: '1px',
              background: `linear-gradient(90deg, transparent 0%, ${alpha(theme.palette.primary.main, 0.3)} 50%, transparent 100%)`
            }
          }}
        >
          {renderInputArea()}
        </Box>

        {/* Dialogs */}
        {renderDialogs()}
      </Box>
    </Box>
  );
};

export default ComplianceChat;
