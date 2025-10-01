import React from 'react';
import { Box, Typography, Divider, List, ListItem, ListItemIcon, ListItemText, useTheme } from '@mui/material';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';

const FormattedResponse = ({ content }) => {
  const theme = useTheme();

  const preprocessContent = (text) => {
    if (!text) return '';

    let processedText = text
      .replace(/(https?:\/\/[^\s#]+)#([^\s]+)/g, '$1%23$2')
      .replace(/(\d+)\s*\*\s*(\d+)/g, '$1×$2')
      .replace(/\*\.([a-zA-Z]+)/g, '*.$1')
      .replace(/\/\/\s*#/g, '//%23')
      .replace(/\/\*\s*#/g, '/*%23');

    processedText = processedText
      .replace(/^#+\s*$/gm, '')
      .replace(/\n\s*\n\s*\n+/g, '\n\n')
      .replace(/^#+\s*([^\n]*)\n#+\s*$/gm, '## $1')
      .replace(/^(#{1,6})([^\s#])/gm, '$1 $2')
      .replace(/^#{4,}/gm, '###')
      .replace(/^(#{1,3})\s*([🔍📋🚨⚠️✨📝🎯📚💡🔧📊📥✅❌⭐🎉🏆🔐🛡️📈📉💼🌟⚡🎯])\s*/gm, '$1 $2 ')
      .replace(/^#{1,3}\s*([🔍📋🚨⚠️✨📝🎯📚💡🔧📊📥✅❌⭐🎉🏆🔐🛡️📈📉💼🌟⚡🎯]*)\s*$/gm, '');

    processedText = processedText
      .replace(/###\s+/g, '\n### ')
      .replace(/##\s+/g, '\n## ')
      .replace(/#\s+/g, '\n# ')
      .replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/\[([^\]]+)\]\((\/api\/compliance\/download\/[^)]+)\)/g, '<a href="http://localhost:8000$2" download style="color: #1976d2; text-decoration: none; font-weight: 600; background: linear-gradient(135deg, #1976d2 0%, #42a5f5 100%); padding: 8px 16px; border-radius: 8px; color: white; display: inline-block; margin: 4px 0; transition: all 0.3s ease; box-shadow: 0 2px 8px rgba(25, 118, 210, 0.3);" onmouseover="this.style.transform=\'translateY(-2px)\'; this.style.boxShadow=\'0 4px 12px rgba(25, 118, 210, 0.4)\';" onmouseout="this.style.transform=\'translateY(0)\'; this.style.boxShadow=\'0 2px 8px rgba(25, 118, 210, 0.3)\';">📥 $1</a>')
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" style="color: #1976d2; text-decoration: none; font-weight: 500; border-bottom: 1px solid #1976d2; padding-bottom: 1px;">$1</a>')
      .replace(/\*\s+/g, '\n* ')
      .replace(/-\s+/g, '\n- ')
      .replace(/\n\*\*\*\n/g, '\n<hr/>\n')
      .replace(/^\s*#+\s*$/gm, '')
      .replace(/\n{3,}/g, '\n\n')
      .trim();

    return processedText;
  };

  const formatBulletPoints = (text) => {
    if (!text || !text.trim()) return null;
    const paragraphs = text
      .split(/\n\n+/)
      .map(p => p.trim())
      .filter(p => p && p.length > 0 && p !== '#' && p !== '##' && p !== '###');

    return paragraphs.map((paragraph, index) => {
      if (!paragraph || /^[#\s]*$/.test(paragraph)) return null;
      if (paragraph.includes('* ') || paragraph.includes('- ')) {
        const points = paragraph
          .split(/\n/)
          .filter(line => line.trim().startsWith('* ') || line.trim().startsWith('- '))
          .map(line => line.trim())
          .filter(line => line && line.length > 2);

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
                        fontFamily: 'Inter, sans-serif',
                        lineHeight: 1.6,
                        fontSize: '0.95rem',
                        '& a': { cursor: 'pointer', '&:hover': { opacity: 0.8 } }
                      }}
                      dangerouslySetInnerHTML={{ __html: point.replace(/^[*-]\s+/, '') }}
                    />
                  }
                />
              </ListItem>
            ))}
          </List>
        );
      }

      return (
        <Typography
          key={index}
          variant="body1"
          sx={{
            fontFamily: 'Inter, sans-serif',
            lineHeight: 1.6,
            mb: 2,
            fontSize: '0.95rem',
            '& strong': { fontWeight: 600, color: theme.palette.text.primary },
            '& em': { fontStyle: 'italic', color: theme.palette.text.secondary },
            '& a': { cursor: 'pointer', '&:hover': { opacity: 0.8 } }
          }}
          dangerouslySetInnerHTML={{ __html: paragraph.trim() }}
        />
      );
    }).filter(Boolean);
  };

  const formatContent = (text) => {
    if (!text) return null;
    const processedText = preprocessContent(text);
    const sections = processedText
      .split(/(?=#{1,3}\s[^#\s]|^[*-]\s|<hr\/>)/m)
      .filter(section => section.trim() && section.trim() !== '#' && section.trim() !== '##' && section.trim() !== '###')
      .map(section => section.trim())
      .filter(section => section.length > 0);

    return sections.map((section, index) => {
      if (section.trim() === '<hr/>') {
        return (
          <Divider key={index} sx={{ my: 3, borderColor: theme.palette.divider, opacity: 0.5 }} />
        );
      }

      const headingMatch = section.match(/^(#{1,3})\s+(.+?)$/m);
      if (headingMatch) {
        const level = headingMatch[1].length;
        const headingText = headingMatch[2].trim();
        const contentLines = section.split('\n');
        const content = contentLines.slice(1).join('\n').trim();
        if (headingText && headingText.length > 0 && headingText !== '#' && !/^[🔍📋🚨⚠️✨📝🎯📚💡🔧📊📥✅❌⭐🎉🏆🔐🛡️📈📉💼🌟⚡🎯\s]*$/.test(headingText)) {
          return (
            <Box key={index} sx={{ mb: 3 }}>
              <Typography
                variant={level === 1 ? 'h4' : level === 2 ? 'h5' : 'h6'}
                sx={{
                  fontFamily: 'Poppins, sans-serif',
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

      if (section.trim()) {
        return (
          <Box key={index} sx={{ mb: 2 }}>
            {formatBulletPoints(section)}
          </Box>
        );
      }
      return null;
    }).filter(Boolean);
  };

  return (
    <Box sx={{ width: '100%' }}>
      {content ? formatContent(content) : null}
    </Box>
  );
};

export default FormattedResponse;


