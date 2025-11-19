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
      .replace(/\[([^\]]+)\]\((\/api\/compliance\/download\/[^)]+)\)/g, (_match, label, path) => `<a href="${buildApiUrl(path)}" download style="color: #1976d2; text-decoration: none; font-weight: 600; background: linear-gradient(135deg, #1976d2 0%, #42a5f5 100%); padding: 8px 16px; border-radius: 8px; color: white; display: inline-block; margin: 4px 0; transition: all 0.3s ease; box-shadow: 0 2px 8px rgba(25, 118, 210, 0.3);" onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 12px rgba(25, 118, 210, 0.4)';" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 8px rgba(25, 118, 210, 0.3)';">${label}</a>`)
      // Regular markdown links - convert [text](url) to clickable links
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" style="color: #1976d2; text-decoration: none; font-weight: 500; border-bottom: 1px solid #1976d2; padding-bottom: 1px;">$1</a>')
      // Evidence-based citations - highlight with green background
      // Matches patterns like: (Legal Basis: "quote" - Source) or (Evidence: "quote" - Framework)
      .replace(/(\((?:Legal Basis|Evidence|Source|Regulation|Framework|Based on):\s*"[^"]+"\s*(?:-\s*[^)]+)?\))/gi, '<span class="evidence-citation" style="background: linear-gradient(135deg, rgba(76, 175, 80, 0.12) 0%, rgba(129, 199, 132, 0.12) 100%); border-left: 3px solid #4CAF50; padding: 4px 8px 4px 12px; border-radius: 6px; display: inline-block; margin: 2px 0; font-size: 0.9em; color: #2E7D32; font-weight: 500; box-shadow: 0 1px 3px rgba(76, 175, 80, 0.1);">$1</span>')
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
        gap: 1, 
        mt: 1.5, 
        justifyContent: 'flex-start',
        opacity: 0.7,
        '&:hover': { opacity: 1 },
        transition: 'opacity 0.2s ease'
      }}>
        <Tooltip title={currentFeedback === true ? "You found this helpful" : "Mark as helpful"} arrow>
          <IconButton 
            size="small"
            onClick={() => handleFeedback(messageIndex, true, originalQuery)}
            disabled={currentFeedback !== undefined}
            sx={{ 
              color: currentFeedback === true ? theme.palette.success.main : 'inherit',
              bgcolor: currentFeedback === true ? alpha(theme.palette.success.main, 0.1) : 'transparent',
              border: `1px solid ${currentFeedback === true ? theme.palette.success.main : 'transparent'}`,
              '&:hover': { 
                bgcolor: currentFeedback === true 
                  ? alpha(theme.palette.success.main, 0.2)
                  : alpha(theme.palette.action.hover, 0.05),
                borderColor: currentFeedback === true ? theme.palette.success.main : theme.palette.divider
              },
              transition: 'all 0.2s ease'
            }}
          >
            {currentFeedback === true ? <ThumbUpIcon fontSize="small" /> : <ThumbUpOffAltIcon fontSize="small" />}
          </IconButton>
        </Tooltip>
        <Tooltip title={currentFeedback === false ? "You marked this as not helpful" : "Mark as not helpful"} arrow>
          <IconButton 
            size="small"
            onClick={() => handleFeedback(messageIndex, false, originalQuery)}
            disabled={currentFeedback !== undefined}
            sx={{ 
              color: currentFeedback === false ? theme.palette.error.main : 'inherit',
              bgcolor: currentFeedback === false ? alpha(theme.palette.error.main, 0.1) : 'transparent',
              border: `1px solid ${currentFeedback === false ? theme.palette.error.main : 'transparent'}`,
              '&:hover': { 
                bgcolor: currentFeedback === false 
                  ? alpha(theme.palette.error.main, 0.2)
                  : alpha(theme.palette.action.hover, 0.05),
                borderColor: currentFeedback === false ? theme.palette.error.main : theme.palette.divider
              },
              transition: 'all 0.2s ease'
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
            height: '100%',
            boxSizing: 'border-box',
            background: `linear-gradient(180deg, ${alpha(theme.palette.background.default, 0.95)} 0%, ${alpha(theme.palette.background.paper, 0.95)} 100%)`,
            backdropFilter: 'blur(20px)',
            border: 'none',
            borderRight: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
            boxShadow: `inset -1px 0 0 ${alpha(theme.palette.primary.main, 0.05)}`,
          },
        }}
      >
      <Box sx={{ 
        px: 2,
        py: 2.2,
        height: '80.44px',
        borderBottom: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
        background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.08)} 0%, ${alpha(theme.palette.secondary.main, 0.05)} 100%)`,
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
              border: `1px solid ${alpha(theme.palette.primary.main, 0.3)}`,
              color: theme.palette.primary.main,
              '&:hover': {
                borderColor: theme.palette.primary.main,
                bgcolor: alpha(theme.palette.primary.main, 0.05)
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
            background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.primary.dark} 100%)`,
            color: 'white',
            fontFamily: 'Montserrat, sans-serif',
            fontWeight: 600,
            textTransform: 'none',
            py: 1,
            boxShadow: `0 4px 12px ${alpha(theme.palette.primary.main, 0.3)}`,
            '&:hover': {
              background: `linear-gradient(135deg, ${theme.palette.primary.dark} 0%, ${theme.palette.primary.main} 100%)`,
              boxShadow: `0 6px 16px ${alpha(theme.palette.primary.main, 0.4)}`,
              transform: 'translateY(-1px)'
            },
            transition: 'all 0.3s ease'
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
          width: '6px',
        },
        '&::-webkit-scrollbar-track': {
          background: 'transparent',
        },
        '&::-webkit-scrollbar-thumb': {
          background: alpha(theme.palette.primary.main, 0.2),
          borderRadius: '3px',
          '&:hover': {
            background: alpha(theme.palette.primary.main, 0.3),
          }
        },
      }}>
        <Typography
          variant="overline"
          sx={{
            color: theme.palette.text.secondary,
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
                background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.15)} 0%, ${alpha(theme.palette.secondary.main, 0.1)} 100%)`,
                border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`,
                '&:hover': {
                  background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.2)} 0%, ${alpha(theme.palette.secondary.main, 0.15)} 100%)`,
                  transform: 'translateX(4px)',
                  boxShadow: `0 4px 12px ${alpha(theme.palette.primary.main, 0.2)}`
                },
                transition: 'all 0.3s ease',
                cursor: 'pointer'
              }}
            >
              <ListItemIcon sx={{ minWidth: 36 }}>
                <SmartToyIcon fontSize="small" sx={{ color: theme.palette.primary.main }} />
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
                  fontSize: '0.7rem',
                  fontFamily: 'DM Sans, sans-serif',
                  color: theme.palette.text.secondary
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
                      background: alpha(theme.palette.background.paper, 0.4),
                      border: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
                      '&:hover': {
                        background: alpha(theme.palette.background.paper, 0.7),
                        borderColor: alpha(theme.palette.primary.main, 0.3),
                        transform: 'translateX(4px)',
                        boxShadow: `0 4px 12px ${alpha(theme.palette.primary.main, 0.1)}`
                      },
                      transition: 'all 0.3s ease'
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
                          fontSize: '0.7rem',
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
            background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.1)} 0%, ${alpha(theme.palette.secondary.main, 0.1)} 100%)`,
            border: `2px solid ${alpha(theme.palette.primary.main, 0.2)}`,
            width: 48,
            height: 48,
            '&:hover': {
              background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.2)} 0%, ${alpha(theme.palette.secondary.main, 0.2)} 100%)`,
              borderColor: theme.palette.primary.main,
              transform: 'translateY(-2px)',
              boxShadow: `0 6px 16px ${alpha(theme.palette.primary.main, 0.3)}`
            },
            '&:disabled': {
              opacity: 0.5
            },
            transition: 'all 0.3s ease'
          }}
        >
          {uploading ? (
            <CircularProgress size={24} sx={{ color: theme.palette.primary.main }} />
          ) : (
            <UploadFileIcon sx={{ color: theme.palette.primary.main }} />
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
            background: alpha(theme.palette.background.default, 0.5),
            backdropFilter: 'blur(10px)',
            borderRadius: 3,
            fontSize: '0.95rem',
            fontFamily: 'DM Sans, sans-serif',
            padding: '12px 16px',
            border: `2px solid ${alpha(theme.palette.primary.main, 0.1)}`,
            transition: 'all 0.3s ease',
            '&:hover': {
              background: alpha(theme.palette.background.default, 0.7),
              borderColor: alpha(theme.palette.primary.main, 0.3),
            },
            '&.Mui-focused': {
              background: alpha(theme.palette.background.default, 0.9),
              borderColor: theme.palette.primary.main,
              boxShadow: `0 0 0 4px ${alpha(theme.palette.primary.main, 0.1)}`
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
          px: 4,
          minWidth: '120px',
          height: '48px',
          borderRadius: 3,
          textTransform: 'none',
          fontFamily: 'DM Sans, sans-serif',
          fontWeight: 600,
          fontSize: '0.95rem',
          background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.primary.dark} 100%)`,
          boxShadow: `0 4px 14px ${alpha(theme.palette.primary.main, 0.4)}`,
          '&:hover': {
            background: `linear-gradient(135deg, ${theme.palette.primary.dark} 0%, ${theme.palette.primary.main} 100%)`,
            boxShadow: `0 6px 20px ${alpha(theme.palette.primary.main, 0.5)}`,
            transform: 'translateY(-2px)'
          },
          '&:disabled': {
            background: alpha(theme.palette.action.disabled, 0.12),
            color: theme.palette.action.disabled
          },
          transition: 'all 0.3s ease'
        }}
        endIcon={loading ? <CircularProgress size={20} color="inherit" /> : <SendIcon />}
      >
        {loading ? 'Sending' : 'Send'}
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
        {/* Modern Header with Gradient */}
        <Box
          component={motion.div}
          initial={{ y: -20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.2 }}
          sx={{
            width: '100%',
            px: 2,
            py: 2.2,
            height: '80.44px',
            background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.primary.dark} 100%)`,
            boxShadow: `0 4px 24px ${alpha(theme.palette.primary.main, 0.4)}`,
            display: 'flex',
            alignItems: 'center',
            gap: 2,
            zIndex: 1,
            position: 'relative',
            boxSizing: 'border-box',
            '&::before': {
              content: '""',
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: `radial-gradient(circle at 20% 50%, ${alpha(theme.palette.secondary.main, 0.2)} 0%, transparent 50%)`,
              pointerEvents: 'none'
            }
          }}
        >
          {isMobile && (
            <IconButton onClick={() => setDrawerOpen(true)} sx={{ color: 'white', zIndex: 1 }}>
              <MenuIcon />
            </IconButton>
          )}
          <Box
            sx={{
              width: 40,
              height: 40,
              borderRadius: 2,
              background: alpha('#ffffff', 0.15),
              backdropFilter: 'blur(10px)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 1
            }}
          >
            <SmartToyIcon sx={{ fontSize: 24, color: 'white' }} />
          </Box>
          <Box sx={{ zIndex: 1 }}>
            <Typography 
              variant="h5" 
              sx={{ 
                fontWeight: 700,
                fontFamily: 'Montserrat, sans-serif',
                fontSize: '1.2rem',
                color: 'white',
                letterSpacing: '-0.02em',
                lineHeight: 1.2
              }}
            >
              Compliance Assistant
            </Typography>
            <Typography 
              variant="body2" 
              sx={{ 
                opacity: 0.9,
                fontFamily: 'DM Sans, sans-serif',
                fontSize: '0.75rem',
                color: 'white',
                mt: 0.2,
                lineHeight: 1.3
              }}
            >
              <SecurityIcon sx={{ fontSize: 12, mr: 0.5, verticalAlign: 'middle' }} />
              Your intelligent compliance & security expert
            </Typography>
          </Box>
          <Box sx={{ flex: 1 }} />
          <Tooltip title="Clear conversation" arrow>
            <IconButton 
              onClick={handleReset} 
              sx={{ 
                color: 'white',
                background: alpha('#ffffff', 0.1),
                backdropFilter: 'blur(10px)',
                border: `1px solid ${alpha('#ffffff', 0.2)}`,
                '&:hover': {
                  background: alpha('#ffffff', 0.2),
                  transform: 'rotate(180deg)',
                  borderColor: alpha('#ffffff', 0.4)
                },
                transition: 'all 0.4s ease',
                zIndex: 1
              }}
            >
              <DeleteIcon />
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
            background: `radial-gradient(ellipse at top, ${alpha(theme.palette.primary.main, 0.02)} 0%, transparent 50%)`,
            '&::-webkit-scrollbar': {
              width: '8px',
            },
            '&::-webkit-scrollbar-track': {
              background: alpha(theme.palette.background.paper, 0.3),
              borderRadius: '4px',
            },
            '&::-webkit-scrollbar-thumb': {
              background: alpha(theme.palette.primary.main, 0.3),
              borderRadius: '4px',
              '&:hover': {
                background: alpha(theme.palette.primary.main, 0.5),
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
                    y: [0, -15, 0],
                    rotate: [0, 5, -5, 0]
                  }}
                  transition={{ 
                    duration: 3,
                    repeat: Infinity,
                    repeatType: "reverse",
                    ease: "easeInOut"
                  }}
                >
                  <Box
                    sx={{
                      width: 120,
                      height: 120,
                      borderRadius: 4,
                      background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.1)} 0%, ${alpha(theme.palette.secondary.main, 0.1)} 100%)`,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      mb: 3,
                      boxShadow: `0 8px 32px ${alpha(theme.palette.primary.main, 0.2)}`,
                      border: `2px solid ${alpha(theme.palette.primary.main, 0.2)}`
                    }}
                  >
                    <SmartToyIcon sx={{ fontSize: 64, color: theme.palette.primary.main, opacity: 0.8 }} />
                  </Box>
                </motion.div>
                <Typography 
                  variant="h4"
                  sx={{ 
                    mb: 2,
                    fontFamily: 'Montserrat, sans-serif',
                    fontWeight: 700,
                    background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.secondary.main} 100%)`,
                    backgroundClip: 'text',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    letterSpacing: '-0.02em'
                  }}
                >
                  Welcome to Compliance Assistant
                </Typography>
                <Typography
                  variant="h6"
                  sx={{ 
                    maxWidth: '600px',
                    fontFamily: 'DM Sans, sans-serif',
                    color: theme.palette.text.secondary,
                    lineHeight: 1.6,
                    mb: 3
                  }}
                >
                  Your intelligent expert for compliance frameworks, security controls, and regulatory requirements
                </Typography>
                <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', justifyContent: 'center', mt: 2 }}>
                  {['GDPR', 'HIPAA', 'ISO 27001', 'SOC 2'].map((framework) => (
                    <Chip
                      key={framework}
                      label={framework}
                      sx={{
                        background: alpha(theme.palette.primary.main, 0.08),
                        color: theme.palette.primary.main,
                        fontWeight: 600,
                        fontSize: '0.85rem',
                        px: 1,
                        border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`,
                        '&:hover': {
                          background: alpha(theme.palette.primary.main, 0.15),
                          transform: 'translateY(-2px)',
                          boxShadow: `0 4px 12px ${alpha(theme.palette.primary.main, 0.2)}`
                        },
                        transition: 'all 0.3s ease'
                      }}
                    />
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
                        width: 40,
                        height: 40,
                        boxShadow: message.type === 'user'
                          ? `0 4px 14px ${alpha(theme.palette.primary.main, 0.4)}`
                          : `0 4px 14px ${alpha(theme.palette.secondary.main, 0.4)}`,
                        border: `2px solid ${alpha('#ffffff', 0.1)}`
                      }}
                    >
                      {message.type === 'user' ? <PersonIcon /> : <SmartToyIcon />}
                    </Avatar>
                    <Box 
                      sx={{ 
                        maxWidth: '75%',
                        minWidth: '200px',
                      }}
                    >
                      <Paper
                        elevation={0}
                        sx={{
                          p: 2.5,
                          background: message.type === 'user' 
                            ? `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.primary.dark} 100%)`
                            : `linear-gradient(135deg, ${alpha(theme.palette.background.paper, 0.9)} 0%, ${alpha(theme.palette.background.default, 0.9)} 100%)`,
                          backdropFilter: 'blur(10px)',
                          color: message.type === 'user' ? 'white' : 'text.primary',
                          borderRadius: 3,
                          border: message.type === 'user' 
                            ? `1px solid ${alpha('#ffffff', 0.1)}`
                            : `1px solid ${alpha(theme.palette.primary.main, 0.1)}`,
                          boxShadow: message.type === 'user'
                            ? `0 8px 24px ${alpha(theme.palette.primary.main, 0.3)}`
                            : `0 8px 24px ${alpha(theme.palette.divider, 0.1)}`,
                          position: 'relative',
                          overflow: 'hidden',
                          '&::before': message.type !== 'user' ? {
                            content: '""',
                            position: 'absolute',
                            top: 0,
                            left: 0,
                            width: '4px',
                            height: '100%',
                            background: `linear-gradient(180deg, ${theme.palette.primary.main} 0%, ${theme.palette.secondary.main} 100%)`
                          } : {}
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
                            mt: 2, 
                            pt: 2, 
                            borderTop: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
                            display: 'flex',
                            alignItems: 'center',
                            gap: 1
                          }}>
                            <AutoAwesomeIcon sx={{ fontSize: 14, color: theme.palette.primary.main, opacity: 0.7 }} />
                            <Typography 
                              variant="caption"
                              sx={{ 
                                color: theme.palette.text.secondary,
                                fontFamily: 'DM Sans, sans-serif',
                                fontSize: '0.75rem',
                                fontStyle: 'italic'
                              }}
                            >
                              Consulted experts: {message.experts.join(', ')}
                            </Typography>
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
                          mt: 1,
                          ml: message.type === 'user' ? 0 : 1,
                          mr: message.type === 'user' ? 1 : 0,
                          color: theme.palette.text.secondary,
                          textAlign: message.type === 'user' ? 'right' : 'left',
                          fontFamily: 'DM Sans, sans-serif',
                          fontSize: '0.7rem'
                        }}
                      >
                        {message.timestamp.toLocaleTimeString()}
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
            p: 3,
            background: `linear-gradient(180deg, transparent 0%, ${alpha(theme.palette.background.paper, 0.8)} 20%, ${alpha(theme.palette.background.paper, 0.95)} 100%)`,
            backdropFilter: 'blur(10px)',
            borderTop: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
            boxShadow: `0 -4px 24px ${alpha(theme.palette.divider, 0.1)}`
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
