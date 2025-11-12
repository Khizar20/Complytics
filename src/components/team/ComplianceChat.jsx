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
  Chip
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import RefreshIcon from '@mui/icons-material/Refresh';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import PersonIcon from '@mui/icons-material/Person';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import DeleteIcon from '@mui/icons-material/Delete';
import MenuIcon from '@mui/icons-material/Menu';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import PolicyIcon from '@mui/icons-material/Policy';
import DescriptionIcon from '@mui/icons-material/Description';
import ThumbUpIcon from '@mui/icons-material/ThumbUp';
import ThumbDownIcon from '@mui/icons-material/ThumbDown';
import ThumbUpOffAltIcon from '@mui/icons-material/ThumbUpOffAlt';
import ThumbDownOffAltIcon from '@mui/icons-material/ThumbDownOffAlt';
import { useAuth } from '../../context/AuthContext';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';

// Formatted response component
const FormattedResponse = ({ content }) => {
  const theme = useTheme();

  const preprocessContent = (text) => {
    if (!text) return ''; // Return empty string if text is undefined or null
    
    // First, handle special cases to avoid conflicts
    let processedText = text
      // Handle URLs with fragments
      .replace(/(https?:\/\/[^\s#]+)#([^\s]+)/g, '$1%23$2')
      // Handle multiplication in code
      .replace(/(\d+)\s*\*\s*(\d+)/g, '$1×$2')
      // Handle wildcards in code
      .replace(/\*\.([a-zA-Z]+)/g, '*.$1')
      // Handle comments
      .replace(/\/\/\s*#/g, '//%23')
      .replace(/\/\*\s*#/g, '/*%23');

    // Clean up standalone hashtags and malformed markdown
    processedText = processedText
      // Remove standalone hashtags on their own lines
      .replace(/^#+\s*$/gm, '')
      // Remove multiple consecutive empty lines
      .replace(/\n\s*\n\s*\n+/g, '\n\n')
      // Clean up hashtags at start of lines that don't have proper content
      .replace(/^#+\s*([^\n]*)\n#+\s*$/gm, '## $1')
      // Fix malformed headers - ensure space after hashtags
      .replace(/^(#{1,6})([^\s#])/gm, '$1 $2')
      // Clean up repeated hashtags
      .replace(/^#{4,}/gm, '###')
      // Handle emojis followed by headers properly
      .replace(/^(#{1,3})\s*([🔍📋🚨⚠️✨📝🎯📚💡🔧📊📥✅❌⭐🎉🏆🔐🛡️📈📉💼🌟⚡🎯])\s*/gm, '$1 $2 ')
      // Remove empty headers (headers with only emoji or whitespace)
      .replace(/^#{1,3}\s*([🔍📋🚨⚠️✨📝🎯📚💡🔧📊📥✅❌⭐🎉🏆🔐🛡️📈📉💼🌟⚡🎯]*)\s*$/gm, '');

    // Then handle markdown formatting
    processedText = processedText
      // Headings - ensure proper spacing
      .replace(/###\s+/g, '\n### ')
      .replace(/##\s+/g, '\n## ')
      .replace(/#\s+/g, '\n# ')
      // Bold and italic
      .replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      // Download links - special handling for /api/compliance/download/ links
      .replace(/\[([^\]]+)\]\((\/api\/compliance\/download\/[^)]+)\)/g, '<a href="http://localhost:8000$2" download style="color: #1976d2; text-decoration: none; font-weight: 600; background: linear-gradient(135deg, #1976d2 0%, #42a5f5 100%); padding: 8px 16px; border-radius: 8px; color: white; display: inline-block; margin: 4px 0; transition: all 0.3s ease; box-shadow: 0 2px 8px rgba(25, 118, 210, 0.3);" onmouseover="this.style.transform=\'translateY(-2px)\'; this.style.boxShadow=\'0 4px 12px rgba(25, 118, 210, 0.4)\';" onmouseout="this.style.transform=\'translateY(0)\'; this.style.boxShadow=\'0 2px 8px rgba(25, 118, 210, 0.3)\';">📥 $1</a>')
      // Regular markdown links - convert [text](url) to clickable links
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" style="color: #1976d2; text-decoration: none; font-weight: 500; border-bottom: 1px solid #1976d2; padding-bottom: 1px;">$1</a>')
      // Bullet points
      .replace(/\*\s+/g, '\n* ')
      .replace(/-\s+/g, '\n- ')
      // Dividers
      .replace(/\n\*\*\*\n/g, '\n<hr/>\n')
      // Final cleanup - remove any remaining standalone hashtags
      .replace(/^\s*#+\s*$/gm, '')
      // Clean up extra whitespace
      .replace(/\n{3,}/g, '\n\n')
      .trim();

    return processedText;
  };

  const formatContent = (text) => {
    if (!text) return null; // Return null if text is undefined or null
    
    const processedText = preprocessContent(text);
    // Split content into sections based on headings and bullet points, but filter out empty sections
    const sections = processedText
      .split(/(?=#{1,3}\s[^#\s]|^[*-]\s|<hr\/>)/m)
      .filter(section => section.trim() && section.trim() !== '#' && section.trim() !== '##' && section.trim() !== '###')
      .map(section => section.trim())
      .filter(section => section.length > 0);
    
    return sections.map((section, index) => {
      // Handle dividers
      if (section.trim() === '<hr/>') {
        return (
          <Divider 
            key={index} 
            sx={{ 
              my: 3,
              borderColor: theme.palette.divider,
              opacity: 0.5
            }} 
          />
        );
      }

      // Check if section starts with a heading - improved regex to handle emojis
      const headingMatch = section.match(/^(#{1,3})\s+(.+?)$/m);
      
      if (headingMatch) {
        const level = headingMatch[1].length;
        const headingText = headingMatch[2].trim();
        // Get content after the heading line
        const contentLines = section.split('\n');
        const content = contentLines.slice(1).join('\n').trim();
        
        // Only render if heading text is meaningful (not just emoji or empty)
        if (headingText && headingText.length > 0 && headingText !== '#' && !/^[🔍📋🚨⚠️✨📝🎯📚💡🔧📊📥✅❌⭐🎉🏆🔐🛡️📈📉💼🌟⚡🎯\s]*$/.test(headingText)) {
        return (
          <Box key={index} sx={{ mb: 3 }}>
            <Typography
              variant={level === 1 ? "h4" : level === 2 ? "h5" : "h6"}
              sx={{
                fontFamily: 'Montserrat, sans-serif',
                fontWeight: 600,
                mb: 2,
                color: theme.palette.text.primary,
                fontSize: level === 1 ? '1.5rem' : level === 2 ? '1.25rem' : '1.1rem'
              }}
            >
              {headingText}
            </Typography>
            {content && (
              <Box sx={{ pl: 2 }}>
                {formatBulletPoints(content)}
              </Box>
            )}
          </Box>
        );
      }
      }
      
      // For non-heading sections, format as bullet points or paragraphs
      if (section.trim()) {
        return (
          <Box key={index} sx={{ mb: 2 }}>
            {formatBulletPoints(section)}
          </Box>
        );
      }
      
      return null;
    }).filter(Boolean); // Remove any null entries
  };

  const formatBulletPoints = (text) => {
    if (!text || !text.trim()) return null;
    
    // Split content into paragraphs and filter out empty ones
    const paragraphs = text
      .split(/\n\n+/)
      .map(p => p.trim())
      .filter(p => p && p.length > 0 && p !== '#' && p !== '##' && p !== '###');
    
    return paragraphs.map((paragraph, index) => {
      // Skip if paragraph is just hashtags or whitespace
      if (!paragraph || /^[#\s]*$/.test(paragraph)) {
        return null;
      }
      
      // Check if paragraph contains bullet points
      if (paragraph.includes('* ') || paragraph.includes('- ')) {
        const points = paragraph
          .split(/\n/)
          .filter(line => line.trim().startsWith('* ') || line.trim().startsWith('- '))
          .map(line => line.trim())
          .filter(line => line && line.length > 2); // Must have content after bullet
        
        if (points.length === 0) return null;
        
        return (
          <List key={index} sx={{ py: 0, pl: 2 }}>
            {points.map((point, pointIndex) => (
              <ListItem key={pointIndex} sx={{ py: 0.5, pl: 0 }}>
                <ListItemIcon sx={{ minWidth: 24 }}>
                  <FiberManualRecordIcon sx={{ fontSize: 8, color: theme.palette.primary.main }} />
                </ListItemIcon>
                <ListItemText
                  primary={
                    <Typography
                      variant="body1"
                      sx={{
                        fontFamily: 'DM Sans, sans-serif',
                        lineHeight: 1.6,
                        fontSize: '0.95rem',
                        '& a': {
                          cursor: 'pointer',
                          '&:hover': {
                            opacity: 0.8
                          }
                        }
                      }}
                      dangerouslySetInnerHTML={{
                        __html: point.replace(/^[*-]\s+/, '')
                      }}
                    />
                  }
                />
              </ListItem>
            ))}
          </List>
        );
      }
      
      // Regular paragraph with HTML formatting
      return (
        <Typography
          key={index}
          variant="body1"
          sx={{
            fontFamily: 'DM Sans, sans-serif',
            lineHeight: 1.6,
            mb: 2,
            fontSize: '0.95rem',
            '& strong': {
              fontWeight: 600,
              color: theme.palette.text.primary
            },
            '& em': {
              fontStyle: 'italic',
              color: theme.palette.text.secondary
            },
            '& a': {
              cursor: 'pointer',
              '&:hover': {
                opacity: 0.8
              }
            }
          }}
          dangerouslySetInnerHTML={{
            __html: paragraph.trim()
          }}
        />
      );
    }).filter(Boolean); // Remove any null entries
  };

  return (
    <Box sx={{ width: '100%' }}>
      {content ? formatContent(content) : null}
    </Box>
  );
};

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
          <FormattedResponse content={displayedText} />
          <motion.span
            animate={{ opacity: [1, 0] }}
            transition={{ duration: 0.4, repeat: Infinity }}
            style={{ marginLeft: 2 }}
          >
            |
          </motion.span>
        </Box>
      ) : (
        <FormattedResponse content={text} />
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
  
  const DRAWER_WIDTH = 280;

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
      const response = await fetchWithRetry(`http://localhost:8000/api/compliance/history?session_id=${currentSessionId}`);
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
      const response = await fetchWithRetry('http://localhost:8000/api/compliance/all-history');
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
      const response = await fetchWithRetry('http://localhost:8000/api/compliance/chat', {
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
      await fetchWithRetry('http://localhost:8000/api/compliance/reset', {
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
      await fetchWithRetry('http://localhost:8000/api/compliance/feedback', {
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
        gap: 1, 
        mt: 1, 
        justifyContent: 'flex-start',
        opacity: 0.7,
        '&:hover': { opacity: 1 }
      }}>
        <Tooltip title={currentFeedback === true ? "You found this helpful" : "Mark as helpful"}>
          <IconButton 
            size="small"
            onClick={() => handleFeedback(messageIndex, true, originalQuery)}
            disabled={currentFeedback !== undefined}
            sx={{ 
              color: currentFeedback === true ? theme.palette.success.main : theme.palette.text.secondary,
              '&:hover': { 
                bgcolor: currentFeedback === true 
                  ? alpha(theme.palette.success.main, 0.1)
                  : alpha(theme.palette.text.secondary, 0.1)
              }
            }}
          >
            {currentFeedback === true ? <ThumbUpIcon fontSize="small" /> : <ThumbUpOffAltIcon fontSize="small" />}
          </IconButton>
        </Tooltip>
        <Tooltip title={currentFeedback === false ? "You marked this as not helpful" : "Mark as not helpful"}>
          <IconButton 
            size="small"
            onClick={() => handleFeedback(messageIndex, false, originalQuery)}
            disabled={currentFeedback !== undefined}
            sx={{ 
              color: currentFeedback === false ? theme.palette.error.main : theme.palette.text.secondary,
              '&:hover': { 
                bgcolor: currentFeedback === false 
                  ? alpha(theme.palette.error.main, 0.1)
                  : alpha(theme.palette.text.secondary, 0.1)
              }
            }}
          >
            {currentFeedback === false ? <ThumbDownIcon fontSize="small" /> : <ThumbDownOffAltIcon fontSize="small" />}
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
      if (target.tagName === 'A' && target.href && 
          (target.href.includes('/api/compliance/download/') || 
           target.href.includes('localhost:8000/api/compliance/download/'))) {
        event.preventDefault();
        const filename = target.href.split('/').pop();
        const fullUrl = target.href.startsWith('http') ? target.href : `http://localhost:8000${target.href}`;
        handleDownload(fullUrl, filename);
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
      const response = await fetch('http://localhost:8000/api/compliance/upload-document', {
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
        throw new Error(data.detail?.message || 'Upload failed');
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
      const response = await fetchWithRetry('http://localhost:8000/api/compliance/analyze-privacy-policy', {
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
        ? 'http://localhost:8000/api/compliance/generate-privacy-policy'
        : 'http://localhost:8000/api/compliance/generate-terms';

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
    <Drawer
      variant={isMobile ? "temporary" : "permanent"}
      open={isMobile ? drawerOpen : true}
      onClose={() => setDrawerOpen(false)}
      sx={{
        width: DRAWER_WIDTH,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: DRAWER_WIDTH,
          position: 'relative',
          height: '100%',
          boxSizing: 'border-box',
          bgcolor: theme.palette.background.default,
          border: 'none',
          borderRight: `1px solid ${theme.palette.divider}`,
        },
      }}
    >
      <Box sx={{ 
        p: 2, 
        borderBottom: `1px solid ${theme.palette.divider}`,
        bgcolor: theme.palette.background.default,
        display: 'flex',
        flexDirection: 'column',
        gap: 1
      }}>
        <Button
          fullWidth
          variant="outlined"
          startIcon={<ArrowBackIcon />}
          onClick={handleBackToDashboard}
          sx={{ 
            fontFamily: 'Montserrat, sans-serif',
            fontWeight: 600,
            mb: 1
          }}
        >
          Back to Dashboard
        </Button>
        <Button
          fullWidth
          variant="contained"
          startIcon={<RefreshIcon />}
          onClick={handleReset}
          sx={{ 
            bgcolor: theme.palette.primary.main,
            color: 'white',
            fontFamily: 'Montserrat, sans-serif',
            fontWeight: 600,
            '&:hover': {
              bgcolor: theme.palette.primary.dark,
            }
          }}
        >
          New Chat
        </Button>
      </Box>
      <List sx={{ 
        overflow: 'auto', 
        flex: 1, 
        p: 2,
        '&::-webkit-scrollbar': {
          width: '4px',
        },
        '&::-webkit-scrollbar-track': {
          background: 'transparent',
        },
        '&::-webkit-scrollbar-thumb': {
          background: theme.palette.divider,
          borderRadius: '2px',
        },
      }}>
        <Typography
          variant="overline"
          sx={{
            color: theme.palette.text.secondary,
            fontWeight: 500,
            pl: 2,
            fontFamily: 'Montserrat, sans-serif',
          }}
        >
          Current Session
        </Typography>
        {sessionHistory.length > 0 && (() => {
          const firstQuery = sessionHistory.find(msg => msg?.query && typeof msg.query === 'string');
          return firstQuery && (
            <ListItem
              sx={{
                borderRadius: 1,
                mb: 0.5,
                bgcolor: alpha(theme.palette.primary.main, 0.1),
                '&:hover': {
                  bgcolor: alpha(theme.palette.primary.main, 0.2),
                }
              }}
            >
              <ListItemIcon sx={{ minWidth: 36 }}>
                <SmartToyIcon fontSize="small" color="primary" />
              </ListItemIcon>
              <ListItemText
                primary={firstQuery.query.substring(0, 30) + (firstQuery.query.length > 30 ? '...' : '')}
                secondary={new Date(firstQuery.timestamp).toLocaleTimeString()}
                primaryTypographyProps={{
                  noWrap: true,
                  fontSize: '0.875rem',
                  fontFamily: 'DM Sans, sans-serif',
                  fontWeight: 600
                }}
                secondaryTypographyProps={{
                  fontSize: '0.75rem',
                  fontFamily: 'DM Sans, sans-serif'
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
                color: theme.palette.text.secondary,
                fontWeight: 500,
                pl: 2,
                mt: 3,
                mb: 2,
                fontFamily: 'Montserrat, sans-serif',
                display: 'block'
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
                      borderRadius: 1,
                      overflow: 'hidden',
                      bgcolor: alpha(theme.palette.background.paper, 0.1),
                      '&:hover': {
                        bgcolor: alpha(theme.palette.background.paper, 0.3),
                      }
                    }}
                    onClick={() => handleLoadPreviousSession(session)}
                  >
                    <Typography
                      variant="caption"
                      sx={{
                        color: theme.palette.text.secondary,
                        pl: 2,
                        pt: 1,
                        fontFamily: 'DM Sans, sans-serif',
                        display: 'block',
                        mb: 1
                      }}
                    >
                      {new Date(session.timestamp).toLocaleDateString()}
                    </Typography>
                    <ListItem
                      sx={{
                        borderRadius: 1,
                        mb: 0.5,
                        bgcolor: alpha(theme.palette.background.paper, 0.3),
                        '&:hover': {
                          bgcolor: alpha(theme.palette.background.paper, 0.6),
                        }
                      }}
                    >
                      <ListItemIcon sx={{ minWidth: 36 }}>
                        <SmartToyIcon fontSize="small" color="inherit" />
                      </ListItemIcon>
                      <ListItemText
                        primary={firstQuery.query.substring(0, 30) + (firstQuery.query.length > 30 ? '...' : '')}
                        secondary={new Date(firstQuery.timestamp).toLocaleTimeString()}
                        primaryTypographyProps={{
                          noWrap: true,
                          fontSize: '0.875rem',
                          fontFamily: 'DM Sans, sans-serif',
                          fontWeight: 500
                        }}
                        secondaryTypographyProps={{
                          fontSize: '0.75rem',
                          fontFamily: 'DM Sans, sans-serif'
                        }}
                      />
                    </ListItem>
                  </Box>
                );
              })}
          </>
        )}
      </List>
    </Drawer>
  );

  const renderInputArea = () => (
    <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-start' }}>
      <input
        type="file"
        accept=".pdf,.docx"
        style={{ display: 'none' }}
        ref={fileInputRef}
        onChange={handleFileUpload}
      />
      <Tooltip title="Upload document (PDF/DOCX)">
        <IconButton
          onClick={() => fileInputRef.current?.click()}
          disabled={loading || isTyping || uploading}
          sx={{
            bgcolor: theme.palette.background.default,
            '&:hover': {
              bgcolor: alpha(theme.palette.background.default, 0.9),
            },
          }}
        >
          {uploading ? (
            <CircularProgress size={24} />
          ) : (
            <UploadFileIcon />
          )}
        </IconButton>
      </Tooltip>
      <Box sx={{ flex: 1 }}>
        {pendingAttachment && (
          <Box sx={{ mb: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
            <Chip
              label={`${pendingAttachment.filename} (${pendingAttachment.doc_type || 'document'})`}
              onDelete={() => setPendingAttachment(null)}
              color="primary"
              variant="outlined"
            />
          </Box>
        )}
        <TextField
        fullWidth
        variant="outlined"
        placeholder="Ask about the uploaded document, request analysis, or ask to generate a new document..."
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
        disabled={loading || isTyping || uploading}
        multiline
        maxRows={4}
        size="small"
        sx={{
          '& .MuiOutlinedInput-root': {
            bgcolor: theme.palette.background.default,
            borderRadius: 2,
            fontSize: '0.9rem',
            fontFamily: 'DM Sans, sans-serif',
            '&:hover': {
              bgcolor: alpha(theme.palette.background.default, 0.9),
            },
            '& fieldset': {
              borderColor: theme.palette.divider,
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
          px: 3,
          minWidth: '100px',
          height: '40px',
          textTransform: 'none',
          fontFamily: 'DM Sans, sans-serif',
          fontWeight: 500,
        }}
        endIcon={loading ? <CircularProgress size={20} color="inherit" /> : <SendIcon />}
      >
        Send
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
        bgcolor: theme.palette.background.default,
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
        }}
      >
        {/* Header */}
        <Box
          component={motion.div}
          initial={{ y: -20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.2 }}
          sx={{
            width: '100%',
            p: 2,
            bgcolor: theme.palette.primary.main,
            color: 'white',
            borderBottom: `1px solid ${alpha(theme.palette.common.white, 0.1)}`,
            display: 'flex',
            alignItems: 'center',
            gap: 2,
            zIndex: 1,
          }}
        >
          {isMobile && (
            <IconButton onClick={() => setDrawerOpen(true)} sx={{ color: 'white' }}>
              <MenuIcon />
            </IconButton>
          )}
          <SmartToyIcon sx={{ fontSize: 24 }} />
          <Box>
            <Typography 
              variant="h6" 
              sx={{ 
                fontWeight: 600,
                fontFamily: 'Montserrat, sans-serif',
                fontSize: '1.1rem',
              }}
            >
              Compliance Assistant
            </Typography>
            <Typography 
              variant="body2" 
              sx={{ 
                opacity: 0.8,
                fontFamily: 'DM Sans, sans-serif',
                fontSize: '0.85rem',
              }}
            >
              Your AI-powered compliance expert
            </Typography>
          </Box>
          <Box sx={{ flex: 1 }} />
          <IconButton 
            onClick={handleReset} 
            sx={{ 
              color: 'white',
              '&:hover': {
                bgcolor: alpha(theme.palette.common.white, 0.1),
              },
            }}
          >
            <DeleteIcon />
          </IconButton>
        </Box>

        {/* Chat Messages */}
        <Box 
          sx={{ 
            flex: 1,
            width: '100%',
            overflow: 'auto',
            display: 'flex',
            flexDirection: 'column',
            p: 3,
            '&::-webkit-scrollbar': {
              width: '4px',
            },
            '&::-webkit-scrollbar-track': {
              background: 'transparent',
            },
            '&::-webkit-scrollbar-thumb': {
              background: theme.palette.divider,
              borderRadius: '2px',
            },
          }}
        >
          <AnimatePresence mode="popLayout">
            {messages.length === 0 ? (
              <Box
                component={motion.div}
                key="empty-state"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
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
                    y: [0, -10, 0],
                    rotate: [0, 5, 0]
                  }}
                  transition={{ 
                    duration: 2,
                    repeat: Infinity,
                    repeatType: "reverse"
                  }}
                >
                  <SmartToyIcon sx={{ fontSize: 64, mb: 2, opacity: 0.5 }} />
                </motion.div>
                <Typography 
                  variant="h5"
                  sx={{ 
                    mb: 1,
                    fontFamily: 'Montserrat, sans-serif',
                    fontWeight: 600,
                  }}
                >
                  Welcome to Compliance Assistant
                </Typography>
                <Typography
                  sx={{ 
                    maxWidth: '500px',
                    fontFamily: 'DM Sans, sans-serif',
                  }}
                >
                  Ask questions about compliance frameworks, security controls, and regulatory requirements.
                </Typography>
              </Box>
            ) : (
              messages.map((message, index) => (
                <Box
                  component={motion.div}
                  key={`${message.type}-${index}`}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
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
                      bgcolor: message.type === 'user' ? theme.palette.primary.main : theme.palette.secondary.main,
                      width: 32,
                      height: 32,
                    }}
                  >
                    {message.type === 'user' ? <PersonIcon /> : <SmartToyIcon />}
                  </Avatar>
                  <Box 
                    sx={{ 
                      maxWidth: '70%',
                      minWidth: '200px',
                    }}
                  >
                    <Paper
                      elevation={1}
                      sx={{
                        p: 2,
                        bgcolor: message.type === 'user' 
                          ? theme.palette.primary.main 
                          : theme.palette.background.paper,
                        color: message.type === 'user' ? 'white' : 'text.primary',
                        borderRadius: 2,
                      }}
                    >
                      {message.type === 'response' && message.isTyping ? (
                        <TypewriterText 
                          text={message.content} 
                          onComplete={() => handleTypingComplete(index)}
                        />
                      ) : (
                        <FormattedResponse content={message.content} />
                      )}
              {message.attachments && message.attachments.length > 0 && (
                <Box sx={{ mt: 1, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  {message.attachments.map((att, i) => (
                    <Chip
                      key={i}
                      label={`${att.filename}${att.doc_type ? ` • ${att.doc_type}` : ''}`}
                      variant="outlined"
                      size="small"
                      onClick={() => {
                        // optionally open a sidebar or just ignore
                      }}
                    />
                  ))}
                </Box>
              )}
              {message.experts && !message.isTyping && (
                        <Box sx={{ mt: 1, pt: 1, borderTop: `1px solid ${theme.palette.divider}` }}>
                          <Typography 
                            variant="caption"
                            sx={{ 
                              color: theme.palette.text.secondary,
                              fontFamily: 'DM Sans, sans-serif',
                            }}
                          >
                            Consulted experts: {message.experts.join(', ')}
                          </Typography>
                        </Box>
                      )}
                      {/* Add feedback buttons for bot responses */}
                      {message.type === 'response' && !message.isTyping && message.originalQuery && (
                        <Box sx={{ mt: 1 }}>
                          {getFeedbackButtons(index, message.originalQuery)}
                        </Box>
                      )}
                    </Paper>
                    <Typography 
                      variant="caption" 
                      sx={{ 
                        display: 'block',
                        mt: 0.5,
                        color: theme.palette.text.secondary,
                        textAlign: message.type === 'user' ? 'right' : 'left',
                      }}
                    >
                      {message.timestamp.toLocaleTimeString()}
                    </Typography>
                  </Box>
                </Box>
              ))
            )}
          </AnimatePresence>
          <div ref={messagesEndRef} />
        </Box>

        {/* Input Area */}
        <Box
          component={motion.div}
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          sx={{ 
            width: '100%',
            p: 2,
            borderTop: `1px solid ${theme.palette.divider}`,
            bgcolor: theme.palette.background.paper,
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