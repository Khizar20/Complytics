import React from 'react';
import { Box, Typography, Divider, List, ListItem, ListItemIcon, ListItemText, useTheme } from '@mui/material';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import { buildApiUrl } from '@/lib/api';

const FormattedResponse = ({ content }) => {
  const theme = useTheme();

  const preprocessContent = (text) => {
    if (!text) return '';

    // First, preserve code blocks before processing
    // Match ```lang\ncode``` or ```code``` patterns
    const codeBlockRegex = /```(\w+)?\n?([\s\S]*?)```/g;
    const codeBlocks = [];
    let codeBlockIndex = 0;
    let processedText = text.replace(codeBlockRegex, (match, lang, code) => {
      const placeholder = `__CODE_BLOCK_${codeBlockIndex}__`;
      const cleanCode = code.trim();
      codeBlocks.push({ placeholder, lang: (lang || 'text').toLowerCase(), code: cleanCode });
      codeBlockIndex++;
      return placeholder;
    });

    let processedText2 = processedText
      .replace(/(https?:\/\/[^\s#]+)#([^\s]+)/g, '$1%23$2')
      .replace(/(\d+)\s*\*\s*(\d+)/g, '$1×$2')
      .replace(/\*\.([a-zA-Z]+)/g, '*.$1')
      .replace(/\/\/\s*#/g, '//%23')
      .replace(/\/\*\s*#/g, '/*%23');

    processedText2 = processedText2
      .replace(/^#+\s*$/gm, '')
      .replace(/\n\s*\n\s*\n+/g, '\n\n')
      .replace(/^#+\s*([^\n]*)\n#+\s*$/gm, '## $1')
      .replace(/^(#{1,6})([^\s#])/gm, '$1 $2')
      .replace(/^#{4,}/gm, '###')
      .replace(/^(#{1,3})\s*([🔍📋🚨⚠️✨📝🎯📚💡🔧📊📥✅❌⭐🎉🏆🔐🛡️📈📉💼🌟⚡🎯])\s*/gm, '$1 $2 ')
      .replace(/^#{1,3}\s*([🔍📋🚨⚠️✨📝🎯📚💡🔧📊📥✅❌⭐🎉🏆🔐🛡️📈📉💼🌟⚡🎯]*)\s*$/gm, '');

    processedText2 = processedText2
      .replace(/###\s+/g, '\n### ')
      .replace(/##\s+/g, '\n## ')
      .replace(/#\s+/g, '\n# ')
      .replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/\[([^\]]+)\]\((\/api\/compliance\/download\/[^)]+)\)/g, (_match, label, path) => `<a href="${buildApiUrl(path)}" download style="color: #1976d2; text-decoration: none; font-weight: 600; background: linear-gradient(135deg, #1976d2 0%, #42a5f5 100%); padding: 8px 16px; border-radius: 8px; color: white; display: inline-block; margin: 4px 0; transition: all 0.3s ease; box-shadow: 0 2px 8px rgba(25, 118, 210, 0.3);" onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 12px rgba(25, 118, 210, 0.4)';" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 8px rgba(25, 118, 210, 0.3)';">📥 ${label}</a>`)
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" style="color: #1976d2; text-decoration: none; font-weight: 500; border-bottom: 1px solid #1976d2; padding-bottom: 1px;">$1</a>')
      .replace(/\*\s+/g, '\n* ')
      .replace(/-\s+/g, '\n- ')
      .replace(/\n\*\*\*\n/g, '\n<hr/>\n')
      .replace(/^\s*#+\s*$/gm, '')
      .replace(/\n{3,}/g, '\n\n')
      .trim();

    // Restore code blocks with metadata
    codeBlocks.forEach(({ placeholder, lang, code }) => {
      processedText2 = processedText2.replace(placeholder, `__CODE_BLOCK_${lang}__${code}__END_CODE_BLOCK__`);
    });

    return { text: processedText2, codeBlocks };
  };

  const renderCodeBlock = (code, lang = 'text') => {
    // Escape HTML in code
    const escapedCode = code
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');

    return (
      <Box
        sx={{
          my: 2,
          borderRadius: 1,
          overflow: 'hidden',
          border: `1px solid ${theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'}`,
          backgroundColor: theme.palette.mode === 'dark' ? 'rgba(0,0,0,0.3)' : 'rgba(0,0,0,0.02)'
        }}
      >
        {lang !== 'text' && (
          <Box
            sx={{
              px: 2,
              py: 0.5,
              fontSize: '0.75rem',
              fontWeight: 600,
              textTransform: 'uppercase',
              color: theme.palette.text.secondary,
              backgroundColor: theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)',
              borderBottom: `1px solid ${theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'}`
            }}
          >
            {lang}
          </Box>
        )}
        <Box
          component="pre"
          sx={{
            m: 0,
            p: 2,
            fontSize: '0.875rem',
            fontFamily: 'Monaco, Consolas, "Courier New", monospace',
            lineHeight: 1.6,
            overflowX: 'auto',
            color: theme.palette.text.primary,
            backgroundColor: 'transparent'
          }}
        >
          <code dangerouslySetInnerHTML={{ __html: escapedCode }} />
        </Box>
      </Box>
    );
  };

  const formatBulletPoints = (text, codeBlocks = []) => {
    if (!text || !text.trim()) return null;
    
    // Replace code block placeholders with actual components
    let processedText = text;
    codeBlocks.forEach((block, idx) => {
      const placeholder = `__CODE_BLOCK_${block.lang}__${block.code}__END_CODE_BLOCK__`;
      const componentId = `code-block-${idx}`;
      processedText = processedText.replace(placeholder, `__CODE_COMPONENT_${componentId}__`);
    });

    const paragraphs = processedText
      .split(/\n\n+/)
      .map(p => p.trim())
      .filter(p => p && p.length > 0 && p !== '#' && p !== '##' && p !== '###');

    return paragraphs.map((paragraph, index) => {
      if (!paragraph || /^[#\s]*$/.test(paragraph)) return null;
      
      // Check for code block placeholders
      const codeBlockMatch = paragraph.match(/__CODE_COMPONENT_(code-block-\d+)__/);
      if (codeBlockMatch) {
        const blockId = codeBlockMatch[1];
        const blockIndex = parseInt(blockId.replace('code-block-', ''));
        const block = codeBlocks[blockIndex];
        if (block) {
          return (
            <Box key={index}>
              {renderCodeBlock(block.code, block.lang)}
            </Box>
          );
        }
      }

      // Check if paragraph contains code blocks
      const parts = paragraph.split(/(__CODE_COMPONENT_code-block-\d+__)/);
      if (parts.length > 1) {
        return (
          <Box key={index} sx={{ mb: 2 }}>
            {parts.map((part, partIndex) => {
              const codeMatch = part.match(/__CODE_COMPONENT_(code-block-\d+)__/);
              if (codeMatch) {
                const blockId = codeMatch[1];
                const blockIndex = parseInt(blockId.replace('code-block-', ''));
                const block = codeBlocks[blockIndex];
                if (block) {
                  return <Box key={partIndex}>{renderCodeBlock(block.code, block.lang)}</Box>;
                }
              }
              if (part.trim()) {
                return (
                  <Typography
                    key={partIndex}
                    variant="body1"
                    component="span"
                    sx={{
                      fontFamily: 'DM Sans, sans-serif',
                      lineHeight: 1.6,
                      fontSize: '0.95rem',
                      display: 'inline',
                      '& strong': { fontWeight: 600, color: theme.palette.text.primary },
                      '& em': { fontStyle: 'italic', color: theme.palette.text.secondary },
                      '& a': { cursor: 'pointer', '&:hover': { opacity: 0.8 } }
                    }}
                    dangerouslySetInnerHTML={{ __html: part }}
                  />
                );
              }
              return null;
            })}
          </Box>
        );
      }

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
                        fontFamily: 'DM Sans, sans-serif',
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
                        fontFamily: 'DM Sans, sans-serif',
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
    const { text: processedText, codeBlocks } = preprocessContent(text);
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
                  {formatBulletPoints(content, codeBlocks)}
                </Box>
              )}
            </Box>
          );
        }
      }

      if (section.trim()) {
        return (
          <Box key={index} sx={{ mb: 2 }}>
            {formatBulletPoints(section, codeBlocks)}
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


